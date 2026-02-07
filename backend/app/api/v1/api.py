"""
API v1 router aggregation.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, onboarding, matching

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(matching.router, prefix="/matching", tags=["Matching"])
