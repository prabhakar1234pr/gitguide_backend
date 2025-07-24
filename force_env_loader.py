"""
Force Environment Loader - Overrides system environment variables with .env file values
This ensures .env file takes precedence over Windows system environment variables
"""

import os
from dotenv import load_dotenv

def force_load_env():
    """Force load .env file and override system environment variables"""
    print("🔄 Force loading environment variables from .env file...")
    
    # Load .env file into a dictionary first
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Force override system environment variables
    azure_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_KEY', 
        'AZURE_OPENAI_API_VERSION',
        'AZURE_OPENAI_DEPLOYMENT_GPT_4_1'
    ]
    
    overridden = []
    for var in azure_vars:
        if var in env_vars:
            old_value = os.environ.get(var, 'None')
            os.environ[var] = env_vars[var]
            if old_value != env_vars[var]:
                overridden.append(f"{var}: {old_value[:30]}... → {env_vars[var][:30]}...")
            print(f"✅ {var} = {env_vars[var][:50]}...")
    
    if overridden:
        print(f"🔧 Overridden {len(overridden)} system variables with .env values")
    
    # Also load normally for other variables
    load_dotenv(override=True)
    
    return env_vars

if __name__ == "__main__":
    force_load_env()
    print(f"\n🔍 Current Azure OpenAI config:")
    print(f"ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    print(f"DEPLOYMENT: {os.getenv('AZURE_OPENAI_DEPLOYMENT_GPT_4_1')}")
    print(f"KEY: {os.getenv('AZURE_OPENAI_KEY')[:20]}..." if os.getenv('AZURE_OPENAI_KEY') else "None") 