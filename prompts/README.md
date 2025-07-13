# GitGuide Prompts Directory

This directory contains all prompt templates used for LLM interactions in the GitGuide system.

## Overview

The prompts have been organized into separate modules for better maintainability and reusability:

### 📁 File Structure
```
prompts/
├── __init__.py                 # Package initialization and exports
├── learning_path_prompts.py    # Prompts for learning path generation
├── chat_prompts.py            # Prompts for chat assistant interactions
└── README.md                  # This documentation
```

## 🎯 Prompt Modules

### Learning Path Prompts (`learning_path_prompts.py`)
Contains prompts for analyzing GitHub repositories and generating structured learning paths.

**Functions:**
- `create_analysis_prompt()` - Creates the main prompt for learning path generation
- `prepare_repository_context()` - Helper to prepare repository data for the LLM

**Usage:**
```python
from prompts import create_analysis_prompt, prepare_repository_context

# Prepare context from repository analysis
context = prepare_repository_context(repo_analysis)

# Create prompt for learning path generation
prompt = create_analysis_prompt(context, skill_level, domain)
```

### Chat Prompts (`chat_prompts.py`)
Contains prompts for context-aware chat interactions with the AI tutor.

**Functions:**
- `create_chat_prompt()` - Creates context-aware prompts for chat responses

**Usage:**
```python
from prompts import create_chat_prompt

# Create prompt for chat assistant
prompt = create_chat_prompt(user_message, project_context)
```

## 🔧 Prompt Engineering Guidelines

### Best Practices
1. **Clear Structure**: Use structured sections (REPOSITORY INFO, TASK, INSTRUCTIONS)
2. **Specific Context**: Include actual file contents and project details
3. **Adaptive Complexity**: Adjust language for different skill levels
4. **JSON Format**: Use strict JSON formatting requirements for structured responses
5. **Real Examples**: Reference actual files and code patterns from the repository

### Template Format
```python
def create_prompt_name(context_params):
    """Clear description of what this prompt does"""
    
    # Data preparation
    formatted_data = prepare_context_data(context_params)
    
    prompt = f"""
    Clear role definition for the AI...
    
    CONTEXT SECTION:
    - Structured information
    - Specific details
    
    TASK DESCRIPTION:
    What the AI should accomplish...
    
    INSTRUCTIONS:
    - Specific requirements
    - Output format
    - Quality guidelines
    
    {formatted_data}
    """
    
    return prompt
```

## 📊 Prompt Performance

### Current Models
- **Learning Path Generation**: `llama3-70b-8192` (4000 max tokens)
- **Chat Assistant**: `llama3-70b-8192` (1000 max tokens)

### Optimization Notes
- Repository context limited to ~2000 chars per file
- File samples limited to 10 most relevant files
- Chat context includes max 5 repository files
- Learning path limited to 3-4 concepts for focus

## 🔄 Integration

### How Prompts Are Used

1. **Learning Path Generation Flow:**
   ```
   Repository Analysis → prepare_repository_context() → create_analysis_prompt() → Groq LLM → Structured Learning Path
   ```

2. **Chat Assistant Flow:**
   ```
   User Message + Project Context → create_chat_prompt() → Groq LLM → Contextual Response
   ```

### Import Structure
```python
# In consuming modules
from prompts import create_analysis_prompt, create_chat_prompt, prepare_repository_context
```

## 🚀 Future Enhancements

### Planned Features
- [ ] Multi-language prompt templates
- [ ] Specialized prompts for different domains (ML, Web, Mobile)
- [ ] Adaptive prompts based on learning progress
- [ ] A/B testing framework for prompt optimization
- [ ] Prompt versioning and rollback capabilities

### Template Ideas
- Task-specific prompts for different difficulty levels
- Code review prompts for evaluating student solutions
- Project assessment prompts for measuring understanding
- Debugging assistance prompts for common issues 