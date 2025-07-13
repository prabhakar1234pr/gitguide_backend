from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import json
import asyncio
import sys
import os

from app.models import Project, Concept, Subtopic, Task
from app.db import SessionLocal

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
    project_id: int
    is_processed: bool
    status: str
    message: str

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
                project_id=project_id,
                is_processed=project.is_processed,
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