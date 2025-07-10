import json
from groq import Groq

async def generate_learning_path(repo_analysis, skill_level, domain, groq_api_key):
    """
    Generate a structured learning path based on repository analysis
    
    Args:
        repo_analysis: Repository analysis result from repository_analyzer
        skill_level: User's skill level (Beginner, Intermediate, Pro)
        domain: Project domain (Full Stack, ML, etc.)
        groq_api_key: Groq API key
        
    Returns:
        dict: Structured learning path with project overview, concepts, subtopics, and tasks
    """
    try:
        client = Groq(api_key=groq_api_key)
        
        # Prepare repository context for LLM
        repo_context = prepare_repository_context(repo_analysis)
        
        # Generate project overview and learning structure
        prompt = create_analysis_prompt(repo_context, skill_level, domain)
        
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # Use the more capable 70B model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Parse the LLM response
        learning_structure = parse_llm_response(response.choices[0].message.content)
        
        if not learning_structure['success']:
            return learning_structure
        
        # Add unlocking logic
        apply_unlocking_logic(learning_structure['data'])
        
        return {
            'success': True,
            'project_overview': learning_structure['data']['project_overview'],
            'concepts': learning_structure['data']['concepts']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Learning path generation failed: {str(e)}"
        }

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
    """Create the analysis prompt for the LLM"""
    
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

def parse_llm_response(response_text):
    """Parse the LLM response and extract structured learning path"""
    try:
        # Try to extract JSON from the response
        response_text = response_text.strip()
        
        # Find JSON block
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            return {
                'success': False,
                'error': 'No JSON found in LLM response'
            }
        
        json_text = response_text[json_start:json_end]
        
        # Parse JSON
        parsed_data = json.loads(json_text)
        
        # Validate structure
        if not validate_learning_structure(parsed_data):
            return {
                'success': False,
                'error': 'Invalid learning structure format'
            }
        
        return {
            'success': True,
            'data': parsed_data
        }
        
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'JSON parsing failed: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Response parsing failed: {str(e)}'
        }

def validate_learning_structure(data):
    """Validate that the learning structure has the required format"""
    try:
        # Check required top-level keys
        if 'project_overview' not in data or 'concepts' not in data:
            return False
        
        # Check concepts structure
        for concept in data['concepts']:
            if not all(key in concept for key in ['id', 'name', 'subtopics']):
                return False
            
            # Check subtopics structure
            for subtopic in concept['subtopics']:
                if not all(key in subtopic for key in ['id', 'name', 'tasks']):
                    return False
                
                # Check tasks structure
                for task in subtopic['tasks']:
                    if not all(key in task for key in ['id', 'name', 'description']):
                        return False
        
        return True
        
    except:
        return False

def apply_unlocking_logic(learning_data):
    """Apply progressive unlocking logic to the learning structure"""
    try:
        for i, concept in enumerate(learning_data['concepts']):
            # First concept is unlocked, others are locked
            concept['isUnlocked'] = (i == 0)
            
            for j, subtopic in enumerate(concept['subtopics']):
                # First subtopic of first concept is unlocked
                subtopic['isUnlocked'] = (i == 0 and j == 0)
                
                for k, task in enumerate(subtopic['tasks']):
                    # Only first task of first subtopic of first concept is unlocked
                    task['isUnlocked'] = (i == 0 and j == 0 and k == 0)
        
    except Exception as e:
        print(f"Warning: Failed to apply unlocking logic: {e}")

# Helper function for content generation
async def generate_detailed_content(learning_structure, repo_context, groq_api_key):
    """Generate detailed content for concepts and tasks (optional enhancement)"""
    # This can be used later to generate more detailed explanations
    pass 