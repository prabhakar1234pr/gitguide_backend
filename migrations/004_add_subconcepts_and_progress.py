"""
Migration: Add Subconcepts and Progress Tracking
- Add subconcepts table for new learning structure
- Add progress tracking fields to projects, days, and concepts
- Add content generation status fields to days
- Add GitHub verification fields to tasks
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def fix_database_url(url):
    """Convert SQLAlchemy async URL to asyncpg format"""
    if not url:
        return None
    
    # Replace postgresql+asyncpg:// with postgresql://
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    return url

async def run_migration():
    """Execute the migration to add subconcepts and progress tracking"""
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    # Fix the database URL format
    fixed_url = fix_database_url(DATABASE_URL)
    print(f"🔧 Using database URL: {fixed_url[:50]}...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(fixed_url)
        print("✅ Connected to database")
        
        # Start transaction
        async with conn.transaction():
            
            # 1. Add progress tracking fields to projects table
            print("📊 Adding progress tracking fields to projects table...")
            await conn.execute("""
                ALTER TABLE projects 
                ADD COLUMN IF NOT EXISTS total_days INTEGER DEFAULT 14 NOT NULL,
                ADD COLUMN IF NOT EXISTS completed_days INTEGER DEFAULT 0 NOT NULL,
                ADD COLUMN IF NOT EXISTS current_day INTEGER DEFAULT 0 NOT NULL,
                ADD COLUMN IF NOT EXISTS project_progress FLOAT DEFAULT 0.0 NOT NULL
            """)
            
            # 2. Add progress and content generation fields to days table
            print("📅 Adding progress and content fields to days table...")
            await conn.execute("""
                ALTER TABLE days 
                ADD COLUMN IF NOT EXISTS total_tasks INTEGER DEFAULT 100 NOT NULL,
                ADD COLUMN IF NOT EXISTS completed_tasks INTEGER DEFAULT 0 NOT NULL,
                ADD COLUMN IF NOT EXISTS day_progress FLOAT DEFAULT 0.0 NOT NULL,
                ADD COLUMN IF NOT EXISTS is_content_generated BOOLEAN DEFAULT FALSE NOT NULL,
                ADD COLUMN IF NOT EXISTS content_generation_started BOOLEAN DEFAULT FALSE NOT NULL
            """)
            
            # 3. Add progress tracking fields to concepts table
            print("💡 Adding progress tracking fields to concepts table...")
            await conn.execute("""
                ALTER TABLE concepts 
                ADD COLUMN IF NOT EXISTS total_subconcepts INTEGER DEFAULT 10 NOT NULL,
                ADD COLUMN IF NOT EXISTS completed_subconcepts INTEGER DEFAULT 0 NOT NULL,
                ADD COLUMN IF NOT EXISTS concept_progress FLOAT DEFAULT 0.0 NOT NULL
            """)
            
            # 4. Create subconcepts table
            print("🔧 Creating subconcepts table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS subconcepts (
                    subconcept_id SERIAL PRIMARY KEY,
                    concept_id INTEGER NOT NULL REFERENCES concepts(concept_id) ON DELETE CASCADE,
                    subconcept_external_id VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    "order" INTEGER NOT NULL,
                    is_unlocked BOOLEAN DEFAULT FALSE NOT NULL,
                    is_completed BOOLEAN DEFAULT FALSE NOT NULL
                )
            """)
            
            # 5. Add subconcept relationship to tasks table
            print("📝 Adding subconcept relationship to tasks table...")
            await conn.execute("""
                ALTER TABLE tasks 
                ADD COLUMN IF NOT EXISTS subconcept_id INTEGER REFERENCES subconcepts(subconcept_id) ON DELETE CASCADE
            """)
            
            # 6. Add GitHub verification fields to tasks table
            print("🔗 Adding GitHub verification fields to tasks table...")
            await conn.execute("""
                ALTER TABLE tasks 
                ADD COLUMN IF NOT EXISTS github_verification_status VARCHAR,
                ADD COLUMN IF NOT EXISTS github_check_url VARCHAR
            """)
            
            # 7. Update verification_type field to include 'github_api'
            print("🔍 Updating verification_type field...")
            await conn.execute("""
                UPDATE tasks 
                SET verification_type = 'github_api' 
                WHERE verification_type IS NULL AND subconcept_id IS NOT NULL
            """)
            
            # 8. Set Day 0 as content generated (it's always standard)
            print("📋 Setting Day 0 as content generated...")
            await conn.execute("""
                UPDATE days 
                SET is_content_generated = TRUE 
                WHERE day_number = 0
            """)
            
            # 9. Create indexes for better performance
            print("⚡ Creating indexes for performance...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_subconcepts_concept_id ON subconcepts(concept_id);
                CREATE INDEX IF NOT EXISTS idx_subconcepts_order ON subconcepts("order");
                CREATE INDEX IF NOT EXISTS idx_tasks_subconcept_id ON tasks(subconcept_id);
                CREATE INDEX IF NOT EXISTS idx_days_content_generated ON days(is_content_generated);
                CREATE INDEX IF NOT EXISTS idx_projects_current_day ON projects(current_day);
            """)
            
            print("✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        await conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    asyncio.run(run_migration()) 