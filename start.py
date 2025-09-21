#!/usr/bin/env python3
"""
Startup script for GitGuide Backend on Render
This script helps with debugging and ensures proper startup
"""

import os
import sys
import asyncio
import uvicorn
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_environment():
    """Check critical environment variables"""
    required_vars = [
        "DATABASE_URL",
        "AZURE_OPENAI_KEY", 
        "AZURE_OPENAI_ENDPOINT",
        "CLERK_SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("🔧 Please check your Render environment configuration")
        return False
    
    print("✅ All critical environment variables are set")
    return True

async def test_database_connection():
    """Test database connection"""
    try:
        from app.database_config import get_db
        # This is just a basic import test
        print("✅ Database configuration imported successfully")
        return True
    except Exception as e:
        print(f"❌ Database connection issue: {e}")
        return False

def main():
    """Main startup function"""
    print("🚀 Starting GitGuide Backend...")
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test database (basic import)
    if not asyncio.run(test_database_connection()):
        print("⚠️ Database test failed, but continuing...")
    
    # Get port from environment
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"🌐 Starting server on {host}:{port}")
    
    # Import the FastAPI app
    try:
        from app.api_server import app
        print("✅ FastAPI app imported successfully")
    except Exception as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        sys.exit(1)
    
    # Start the server
    uvicorn.run(
        "app.api_server:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
