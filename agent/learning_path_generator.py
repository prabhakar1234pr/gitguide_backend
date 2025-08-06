import json
import sys
import os
from openai import AzureOpenAI

# Add prompts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from prompts import create_analysis_prompt, prepare_repository_context, create_day_content_generation_prompt

async def generate_learning_path(repo_analysis, skill_level, domain, azure_openai_config):
    """
    Generate a personalized learning path based on repository analysis
    
    Args:
        repo_analysis: Repository analysis data
        skill_level: User's skill level (Beginner, Intermediate, Pro)
        domain: Project domain (Full Stack, ML, etc.)
        azure_openai_config: Azure OpenAI configuration dict
    
    Returns:
        dict: Structured learning path with project overview and Day 1 concepts
    """
    try:
        print(f"🔑 Initializing Azure OpenAI client...")
        client = AzureOpenAI(
            api_key=azure_openai_config['api_key'],
            api_version=azure_openai_config['api_version'],
            azure_endpoint=azure_openai_config['endpoint'],
            timeout=azure_openai_config.get('timeout', 120.0),  # Configurable timeout
            max_retries=3   # Increased to 3 retries
        )
        
        # Prepare repository context for LLM
        repo_context = prepare_repository_context(repo_analysis)
        context_size = sum(len(str(v)) for v in repo_context.values() if isinstance(v, (str, list, dict)))
        print(f"📝 Repository context prepared: {context_size} chars, {len(repo_context.get('file_samples', {}))} files")
        
        # Generate project overview and Day 1 learning structure
        prompt = create_analysis_prompt(repo_context, skill_level, domain)
        print(f"📄 Prompt created: {len(prompt)} chars")
        
        print("🤖 Calling Azure OpenAI for Day 1 content...")
        try:
            response = client.chat.completions.create(
                model=azure_openai_config['deployment_name'],
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
                max_tokens=12000,  # Increased for more content
                stream=False
            )
        except Exception as api_error:
            print(f"❌ Azure OpenAI API call failed: {type(api_error).__name__}: {str(api_error)}")
            # Try with reduced max_tokens as fallback
            if "timeout" in str(api_error).lower():
                print("🔄 Retrying with reduced complexity...")
                response = client.chat.completions.create(
                    model=azure_openai_config['deployment_name'],
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
                    max_tokens=8000,  # Reduced tokens for faster response
                    stream=False
                )
            else:
                raise api_error
        print("✅ LLM response received")
        
        # Parse the LLM response
        learning_structure = parse_llm_response(response.choices[0].message.content)
        print(f"📊 Learning structure parsed: success={learning_structure['success']}")
        
        if not learning_structure['success']:
            print(f"❌ Learning structure parsing failed: {learning_structure.get('error', 'Unknown error')}")
            return learning_structure
        
        # Apply unlocking logic for Day 1
        apply_day_unlocking_logic(learning_structure['data']['concepts'], day_number=1)
        
        return {
            'success': True,
            'project_overview': learning_structure['data']['project_overview'],
            'day_1_concepts': learning_structure['data']['concepts']
        }
        
    except Exception as e:
        print(f"❌ Learning path generation error: {type(e).__name__}: {str(e)}")
        return {
            'success': False,
            'error': f"Learning path generation failed: {str(e)}"
        }

