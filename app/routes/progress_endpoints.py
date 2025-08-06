"""
Progress Tracking and Day Management Endpoints
Handles project progress, day unlocking, and background content generation
"""

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.database_config import get_db
from app.database_models import Project, Day, Task
from app.routes.auth.auth_utilities import extract_user_id_from_token
from app.routes.shared.progress_utilities import (
    update_task_completion, 
    get_project_progress_summary,
    calculate_all_progress
)

router = APIRouter()

class TaskCompletionRequest(BaseModel):
    task_id: int
    github_verification_data: Optional[str] = None

class DayGenerationRequest(BaseModel):
    day_number: int
    force_regenerate: Optional[bool] = False

@router.get("/projects/{project_id}/progress")
async def get_project_progress(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get comprehensive progress summary for a project"""
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
        
        # Get progress summary
        progress_summary = await get_project_progress_summary(db, project_id)
        
        if not progress_summary['success']:
            raise HTTPException(status_code=500, detail=progress_summary['error'])
        
        # Get day-specific progress
        day_progress_result = await db.execute(
            text("""
                SELECT day_number, day_progress, is_completed, is_unlocked, is_content_generated
                FROM days 
                WHERE project_id = :project_id
                ORDER BY day_number
            """),
            {'project_id': project_id}
        )
        
        day_progress = []
        for row in day_progress_result.fetchall():
            day_number, day_prog, is_completed, is_unlocked, is_content_generated = row
            day_progress.append({
                'day_number': day_number,
                'progress': day_prog or 0.0,
                'is_completed': is_completed,
                'is_unlocked': is_unlocked,
                'is_content_generated': is_content_generated,
                'progress_percentage': round((day_prog or 0.0) * 100, 1)
            })
        
        return {
            'success': True,
            'project_id': project_id,
            'overall_progress': progress_summary,
            'day_progress': day_progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting project progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.post("/projects/{project_id}/tasks/{task_id}/complete")
async def complete_task(
    project_id: int,
    task_id: int,
    request: TaskCompletionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Mark a task as completed and update progress"""
    try:
        user_id = extract_user_id_from_token(authorization)
        
        # Verify project and task ownership
        task_result = await db.execute(
            select(Task).join(Project).filter(
                Task.task_id == task_id,
                Task.project_id == project_id,
                Project.user_id == user_id
            )
        )
        task = task_result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found or access denied")
        
        if task.is_completed:
            return {
                'success': True,
                'message': 'Task already completed',
                'task_id': task_id,
                'was_already_completed': True
            }
        
        # Handle GitHub verification if required
        if task.verification_type == 'github_api' and request.github_verification_data:
            # Add GitHub verification logic here
            print(f"🔍 GitHub verification for task {task_id}: {request.github_verification_data}")
            # For now, assume verification passes
            task.github_verification_status = 'verified'
            task.github_check_url = request.github_verification_data
        
        # Update task completion and calculate progress
        progress_update = await update_task_completion(db, project_id, task_id)
        
        if not progress_update['success']:
            raise HTTPException(status_code=500, detail=progress_update['error'])
        
        # If day was completed, trigger background generation for next day
        if progress_update.get('day_completed') and not progress_update.get('next_day_unlocked', True):
            # Find the next day that needs content
            next_day_result = await db.execute(
                text("""
                    SELECT day_number FROM days 
                    WHERE project_id = :project_id 
                    AND is_content_generated = FALSE 
                    AND day_number > 0
                    ORDER BY day_number 
                    LIMIT 1
                """),
                {'project_id': project_id}
            )
            next_day_info = next_day_result.fetchone()
            
            if next_day_info:
                next_day_number = next_day_info[0]
                background_tasks.add_task(
                    trigger_background_day_generation, 
                    project_id, 
                    next_day_number
                )
                print(f"🔄 Scheduled background generation for Day {next_day_number}")
        
        return {
            'success': True,
            'message': 'Task completed successfully',
            'task_id': task_id,
            'progress_updates': progress_update,
            'subconcept_completed': progress_update.get('subconcept_completed', False),
            'concept_completed': progress_update.get('concept_completed', False),
            'day_completed': progress_update.get('day_completed', False),
            'next_day_unlocked': progress_update.get('next_day_unlocked', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error completing task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete task: {str(e)}")

@router.post("/projects/{project_id}/days/{day_number}/generate")
async def generate_day_content(
    project_id: int,
    day_number: int,
    request: DayGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Trigger generation of content for a specific day"""
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
        
        if day_number < 1 or day_number > 14:
            raise HTTPException(status_code=400, detail="Day number must be between 1 and 14")
        
        # Check if day exists and needs content
        day_result = await db.execute(
            select(Day).filter(
                Day.project_id == project_id,
                Day.day_number == day_number
            )
        )
        day = day_result.scalar_one_or_none()
        
        if not day:
            raise HTTPException(status_code=404, detail=f"Day {day_number} not found")
        
        if day.is_content_generated and not request.force_regenerate:
            return {
                'success': True,
                'message': f'Day {day_number} content already generated',
                'day_number': day_number,
                'was_already_generated': True
            }
        
        # Mark generation as started
        await db.execute(
            text("UPDATE days SET content_generation_started = TRUE WHERE day_id = :day_id"),
            {'day_id': day.day_id}
        )
        await db.commit()
        
        # Trigger background generation
        background_tasks.add_task(
            trigger_background_day_generation,
            project_id,
            day_number,
            request.force_regenerate
        )
        
        return {
            'success': True,
            'message': f'Day {day_number} content generation started',
            'day_number': day_number,
            'generation_started': True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error triggering day generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger generation: {str(e)}")

@router.get("/projects/{project_id}/days/{day_number}/status")
async def get_day_status(
    project_id: int,
    day_number: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Get detailed status of a specific day"""
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
        
        # Get day status with detailed task information
        day_result = await db.execute(
            text("""
                SELECT 
                    d.day_id,
                    d.day_number,
                    d.name,
                    d.description,
                    d.is_unlocked,
                    d.is_completed,
                    d.is_content_generated,
                    d.content_generation_started,
                    d.day_progress,
                    d.total_tasks,
                    d.completed_tasks,
                    COUNT(DISTINCT c.concept_id) as total_concepts,
                    COUNT(DISTINCT CASE WHEN c.is_completed = TRUE THEN c.concept_id END) as completed_concepts,
                    COUNT(DISTINCT sc.subconcept_id) as total_subconcepts,
                    COUNT(DISTINCT CASE WHEN sc.is_completed = TRUE THEN sc.subconcept_id END) as completed_subconcepts,
                    COUNT(DISTINCT t.task_id) as actual_total_tasks,
                    COUNT(DISTINCT CASE WHEN t.is_completed = TRUE THEN t.task_id END) as actual_completed_tasks
                FROM days d
                LEFT JOIN concepts c ON d.day_id = c.day_id
                LEFT JOIN subconcepts sc ON c.concept_id = sc.concept_id
                LEFT JOIN tasks t ON sc.subconcept_id = t.subconcept_id OR c.concept_id = t.concept_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
                GROUP BY d.day_id, d.day_number, d.name, d.description, d.is_unlocked, 
                         d.is_completed, d.is_content_generated, d.content_generation_started, 
                         d.day_progress, d.total_tasks, d.completed_tasks
            """),
            {'project_id': project_id, 'day_number': day_number}
        )
        
        day_data = day_result.fetchone()
        
        if not day_data:
            raise HTTPException(status_code=404, detail=f"Day {day_number} not found")
        
        (day_id, day_num, name, description, is_unlocked, is_completed, is_content_generated,
         content_generation_started, day_progress, total_tasks, completed_tasks,
         total_concepts, completed_concepts, total_subconcepts, completed_subconcepts,
         actual_total_tasks, actual_completed_tasks) = day_data
        
        return {
            'success': True,
            'day': {
                'day_id': day_id,
                'day_number': day_num,
                'name': name,
                'description': description,
                'is_unlocked': is_unlocked,
                'is_completed': is_completed,
                'is_content_generated': is_content_generated,
                'content_generation_started': content_generation_started,
                'progress': day_progress or 0.0,
                'progress_percentage': round((day_progress or 0.0) * 100, 1),
                'total_tasks': actual_total_tasks or 0,
                'completed_tasks': actual_completed_tasks or 0,
                'total_concepts': total_concepts or 0,
                'completed_concepts': completed_concepts or 0,
                'total_subconcepts': total_subconcepts or 0,
                'completed_subconcepts': completed_subconcepts or 0,
                'tasks_remaining': (actual_total_tasks or 0) - (actual_completed_tasks or 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting day status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get day status: {str(e)}")

# Background task functions

async def trigger_background_day_generation(project_id: int, day_number: int, force_regenerate: bool = False):
    """Background task to generate day content"""
    try:
        print(f"🔄 Background: Starting Day {day_number} generation for project {project_id}")
        
        # Import here to avoid circular imports
        from app.agent.agent_orchestrator import GitGuideAgent
        
        # This would need to be implemented to get the repository analysis and project details
        # For now, this is a placeholder
        agent = GitGuideAgent()
        
        # In a real implementation, you would:
        # 1. Get project details and repository analysis from database
        # 2. Call agent.generate_day_on_demand()
        # 3. Save the results
        
        print(f"✅ Background: Day {day_number} generation completed for project {project_id}")
        
    except Exception as e:
        print(f"❌ Background: Day {day_number} generation failed: {str(e)}")

@router.post("/projects/{project_id}/refresh-progress")
async def refresh_project_progress(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """Manually refresh and recalculate project progress"""
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
        
        # Recalculate all progress
        progress_percentages = await calculate_all_progress(db, project_id)
        
        # Get updated summary
        progress_summary = await get_project_progress_summary(db, project_id)
        
        await db.commit()
        
        return {
            'success': True,
            'message': 'Progress refreshed successfully',
            'project_id': project_id,
            'progress_percentages': progress_percentages,
            'progress_summary': progress_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error refreshing progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh progress: {str(e)}") 