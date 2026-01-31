"""
Unit tests for authentication service.

Tests registration, login, logout, token refresh, and rate limiting.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from jose import jwt
from fastapi import HTTPException
import redis

from app.services.auth_service import AuthService
from app.models.user import User
from app.core.config import settings


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = Mock(spec=redis.Redis)
    redis_mock.get = Mock(return_value=None)
    redis_mock.setex = Mock(return_value=True)
    redis_mock.incr = Mock(return_value=1)
    redis_mock.delete = Mock(return_value=True)
    redis_mock.ttl = Mock(return_value=900)
    return redis_mock


@pytest.fixture
def auth_service(mock_db, mock_redis):
    """Create AuthService instance with mocked dependencies."""
    return AuthService(db=mock_db, redis_client=mock_redis)


class TestRegisterUser:
    """Tests for user registration."""
    
    def test_register_user_success(self, auth_service, mock_db, mock_redis):
        """Test successful user registration."""
        # Mock database query to return no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Call register_user
        result = auth_service.register_user(
            email="test@example.com",
            password="securepassword123",
            profile_data={},
            ip_address="192.168.1.1"
        )
        
        # Verify user was added to database
        assert mock_db.add.called
        assert mock_db.commit.called
        
        # Verify tokens are returned
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert "user" in result
        assert result["user"]["email"] == "test@example.com"
        
        # Verify rate limit was checked and reset
        assert mock_redis.get.called
        assert mock_redis.delete.called
    
    def test_register_user_duplicate_email(self, auth_service, mock_db):
        """Test registration with existing email."""
        # Mock database query to return existing user
        existing_user = User(email="test@example.com")
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        # Attempt registration with duplicate email
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register_user(
                email="test@example.com",
                password="securepassword123",
                profile_data={}
            )
        
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail
    
    def test_register_user_weak_password(self, auth_service, mock_db):
        """Test registration with weak password."""
        # Mock database query to return no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt registration with weak password
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register_user(
                email="test@example.com",
                password="weak",
                profile_data={}
            )
        
        assert exc_info.value.status_code == 400
        assert "at least 8 characters" in exc_info.value.detail
    
    def test_register_user_rate_limit_exceeded(self, auth_service, mock_db, mock_redis):
        """Test registration with rate limit exceeded."""
        # Mock Redis to return rate limit exceeded
        mock_redis.get.return_value = "5"  # Already at limit
        
        # Attempt registration
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register_user(
                email="test@example.com",
                password="securepassword123",
                profile_data={},
                ip_address="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 429
        assert "Too many authentication attempts" in exc_info.value.detail


class TestLogin:
    """Tests for user login."""
    
    def test_login_success(self, auth_service, mock_db, mock_redis):
        """Test successful login."""
        # Create mock user
        user = User(email="test@example.com")
        user.id = uuid4()
        user.set_password("securepassword123")
        user.reputation_points = 100
        user.current_level = 2
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Call login
        result = auth_service.login(
            email="test@example.com",
            password="securepassword123",
            ip_address="192.168.1.1"
        )
        
        # Verify tokens are returned
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert "user" in result
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["reputation_points"] == 100
        assert result["user"]["current_level"] == 2
        
        # Verify refresh token stored in Redis
        assert mock_redis.setex.called
        
        # Verify rate limit was checked and reset
        assert mock_redis.get.called
        assert mock_redis.delete.called
    
    def test_login_invalid_email(self, auth_service, mock_db, mock_redis):
        """Test login with invalid email."""
        # Mock database query to return no user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt login
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(
                email="nonexistent@example.com",
                password="password123",
                ip_address="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail
    
    def test_login_invalid_password(self, auth_service, mock_db, mock_redis):
        """Test login with invalid password."""
        # Create mock user
        user = User(email="test@example.com")
        user.set_password("correctpassword")
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Attempt login with wrong password
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(
                email="test@example.com",
                password="wrongpassword",
                ip_address="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail
    
    def test_login_rate_limit_exceeded(self, auth_service, mock_db, mock_redis):
        """Test login with rate limit exceeded."""
        # Mock Redis to return rate limit exceeded
        mock_redis.get.return_value = "5"  # Already at limit
        
        # Attempt login
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(
                email="test@example.com",
                password="password123",
                ip_address="192.168.1.1"
            )
        
        assert exc_info.value.status_code == 429
        assert "Too many authentication attempts" in exc_info.value.detail
    
    def test_login_without_ip_address(self, auth_service, mock_db, mock_redis):
        """Test login without IP address (no rate limiting)."""
        # Create mock user
        user = User(email="test@example.com")
        user.id = uuid4()
        user.set_password("securepassword123")
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Call login without IP address
        result = auth_service.login(
            email="test@example.com",
            password="securepassword123"
        )
        
        # Verify tokens are returned
        assert "access_token" in result
        assert "refresh_token" in result
        
        # Verify rate limit was NOT checked (no IP provided)
        # Redis get should not be called for rate limiting
        # (it may be called for storing refresh token)


class TestLogout:
    """Tests for user logout."""
    
    def test_logout_success(self, auth_service, mock_redis):
        """Test successful logout."""
        user_id = uuid4()
        
        # Call logout
        result = auth_service.logout(user_id)
        
        # Verify refresh token was deleted from Redis
        assert result is True
        assert mock_redis.delete.called
        mock_redis.delete.assert_called_with(f"refresh_token:{user_id}")
    
    def test_logout_redis_error(self, auth_service, mock_redis):
        """Test logout with Redis error (should still succeed)."""
        user_id = uuid4()
        
        # Mock Redis to raise error
        mock_redis.delete.side_effect = redis.RedisError("Connection failed")
        
        # Call logout
        result = auth_service.logout(user_id)
        
        # Should still return True even with Redis error
        assert result is True


class TestRefreshToken:
    """Tests for token refresh."""
    
    def test_refresh_token_success(self, auth_service, mock_db, mock_redis):
        """Test successful token refresh."""
        user_id = uuid4()
        
        # Create valid refresh token
        refresh_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(days=7),
                "sub": str(user_id),
                "type": "refresh"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock Redis to return stored token
        mock_redis.get.return_value = refresh_token
        
        # Mock database query
        user = User(email="test@example.com")
        user.id = user_id
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Call refresh_token
        result = auth_service.refresh_token(refresh_token)
        
        # Verify new access token is returned
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["refresh_token"] == refresh_token  # Same refresh token
        assert result["token_type"] == "bearer"
    
    def test_refresh_token_invalid_token(self, auth_service):
        """Test refresh with invalid token."""
        # Attempt refresh with invalid token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_token("invalid_token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired" in exc_info.value.detail
    
    def test_refresh_token_expired(self, auth_service):
        """Test refresh with expired token."""
        user_id = uuid4()
        
        # Create expired refresh token
        expired_token = jwt.encode(
            {
                "exp": datetime.utcnow() - timedelta(days=1),  # Expired
                "sub": str(user_id),
                "type": "refresh"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Attempt refresh with expired token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_token(expired_token)
        
        assert exc_info.value.status_code == 401
    
    def test_refresh_token_wrong_type(self, auth_service):
        """Test refresh with access token instead of refresh token."""
        user_id = uuid4()
        
        # Create access token (wrong type)
        access_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(minutes=15),
                "sub": str(user_id),
                "type": "access"  # Wrong type
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Attempt refresh with access token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_token(access_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail
    
    def test_refresh_token_revoked(self, auth_service, mock_db, mock_redis):
        """Test refresh with revoked token (logged out)."""
        user_id = uuid4()
        
        # Create valid refresh token
        refresh_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(days=7),
                "sub": str(user_id),
                "type": "refresh"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock Redis to return different token (original was revoked)
        mock_redis.get.return_value = "different_token"
        
        # Attempt refresh with revoked token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_token(refresh_token)
        
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail
    
    def test_refresh_token_user_not_found(self, auth_service, mock_db, mock_redis):
        """Test refresh when user no longer exists."""
        user_id = uuid4()
        
        # Create valid refresh token
        refresh_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(days=7),
                "sub": str(user_id),
                "type": "refresh"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock Redis to return stored token
        mock_redis.get.return_value = refresh_token
        
        # Mock database query to return no user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt refresh
        with pytest.raises(HTTPException) as exc_info:
            auth_service.refresh_token(refresh_token)
        
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail


class TestVerifyToken:
    """Tests for token verification."""
    
    def test_verify_token_success(self, auth_service, mock_db):
        """Test successful token verification."""
        user_id = uuid4()
        
        # Create valid access token
        access_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(minutes=15),
                "sub": str(user_id),
                "type": "access"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock database query
        user = User(email="test@example.com")
        user.id = user_id
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Call verify_token
        result = auth_service.verify_token(access_token)
        
        # Verify user is returned
        assert result == user
        assert result.id == user_id
    
    def test_verify_token_invalid(self, auth_service):
        """Test verification with invalid token."""
        # Attempt verification with invalid token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token("invalid_token")
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_expired(self, auth_service):
        """Test verification with expired token."""
        user_id = uuid4()
        
        # Create expired access token
        expired_token = jwt.encode(
            {
                "exp": datetime.utcnow() - timedelta(minutes=1),  # Expired
                "sub": str(user_id),
                "type": "access"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Attempt verification with expired token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(expired_token)
        
        assert exc_info.value.status_code == 401
    
    def test_verify_token_wrong_type(self, auth_service):
        """Test verification with refresh token instead of access token."""
        user_id = uuid4()
        
        # Create refresh token (wrong type)
        refresh_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(days=7),
                "sub": str(user_id),
                "type": "refresh"  # Wrong type
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Attempt verification with refresh token
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(refresh_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token type" in exc_info.value.detail
    
    def test_verify_token_user_not_found(self, auth_service, mock_db):
        """Test verification when user no longer exists."""
        user_id = uuid4()
        
        # Create valid access token
        access_token = jwt.encode(
            {
                "exp": datetime.utcnow() + timedelta(minutes=15),
                "sub": str(user_id),
                "type": "access"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Mock database query to return no user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt verification
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(access_token)
        
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limit_first_attempt(self, auth_service, mock_redis):
        """Test rate limiting on first attempt."""
        # Mock Redis to return None (first attempt)
        mock_redis.get.return_value = None
        
        # Check rate limit
        auth_service._check_rate_limit("192.168.1.1")
        
        # Verify counter was set with expiry
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "auth_rate_limit:192.168.1.1"
        assert call_args[0][1] == settings.AUTH_RATE_LIMIT_WINDOW_MINUTES * 60
        assert call_args[0][2] == 1
    
    def test_rate_limit_subsequent_attempts(self, auth_service, mock_redis):
        """Test rate limiting on subsequent attempts."""
        # Mock Redis to return attempt count
        mock_redis.get.return_value = "3"
        
        # Check rate limit
        auth_service._check_rate_limit("192.168.1.1")
        
        # Verify counter was incremented
        assert mock_redis.incr.called
        mock_redis.incr.assert_called_with("auth_rate_limit:192.168.1.1")
    
    def test_rate_limit_at_threshold(self, auth_service, mock_redis):
        """Test rate limiting at threshold (5 attempts)."""
        # Mock Redis to return limit threshold
        mock_redis.get.return_value = str(settings.AUTH_RATE_LIMIT_ATTEMPTS)
        
        # Check rate limit should raise exception
        with pytest.raises(HTTPException) as exc_info:
            auth_service._check_rate_limit("192.168.1.1")
        
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers
    
    def test_rate_limit_reset(self, auth_service, mock_redis):
        """Test rate limit reset after successful authentication."""
        # Reset rate limit
        auth_service._reset_rate_limit("192.168.1.1")
        
        # Verify counter was deleted
        assert mock_redis.delete.called
        mock_redis.delete.assert_called_with("auth_rate_limit:192.168.1.1")
    
    def test_rate_limit_redis_error(self, auth_service, mock_redis):
        """Test rate limiting with Redis error (should not block)."""
        # Mock Redis to raise error
        mock_redis.get.side_effect = redis.RedisError("Connection failed")
        
        # Check rate limit should not raise exception
        try:
            auth_service._check_rate_limit("192.168.1.1")
            # Should succeed without raising
        except HTTPException:
            pytest.fail("Rate limit check should not raise exception on Redis error")


class TestTokenExpiry:
    """Tests for token expiry times."""
    
    def test_access_token_expiry_15_minutes(self, auth_service, mock_db, mock_redis):
        """Test that access tokens expire in 15 minutes."""
        # Create mock user
        user = User(email="test@example.com")
        user.id = uuid4()
        user.set_password("password123")
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Login to get tokens
        result = auth_service.login(
            email="test@example.com",
            password="password123"
        )
        
        # Decode access token
        access_token = result["access_token"]
        payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify expiry is approximately 15 minutes
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds()
        
        # Should be close to 15 minutes (900 seconds), allow 5 second tolerance
        assert 895 <= time_diff <= 905
    
    def test_refresh_token_expiry_7_days(self, auth_service, mock_db, mock_redis):
        """Test that refresh tokens expire in 7 days."""
        # Create mock user
        user = User(email="test@example.com")
        user.id = uuid4()
        user.set_password("password123")
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = user
        
        # Login to get tokens
        result = auth_service.login(
            email="test@example.com",
            password="password123"
        )
        
        # Decode refresh token
        refresh_token = result["refresh_token"]
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify expiry is approximately 7 days
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds()
        
        # Should be close to 7 days (604800 seconds), allow 5 second tolerance
        assert 604795 <= time_diff <= 604805
