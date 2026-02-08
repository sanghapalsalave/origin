"""
API v1 router aggregation.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, onboarding, matching, mool, chat, notifications, premium, health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
api_router.include_router(matching.router, prefix="/matching", tags=["Matching"])
api_router.include_router(mool.router, prefix="/mool", tags=["Mool Reputation System"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(premium.router, prefix="/premium", tags=["Premium & B2B"])
api_router.include_router(health.router, tags=["Health"])
