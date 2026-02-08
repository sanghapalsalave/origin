"""
Health check endpoints.

Provides health status for the service and its dependencies.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import redis
from app.db.base import get_db
from app.core.config import settings
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns service status without checking dependencies.
    """
    return {
        "status": "healthy",
        "service": "origin-backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check endpoint.
    
    Checks connectivity to all critical dependencies:
    - Database (PostgreSQL)
    - Cache (Redis)
    - Vector database (Pinecone)
    
    Returns:
        Health status with dependency checks
    """
    health_status = {
        "status": "healthy",
        "service": "origin-backend",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {}
    }
    
    # Check database connectivity
    try:
        db.execute("SELECT 1")
        health_status["dependencies"]["database"] = {
            "status": "healthy",
            "type": "postgresql"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["dependencies"]["database"] = {
            "status": "unhealthy",
            "type": "postgresql",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        redis_client = redis.from_url(settings.CELERY_BROKER)
        redis_client.ping()
        health_status["dependencies"]["redis"] = {
            "status": "healthy",
            "type": "cache"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["dependencies"]["redis"] = {
            "status": "unhealthy",
            "type": "cache",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Pinecone connectivity
    try:
        from app.services.pinecone_service import PineconeService
        pinecone_service = PineconeService()
        # Simple check - if initialization succeeds, it's healthy
        health_status["dependencies"]["pinecone"] = {
            "status": "healthy",
            "type": "vector_database"
        }
    except Exception as e:
        logger.error(f"Pinecone health check failed: {str(e)}")
        health_status["dependencies"]["pinecone"] = {
            "status": "unhealthy",
            "type": "vector_database",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/readiness")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check endpoint.
    
    Indicates if the service is ready to accept traffic.
    Checks critical dependencies only.
    
    Returns:
        Readiness status
    """
    ready = True
    checks = {}
    
    # Check database
    try:
        db.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database readiness check failed: {str(e)}")
        checks["database"] = False
        ready = False
    
    # Check Redis
    try:
        redis_client = redis.from_url(settings.CELERY_BROKER)
        redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis readiness check failed: {str(e)}")
        checks["redis"] = False
        ready = False
    
    return {
        "ready": ready,
        "checks": checks
    }


@router.get("/health/liveness")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.
    
    Indicates if the service is alive and running.
    Does not check dependencies.
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "service": "origin-backend"
    }
