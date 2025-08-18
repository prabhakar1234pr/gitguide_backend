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
    important_files = ['README.md', 'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml']
    file_sample = {}
    
    for file_path, content in repo_analysis['files'].items():
        file_name = file_path.split('/')[-1]
        
        # Always include important config files (shorter content for faster processing)
        if file_name in important_files:
            file_sample[file_path] = content[:1500]  # Reduced from 2000 to 1500
        # Add some representative code files (limit to 8 files max)
        elif len(file_sample) < 8 and any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.py']):
            file_sample[file_path] = content[:1000]  # Reduced from 1500 to 1000
    
    context['file_samples'] = file_sample
    
    return context

def create_analysis_prompt(repo_context, skill_level, domain):
    """Create the analysis prompt for learning path generation"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor analyzing a GitHub repository to create a personalized, step-by-step learning journey for a beginner.

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
Create a GitGuide learning structure with:

1. PROJECT OVERVIEW: A comprehensive overview (6-10 sentences) explaining what this project does, its architecture, primary modules, data flow, and what the learner will gain by studying it. Make it concrete and repo-aware (reference files/folders where helpful). No code.

2. LEARNING STRUCTURE: Break down the learning journey into rich concepts. Each concept MUST have a detailed multi-sentence description (4-6 sentences) that teaches the idea before tasks. For each concept, create MANY subconcepts (at least 3-5) with clear 2-3 sentence descriptions.

3. TASKS: For each subconcept, create MULTIPLE tasks (at least 2-4). Tasks must be detailed step-by-step (5-10 sentences), specific, actionable, and must reference actual files, functions, or code patterns from this repository. Never include code. The AI should teach first, then ask the user to apply.

IMPORTANT REQUIREMENTS:
- Descriptions (project overview, concept, subconcept) must be detailed and instructional (not one-liners).
- Tasks must be small, specific, actionable, step-by-step, and never include code.
- The journey should be incremental with clear progression and dependencies.
- Prefer 7-10 concepts for Day 1 if feasible; adapt counts to repo size while staying comprehensive.
- Use repo-aware references (file paths, modules) in tasks when applicable.
- Do not include any explanations or markdown, only valid JSON.

CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, no additional text. Your response must start with {{ and end with }}. Nothing else.

RESPONSE FORMAT (JSON ONLY):
{{
    "project_overview": "Comprehensive project overview (6-10 sentences) grounded in repository structure...",
    "concepts": [
        {{
            "id": "concept-0",
            "name": "Concept name",
            "description": "Detailed 4-6 sentence explanation teaching the concept before tasks; include concrete repository touchpoints.",
            "subconcepts": [
                {{
                    "id": "subconcept-0-0",
                    "name": "Subconcept name",
                    "description": "2-3 sentence explanation of the specific angle covered by this subconcept.",
                    "task": {{
                        "id": "task-0-0-0",
                        "name": "Specific, actionable task referencing actual files (no code)",
                        "description": "Detailed, step-by-step task (5-10 sentences) with specific file references and clear acceptance criteria. No code.",
                        "files_to_study": ["actual/file/path.js", "another/file.py"],
                        "difficulty": "easy|medium|hard",
                        "verification_type": "github_api"
                    }}
                }}
            ]
        }}
    ]
}}

RESPOND WITH ONLY THE JSON STRUCTURE ABOVE. NO OTHER TEXT OR EXPLANATIONS.
"""
    
    return prompt

# ==================== REGENERATION PROMPTS ====================

def create_regenerate_project_overview_prompt(repo_context, current_overview, user_prompt, skill_level, domain):
    """Create prompt for regenerating the entire project overview"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor regenerating a project overview based on specific user feedback.

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

CURRENT PROJECT OVERVIEW:
{current_overview}

USER'S REGENERATION REQUEST:
{user_prompt}

TASK:
Regenerate the project overview based on the user's specific request while maintaining accuracy to the actual repository content.

REQUIREMENTS:
- Address the user's specific feedback or request
- Keep the overview accurate to the actual codebase
- Maintain appropriate complexity for {skill_level} level
- Focus on {domain} aspects when relevant
- Make it clear, engaging, and educational

RESPONSE FORMAT (JSON):
{{
    "project_overview": "Improved project overview addressing the user's request..."
}}

Generate EXACTLY this JSON structure with the improved project overview.
"""
    
    return prompt

