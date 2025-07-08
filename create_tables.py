import asyncio
import os
import sys
from app.db import engine, Base
from app import models  # Import all models

async def create_tables():
    """
    Creates all database tables defined in the models.
    Safe to run multiple times - will not recreate existing tables.
    """
    try:
        print("🗃️ Creating database tables...")
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        print("📋 Tables created:")
        
        # List all tables
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        raise

async def drop_and_create_tables():
    """
    Drops all tables and recreates them.
    WARNING: This will delete all data!
    """
    if os.getenv("ENVIRONMENT") == "production":
        print("❌ Cannot drop tables in production!")
        return
        
    try:
        print("⚠️ Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("🗑️ All tables dropped!")
        
        # Recreate tables
        await create_tables()
        
    except Exception as e:
        print(f"❌ Error in drop/create operation: {str(e)}")
        raise

async def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        await drop_and_create_tables()
    else:
        await create_tables()

if __name__ == "__main__":
    # Use asyncio.run() only once to avoid event loop conflicts
    asyncio.run(main())
