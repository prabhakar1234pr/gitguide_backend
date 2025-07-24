import asyncio
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Force load correct environment variables from .env file
from force_env_loader import force_load_env
force_load_env()

# Load environment variables
load_dotenv()

async def test_azure_openai_api():
    """Test if Azure OpenAI API is working"""
    azure_openai_key = os.getenv('AZURE_OPENAI_KEY')
    azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_openai_version = os.getenv('AZURE_OPENAI_API_VERSION')
    azure_openai_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT_4_1')
    
    print(f"🔑 AZURE_OPENAI_KEY present: {bool(azure_openai_key)}")
    print(f"🔗 AZURE_OPENAI_ENDPOINT: {azure_openai_endpoint}")
    print(f"🔢 AZURE_OPENAI_API_VERSION: {azure_openai_version}")
    print(f"🚀 AZURE_OPENAI_DEPLOYMENT: {azure_openai_deployment}")
    
    if not azure_openai_key or not azure_openai_endpoint:
        print("❌ Azure OpenAI configuration incomplete")
        return
    
    try:
        print("\n🧪 Testing Azure OpenAI API...")
        client = AzureOpenAI(
            api_key=azure_openai_key,
            azure_endpoint=azure_openai_endpoint,
            api_version=azure_openai_version
        )
        
        # Simple test prompt
        response = client.chat.completions.create(
            model=azure_openai_deployment,
            messages=[{"role": "user", "content": "Say 'Hello, GitGuide!' in 5 words or less."}],
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ Azure OpenAI Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Azure OpenAI Error: {type(e).__name__}: {str(e)}")

async def test_agent():
    """Test the GitGuide agent"""
    try:
        from agent.agent_orchestrator import GitGuideAgent
        print("\n🧪 Testing GitGuide Agent...")
        
        agent = GitGuideAgent()
        print(f"✅ Agent initialized. Azure OpenAI configured: {bool(agent.azure_openai_config['api_key'])}")
        
    except Exception as e:
        print(f"❌ Agent Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 GitGuide Agent Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_azure_openai_api())
    asyncio.run(test_agent()) 