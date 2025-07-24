from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.database_models import Task, Project, TaskStatus
from app.database_config import SessionLocal
from app.routes.auth.auth_utilities import extract_user_id_from_token

router = APIRouter()

class TaskCreateRequest(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    order: int

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    order: Optional[int] = None

class TaskResponse(BaseModel):
    task_id: int
    project_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    order: int
    
    class Config:
        from_attributes = True

@router.post("/tasks", 
    response_model=TaskResponse,
    summary="Create New Task",
    description="Create a new learning task for a specific project",
    response_description="Created task details"
)
async def create_task(
    data: TaskCreateRequest,
    authorization: str = Header(None)
):
    """Create a new task for a project"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            # Verify project belongs to user
            project_result = await session.execute(
                select(Project).filter(
                    Project.project_id == data.project_id,
                    Project.user_id == user_id
                )
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found or access denied")
            
            # Create new task
            new_task = Task(
                project_id=data.project_id,
                title=data.title,
                description=data.description,
                order=data.order,
                status=TaskStatus.not_started
            )
            
            session.add(new_task)
            await session.commit()
            await session.refresh(new_task)
            
            print(f"✅ Task created with ID: {new_task.task_id}")
            return new_task
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating task: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/projects/{project_id}/tasks", 
    response_model=List[TaskResponse],
    summary="Get Project Tasks",
    description="Retrieve all learning tasks for a specific project, ordered by sequence",
    response_description="List of tasks with progress status"
)
async def get_project_tasks(
    project_id: int,
    authorization: str = Header(None)
):
    """Get all tasks for a specific project"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            # Verify project belongs to user
            project_result = await session.execute(
                select(Project).filter(
                    Project.project_id == project_id,
                    Project.user_id == user_id
                )
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found or access denied")
            
            # Get tasks ordered by order field
            tasks_result = await session.execute(
                select(Task).filter(Task.project_id == project_id).order_by(Task.order)
            )
            tasks = tasks_result.scalars().all()
            
            return tasks
            
        except Exception as e:
            print(f"❌ Error getting tasks: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdateRequest,
    authorization: str = Header(None)
):
    """Update a task"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            # Get task and verify ownership through project
            task_result = await session.execute(
                select(Task).join(Project).filter(
                    Task.task_id == task_id,
                    Project.user_id == user_id
                )
            )
            task = task_result.scalar_one_or_none()
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found or access denied")
            
            # Update fields
            if data.title is not None:
                task.title = data.title
            if data.description is not None:
                task.description = data.description
            if data.status is not None:
                task.status = data.status
            if data.order is not None:
                task.order = data.order
            
            await session.commit()
            await session.refresh(task)
            
            print(f"✅ Task {task_id} updated")
            return task
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error updating task: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    authorization: str = Header(None)
):
    """Delete a task"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            # Get task and verify ownership through project
            task_result = await session.execute(
                select(Task).join(Project).filter(
                    Task.task_id == task_id,
                    Project.user_id == user_id
                )
            )
            task = task_result.scalar_one_or_none()
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found or access denied")
            
            await session.delete(task)
            await session.commit()
            
            print(f"✅ Task {task_id} deleted")
            return {"message": "Task deleted successfully"}
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error deleting task: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}") 