def create_regenerate_whole_path_prompt(repo_context, current_concepts, user_prompt, skill_level, domain):
    """Create prompt for regenerating the entire learning path"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    # Summarize current structure
    current_structure = ""
    for i, concept in enumerate(current_concepts):
        current_structure += f"\nConcept {i+1}: {concept['name']}\n"
        for j, subtopic in enumerate(concept.get('subtopics', [])):
            current_structure += f"  - Subtopic {j+1}: {subtopic['name']}\n"
            for k, task in enumerate(subtopic.get('tasks', [])):
                current_structure += f"    * Task {k+1}: {task['name']}\n"
    
    prompt = f"""
You are an expert software engineering instructor regenerating an entire learning path based on specific user feedback.

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

CURRENT LEARNING PATH STRUCTURE:
{current_structure}

USER'S REGENERATION REQUEST:
{user_prompt}

TASK:
Completely regenerate the learning path structure (concepts, subtopics, and tasks) based on the user's specific request while keeping it grounded in the actual repository content.

REQUIREMENTS:
- Address the user's specific feedback or request
- Create 3-4 main concepts, each with 2-3 subtopics, each subtopic with 3-4 specific tasks
- Reference ACTUAL files, functions, and code patterns from this repository
- Adapt complexity to {skill_level} level
- Focus on {domain} domain concepts
- Make tasks practical and actionable
- Ensure progressive difficulty within each concept

