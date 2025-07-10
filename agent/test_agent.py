import requests
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def test_github_api():
    """Test if GitHub token works"""
    token = os.getenv('GITHUB_ACCESS_TOKEN')
    if not token:
        print("❌ GITHUB_ACCESS_TOKEN not found in .env")
        return False
    
    print(f"🔍 Using GitHub token: {token[:10]}...")
        
    url = "https://api.github.com/repos/facebook/react"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    print(f"GitHub API: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ GitHub API working!")
        repo_data = response.json()
        print(f"📦 Repo: {repo_data['full_name']} - {repo_data['description'][:50]}...")
        return True
    elif response.status_code == 401:
        print("❌ GitHub API 401: Invalid token. Check your GitHub token.")
        print("💡 Make sure token starts with 'ghp_' and has 'public_repo' scope")
        return False
    else:
        print(f"❌ GitHub API failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_groq_api():
    """Test if Groq API key works"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env")
        return False
    
    print(f"🔍 Using Groq key: {api_key[:10]}...")
        
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Fast and free model
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10
        )
        print("✅ Groq API working!")
        print(f"🤖 Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print("❌ Groq API Error:", e)
        print("💡 Check if your API key starts with 'gsk_'")
        return False

if __name__ == "__main__":
    print("🧪 Testing APIs...")
    print("=" * 50)
    
    github_ok = test_github_api()
    print("-" * 30)
    groq_ok = test_groq_api()
    print("=" * 50)
    
    if github_ok and groq_ok:
        print("🎉 All APIs working! Ready to build agent.")
        print("💡 Using Groq (free) for development")
    else:
        print("❌ Fix the failing APIs first.")
        print("\n🔧 Next steps:")
        if not github_ok:
            print("1. Check your GitHub token in .env file")
            print("2. Make sure it starts with 'ghp_'")
            print("3. Verify it has 'public_repo' scope")
        if not groq_ok:
            print("1. Get free Groq API key from console.groq.com")
            print("2. Add GROQ_API_KEY to .env file") 
            print("3. Make sure it starts with 'gsk_'")