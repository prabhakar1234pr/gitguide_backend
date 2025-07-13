"""
Chat Assistant Prompts
Prompts for context-aware chat interactions with the AI tutor
"""

def create_chat_prompt(user_message: str, context: dict) -> str:
    """Create a context-aware prompt for the chat assistant"""
    
    project = context['project']
    current_task = context['current_task']
    learning_path = context['learning_path']
    repo_files = context['repo_files']
    
    # Create repository files summary
    files_summary = ""
    if repo_files:
        files_summary = "\nREPOSITORY FILES:\n"
        for file_path, content in list(repo_files.items())[:5]:  # Limit to 5 files
            files_summary += f"\n--- {file_path} ---\n{content[:800]}...\n"
    
    # Create learning path summary
    learning_summary = ""
    if learning_path:
        learning_summary = "\nLEARNING PATH:\n"
        for concept in learning_path:
            learning_summary += f"\n📚 {concept['name']}: {concept['description']}\n"
            for subtopic in concept['subtopics']:
                learning_summary += f"  📖 {subtopic['name']}\n"
                for task in subtopic['tasks'][:2]:  # Show first 2 tasks per subtopic
                    status_emoji = "✅" if task['status'] == 'done' else "🔓" if task['is_unlocked'] else "🔒"
                    learning_summary += f"    {status_emoji} {task['name']}\n"
    
    # Create current task context
    current_task_context = ""
    if current_task:
        files_list = ", ".join(current_task['files_to_study']) if current_task['files_to_study'] else "No specific files"
        current_task_context = f"""
CURRENT TASK:
- Name: {current_task['name']}
- Description: {current_task['description']}
- Difficulty: {current_task['difficulty']}
- Files to Study: {files_list}
"""
    
    prompt = f"""
You are an expert programming tutor helping a student learn from a real GitHub repository. You have complete access to the project context and should provide specific, helpful guidance.

PROJECT CONTEXT:
- Project: {project['name']}
- Domain: {project['domain']}
- Skill Level: {project['skill_level']}
- Tech Stack: {project['tech_stack']}
- Overview: {project['overview']}

{current_task_context}

{learning_summary}

{files_summary}

USER QUESTION: {user_message}

INSTRUCTIONS:
- Provide specific, actionable guidance related to the actual codebase
- Reference actual files, functions, and code patterns when relevant
- Help the user understand concepts in the context of this specific project
- If asked about code, explain it line by line when helpful
- Adapt your explanation to the user's skill level ({project['skill_level']})
- Focus on the current task when applicable
- Be encouraging and educational

Respond as a knowledgeable tutor who understands this specific project deeply.
"""
    
    return prompt 