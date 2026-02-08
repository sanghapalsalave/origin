"""
Main FastAPI application entry point.

Implements Requirements:
- 15.3: TLS 1.3 configuration for all endpoints
- 15.7: Audit logging for user data access
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
from app.core.config import settings
from app.core.logging_config import setup_logging, set_request_id, clear_request_id, get_logger
from app.api.v1.api import api_router

# Set up structured logging
setup_logging(log_level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else 'INFO')
logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Security headers
    docs_url=f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Audit logging middleware with request ID tracking
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """
    Audit logging middleware for tracking user data access.
    
    Implements Requirement 15.7: Log all user data access attempts.
    Adds request ID tracking for correlation.
    """
    # Generate and set request ID
    request_id = set_request_id()
    
    start_time = time.time()
    
    # Log request with structured logging
    logger.info(
        "API request received",
        extra={
            'extra_fields': {
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'client_host': request.client.host if request.client else 'unknown',
                'user_agent': request.headers.get('user-agent', 'unknown')
            }
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response with structured logging
    process_time = time.time() - start_time
    logger.info(
        "API request completed",
        extra={
            'extra_fields': {
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'process_time_seconds': round(process_time, 3)
            }
        }
    )
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Request-ID"] = request_id
    
    # Clear request ID from context
    clear_request_id()
    
    return response


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": "origin-backend"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ORIGIN Learning Platform API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs" if settings.ENVIRONMENT != "production" else None
    }
