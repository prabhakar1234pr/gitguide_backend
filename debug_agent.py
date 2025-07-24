import asyncio
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import select, text
from app.database_config import SessionLocal
from app.database_models import Project, Concept
from agent.agent_orchestrator import GitGuideAgent

# Load environment variables
load_dotenv()

async def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    try:
        async with SessionLocal() as session:
            # Test simple query
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Check if there are any projects
            projects = await session.execute(select(Project))
            project_count = len(projects.all())
            print(f"📊 Found {project_count} projects in database")
            
            # Check if there are any concepts
            concepts = await session.execute(select(Concept))
            concept_count = len(concepts.all())
            print(f"📊 Found {concept_count} concepts in database")
            
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_agent_processing():
    """Test agent processing with a sample repository"""
    print("\n🧪 Testing agent processing...")
    
    try:
        agent = GitGuideAgent()
        print(f"✅ Agent initialized. Azure OpenAI configured: {bool(agent.azure_openai_config['api_key'])}")
        
        # Test with a simple repository
        test_repo = "https://github.com/octocat/Hello-World"
        test_project_id = 999  # Fake project ID for testing
        
        print(f"🔍 Testing with repository: {test_repo}")
        
        # Test repository analysis step
        from agent.repository_analyzer import analyze_repository
        
        print("📊 Step 1: Analyzing repository...")
        repo_analysis = await analyze_repository(test_repo, agent.github_token)
        
        if repo_analysis['success']:
            print(f"✅ Repository analysis successful: {repo_analysis['total_files']} files")
        else:
            print(f"❌ Repository analysis failed: {repo_analysis['error']}")
            return False
        
        # Test learning path generation
        from agent.learning_path_generator import generate_learning_path
        
        print("🧠 Step 2: Testing learning path generation...")
        learning_path = await generate_learning_path(
            repo_analysis, 
            "Intermediate", 
            "Full Stack", 
            agent.azure_openai_config
        )
        
        if learning_path['success']:
            print(f"✅ Learning path generation successful: {len(learning_path['concepts'])} concepts")
            print(f"📋 Project overview length: {len(learning_path['project_overview'])} chars")
            return True
        else:
            print(f"❌ Learning path generation failed: {learning_path['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Agent processing error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_background_processing():
    """Test if background processing would work"""
    print("\n⏰ Testing background processing simulation...")
    
    try:
        # Check if we can import background processing function
        from app.routes.agent.agent_utilities import process_project_background
        print("✅ Background processing function imported successfully")
        
        # We won't actually run it with a real project ID since that might interfere with user data
        print("ℹ️  Background processing function is available and should work")
        return True
        
    except Exception as e:
        print(f"❌ Background processing import failed: {e}")
        return False

async def main():
    print("🚀 GitGuide Agent Debug Tool")
    print("=" * 60)
    
    # Test database
    db_ok = await test_database_connection()
    
    # Test agent processing
    agent_ok = await test_agent_processing()
    
    # Test background processing
    bg_ok = await test_background_processing()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print(f"   Database: {'✅ OK' if db_ok else '❌ FAIL'}")
    print(f"   Agent:    {'✅ OK' if agent_ok else '❌ FAIL'}")
    print(f"   Background: {'✅ OK' if bg_ok else '❌ FAIL'}")
    
    if all([db_ok, agent_ok, bg_ok]):
        print("\n🎉 All systems working! The issue might be:")
        print("   1. Frontend not calling the backend correctly")
        print("   2. Authentication/authorization issues")
        print("   3. Background task not being triggered")
        print("   4. Error in specific repository processing")
    else:
        print("\n🚨 Found issues that need to be fixed!")

if __name__ == "__main__":
    asyncio.run(main()) 