async def generate_day_content(repo_analysis, day_number, skill_level, domain, project_overview, azure_openai_config):
    """
    Generate content for a specific day in the background
    
    Args:
        repo_analysis: Repository analysis data
        day_number: Day number to generate content for
        skill_level: User's skill level
        domain: Project domain
        project_overview: Brief project overview for context
        azure_openai_config: Azure OpenAI configuration dict
    
    Returns:
        dict: Day content with 10 concepts, each with 10 subconcepts and tasks
    """
    try:
        print(f"🔑 Initializing Azure OpenAI client for Day {day_number}...")
        client = AzureOpenAI(
            api_key=azure_openai_config['api_key'],
            api_version=azure_openai_config['api_version'],
            azure_endpoint=azure_openai_config['endpoint'],
            timeout=azure_openai_config.get('timeout', 120.0),  # Configurable timeout
            max_retries=3   # Increased to 3 retries
        )
        
        # Prepare repository context
        repo_context = prepare_repository_context(repo_analysis)
        print(f"📝 Repository context prepared for Day {day_number}")
        
        # Generate day-specific content
        prompt = create_day_content_generation_prompt(repo_context, day_number, skill_level, domain, project_overview)
        print(f"📄 Day {day_number} prompt created: {len(prompt)} chars")
        
        print(f"🤖 Calling Azure OpenAI for Day {day_number} content...")
        response = client.chat.completions.create(
            model=azure_openai_config['deployment_name'],
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
            max_tokens=8000  # Large token count for extensive content
        )
        print(f"✅ Day {day_number} LLM response received")
        
        # Parse the LLM response
        day_structure = parse_day_response(response.choices[0].message.content)
        print(f"📊 Day {day_number} structure parsed: success={day_structure['success']}")
        
        if not day_structure['success']:
            print(f"❌ Day {day_number} structure parsing failed: {day_structure.get('error', 'Unknown error')}")
            return day_structure
        
        # Apply unlocking logic (all locked initially)
        apply_day_unlocking_logic(day_structure['data']['concepts'], day_number=day_number, all_locked=True)
        
        return {
            'success': True,
            'day_number': day_number,
            'concepts': day_structure['data']['concepts']
        }
        
    except Exception as e:
        print(f"❌ Day {day_number} content generation error: {type(e).__name__}: {str(e)}")
        return {
            'success': False,
            'error': f"Day {day_number} content generation failed: {str(e)}"
        }

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

def parse_day_response(response_text):
    """Parse the day-specific LLM response"""
    # Use the same parsing logic as the main response
    return parse_llm_response(response_text)

def validate_learning_structure(data):
    """Validate that the learning structure has the required format"""
    try:
        # Check required top-level keys
        if 'project_overview' not in data and 'concepts' not in data:
            return False
        
        # For day-specific responses, only concepts are required
        if 'concepts' not in data:
            return False
        
        # Check concepts structure
        for concept in data['concepts']:
            if not all(key in concept for key in ['id', 'name', 'subconcepts']):
                # Also check for old format for backward compatibility
                if not all(key in concept for key in ['id', 'name', 'subtopics']):
                    return False
                else:
                    # Convert old format to new format
                    concept['subconcepts'] = concept.pop('subtopics', [])
            
            # Check subconcepts structure
            subconcepts_key = 'subconcepts' if 'subconcepts' in concept else 'subtopics'
            for subconcept in concept[subconcepts_key]:
                if not all(key in subconcept for key in ['id', 'name', 'task']):
                    # Check old format
                    if not all(key in subconcept for key in ['id', 'name', 'tasks']):
                        return False
                    else:
                        # Convert old format: take first task
                        if subconcept['tasks']:
                            subconcept['task'] = subconcept['tasks'][0]
                        else:
                            return False
                
                # Check task structure
                task = subconcept.get('task')
                if not task or not all(key in task for key in ['id', 'name', 'description']):
                    return False
        
        return True
        
    except:
        return False

def apply_day_unlocking_logic(concepts, day_number=1, all_locked=False):
    """Apply progressive unlocking logic to day concepts"""
    try:
        for i, concept in enumerate(concepts):
            # For Day 1, first concept is unlocked; for other days, all locked initially
            concept['isUnlocked'] = (not all_locked and i == 0)
            
            subconcepts_key = 'subconcepts' if 'subconcepts' in concept else 'subtopics'
            for j, subconcept in enumerate(concept[subconcepts_key]):
                # First subconcept of first concept is unlocked for Day 1
                subconcept['isUnlocked'] = (not all_locked and i == 0 and j == 0)
                
                # Handle task unlocking
                task = subconcept.get('task')
                if task:
                    # Only first task of first subconcept of first concept is unlocked for Day 1
                    task['isUnlocked'] = (not all_locked and i == 0 and j == 0)
                
                # Handle old format with multiple tasks
                if 'tasks' in subconcept:
                    for k, task in enumerate(subconcept['tasks']):
                        task['isUnlocked'] = (not all_locked and i == 0 and j == 0 and k == 0)
        
    except Exception as e:
        print(f"Warning: Failed to apply unlocking logic: {e}")

# Helper function for content generation
async def generate_detailed_content(learning_structure, repo_context, azure_openai_config):
    """Generate detailed content for concepts and tasks (optional enhancement)"""
    # This can be used later to generate more detailed explanations
    pass 