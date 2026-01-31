"""
Authentication service for user registration, login, logout, and token management.

Implements Requirements 15.6 (JWT tokens, rate limiting).
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import redis
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password
)
from app.models.user import User
from app.models.user import UserProfile


class AuthService:
    """
    Authentication service handling user registration, login, logout, and token management.
    
    Implements:
    - JWT token generation with 15-minute access, 7-day refresh expiry
    - Rate limiting (5 attempts per 15 minutes per IP)
    - Token verification and refresh
    """
    
    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        """
        Initialize authentication service.
        
        Args:
            db: SQLAlchemy database session
            redis_client: Redis client for rate limiting (optional, will create if not provided)
        """
        self.db = db
        self.redis_client = redis_client or redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    
    def _check_rate_limit(self, ip_address: str) -> None:
        """
        Check if IP address has exceeded rate limit for authentication attempts.
        
        Implements rate limiting: 5 attempts per 15 minutes per IP (Requirement 15.6).
        
        Args:
            ip_address: Client IP address
            
        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        rate_limit_key = f"auth_rate_limit:{ip_address}"
        
        try:
            # Get current attempt count
            attempts = self.redis_client.get(rate_limit_key)
            
            if attempts is None:
                # First attempt, set counter with expiry
                self.redis_client.setex(
                    rate_limit_key,
                    settings.AUTH_RATE_LIMIT_WINDOW_MINUTES * 60,
                    1
                )
            else:
                attempts = int(attempts)
                if attempts >= settings.AUTH_RATE_LIMIT_ATTEMPTS:
                    # Rate limit exceeded
                    ttl = self.redis_client.ttl(rate_limit_key)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many authentication attempts. Please try again in {ttl} seconds.",
                        headers={"Retry-After": str(ttl)}
                    )
                else:
                    # Increment counter
                    self.redis_client.incr(rate_limit_key)
        except redis.RedisError as e:
            # If Redis is unavailable, log error but don't block authentication
            # In production, you might want to handle this differently
            print(f"Redis error in rate limiting: {e}")
    
    def _reset_rate_limit(self, ip_address: str) -> None:
        """
        Reset rate limit counter for IP address after successful authentication.
        
        Args:
            ip_address: Client IP address
        """
        rate_limit_key = f"auth_rate_limit:{ip_address}"
        try:
            self.redis_client.delete(rate_limit_key)
        except redis.RedisError as e:
            print(f"Redis error resetting rate limit: {e}")
    
    def register_user(
        self,
        email: str,
        password: str,
        profile_data: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user with email and password.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            profile_data: User profile information (display_name, interest_area, etc.)
            ip_address: Client IP address for rate limiting (optional)
            
        Returns:
            Dictionary containing user data and authentication tokens
            
        Raises:
            HTTPException: 400 if user already exists or validation fails
            HTTPException: 429 if rate limit exceeded
        """
        # Check rate limit if IP provided
        if ip_address:
            self._check_rate_limit(ip_address)
        
        # Check if user already exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate password strength (basic validation)
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Create new user
        user = User(email=email)
        user.set_password(password)
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Create user profile if profile_data provided
        if profile_data:
            profile = UserProfile(
                user_id=user.id,
                display_name=profile_data.get("display_name", ""),
                interest_area=profile_data.get("interest_area", ""),
                skill_level=profile_data.get("skill_level", 1),
                timezone=profile_data.get("timezone", "UTC"),
                preferred_language=profile_data.get("preferred_language", "en"),
                learning_velocity=profile_data.get("learning_velocity", 0.0),
                vector_embedding_id=profile_data.get("vector_embedding_id"),
                github_url=profile_data.get("github_url"),
                linkedin_profile=profile_data.get("linkedin_profile"),
                portfolio_url=profile_data.get("portfolio_url"),
                resume_data=profile_data.get("resume_data"),
                manual_skills=profile_data.get("manual_skills")
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        
        # Generate tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        
        # Reset rate limit on successful registration
        if ip_address:
            self._reset_rate_limit(ip_address)
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and return JWT tokens.
        
        Implements JWT token generation with 15-minute access, 7-day refresh expiry.
        
        Args:
            email: User email address
            password: Plain text password
            ip_address: Client IP address for rate limiting (optional)
            
        Returns:
            Dictionary containing authentication tokens and user data
            
        Raises:
            HTTPException: 401 if credentials are invalid
            HTTPException: 429 if rate limit exceeded
        """
        # Check rate limit if IP provided
        if ip_address:
            self._check_rate_limit(ip_address)
        
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        
        # Verify password
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Generate tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        
        # Store refresh token in Redis for logout functionality
        refresh_token_key = f"refresh_token:{user.id}"
        try:
            self.redis_client.setex(
                refresh_token_key,
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                refresh_token
            )
        except redis.RedisError as e:
            print(f"Redis error storing refresh token: {e}")
        
        # Reset rate limit on successful login
        if ip_address:
            self._reset_rate_limit(ip_address)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "reputation_points": user.reputation_points,
                "current_level": user.current_level
            }
        }
    
    def logout(self, user_id: UUID) -> bool:
        """
        Invalidate user session and tokens.
        
        Removes refresh token from Redis to prevent token refresh.
        
        Args:
            user_id: User ID
            
        Returns:
            True if logout successful
        """
        refresh_token_key = f"refresh_token:{user_id}"
        
        try:
            self.redis_client.delete(refresh_token_key)
            return True
        except redis.RedisError as e:
            print(f"Redis error during logout: {e}")
            # Even if Redis fails, consider logout successful
            # Access tokens will expire naturally
            return True
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new access token and same refresh token
            
        Raises:
            HTTPException: 401 if refresh token is invalid or expired
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Verify token type
            token_type = payload.get("type")
            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Get user ID from token
            user_id_str = payload.get("sub")
            if user_id_str is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user_id = UUID(user_id_str)
            
            # Verify refresh token exists in Redis (not logged out)
            refresh_token_key = f"refresh_token:{user_id}"
            try:
                stored_token = self.redis_client.get(refresh_token_key)
                if stored_token != refresh_token:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            except redis.RedisError as e:
                # If Redis is unavailable, allow refresh but log error
                print(f"Redis error verifying refresh token: {e}")
            
            # Verify user still exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Generate new access token
            new_access_token = create_access_token(subject=str(user_id))
            
            return {
                "access_token": new_access_token,
                "refresh_token": refresh_token,  # Return same refresh token
                "token_type": "bearer"
            }
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def verify_token(self, token: str) -> User:
        """
        Verify JWT token and return associated user.
        
        Args:
            token: JWT access token
            
        Returns:
            User object if token is valid
            
        Raises:
            HTTPException: 401 if token is invalid or expired
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Verify token type
            token_type = payload.get("type")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Get user ID from token
            user_id_str = payload.get("sub")
            if user_id_str is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user_id = UUID(user_id_str)
            
            # Get user from database
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return user
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
