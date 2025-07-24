import asyncio
from app.database_config import SessionLocal
from app.database_models import Project
from sqlalchemy import select, func

async def cleanup_duplicate_projects():
    """Remove duplicate projects, keeping only the latest one for each user/repo combination"""
    
    async with SessionLocal() as session:
        try:
            print("🔍 Finding duplicate projects...")
            
            # Find all projects
            result = await session.execute(select(Project))
            all_projects = result.scalars().all()
            
            print(f"📊 Total projects: {len(all_projects)}")
            
            # Group projects by user_id and repo_url
            duplicates_to_remove = []
            seen_combinations = {}
            
            for project in all_projects:
                key = (project.user_id, project.repo_url)
                
                if key in seen_combinations:
                    # Found a duplicate
                    existing_project = seen_combinations[key]
                    
                    # Keep the one with higher project_id (more recent)
                    if project.project_id > existing_project.project_id:
                        duplicates_to_remove.append(existing_project)
                        seen_combinations[key] = project
                        print(f"🔄 Will keep project {project.project_id} over {existing_project.project_id} for {project.repo_url}")
                    else:
                        duplicates_to_remove.append(project)
                        print(f"🔄 Will keep project {existing_project.project_id} over {project.project_id} for {project.repo_url}")
                else:
                    seen_combinations[key] = project
            
            if not duplicates_to_remove:
                print("✅ No duplicate projects found")
                return
            
            print(f"🗑️ Found {len(duplicates_to_remove)} duplicate projects to remove:")
            
            for project in duplicates_to_remove:
                print(f"  - Project {project.project_id}: {project.repo_url} (User: {project.user_id})")
            
            # Ask for confirmation
            confirm = input("\n❓ Do you want to remove these duplicate projects? (y/N): ")
            
            if confirm.lower() == 'y':
                for project in duplicates_to_remove:
                    await session.delete(project)
                    print(f"🗑️ Removed project {project.project_id}")
                
                await session.commit()
                print(f"✅ Successfully removed {len(duplicates_to_remove)} duplicate projects")
            else:
                print("❌ Cleanup cancelled")
                
        except Exception as e:
            await session.rollback()
            print(f"❌ Error during cleanup: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(cleanup_duplicate_projects()) 