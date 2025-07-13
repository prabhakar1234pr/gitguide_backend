import os
import asyncio
from dotenv import load_dotenv
from .repository_analyzer import analyze_repository
from .learning_path_generator import generate_learning_path
from .api_client import save_learning_content

load_dotenv()

class GitGuideAgent:
    """Main agent orchestrator for GitGuide project analysis and learning path generation"""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.backend_url = "http://localhost:8000"
        
    async def process_new_project(self, project_id, repo_url, skill_level, domain, user_id):
        """
        Main function to process a new project
        
        Args:
            project_id: Database project ID
            repo_url: GitHub repository URL
            skill_level: User's skill level (Beginner, Intermediate, Pro)
            domain: Project domain (Full Stack, ML, etc.)
            user_id: Clerk user ID
        
        Returns:
            dict: Processing result
        """
        try:
            print(f"🚀 Processing project {project_id}")
            print(f"📦 Repository: {repo_url}")
            print(f"👤 User: {user_id} | Skill: {skill_level} | Domain: {domain}")
            
            # Step 1: Analyze repository
            print("\n📊 Step 1: Analyzing repository...")
            repo_analysis = await analyze_repository(repo_url, self.github_token)
            
            if not repo_analysis['success']:
                return {
                    'success': False, 
                    'error': f"Repository analysis failed: {repo_analysis['error']}"
                }
            
            print(f"✅ Repository analyzed: {len(repo_analysis['files'])} files found")
            
            # Step 2: Generate learning path
            print("\n🎯 Step 2: Generating learning path...")
            learning_path = await generate_learning_path(
                repo_analysis=repo_analysis,
                skill_level=skill_level,
                domain=domain,
                groq_api_key=self.groq_api_key
            )
            
            if not learning_path['success']:
                return {
                    'success': False,
                    'error': f"Learning path generation failed: {learning_path['error']}"
                }
            
            print(f"✅ Learning path generated:")
            print(f"   📚 Concepts: {len(learning_path['concepts'])}")
            print(f"   📖 Total subtopics: {sum(len(c['subtopics']) for c in learning_path['concepts'])}")
            print(f"   ✏️ Total tasks: {sum(sum(len(st['tasks']) for st in c['subtopics']) for c in learning_path['concepts'])}")
            
            # Step 3: Save to database
            print("\n💾 Step 3: Saving to database...")
            save_result = await save_learning_content(
                project_id=project_id,
                learning_path=learning_path,
                backend_url=self.backend_url,
                user_id=user_id
            )
            
            if not save_result['success']:
                return {
                    'success': False,
                    'error': f"Database save failed: {save_result['error']}"
                }
            
            print("✅ Learning content saved to database")
            print(f"🎉 Project {project_id} processing completed successfully!")
            
            return {
                'success': True,
                'project_id': project_id,
                'concepts_count': len(learning_path['concepts']),
                'project_overview': learning_path['project_overview']
            }
            
        except Exception as e:
            print(f"❌ Agent processing failed: {str(e)}")
            return {
                'success': False,
                'error': f"Agent processing failed: {str(e)}"
            }

# Convenience function for direct calls
async def process_project(project_id, repo_url, skill_level, domain, user_id):
    """Convenience function to process a project"""
    agent = GitGuideAgent()
    return await agent.process_new_project(project_id, repo_url, skill_level, domain, user_id)

# Test function
async def test_agent():
    """Test the agent with a sample repository"""
    result = await process_project(
        project_id=999,
        repo_url="https://github.com/vercel/next.js",
        skill_level="Intermediate",
        domain="Full Stack",
        user_id="test_user_123"
    )
    print(f"\n🧪 Test Result: {result}")

if __name__ == "__main__":
    print("🤖 GitGuide Agent Starting...")
    asyncio.run(test_agent()) 