"""
General endpoints for health checks and basic information.
"""

from fastapi import APIRouter

router = APIRouter(tags=["general"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if the API service is running and healthy",
    response_description="Health status",
)
async def health_check():
    return {"status": "healthy"}
