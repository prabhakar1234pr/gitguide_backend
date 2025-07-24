"""
Agent utilities for GitGuide
Helper functions for agent operations and database interactions
"""

import os
import sys
import logging
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Add path to import force_env_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from force_env_loader import force_load_env

# Force load correct environment variables from .env file
force_load_env()

# Add the agent directory to path
agent_dir = Path(__file__).parent.parent.parent / "agent"
sys.path.append(str(agent_dir))

# Import agent functions
from repository_analyzer import analyze_repository
from learning_path_generator import generate_learning_path
from prompts.learning_path_prompts import prepare_repository_context
from openai import AzureOpenAI

from app.database_models import Project, Concept, Subtopic, Task
from app.database_config import SessionLocal
from app.routes.shared.logging_and_paths import get_logger

logger = get_logger(__name__)

# Add agent directory to path
try:
    backend_root = Path(__file__).resolve().parent.parent.parent.parent  # Go up 4 levels to reach gitguide_backend
    agent_path = str(backend_root / "agent")  # /gitguide_backend/agent
    if agent_path not in sys.path:
        sys.path.insert(0, agent_path)
    
    logger.info("🔍 Attempting to import GitGuideAgent...")
    from agent.agent_orchestrator import GitGuideAgent
    logger.info("✅ GitGuideAgent imported successfully")
except ImportError as e:
    logger.error(f"❌ GitGuide Agent import failed: {str(e)}")
    GitGuideAgent = None
except Exception as e:
    logger.error(f"❌ Unexpected error during agent setup: {str(e)}")
    GitGuideAgent = None


# ================== PYDANTIC MODELS ==================

class AgentProcessRequest(BaseModel):
    project_id: int

class AgentStatusResponse(BaseModel):
    status: str
    message: str
    details: Optional[dict] = None

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


# ================== AGENT UTILITIES ==================

def check_agent_availability():
    """Check if GitGuide Agent is available"""
    if not GitGuideAgent:
        raise HTTPException(
            status_code=503,
            detail="GitGuide Agent service is not available"
        )

def get_agent_instance():
    """Get a GitGuideAgent instance with error handling"""
    check_agent_availability()
    try:
        return GitGuideAgent()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent initialization failed: {str(e)}"
        )


# ================== DATABASE OPERATIONS ==================

async def get_project_with_ownership_check(project_id: int, user_id: str) -> Any:
    """Get project with ownership verification"""
    async with SessionLocal() as session:
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

async def get_project_processing_status(project_id: int, user_id: str) -> Dict[str, Any]:
    """Get comprehensive project processing status"""
    async with SessionLocal() as session:
        # Get project details
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
        
        return {
            "status": status,
            "message": message,
            "project": project,
            "concepts_count": len(concepts)
        }


# ================== CONTENT SAVING ==================

async def save_agent_content_to_db(project_id: int, learning_path: Dict[str, Any], repo_info: Dict[str, Any]) -> Dict[str, Any]:
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
            project.project_overview = learning_path.get('project_overview', '')
            project.repo_name = repo_info.get('name', '')
            project.tech_stack = json.dumps(repo_info.get('tech_stack', {}))
            project.is_processed = True
            
            # Save concepts
            for concept_data in learning_path.get('concepts', []):
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
                for subtopic_data in concept_data.get('subtopics', []):
                    subtopic = Subtopic(
                        concept_id=concept.concept_id,
                        subtopic_external_id=subtopic_data['id'],
                        name=subtopic_data['name'],
                        description=subtopic_data.get('description', ''),
                        order=int(subtopic_data['id'].split('-')[2]),
                        is_unlocked=subtopic_data.get('isUnlocked', False)
                    )
                    session.add(subtopic)
                    await session.flush()
                    
                    # Save tasks
                    for task_data in subtopic_data.get('tasks', []):
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


# ================== BACKGROUND PROCESSING ==================

