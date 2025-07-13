# GitGuide Agent 🤖

AI-powered repository analysis and personalized learning path generation for GitHub repositories.

## Overview

The GitGuide Agent analyzes GitHub repositories and creates structured learning journeys tailored to individual skill levels and domain focuses. It uses advanced LLM technology to understand codebases and generate specific, actionable learning tasks.

## Features

✨ **Repository Analysis**
- Automatic GitHub repository scanning
- Technology stack detection
- File structure analysis
- Key file content extraction

🎯 **Personalized Learning Paths**
- Skill-level adaptation (Beginner, Intermediate, Pro)
- Domain-specific focus (Full Stack, ML, Desktop, etc.)
- Hierarchical learning structure (Concepts → Subtopics → Tasks)
- Progressive unlocking system

🔧 **Smart Content Generation**
- AI-generated project overviews
- Specific task descriptions referencing actual files
- Difficulty-based task progression
- Context-aware learning objectives

## Architecture

```
gitguide_backend/
├── agent/                   # AI Agent Package
│   ├── main.py             # Main orchestrator
│   ├── repository_analyzer.py  # GitHub API integration
│   ├── learning_path_generator.py  # LLM integration
│   └── api_client.py       # Backend database integration
├── prompts/                # LLM Prompt Templates
│   ├── learning_path_prompts.py  # Learning path generation prompts
│   ├── chat_prompts.py     # Chat assistant prompts
│   └── README.md           # Prompt documentation
└── app/routes/             # API Integration
    ├── agent.py           # Agent processing endpoints
    └── chat.py            # Chat assistant endpoints
```

## Setup

### 1. Install Dependencies
```bash
cd gitguide_backend/agent
pip install -r requirements.txt
```

### 2. Environment Variables
Add these to your `.env` file in the project root:

```env
# GitHub API (required)
GITHUB_ACCESS_TOKEN=ghp_your_github_token_here

# Groq API (required) 
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 3. Get API Keys

**GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate token with `public_repo` scope
3. Use format: `ghp_...`

**Groq API Key:**
1. Visit [console.groq.com](https://console.groq.com)
2. Create free account (no billing required)
3. Generate API key with format: `gsk_...`

## Usage

### Basic Usage
```python
from agent import process_project

result = await process_project(
    project_id=123,
    repo_url="https://github.com/owner/repo",
    skill_level="Intermediate",
    domain="Full Stack",
    user_id="user_123"
)
```

### Direct Agent Usage
```python
from agent.main import GitGuideAgent

agent = GitGuideAgent()
result = await agent.process_new_project(
    project_id=123,
    repo_url="https://github.com/owner/repo", 
    skill_level="Beginner",
    domain="Machine Learning",
    user_id="user_456"
)
```

### Testing
```bash
# Test the agent directly
python -c "from agent.main import GitGuideAgent; import asyncio; asyncio.run(test_agent())"

# Test imports
python -c "from agent import GitGuideAgent; print('Agent imports working')"

