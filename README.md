# GitGuide Backend

🚀 **FastAPI-powered backend for GitGuide** - Transform GitHub repositories into personalized learning journeys with AI-generated learning paths and context-aware chat assistance.

## 🌟 Overview

GitGuide Backend is a sophisticated AI-powered learning platform that analyzes GitHub repositories and creates personalized, structured learning paths. It combines repository analysis, AI content generation, and interactive tutoring to provide a comprehensive learning experience.

### Key Features

- **🤖 AI Agent System**: Automated learning path generation using Azure OpenAI
- **💬 Smart Chat Assistant**: Context-aware AI tutor with full project understanding
- **📂 Project Management**: Complete GitHub repository analysis and learning path storage
- **✅ Task Management**: Structured learning tasks with progress tracking
- **🔐 Secure Authentication**: JWT-based authentication via Clerk
- **📊 Database**: Async PostgreSQL with SQLAlchemy ORM
- **📝 API Documentation**: Auto-generated Swagger/OpenAPI docs
- **🔄 Regeneration System**: AI-powered content regeneration with custom prompts

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL database
- Azure OpenAI access (for AI features)
- GitHub Personal Access Token
- Clerk account (for authentication)

### Installation

```bash
# Clone and navigate to backend
cd gitguide_backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/gitguide_db

# AI Services
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-04-01-preview
AZURE_OPENAI_DEPLOYMENT_GPT_4_1=your-gpt4-deployment-name
GITHUB_ACCESS_TOKEN=ghp_your_github_token_here

# Authentication
CLERK_SECRET_KEY=sk_your_clerk_secret_key

# Optional: Development settings
DEBUG=True
LOG_LEVEL=INFO
```

### Database Setup

```bash
# Apply database migrations
python migrate_database.py

# Verify setup
python -c "from app.database_config import engine; print('✅ Database connected!')"
```

### Run the Server

```bash
# Start development server
uvicorn app.api_server:app --reload --host 0.0.0.0 --port 8000

# Server will be available at:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Redoc: http://localhost:8000/redoc
```

---

## 🏗️ Architecture

### Clean & Modular Structure

```
gitguide_backend/
├── app/                              # FastAPI Application
│   ├── api_server.py                # FastAPI app server & route configuration
│   ├── database_models.py           # SQLAlchemy database schema definitions
│   ├── database_config.py           # Database connection configuration
│   └── routes/                      # API Endpoints (organized by purpose)
│       ├── health_endpoints.py     # Health check endpoints (/ping)
│       ├── project_endpoints.py    # Project CRUD API endpoints
│       ├── task_endpoints.py       # Task management API endpoints
│       ├── chat_endpoints.py       # AI chat assistant API endpoints
│       ├── auth/                    # Authentication Module
│       │   ├── __init__.py
│       │   └── auth_utilities.py   # JWT token processing & Clerk integration
│       ├── agent/                   # AI Agent Endpoints
│       │   ├── __init__.py
│       │   ├── core_endpoints.py   # Core agent endpoints (process, status, health)
│       │   ├── regeneration_endpoints.py # Learning path regeneration endpoints
│       │   └── agent_utilities.py  # Agent database operations & helpers
│       └── shared/                  # Shared Utilities
│           ├── __init__.py
│           ├── logging_and_paths.py # Logging configuration & path setup
│           └── database_utilities.py # Database session patterns & utilities
├── agent/                           # AI Agent System
│   ├── __init__.py
│   ├── agent_orchestrator.py       # Main agent orchestrator & processing logic
│   ├── repository_analyzer.py      # GitHub API integration & repo analysis
│   ├── learning_path_generator.py  # Azure OpenAI integration & content generation
│   └── api_client.py               # Backend database integration
├── prompts/                         # LLM Prompt Templates
│   ├── __init__.py
│   ├── learning_path_prompts.py    # Learning path generation prompts
│   └── chat_prompts.py             # Chat assistant prompts
├── migrate_database.py             # Database migration & schema management
├── requirements.txt                # Python dependencies
└── README.md                       # This comprehensive documentation
```

### Naming Convention Benefits

- **Crystal Clear Purposes**: Every file name immediately tells you its function
- **Zero Name Conflicts**: No duplicate file names across the entire codebase
- **Intuitive Navigation**: `*_endpoints.py` for APIs, `*_utilities.py` for helpers, `*_config.py` for configuration
- **Easy Maintenance**: Find functionality by logical file names with clear separation of concerns

---

## 📊 Complete API Reference

### 🏥 Health & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message with API information |
| `GET` | `/ping` | Health check endpoint |
| `GET` | `/agent/health` | AI Agent service health check |
| `GET` | `/chat/health` | Chat service health check |

