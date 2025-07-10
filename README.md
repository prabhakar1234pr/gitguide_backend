# GitGuide Backend

A FastAPI-based backend for the GitGuide application that transforms GitHub repositories into personalized learning journeys with sequential tasks.

## 🗃️ Database Setup

### Prerequisites
- PostgreSQL database (we recommend [Neon](https://neon.tech) for cloud hosting)
- Python 3.8+

### Environment Configuration
Create a `.env` file in the backend directory:
```env
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
ENVIRONMENT=development
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key_here
```

### Database Schema Management

#### Create Tables
```bash
# Create all database tables
python create_tables.py

# Output:
# 🗃️ Creating database tables...
# ✅ Database tables created successfully!
# 📋 Tables created:
#   - projects
#   - tasks
```

#### Reset Database (Development Only)
```bash
# Drop and recreate all tables
python create_tables.py --drop
```

### Schema Overview

#### Projects Table
```python
class Project(Base):
    __tablename__ = "projects"
    
    project_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    skill_level = Column(String, nullable=False)  # Beginner, Intermediate, Pro
    domain = Column(String, nullable=False)       # Full Stack, ML, etc.
    
    # Relationship to tasks
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
```

#### Tasks Table
```python
class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(BigInteger, primary_key=True, index=True)
    project_id = Column(BigInteger, ForeignKey("projects.project_id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.not_started, nullable=False)
    order = Column(Integer, nullable=False)  # For sequential display
    
    # Relationship back to project
    project = relationship("Project", back_populates="tasks")
```

#### Task Status Enum
```python
class TaskStatus(enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    done = "done"
```

## 🚀 Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python create_tables.py

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🏗️ Architecture

- **FastAPI**: Modern async web framework
- **SQLAlchemy**: Async ORM for database operations
- **PostgreSQL**: Production-ready relational database
- **Pydantic**: Data validation and serialization
- **Clerk**: Authentication and user management

## 📊 API Endpoints

### Projects
- `POST /projects` - Create a new learning project
- `GET /projects` - Get user's projects with user details
- `GET /projects/{project_id}` - Get a specific project by ID
- `DELETE /projects/{project_id}` - Delete a project (cascade deletes all tasks)

### Tasks
- `POST /tasks` - Create a new task for a project
- `GET /projects/{project_id}/tasks` - Get all tasks for a project (ordered sequentially)
- `PUT /tasks/{task_id}` - Update a task (title, description, status, order)
- `DELETE /tasks/{task_id}` - Delete a task

### Users
- `GET /users/{user_id}` - Get user details by Clerk user ID

### System
- `GET /ping` - Health check endpoint

## 🔐 Authentication

Authentication is handled via Clerk. All project and task endpoints require valid user authentication tokens passed in the `Authorization` header.

## 📝 Project & Task Management Features

### Project Management
- **Full CRUD Operations**: Create, read, update, delete projects
- **User Isolation**: Users can only access their own projects
- **Repository Integration**: Links to GitHub repositories
- **Skill Level Tracking**: Beginner, Intermediate, Pro levels
- **Domain Classification**: Full Stack, ML, Data Science, Mobile App, etc.
- **Cascade Deletion**: Deleting a project removes all associated tasks

### Task Management
- **Sequential Learning**: Tasks are ordered for step-by-step learning
- **Progress Tracking**: Status tracking (not_started → in_progress → done)
- **Project-Linked**: Tasks belong to specific projects
- **User Security**: Users can only access their own project tasks
- **Flexible Ordering**: Tasks can be reordered for optimal learning flow

## 🔄 Data Types & Constraints

- **BigInteger IDs**: Supports large ID values for scalability
- **Enum Status**: Strict task status validation
- **Foreign Key Constraints**: Ensures data integrity
- **Cascade Operations**: Automatic cleanup of related data 