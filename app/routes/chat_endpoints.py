from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import os
import sys

# Add path to import force_env_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from force_env_loader import force_load_env

# Force load correct environment variables from .env file
force_load_env()

from app.database_models import Project, Concept, Subtopic, Task
from app.database_config import SessionLocal
from app.routes.auth.auth_utilities import extract_user_id_from_token
from app.routes.shared.logging_and_paths import get_logger
from app.routes.shared.database_utilities import get_db_session, verify_project_ownership

logger = get_logger(__name__)

try:
    from openai import AzureOpenAI
    from agent.repository_analyzer import analyze_repository
    from prompts import create_chat_prompt
except ImportError:
    print("⚠️ Chat dependencies not available")
    AzureOpenAI = None

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    context_used: dict


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
        all_concepts = concepts_result.scalars().all()
        # Filter: only include concepts for unlocked days
        concepts = []
        from app.database_models import Day
        for concept in all_concepts:
            if concept.day_id:
                day_res = await session.execute(select(Day).filter(Day.day_id == concept.day_id))
                day = day_res.scalar_one_or_none()
                if day and day.is_unlocked:
                    concepts.append(concept)
        
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
                'name': concept.title,
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
    
    if not AzureOpenAI:
        logger.error("❌ Azure OpenAI not available")
        raise HTTPException(
            status_code=503,
            detail="Chat service not available - Azure OpenAI not configured"
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
        
        # Call Azure OpenAI
        azure_openai_key = os.getenv('AZURE_OPENAI_KEY')
        azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_openai_version = os.getenv('AZURE_OPENAI_API_VERSION')
        azure_openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT_4_1')
        
        if not azure_openai_key or not azure_openai_endpoint:
            logger.error("❌ Azure OpenAI configuration not complete")
            raise HTTPException(status_code=503, detail="Azure OpenAI not configured")
        
        logger.info(f"🤖 Calling Azure OpenAI...")
        client = AzureOpenAI(
            api_key=azure_openai_key,
            azure_endpoint=azure_openai_endpoint,
            api_version=azure_openai_version
        )
        
        response = client.chat.completions.create(
            model=azure_openai_deployment,
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
        "status": "available" if AzureOpenAI else "unavailable",
        "azure_openai_available": bool(AzureOpenAI),
        "azure_openai_key": bool(os.getenv('AZURE_OPENAI_KEY')),
        "azure_openai_endpoint": bool(os.getenv('AZURE_OPENAI_ENDPOINT')),
        "github_token": bool(os.getenv('GITHUB_ACCESS_TOKEN'))
    } 