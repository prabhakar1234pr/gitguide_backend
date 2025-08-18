"""
AI Agent Regeneration endpoints for GitGuide
Handles all regeneration operations for learning path components
"""

from fastapi import APIRouter, HTTPException, Header
from sqlalchemy import text
import json

from app.routes.auth.auth_utilities import extract_user_id_from_token
from app.database_config import SessionLocal
from .agent_utilities import (
    RegenerateRequest,
    RegenerateConceptRequest,
    RegenerateSubtopicRequest,
    RegenerateTaskRequest,
    check_agent_availability,
    get_agent_instance,
    get_project_for_regeneration,
    get_repository_context_for_regeneration,
    call_llm_for_regeneration,
    clear_learning_path_for_project,
    update_project_overview,
    save_agent_content_to_db,
    handle_regeneration_error
)

router = APIRouter()


@router.post("/agent/regenerate/project-overview",
    summary="Regenerate Project Overview",
    description="Regenerate the project overview with custom user prompt"
)
async def regenerate_project_overview(
    request: RegenerateRequest,
    authorization: str = Header(None)
):
    """Regenerate project overview with custom prompt"""
    try:
        user_id = extract_user_id_from_token(authorization)
        check_agent_availability()
        
        # Get project details
        project = await get_project_for_regeneration(request.project_id, user_id)
        
        # Get repository context and agent
        agent = get_agent_instance()
        repo_context = await get_repository_context_for_regeneration(project, agent)

        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_project_overview_prompt
        prompt = create_regenerate_project_overview_prompt(
            repo_context=repo_context,
            current_overview=project.project_overview or "",
            user_prompt=request.user_prompt,
            skill_level=project.skill_level,
            domain=project.domain
        )

        # Call LLM for regeneration
        result = await call_llm_for_regeneration(agent, prompt)
        new_overview = result["project_overview"]

        # Update database
        await update_project_overview(request.project_id, new_overview)

        return {
            "status": "success",
            "message": "Project overview regenerated successfully",
            "project_overview": new_overview
        }

    except Exception as e:
        handle_regeneration_error("regenerating project overview", e)


@router.post("/agent/regenerate/whole-path",
    summary="Regenerate Entire Learning Path",
    description="Regenerate the entire learning path with custom user prompt"
)
async def regenerate_whole_path(
    request: RegenerateRequest,
    authorization: str = Header(None)
):
    """Regenerate entire learning path with custom prompt"""
    try:
        user_id = extract_user_id_from_token(authorization)
        check_agent_availability()

        # Get project details and current concepts
        project = await get_project_for_regeneration(request.project_id, user_id)

        # Get current learning path aligned with actual schema
        async with SessionLocal() as session:
            result = await session.execute(
                text(
                    """
                    SELECT 
                        c.concept_external_id as concept_external_id,
                        c.title as concept_title,
                        c.description as concept_description,
                        COALESCE(
                            (
                                SELECT json_agg(
                                    json_build_object(
                                        'id', s.subtopic_external_id,
                                        'name', s.name,
                                        'description', s.description,
                                        'tasks', COALESCE(
                                            (
                                                SELECT json_agg(
                                                    json_build_object(
                                                        'id', t.task_external_id,
                                                        'name', t.title,
                                                        'description', t.description,
                                                        'files_to_study', COALESCE(NULLIF(t.files_to_study,''),'[]')::json,
                                                        'difficulty', t.difficulty
                                                    )
                                                    ORDER BY t."order"
                                                )
                                                FROM tasks t
                                                WHERE t.subtopic_id = s.subtopic_id
                                            ), '[]'::json)
                                    )
                                    ORDER BY s."order"
                                )
                                FROM subtopics s
                                WHERE s.concept_id = c.concept_id
                            ), '[]'::json
                        ) as subtopics
                    FROM concepts c
                    WHERE c.project_id = :project_id
                    ORDER BY c."order"
                    """
                ),
                {"project_id": request.project_id},
            )
            rows = result.fetchall()

        current_concepts = [
            {
                "id": row.concept_external_id,
                "name": row.concept_title,
                "description": row.concept_description,
                "subtopics": json.loads(row.subtopics) if row.subtopics else [],
            }
            for row in rows
        ]

        # Get repository context
        agent = get_agent_instance()
        repo_context = await get_repository_context_for_regeneration(project, agent)

        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_whole_path_prompt
        prompt = create_regenerate_whole_path_prompt(
            repo_context=repo_context,
            current_concepts=current_concepts,
            user_prompt=request.user_prompt,
            skill_level=project.skill_level,
            domain=project.domain
        )

        # Call LLM for regeneration
        result = await call_llm_for_regeneration(agent, prompt)
        new_concepts = result["concepts"]

        # Clear existing learning path and save new one
        await clear_learning_path_for_project(request.project_id)
        await save_agent_content_to_db(request.project_id, {"concepts": new_concepts}, {})

        return {
            "status": "success",
            "message": "Entire learning path regenerated successfully",
            "concepts": new_concepts
        }

    except Exception as e:
        handle_regeneration_error("regenerating learning path", e)


