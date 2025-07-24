from fastapi import FastAPI
from app.routes import health_endpoints, project_endpoints, task_endpoints, chat_endpoints, days_endpoints
from app.routes.agent.core_endpoints import router as core_endpoints_router
from app.routes.agent.regeneration_endpoints import router as regeneration_endpoints_router
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app with enhanced metadata for better Swagger documentation
app = FastAPI(
    title="GitGuide API",
    description="""
    🚀 **GitGuide Backend API** - Transform GitHub repositories into personalized 14-day learning journeys!
    
    ## Features
    * **📂 Project Management** - Create and manage learning projects from GitHub repos
    * **📅 14-Day Progression** - Structured learning across 14 days with unlocking progression
    * **🤖 AI Agent** - Automated learning path generation using advanced LLM technology
    * **💬 Chat Assistant** - Context-aware AI tutor for personalized guidance
    * **✅ Task Management** - Structured learning tasks with progress tracking
    * **🔐 Authentication** - Secure user authentication via Clerk
    
    ## Learning Hierarchy
    ```
    Project → Days (14) → Concepts → Subtopics → Tasks
    ```
    
    ## Getting Started
    1. Authenticate with Clerk JWT token in Authorization header
    2. Create a project from a GitHub repository
    3. Trigger AI agent to generate learning path (auto-creates 14 days)
    4. Progress through Day 1 (unlocked) to unlock subsequent days
    5. Chat with AI assistant for guidance
    """,
    version="2.0.0 - Days Edition",
    contact={
        "name": "GitGuide Team",
        "url": "https://github.com/your-repo/gitguide",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with organized structure
app.include_router(health_endpoints.router, tags=["🏥 Health"])
app.include_router(project_endpoints.router, tags=["📂 Projects"])
app.include_router(days_endpoints.router, tags=["📅 14-Day Progression"])
app.include_router(task_endpoints.router, tags=["✅ Tasks"])
app.include_router(core_endpoints_router, tags=["🤖 AI Agent - Core"])
app.include_router(regeneration_endpoints_router, tags=["🔄 AI Agent - Regeneration"])
app.include_router(chat_endpoints.router, tags=["💬 Chat Assistant"])

@app.get("/", 
    tags=["🏠 Welcome"],
    summary="API Welcome",
    description="Welcome endpoint with basic API information and links to documentation",
    response_description="Welcome message and API details"
)
def root():
    return {
        "message": "🚀 Welcome to GitGuide API!",
        "description": "Transform GitHub repositories into personalized 14-day learning journeys",
        "version": "2.0.0 - Days Edition",
        "features": [
            "📅 14-day structured learning progression",
            "🤖 AI-powered learning path generation", 
            "💬 Context-aware chat assistant",
            "🔓 Progressive day unlocking system"
        ],
        "hierarchy": "Project → Days (14) → Concepts → Subtopics → Tasks",
        "docs": "/docs",
        "health": "/ping"
    } 