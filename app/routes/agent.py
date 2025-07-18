from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import json
import asyncio
import sys
import os
from typing import Optional

from app.models import Project, Concept, Subtopic, Task
from app.db import SessionLocal
from sqlalchemy import text
import json

# Add agent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../agent'))

try:
    from agent.main import GitGuideAgent
except ImportError:
    print("⚠️ GitGuide Agent not available - agent endpoints will be disabled")
    GitGuideAgent = None

router = APIRouter()

class AgentProcessRequest(BaseModel):
    project_id: int

class AgentStatusResponse(BaseModel):
    status: str
    message: str
    details: Optional[dict] = None

# Add regeneration request models
class RegenerateRequest(BaseModel):
    project_id: int
    user_prompt: str

class RegenerateConceptRequest(BaseModel):
    project_id: int
    concept_id: str
    user_prompt: str

class RegenerateSubtopicRequest(BaseModel):
    project_id: int
    concept_id: str
    subtopic_id: str
    user_prompt: str

class RegenerateTaskRequest(BaseModel):
    project_id: int
    concept_id: str
    subtopic_id: str
    task_id: str
    user_prompt: str

def extract_user_id_from_token(authorization: str = None) -> str:
    """Extract Clerk user ID from JWT token (shared utility)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization token required")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID found")
            
        return user_id
        
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

async def save_agent_content_to_db(project_id: int, learning_path: dict, repo_info: dict):
    """Save agent-generated content directly to database"""
    
    async with SessionLocal() as session:
        try:
            # Update project with overview and metadata
            result = await session.execute(
                select(Project).filter(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            # Update project with agent-generated content
            project.project_overview = learning_path['project_overview']
            project.repo_name = repo_info.get('name', '')
            project.tech_stack = json.dumps(repo_info.get('tech_stack', {}))
            project.is_processed = True
            
            # Save concepts
            for concept_data in learning_path['concepts']:
                concept = Concept(
                    project_id=project_id,
                    concept_external_id=concept_data['id'],
                    name=concept_data['name'],
                    description=concept_data.get('description', ''),
                    order=int(concept_data['id'].split('-')[1]),
                    is_unlocked=concept_data.get('isUnlocked', False)
                )
                session.add(concept)
                await session.flush()  # Get the concept_id
                
                # Save subtopics
                for subtopic_data in concept_data['subtopics']:
                    subtopic = Subtopic(
                        concept_id=concept.concept_id,
                        subtopic_external_id=subtopic_data['id'],
                        name=subtopic_data['name'],
                        description=subtopic_data.get('description', ''),
                        order=int(subtopic_data['id'].split('-')[2]),
                        is_unlocked=subtopic_data.get('isUnlocked', False)
                    )
                    session.add(subtopic)
                    await session.flush()  # Get the subtopic_id
                    
                    # Save tasks
                    for task_data in subtopic_data['tasks']:
                        task = Task(
                            project_id=project_id,
                            subtopic_id=subtopic.subtopic_id,
                            task_external_id=task_data['id'],
                            title=task_data['name'],
                            description=task_data.get('description', ''),
                            order=int(task_data['id'].split('-')[3]),
                            difficulty=task_data.get('difficulty', 'medium'),
                            files_to_study=json.dumps(task_data.get('files_to_study', [])),
                            is_unlocked=task_data.get('isUnlocked', False)
                        )
                        session.add(task)
            
            await session.commit()
            return {"success": True, "message": "Learning content saved successfully"}
            
        except Exception as e:
            await session.rollback()
            raise Exception(f"Database save failed: {str(e)}")

async def process_project_background(project_id: int, user_id: str):
    """Background task to process project with agent"""
    
    if not GitGuideAgent:
        print("❌ GitGuide Agent not available")
        return
    
    try:
        print(f"🚀 Starting background processing for project {project_id}")
        
        # Get project details
        async with SessionLocal() as session:
            result = await session.execute(
                select(Project).filter(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                print(f"❌ Project {project_id} not found")
                return
        
        # Initialize agent and process
        agent = GitGuideAgent()
        result = await agent.process_new_project(
            project_id=project_id,
            repo_url=project.repo_url,
            skill_level=project.skill_level,
            domain=project.domain,
            user_id=user_id
        )
        
        if result['success']:
            print(f"✅ Agent processing completed for project {project_id}")
            
            # Save the generated content to database 
            # (For now, we'll use the simulated content structure)
            # In the full implementation, this would save the actual agent results
            
        else:
            print(f"❌ Agent processing failed for project {project_id}: {result['error']}")
            
    except Exception as e:
        print(f"❌ Background processing failed for project {project_id}: {str(e)}")

@router.post("/agent/process",
    summary="Generate Learning Path",
    description="Trigger AI agent to analyze GitHub repository and generate personalized learning path",
    response_description="Processing confirmation with status"
)
async def trigger_agent_processing(
    request: AgentProcessRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """Trigger agent processing for a project"""
    
    if not GitGuideAgent:
        raise HTTPException(
            status_code=503, 
            detail="GitGuide Agent service is not available"
        )
    
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            # Verify project exists and belongs to user
            result = await session.execute(
                select(Project).filter(
                    Project.project_id == request.project_id,
                    Project.user_id == user_id
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            if project.is_processed:
                return {
                    "message": "Project already processed",
                    "project_id": request.project_id,
                    "status": "already_processed"
                }
            
            # Add background task to process the project
            background_tasks.add_task(
                process_project_background, 
                request.project_id, 
                user_id
            )
            
            return {
                "message": "Agent processing started",
                "project_id": request.project_id,
                "status": "processing"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error triggering agent: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to trigger agent: {str(e)}")

@router.get("/agent/status/{project_id}",
    summary="Check Processing Status", 
    description="Check the current processing status of AI learning path generation",
    response_description="Processing status and completion details"
)
async def get_agent_status(
    project_id: int,
    authorization: str = Header(None)
) -> AgentStatusResponse:
    """Get the processing status of a project"""
    
    user_id = extract_user_id_from_token(authorization)
    
    async with SessionLocal() as session:
        try:
            result = await session.execute(
                select(Project).filter(
                    Project.project_id == project_id,
                    Project.user_id == user_id
                )
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Check if concepts exist (indicating processing is complete)
            concepts_result = await session.execute(
                select(Concept).filter(Concept.project_id == project_id)
            )
            concepts = concepts_result.scalars().all()
            
            if project.is_processed and len(concepts) > 0:
                status = "completed"
                message = f"Learning path generated with {len(concepts)} concepts"
            elif project.is_processed:
                status = "completed_basic"
                message = "Project processed, but no structured learning path available"
            else:
                status = "not_processed"
                message = "Project not yet processed by agent"
            
            return AgentStatusResponse(
                status=status,
                message=message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Error getting agent status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/agent/health",
    summary="Agent Health Check",
    description="Check if AI agent service is available and properly configured",
    response_description="Agent service status and configuration details"
)
async def agent_health_check():
    """Check if the agent service is available"""
    
    if not GitGuideAgent:
        return {
            "status": "unavailable",
            "message": "GitGuide Agent is not installed or configured",
            "agent_available": False
        }
    
    # Test agent initialization
    try:
        agent = GitGuideAgent()
        return {
            "status": "available",
            "message": "GitGuide Agent is ready",
            "agent_available": True,
            "github_token": bool(agent.github_token),
            "groq_api_key": bool(agent.groq_api_key)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Agent initialization failed: {str(e)}",
            "agent_available": False
        } 

# ==================== REGENERATION ENDPOINTS ====================

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
        if not GitGuideAgent:
            raise HTTPException(
                status_code=503,
                detail="GitGuide Agent service is not available"
            )

        # Get project details
        project = db.execute(
            text("SELECT * FROM projects WHERE id = :id AND user_id = :user_id"),
            {"id": request.project_id, "user_id": current_user["id"]}
        ).fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get repository context (from agent)
        agent = GitGuideAgent()
        repo_analysis = await agent.repository_analyzer.analyze(project.repo_url)
        repo_context = agent.learning_path_generator.prepare_repository_context(repo_analysis)

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
        response = await agent.learning_path_generator.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        # Parse response
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            new_overview = result["project_overview"]
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

        # Update database
        db.execute(
            text("UPDATE projects SET project_overview = :overview WHERE id = :id"),
            {"overview": new_overview, "id": request.project_id}
        )
        db.commit()

        return {
            "status": "success",
            "message": "Project overview regenerated successfully",
            "project_overview": new_overview
        }

    except Exception as e:
        print(f"❌ Error regenerating project overview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate project overview: {str(e)}")

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
        if not GitGuideAgent:
            raise HTTPException(
                status_code=503,
                detail="GitGuide Agent service is not available"
            )

        # Get project details
        project = db.execute(
            text("SELECT * FROM projects WHERE id = :id AND user_id = :user_id"),
            {"id": request.project_id, "user_id": current_user["id"]}
        ).fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get current concepts
        concepts = db.execute(
            text("""
                SELECT c.*, 
                       COALESCE(s.subtopics, '[]'::json) as subtopics
                FROM concepts c
                LEFT JOIN (
                    SELECT concept_id,
                           json_agg(
                               json_build_object(
                                   'id', s.id,
                                   'name', s.name,
                                   'description', s.description,
                                   'tasks', COALESCE(t.tasks, '[]'::json)
                               ) ORDER BY s.order_index
                           ) as subtopics
                    FROM subtopics s
                    LEFT JOIN (
                        SELECT subtopic_id,
                               json_agg(
                                   json_build_object(
                                       'id', t.id,
                                       'name', t.name,
                                       'description', t.description,
                                       'files_to_study', t.files_to_study,
                                       'difficulty', t.difficulty
                                   ) ORDER BY t.order_index
                               ) as tasks
                        FROM tasks t
                        GROUP BY subtopic_id
                    ) t ON s.id = t.subtopic_id
                    GROUP BY concept_id
                ) s ON c.id = s.concept_id
                WHERE c.project_id = :project_id
                ORDER BY c.order_index
            """),
            {"project_id": request.project_id}
        ).fetchall()

        current_concepts = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "subtopics": json.loads(c.subtopics) if c.subtopics else []
            }
            for c in concepts
        ]

        # Get repository context
        agent = GitGuideAgent()
        repo_analysis = await agent.repository_analyzer.analyze(project.repo_url)
        repo_context = agent.learning_path_generator.prepare_repository_context(repo_analysis)

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
        response = await agent.learning_path_generator.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        # Parse response
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            new_concepts = result["concepts"]
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

        # Clear existing learning path
        db.execute(text("DELETE FROM tasks WHERE subtopic_id IN (SELECT id FROM subtopics WHERE concept_id IN (SELECT id FROM concepts WHERE project_id = :project_id))"), {"project_id": request.project_id})
        db.execute(text("DELETE FROM subtopics WHERE concept_id IN (SELECT id FROM concepts WHERE project_id = :project_id)"), {"project_id": request.project_id})
        db.execute(text("DELETE FROM concepts WHERE project_id = :project_id"), {"project_id": request.project_id})

        # Save new learning path
        await save_agent_content_to_db(request.project_id, {"concepts": new_concepts}, {})

        return {
            "status": "success",
            "message": "Entire learning path regenerated successfully",
            "concepts": new_concepts
        }

    except Exception as e:
        print(f"❌ Error regenerating learning path: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate learning path: {str(e)}")

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
        if not GitGuideAgent:
            raise HTTPException(
                status_code=503,
                detail="GitGuide Agent service is not available"
            )

        # Get project and concept details
        project = db.execute(
            text("SELECT * FROM projects WHERE id = :id AND user_id = :user_id"),
            {"id": request.project_id, "user_id": current_user["id"]}
        ).fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get current concept
        concept = db.execute(
            text("SELECT * FROM concepts WHERE id = :id AND project_id = :project_id"),
            {"id": request.concept_id, "project_id": request.project_id}
        ).fetchone()

        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")

        # Get current subtopics and tasks
        subtopics = db.execute(
            text("""
                SELECT s.*, 
                       COALESCE(t.tasks, '[]'::json) as tasks
                FROM subtopics s
                LEFT JOIN (
                    SELECT subtopic_id,
                           json_agg(
                               json_build_object(
                                   'id', t.id,
                                   'name', t.name,
                                   'description', t.description,
                                   'files_to_study', t.files_to_study,
                                   'difficulty', t.difficulty
                               ) ORDER BY t.order_index
                           ) as tasks
                    FROM tasks t
                    GROUP BY subtopic_id
                ) t ON s.id = t.subtopic_id
                WHERE s.concept_id = :concept_id
                ORDER BY s.order_index
            """),
            {"concept_id": request.concept_id}
        ).fetchall()

        current_concept = {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description,
            "subtopics": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "tasks": json.loads(s.tasks) if s.tasks else []
                }
                for s in subtopics
            ]
        }

        # Get repository context
        agent = GitGuideAgent()
        repo_analysis = await agent.repository_analyzer.analyze(project.repo_url)
        repo_context = agent.learning_path_generator.prepare_repository_context(repo_analysis)

        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_concept_prompt
        prompt = create_regenerate_concept_prompt(
            repo_context=repo_context,
            concept_to_regenerate=current_concept,
            user_prompt=request.user_prompt,
            skill_level=project.skill_level,
            domain=project.domain
        )

        # Call LLM for regeneration
        response = await agent.learning_path_generator.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        # Parse response
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            new_concept = result["concept"]
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

        # Delete existing subtopics and tasks for this concept
        db.execute(text("DELETE FROM tasks WHERE subtopic_id IN (SELECT id FROM subtopics WHERE concept_id = :concept_id)"), {"concept_id": request.concept_id})
        db.execute(text("DELETE FROM subtopics WHERE concept_id = :concept_id"), {"concept_id": request.concept_id})

        # Update concept
        db.execute(
            text("UPDATE concepts SET name = :name, description = :description WHERE id = :id"),
            {"name": new_concept["name"], "description": new_concept["description"], "id": request.concept_id}
        )

        # Save new subtopics and tasks
        for subtopic_index, subtopic in enumerate(new_concept["subtopics"]):
            subtopic_result = db.execute(
                text("""
                    INSERT INTO subtopics (concept_id, name, description, order_index)
                    VALUES (:concept_id, :name, :description, :order_index)
                    RETURNING id
                """),
                {
                    "concept_id": request.concept_id,
                    "name": subtopic["name"],
                    "description": subtopic["description"],
                    "order_index": subtopic_index
                }
            )
            subtopic_id = subtopic_result.fetchone()[0]

            for task_index, task in enumerate(subtopic["tasks"]):
                db.execute(
                    text("""
                        INSERT INTO tasks (subtopic_id, name, description, files_to_study, difficulty, order_index)
                        VALUES (:subtopic_id, :name, :description, :files_to_study, :difficulty, :order_index)
                    """),
                    {
                        "subtopic_id": subtopic_id,
                        "name": task["name"],
                        "description": task["description"],
                        "files_to_study": json.dumps(task.get("files_to_study", [])),
                        "difficulty": task.get("difficulty", "medium"),
                        "order_index": task_index
                    }
                )

        db.commit()

        return {
            "status": "success",
            "message": "Concept regenerated successfully",
            "concept": new_concept
        }

    except Exception as e:
        print(f"❌ Error regenerating concept: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate concept: {str(e)}")

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
        if not GitGuideAgent:
            raise HTTPException(
                status_code=503,
                detail="GitGuide Agent service is not available"
            )

        # Get project, concept, and subtopic details
        project = db.execute(
            text("SELECT * FROM projects WHERE id = :id AND user_id = :user_id"),
            {"id": request.project_id, "user_id": current_user["id"]}
        ).fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get parent concept
        concept = db.execute(
            text("SELECT * FROM concepts WHERE id = :id AND project_id = :project_id"),
            {"id": request.concept_id, "project_id": request.project_id}
        ).fetchone()

        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")

        # Get current subtopic and tasks
        subtopic = db.execute(
            text("SELECT * FROM subtopics WHERE id = :id AND concept_id = :concept_id"),
            {"id": request.subtopic_id, "concept_id": request.concept_id}
        ).fetchone()

        if not subtopic:
            raise HTTPException(status_code=404, detail="Subtopic not found")

        tasks = db.execute(
            text("SELECT * FROM tasks WHERE subtopic_id = :subtopic_id ORDER BY order_index"),
            {"subtopic_id": request.subtopic_id}
        ).fetchall()

        current_subtopic = {
            "id": subtopic.id,
            "name": subtopic.name,
            "description": subtopic.description,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "files_to_study": json.loads(t.files_to_study) if t.files_to_study else [],
                    "difficulty": t.difficulty
                }
                for t in tasks
            ]
        }

        parent_concept = {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description
        }

        # Get repository context
        agent = GitGuideAgent()
        repo_analysis = await agent.repository_analyzer.analyze(project.repo_url)
        repo_context = agent.learning_path_generator.prepare_repository_context(repo_analysis)

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
        response = await agent.learning_path_generator.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        # Parse response
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            new_subtopic = result["subtopic"]
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

        # Delete existing tasks for this subtopic
        db.execute(text("DELETE FROM tasks WHERE subtopic_id = :subtopic_id"), {"subtopic_id": request.subtopic_id})

        # Update subtopic
        db.execute(
            text("UPDATE subtopics SET name = :name, description = :description WHERE id = :id"),
            {"name": new_subtopic["name"], "description": new_subtopic["description"], "id": request.subtopic_id}
        )

        # Save new tasks
        for task_index, task in enumerate(new_subtopic["tasks"]):
            db.execute(
                text("""
                    INSERT INTO tasks (subtopic_id, name, description, files_to_study, difficulty, order_index)
                    VALUES (:subtopic_id, :name, :description, :files_to_study, :difficulty, :order_index)
                """),
                {
                    "subtopic_id": request.subtopic_id,
                    "name": task["name"],
                    "description": task["description"],
                    "files_to_study": json.dumps(task.get("files_to_study", [])),
                    "difficulty": task.get("difficulty", "medium"),
                    "order_index": task_index
                }
            )

        db.commit()

        return {
            "status": "success",
            "message": "Subtopic regenerated successfully",
            "subtopic": new_subtopic
        }

    except Exception as e:
        print(f"❌ Error regenerating subtopic: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate subtopic: {str(e)}")

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
        if not GitGuideAgent:
            raise HTTPException(
                status_code=503,
                detail="GitGuide Agent service is not available"
            )

        # Get project, concept, subtopic, and task details
        project = db.execute(
            text("SELECT * FROM projects WHERE id = :id AND user_id = :user_id"),
            {"id": request.project_id, "user_id": current_user["id"]}
        ).fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get parent concept
        concept = db.execute(
            text("SELECT * FROM concepts WHERE id = :id AND project_id = :project_id"),
            {"id": request.concept_id, "project_id": request.project_id}
        ).fetchone()

        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")

        # Get parent subtopic
        subtopic = db.execute(
            text("SELECT * FROM subtopics WHERE id = :id AND concept_id = :concept_id"),
            {"id": request.subtopic_id, "concept_id": request.concept_id}
        ).fetchone()

        if not subtopic:
            raise HTTPException(status_code=404, detail="Subtopic not found")

        # Get current task
        task = db.execute(
            text("SELECT * FROM tasks WHERE id = :id AND subtopic_id = :subtopic_id"),
            {"id": request.task_id, "subtopic_id": request.subtopic_id}
        ).fetchone()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        current_task = {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "files_to_study": json.loads(task.files_to_study) if task.files_to_study else [],
            "difficulty": task.difficulty
        }

        parent_concept = {
            "id": concept.id,
            "name": concept.name,
            "description": concept.description
        }

        parent_subtopic = {
            "id": subtopic.id,
            "name": subtopic.name,
            "description": subtopic.description
        }

        # Get repository context
        agent = GitGuideAgent()
        repo_analysis = await agent.repository_analyzer.analyze(project.repo_url)
        repo_context = agent.learning_path_generator.prepare_repository_context(repo_analysis)

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
        response = await agent.learning_path_generator.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.7
        )

        # Parse response
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            new_task = result["task"]
        except (json.JSONDecodeError, KeyError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

        # Update task
        db.execute(
            text("""
                UPDATE tasks 
                SET name = :name, description = :description, files_to_study = :files_to_study, difficulty = :difficulty
                WHERE id = :id
            """),
            {
                "name": new_task["name"],
                "description": new_task["description"],
                "files_to_study": json.dumps(new_task.get("files_to_study", [])),
                "difficulty": new_task.get("difficulty", "medium"),
                "id": request.task_id
            }
        )

        db.commit()

        return {
            "status": "success",
            "message": "Task regenerated successfully",
            "task": new_task
        }

    except Exception as e:
        print(f"❌ Error regenerating task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate task: {str(e)}") 