### 📂 Project Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/projects` | Create new learning project from GitHub repo | ✅ |
| `GET` | `/projects` | Get user's projects with metadata | ✅ |
| `GET` | `/projects/{project_id}` | Get specific project details | ✅ |
| `DELETE` | `/projects/{project_id}` | Delete project (cascade deletes all content) | ✅ |
| `GET` | `/projects/{project_id}/concepts` | Get AI-generated learning path | ✅ |

### ✅ Task Management  

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/tasks` | Create new learning task | ✅ |
| `GET` | `/projects/{project_id}/tasks` | Get all tasks for project (ordered) | ✅ |
| `PUT` | `/tasks/{task_id}` | Update task (title, description, status, order) | ✅ |
| `DELETE` | `/tasks/{task_id}` | Delete specific task | ✅ |

### 🤖 AI Agent

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/agent/process` | Trigger AI learning path generation | ✅ |
| `GET` | `/agent/status/{project_id}` | Check processing status | ✅ |

### 🔄 AI Regeneration

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/agent/regenerate/project-overview` | Regenerate project overview with custom prompt | ✅ |
| `POST` | `/agent/regenerate/whole-path` | Regenerate entire learning path | ✅ |
| `POST` | `/agent/regenerate/concept` | Regenerate specific concept | ✅ |
| `POST` | `/agent/regenerate/subtopic` | Regenerate specific subtopic | ✅ |
| `POST` | `/agent/regenerate/task` | Regenerate specific task | ✅ |

### 💬 AI Chat Assistant

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/chat/project/{project_id}` | Chat with context-aware AI tutor | ✅ |
| `GET` | `/chat/project/{project_id}/context` | Get available chat context | ✅ |

### 👤 User Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/users/{user_id}` | Get user details from Clerk | ✅ |

---

## 🗃️ Database Schema

### Core Tables

#### Projects
```python
class Project(Base):
    project_id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)           # Clerk user ID
    repo_url = Column(String, nullable=False)          # GitHub repository URL
    skill_level = Column(String, nullable=False)       # Beginner/Intermediate/Pro
    domain = Column(String, nullable=False)            # Full Stack/ML/etc.
    project_overview = Column(Text, nullable=True)     # AI-generated overview
    repo_name = Column(String, nullable=True)          # Repository name
    tech_stack = Column(Text, nullable=True)           # JSON: detected technologies
    is_processed = Column(Boolean, default=False)      # Agent processing status
```

#### Concepts (Learning Path Structure)
```python
class Concept(Base):
    concept_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    concept_external_id = Column(String, nullable=False)  # e.g., "concept-0"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False)
```

#### Subtopics
```python
class Subtopic(Base):
    subtopic_id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"))
    subtopic_external_id = Column(String, nullable=False)  # e.g., "subtopic-0-0"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False)
```

#### Tasks
```python
class Task(Base):
    task_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    subtopic_id = Column(Integer, ForeignKey("subtopics.subtopic_id"))
    task_external_id = Column(String, nullable=True)    # e.g., "task-0-0-0"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.not_started)
    order = Column(Integer, nullable=False)
    difficulty = Column(String, nullable=True)           # easy/medium/hard
    files_to_study = Column(Text, nullable=True)         # JSON: array of file paths
    is_unlocked = Column(Boolean, default=False)
```

### Task Status Flow
```python
class TaskStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
```

### Database Management

```bash
# Apply migrations
python migrate_database.py

# Reset database (development only)
python migrate_database.py --rollback
# You'll be prompted to type 'CONFIRM'
```

---

## 🤖 AI Agent System

### How It Works

1. **Repository Analysis** (`repository_analyzer.py`)
   - Fetches GitHub repository structure via GitHub API
   - Extracts key files (README, package.json, requirements.txt, etc.)
   - Analyzes technology stack and project structure
   - Filters relevant files and content

2. **Learning Path Generation** (`learning_path_generator.py`)
   - Prepares repository context for LLM consumption
   - Uses Azure OpenAI with specialized prompts
   - Generates hierarchical learning structure: Project Overview → Concepts → Subtopics → Tasks
   - Applies progressive unlocking logic

3. **Content Storage** (`agent_orchestrator.py`)
   - Saves generated content to PostgreSQL database
   - Maintains relationships between concepts, subtopics, and tasks
   - Updates project processing status

### AI Models & Performance

- **Model**: GPT-4 (Azure OpenAI)
- **Learning Path Generation**: 4000 max tokens, 10-60 seconds
- **Chat Responses**: 1000 max tokens, 1-3 seconds
- **Repository Support**: Up to 200+ files per repository
- **Cost Optimization**: Intelligent prompt design minimizes API usage

