from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
import json
import os
import sys
import logging

from app.models import Project, Concept, Subtopic, Task
from app.db import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add agent directory to path for LLM access
sys.path.append(os.path.join(os.path.dirname(__file__), '../../agent'))
# Add prompts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../prompts'))

try:
    from groq import Groq
    from agent.repository_analyzer import analyze_repository
    from prompts import create_chat_prompt
except ImportError:
    print("⚠️ Chat dependencies not available")
    Groq = None

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    context_used: dict

def extract_user_id_from_token(authorization: str = None) -> str:
    """Extract Clerk user ID from JWT token"""
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

async def get_project_full_context(project_id: int, user_id: str):
    """Get complete project context including repository files and learning path"""
    
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
        
        # Get learning path (concepts, subtopics, tasks)
        concepts_result = await session.execute(
            select(Concept).filter(Concept.project_id == project_id).order_by(Concept.order)
        )
        concepts = concepts_result.scalars().all()
        
        learning_path = []
        current_task = None
        
        for concept in concepts:
            # Get subtopics for this concept
            subtopics_result = await session.execute(
                select(Subtopic).filter(Subtopic.concept_id == concept.concept_id).order_by(Subtopic.order)
            )
            subtopics = subtopics_result.scalars().all()
            
            concept_data = {
                'id': concept.concept_external_id,
                'name': concept.name,
                'description': concept.description,
                'is_unlocked': concept.is_unlocked,
                'subtopics': []
            }
            
            for subtopic in subtopics:
                # Get tasks for this subtopic
                tasks_result = await session.execute(
                    select(Task).filter(Task.subtopic_id == subtopic.subtopic_id).order_by(Task.order)
                )
                tasks = tasks_result.scalars().all()
                
                subtopic_data = {
                    'id': subtopic.subtopic_external_id,
                    'name': subtopic.name,
                    'description': subtopic.description,
                    'is_unlocked': subtopic.is_unlocked,
                    'tasks': []
                }
                
                for task in tasks:
                    task_data = {
                        'id': task.task_external_id,
                        'name': task.title,
                        'description': task.description,
                        'difficulty': task.difficulty,
                        'files_to_study': json.loads(task.files_to_study) if task.files_to_study else [],
                        'is_unlocked': task.is_unlocked,
                        'status': task.status.value
                    }
                    
                    # Track current task (first unlocked, not completed task)
                    if task.is_unlocked and task.status.value == 'not_started' and not current_task:
                        current_task = task_data
                    
                    subtopic_data['tasks'].append(task_data)
                
                concept_data['subtopics'].append(subtopic_data)
            
            learning_path.append(concept_data)
        
        # Get repository files if available
        repo_files = {}
        if project.is_processed:
            try:
                github_token = os.getenv('GITHUB_ACCESS_TOKEN')
                if github_token:
                    repo_analysis = await analyze_repository(project.repo_url, github_token)
                    if repo_analysis['success']:
                        repo_files = repo_analysis['files']
            except Exception as e:
                print(f"Failed to get repository files: {e}")
        
        return {
            'project': {
                'name': project.repo_name or project.repo_url.split('/')[-1],
                'overview': project.project_overview,
                'repo_url': project.repo_url,
                'skill_level': project.skill_level,
                'domain': project.domain,
                'tech_stack': json.loads(project.tech_stack) if project.tech_stack else {},
                'is_processed': project.is_processed
            },
            'learning_path': learning_path,
            'current_task': current_task,
            'repo_files': repo_files
        }

# Chat prompt function moved to prompts/chat_prompts.py

@router.post("/chat/project/{project_id}",
    summary="Chat with AI Tutor",
    description="Send message to context-aware AI assistant that knows your project, repository, and learning progress",
    response_description="AI tutor response with context information"
)
async def chat_with_project_context(
    project_id: int,
    message: ChatMessage,
    authorization: str = Header(None)
) -> ChatResponse:
    """Chat with AI assistant that has full project context"""
    logger.info(f"💬 Chat request for project {project_id}: '{message.message[:50]}...'")
    
    if not Groq:
        logger.error("❌ Groq API not available")
        raise HTTPException(
            status_code=503,
            detail="Chat service not available - Groq API not configured"
        )
    
    try:
        user_id = extract_user_id_from_token(authorization)
        logger.info(f"👤 User {user_id} chatting with project {project_id}")
        
        # Get complete project context
        logger.info(f"🔍 Fetching project context...")
        context = await get_project_full_context(project_id, user_id)
        logger.info(f"📊 Context loaded: {len(context['repo_files'])} files, {len(context['learning_path'])} concepts, processed={context['project']['is_processed']}")
        
        # Create context-aware prompt
        prompt = create_chat_prompt(message.message, context)
        logger.info(f"📝 Prompt created: {len(prompt)} characters")
        
        # Call Groq LLM
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            logger.error("❌ Groq API key not configured")
            raise HTTPException(status_code=503, detail="Groq API key not configured")
        
        logger.info(f"🤖 Calling Groq LLM...")
        client = Groq(api_key=groq_api_key)
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        assistant_response = response.choices[0].message.content
        logger.info(f"✅ LLM response received: {len(assistant_response)} characters")
        
        # Return response with context summary
        context_summary = {
            'has_repo_files': len(context['repo_files']) > 0,
            'has_learning_path': len(context['learning_path']) > 0,
            'current_task': context['current_task']['name'] if context['current_task'] else None,
            'project_processed': context['project']['is_processed']
        }
        
        logger.info(f"📤 Returning chat response with context: {context_summary}")
        return ChatResponse(
            response=assistant_response,
            context_used=context_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat error for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@router.get("/chat/project/{project_id}/context",
    summary="Get Chat Context",
    description="Retrieve available context information that the AI assistant can access for this project",
    response_description="Project context summary including files, concepts, and progress"
)
async def get_chat_context(
    project_id: int,
    authorization: str = Header(None)
):
    """Get the context that would be available to the chat assistant"""
    
    try:
        user_id = extract_user_id_from_token(authorization)
        context = await get_project_full_context(project_id, user_id)
        
        # Return summary of available context
        return {
            'project_name': context['project']['name'],
            'is_processed': context['project']['is_processed'],
            'has_overview': bool(context['project']['overview']),
            'concepts_count': len(context['learning_path']),
            'repo_files_count': len(context['repo_files']),
            'current_task': context['current_task']['name'] if context['current_task'] else None,
            'tech_stack': context['project']['tech_stack']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")

@router.get("/chat/health",
    summary="Chat Service Health",
    description="Check if AI chat service is available and properly configured",
    response_description="Chat service status and dependencies"
)
async def chat_health_check():
    """Check if chat service is available"""
    
    return {
        "status": "available" if Groq else "unavailable",
        "groq_available": bool(Groq),
        "groq_api_key": bool(os.getenv('GROQ_API_KEY')),
        "github_token": bool(os.getenv('GITHUB_ACCESS_TOKEN'))
    } 