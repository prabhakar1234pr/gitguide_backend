from fastapi import APIRouter

router = APIRouter()

@router.get("/ping",
    summary="Health Check",
    description="Simple endpoint to check if the API server is running and responsive",
    response_description="Confirmation that server is alive"
)
async def ping():
    return {"message": "pong"} 