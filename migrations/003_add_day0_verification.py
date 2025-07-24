"""
Database migration to add Day 0 verification system
Adds verification fields and creates Day 0 for existing projects
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database_config import engine, SessionLocal

async def add_day0_verification():
    """Add Day 0 verification system to database"""
    
    print("🚀 Starting Day 0 verification migration...")
    
    try:
        async with engine.begin() as conn:
            # Add verification fields to days table
            print("📅 Adding verification fields to days table...")
            try:
                await conn.execute(text("""
                    ALTER TABLE days 
                    ADD COLUMN requires_verification BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN verification_repo_url VARCHAR,
                    ADD COLUMN is_verified BOOLEAN DEFAULT FALSE NOT NULL
                """))
                print("✅ Verification fields added to days table")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⚠️ Verification fields already exist, skipping...")
                else:
                    raise e
        
        print("🎉 Day 0 verification migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise e

async def create_day0_for_existing_projects():
    """Create Day 0 for all existing projects"""
    
    print("\n🔄 Creating Day 0 for existing projects...")
    
    async with SessionLocal() as session:
        try:
            # Get all projects that don't have Day 0 yet
            result = await session.execute(text("""
                SELECT project_id, repo_name, repo_url 
                FROM projects 
                WHERE project_id NOT IN (SELECT DISTINCT project_id FROM days WHERE day_number = 0)
            """))
            projects_without_day0 = result.fetchall()
            
            if not projects_without_day0:
                print("ℹ️ No existing projects need Day 0 created")
                return
            
            print(f"📊 Found {len(projects_without_day0)} projects without Day 0")
            
            # Create Day 0 for each project
            for project in projects_without_day0:
                project_id = project[0]
                repo_name = project[1] or "Repository"
                repo_url = project[2]
                
                print(f"  📅 Creating Day 0 for project {project_id} ({repo_name})")
                
                # Extract project name from repo URL for repository naming
                project_name = repo_url.split('/')[-1].replace('.git', '') if repo_url else repo_name
                
                await session.execute(text("""
                    INSERT INTO days (project_id, day_number, day_external_id, name, description, 
                                    is_unlocked, is_completed, "order", requires_verification, is_verified)
                    VALUES (:project_id, :day_number, :day_external_id, :name, :description, 
                            :is_unlocked, :is_completed, :order, :requires_verification, :is_verified)
                """), {
                    'project_id': project_id,
                    'day_number': 0,
                    'day_external_id': 'day-0',
                    'name': 'Day 0: Setup Your Practice Repository',
                    'description': f'Create your own GitHub repository named "{project_name}-gitguide" to practice and track your learning progress.',
                    'is_unlocked': True,  # Day 0 is always unlocked
                    'is_completed': False,
                    'order': 0,
                    'requires_verification': True,
                    'is_verified': False
                })
            
            # Update existing Day 1 to be locked until Day 0 verification
            await session.execute(text("""
                UPDATE days 
                SET is_unlocked = FALSE 
                WHERE day_number = 1 AND project_id IN (
                    SELECT project_id FROM days WHERE day_number = 0 AND requires_verification = TRUE
                )
            """))
            
            await session.commit()
            print(f"✅ Created Day 0 for {len(projects_without_day0)} projects")
            print("🔒 Locked Day 1 until Day 0 verification is completed")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to create Day 0: {str(e)}")
            raise e

async def rollback_day0_verification():
    """Rollback the Day 0 verification migration (use with caution!)"""
    print("⚠️ Rolling back Day 0 verification migration...")
    
    try:
        async with engine.begin() as conn:
            # Remove Day 0 entries
            await conn.execute(text("DELETE FROM days WHERE day_number = 0"))
            
            # Remove verification fields
            await conn.execute(text("""
                ALTER TABLE days 
                DROP COLUMN IF EXISTS requires_verification,
                DROP COLUMN IF EXISTS verification_repo_url,
                DROP COLUMN IF EXISTS is_verified
            """))
            
            # Re-unlock Day 1 for all projects
            await conn.execute(text("""
                UPDATE days 
                SET is_unlocked = TRUE 
                WHERE day_number = 1
            """))
            
        print("✅ Day 0 verification migration rollback completed")
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        raise e

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("⚠️ DANGER: This will rollback the Day 0 verification migration!")
        confirm = input("Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            asyncio.run(rollback_day0_verification())
        else:
            print("❌ Rollback cancelled")
    elif len(sys.argv) > 1 and sys.argv[1] == "--create-day0":
        asyncio.run(create_day0_for_existing_projects())
    else:
        # Run the full migration
        asyncio.run(add_day0_verification())
        
        # Ask if user wants to create Day 0 for existing projects
        create_day0 = input("\n🤔 Create Day 0 for existing projects? (y/n): ")
        if create_day0.lower() in ['y', 'yes']:
            asyncio.run(create_day0_for_existing_projects())
        else:
            print("ℹ️ Skipped creating Day 0. You can run this later with: python migrations/003_add_day0_verification.py --create-day0") 