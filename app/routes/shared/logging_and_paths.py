"""
Shared logging configuration and path setup for route modules
Eliminates duplicated logging and path setup across the application
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging once for the entire routes package
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a route module"""
    return logging.getLogger(name)

logger = get_logger(__name__)

def setup_agent_imports():
    """Setup sys.path for agent and prompts imports - shared utility"""
    try:
        # Get absolute path to backend root (gitguide_backend directory)
        current_dir = Path(__file__).resolve()  # /app/routes/shared/logging_and_paths.py
        backend_root = current_dir.parent.parent.parent.parent  # Go up 4 levels to reach gitguide_backend
        
        # Add agent directory to path
        agent_path = str(backend_root / "agent")  # /gitguide_backend/agent
        if agent_path not in sys.path:
            logger.info(f"Adding agent path to sys.path: {agent_path}")
            sys.path.insert(0, agent_path)
        
        # Add prompts directory to path  
        prompts_path = str(backend_root / "prompts")  # /gitguide_backend/prompts
        if prompts_path not in sys.path:
            logger.info(f"Adding prompts path to sys.path: {prompts_path}")
            sys.path.insert(0, prompts_path)
            
        # Verify paths exist
        if not os.path.exists(agent_path):
            logger.error(f"Agent path does not exist: {agent_path}")
            raise ImportError(f"Agent path not found: {agent_path}")
            
        if not os.path.exists(prompts_path):
            logger.error(f"Prompts path does not exist: {prompts_path}")
            raise ImportError(f"Prompts path not found: {prompts_path}")
            
        logger.info("✅ Agent imports setup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup agent imports: {str(e)}")
        raise

# Call setup once when module is imported
setup_agent_imports() 