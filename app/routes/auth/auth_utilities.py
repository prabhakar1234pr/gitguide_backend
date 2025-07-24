"""
Authentication helper utilities for GitGuide API
Shared across all route modules to eliminate duplication
"""

from fastapi import HTTPException
import jwt
import httpx
import os
from typing import Dict


def extract_user_id_from_token(authorization: str = None) -> str:
    """Extract Clerk user ID from JWT token (shared utility)"""
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


async def get_user_details_from_clerk(user_id: str) -> Dict[str, str]:
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