@router.post("/agent/regenerate/concept",
    summary="Regenerate Specific Concept",
    description="Regenerate a specific concept with custom user prompt"
)
async def regenerate_concept(
    request: RegenerateConceptRequest,
    authorization: str = Header(None)
):
    """Regenerate specific concept with custom prompt"""
    try:
        user_id = extract_user_id_from_token(authorization)
        check_agent_availability()

        # Get project and concept details
        project = await get_project_for_regeneration(request.project_id, user_id)
        
        async with SessionLocal() as session:
            # Get current concept
            result = await session.execute(
                text("SELECT * FROM concepts WHERE concept_external_id = :concept_external_id AND project_id = :project_id"),
                {"concept_external_id": request.concept_id, "project_id": request.project_id}
            )
            concept = result.fetchone()

            if not concept:
                raise HTTPException(status_code=404, detail="Concept not found")

            # Convert concept to dict for processing
            concept_dict = {
                "id": concept.concept_external_id,
                "name": concept.title,
                "description": concept.description,
            }

            project_dict = {
                "repo_url": project.repo_url,
                "skill_level": project.skill_level,
                "domain": project.domain
            }

            # Get repository context
            agent = get_agent_instance()
            repo_context = await get_repository_context_for_regeneration(project, agent)

            # Create regeneration prompt
            from prompts.learning_path_prompts import create_regenerate_concept_prompt
            prompt = create_regenerate_concept_prompt(
                repo_context=repo_context,
                concept_to_regenerate=concept_dict,
                user_prompt=request.user_prompt,
                skill_level=project.skill_level,
                domain=project.domain
            )

            # Call LLM for regeneration
            result = await call_llm_for_regeneration(agent, prompt)
            new_concept = result["concept"]

        # Update database
        async with SessionLocal() as session:
            # Delete existing subtopics and tasks for this concept
            await session.execute(
                text("DELETE FROM tasks WHERE subtopic_id IN (SELECT subtopic_id FROM subtopics WHERE concept_id = :concept_id)"),
                {"concept_id": concept.concept_id},
            )
            await session.execute(
                text("DELETE FROM subtopics WHERE concept_id = :concept_id"),
                {"concept_id": concept.concept_id},
            )

            # Update concept (use title column)
            await session.execute(
                text("UPDATE concepts SET title = :title, description = :description WHERE concept_external_id = :concept_external_id"),
                {"title": new_concept["name"], "description": new_concept["description"], "concept_external_id": request.concept_id},
            )

            # Save new subtopics and tasks
            for subtopic_index, subtopic in enumerate(new_concept["subtopics"]):
                subtopic_result = await session.execute(
                    text(
                        """
                        INSERT INTO subtopics (concept_id, subtopic_external_id, name, description, "order", is_unlocked)
                        VALUES (:concept_id, :subtopic_external_id, :name, :description, :order, :is_unlocked)
                        RETURNING subtopic_id
                        """
                    ),
                    {
                        "concept_id": concept.concept_id,
                        "subtopic_external_id": subtopic["id"],
                        "name": subtopic["name"],
                        "description": subtopic["description"],
                        "order": subtopic_index,
                        "is_unlocked": subtopic.get("isUnlocked", False),
                    },
                )
                subtopic_id = subtopic_result.fetchone()[0]

                for task_index, task in enumerate(subtopic["tasks"]):
                    await session.execute(
                        text(
                            """
                            INSERT INTO tasks (project_id, subtopic_id, task_external_id, title, description, files_to_study, difficulty, "order", is_unlocked, status)
                            VALUES (:project_id, :subtopic_id, :task_external_id, :title, :description, :files_to_study, :difficulty, :order, :is_unlocked, :status)
                            """
                        ),
                        {
                            "project_id": concept.project_id,
                            "subtopic_id": subtopic_id,
                            "task_external_id": task["id"],
                            "title": task["name"],
                            "description": task["description"],
                            "files_to_study": json.dumps(task.get("files_to_study", [])),
                            "difficulty": task.get("difficulty", "medium"),
                            "order": task_index,
                            "is_unlocked": task.get("isUnlocked", False),
                            "status": "not_started",
                        },
                    )

            await session.commit()

        return {
            "status": "success",
            "message": "Concept regenerated successfully",
            "concept": new_concept
        }

    except Exception as e:
        handle_regeneration_error("regenerating concept", e)


