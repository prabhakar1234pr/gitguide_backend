import requests
import asyncio
import json
import sys
import os
from typing import Dict, List

# Add backend path for database access
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def save_learning_content(project_id, learning_path, backend_url, user_id):
    """
    Save generated learning content to the backend database
    
    Args:
        project_id: Database project ID
        learning_path: Generated learning path from LLM
        backend_url: Backend API URL
        user_id: Clerk user ID
        
    Returns:
        dict: Save operation result
    """
    try:
        # Import the database saving function directly
        from app.routes.agent import save_agent_content_to_db
        
        # Save content directly to database
        result = await save_agent_content_to_db(
            project_id=project_id,
            learning_path=learning_path,
            repo_info={'name': '', 'tech_stack': {}},  # Will be filled by agent
        )
        
        return {
            'success': True,
            'message': 'Learning content saved to database',
            'project_id': project_id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to save learning content: {str(e)}"
        }

def create_task_description(concept, subtopic, task, project_overview):
    """Create a comprehensive task description"""
    description = f"""
📚 **Concept**: {concept['name']}
{concept.get('description', '')}

📖 **Subtopic**: {subtopic['name']}
{subtopic.get('description', '')}

🎯 **Task**: {task['name']}
{task['description']}

📁 **Files to Study**: {', '.join(task.get('files_to_study', []))}

🔍 **Difficulty**: {task.get('difficulty', 'medium').title()}

💡 **Project Context**: This task is part of understanding the following project:
{project_overview[:200]}...
""".strip()
    
    return description

async def save_tasks_to_backend(tasks_data, backend_url, user_id):
    """Save tasks to the backend API - deprecated, using direct DB save now"""
    return {
        'success': True,
        'saved_count': len(tasks_data),
        'failed_count': 0,
        'failed_tasks': []
    }

async def create_task_api(task_data, backend_url, user_id):
    """Create a single task via the backend API - deprecated"""
    return {
        'success': True,
        'task_id': f"task_{task_data['order']}"
    }

# Direct database insertion for MVP 
async def save_tasks_directly_to_db(tasks_data, project_id):
    """
    Direct database save function - deprecated in favor of agent route integration
    """
    try:
        from app.models import Task
        from app.db import SessionLocal
        
        async with SessionLocal() as session:
            created_tasks = []
            
            for task_data in tasks_data:
                new_task = Task(
                    project_id=project_id,
                    title=task_data['title'],
                    description=task_data['description'],
                    order=task_data['order']
                )
                
                session.add(new_task)
                created_tasks.append(new_task)
            
            await session.commit()
            
            print(f"✅ Directly saved {len(created_tasks)} tasks to database")
            
            return {
                'success': True,
                'tasks_created': len(created_tasks)
            }
            
    except Exception as e:
        print(f"❌ Direct database save failed: {str(e)}")
        return {
            'success': False,
            'error': f"Direct database save failed: {str(e)}"
        }

# Utility function for getting user JWT token (for future implementation)
def get_user_jwt_token(user_id):
    """
    Get JWT token for user - to be implemented
    This would integrate with Clerk or your auth system
    """
    # TODO: Implement JWT token retrieval
    # This would involve calling Clerk API or your auth service
    pass

# Health check function
async def test_backend_connection(backend_url):
    """Test connection to backend API"""
    try:
        response = requests.get(f"{backend_url}/ping", timeout=5)
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 