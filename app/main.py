from fastapi import FastAPI
from app.routes import ping, projects, tasks, agent, chat
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app with enhanced metadata for better Swagger documentation
app = FastAPI(
    title="GitGuide API",
    description="""
    🚀 **GitGuide Backend API** - Transform GitHub repositories into personalized learning journeys!
    
    ## Features
    * **📂 Project Management** - Create and manage learning projects from GitHub repos
    * **🤖 AI Agent** - Automated learning path generation using advanced LLM technology
    * **💬 Chat Assistant** - Context-aware AI tutor for personalized guidance
    * **✅ Task Management** - Structured learning tasks with progress tracking
    * **🔐 Authentication** - Secure user authentication via Clerk
    
    ## Getting Started
    1. Authenticate with Clerk JWT token in Authorization header
    2. Create a project from a GitHub repository
    3. Trigger AI agent to generate learning path
    4. Chat with AI assistant for guidance
    """,
    version="1.0.0",
    contact={
        "name": "GitGuide Team",
        "email": "support@gitguide.dev",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Allow frontend (Next.js on Vercel) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with organized structure
app.include_router(ping.router, tags=["🏥 Health"])
app.include_router(projects.router, tags=["📂 Projects"])
app.include_router(tasks.router, tags=["✅ Tasks"])
app.include_router(agent.router, tags=["🤖 AI Agent"])
app.include_router(chat.router, tags=["💬 Chat Assistant"])

@app.get("/", 
    tags=["🏠 Welcome"],
    summary="API Welcome",
    description="Welcome endpoint with basic API information and links to documentation",
    response_description="Welcome message and API details"
)
def root():
    return {
        "message": "🚀 Welcome to GitGuide API!",
        "description": "Transform GitHub repositories into personalized learning journeys",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/ping"
    }
