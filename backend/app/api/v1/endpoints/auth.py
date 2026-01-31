"""
Authentication API endpoints.

Implements POST /auth/register, /auth/login, /auth/logout, /auth/refresh
with request validation and error handling.

Requirements: 15.1, 15.6
"""
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from app.db.base import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.api.dependencies import get_current_user


router = APIRouter()


# Pydantic models for request validation

class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")
    display_name: str = Field(..., min_length=1, max_length=100, description="User display name")
    interest_area: str = Field(..., min_length=1, max_length=200, description="Primary interest area")
    timezone: str = Field(..., description="IANA timezone (e.g., 'America/New_York')")
    preferred_language: str = Field(..., min_length=2, max_length=2, description="ISO 639-1 language code (e.g., 'en')")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!",
                    "display_name": "John Doe",
                    "interest_area": "Web Development",
                    "timezone": "America/New_York",
                    "preferred_language": "en"
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!"
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Valid refresh token")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
            ]
        }
    }


class AuthResponse(BaseModel):
    """Response model for authentication endpoints."""
    access_token: str = Field(..., description="JWT access token (15-minute expiry)")
    refresh_token: str = Field(..., description="JWT refresh token (7-day expiry)")
    token_type: str = Field(default="bearer", description="Token type")
    user: Dict[str, Any] = Field(..., description="User information")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "user": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "reputation_points": 0,
                        "current_level": 1
                    }
                }
            ]
        }
    }


class TokenRefreshResponse(BaseModel):
    """Response model for token refresh endpoint."""
    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="Same refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class LogoutResponse(BaseModel):
    """Response model for logout endpoint."""
    message: str = Field(..., description="Logout confirmation message")
    success: bool = Field(..., description="Logout success status")


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    detail: str = Field(..., description="Error message")


# Helper function to get client IP
def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


# Dependency to get auth service
def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance.
    
    Args:
        db: Database session
        
    Returns:
        AuthService instance
    """
    return AuthService(db=db)


# API Endpoints

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User successfully registered"},
        400: {"model": ErrorResponse, "description": "Invalid request or user already exists"},
        429: {"model": ErrorResponse, "description": "Too many registration attempts"},
    },
    summary="Register a new user",
    description="Register a new user with email, password, and profile information. "
                "Returns authentication tokens upon successful registration. "
                "Rate limited to 5 attempts per 15 minutes per IP address."
)
async def register(
    request: Request,
    register_data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """
    Register a new user.
    
    Implements Requirement 15.1: Password hashing with bcrypt (12 rounds minimum)
    Implements Requirement 15.6: Rate limiting (5 attempts per 15 minutes per IP)
    
    Args:
        request: FastAPI request object (for IP extraction)
        register_data: Registration data including email, password, and profile info
        auth_service: Authentication service instance
        
    Returns:
        Authentication response with tokens and user data
        
    Raises:
        HTTPException: 400 if validation fails or user exists
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = get_client_ip(request)
    
    # Prepare profile data
    profile_data = {
        "display_name": register_data.display_name,
        "interest_area": register_data.interest_area,
        "timezone": register_data.timezone,
        "preferred_language": register_data.preferred_language
    }
    
    try:
        result = auth_service.register_user(
            email=register_data.email,
            password=register_data.password,
            profile_data=profile_data,
            ip_address=client_ip
        )
        return AuthResponse(**result)
    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Log unexpected errors and return generic error
        print(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"model": ErrorResponse, "description": "Too many login attempts"},
    },
    summary="Login user",
    description="Authenticate user with email and password. "
                "Returns JWT tokens with 15-minute access token and 7-day refresh token. "
                "Rate limited to 5 attempts per 15 minutes per IP address."
)
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """
    Authenticate user and return JWT tokens.
    
    Implements Requirement 15.6: JWT tokens with 15-minute access, 7-day refresh expiry
    Implements Requirement 15.6: Rate limiting (5 attempts per 15 minutes per IP)
    
    Args:
        request: FastAPI request object (for IP extraction)
        login_data: Login credentials (email and password)
        auth_service: Authentication service instance
        
    Returns:
        Authentication response with tokens and user data
        
    Raises:
        HTTPException: 401 if credentials are invalid
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = get_client_ip(request)
    
    try:
        result = auth_service.login(
            email=login_data.email,
            password=login_data.password,
            ip_address=client_ip
        )
        return AuthResponse(**result)
    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Log unexpected errors and return generic error
        print(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Successfully logged out"},
        401: {"model": ErrorResponse, "description": "Invalid or missing token"},
    },
    summary="Logout user",
    description="Invalidate user session and refresh token. "
                "Requires valid access token in Authorization header."
)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> LogoutResponse:
    """
    Logout user and invalidate tokens.
    
    Extracts user from JWT token in Authorization header and invalidates their session.
    
    Args:
        current_user: Current authenticated user (from JWT token)
        auth_service: Authentication service instance
        
    Returns:
        Logout confirmation response
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    try:
        success = auth_service.logout(user_id=current_user.id)
        return LogoutResponse(
            message="Successfully logged out",
            success=success
        )
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Token successfully refreshed"},
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
    summary="Refresh access token",
    description="Refresh an expired access token using a valid refresh token. "
                "Returns a new access token while keeping the same refresh token."
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenRefreshResponse:
    """
    Refresh expired access token using refresh token.
    
    Args:
        refresh_data: Refresh token data
        auth_service: Authentication service instance
        
    Returns:
        New access token and same refresh token
        
    Raises:
        HTTPException: 401 if refresh token is invalid or expired
    """
    try:
        result = auth_service.refresh_token(
            refresh_token=refresh_data.refresh_token
        )
        return TokenRefreshResponse(**result)
    except HTTPException:
        # Re-raise HTTP exceptions from service
        raise
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh"
        )

