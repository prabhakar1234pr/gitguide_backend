from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.database_models import Project, Concept, Subtopic, Task, Day
from app.database_config import SessionLocal
from app.routes.auth.auth_utilities import extract_user_id_from_token, get_user_details_from_clerk
from app.routes.shared.logging_and_paths import get_logger
from app.routes.shared.database_utilities import get_db_session, verify_project_ownership

logger = get_logger(__name__)

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    repo_url: str
    skill_level: str
    domain: str


@router.post("/projects", 
    summary="Create New Project",
    description="Create a new learning project from a GitHub repository URL",
    response_description="Project creation confirmation with project ID"
)
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
            # Check if project already exists for this user and repo URL
            existing_project_result = await session.execute(
                select(Project).filter(
                    Project.user_id == user_id,
                    Project.repo_url == data.repo_url
                )
            )
            existing_project = existing_project_result.scalar_one_or_none()
            
            if existing_project:
                print(f"⚠️ Project already exists with ID: {existing_project.project_id}")
                return {
                    "message": "Project already exists for this repository",
                    "project_id": existing_project.project_id,
                    "user_id": existing_project.user_id,
                    "existing": True
                }
            
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
                "user_id": new_project.user_id,
                "existing": False
            }
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")

@router.get("/projects",
    summary="Get User Projects",
    description="Retrieve all projects belonging to the authenticated user",
    response_description="List of user's projects with metadata"
)
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
                        "user_id": p.user_id,
                        "project_overview": p.project_overview,
                        "repo_name": p.repo_name,
                        "tech_stack": p.tech_stack,
                        "is_processed": p.is_processed
                    }
                    for p in projects
                ]
            }
            
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get projects: {str(e)}")

