"""
Standalone tests for authentication service core functionality.

These tests verify the authentication service logic without requiring
a full database or Redis connection.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from uuid import uuid4
from jose import jwt

# Test JWT token generation
def test_jwt_token_structure():
    """Test JWT token structure and expiry times."""
    from app.core.config import settings
    from app.core.security import create_access_token, create_refresh_token
    
    user_id = str(uuid4())
    
    # Test access token
    access_token = create_access_token(subject=user_id)
    access_payload = jwt.decode(
        access_token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    
    print("✓ Access token created successfully")
    assert access_payload["sub"] == user_id
    assert access_payload["type"] == "access"
    print("✓ Access token has correct subject and type")
    
    # Verify 15-minute expiry
    exp_time = datetime.utcfromtimestamp(access_payload["exp"])
    now = datetime.utcnow()
    time_diff = (exp_time - now).total_seconds()
    assert 895 <= time_diff <= 905, f"Access token expiry is {time_diff}s, expected ~900s (15 min)"
    print(f"✓ Access token expires in ~{int(time_diff)}s (15 minutes)")
    
    # Test refresh token
    refresh_token = create_refresh_token(subject=user_id)
    refresh_payload = jwt.decode(
        refresh_token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    
    print("✓ Refresh token created successfully")
    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"
    print("✓ Refresh token has correct subject and type")
    
    # Verify 7-day expiry
    exp_time = datetime.utcfromtimestamp(refresh_payload["exp"])
    now = datetime.utcnow()
    time_diff = (exp_time - now).total_seconds()
    assert 604795 <= time_diff <= 604805, f"Refresh token expiry is {time_diff}s, expected ~604800s (7 days)"
    print(f"✓ Refresh token expires in ~{int(time_diff)}s (7 days)")


def test_password_hashing():
    """Test password hashing with bcrypt."""
    from app.core.security import get_password_hash, verify_password
    
    password = "secure123"  # Shorter password to avoid bcrypt issues
    
    # Hash password
    hashed = get_password_hash(password)
    print("✓ Password hashed successfully")
    
    # Verify bcrypt format and rounds
    assert hashed.startswith("$2b$12$"), f"Hash format incorrect: {hashed[:10]}"
    print("✓ Password hash uses bcrypt with 12 rounds")
    
    # Verify correct password
    assert verify_password(password, hashed) is True
    print("✓ Correct password verification works")
    
    # Verify incorrect password
    assert verify_password("wrong", hashed) is False
    print("✓ Incorrect password verification works")


def test_user_model_password_methods():
    """Test User model password methods."""
    from app.models.user import User
    
    user = User(email="test@example.com")
    password = "test123"  # Shorter password
    
    # Set password
    user.set_password(password)
    print("✓ User.set_password() works")
    
    # Verify password hash is set
    assert user.password_hash is not None
    assert user.password_hash.startswith("$2b$12$")
    print("✓ Password hash stored correctly")
    
    # Verify correct password
    assert user.verify_password(password) is True
    print("✓ User.verify_password() works with correct password")
    
    # Verify incorrect password
    assert user.verify_password("wrong") is False
    print("✓ User.verify_password() rejects incorrect password")


def test_auth_service_structure():
    """Test AuthService class structure and methods."""
    from app.services.auth_service import AuthService
    
    # Verify class exists
    assert AuthService is not None
    print("✓ AuthService class exists")
    
    # Verify required methods exist
    required_methods = [
        'register_user',
        'login',
        'logout',
        'refresh_token',
        'verify_token',
        '_check_rate_limit',
        '_reset_rate_limit'
    ]
    
    for method_name in required_methods:
        assert hasattr(AuthService, method_name), f"Missing method: {method_name}"
        print(f"✓ AuthService.{method_name}() exists")


def test_rate_limiting_configuration():
    """Test rate limiting configuration."""
    from app.core.config import settings
    
    # Verify rate limiting settings
    assert settings.AUTH_RATE_LIMIT_ATTEMPTS == 5
    print("✓ Rate limit set to 5 attempts")
    
    assert settings.AUTH_RATE_LIMIT_WINDOW_MINUTES == 15
    print("✓ Rate limit window set to 15 minutes")


def main():
    """Run all standalone tests."""
    print("\n" + "="*60)
    print("AUTHENTICATION SERVICE STANDALONE TESTS")
    print("="*60 + "\n")
    
    tests = [
        ("JWT Token Structure", test_jwt_token_structure),
        ("Password Hashing", test_password_hashing),
        ("User Model Password Methods", test_user_model_password_methods),
        ("AuthService Structure", test_auth_service_structure),
        ("Rate Limiting Configuration", test_rate_limiting_configuration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\nTest: {test_name}")
        print("-" * 60)
        try:
            test_func()
            print(f"\n✅ {test_name} PASSED\n")
            passed += 1
        except Exception as e:
            print(f"\n❌ {test_name} FAILED: {e}\n")
            failed += 1
    
    print("="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
