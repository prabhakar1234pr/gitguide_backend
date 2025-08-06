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
from .learning_path_generator import generate_learning_path, generate_day_content
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
            'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT_4_1'),
            'timeout': float(os.getenv('AZURE_OPENAI_TIMEOUT', '120'))  # Default 120 seconds
        }
        self.backend_url = "http://localhost:8000"
        print(f"🚀 GitGuideAgent initialized: Azure OpenAI configured: {bool(self.azure_openai_config['api_key'])}")
        
    async def process_new_project(self, project_id, repo_url, skill_level, domain, user_id):
        """
        Main function to process a new project
        Creates brief project overview and Day 0 content, then starts background generation for Day 1
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
            # Step 2: Generate brief project overview and Day 0 content
            print("🧠 Step 2: Generating brief project overview and Day 0 content...")
            day_0_content = await generate_day_content(
                repo_analysis,
                0,  # Day 0
                skill_level,
                domain,
                None,  # No project overview for Day 0
                self.azure_openai_config
            )
            if not day_0_content['success']:
                return {
                    'success': False,
                    'error': f"Day 0 generation failed: {day_0_content['error']}"
                }
            print(f"🎯 Day 0 content generated with {len(day_0_content['concepts'])} concepts")
            # Step 3: Save initial content to database (Day 0 only)
            print("💾 Step 3: Saving Day 0 content to database...")
            save_result = await save_learning_content(
                project_id,
                {
                    'project_overview': '',  # No overview for Day 0
                    'day_0_concepts': day_0_content['concepts']
                },
                repo_analysis['repo_info']
            )
            if not save_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to save Day 0 content: {save_result['error']}"
                }
            # Step 4: Start background generation for Day 1 (don't wait for completion)
            print("🔄 Step 4: Starting background generation for Day 1...")
            asyncio.create_task(self.generate_next_day_background(
                project_id, 1, repo_analysis, skill_level, domain, ''
            ))
            print(f"✅ GitGuide Agent completed initial setup for project {project_id}")
            return {
                'success': True,
                'project_id': project_id,
                'day_0_concepts_generated': len(day_0_content['concepts']),
                'repo_info': repo_analysis['repo_info'],
                'day_1_generation_started': True
            }
        except Exception as e:
            error_msg = f"Agent processing failed for project {project_id}: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

    async def generate_next_day_background(self, project_id, day_number, repo_analysis, skill_level, domain, project_overview):
        """
        Generate content for a specific day in the background
        Called when user is progressing through days
        
        Args:
            project_id: Database project ID
            day_number: Day number to generate (1-14)
            repo_analysis: Repository analysis data
            skill_level: User's skill level
            domain: Project domain
            project_overview: Brief project overview for context
        """
        try:
            print(f"🔄 Background: Starting Day {day_number} content generation for project {project_id}")
            
            # Generate day-specific content
            day_content = await generate_day_content(
                repo_analysis,
                day_number,
                skill_level,
                domain,
                project_overview,
                self.azure_openai_config
            )
            
            if not day_content['success']:
                print(f"❌ Background: Day {day_number} generation failed: {day_content['error']}")
                return
            
            print(f"🎯 Background: Day {day_number} content generated with {len(day_content['concepts'])} concepts")
            
            # Save day content to database
            save_result = await save_learning_content(
                project_id,
                {
                    f'day_{day_number}_concepts': day_content['concepts']
                },
                {}  # No repo info needed for day content
            )
            
            if not save_result['success']:
                print(f"❌ Background: Failed to save Day {day_number} content: {save_result['error']}")
                return
            
            print(f"✅ Background: Day {day_number} content saved successfully")
            
            # If this isn't the last day, start generating the next day
            if day_number < 14:
                next_day = day_number + 1
                print(f"🔄 Background: Scheduling Day {next_day} generation...")
                # Add a small delay to prevent overwhelming the API
                await asyncio.sleep(5)
                asyncio.create_task(self.generate_next_day_background(
                    project_id, next_day, repo_analysis, skill_level, domain, project_overview
                ))
            else:
                print(f"🏁 Background: All days generated for project {project_id}")
                
        except Exception as e:
            print(f"❌ Background Day {day_number} generation error: {str(e)}")

    async def generate_day_on_demand(self, project_id, day_number, repo_analysis, skill_level, domain, project_overview):
        """
        Generate content for a specific day on-demand (when user is about to unlock it)
        
        Args:
            project_id: Database project ID
            day_number: Day number to generate
            repo_analysis: Repository analysis data
            skill_level: User's skill level
            domain: Project domain
            project_overview: Brief project overview for context
            
        Returns:
            dict: Generation result
        """
        try:
            print(f"⚡ On-demand: Generating Day {day_number} content for project {project_id}")
            
            # Generate day-specific content
            day_content = await generate_day_content(
                repo_analysis,
                day_number,
                skill_level,
                domain,
                project_overview,
                self.azure_openai_config
            )
            
            if not day_content['success']:
                return {
                    'success': False,
                    'error': f"Day {day_number} generation failed: {day_content['error']}"
                }
            
            print(f"🎯 On-demand: Day {day_number} content generated with {len(day_content['concepts'])} concepts")
            
            # Save day content to database
            save_result = await save_learning_content(
                project_id,
                {
                    f'day_{day_number}_concepts': day_content['concepts']
                },
                {}  # No repo info needed for day content
            )
            
            if not save_result['success']:
                return {
                    'success': False,
                    'error': f"Failed to save Day {day_number} content: {save_result['error']}"
                }
            
            print(f"✅ On-demand: Day {day_number} content generated and saved")
            return {
                'success': True,
                'day_number': day_number,
                'concepts_generated': len(day_content['concepts'])
            }
            
        except Exception as e:
            error_msg = f"On-demand Day {day_number} generation failed: {str(e)}"
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
        print(f"Day 1 Concepts: {test_result['day_1_concepts_generated']}")
        print(f"Repository: {test_result['repo_info']['name']}")
        print(f"Project Overview: {test_result['project_overview_generated']}")
        print(f"Day 2 Started: {test_result['day_2_generation_started']}")
    else:
        print(f"Error: {test_result['error']}")


if __name__ == "__main__":
    print("🧪 Testing GitGuide Agent...")
    asyncio.run(test_agent()) 