async def process_project_background(project_id: int, user_id: str):
    """Background task to process project with agent"""
    
    if not GitGuideAgent:
        print("❌ GitGuide Agent not available")
        return
    
    try:
        print(f"🚀 Starting background processing for project {project_id}")
        
        # Get project details
        print("📊 Fetching project details from database...")
        async with SessionLocal() as session:
            result = await session.execute(
                select(Project).filter(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                print(f"❌ Project {project_id} not found")
                return
            
            print(f"✅ Project found: {project.repo_url}")
            
            # Initialize agent
            print("🤖 Initializing GitGuide Agent...")
            agent = GitGuideAgent()
            print(f"✅ Agent initialized (Azure OpenAI configured: {bool(agent.azure_openai_config['api_key'])})")
            
            # Process with agent
            print(f"🔍 Processing project with agent...")
            result = await agent.process_new_project(
                project_id=project_id,
                repo_url=project.repo_url,
                skill_level=project.skill_level,
                domain=project.domain,
                user_id=user_id
            )
            print(f"📊 Agent processing result: {result}")
            
            if result['success']:
                print("✅ Agent processing completed successfully")
                # Update project status
                project.is_processed = True
                await session.commit()
                print("✅ Project status updated in database")
            else:
                print(f"❌ Agent processing failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Background processing failed for project {project_id}: {str(e)}")
        import traceback
        traceback.print_exc()


# ================== REGENERATION HELPERS ==================

async def get_project_for_regeneration(project_id: int, user_id: str) -> Any:
    """Get project details using raw SQL for regeneration endpoints"""
    async with SessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM projects WHERE project_id = :project_id AND user_id = :user_id"),
            {"project_id": project_id, "user_id": user_id}
        )
        project = result.fetchone()
        return project

async def get_repository_context_for_regeneration(project, agent):
    """Get repository context for regeneration operations"""
    repo_analysis = await analyze_repository(project.repo_url, agent.github_token)
    return prepare_repository_context(repo_analysis)

async def call_llm_for_regeneration(agent, prompt: str) -> Dict[str, Any]:
    """Call LLM for regeneration and parse response"""
    azure_client = AzureOpenAI(
        api_key=agent.azure_openai_config['api_key'],
        azure_endpoint=agent.azure_openai_config['endpoint'],
        api_version=agent.azure_openai_config['api_version']
    )
    response = azure_client.chat.completions.create(
        model=agent.azure_openai_config['deployment_name'],
        messages=[
            {
                "role": "system", 
                "content": "You are a technical learning expert. You MUST respond with ONLY valid JSON. No explanations, no markdown, no additional text. Your response must start with { and end with }."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=4000,
        temperature=0.7
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")

async def regenerate_concept_content(user_id: str, project_id: int, user_prompt: str, project_dict: Dict, concept_dict: Dict) -> Dict[str, Any]:
    """Regenerate concept content using LLM"""
    try:
        # Get agent instance
        agent = get_agent_instance()
        
        # Get project from database to get full details
        project = await get_project_for_regeneration(project_id, user_id)
        
        # Get repository context
        repo_context = await get_repository_context_for_regeneration(project, agent)
        
        # Create regeneration prompt
        from prompts.learning_path_prompts import create_regenerate_concept_prompt
        prompt = create_regenerate_concept_prompt(
            repo_context=repo_context,
            concept_to_regenerate=concept_dict,
            user_prompt=user_prompt,
            skill_level=project_dict['skill_level'],
            domain=project_dict['domain']
        )
        
        # Call LLM for regeneration
        result = await call_llm_for_regeneration(agent, prompt)
        
        return {
            'success': True,
            'concept': result.get('concept', result)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

async def clear_learning_path_for_project(project_id: int):
    """Clear entire learning path for project"""
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM tasks WHERE subtopic_id IN (SELECT id FROM subtopics WHERE concept_id IN (SELECT id FROM concepts WHERE project_id = :project_id))"), 
            {"project_id": project_id}
        )
        await session.execute(
            text("DELETE FROM subtopics WHERE concept_id IN (SELECT id FROM concepts WHERE project_id = :project_id)"), 
            {"project_id": project_id}
        )
        await session.execute(
            text("DELETE FROM concepts WHERE project_id = :project_id"), 
            {"project_id": project_id}
        )
        await session.commit()

async def update_project_overview(project_id: int, new_overview: str):
    """Update project overview in database"""
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE projects SET project_overview = :overview WHERE project_id = :project_id"),
            {"overview": new_overview, "project_id": project_id}
        )
        await session.commit()


# ================== ERROR HANDLING ==================

def handle_regeneration_error(operation: str, error: Exception):
    """Standardized error handling for regeneration operations"""
    print(f"❌ Error {operation}: {str(error)}")
    raise HTTPException(
        status_code=500, 
        detail=f"Failed to {operation}: {str(error)}"
    ) 