@router.get("/projects/{project_id}",
    summary="Get Project Details", 
    description="Retrieve detailed information about a specific project",
    response_description="Complete project data including AI-generated content"
)
async def get_project_by_id(project_id: int, authorization: str = Header(None)):
    """Get a specific project by ID for the authenticated user"""
    logger.info(f"📋 Fetching project {project_id}")
    user_id = extract_user_id_from_token(authorization)
    logger.info(f"👤 User {user_id} requesting project {project_id}")
    
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(Project).filter(
                    Project.project_id == project_id,
                    Project.user_id == user_id  # Ensure user can only access their own projects
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                logger.warning(f"❌ Project {project_id} not found for user {user_id}")
                raise HTTPException(status_code=404, detail="Project not found")
            
            project_data = {
                "project_id": project.project_id,
                "repo_url": project.repo_url,
                "skill_level": project.skill_level,
                "domain": project.domain,
                "user_id": project.user_id,
                "project_overview": project.project_overview,
                "repo_name": project.repo_name,
                "tech_stack": project.tech_stack,
                "is_processed": project.is_processed
            }
            
            logger.info(f"✅ Project {project_id} data: overview={bool(project.project_overview)}, processed={project.is_processed}")
            return project_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Database error for project {project_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")

@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, authorization: str = Header(None)):
    """Delete a specific project by ID for the authenticated user"""
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            from sqlalchemy import select
            result = await session.execute(
                select(Project).filter(
                    Project.project_id == project_id,
                    Project.user_id == user_id  # Ensure user can only delete their own projects
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Delete the project (tasks will be cascade deleted due to relationship)
            await session.delete(project)
            await session.commit()
            
            return {"message": "Project deleted successfully", "project_id": project_id}
            
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            print(f"❌ Database error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

@router.get("/projects/{project_id}/concepts",
    summary="Get Learning Path",
    description="Retrieve the AI-generated learning path with concepts, subtopics, and tasks. Optionally scope by day.",
    response_description="Hierarchical learning structure for the project"
)
async def get_project_concepts(
    project_id: int,
    authorization: str = Header(None),
    active_day: int | None = None,
    include_past: bool = False
):
    """Get all concepts for a specific project"""
    logger.info(f"🎯 Fetching concepts for project {project_id}")
    logger.info(f"🔑 Authorization header present: {bool(authorization)}")
    
    try:
        user_id = extract_user_id_from_token(authorization)
        logger.info(f"👤 Extracted user_id: {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to extract user_id: {e}")
        raise
    
    async with SessionLocal() as session:
        try:
            # First, check if project exists at all
            all_projects_result = await session.execute(select(Project))
            all_projects = all_projects_result.scalars().all()
            logger.info(f"📋 Total projects in database: {len(all_projects)}")
            for p in all_projects:
                logger.info(f"  Project {p.project_id}: user={p.user_id}, processed={p.is_processed}")
            
            # Verify project belongs to user
            project_result = await session.execute(
                select(Project).filter(
                    Project.project_id == project_id,
                    Project.user_id == user_id
                )
            )
            project = project_result.scalar_one_or_none()
            
            if not project:
                logger.warning(f"❌ Project {project_id} not found for user {user_id}")
                # Check if project exists for different user
                any_project_result = await session.execute(
                    select(Project).filter(Project.project_id == project_id)
                )
                any_project = any_project_result.scalar_one_or_none()
                if any_project:
                    logger.warning(f"❌ Project {project_id} exists but belongs to user {any_project.user_id}, not {user_id}")
                else:
                    logger.warning(f"❌ Project {project_id} does not exist in database")
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Safety: ensure Day 1 stays locked until all Day 0 verification tasks are verified
            try:
                from sqlalchemy import text
                counts_res = await session.execute(text(
                    """
                    SELECT COUNT(*) as total_tasks,
                           COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks
                    FROM tasks t
                    JOIN concepts c ON t.concept_id = c.concept_id
                    JOIN days d ON c.day_id = d.day_id
                    WHERE d.project_id = :project_id AND d.day_number = 0
                          AND t.verification_type IS NOT NULL
                    """
                ), {"project_id": project_id})
                total_tasks, verified_tasks = counts_res.fetchone() or (0, 0)
                if (total_tasks or 0) > 0 and (verified_tasks or 0) < (total_tasks or 0):
                    # Re-lock Day 1 defensively if Day 0 not fully verified
                    await session.execute(text(
                        "UPDATE days SET is_unlocked = FALSE WHERE project_id = :project_id AND day_number = 1"
                    ), {"project_id": project_id})
                    await session.commit()
            except Exception as _:
                pass

            # If requesting a specific active day and it's unlocked, defensively ensure its concepts/subtopics are unlocked
            if active_day is not None:
                try:
                    from sqlalchemy import text
                    # Check day state
                    day_state_res = await session.execute(text(
                        "SELECT is_unlocked FROM days WHERE project_id = :project_id AND day_number = :day_number"
                    ), {"project_id": project_id, "day_number": active_day})
                    day_state_row = day_state_res.fetchone()
                    if day_state_row and bool(day_state_row[0]):
                        # Unlock concepts/subtopics for this day idempotently
                        await session.execute(text(
                            """
                            UPDATE concepts c
                            SET is_unlocked = TRUE
                            FROM days d
                            WHERE c.day_id = d.day_id AND d.project_id = :project_id AND d.day_number = :day_number
                            """
                        ), {"project_id": project_id, "day_number": active_day})

                        await session.execute(text(
                            """
                            UPDATE subtopics s
                            SET is_unlocked = TRUE
                            WHERE s.concept_id IN (
                                SELECT c.concept_id FROM concepts c
                                JOIN days d ON d.day_id = c.day_id
                                WHERE d.project_id = :project_id AND d.day_number = :day_number
                            )
                            """
                        ), {"project_id": project_id, "day_number": active_day})

                        # First task per subtopic unlocked; others locked
                        await session.execute(text(
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
                        ), {"project_id": project_id, "day_number": active_day})
                        await session.commit()
                except Exception as _:
                    pass

            # Get concepts for this project (optionally scoped by day)
            concepts_query = select(Concept).filter(Concept.project_id == project_id)
            concepts_query = concepts_query.order_by(Concept.order)
            concepts_result = await session.execute(concepts_query)
            concepts = concepts_result.scalars().all()
            
            concepts_data = []
            for concept in concepts:
                # Get the day information for this concept
                day_result = await session.execute(
                    select(Day).filter(Day.day_id == concept.day_id)
                )
                day_obj = day_result.scalar_one_or_none()
                if not day_obj:
                    continue
                # Only return concepts for unlocked days (hide future days' content)
                # If a specific active day is requested, filter strictly to that day (and optionally include past days)
                day_number = day_obj.day_number
                if active_day is not None:
                    if include_past:
                        if day_number > active_day:
                            continue
                    else:
                        if day_number != active_day:
                            continue
                    # Never leak future locked days even if requested
                    if not day_obj.is_unlocked:
                        continue
                else:
                    # Default behavior: only include unlocked days
                    if not day_obj.is_unlocked:
                        continue
                
                # Get subtopics for this concept
                subtopics_result = await session.execute(
                    select(Subtopic).filter(Subtopic.concept_id == concept.concept_id).order_by(Subtopic.order)
                )
                subtopics = subtopics_result.scalars().all()
                
                # Get tasks directly attached to this concept (for Day 0)
                direct_tasks_result = await session.execute(
                    select(Task).filter(Task.concept_id == concept.concept_id, Task.subtopic_id.is_(None)).order_by(Task.order)
                )
                direct_tasks = direct_tasks_result.scalars().all()
                
                subtopics_data = []
                
                # Process regular subtopics (Days 1-14)
                for subtopic in subtopics:
                    # Get tasks for this subtopic
                    tasks_result = await session.execute(
                        select(Task).filter(Task.subtopic_id == subtopic.subtopic_id).order_by(Task.order)
                    )
                    tasks = tasks_result.scalars().all()
                    
                    tasks_data = [
                        {
                            "id": task.task_external_id,
                            "task_id": task.task_id,  # Add DB integer ID
                            "name": task.title,
                            "description": task.description,
                            "difficulty": task.difficulty,
                            "files_to_study": json.loads(task.files_to_study) if task.files_to_study else [],
                            "isUnlocked": task.is_unlocked,
                            "status": task.status.value,
                            "is_completed": task.is_completed,  # Add completion status
                            "is_verified": task.is_verified  # Add verification status
                        }
                        for task in tasks
                    ]
                    
                    subtopics_data.append({
                        "id": subtopic.subtopic_external_id,
                        "name": subtopic.name,
                        "description": subtopic.description,
                        "isUnlocked": subtopic.is_unlocked,
                        "tasks": tasks_data
                    })
                
                # If there are direct tasks (Day 0), create a virtual subtopic for them
                if direct_tasks:
                    direct_tasks_data = [
                        {
                            "id": task.task_external_id,
                            "task_id": task.task_id,  # Add DB integer ID
                            "name": task.title,
                            "description": task.description,
                            "difficulty": "Beginner",  # Day 0 tasks are always beginner level
                            "files_to_study": [],
                            "isUnlocked": task.is_unlocked,
                            "status": task.status.value,
                            "verification_type": task.verification_type,
                            "is_verified": task.is_verified,
                            "is_completed": task.is_completed  # Add completion status for Day 0 tasks
                        }
                        for task in direct_tasks
                    ]
                    
                    # Create a virtual subtopic for Day 0 tasks
                    subtopics_data.insert(0, {
                        "id": f"day0-tasks-{concept.concept_external_id}",
                        "name": "Setup Tasks",
                        "description": "Complete these verification tasks to unlock the next day",
                        "isUnlocked": True,  # Day 0 tasks are always unlocked
                        "tasks": direct_tasks_data
                    })
                
                concepts_data.append({
                    "id": concept.concept_external_id,
                    "name": concept.title,
                    "description": concept.description,
                    "isUnlocked": concept.is_unlocked,
                    "day_number": day_number,  # Add day number
                    "subTopics": subtopics_data
                })
            
            logger.info(f"✅ Found {len(concepts_data)} concepts for project {project_id}")
            for i, concept in enumerate(concepts_data):
                logger.info(f"  📚 Concept {i+1}: '{concept['name']}' ({len(concept['subTopics'])} subtopics)")
            
            return {
                "project_id": project_id,
                "concepts": concepts_data
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Database error fetching concepts for project {project_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get concepts: {str(e)}")

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