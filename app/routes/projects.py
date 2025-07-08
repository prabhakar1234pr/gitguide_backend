from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import json
import httpx
import os
from app.models import Project
from app.db import SessionLocal

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    repo_url: str
    skill_level: str
    domain: str

def extract_user_id_from_token(authorization: str = None) -> str:
    """Extract Clerk user ID from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decode JWT without verification for now (in production, verify with Clerk's public key)
        # This extracts the user ID from Clerk's JWT payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get("sub")  # 'sub' contains the Clerk user ID
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID found")
            
        return user_id
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

async def get_user_details_from_clerk(user_id: str):
    """Fetch user details from Clerk API"""
    try:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        if not clerk_secret_key:
            return {"name": "Unknown User", "email": "unknown@example.com"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {clerk_secret_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                    "email": user_data.get('email_addresses', [{}])[0].get('email_address', 'unknown@example.com')
                }
            else:
                return {"name": "Unknown User", "email": "unknown@example.com"}
                
    except Exception as e:
        print(f"Error fetching user details: {e}")
        return {"name": "Unknown User", "email": "unknown@example.com"}

@router.post("/projects")
async def create_project(
    data: ProjectCreateRequest,
    authorization: str = Header(None)
):
    print("🎯 New Project Received:")
    print(f"Repo URL: {data.repo_url}")
    print(f"Skill Level: {data.skill_level}")
    print(f"Domain: {data.domain}")
    
    # Extract real Clerk user ID from JWT token
    user_id = extract_user_id_from_token(authorization)
    print(f"👤 User ID: {user_id}")
    
    # Create database session and save project
    async with SessionLocal() as session:
        try:
            # Create new project instance with real Clerk user_id
            new_project = Project(
                user_id=user_id,
                repo_url=data.repo_url,
                skill_level=data.skill_level,
                domain=data.domain
            )
            
            # Add to session and commit
            session.add(new_project)
            await session.commit()
            await session.refresh(new_project)
            
            print(f"✅ Project saved to database with project_id: {new_project.project_id}")
            return {
                "message": "Project saved successfully to database",
                "project_id": new_project.project_id,
                "user_id": new_project.user_id
            }
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")

@router.get("/projects")
async def get_user_projects(authorization: str = Header(None)):
    """Get all projects for the authenticated user with user details"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Project).filter(Project.user_id == user_id)
            )
            projects = result.scalars().all()
            
            # Get user details from Clerk
            user_details = await get_user_details_from_clerk(user_id)
            
            return {
                "user": {
                    "id": user_id,
                    "name": user_details["name"],
                    "email": user_details["email"]
                },
                "projects": [
                    {
                        "project_id": p.project_id,
                        "repo_url": p.repo_url,
                        "skill_level": p.skill_level,
                        "domain": p.domain,
                        "user_id": p.user_id
                    }
                    for p in projects
                ]
            }
            
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get projects: {str(e)}")

@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str):
    """Get user details by Clerk user ID"""
    try:
        user_details = await get_user_details_from_clerk(user_id)
        return {
            "user_id": user_id,
            "name": user_details["name"],
            "email": user_details["email"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user details: {str(e)}")