@router.post("/agent/regenerate/subtopic",
    summary="Regenerate Specific Subtopic",
    description="Regenerate a specific subtopic with custom user prompt"
)
async def regenerate_subtopic(
    request: RegenerateSubtopicRequest,
    authorization: str = Header(None)
):
    """Regenerate specific subtopic with custom prompt"""
    try:
        user_id = extract_user_id_from_token(authorization)
        check_agent_availability()

        # Get project details
        project = await get_project_for_regeneration(request.project_id, user_id)
        
        async with SessionLocal() as session:
            # Get parent concept
            result = await session.execute(
                text("SELECT * FROM concepts WHERE concept_external_id = :concept_external_id AND project_id = :project_id"),
                {"concept_external_id": request.concept_id, "project_id": request.project_id}
            )
            concept = result.fetchone()

            if not concept:
                raise HTTPException(status_code=404, detail="Concept not found")

            # Get current subtopic
            result = await session.execute(
                text("SELECT * FROM subtopics WHERE subtopic_external_id = :subtopic_external_id AND concept_id = :concept_id"),
                {"subtopic_external_id": request.subtopic_id, "concept_id": concept.concept_id}
            )
            subtopic = result.fetchone()

            if not subtopic:
                raise HTTPException(status_code=404, detail="Subtopic not found")

            # Get all tasks for this subtopic
            result = await session.execute(
                text("SELECT * FROM tasks WHERE subtopic_id = :subtopic_id ORDER BY \"order\""),
                {"subtopic_id": subtopic.subtopic_id},
            )
            tasks = result.fetchall()

        current_subtopic = {
            "id": subtopic.subtopic_external_id,
            "name": subtopic.name,
            "description": subtopic.description,
            "tasks": [
                {
                    "id": t.task_external_id,
                    "name": t.title,
                    "description": t.description,
                    "files_to_study": json.loads(t.files_to_study) if t.files_to_study else [],
                    "difficulty": t.difficulty,
                }
                for t in tasks
            ],
        }

        parent_concept = {
            "id": concept.concept_external_id,
            "name": concept.title,
            "description": concept.description
        }

        # Get repository context
        agent = get_agent_instance()
        repo_context = await get_repository_context_for_regeneration(project, agent)

        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_subtopic_prompt
        prompt = create_regenerate_subtopic_prompt(
            repo_context=repo_context,
            subtopic_to_regenerate=current_subtopic,
            parent_concept=parent_concept,
            user_prompt=request.user_prompt,
            skill_level=project.skill_level,
            domain=project.domain
        )

        # Call LLM for regeneration
        result = await call_llm_for_regeneration(agent, prompt)
        new_subtopic = result["subtopic"]

        # Update database
        async with SessionLocal() as session:
            # Delete existing tasks for this subtopic
            await session.execute(
                text("DELETE FROM tasks WHERE subtopic_id = :subtopic_id"), 
                {"subtopic_id": subtopic.subtopic_id}
            )

            # Update subtopic
            await session.execute(
                text("UPDATE subtopics SET name = :name, description = :description WHERE subtopic_external_id = :subtopic_external_id"),
                {"name": new_subtopic["name"], "description": new_subtopic["description"], "subtopic_external_id": request.subtopic_id}
            )

            # Save new tasks
            for task_index, task in enumerate(new_subtopic["tasks"]):
                await session.execute(
                    text("""
                        INSERT INTO tasks (project_id, subtopic_id, task_external_id, title, description, files_to_study, difficulty, "order", is_unlocked, status)
                        VALUES (:project_id, :subtopic_id, :task_external_id, :title, :description, :files_to_study, :difficulty, :order, :is_unlocked, :status)
                    """),
                    {
                        "project_id": concept.project_id,
                        "subtopic_id": subtopic.subtopic_id,
                        "task_external_id": task["id"],
                        "title": task["name"],
                        "description": task["description"],
                        "files_to_study": json.dumps(task.get("files_to_study", [])),
                        "difficulty": task.get("difficulty", "medium"),
                        "order": task_index,
                        "is_unlocked": task.get("isUnlocked", False),
                        "status": "not_started"
                    }
                )

            await session.commit()

        return {
            "status": "success",
            "message": "Subtopic regenerated successfully",
            "subtopic": new_subtopic
        }

    except Exception as e:
        handle_regeneration_error("regenerating subtopic", e)