### Regeneration System

The regeneration system allows users to customize any part of their learning path:

- **Project Overview**: Regenerate with custom focus or style
- **Whole Learning Path**: Complete restructuring with user guidance
- **Individual Concepts**: Targeted improvements to specific learning areas
- **Subtopics & Tasks**: Fine-grained customization of learning components

---

## 🔐 Authentication & Security

### Clerk Integration

Authentication is handled via [Clerk](https://clerk.dev) with JWT tokens:

1. **Frontend**: User authenticates with Clerk
2. **Token**: Clerk issues JWT token to client
3. **Backend**: Extracts user ID from JWT for all authenticated endpoints
4. **Authorization**: Users can only access their own projects and data

### Security Features

- **User Isolation**: Strict user-project ownership verification
- **Input Validation**: Pydantic models validate all API inputs
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Error Handling**: Sanitized error responses (no sensitive data leakage)

### Authentication Flow

```python
# Extract user from JWT token
user_id = extract_user_id_from_token(authorization_header)

# Verify project ownership
project = await verify_project_ownership(project_id, user_id, session)

# Proceed with authorized operation
```

---

## 🛠️ Development Workflow

### Code Organization

- **Modular Design**: Each file has a single, clear responsibility
- **Shared Utilities**: Common patterns extracted into shared modules
- **Type Safety**: Pydantic models for API validation
- **Async/Await**: Full async support for database and external API calls

### Development Commands

```bash
# Start development server with auto-reload
uvicorn app.api_server:app --reload --host 0.0.0.0 --port 8000

# Test database models
python -c "from app.database_models import Base; print('✅ Models import successfully')"

# Test agent system
python -c "from agent.agent_orchestrator import GitGuideAgent; print('✅ Agent imports successfully')"

# Check API endpoints
curl http://localhost:8000/ping
curl http://localhost:8000/agent/health
curl http://localhost:8000/chat/health
```

### Testing & Debugging

```bash
# View API documentation
open http://localhost:8000/docs

# Test agent processing
python agent/agent_orchestrator.py

# Database queries
python migrate_database.py
```

---

## 🌐 Deployment

### Environment Variables

Production environment requires:

```env
# Database (Required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# AI Services (Required)
AZURE_OPENAI_KEY=your_key...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-04-01-preview
AZURE_OPENAI_DEPLOYMENT_GPT_4_1=your-deployment-name
GITHUB_ACCESS_TOKEN=ghp_...

# Authentication (Required)
CLERK_SECRET_KEY=sk_...

# Optional: Production settings
DEBUG=False
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://yourdomain.com"]
```

### Production Deployment

```bash
# Install production dependencies
pip install -r requirements.txt

# Apply database migrations
python migrate_database.py

# Start production server
uvicorn app.api_server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Support

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📋 API Usage Examples

### Create and Process Project

```python
import httpx

# 1. Create project
response = httpx.post("http://localhost:8000/projects", 
    json={
        "repo_url": "https://github.com/user/repo",
        "skill_level": "Intermediate", 
        "domain": "Full Stack"
    },
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
project = response.json()

# 2. Trigger AI processing
httpx.post("http://localhost:8000/agent/process",
    json={"project_id": project["project_id"]},
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

# 3. Check status
status = httpx.get(f"http://localhost:8000/agent/status/{project['project_id']}",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

# 4. Get learning path
concepts = httpx.get(f"http://localhost:8000/projects/{project['project_id']}/concepts",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
```

### Chat with AI Assistant

```python
# Send message to AI tutor
response = httpx.post(f"http://localhost:8000/chat/project/{project_id}",
    json={"message": "How do I implement user authentication in this project?"},
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
ai_response = response.json()["response"]
```

### Regenerate Content

```python
# Regenerate project overview with custom prompt
httpx.post("http://localhost:8000/agent/regenerate/project-overview",
    json={
        "project_id": project_id,
        "user_prompt": "Focus more on advanced patterns and best practices"
    },
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
```

---

## 🔧 Configuration

### Logging

Logging is configured in `app/routes/shared/logging_and_paths.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Database Connection

Database configuration in `app/database_config.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession)
```

### CORS Configuration

CORS settings in `app/api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🤝 Contributing

1. Follow the established file naming conventions
2. Each file should have a single, clear responsibility
3. Use async/await for all database and external API operations
4. Add proper error handling and logging
5. Update this README for any new features or changes

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🆘 Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the health endpoints for service status
3. Check logs for detailed error information
4. Ensure all environment variables are properly configured

**Made with ❤️ for developers who want to learn from real-world codebases** 