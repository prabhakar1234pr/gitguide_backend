"""
Shared database utilities for route endpoints
Eliminates redundant SessionLocal patterns and project ownership verification
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any
import logging

from app.database_models import Project
from app.database_config import SessionLocal

# Configure logging once for all shared utilities
logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Shared database session context manager"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database error: {str(e)}")
            raise


async def verify_project_ownership(project_id: int, user_id: str, session: AsyncSession) -> Project:
    """Verify project exists and belongs to user - shared utility"""
    result = await session.execute(
        select(Project).filter(
            Project.project_id == project_id,
            Project.user_id == user_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


async def get_user_projects(user_id: str, session: AsyncSession) -> list:
    """Get all projects for a user - shared utility"""
    result = await session.execute(
        select(Project).filter(Project.user_id == user_id)
    )
    return result.scalars().all()


async def get_project_by_id(project_id: int, user_id: str, session: AsyncSession) -> Optional[Project]:
    """Get project by ID with ownership check - shared utility"""
    return await verify_project_ownership(project_id, user_id, session)


# Shared error handling utilities
def handle_database_error(operation: str, error: Exception):
    """Standardized database error handling"""
    logger.error(f"❌ Database error during {operation}: {str(error)}")
    raise HTTPException(
        status_code=500, 
        detail=f"Database operation failed: {operation}"
    )


def handle_not_found_error(resource: str, resource_id: Any):
    """Standardized not found error handling"""
    logger.warning(f"❌ {resource} {resource_id} not found")
    raise HTTPException(
        status_code=404, 
        detail=f"{resource} not found"
    ) 