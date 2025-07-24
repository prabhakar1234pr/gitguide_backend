"""
Core AI Agent endpoints for GitGuide
Handles core agent operations: trigger processing, check status, health checks
"""

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks

from app.routes.auth.auth_utilities import extract_user_id_from_token
from .agent_utilities import (
    AgentProcessRequest, 
    AgentStatusResponse,
    check_agent_availability,
    get_agent_instance,
    get_project_with_ownership_check,
    get_project_processing_status,
    process_project_background
)

router = APIRouter()


@router.post("/agent/process",
    summary="Generate Learning Path",
    description="Trigger AI agent to analyze GitHub repository and generate personalized learning path",
    response_description="Processing confirmation with status"
)
async def trigger_agent_processing(
    request: AgentProcessRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """Trigger agent processing for a project"""
    print(f"🎯 Agent processing request received for project {request.project_id}")
    
    try:
        print("🔍 Checking agent availability...")
        check_agent_availability()
        print("✅ Agent is available")
        
        print("🔐 Extracting user ID from token...")
        user_id = extract_user_id_from_token(authorization)
        print(f"✅ User ID extracted: {user_id}")
        
        try:
            # Verify project exists and belongs to user
            print("📊 Verifying project ownership...")
            project = await get_project_with_ownership_check(request.project_id, user_id)
            print(f"✅ Project verified: {project.repo_url}")
            
            if project.is_processed:
                print("ℹ️ Project already processed")
                return {
                    "message": "Project already processed",
                    "project_id": request.project_id,
                    "status": "already_processed"
                }
            
            # Add background task to process the project
            print("🚀 Adding background task for processing...")
            background_tasks.add_task(
                process_project_background, 
                request.project_id,
                user_id
            )
            print("✅ Background task added successfully")
            
            return {
                "message": "Processing started",
                "project_id": request.project_id,
                "status": "processing"
            }
            
        except Exception as e:
            print(f"❌ Error during project verification: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start processing: {str(e)}"
            )
            
    except HTTPException as he:
        print(f"❌ HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/agent/status/{project_id}",
    summary="Check Processing Status", 
    description="Check the current processing status of AI learning path generation",
    response_description="Processing status and completion details"
)
async def get_agent_status(
    project_id: int,
    authorization: str = Header(None)
) -> AgentStatusResponse:
    """Get the processing status of a project"""
    
    user_id = extract_user_id_from_token(authorization)
    
    try:
        status_data = await get_project_processing_status(project_id, user_id)
        
        return AgentStatusResponse(
            status=status_data["status"],
            message=status_data["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting agent status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/agent/health",
    summary="Agent Health Check",
    description="Check if AI agent service is available and properly configured",
    response_description="Agent service status and configuration details"
)
async def agent_health_check():
    """Check if the agent service is available"""
    
    try:
        agent = get_agent_instance()
        return {
            "status": "available",
            "message": "GitGuide Agent is ready",
            "agent_available": True,
            "github_token": bool(agent.github_token),
            "groq_api_key": bool(agent.groq_api_key)
        }
    except HTTPException as e:
        if e.status_code == 503:
            return {
                "status": "unavailable",
                "message": "GitGuide Agent is not installed or configured",
                "agent_available": False
            }
        return {
            "status": "error",
            "message": f"Agent initialization failed: {e.detail}",
            "agent_available": False
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Agent initialization failed: {str(e)}",
            "agent_available": False
        } 