RESPONSE FORMAT (JSON):
{{
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

Generate EXACTLY this JSON structure with completely new learning path content addressing the user's request.
"""
    
    return prompt

def create_regenerate_concept_prompt(repo_context, concept_to_regenerate, user_prompt, skill_level, domain):
    """Create prompt for regenerating a specific concept"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor regenerating a specific learning concept based on user feedback.

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

CURRENT CONCEPT TO REGENERATE:
Name: {concept_to_regenerate['name']}
Description: {concept_to_regenerate['description']}

Current Subtopics:
{chr(10).join([f"- {st['name']}: {st['description']}" for st in concept_to_regenerate.get('subtopics', [])])}

USER'S REGENERATION REQUEST:
{user_prompt}

TASK:
Regenerate this specific concept (including its subtopics and tasks) based on the user's request while keeping it relevant to the repository.

REQUIREMENTS:
- Address the user's specific feedback or request
- Create 2-3 subtopics, each with 3-4 specific tasks
- Reference ACTUAL files, functions, and code patterns from this repository
- Adapt complexity to {skill_level} level
- Focus on {domain} domain concepts
- Make tasks practical and actionable
- Ensure progressive difficulty within subtopics

RESPONSE FORMAT (JSON):
{{
    "concept": {{
        "id": "{concept_to_regenerate['id']}",
        "name": "Regenerated concept name",
        "description": "What this regenerated concept teaches",
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
}}

Generate EXACTLY this JSON structure with the regenerated concept content.
"""
    
    return prompt

def create_regenerate_subtopic_prompt(repo_context, subtopic_to_regenerate, parent_concept, user_prompt, skill_level, domain):
    """Create prompt for regenerating a specific subtopic"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor regenerating a specific learning subtopic based on user feedback.

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

PARENT CONCEPT CONTEXT:
Name: {parent_concept['name']}
Description: {parent_concept['description']}

CURRENT SUBTOPIC TO REGENERATE:
Name: {subtopic_to_regenerate['name']}
Description: {subtopic_to_regenerate['description']}

Current Tasks:
{chr(10).join([f"- {task['name']}: {task['description']}" for task in subtopic_to_regenerate.get('tasks', [])])}

USER'S REGENERATION REQUEST:
{user_prompt}

TASK:
Regenerate this specific subtopic (including its tasks) based on the user's request while keeping it aligned with the parent concept and repository content.

REQUIREMENTS:
- Address the user's specific feedback or request
- Create 3-4 specific tasks for this subtopic
- Reference ACTUAL files, functions, and code patterns from this repository
- Ensure tasks fit within the parent concept "{parent_concept['name']}"
- Adapt complexity to {skill_level} level
- Focus on {domain} domain concepts
- Make tasks practical and actionable
- Ensure progressive difficulty within tasks

RESPONSE FORMAT (JSON):
{{
    "subtopic": {{
        "id": "{subtopic_to_regenerate['id']}",
        "name": "Regenerated subtopic name",
        "description": "What this regenerated subtopic covers",
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
}}

Generate EXACTLY this JSON structure with the regenerated subtopic content.
"""
    
    return prompt

def create_regenerate_task_prompt(repo_context, task_to_regenerate, parent_subtopic, parent_concept, user_prompt, skill_level, domain):
    """Create prompt for regenerating a specific task"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor regenerating a specific learning task based on user feedback.

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

LEARNING CONTEXT:
Concept: {parent_concept['name']} - {parent_concept['description']}
Subtopic: {parent_subtopic['name']} - {parent_subtopic['description']}

CURRENT TASK TO REGENERATE:
Name: {task_to_regenerate['name']}
Description: {task_to_regenerate['description']}
Files to Study: {task_to_regenerate.get('files_to_study', [])}
Difficulty: {task_to_regenerate.get('difficulty', 'medium')}

USER'S REGENERATION REQUEST:
{user_prompt}

TASK:
Regenerate this specific task based on the user's request while keeping it aligned with the parent subtopic and concept.

REQUIREMENTS:
- Address the user's specific feedback or request
- Reference ACTUAL files, functions, and code patterns from this repository
- Ensure the task fits within subtopic "{parent_subtopic['name']}" and concept "{parent_concept['name']}"
- Adapt complexity to {skill_level} level
- Focus on {domain} domain concepts
- Make the task practical and actionable
- Include specific file references and learning objectives

RESPONSE FORMAT (JSON):
{{
    "task": {{
        "id": "{task_to_regenerate['id']}",
        "name": "Regenerated task name referencing actual files",
        "description": "Detailed regenerated task description with specific file references and what to learn",
        "files_to_study": ["actual/file/path.js", "another/file.py"],
        "difficulty": "easy|medium|hard"
    }}
}}

Generate EXACTLY this JSON structure with the regenerated task content.
"""
    
    return prompt 

# ==================== BACKGROUND DAY GENERATION ====================

def create_day_content_generation_prompt(repo_context, day_number, skill_level, domain, project_overview):
    """Create prompt for generating content for a specific day in the background"""
    
    file_contents_text = ""
    for file_path, content in repo_context['file_samples'].items():
        file_contents_text += f"\n\n--- {file_path} ---\n{content[:1000]}"
    
    prompt = f"""
You are an expert software engineering instructor generating Day {day_number} content for a GitGuide learning journey.

REPOSITORY INFORMATION:
- Name: {repo_context['repo_info']['name']}
- Description: {repo_context['repo_info']['description']}
- Primary Language: {repo_context['repo_info']['language']}
- Tech Stack: {repo_context['tech_stack']}
- Total Files: {repo_context['file_count']}

LEARNER PROFILE:
- Skill Level: {skill_level}
- Domain Focus: {domain}

PROJECT OVERVIEW CONTEXT:
{project_overview}

KEY FILES CONTENT:{file_contents_text}

TASK:
Generate Day {day_number} content as a detailed step-by-step journey. Aim for 6-8 concepts for the day, each with 3-6 subconcepts, and each subconcept with 2-4 tasks. Each concept MUST include a detailed 4-6 sentence description. Each subconcept MUST include a clear 2-3 sentence description. For each task, write 5-10 sentence, step-by-step instructions referencing actual files/modules from the repository. Never include code.

IMPORTANT REQUIREMENTS:
- Descriptions must be detailed and instructional (not one-liners).
- Tasks must be specific, actionable, step-by-step, with file references; no code.
- Keep progression coherent and repo-aware.
- Output ONLY valid JSON; no markdown or extra text.

CRITICAL: You MUST respond with ONLY valid JSON. No explanations, no markdown, no additional text. Your response must start with {{ and end with }}. Nothing else.

RESPONSE FORMAT (JSON ONLY):
{{
    "day_number": {day_number},
    "concepts": [
        {{
            "id": "day{day_number}-concept-0",
            "name": "Concept name",
            "description": "Detailed 4-6 sentence description teaching this concept; mention repo files/modules when relevant.",
            "subconcepts": [
                {{
                    "id": "day{day_number}-subconcept-0-0",
                    "name": "Subconcept name",
                    "description": "2-3 sentence description of the specific topic",
                    "task": {{
                        "id": "day{day_number}-task-0-0-0",
                        "name": "Specific, actionable task referencing actual files (no code)",
                        "description": "Step-by-step (5-10 sentences) task with concrete file references and acceptance criteria. No code.",
                        "files_to_study": ["actual/file/path.js", "another/file.py"],
                        "difficulty": "easy|medium|hard",
                        "verification_type": "github_api"
                    }}
                }}
            ]
        }}
    ]
}}

RESPOND WITH ONLY THE JSON STRUCTURE ABOVE. NO OTHER TEXT OR EXPLANATIONS.
"""
    
    return prompt 