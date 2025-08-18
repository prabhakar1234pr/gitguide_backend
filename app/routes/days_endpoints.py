"""
Days endpoints for GitGuide
API endpoints for managing 14-day learning progression
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any, Optional
import json

from app.database_config import get_db
from app.database_models import Project, Day
from app.routes.auth.auth_utilities import extract_user_id_from_token
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
        # Extract user ID from token for authentication
        user_id = extract_user_id_from_token(authorization)
        
        print(f"✅ Marking Day {day_number} as completed for project {project_id} by user {user_id}")
        
        # Validate day number
        if day_number < 0 or day_number > 14:
            raise HTTPException(status_code=400, detail="Day number must be between 0 and 14")
        
        # Verify project ownership
        project_result = await db.execute(
            select(Project).filter(
                Project.project_id == project_id,
                Project.user_id == user_id
            )
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Mark day as completed
        success = await mark_day_completed(db, project_id, day_number)
        
        if not success:
            # Get more detailed error information
            from sqlalchemy import text
            if day_number == 0:
                # Check Day 0 verification status
                result = await db.execute(text("""
                    SELECT COUNT(*) as total_tasks, 
                           COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks
                    FROM tasks t
                    JOIN concepts c ON t.concept_id = c.concept_id
                    JOIN days d ON c.day_id = d.day_id
                    WHERE d.project_id = :project_id AND d.day_number = :day_number
                    AND t.verification_type IS NOT NULL
                """), {'project_id': project_id, 'day_number': day_number})
                
                task_counts = result.fetchone()
                total_tasks = task_counts[0] if task_counts else 0
                verified_tasks = task_counts[1] if task_counts else 0
                
                error_detail = f"Cannot mark Day {day_number} as completed: Only {verified_tasks}/{total_tasks} verification tasks completed"
            else:
                # Check regular day completion status
                result = await db.execute(text("""
                    SELECT COUNT(*) as total_tasks, 
                           COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks
                    FROM tasks t
                    WHERE t.project_id = :project_id
                    AND EXISTS (
                        SELECT 1 FROM concepts c 
                        JOIN days d ON c.day_id = d.day_id 
                        WHERE c.concept_id = t.concept_id 
                        AND d.day_number = :day_number
                    )
                """), {'project_id': project_id, 'day_number': day_number})
                
                task_counts = result.fetchone()
                total_tasks = task_counts[0] if task_counts else 0
                completed_tasks = task_counts[1] if task_counts else 0
                
                error_detail = f"Cannot mark Day {day_number} as completed: Only {completed_tasks}/{total_tasks} tasks completed"
                
            print(f"❌ {error_detail}")
            raise HTTPException(status_code=400, detail=error_detail)
        
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
        
        from sqlalchemy import text
        # Unlock the day
        await db.execute(text("""
            UPDATE days 
            SET is_unlocked = TRUE 
            WHERE project_id = :project_id AND day_number = :day_number
        """), {'project_id': project_id, 'day_number': day_number})

        # Unlock all concepts for the day
        await db.execute(text("""
            UPDATE concepts c
            SET is_unlocked = TRUE
            FROM days d
            WHERE c.day_id = d.day_id AND d.project_id = :project_id AND d.day_number = :day_number
        """), {'project_id': project_id, 'day_number': day_number})

        # Unlock all subtopics for those concepts
        await db.execute(text("""
            UPDATE subtopics s
            SET is_unlocked = TRUE
            WHERE s.concept_id IN (
                SELECT c.concept_id FROM concepts c
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
            )
        """), {'project_id': project_id, 'day_number': day_number})

        # Ensure only the first task per subtopic starts unlocked; others locked until progression
        await db.execute(text(
            """
            WITH subtopic_first_tasks AS (
                SELECT DISTINCT ON (t.subtopic_id) t.task_id
                FROM tasks t
                JOIN subtopics s ON s.subtopic_id = t.subtopic_id
                JOIN concepts c ON c.concept_id = s.concept_id
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
                ORDER BY t.subtopic_id, t."order"
            )
            UPDATE tasks AS all_tasks
            SET is_unlocked = CASE
                WHEN all_tasks.task_id IN (SELECT task_id FROM subtopic_first_tasks) THEN TRUE
                ELSE FALSE
            END
            WHERE all_tasks.subtopic_id IN (
                SELECT s.subtopic_id FROM subtopics s
                JOIN concepts c ON c.concept_id = s.concept_id
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
            );
            """
        ), {'project_id': project_id, 'day_number': day_number})

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

@router.get("/projects/{project_id}/days/0/debug")
async def debug_day0_status_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Debug endpoint to check Day 0 status and task verification"""
    try:
        from sqlalchemy import text
        
        print(f"🔍 Debug: Checking Day 0 status for project {project_id}")
        
        # Get Day 0 basic info
        result = await db.execute(text("""
            SELECT day_id, is_unlocked, is_completed, is_verified, requires_verification
            FROM days 
            WHERE project_id = :project_id AND day_number = 0
        """), {'project_id': project_id})
        
        day0_info = result.fetchone()
        if not day0_info:
            return {
                "success": False,
                "error": "Day 0 not found for this project"
            }
        
        # Get Day 0 tasks and their verification status
        result = await db.execute(text("""
            SELECT 
                t.task_id,
                t.title,
                t.verification_type,
                t.is_verified,
                t.is_completed,
                t.verification_data
            FROM tasks t
            JOIN concepts c ON t.concept_id = c.concept_id
            JOIN days d ON c.day_id = d.day_id
            WHERE d.project_id = :project_id AND d.day_number = 0
            ORDER BY t.order
        """), {'project_id': project_id})
        
        tasks = result.fetchall()
        
        # Get Day 1 status
        result = await db.execute(text("""
            SELECT day_id, is_unlocked, is_completed
            FROM days 
            WHERE project_id = :project_id AND day_number = 1
        """), {'project_id': project_id})
        
        day1_info = result.fetchone()
        
        # Format response
        task_details = []
        for task in tasks:
            task_details.append({
                "task_id": task[0],
                "title": task[1],
                "verification_type": task[2],
                "is_verified": task[3],
                "is_completed": task[4],
                "has_verification_data": bool(task[5])
            })
        
        return {
            "success": True,
            "project_id": project_id,
            "day0": {
                "day_id": day0_info[0],
                "is_unlocked": day0_info[1],
                "is_completed": day0_info[2],
                "is_verified": day0_info[3],
                "requires_verification": day0_info[4]
            },
            "day0_tasks": task_details,
            "day1": {
                "day_id": day1_info[0] if day1_info else None,
                "is_unlocked": day1_info[1] if day1_info else False,
                "is_completed": day1_info[2] if day1_info else False
            } if day1_info else None,
            "summary": {
                "total_day0_tasks": len(tasks),
                "verified_tasks": len([t for t in task_details if t["is_verified"]]),
                "all_tasks_verified": len(tasks) > 0 and all(t["is_verified"] for t in task_details),
                "day1_accessible": day1_info[1] if day1_info else False
            }
        }
        
    except Exception as e:
        print(f"❌ Error in Day 0 debug endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

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

@router.get("/projects/{project_id}/test/day-progression")
async def test_day_progression_endpoint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Test endpoint to check day progression status"""
    try:
        user_id = extract_user_id_from_token(authorization)
        
        # Verify project ownership
        project_result = await db.execute(
            select(Project).filter(
                Project.project_id == project_id,
                Project.user_id == user_id
            )
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found or access denied")
        
        # Get all days status
        days_result = await db.execute(text("""
            SELECT day_number, is_unlocked, is_completed, is_verified
            FROM days 
            WHERE project_id = :project_id
            ORDER BY day_number
        """), {'project_id': project_id})
        
        days = days_result.fetchall()
        
        # Get task completion by day
        tasks_result = await db.execute(text("""
            SELECT 
                d.day_number,
                COUNT(t.task_id) as total_tasks,
                COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks
            FROM days d
            LEFT JOIN concepts c ON d.day_id = c.day_id
            LEFT JOIN tasks t ON (c.concept_id = t.concept_id)
            WHERE d.project_id = :project_id
            GROUP BY d.day_number
            ORDER BY d.day_number
        """), {'project_id': project_id})
        
        task_stats = {row[0]: {"total": row[1], "completed": row[2], "verified": row[3]} for row in tasks_result.fetchall()}
        
        # Format response
        day_status = []
        for day in days:
            day_num = day[0]
            stats = task_stats.get(day_num, {"total": 0, "completed": 0, "verified": 0})
            
            day_status.append({
                "day_number": day_num,
                "is_unlocked": day[1],
                "is_completed": day[2],
                "is_verified": day[3] if len(day) > 3 else None,
                "tasks": stats,
                "can_be_marked_complete": (
                    stats["verified"] == stats["total"] if day_num == 0 
                    else stats["completed"] == stats["total"]
                ) and stats["total"] > 0
            })
        
        return {
            "success": True,
            "project_id": project_id,
            "day_progression": day_status
        }
        
    except Exception as e:
        print(f"❌ Error in test day progression endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

def _calculate_current_streak(days: List[Dict[str, Any]]) -> int:
    """Calculate current consecutive completion streak"""
    streak = 0
    for day in sorted(days, key=lambda x: x['day_number']):
        if day['is_completed']:
            streak += 1
        else:
            break
    return streak 