# Test prompts
python -c "from prompts import create_analysis_prompt; print('Prompts working')"
```

## API Integration

The agent integrates with the GitGuide backend through several steps:

1. **Repository Analysis**: Fetches repository data via GitHub API
2. **Learning Generation**: Uses Groq LLM to create learning content
3. **Database Storage**: Saves structured learning paths to PostgreSQL

### Generated Data Structure
```json
{
  "project_overview": "Detailed project description...",
  "concepts": [
    {
      "id": "concept-0",
      "name": "Core Architecture",
      "description": "Understanding the project structure",
      "isUnlocked": true,
      "subtopics": [
        {
          "id": "subtopic-0-0", 
          "name": "Project Setup",
          "description": "Configuration and dependencies",
          "isUnlocked": true,
          "tasks": [
            {
              "id": "task-0-0-0",
              "name": "Analyze package.json structure",
              "description": "Study the project dependencies...",
              "files_to_study": ["package.json", "src/index.js"],
              "difficulty": "easy",
              "isUnlocked": true
            }
          ]
        }
      ]
    }
  ]
}
```

## Configuration

### Model Settings
- **LLM Model**: `llama3-70b-8192` (Groq)
- **Max Tokens**: 4000 (learning path), 1000 (chat)
- **Temperature**: 0.7
- **File Size Limit**: 400KB total context

### Repository Filtering
- **Supported Extensions**: `.js`, `.jsx`, `.ts`, `.tsx`, `.py`, `.java`, `.cpp`, etc.
- **Priority Files**: `README.md`, `package.json`, `requirements.txt`, etc.
- **Excluded Directories**: `node_modules`, `.git`, `dist`, `__pycache__`, etc.

### Prompt Engineering
All LLM prompts are centralized in the `../prompts/` directory:

- **Learning Path Prompts** (`learning_path_prompts.py`):
  - Repository context preparation
  - Structured learning path generation
  - JSON format enforcement
  - Skill-level adaptation

- **Chat Prompts** (`chat_prompts.py`):
  - Context-aware tutoring
  - Repository file integration
  - Task-specific guidance
  - Progressive difficulty adjustment

**Prompt Optimization:**
- File content limited to 1000-2000 chars per file
- Repository samples limited to 10 most relevant files
- Structured sections for better LLM understanding
- Real file references for actionable tasks

## Performance

### Processing Times
- **Small repos** (< 50 files): 10-30 seconds
- **Medium repos** (50-200 files): 30-60 seconds  
- **Large repos** (200+ files): 1-3 minutes

### API Costs (Estimated)
- **Repository Analysis**: ~$2-12 per project (depends on repository size)
- **Learning Path Generation**: ~$0.05-0.15 per project (included in analysis)
- **Chat Messages**: ~$0.10-0.50 per message (context-aware responses)
- **Monthly Usage**: ~$50-130 for moderate use (50-100 projects + chat)

## Error Handling

The agent includes comprehensive error handling:

- **GitHub API Errors**: Repository not found, rate limits, permissions
- **LLM Errors**: Invalid responses, quota limits, parsing failures
- **Database Errors**: Connection issues, constraint violations
- **Network Errors**: Timeouts, connectivity issues

## Example Output

```
🚀 Processing project 123
📦 Repository: https://github.com/microsoft/calculator
👤 User: user_456 | Skill: Beginner | Domain: Desktop App

📊 Step 1: Analyzing repository...
✅ Repository analyzed: 45 files found

🎯 Step 2: Generating learning path...
✅ Learning path generated:
   📚 Concepts: 3
   📖 Total subtopics: 6
   ✏️ Total tasks: 12

💾 Step 3: Saving to database...
✅ Learning content saved to database
🎉 Project 123 processing completed successfully!
```

## Development

### Adding New Features
1. **Repository Analysis**: Modify `repository_analyzer.py`
2. **Prompt Engineering**: Update templates in `../prompts/` directory
   - `learning_path_prompts.py` - Learning path generation
   - `chat_prompts.py` - Chat assistant interactions
3. **Learning Generation**: Extend logic in `learning_path_generator.py`
4. **Database Integration**: Extend `api_client.py`
5. **API Endpoints**: Add new routes in `../app/routes/`

### Testing New Repositories
```python
# Direct testing approach
from agent.main import GitGuideAgent
import asyncio

async def test_new_repo():
    agent = GitGuideAgent()
    result = await agent.process_new_project(
        project_id=999,
        repo_url="https://github.com/your/repo",
        skill_level="Pro",
        domain="Your Domain",
        user_id="test_user"
    )
    print(f"Result: {result}")

asyncio.run(test_new_repo())
```

## Troubleshooting

### Common Issues

**"Repository analysis failed: 404"**
- Check repository URL format
- Verify repository is public
- Ensure GitHub token has correct permissions

**"Learning path generation failed"**
- Check Groq API key is valid
- Verify internet connection
- Review repository content (might be too large/small)
- Check prompts directory imports are working

**"Database save failed"**
- Ensure backend is running on localhost:8000
- Check database connection
- Verify project_id exists in database

**"Prompt import errors"**
- Ensure prompts directory is in Python path
- Check that `../prompts/` directory exists
- Verify `__init__.py` file is present in prompts directory
- Try running from correct working directory

### Debug Mode
Set environment variable for verbose logging:
```bash
export AGENT_DEBUG=true
```

## License

Part of the GitGuide project. See main project license for details. 