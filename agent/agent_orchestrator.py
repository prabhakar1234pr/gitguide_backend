import os
import asyncio
import sys

# Add the parent directory to path to import force_env_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from force_env_loader import force_load_env

# Force load correct environment variables from .env file
force_load_env()

from dotenv import load_dotenv
from .repository_analyzer import analyze_repository
from .learning_path_generator import generate_learning_path
from .api_client import save_learning_content

load_dotenv()

class GitGuideAgent:
    """Main agent orchestrator for GitGuide project analysis and learning path generation"""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        self.azure_openai_config = {
            'api_key': os.getenv('AZURE_OPENAI_KEY'),
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_version': os.getenv('AZURE_OPENAI_API_VERSION'),
            'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT_4_1')
        }
        self.backend_url = "http://localhost:8000"
        print(f"🚀 GitGuideAgent initialized: Azure OpenAI configured: {bool(self.azure_openai_config['api_key'])}")
        
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
        print(f"🎯 Starting processing for project {project_id}: {repo_url}")
        print(f"   Skill Level: {skill_level}, Domain: {domain}")
        
        try:
            # Step 1: Analyze repository
            print("🔍 Step 1: Analyzing repository...")
            repo_analysis = await analyze_repository(repo_url, self.github_token)
            print(f"   Analysis complete: success={repo_analysis['success']}")
            
            if not repo_analysis['success']:
                error_msg = f"Repository analysis failed: {repo_analysis['error']}"
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            print(f"✅ Repository analyzed: {repo_analysis['total_files']} files, {len(repo_analysis['tech_stack'])} technologies")
            
            # Step 2: Generate learning path
            print("🧠 Step 2: Generating personalized learning path...")
            learning_path = await generate_learning_path(
                repo_analysis, 
                skill_level, 
                domain, 
                self.azure_openai_config
            )
            
            if not learning_path['success']:
                return {
                    'success': False,
                    'error': f"Learning path generation failed: {learning_path['error']}"
                }
            
            print(f"🎯 Learning path generated with {len(learning_path['concepts'])} concepts")
            
            # Step 3: Save to database
            print("💾 Step 3: Saving learning content to database...")
            save_result = await save_learning_content(
                project_id,
                learning_path,
                repo_analysis['repo_info']
            )
            
            if not save_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to save learning content: {save_result['error']}"
                }
            
            print(f"✅ GitGuide Agent completed successfully for project {project_id}")
            return {
                'success': True,
                'project_id': project_id,
                'concepts_generated': len(learning_path['concepts']),
                'repo_info': repo_analysis['repo_info']
            }
            
        except Exception as e:
            error_msg = f"Agent processing failed for project {project_id}: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }


# Main processing function (for backward compatibility)
async def process_project(project_id, repo_url, skill_level, domain, user_id):
    """Process a project using GitGuide Agent"""
    agent = GitGuideAgent()
    return await agent.process_new_project(project_id, repo_url, skill_level, domain, user_id)


# Test function for development
async def test_agent():
    """Test the agent with a sample repository"""
    agent = GitGuideAgent()
    
    # Test with a simple public repository
    test_result = await agent.process_new_project(
        project_id=999,
        repo_url="https://github.com/octocat/Hello-World",
        skill_level="Beginner",
        domain="Full Stack",
        user_id="test_user"
    )
    
    print("🧪 Agent Test Result:")
    print(f"Success: {test_result['success']}")
    if test_result['success']:
        print(f"Concepts: {test_result['concepts_generated']}")
        print(f"Repository: {test_result['repo_info']['name']}")
    else:
        print(f"Error: {test_result['error']}")


if __name__ == "__main__":
    print("🧪 Testing GitGuide Agent...")
    asyncio.run(test_agent()) 