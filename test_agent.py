import asyncio
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

async def test_groq_api():
    """Test if Groq API is working"""
    groq_api_key = os.getenv('GROQ_API_KEY')
    print(f"🔑 GROQ_API_KEY present: {bool(groq_api_key)}")
    print(f"🔑 Key preview: {groq_api_key[:20] if groq_api_key else 'None'}...")
    
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment")
        return
    
    try:
        print("\n🧪 Testing Groq API...")
        client = Groq(api_key=groq_api_key, timeout=30.0)
        
        # Simple test prompt
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": "Say 'Hello, GitGuide!' in 5 words or less."}],
            temperature=0.7,
            max_tokens=50,
            timeout=30.0
        )
        
        print(f"✅ Groq API Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Groq API Error: {type(e).__name__}: {str(e)}")

async def test_agent():
    """Test the GitGuide agent"""
    try:
        from agent.agent_orchestrator import GitGuideAgent
        print("\n🧪 Testing GitGuide Agent...")
        
        agent = GitGuideAgent()
        print(f"✅ Agent initialized. Groq API key present: {bool(agent.groq_api_key)}")
        
    except Exception as e:
        print(f"❌ Agent Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 GitGuide Agent Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_groq_api())
    asyncio.run(test_agent()) 