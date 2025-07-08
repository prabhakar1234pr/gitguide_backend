# GitGuide Backend

A FastAPI-based backend for the GitGuide application that transforms GitHub repositories into personalized learning journeys.

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
    
    project_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    skill_level = Column(String, nullable=False)  # Beginner, Intermediate, Pro
    domain = Column(String, nullable=False)       # Full Stack, ML, etc.
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
- `GET /ping` - Health check

### Users
- `GET /users/{user_id}` - Get user details by Clerk user ID

## 🔐 Authentication

Authentication is handled via Clerk. All project endpoints require valid user authentication tokens passed in the `Authorization` header. 