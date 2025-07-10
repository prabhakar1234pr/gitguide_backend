"""
Database migration script to update schema for rich learning content
Run this script to migrate existing database to new schema
"""

import asyncio
from sqlalchemy import text
from app.db import engine, SessionLocal
from app.models import Base

async def migrate_database():
    """Migrate database to new schema"""
    
    print("🚀 Starting database migration...")
    
    try:
        # Create all new tables and columns
        async with engine.begin() as conn:
            # Add new columns to projects table
            print("📊 Adding new columns to projects table...")
            
            try:
                await conn.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN project_overview TEXT,
                    ADD COLUMN repo_name VARCHAR,
                    ADD COLUMN tech_stack TEXT,
                    ADD COLUMN is_processed BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✅ Projects table updated")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Projects columns already exist, skipping...")
                else:
                    raise e
            
            # Create concepts table
            print("📚 Creating concepts table...")
            try:
                await conn.execute(text("""
                    CREATE TABLE concepts (
                        concept_id SERIAL PRIMARY KEY,
                        project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        concept_external_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        description TEXT,
                        "order" INTEGER NOT NULL,
                        is_unlocked BOOLEAN DEFAULT FALSE NOT NULL
                    )
                """))
                print("✅ Concepts table created")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Concepts table already exists, skipping...")
                else:
                    raise e
            
            # Create subtopics table
            print("📖 Creating subtopics table...")
            try:
                await conn.execute(text("""
                    CREATE TABLE subtopics (
                        subtopic_id SERIAL PRIMARY KEY,
                        concept_id INTEGER NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
                        subtopic_external_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        description TEXT,
                        "order" INTEGER NOT NULL,
                        is_unlocked BOOLEAN DEFAULT FALSE NOT NULL
                    )
                """))
                print("✅ Subtopics table created")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Subtopics table already exists, skipping...")
                else:
                    raise e
            
            # Add new columns to tasks table
            print("✏️ Adding new columns to tasks table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE tasks 
                    ADD COLUMN subtopic_id INTEGER REFERENCES subtopics(subtopic_id) ON DELETE CASCADE,
                    ADD COLUMN task_external_id VARCHAR,
                    ADD COLUMN difficulty VARCHAR,
                    ADD COLUMN files_to_study TEXT,
                    ADD COLUMN is_unlocked BOOLEAN DEFAULT FALSE NOT NULL
                """))
                
                # Change description column to TEXT type
                await conn.execute(text("ALTER TABLE tasks ALTER COLUMN description TYPE TEXT"))
                
                print("✅ Tasks table updated")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Tasks columns already exist, skipping...")
                else:
                    raise e
        
        print("🎉 Database migration completed successfully!")
        
        # Display migration summary
        print("\n📋 Migration Summary:")
        print("  ✅ Projects table: Added project_overview, repo_name, tech_stack, is_processed")
        print("  ✅ Concepts table: Created with hierarchical structure")
        print("  ✅ Subtopics table: Created as child of concepts")
        print("  ✅ Tasks table: Added subtopic_id, task_external_id, difficulty, files_to_study, is_unlocked")
        print("\n🚀 Your database is now ready for the GitGuide Agent!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise e

async def rollback_migration():
    """Rollback migration (use with caution!)"""
    print("⚠️ Rolling back database migration...")
    
    try:
        async with engine.begin() as conn:
            # Drop new tables
            await conn.execute(text("DROP TABLE IF EXISTS subtopics CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS concepts CASCADE"))
            
            # Remove new columns from tasks
            await conn.execute(text("""
                ALTER TABLE tasks 
                DROP COLUMN IF EXISTS subtopic_id,
                DROP COLUMN IF EXISTS task_external_id,
                DROP COLUMN IF EXISTS difficulty,
                DROP COLUMN IF EXISTS files_to_study,
                DROP COLUMN IF EXISTS is_unlocked
            """))
            
            # Remove new columns from projects
            await conn.execute(text("""
                ALTER TABLE projects 
                DROP COLUMN IF EXISTS project_overview,
                DROP COLUMN IF EXISTS repo_name,
                DROP COLUMN IF EXISTS tech_stack,
                DROP COLUMN IF EXISTS is_processed
            """))
            
        print("✅ Rollback completed")
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        raise e

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("⚠️ DANGER: This will rollback all schema changes!")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            asyncio.run(rollback_migration())
        else:
            print("❌ Rollback cancelled")
    else:
        asyncio.run(migrate_database()) 