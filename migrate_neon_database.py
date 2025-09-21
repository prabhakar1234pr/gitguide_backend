#!/usr/bin/env python3
"""
Neon Database Migration Script for GitGuide
Handles database migrations specifically for Neon Tech PostgreSQL
"""

import os
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.database_models import Base
from force_env_loader import force_load_env

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_neon_connection():
    """Test connection to Neon database"""
    try:
        force_load_env()
        database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
        
        if not database_url:
            raise ValueError("No DATABASE_URL or NEON_DATABASE_URL found in environment")
        
        logger.info(f"🔗 Connecting to Neon database...")
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Connected to PostgreSQL: {version}")
            
            # Check if this is Neon
            if "neon" in version.lower() or "postgres" in version.lower():
                logger.info("🎯 Confirmed: Connected to Neon PostgreSQL")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

async def run_migrations():
    """Run database migrations for Neon"""
    try:
        force_load_env()
        database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
        
        if not database_url:
            raise ValueError("No DATABASE_URL or NEON_DATABASE_URL found in environment")
        
        logger.info("🔄 Starting Neon database migrations...")
        
        # Create async engine with Neon-optimized settings
        engine = create_async_engine(
            database_url,
            echo=True,
            pool_pre_ping=True,  # Important for serverless databases like Neon
            pool_recycle=300,    # Recycle connections every 5 minutes
            connect_args={
                "server_settings": {
                    "application_name": "GitGuide_Migration",
                }
            }
        )
        
        # Create all tables
        async with engine.begin() as conn:
            logger.info("📋 Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created successfully!")
            
            # Verify tables were created
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            logger.info(f"📊 Created tables: {', '.join(tables)}")
            
        await engine.dispose()
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

async def verify_database_schema():
    """Verify database schema is correct"""
    try:
        force_load_env()
        database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")
        
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Check all expected tables exist
            expected_tables = [
                'projects', 'days', 'concepts', 'subconcepts', 'tasks'
            ]
            
            for table in expected_tables:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """))
                exists = result.fetchone()[0]
                
                if exists:
                    logger.info(f"✅ Table '{table}' exists")
                else:
                    logger.error(f"❌ Table '{table}' missing")
                    return False
            
            logger.info("🎯 Database schema verification successful!")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}")
        return False

async def main():
    """Main migration function"""
    logger.info("🚀 GitGuide Neon Database Migration")
    logger.info("=" * 50)
    
    # Step 1: Test connection
    logger.info("Step 1: Testing Neon connection...")
    if not await check_neon_connection():
        logger.error("❌ Cannot connect to Neon database. Check your DATABASE_URL.")
        return False
    
    # Step 2: Run migrations
    logger.info("\nStep 2: Running migrations...")
    if not await run_migrations():
        logger.error("❌ Migration failed!")
        return False
    
    # Step 3: Verify schema
    logger.info("\nStep 3: Verifying database schema...")
    if not await verify_database_schema():
        logger.error("❌ Schema verification failed!")
        return False
    
    logger.info("\n🎉 All steps completed successfully!")
    logger.info("🌐 Your Neon database is ready for GitGuide!")
    return True

if __name__ == "__main__":
    asyncio.run(main())
