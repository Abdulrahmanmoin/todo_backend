"""
Authentication service with JWT handling for the Todo application.
This module handles user registration, authentication, password hashing,
JWT token creation/verification, and token refresh functionality.
"""

import os
import secrets
import hashlib
import hmac
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a JWT token and return its payload."""
    from jose import jwt
    from ..config import settings
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenData(BaseModel):
    """Token data model for JWT payload."""
    user_id: str
    username: str
    exp: Optional[float] = None  # Use float to handle timestamp values properly
    iat: Optional[float] = None  # Use float to handle timestamp values properly
    token_type: str = "access"  # Default for access tokens when creating


class RefreshTokenData(BaseModel):
    """Refresh token data model for JWT payload."""
    user_id: str
    username: str
    exp: Optional[float] = None  # Use float to handle timestamp values properly
    iat: Optional[float] = None  # Use float to handle timestamp values properly
    token_type: str = "refresh"


class AuthException(Exception):
    """Custom exception for authentication errors."""
    pass


class PasswordStrengthError(Exception):
    """Exception raised for weak passwords."""
    pass


class RefreshToken:
    """Class to represent a refresh token with metadata."""
    def __init__(self, token_id: str, user_id: str, username: str,
                 token_hash: str, expires_at: datetime, created_at: datetime,
                 is_revoked: bool = False):
        # Ensure datetime objects are timezone-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        self.token_id = token_id
        self.user_id = user_id
        self.username = username
        self.token_hash = token_hash  # Hash of the original refresh token
        self.expires_at = expires_at
        self.created_at = created_at
        self.is_revoked = is_revoked


class AuthService:
    """Authentication service class handling all auth-related operations."""

    def __init__(self):
        """Initialize the auth service with required settings."""
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = REFRESH_TOKEN_EXPIRE_DAYS
        # In-memory storage for refresh tokens (in production, use a database)
        self.refresh_tokens_storage: Dict[str, RefreshToken] = {}

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if passwords match, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, username: str) -> str:
        """
        Create an access token with expiration.

        Args:
            user_id: Unique identifier for the user
            username: Username for the token payload

        Returns:
            Encoded JWT access token
        """
        current_time = datetime.now(timezone.utc)
        expire = current_time + timedelta(minutes=self.access_token_expire_minutes)
        token_data = TokenData(
            user_id=user_id,
            username=username,
            exp=expire.timestamp(),
            iat=current_time.timestamp(),
            token_type="access"
        )
        return jwt.encode(token_data.dict(), self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str, username: str) -> str:
        """
        Create a refresh token with longer expiration.

        Args:
            user_id: Unique identifier for the user
            username: Username for the token payload

        Returns:
            Encoded JWT refresh token
        """
        current_time = datetime.now(timezone.utc)
        expire = current_time + timedelta(days=self.refresh_token_expire_days)
        token_data = RefreshTokenData(
            user_id=user_id,
            username=username,
            exp=expire.timestamp(),
            iat=current_time.timestamp(),
            token_type="refresh"
        )
        return jwt.encode(token_data.dict(), self.secret_key, algorithm=self.algorithm)

    def verify_access_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode an access token.

        Args:
            token: JWT access token to verify

        Returns:
            TokenData object if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_data = TokenData(**payload)

            # Check if token is an access token
            if token_data.token_type != "access":
                return None

            # Check if token has expired
            current_time = datetime.now(timezone.utc).timestamp()
            if token_data.exp and current_time > token_data.exp:
                return None

            return token_data
        except JWTError:
            return None

    def verify_refresh_token(self, token: str) -> Optional[RefreshTokenData]:
        """
        Verify and decode a refresh token.

        Args:
            token: JWT refresh token to verify

        Returns:
            RefreshTokenData object if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_data = RefreshTokenData(**payload)

            # Check if token is a refresh token
            if token_data.token_type != "refresh":
                return None

            # Check if token has expired
            current_time = datetime.now(timezone.utc).timestamp()
            if token_data.exp and current_time > token_data.exp:
                return None

            return token_data
        except JWTError:
            return None

    def create_tokens(self, user_id: str, username: str) -> Dict[str, str]:
        """
        Create both access and refresh tokens for a user.

        Args:
            user_id: Unique identifier for the user
            username: Username for the token payload

        Returns:
            Dictionary containing both access and refresh tokens
        """
        access_token = self.create_access_token(user_id, username)
        refresh_token = self.create_refresh_token(user_id, username)

        # Store the refresh token in our storage system
        self.store_refresh_token(user_id, username, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate a new access token using a refresh token with proper validation and security.
        Implements refresh token rotation to prevent reuse of stolen tokens.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new access token and new refresh token if refresh is successful,
            None otherwise
        """
        # First verify the refresh token is valid JWT
        token_data = self.verify_refresh_token(refresh_token)
        if not token_data:
            return None

        # Hash the provided refresh token to compare with stored hash
        token_hash = self._hash_token(refresh_token)

        # Find the matching stored token by user_id and token_hash
        stored_token = None
        stored_token_id = None
        for token_id, token_obj in self.refresh_tokens_storage.items():
            if (token_obj.user_id == token_data.user_id and
                token_obj.token_hash == token_hash and
                not token_obj.is_revoked and
                datetime.now(timezone.utc) <= token_obj.expires_at):
                stored_token = token_obj
                stored_token_id = token_id
                break

        if not stored_token:
            # Token not found in storage, possibly already used or invalid
            return None

        # Additional security: Validate token consistency
        # Ensure the JWT token data matches the stored token data
        if (token_data.user_id != stored_token.user_id or
            token_data.username != stored_token.username):
            # Mismatch between JWT and stored token - possible token tampering
            self.revoke_refresh_token(stored_token_id)  # Revoke the suspicious token
            return None

        # Create new tokens
        new_access_token = self.create_access_token(
            user_id=token_data.user_id,
            username=token_data.username
        )
        new_refresh_token = self.create_refresh_token(
            user_id=token_data.user_id,
            username=token_data.username
        )

        # Revoke the old refresh token to implement rotation
        self.revoke_refresh_token(stored_token_id)

        # Store the new refresh token
        self.store_refresh_token(token_data.user_id, token_data.username, new_refresh_token)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,  # Include new refresh token for rotation
            "token_type": "bearer"
        }

    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for secure storage.

        Args:
            token: The token string to hash

        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def store_refresh_token(self, user_id: str, username: str, refresh_token: str) -> str:
        """
        Store a refresh token in memory with metadata.

        Args:
            user_id: The user ID associated with the token
            username: The username associated with the token
            refresh_token: The raw refresh token to store (will be hashed)

        Returns:
            The token ID for reference
        """
        token_id = str(uuid.uuid4())
        token_hash = self._hash_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        created_at = datetime.now(timezone.utc)

        refresh_token_obj = RefreshToken(
            token_id=token_id,
            user_id=user_id,
            username=username,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=created_at
        )

        self.refresh_tokens_storage[token_id] = refresh_token_obj
        return token_id

    def get_refresh_token(self, token_id: str) -> Optional[RefreshToken]:
        """
        Retrieve a refresh token from storage by ID.

        Args:
            token_id: The ID of the refresh token to retrieve

        Returns:
            RefreshToken object if found and valid, None otherwise
        """
        if token_id not in self.refresh_tokens_storage:
            return None

        token_obj = self.refresh_tokens_storage[token_id]

        # Check if token is expired or revoked
        if (token_obj.is_revoked or
            datetime.now(timezone.utc) > token_obj.expires_at):
            # Remove expired/revoked token
            del self.refresh_tokens_storage[token_id]
            return None

        return token_obj

    def revoke_refresh_token(self, token_id: str) -> bool:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token_id: The ID of the refresh token to revoke

        Returns:
            True if token was successfully revoked, False otherwise
        """
        if token_id in self.refresh_tokens_storage:
            self.refresh_tokens_storage[token_id].is_revoked = True
            return True
        return False

    def revoke_all_user_refresh_tokens(self, user_id: str) -> int:
        """
        Revoke all refresh tokens for a specific user.

        Args:
            user_id: The user ID whose tokens should be revoked

        Returns:
            Number of tokens revoked
        """
        revoked_count = 0
        for token_id, token_obj in list(self.refresh_tokens_storage.items()):
            if token_obj.user_id == user_id and not token_obj.is_revoked:
                token_obj.is_revoked = True
                revoked_count += 1
        return revoked_count

    def cleanup_expired_tokens(self) -> int:
        """
        Remove all expired tokens from storage.

        Returns:
            Number of tokens removed
        """
        removed_count = 0
        current_time = datetime.now(timezone.utc)

        for token_id, token_obj in list(self.refresh_tokens_storage.items()):
            if current_time > token_obj.expires_at:
                del self.refresh_tokens_storage[token_id]
                removed_count += 1

        return removed_count

    def authenticate_user(self, stored_password_hash: str, provided_password: str) -> bool:
        """
        Authenticate a user by comparing passwords.

        Args:
            stored_password_hash: Hashed password stored in the database
            provided_password: Plain text password provided by user

        Returns:
            True if authentication is successful, False otherwise
        """
        return self.verify_password(provided_password, stored_password_hash)

    def validate_username(self, username: str) -> bool:
        """
        Validate username format according to security requirements.

        Args:
            username: Username to validate

        Returns:
            True if username meets requirements, raises exception otherwise
        """
        # Check that username is not empty
        if not username or len(username.strip()) == 0:
            raise ValueError("Username cannot be empty")

        # Check length (3-50 characters)
        if len(username) < 3 or len(username) > 50:
            raise ValueError("Username must be between 3 and 50 characters")

        # Check for valid characters (alphanumeric and underscores/hyphens)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain alphanumeric characters, underscores, and hyphens")

        return True

    def validate_password_strength(self, password: str) -> bool:
        """
        Validate password strength according to security requirements.

        Args:
            password: Plain text password to validate

        Returns:
            True if password meets requirements, raises exception otherwise
        """
        # Check minimum length
        if len(password) < 8:
            raise PasswordStrengthError("Password must be at least 8 characters long")

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise PasswordStrengthError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise PasswordStrengthError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not re.search(r'\d', password):
            raise PasswordStrengthError("Password must contain at least one digit")

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise PasswordStrengthError("Password must contain at least one special character")

        return True

    def register_user(self, password: str) -> str:
        """
        Register a new user by hashing their password.

        Args:
            password: Plain text password to hash for storage

        Returns:
            Hashed password for storage in database
        """
        # Validate password strength before hashing
        self.validate_password_strength(password)
        return self.hash_password(password)


# Global instance of the auth service
auth_service = AuthService()


# Convenience functions for external use
def hash_password(password: str) -> str:
    """Hash a password using the global auth service."""
    return auth_service.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using the global auth service."""
    return auth_service.verify_password(plain_password, hashed_password)


def create_access_token(user_id: str, username: str) -> str:
    """Create an access token using the global auth service."""
    return auth_service.create_access_token(user_id, username)


def create_refresh_token(user_id: str, username: str) -> str:
    """Create a refresh token using the global auth service."""
    return auth_service.create_refresh_token(user_id, username)


def verify_access_token(token: str) -> Optional[TokenData]:
    """Verify an access token using the global auth service."""
    return auth_service.verify_access_token(token)


def verify_refresh_token(token: str) -> Optional[RefreshTokenData]:
    """Verify a refresh token using the global auth service."""
    return auth_service.verify_refresh_token(token)


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """Refresh an access token using the global auth service."""
    return auth_service.refresh_access_token(refresh_token)


def store_refresh_token(user_id: str, username: str, refresh_token: str) -> str:
    """Store a refresh token using the global auth service."""
    return auth_service.store_refresh_token(user_id, username, refresh_token)


def revoke_refresh_token(token_id: str) -> bool:
    """Revoke a refresh token using the global auth service."""
    return auth_service.revoke_refresh_token(token_id)


def revoke_all_user_refresh_tokens(user_id: str) -> int:
    """Revoke all refresh tokens for a user using the global auth service."""
    return auth_service.revoke_all_user_refresh_tokens(user_id)


def cleanup_expired_tokens() -> int:
    """Clean up expired tokens using the global auth service."""
    return auth_service.cleanup_expired_tokens()


def authenticate_user(stored_password_hash: str, provided_password: str) -> bool:
    """Authenticate a user using the global auth service."""
    return auth_service.authenticate_user(stored_password_hash, provided_password)


def register_user(password: str) -> str:
    """Register a user by hashing their password using the global auth service."""
    return auth_service.register_user(password)