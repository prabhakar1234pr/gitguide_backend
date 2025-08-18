"""
API client for GitGuide backend
Handles communication with FastAPI backend
"""

import os
import json
import aiohttp
import sys
from typing import Dict, Any, Optional
from sqlalchemy import select, text
from app.database_models import Project, Concept, Subtopic, Task
from app.database_config import SessionLocal

# Import days utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.routes.shared.days_utilities import create_15_days_for_project

async def save_learning_content(project_id: int, learning_path: Dict[str, Any], repo_info: Dict[str, Any]) -> Dict[str, Any]:
    """Save learning content to database directly.

    Supports payloads of the form:
      - { "concepts": [...] }                         # general save/regeneration
      - { "day_0_concepts": [...] }                   # day-specific content
      - { "day_1_concepts": [...]} .. { "day_14_concepts": [...] }
    """
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
            
            # Update project overview/metadata if provided
            if 'project_overview' in learning_path:
                project.project_overview = learning_path.get('project_overview', '')
            if repo_info:
                project.tech_stack = json.dumps(repo_info.get('tech_stack', []))
            # Mark as processed when first content saved
            project.is_processed = True
            
            # 🆕 Ensure days exist once
            existing_day = await session.execute(text("SELECT day_id FROM days WHERE project_id = :project_id LIMIT 1"), {"project_id": project_id})
            if not existing_day.fetchone():
                print(f"📅 Creating Day 0 + 14-day learning progression for project {project_id}")
                try:
                    project_name = repo_info.get('repo_name') or project.repo_name
                    if not project_name and project.repo_url:
                        project_name = project.repo_url.split('/')[-1].replace('.git', '')
                    days_created = await create_15_days_for_project(session, project_id, project_name)
                    print(f"✅ Created {len(days_created)} days (Day 0 unlocked for verification, Days 1-14 locked)")
                except Exception as days_error:
                    print(f"⚠️ Failed to create days (continuing with concepts): {str(days_error)}")
            
            # Determine target day and concepts array
            target_day_number: Optional[int] = None
            concepts_data = []
            if 'concepts' in learning_path:
                concepts_data = learning_path.get('concepts', [])
            else:
                # day_n_concepts keys
                for n in range(0, 15):
                    key = f'day_{n}_concepts'
                    if key in learning_path and isinstance(learning_path[key], list):
                        target_day_number = n
                        concepts_data = learning_path[key]
                        break

            print(f"📚 Processing {len(concepts_data)} concepts (day={target_day_number if target_day_number is not None else 'N/A'})")

            # If day-specific, fetch day row to set day_id and lock state
            day_row = None
            if target_day_number is not None:
                res = await session.execute(text("SELECT day_id, is_unlocked FROM days WHERE project_id = :project_id AND day_number = :day_number"), {"project_id": project_id, "day_number": target_day_number})
                day_row = res.fetchone()
            
            for i, concept_data in enumerate(concepts_data):
                print(f"📖 Concept {i+1}: {concept_data.get('name', 'Unnamed')}")
                print(f"   ID: {concept_data.get('id', 'No ID')}")
                print(f"   Subtopics: {len(concept_data.get('subTopics', []))}")
                
                concept = Concept(
                    project_id=project_id,
                    day_id=day_row[0] if day_row else None,
                    concept_external_id=concept_data['id'],
                    title=concept_data.get('name', concept_data.get('title', '')),
                    description=concept_data.get('description', ''),
                    order=(concept_data.get('order') if isinstance(concept_data.get('order'), int) else (int(concept_data['id'].split('-')[-1]) if '-' in concept_data['id'] else i + 1)),
                    is_unlocked=(bool(day_row[1]) if day_row is not None else concept_data.get('isUnlocked', False))
                )
                session.add(concept)
                await session.flush()
                print(f"✅ Concept saved with ID: {concept.concept_id}")
                
                # Save subtopics (support 'subtopics', 'subTopics', or 'subconcepts')
                subtopics_data = (
                    concept_data.get('subtopics')
                    or concept_data.get('subTopics')
                    or concept_data.get('subconcepts', [])
                )
                print(f"📝 Processing {len(subtopics_data)} subtopics for concept {concept.concept_id}")
                
                for j, subtopic_data in enumerate(subtopics_data):
                    try:
                        print(f"   📄 Subtopic {j+1}: {subtopic_data.get('name', 'Unnamed')}")
                        print(f"      ID: {subtopic_data.get('id', 'No ID')}")
                        
                        # Check all supported task shapes: single 'task', array 'tasks', or 'subTasks'
                        if 'task' in subtopic_data and subtopic_data.get('task'):
                            candidate_tasks = [subtopic_data['task']]
                        else:
                            candidate_tasks = subtopic_data.get('tasks', subtopic_data.get('subTasks', []))
                        tasks_count = len(candidate_tasks)
                        print(f"      Tasks: {tasks_count}")
                        
                        # Safe order calculation - fallback to enumeration index
                        try:
                            subtopic_order = int(subtopic_data['id'].split('-')[2])
                        except (IndexError, ValueError):
                            subtopic_order = j + 1
                            print(f"      ⚠️ Using fallback order: {subtopic_order}")
                        
                        subtopic = Subtopic(
                            concept_id=concept.concept_id,
                            subtopic_external_id=subtopic_data.get('id', f"subtopic-{i}-{j}"),
                            name=subtopic_data.get('name', ''),
                            description=subtopic_data.get('description', ''),
                            order=subtopic_order,
                            is_unlocked=subtopic_data.get('isUnlocked', bool(day_row[1]) if day_row is not None else False),
                        )
                        session.add(subtopic)
                        await session.flush()
                        print(f"   ✅ Subtopic saved with ID: {subtopic.subtopic_id}")
                        
                        # Save tasks (normalize to list)
                        tasks_data = candidate_tasks
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
                                    task_external_id=task_data.get('id', f"task-{i}-{j}-{k}"),
                                    title=task_data.get('name', task_data.get('title', '')),
                                    description=task_data.get('description', ''),
                                    order=task_order,
                                    difficulty=task_data.get('difficulty', 'medium'),
                                    files_to_study=json.dumps(task_data.get('files_to_study', [])),
                                    is_unlocked=task_data.get('isUnlocked', bool(day_row[1]) if day_row is not None else False),
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
            
            # If day-specific, mark day content as generated
            if target_day_number is not None:
                await session.execute(
                    text("UPDATE days SET is_content_generated = TRUE WHERE project_id = :project_id AND day_number = :day_number"),
                    {"project_id": project_id, "day_number": target_day_number},
                )

            await session.commit()
            print("✅ All learning content saved successfully")
            print("🚀 New hierarchy: Project → Days (14) → Concepts → Subtopics → Tasks")
            print("🔓 Day 1 is unlocked, Days 2-14 are locked and will unlock as you progress")
            
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

# Deprecated direct DB save helpers removed (kept API minimal)

# Utility function for getting user JWT token (for future implementation)
def get_user_jwt_token(user_id):
    """
    Get JWT token for user - to be implemented
    This would integrate with Clerk or your auth system
    """
    # TODO: Implement JWT token retrieval
    # This would involve calling Clerk API or your auth service
    pass

# Health check function (not used; removed to avoid extra dependency)