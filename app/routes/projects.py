from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    repo_url: str
    skill_level: str
    domain: str

@router.post("/projects")
async def create_project(data: ProjectCreateRequest):
    print("🎯 New Project Received:")
    print(f"Repo URL: {data.repo_url}")
    print(f"Skill Level: {data.skill_level}")
    print(f"Domain: {data.domain}")
    return {"message": "Project received successfully"}
