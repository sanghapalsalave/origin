"""
Security utilities for authentication and encryption.

Implements Requirements:
- 15.1: Password hashing with bcrypt (12 rounds minimum)
- 15.2: Sensitive data encryption at rest using AES-256
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os
from app.core.config import settings

# Password hashing context with bcrypt (12 rounds minimum)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """
    Create JWT refresh token.
    
    Args:
        subject: Token subject (usually user ID)
        
    Returns:
        Encoded JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with 12 rounds.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)



# Encryption utilities for sensitive data at rest (AES-256)
class DataEncryption:
    """
    Utility class for encrypting and decrypting sensitive data at rest.
    
    Uses AES-256 encryption via Fernet (symmetric encryption).
    Implements Requirement 15.2: Sensitive data encryption at rest.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key.
        
        Args:
            encryption_key: Base64-encoded encryption key. If None, uses settings.
        """
        if encryption_key is None:
            # Use encryption key from settings or generate one
            encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
            if encryption_key is None:
                # Generate a key if not provided (for development only)
                encryption_key = Fernet.generate_key().decode()
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.fernet = Fernet(encryption_key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data using AES-256.
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Base64-encoded encrypted data
        """
        if data is None:
            return None
        
        # Convert to bytes if string
        if isinstance(data, str):
            data = data.encode()
        
        # Encrypt and return as base64 string
        encrypted = self.fernet.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted plain text data
        """
        if encrypted_data is None:
            return None
        
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        
        # Decrypt and return as string
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode()


# Global encryption instance
_encryption_instance = None


def get_encryption() -> DataEncryption:
    """
    Get global encryption instance (singleton pattern).
    
    Returns:
        DataEncryption instance
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption()
    return _encryption_instance


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data using AES-256.
    
    Implements Requirement 15.2: Sensitive data encryption at rest.
    
    Args:
        data: Plain text data to encrypt
        
    Returns:
        Encrypted data as base64 string
    """
    return get_encryption().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data: Encrypted data as base64 string
        
    Returns:
        Decrypted plain text data
    """
    return get_encryption().decrypt(encrypted_data)


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for AES-256.
    
    Returns:
        Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()
