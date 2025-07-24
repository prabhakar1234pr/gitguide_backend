import json
import sys
import os
from groq import Groq

# Add prompts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from prompts import create_analysis_prompt, prepare_repository_context

async def generate_learning_path(repo_analysis, skill_level, domain, groq_api_key):
    """
    Generate a personalized learning path based on repository analysis
    
    Args:
        repo_analysis: Repository analysis data
        skill_level: User's skill level (Beginner, Intermediate, Pro)
        domain: Project domain (Full Stack, ML, etc.)
        groq_api_key: Groq API key
    
    Returns:
        dict: Structured learning path with project overview, concepts, subtopics, and tasks
    """
    try:
        print(f"🔑 Initializing Groq client with API key: {groq_api_key[:10]}...")
        client = Groq(
            api_key=groq_api_key,
            timeout=60.0,  # 60 second timeout
            max_retries=2  # Retry up to 2 times
        )
        
        # Prepare repository context for LLM
        repo_context = prepare_repository_context(repo_analysis)
        print(f"📝 Repository context prepared: {len(repo_context)} chars")
        
        # Generate project overview and learning structure
        prompt = create_analysis_prompt(repo_context, skill_level, domain)
        print(f"📄 Prompt created: {len(prompt)} chars")
        
        print("🤖 Calling Groq LLM (llama3-8b-8192)...")
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a technical learning expert. You MUST respond with ONLY valid JSON. No explanations, no markdown, no additional text. Your response must start with { and end with }."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000,
            timeout=60.0  # Explicit timeout for this call
        )
        print("✅ LLM response received")
        
        # Parse the LLM response
        learning_structure = parse_llm_response(response.choices[0].message.content)
        print(f"📊 Learning structure parsed: success={learning_structure['success']}")
        
        if not learning_structure['success']:
            print(f"❌ Learning structure parsing failed: {learning_structure.get('error', 'Unknown error')}")
            return learning_structure
        
        # Add unlocking logic
        apply_unlocking_logic(learning_structure['data'])
        
        return {
            'success': True,
            'project_overview': learning_structure['data']['project_overview'],
            'concepts': learning_structure['data']['concepts']
        }
        
    except Exception as e:
        print(f"❌ Learning path generation error: {type(e).__name__}: {str(e)}")
        return {
            'success': False,
            'error': f"Learning path generation failed: {str(e)}"
        }

# Functions moved to prompts/learning_path_prompts.py

def parse_llm_response(response_text):
    """Parse the LLM response and extract structured learning path"""
    try:
        # Log the raw response for debugging
        print(f"\n📤 Raw LLM Response ({len(response_text)} chars):")
        print(f"First 500 chars: {response_text[:500]}")
        print(f"Last 500 chars: {response_text[-500:]}")
        
        # Try to extract JSON from the response
        response_text = response_text.strip()
        
        # Try different methods to find JSON
        json_text = None
        
        # Method 1: Look for JSON in markdown code blocks
        if '```json' in response_text.lower():
            start_marker = '```json'
            end_marker = '```'
            start_idx = response_text.lower().find(start_marker)
            if start_idx != -1:
                start_idx += len(start_marker)
                end_idx = response_text.find(end_marker, start_idx)
                if end_idx != -1:
                    json_text = response_text[start_idx:end_idx].strip()
                    print(f"📋 Found JSON in markdown block")
        
        # Method 2: Look for JSON in regular code blocks
        if not json_text and '```' in response_text:
            lines = response_text.split('\n')
            in_code_block = False
            json_lines = []
            
            for line in lines:
                if line.strip().startswith('```'):
                    if in_code_block:
                        break
                    in_code_block = True
                    continue
                if in_code_block:
                    json_lines.append(line)
            
            if json_lines:
                potential_json = '\n'.join(json_lines).strip()
                if potential_json.startswith('{') and potential_json.endswith('}'):
                    json_text = potential_json
                    print(f"📋 Found JSON in code block")
        
        # Method 3: Find JSON by braces (original method)
        if not json_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                print(f"📋 Found JSON by braces")
        
        # Method 4: Try to clean and extract if response looks like JSON
        if not json_text and response_text.strip().startswith('{'):
            json_text = response_text.strip()
            print(f"📋 Using entire response as JSON")
        
        if not json_text:
            print(f"❌ No JSON found using any method")
            return {
                'success': False,
                'error': 'No JSON found in LLM response'
            }
        
        print(f"📋 Extracted JSON ({len(json_text)} chars): {json_text[:200]}...")
        
        # Parse JSON
        parsed_data = json.loads(json_text)
        print(f"✅ JSON parsed successfully")
        
        # Validate structure
        if not validate_learning_structure(parsed_data):
            print(f"❌ Invalid learning structure format")
            return {
                'success': False,
                'error': 'Invalid learning structure format'
            }
        
        print(f"✅ Learning structure validated")
        return {
            'success': True,
            'data': parsed_data
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {str(e)}")
        print(f"   JSON text was: {json_text[:500] if json_text else 'None'}...")
        return {
            'success': False,
            'error': f'JSON parsing failed: {str(e)}'
        }
    except Exception as e:
        print(f"❌ Response parsing failed: {str(e)}")
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