"""
Days endpoints for GitGuide
API endpoints for managing 14-day learning progression
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import json

from app.database_config import get_db
from app.routes.shared.days_utilities import (
    get_project_days, 
    get_current_day, 
    mark_day_completed,
    unlock_next_day,
    verify_day0_repository,
    get_day0_verification_status,
    verify_github_profile,
    verify_repository_creation_task,
    verify_commit_task
)

router = APIRouter()

class DayCompleteRequest(BaseModel):
    project_id: int
    day_number: int

class Day0VerificationRequest(BaseModel):
    repo_url: str

class DayResponse(BaseModel):
    day_id: int
    project_id: int
    day_number: int
    day_external_id: str
    name: str
    description: str
    is_unlocked: bool
    is_completed: bool
    order: int
    requires_verification: bool = False
    verification_repo_url: str = None
    is_verified: bool = False

class TaskVerificationRequest(BaseModel):
    verification_data: str  # URL or other data needed for verification

@router.get("/projects/{project_id}/days")
async def get_project_days_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get all 14 days for a project with their unlock/completion status"""
    try:
        print(f"📅 Getting days for project {project_id}")
        
        days = await get_project_days(db, project_id)
        
        if not days:
            raise HTTPException(
                status_code=404, 
                detail=f"No days found for project {project_id}. Run the migration or create a new project."
            )
        
        print(f"✅ Found {len(days)} days for project {project_id}")
        
        return {
            "success": True,
            "project_id": project_id,
            "total_days": len(days),
            "days": days,
            "current_day": next((d for d in days if d['is_unlocked'] and not d['is_completed']), None),
            "completed_days": len([d for d in days if d['is_completed']]),
            "unlocked_days": len([d for d in days if d['is_unlocked']])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting days for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get days: {str(e)}")

@router.get("/projects/{project_id}/days/current")
async def get_current_day_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get the current active day (unlocked but not completed)"""
    try:
        print(f"🎯 Getting current day for project {project_id}")
        
        current_day = await get_current_day(db, project_id)
        
        if not current_day:
            return {
                "success": True,
                "project_id": project_id,
                "current_day": None,
                "message": "No active day found. All days may be completed or none unlocked."
            }
        
        print(f"✅ Current day for project {project_id}: Day {current_day['day_number']}")
        
        return {
            "success": True,
            "project_id": project_id,
            "current_day": current_day
        }
        
    except Exception as e:
        print(f"❌ Error getting current day for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get current day: {str(e)}")

@router.post("/projects/{project_id}/days/{day_number}/complete")
async def mark_day_complete_endpoint(
    project_id: int,
    day_number: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Mark a day as completed and unlock the next day"""
    try:
        print(f"✅ Marking Day {day_number} as completed for project {project_id}")
        
        if day_number < 0 or day_number > 14:
            raise HTTPException(status_code=400, detail="Day number must be between 0 and 14")
        
        success = await mark_day_completed(db, project_id, day_number)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to mark day as completed")
        
        # Get updated current day
        current_day = await get_current_day(db, project_id)
        
        return {
            "success": True,
            "project_id": project_id,
            "completed_day": day_number,
            "message": f"Day {day_number} marked as completed",
            "current_day": current_day,
            "next_day_unlocked": current_day['day_number'] == day_number + 1 if current_day else False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error marking day {day_number} complete for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark day complete: {str(e)}")

@router.post("/projects/{project_id}/days/{day_number}/unlock")
async def unlock_day_endpoint(
    project_id: int,
    day_number: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Manually unlock a specific day (admin/testing function)"""
    try:
        print(f"🔓 Manually unlocking Day {day_number} for project {project_id}")
        
        if day_number < 0 or day_number > 14:
            raise HTTPException(status_code=400, detail="Day number must be between 0 and 14")
        
        # This is a simplified unlock - doesn't check prerequisites
        from sqlalchemy import text
        await db.execute(text("""
            UPDATE days 
            SET is_unlocked = TRUE 
            WHERE project_id = :project_id AND day_number = :day_number
        """), {'project_id': project_id, 'day_number': day_number})
        
        await db.commit()
        
        return {
            "success": True,
            "project_id": project_id,
            "unlocked_day": day_number,
            "message": f"Day {day_number} manually unlocked"
        }
        
    except Exception as e:
        print(f"❌ Error unlocking day {day_number} for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to unlock day: {str(e)}")

@router.post("/projects/{project_id}/days/0/verify")
async def verify_day0_repository_endpoint(
    project_id: int,
    verification_request: Day0VerificationRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Verify Day 0 GitHub repository and unlock Day 1"""
    try:
        print(f"🔍 Verifying Day 0 repository for project {project_id}")
        print(f"📍 Repository URL: {verification_request.repo_url}")
        
        result = await verify_day0_repository(db, project_id, verification_request.repo_url)
        
        if result['success']:
            print(f"✅ Day 0 verification successful for project {project_id}")
            return {
                "success": True,
                "project_id": project_id,
                "message": result['message'],
                "repo_info": result.get('repo_info')
            }
        else:
            print(f"❌ Day 0 verification failed for project {project_id}: {result['error']}")
            return {
                "success": False,
                "project_id": project_id,
                "error": result['error']
            }
        
    except Exception as e:
        print(f"❌ Error verifying Day 0 for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify repository: {str(e)}")

@router.get("/projects/{project_id}/days/0/verification-status")
async def get_day0_verification_status_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get Day 0 verification status"""
    try:
        print(f"📊 Getting Day 0 verification status for project {project_id}")
        
        status = await get_day0_verification_status(db, project_id)
        
        return {
            "success": True,
            "project_id": project_id,
            "verification_status": status
        }
        
    except Exception as e:
        print(f"❌ Error getting Day 0 status for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get verification status: {str(e)}")

@router.get("/projects/{project_id}/days/progress")
async def get_days_progress_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get progress statistics for days"""
    try:
        days = await get_project_days(db, project_id)
        
        if not days:
            raise HTTPException(status_code=404, detail="No days found for project")
        
        total_days = len(days)
        completed_days = len([d for d in days if d['is_completed']])
        unlocked_days = len([d for d in days if d['is_unlocked']])
        progress_percentage = (completed_days / total_days) * 100
        
        return {
            "success": True,
            "project_id": project_id,
            "progress": {
                "total_days": total_days,
                "completed_days": completed_days,
                "unlocked_days": unlocked_days,
                "remaining_days": total_days - completed_days,
                "progress_percentage": round(progress_percentage, 1),
                "current_streak": _calculate_current_streak(days),
                "days_until_completion": total_days - completed_days
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting progress for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.post("/projects/{project_id}/tasks/{task_id}/verify")
async def verify_task_endpoint(
    project_id: int,
    task_id: int,  # Change to int
    verification_request: TaskVerificationRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Verify Day 0 task completion based on verification type"""
    try:
        print(f"🔍 Verifying task {task_id} for project {project_id}")
        from sqlalchemy import text
        # Use integer task_id for lookup
        result = await db.execute(text("""
            SELECT task_id, verification_type 
            FROM tasks 
            WHERE project_id = :project_id
            AND task_id = :task_id
        """), {
            'project_id': project_id,
            'task_id': task_id
        })
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        db_task_id = row[0]
        verification_type = row[1]
        if not verification_type:
            raise HTTPException(status_code=404, detail="No verification required for this task")
        verification_data = verification_request.verification_data.strip()
        # Route to appropriate verification function
        if verification_type == 'github_profile':
            result = await verify_github_profile(db, project_id, db_task_id, verification_data)
        elif verification_type == 'repository_creation':
            result = await verify_repository_creation_task(db, project_id, db_task_id, verification_data)
        elif verification_type == 'commit_verification':
            result = await verify_commit_task(db, project_id, db_task_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown verification type: {verification_type}")
        if result['success']:
            print(f"✅ Task {task_id} verification successful")
            return {
                "success": True,
                "project_id": project_id,
                "task_id": task_id,
                "verification_type": verification_type,
                "message": result['message'],
                "data": result.get('profile_info') or result.get('repo_info') or result.get('commit_info')
            }
        else:
            print(f"❌ Task {task_id} verification failed: {result['error']}")
            return {
                "success": False,
                "project_id": project_id,
                "task_id": task_id,
                "verification_type": verification_type,
                "error": result['error']
            }
    except Exception as e:
        print(f"❌ Error verifying task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify task: {str(e)}")

@router.get("/projects/{project_id}/days/0/concepts")
async def get_day0_concepts_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get Day 0 concepts and tasks for a project"""
    try:
        from sqlalchemy import text
        
        print(f"📚 Getting Day 0 concepts for project {project_id}")
        
        # Get Day 0 concepts with their tasks
        result = await db.execute(text("""
            SELECT 
                c.concept_id,
                c.title,
                c.description,
                c.is_unlocked,
                c.is_completed,
                c.order,
                t.task_id,
                t.title as task_title,
                t.description as task_description,
                t.verification_type,
                t.is_completed as task_completed,
                t.is_verified as task_verified,
                t.verification_data,
                t.order as task_order
            FROM concepts c
            JOIN days d ON c.day_id = d.day_id
            LEFT JOIN tasks t ON t.concept_id = c.concept_id
            WHERE d.project_id = :project_id AND d.day_number = 0
            ORDER BY c.order, t.order
        """), {'project_id': project_id})
        
        rows = result.fetchall()
        
        if not rows:
            raise HTTPException(status_code=404, detail="Day 0 concepts not found for this project")
        
        # Group tasks by concept
        concepts = {}
        for row in rows:
            concept_id = row[0]
            
            if concept_id not in concepts:
                concepts[concept_id] = {
                    'concept_id': concept_id,
                    'title': row[1],
                    'description': row[2],
                    'is_unlocked': row[3],
                    'is_completed': row[4],
                    'order': row[5],
                    'tasks': []
                }
            
            # Add task if it exists
            if row[6]:  # task_id exists
                task = {
                    'task_id': row[6],
                    'title': row[7],
                    'description': row[8],
                    'verification_type': row[9],
                    'is_completed': row[10],
                    'is_verified': row[11],
                    'verification_data': row[12],
                    'order': row[13]
                }
                concepts[concept_id]['tasks'].append(task)
        
        # Convert to list and sort by order
        concepts_list = list(concepts.values())
        concepts_list.sort(key=lambda x: x['order'])
        
        return {
            "success": True,
            "project_id": project_id,
            "concepts": concepts_list
        }
        
    except Exception as e:
        print(f"❌ Error getting Day 0 concepts for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Day 0 concepts: {str(e)}")

def _calculate_current_streak(days: List[Dict[str, Any]]) -> int:
    """Calculate current consecutive completion streak"""
    streak = 0
    for day in sorted(days, key=lambda x: x['day_number']):
        if day['is_completed']:
            streak += 1
        else:
            break
    return streak 