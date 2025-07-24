"""
Database migration to add Day 0 task verification system
Adds task verification fields and concept-level tasks
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database_config import engine, SessionLocal

async def add_task_verification_fields():
    """Add Day 0 task verification fields to database"""
    
    print("🚀 Starting Day 0 task verification migration...")
    
    try:
        async with engine.begin() as conn:
            # Add verification fields to tasks table
            print("📋 Adding verification fields to tasks table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE tasks 
                    ADD COLUMN concept_id INTEGER REFERENCES concepts(concept_id),
                    ADD COLUMN is_completed BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN verification_type VARCHAR,
                    ADD COLUMN verification_data TEXT,
                    ADD COLUMN is_verified BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✅ Verification fields added to tasks table")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Verification fields already exist, skipping...")
                else:
                    raise e
            
            # Add completion field to concepts table  
            print("📚 Adding completion field to concepts table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE concepts 
                    ADD COLUMN is_completed BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✅ Completion field added to concepts table")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Completion field already exists, skipping...")
                else:
                    raise e
                    
            # Change concepts.name to concepts.title for consistency
            print("🏷️ Updating concepts table naming...")
            try:
                # Check if title column exists
                result = await conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'concepts' AND column_name = 'title'
                """))
                title_exists = result.fetchone() is not None
                
                if not title_exists:
                    await conn.execute(text("ALTER TABLE concepts RENAME COLUMN name TO title"))
                    print("✅ Renamed concepts.name to concepts.title")
                else:
                    print("ℹ️ concepts.title already exists")
            except Exception as e:
                print(f"⚠️ Could not rename column: {str(e)}")
        
        print("🎉 Day 0 task verification migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise e

async def create_day0_content_for_existing_projects():
    """Create Day 0 concepts and tasks for existing projects"""
    
    print("\n🔄 Creating Day 0 content for existing projects...")
    
    # Import here to avoid circular imports
    from app.routes.shared.days_utilities import create_day0_concepts_and_tasks
    
    async with SessionLocal() as session:
        try:
            # Get all projects that have Day 0 but no concepts yet
            result = await session.execute(text("""
                SELECT DISTINCT d.project_id 
                FROM days d 
                WHERE d.day_number = 0 
                AND d.project_id NOT IN (
                    SELECT DISTINCT c.project_id 
                    FROM concepts c 
                    JOIN days d2 ON c.day_id = d2.day_id 
                    WHERE d2.day_number = 0
                )
            """))
            
            projects_needing_content = result.fetchall()
            
            if not projects_needing_content:
                print("ℹ️ No existing projects need Day 0 content created")
                return
            
            print(f"📊 Found {len(projects_needing_content)} projects needing Day 0 content")
            
            # Create Day 0 content for each project
            for (project_id,) in projects_needing_content:
                print(f"  📝 Creating Day 0 content for project {project_id}")
                await create_day0_concepts_and_tasks(session, project_id)
            
            print(f"✅ Created Day 0 content for {len(projects_needing_content)} projects")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to create Day 0 content: {str(e)}")
            raise e

async def rollback_task_verification():
    """Rollback the task verification migration (use with caution!)"""
    print("⚠️ Rolling back Day 0 task verification migration...")
    
    try:
        async with engine.begin() as conn:
            # Remove Day 0 concepts and tasks
            await conn.execute(text("""
                DELETE FROM tasks WHERE concept_id IN (
                    SELECT c.concept_id FROM concepts c 
                    JOIN days d ON c.day_id = d.day_id 
                    WHERE d.day_number = 0
                )
            """))
            
            await conn.execute(text("""
                DELETE FROM concepts WHERE day_id IN (
                    SELECT day_id FROM days WHERE day_number = 0
                )
            """))
            
            # Remove verification fields
            await conn.execute(text("""
                ALTER TABLE tasks 
                DROP COLUMN IF EXISTS concept_id,
                DROP COLUMN IF EXISTS is_completed,
                DROP COLUMN IF EXISTS verification_type,
                DROP COLUMN IF EXISTS verification_data,
                DROP COLUMN IF EXISTS is_verified
            """))
            
            await conn.execute(text("""
                ALTER TABLE concepts 
                DROP COLUMN IF EXISTS is_completed
            """))
            
        print("✅ Day 0 task verification migration rollback completed")
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        raise e

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("⚠️ DANGER: This will rollback the Day 0 task verification migration!")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            asyncio.run(rollback_task_verification())
        else:
            print("❌ Rollback cancelled")
    elif len(sys.argv) > 1 and sys.argv[1] == "--create-content":
        asyncio.run(create_day0_content_for_existing_projects())
    else:
        # Run the full migration
        asyncio.run(add_task_verification_fields())
        
        # Ask if user wants to create Day 0 content for existing projects
        create_content = input("\n🤔 Create Day 0 content for existing projects? (y/n): ")
        if create_content.lower() in ['y', 'yes']:
            asyncio.run(create_day0_content_for_existing_projects())
        else:
            print("ℹ️ Skipped creating Day 0 content. You can run this later with: python migrations/004_add_day0_tasks_verification.py --create-content") 