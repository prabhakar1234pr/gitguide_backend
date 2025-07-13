import json
import sys
import os
from groq import Groq

# Add prompts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from prompts import create_analysis_prompt, prepare_repository_context

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

# Functions moved to prompts/learning_path_prompts.py

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