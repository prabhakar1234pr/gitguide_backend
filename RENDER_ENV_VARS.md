# Environment Variables for Render Deployment

Add these environment variables in your Render dashboard:

## Required Variables:

```
DATABASE_URL=your_neon_database_url_here

AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_API_VERSION=2024-04-01-preview
AZURE_OPENAI_DEPLOYMENT_GPT_4_1=your_gpt4_deployment_name
AZURE_OPENAI_TIMEOUT=180

CLERK_SECRET_KEY=sk_your_clerk_secret_key_here

GITHUB_ACCESS_TOKEN=ghp_your_github_token_here

GROQ_API_KEY=gsk_your_groq_api_key_here

OPENAI_API_KEY=sk-your_openai_api_key_here

# Production Settings
DEBUG=False
LOG_LEVEL=INFO
FRONTEND_URL=https://gitguidefrontend.vercel.app
```

## Instructions:
1. In Render dashboard → Your Service → Environment
2. Add each variable above
3. Click "Save Changes"
4. Render will automatically redeploy