@router.post("/agent/regenerate/task",
    summary="Regenerate Specific Task",
    description="Regenerate a specific task with custom user prompt"
)
async def regenerate_task(
    request: RegenerateTaskRequest,
    authorization: str = Header(None)
):
    """Regenerate specific task with custom prompt"""
    try:
        user_id = extract_user_id_from_token(authorization)
        check_agent_availability()

        # Get project details
        project = await get_project_for_regeneration(request.project_id, user_id)
        
        async with SessionLocal() as session:
            # Get parent concept
            result = await session.execute(
                text("SELECT * FROM concepts WHERE concept_external_id = :concept_external_id AND project_id = :project_id"),
                {"concept_external_id": request.concept_id, "project_id": request.project_id}
            )
            concept = result.fetchone()

            if not concept:
                raise HTTPException(status_code=404, detail="Concept not found")

            # Get parent subtopic
            result = await session.execute(
                text("SELECT * FROM subtopics WHERE subtopic_external_id = :subtopic_external_id AND concept_id = :concept_id"),
                {"subtopic_external_id": request.subtopic_id, "concept_id": concept.concept_id}
            )
            subtopic = result.fetchone()

            if not subtopic:
                raise HTTPException(status_code=404, detail="Subtopic not found")

            # Get current task
            result = await session.execute(
                text("SELECT * FROM tasks WHERE task_external_id = :task_external_id AND subtopic_id = :subtopic_id"),
                {"task_external_id": request.task_id, "subtopic_id": subtopic.subtopic_id}
            )
            task = result.fetchone()

            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

        current_task = {
            "id": task.task_external_id,
            "name": task.title,
            "description": task.description,
            "files_to_study": json.loads(task.files_to_study) if task.files_to_study else [],
            "difficulty": task.difficulty
        }

        parent_concept = {
            "id": concept.concept_external_id,
            "name": concept.title,
            "description": concept.description
        }

        parent_subtopic = {
            "id": subtopic.subtopic_external_id,
            "name": subtopic.name,
            "description": subtopic.description
        }

        # Get repository context
        agent = get_agent_instance()
        repo_context = await get_repository_context_for_regeneration(project, agent)

        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_task_prompt
        prompt = create_regenerate_task_prompt(
            repo_context=repo_context,
            task_to_regenerate=current_task,
            parent_subtopic=parent_subtopic,
            parent_concept=parent_concept,
            user_prompt=request.user_prompt,
            skill_level=project.skill_level,
            domain=project.domain
        )

        # Call LLM for regeneration
        result = await call_llm_for_regeneration(agent, prompt)
        new_task = result["task"]

        # Update task in database
        async with SessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE tasks 
                    SET title = :title, description = :description, files_to_study = :files_to_study, difficulty = :difficulty
                    WHERE task_external_id = :task_external_id
                """),
                {
                    "title": new_task["name"],
                    "description": new_task["description"],
                    "files_to_study": json.dumps(new_task.get("files_to_study", [])),
                    "difficulty": new_task.get("difficulty", "medium"),
                    "task_external_id": request.task_id
                }
            )
            await session.commit()

        return {
            "status": "success",
            "message": "Task regenerated successfully",
            "task": new_task
        }

    except Exception as e:
        handle_regeneration_error("regenerating task", e) 