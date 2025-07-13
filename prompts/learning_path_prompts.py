"""
Learning Path Generation Prompts
Prompts for generating structured learning paths from repository analysis
"""

def prepare_repository_context(repo_analysis):
    """Prepare repository context for LLM analysis"""
    context = {
        'repo_info': repo_analysis['repo_info'],
        'tech_stack': repo_analysis['tech_stack'],
        'file_count': repo_analysis['total_files'],
        'key_files': []
    }
    
    # Add key file contents (limited to most important ones)
    important_files = ['README.md', 'package.json', 'requirements.txt', 'setup.py']
    file_sample = {}
    
    for file_path, content in repo_analysis['files'].items():
        file_name = file_path.split('/')[-1]
        
        # Always include important config files
        if file_name in important_files:
            file_sample[file_path] = content[:2000]  # Limit content length
        # Add some representative code files
        elif len(file_sample) < 10 and any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.py']):
            file_sample[file_path] = content[:1500]
    
    context['file_samples'] = file_sample
    
    return context

def create_analysis_prompt(repo_context, skill_level, domain):
    """Create the analysis prompt for learning path generation"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor analyzing a GitHub repository to create a personalized learning journey.

REPOSITORY INFORMATION:
- Name: {repo_context['repo_info']['name']}
- Description: {repo_context['repo_info']['description']}
- Primary Language: {repo_context['repo_info']['language']}
- Tech Stack: {repo_context['tech_stack']}
- Total Files: {repo_context['file_count']}

LEARNER PROFILE:
- Skill Level: {skill_level}
- Domain Focus: {domain}

KEY FILES CONTENT:{file_contents_text}

TASK:
Create a comprehensive learning path with:

1. PROJECT OVERVIEW: A detailed explanation of what this project does, its architecture, and key learning objectives.

2. LEARNING STRUCTURE: 3-4 main concepts, each with 2-3 subtopics, each subtopic with 3-4 specific tasks.

IMPORTANT REQUIREMENTS:
- Make tasks reference ACTUAL files, functions, and code patterns from this repository
- Adapt complexity to {skill_level} level
- Focus on {domain} domain concepts
- Make tasks practical and actionable
- Ensure progressive difficulty within each concept

RESPONSE FORMAT (JSON):
{{
    "project_overview": "Detailed overview explaining the project, its purpose, architecture, and what the learner will gain by studying it...",
    "concepts": [
        {{
            "id": "concept-0",
            "name": "Descriptive concept name",
            "description": "What this concept teaches",
            "subtopics": [
                {{
                    "id": "subtopic-0-0",
                    "name": "Specific subtopic name",
                    "description": "What this subtopic covers",
                    "tasks": [
                        {{
                            "id": "task-0-0-0",
                            "name": "Specific task referencing actual files",
                            "description": "Detailed task description with specific file references and what to learn",
                            "files_to_study": ["actual/file/path.js", "another/file.py"],
                            "difficulty": "easy|medium|hard"
                        }}
                    ]
                }}
            ]
        }}
    ]
}}

Generate EXACTLY this JSON structure with real, specific content based on the repository analysis.
"""
    
    return prompt 