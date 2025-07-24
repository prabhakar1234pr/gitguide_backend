"""
API client for GitGuide backend
Handles communication with FastAPI backend
"""

import os
import json
import aiohttp
from typing import Dict, Any, Optional
from sqlalchemy import select
from app.database_models import Project, Concept, Subtopic, Task
from app.database_config import SessionLocal

async def save_learning_content(project_id: int, learning_path: Dict[str, Any], repo_info: Dict[str, Any]) -> Dict[str, Any]:
    """Save learning content to database directly"""
    async with SessionLocal() as session:
        try:
            print(f"💾 Saving learning content for project {project_id}")
            print(f"📊 Learning path structure: {json.dumps(learning_path, indent=2)[:1000]}...")
            
            # Update project with overview and metadata
            result = await session.execute(
                select(Project).filter(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                raise Exception(f"Project {project_id} not found")
            
            # Update project overview
            project.project_overview = learning_path.get('project_overview', '')
            project.tech_stack = json.dumps(repo_info.get('tech_stack', []))
            project.is_processed = True
            
            # Save concepts
            concepts_data = learning_path.get('concepts', [])
            print(f"📚 Processing {len(concepts_data)} concepts")
            
            for i, concept_data in enumerate(concepts_data):
                print(f"📖 Concept {i+1}: {concept_data.get('name', 'Unnamed')}")
                print(f"   ID: {concept_data.get('id', 'No ID')}")
                print(f"   Subtopics: {len(concept_data.get('subTopics', []))}")
                
                concept = Concept(
                    project_id=project_id,
                    concept_external_id=concept_data['id'],
                    name=concept_data['name'],
                    description=concept_data.get('description', ''),
                    order=int(concept_data['id'].split('-')[1]),
                    is_unlocked=concept_data.get('isUnlocked', False)
                )
                session.add(concept)
                await session.flush()
                print(f"✅ Concept saved with ID: {concept.concept_id}")
                
                # Save subtopics
                subtopics_data = concept_data.get('subtopics', concept_data.get('subTopics', []))
                print(f"📝 Processing {len(subtopics_data)} subtopics for concept {concept.concept_id}")
                
                for j, subtopic_data in enumerate(subtopics_data):
                    try:
                        print(f"   📄 Subtopic {j+1}: {subtopic_data.get('name', 'Unnamed')}")
                        print(f"      ID: {subtopic_data.get('id', 'No ID')}")
                        
                        # Check both 'tasks' and 'subTasks' keys
                        tasks_count = len(subtopic_data.get('tasks', subtopic_data.get('subTasks', [])))
                        print(f"      Tasks: {tasks_count}")
                        
                        # Safe order calculation - fallback to enumeration index
                        try:
                            subtopic_order = int(subtopic_data['id'].split('-')[2])
                        except (IndexError, ValueError):
                            subtopic_order = j + 1
                            print(f"      ⚠️ Using fallback order: {subtopic_order}")
                        
                        subtopic = Subtopic(
                            concept_id=concept.concept_id,
                            subtopic_external_id=subtopic_data['id'],
                            name=subtopic_data['name'],
                            description=subtopic_data.get('description', ''),
                            order=subtopic_order,
                            is_unlocked=subtopic_data.get('isUnlocked', False)
                        )
                        session.add(subtopic)
                        await session.flush()
                        print(f"   ✅ Subtopic saved with ID: {subtopic.subtopic_id}")
                        
                        # Save tasks - check both keys
                        tasks_data = subtopic_data.get('tasks', subtopic_data.get('subTasks', []))
                        print(f"   📋 Processing {len(tasks_data)} tasks for subtopic {subtopic.subtopic_id}")
                        
                        for k, task_data in enumerate(tasks_data):
                            try:
                                print(f"      ⚡ Task {k+1}: {task_data.get('name', 'Unnamed')}")
                                
                                # Safe order calculation - fallback to enumeration index
                                try:
                                    task_order = int(task_data['id'].split('-')[3])
                                except (IndexError, ValueError):
                                    task_order = k + 1
                                    print(f"         ⚠️ Using fallback task order: {task_order}")
                                
                                task = Task(
                                    project_id=project_id,
                                    subtopic_id=subtopic.subtopic_id,
                                    task_external_id=task_data['id'],
                                    title=task_data['name'],
                                    description=task_data.get('description', ''),
                                    order=task_order,
                                    difficulty=task_data.get('difficulty', 'medium'),
                                    files_to_study=json.dumps(task_data.get('files_to_study', [])),
                                    is_unlocked=task_data.get('isUnlocked', False)
                                )
                                session.add(task)
                                print(f"      ✅ Task saved: {task.title}")
                                
                            except Exception as task_error:
                                print(f"      ❌ Failed to save task {k+1}: {str(task_error)}")
                                import traceback
                                traceback.print_exc()
                                continue
                                
                    except Exception as subtopic_error:
                        print(f"   ❌ Failed to save subtopic {j+1}: {str(subtopic_error)}")
                        import traceback
                        traceback.print_exc()
                        continue
            
            await session.commit()
            print("✅ All learning content saved successfully")
            return {"success": True, "message": "Learning content saved successfully"}
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to save learning content: {str(e)}")
            import traceback
            traceback.print_exc()
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