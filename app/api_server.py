from fastapi import FastAPI
from app.routes import health_endpoints, project_endpoints, task_endpoints, chat_endpoints, days_endpoints, progress_endpoints
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
    * **📊 Progress Tracking** - Real-time progress monitoring and day unlocking
    * **🔐 Authentication** - Secure user authentication via Clerk
    
    ## New GitGuide Structure
    ```
    Project → Days (14) → Concepts (10/day) → Subconcepts (10/concept) → Tasks (1/subconcept)
    ```
    
    ## Key Features
    * **Brief Project Overview** - Concise 3-page project summaries
    * **100 Tasks per Day** - 10 concepts × 10 subconcepts × 1 task each
    * **Background Content Generation** - AI generates next day content while user learns
    * **GitHub API Verification** - Direct task verification through GitHub
    * **Real-time Progress** - Live tracking of day, concept, and project progress
    
    ## Getting Started
    1. Authenticate with Clerk JWT token in Authorization header
    2. Create a project from a GitHub repository
    3. AI generates brief overview + Day 1 content (Day 2+ generated in background)
    4. Complete Day 0 verification to unlock Day 1
    5. Progress through tasks to unlock subsequent days
    6. Chat with AI assistant for guidance
    """,
    version="3.0.0 - Subconcepts & Progress Edition",
    contact={
        "name": "GitGuide Team",
        "url": "https://github.com/your-repo/gitguide",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Configure CORS - Production ready with environment-based origins
import os
# For debugging - temporarily allow all origins
# TODO: Restrict this to specific domains after fixing the connection
allowed_origins = ["*"]  # Temporarily allow all origins for debugging

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with organized structure
app.include_router(health_endpoints.router, tags=["🏥 Health"])
app.include_router(project_endpoints.router, tags=["📂 Projects"])
app.include_router(days_endpoints.router, tags=["📅 14-Day Progression"])
app.include_router(progress_endpoints.router, tags=["📊 Progress & Day Management"])
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
        "message": "🚀 Welcome to GitGuide API v3.0!",
        "description": "Transform GitHub repositories into personalized 14-day learning journeys with subconcepts",
        "version": "3.0.0 - Subconcepts & Progress Edition",
        "features": [
            "📅 14-day structured learning progression",
            "🧩 10 concepts per day, 10 subconcepts per concept", 
            "🎯 1 task per subconcept (100 tasks/day)",
            "🤖 AI-powered brief overviews and content generation",
            "📊 Real-time progress tracking",
            "🔄 Background day content generation",
            "🔗 GitHub API task verification",
            "💬 Context-aware chat assistant",
            "🔓 Progressive day unlocking system"
        ],
        "structure": "Project → Days (14) → Concepts (10) → Subconcepts (10) → Tasks (1)",
        "docs": "/docs",
        "health": "/ping"
    } 