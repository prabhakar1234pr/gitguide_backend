"""
Progress Tracking Utilities
Handles day progress, project progress, and automatic unlocking logic
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, update
from typing import Dict, Any, Optional

async def update_task_completion(session: AsyncSession, project_id: int, task_id: int) -> Dict[str, Any]:
    """
    Update task completion and trigger progress recalculation
    
    Args:
        session: Database session
        project_id: Project ID
        task_id: Task ID that was completed
        
    Returns:
        Dict with progress updates and unlock status
    """
    try:
        # Mark task as completed
        await session.execute(
            text("UPDATE tasks SET is_completed = TRUE, status = 'completed' WHERE task_id = :task_id"),
            {'task_id': task_id}
        )
        
        # Get task details to find subconcept and concept
        task_result = await session.execute(
            text("""
                SELECT t.subconcept_id, t.concept_id, sc.concept_id as sc_concept_id, c.day_id
                FROM tasks t 
                LEFT JOIN subconcepts sc ON t.subconcept_id = sc.subconcept_id
                LEFT JOIN concepts c ON COALESCE(sc.concept_id, t.concept_id) = c.concept_id
                WHERE t.task_id = :task_id
            """),
            {'task_id': task_id}
        )
        task_info = task_result.fetchone()
        
        if not task_info:
            return {'success': False, 'error': 'Task not found'}
        
        subconcept_id = task_info[0]
        concept_id = task_info[1] or task_info[2]
        day_id = task_info[3]
        
        progress_updates = {
            'subconcept_completed': False,
            'concept_completed': False,
            'day_completed': False,
            'next_day_unlocked': False,
            'progress_percentages': {}
        }
        
        # Check if subconcept is completed (if applicable)
        if subconcept_id:
            subconcept_completed = await check_subconcept_completion(session, subconcept_id)
            if subconcept_completed:
                await mark_subconcept_completed(session, subconcept_id)
                progress_updates['subconcept_completed'] = True
                
                # Check if concept is completed
                concept_completed = await check_concept_completion(session, concept_id)
                if concept_completed:
                    await mark_concept_completed(session, concept_id)
                    progress_updates['concept_completed'] = True
        
        # Check if day is completed
        if day_id:
            day_completed = await check_day_completion(session, day_id)
            if day_completed:
                await mark_day_completed(session, day_id)
                progress_updates['day_completed'] = True
                
                # Try to unlock next day
                next_day_unlocked = await unlock_next_day(session, project_id, day_id)
                progress_updates['next_day_unlocked'] = next_day_unlocked
        
        # Update progress percentages
        progress_updates['progress_percentages'] = await calculate_all_progress(session, project_id)
        
        await session.commit()
        
        return {
            'success': True,
            'task_id': task_id,
            **progress_updates
        }
        
    except Exception as e:
        await session.rollback()
        print(f"❌ Error updating task completion: {str(e)}")
        return {'success': False, 'error': str(e)}

async def check_subconcept_completion(session: AsyncSession, subconcept_id: int) -> bool:
    """Check if all tasks in a subconcept are completed"""
    try:
        result = await session.execute(
            text("""
                SELECT COUNT(*) as total_tasks, 
                       COUNT(CASE WHEN is_completed = TRUE THEN 1 END) as completed_tasks
                FROM tasks 
                WHERE subconcept_id = :subconcept_id
            """),
            {'subconcept_id': subconcept_id}
        )
        
        counts = result.fetchone()
        total_tasks = counts[0] if counts else 0
        completed_tasks = counts[1] if counts else 0
        
        return total_tasks > 0 and completed_tasks == total_tasks
        
    except Exception as e:
        print(f"❌ Error checking subconcept completion: {str(e)}")
        return False

async def check_concept_completion(session: AsyncSession, concept_id: int) -> bool:
    """Check if all subconcepts in a concept are completed"""
    try:
        result = await session.execute(
            text("""
                SELECT COUNT(*) as total_subconcepts, 
                       COUNT(CASE WHEN is_completed = TRUE THEN 1 END) as completed_subconcepts
                FROM subconcepts 
                WHERE concept_id = :concept_id
            """),
            {'concept_id': concept_id}
        )
        
        counts = result.fetchone()
        total_subconcepts = counts[0] if counts else 0
        completed_subconcepts = counts[1] if counts else 0
        
        return total_subconcepts > 0 and completed_subconcepts == total_subconcepts
        
    except Exception as e:
        print(f"❌ Error checking concept completion: {str(e)}")
        return False

async def check_day_completion(session: AsyncSession, day_id: int) -> bool:
    """Check if all concepts in a day are completed"""
    try:
        result = await session.execute(
            text("""
                SELECT COUNT(*) as total_concepts, 
                       COUNT(CASE WHEN is_completed = TRUE THEN 1 END) as completed_concepts
                FROM concepts 
                WHERE day_id = :day_id
            """),
            {'day_id': day_id}
        )
        
        counts = result.fetchone()
        total_concepts = counts[0] if counts else 0
        completed_concepts = counts[1] if counts else 0
        
        return total_concepts > 0 and completed_concepts == total_concepts
        
    except Exception as e:
        print(f"❌ Error checking day completion: {str(e)}")
        return False

async def mark_subconcept_completed(session: AsyncSession, subconcept_id: int) -> None:
    """Mark a subconcept as completed"""
    try:
        await session.execute(
            text("UPDATE subconcepts SET is_completed = TRUE WHERE subconcept_id = :subconcept_id"),
            {'subconcept_id': subconcept_id}
        )
        print(f"✅ Subconcept {subconcept_id} marked as completed")
        
    except Exception as e:
        print(f"❌ Error marking subconcept as completed: {str(e)}")

async def mark_concept_completed(session: AsyncSession, concept_id: int) -> None:
    """Mark a concept as completed and update progress"""
    try:
        await session.execute(
            text("UPDATE concepts SET is_completed = TRUE, concept_progress = 1.0 WHERE concept_id = :concept_id"),
            {'concept_id': concept_id}
        )
        print(f"✅ Concept {concept_id} marked as completed")
        
    except Exception as e:
        print(f"❌ Error marking concept as completed: {str(e)}")

async def mark_day_completed(session: AsyncSession, day_id: int) -> None:
    """Mark a day as completed and update progress"""
    try:
        await session.execute(
            text("UPDATE days SET is_completed = TRUE, day_progress = 1.0 WHERE day_id = :day_id"),
            {'day_id': day_id}
        )
        print(f"✅ Day {day_id} marked as completed")
        
    except Exception as e:
        print(f"❌ Error marking day as completed: {str(e)}")

async def unlock_next_day(session: AsyncSession, project_id: int, current_day_id: int) -> bool:
    """Unlock the next day after completing current day"""
    try:
        # Get current day number
        day_result = await session.execute(
            text("SELECT day_number FROM days WHERE day_id = :day_id"),
            {'day_id': current_day_id}
        )
        day_info = day_result.fetchone()
        
        if not day_info:
            return False
        
        current_day_number = day_info[0]
        next_day_number = current_day_number + 1
        
        # Check if next day exists and unlock it
        next_day_result = await session.execute(
            text("""
                UPDATE days 
                SET is_unlocked = TRUE 
                WHERE project_id = :project_id AND day_number = :next_day_number
                RETURNING day_id
            """),
            {'project_id': project_id, 'next_day_number': next_day_number}
        )
        
        unlocked_day = next_day_result.fetchone()
        
        if unlocked_day:
            # Update project current day
            await session.execute(
                text("UPDATE projects SET current_day = :next_day_number WHERE project_id = :project_id"),
                {'project_id': project_id, 'next_day_number': next_day_number}
            )
            
            print(f"✅ Day {next_day_number} unlocked for project {project_id}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error unlocking next day: {str(e)}")
        return False

async def calculate_all_progress(session: AsyncSession, project_id: int) -> Dict[str, float]:
    """Calculate progress percentages for project, days, and concepts"""
    try:
        progress = {}
        
        # Project progress
        project_result = await session.execute(
            text("""
                SELECT 
                    COUNT(DISTINCT d.day_id) as total_days,
                    COUNT(DISTINCT CASE WHEN d.is_completed = TRUE THEN d.day_id END) as completed_days,
                    COUNT(DISTINCT c.concept_id) as total_concepts,
                    COUNT(DISTINCT CASE WHEN c.is_completed = TRUE THEN c.concept_id END) as completed_concepts,
                    COUNT(DISTINCT sc.subconcept_id) as total_subconcepts,
                    COUNT(DISTINCT CASE WHEN sc.is_completed = TRUE THEN sc.subconcept_id END) as completed_subconcepts,
                    COUNT(DISTINCT t.task_id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.is_completed = TRUE THEN t.task_id END) as completed_tasks
                FROM projects p
                LEFT JOIN days d ON p.project_id = d.project_id
                LEFT JOIN concepts c ON d.day_id = c.day_id
                LEFT JOIN subconcepts sc ON c.concept_id = sc.concept_id
                LEFT JOIN tasks t ON sc.subconcept_id = t.subconcept_id OR c.concept_id = t.concept_id
                WHERE p.project_id = :project_id
            """),
            {'project_id': project_id}
        )
        
        project_stats = project_result.fetchone()
        
        if project_stats:
            total_tasks = project_stats[7] or 0
            completed_tasks = project_stats[8] or 0
            
            if total_tasks > 0:
                progress['project'] = completed_tasks / total_tasks
            else:
                progress['project'] = 0.0
            
            # Update project progress in database
            await session.execute(
                text("UPDATE projects SET project_progress = :progress, completed_days = :completed_days WHERE project_id = :project_id"),
                {
                    'project_id': project_id, 
                    'progress': progress['project'],
                    'completed_days': project_stats[1] or 0
                }
            )
        
        # Day-specific progress
        day_result = await session.execute(
            text("""
                SELECT 
                    d.day_id,
                    d.day_number,
                    COUNT(DISTINCT t.task_id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.is_completed = TRUE THEN t.task_id END) as completed_tasks
                FROM days d
                LEFT JOIN concepts c ON d.day_id = c.day_id
                LEFT JOIN subconcepts sc ON c.concept_id = sc.concept_id
                LEFT JOIN tasks t ON sc.subconcept_id = t.subconcept_id OR c.concept_id = t.concept_id
                WHERE d.project_id = :project_id
                GROUP BY d.day_id, d.day_number
                ORDER BY d.day_number
            """),
            {'project_id': project_id}
        )
        
        for row in day_result.fetchall():
            day_id, day_number, total_tasks, completed_tasks = row
            day_progress = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0
            progress[f'day_{day_number}'] = day_progress
            
            # Update day progress in database
            await session.execute(
                text("UPDATE days SET day_progress = :progress, completed_tasks = :completed_tasks WHERE day_id = :day_id"),
                {'day_id': day_id, 'progress': day_progress, 'completed_tasks': completed_tasks or 0}
            )
        
        return progress
        
    except Exception as e:
        print(f"❌ Error calculating progress: {str(e)}")
        return {}

async def get_project_progress_summary(session: AsyncSession, project_id: int) -> Dict[str, Any]:
    """Get comprehensive progress summary for a project"""
    try:
        result = await session.execute(
            text("""
                SELECT 
                    p.project_progress,
                    p.current_day,
                    p.completed_days,
                    p.total_days,
                    COUNT(DISTINCT d.day_id) as actual_days,
                    COUNT(DISTINCT CASE WHEN d.is_completed = TRUE THEN d.day_id END) as actual_completed_days,
                    COUNT(DISTINCT t.task_id) as total_tasks,
                    COUNT(DISTINCT CASE WHEN t.is_completed = TRUE THEN t.task_id END) as completed_tasks
                FROM projects p
                LEFT JOIN days d ON p.project_id = d.project_id
                LEFT JOIN concepts c ON d.day_id = c.day_id
                LEFT JOIN subconcepts sc ON c.concept_id = sc.concept_id
                LEFT JOIN tasks t ON sc.subconcept_id = t.subconcept_id OR c.concept_id = t.concept_id
                WHERE p.project_id = :project_id
                GROUP BY p.project_id, p.project_progress, p.current_day, p.completed_days, p.total_days
            """),
            {'project_id': project_id}
        )
        
        data = result.fetchone()
        
        if not data:
            return {'success': False, 'error': 'Project not found'}
        
        project_progress, current_day, completed_days, total_days, actual_days, actual_completed_days, total_tasks, completed_tasks = data
        
        return {
            'success': True,
            'project_progress': project_progress or 0.0,
            'current_day': current_day or 0,
            'completed_days': actual_completed_days or 0,
            'total_days': actual_days or 0,
            'total_tasks': total_tasks or 0,
            'completed_tasks': completed_tasks or 0,
            'tasks_remaining': (total_tasks or 0) - (completed_tasks or 0),
            'progress_percentage': round((project_progress or 0.0) * 100, 1)
        }
        
    except Exception as e:
        print(f"❌ Error getting progress summary: {str(e)}")
        return {'success': False, 'error': str(e)} 