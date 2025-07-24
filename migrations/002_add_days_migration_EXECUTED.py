"""
Database migration to add Days table for 14-day learning progression
Run this script to add the new Days table and update relationships
"""

import asyncio
from sqlalchemy import text
from app.database_config import engine, SessionLocal
from app.database_models import Base

async def add_days_table():
    """Add Days table and update schema for 14-day progression"""
    
    print("🚀 Starting Days table migration...")
    
    try:
        async with engine.begin() as conn:
            # Create Days table
            print("📅 Creating days table...")
            try:
                await conn.execute(text("""
                    CREATE TABLE days (
                        day_id SERIAL PRIMARY KEY,
                        project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        day_number INTEGER NOT NULL,
                        day_external_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        description TEXT,
                        is_unlocked BOOLEAN DEFAULT FALSE NOT NULL,
                        is_completed BOOLEAN DEFAULT FALSE NOT NULL,
                        "order" INTEGER NOT NULL,
                        CONSTRAINT unique_project_day UNIQUE (project_id, day_number)
                    )
                """))
                print("✅ Days table created")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Days table already exists, skipping...")
                else:
                    raise e
            
            # Add day_id column to concepts table
            print("🔗 Adding day_id to concepts table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE concepts 
                    ADD COLUMN day_id INTEGER REFERENCES days(day_id) ON DELETE CASCADE
                """))
                print("✅ day_id column added to concepts table")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ day_id column already exists, skipping...")
                else:
                    raise e
        
        print("🎉 Days table migration completed successfully!")
        
        # Display migration summary
        print("\n📋 Migration Summary:")
        print("  ✅ Days table: Created with 14-day progression support")
        print("  ✅ Concepts table: Added day_id foreign key relationship")
        print("  ✅ Unique constraints: Added to prevent duplicate days per project")
        print("\n🚀 New hierarchy: Project → Days → Concepts → Subtopics → Tasks")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise e

async def create_sample_days_for_existing_projects():
    """Create 14 days for all existing projects that don't have days yet"""
    
    print("\n🔄 Creating sample days for existing projects...")
    
    async with SessionLocal() as session:
        try:
            # Get all projects that don't have days yet
            result = await session.execute(text("""
                SELECT project_id, repo_name 
                FROM projects 
                WHERE project_id NOT IN (SELECT DISTINCT project_id FROM days)
            """))
            projects_without_days = result.fetchall()
            
            if not projects_without_days:
                print("ℹ️ No existing projects need days created")
                return
            
            print(f"📊 Found {len(projects_without_days)} projects without days")
            
            # Create 14 days for each project
            for project in projects_without_days:
                project_id = project[0]
                repo_name = project[1] or "Repository"
                
                print(f"  📅 Creating 14 days for project {project_id} ({repo_name})")
                
                for day_num in range(1, 15):  # Days 1-14
                    day_name = f"Day {day_num}"
                    if day_num == 1:
                        day_name += ": Getting Started"
                    elif day_num <= 3:
                        day_name += ": Foundation"
                    elif day_num <= 7:
                        day_name += ": Core Concepts"
                    elif day_num <= 10:
                        day_name += ": Advanced Topics"
                    else:
                        day_name += ": Mastery"
                    
                    # Only Day 1 is unlocked initially
                    is_unlocked = (day_num == 1)
                    
                    await session.execute(text("""
                        INSERT INTO days (project_id, day_number, day_external_id, name, description, is_unlocked, is_completed, "order")
                        VALUES (:project_id, :day_number, :day_external_id, :name, :description, :is_unlocked, :is_completed, :order)
                    """), {
                        'project_id': project_id,
                        'day_number': day_num,
                        'day_external_id': f"day-{day_num}",
                        'name': day_name,
                        'description': f"Learning objectives and concepts for {day_name.lower()}",
                        'is_unlocked': is_unlocked,
                        'is_completed': False,
                        'order': day_num
                    })
            
            await session.commit()
            print(f"✅ Created 14 days each for {len(projects_without_days)} projects")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to create sample days: {str(e)}")
            raise e

async def rollback_days_migration():
    """Rollback the days migration (use with caution!)"""
    print("⚠️ Rolling back days migration...")
    
    try:
        async with engine.begin() as conn:
            # Remove day_id column from concepts
            await conn.execute(text("ALTER TABLE concepts DROP COLUMN IF EXISTS day_id"))
            
            # Drop days table
            await conn.execute(text("DROP TABLE IF EXISTS days CASCADE"))
            
        print("✅ Days migration rollback completed")
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        raise e

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("⚠️ DANGER: This will rollback the days table migration!")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            asyncio.run(rollback_days_migration())
        else:
            print("❌ Rollback cancelled")
    elif len(sys.argv) > 1 and sys.argv[1] == "--create-sample-days":
        asyncio.run(create_sample_days_for_existing_projects())
    else:
        # Run the full migration
        asyncio.run(add_days_table())
        
        # Ask if user wants to create sample days for existing projects
        create_sample = input("\n🤔 Create sample 14 days for existing projects? (y/n): ")
        if create_sample.lower() in ['y', 'yes']:
            asyncio.run(create_sample_days_for_existing_projects())
        else:
            print("ℹ️ Skipped creating sample days. You can run this later with: python add_days_migration.py --create-sample-days") 