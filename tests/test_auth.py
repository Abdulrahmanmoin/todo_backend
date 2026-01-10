"""
Test cases for the authentication service.
"""

import os
import pytest
from datetime import datetime, timedelta
from backend.src.services.auth import (
    AuthService,
    auth_service,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    refresh_access_token,
    authenticate_user,
    register_user,
    PasswordStrengthError,
    revoke_all_user_refresh_tokens
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    # Verify the password matches the hash
    assert verify_password(password, hashed) is True

    # Verify incorrect password doesn't match
    assert verify_password("WrongPassword", hashed) is False


def test_password_strength_validation():
    """Test password strength validation."""
    # Valid password
    valid_password = "ValidPass123!"
    assert auth_service.validate_password_strength(valid_password) is True

    # Invalid passwords
    with pytest.raises(PasswordStrengthError):
        auth_service.validate_password_strength("weak")  # Too short

    with pytest.raises(PasswordStrengthError):
        auth_service.validate_password_strength("nouppercase123!")  # No uppercase

    with pytest.raises(PasswordStrengthError):
        auth_service.validate_password_strength("NOLOWERCASE123!")  # No lowercase

    with pytest.raises(PasswordStrengthError):
        auth_service.validate_password_strength("NoDigits!")  # No digits

    with pytest.raises(PasswordStrengthError):
        auth_service.validate_password_strength("NoSpecialChar123")  # No special char


def test_username_validation():
    """Test username validation."""
    # Valid usernames
    assert auth_service.validate_username("testuser") is True
    assert auth_service.validate_username("user_123") is True
    assert auth_service.validate_username("user-123") is True

    # Invalid usernames
    with pytest.raises(ValueError):
        auth_service.validate_username("")  # Empty

    with pytest.raises(ValueError):
        auth_service.validate_username("ab")  # Too short

    with pytest.raises(ValueError):
        auth_service.validate_username("a" * 51)  # Too long

    with pytest.raises(ValueError):
        auth_service.validate_username("user@name")  # Invalid character


def test_register_user():
    """Test user registration with password validation."""
    password = "ValidPass123!"
    hashed = register_user(password)

    # Verify the password was hashed correctly
    assert verify_password(password, hashed) is True


def test_access_token_creation():
    """Test access token creation and verification."""
    user_id = "123"
    username = "testuser"

    token = create_access_token(user_id, username)
    token_data = verify_access_token(token)

    assert token_data is not None
    assert token_data.user_id == user_id
    assert token_data.username == username
    assert token_data.token_type == "access"


def test_refresh_token_creation():
    """Test refresh token creation and verification."""
    user_id = "123"
    username = "testuser"

    token = create_refresh_token(user_id, username)
    token_data = verify_refresh_token(token)

    assert token_data is not None
    assert token_data.user_id == user_id
    assert token_data.username == username
    assert token_data.token_type == "refresh"


def test_token_expiration():
    """Test that expired tokens are properly rejected."""
    # Create a token that expired 1 hour ago
    user_id = "123"
    username = "testuser"

    # Manually create an expired token
    from jose import jwt
    import time

    expired_payload = {
        "user_id": user_id,
        "username": username,
        "exp": time.time() - 3600,  # Expired 1 hour ago
        "iat": time.time() - 3700,
        "token_type": "access"
    }

    secret_key = os.getenv("JWT_SECRET_KEY", "test_secret")
    expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")

    # Verify that the expired token is rejected
    assert verify_access_token(expired_token) is None


def test_token_refresh():
    """Test refreshing an access token with a refresh token."""
    user_id = "123"
    username = "testuser"

    # Create both access and refresh tokens using the create_tokens method
    tokens = auth_service.create_tokens(user_id, username)
    refresh_token = tokens["refresh_token"]

    # Use it to refresh the access token
    result = refresh_access_token(refresh_token)

    assert result is not None
    assert "access_token" in result
    assert "refresh_token" in result  # New refresh token should be returned for rotation
    assert result["token_type"] == "bearer"

    # Verify the new access token
    new_token_data = verify_access_token(result["access_token"])
    assert new_token_data is not None
    assert new_token_data.user_id == user_id
    assert new_token_data.username == username

    # Verify the new refresh token is different from the old one
    assert result["refresh_token"] != refresh_token

    # The old refresh token should no longer be valid (due to rotation)
    old_token_result = refresh_access_token(refresh_token)
    assert old_token_result is None


def test_user_authentication():
    """Test user authentication."""
    password = "ValidPass123!"
    hashed = hash_password(password)

    # Valid authentication
    assert authenticate_user(hashed, password) is True

    # Invalid authentication
    assert authenticate_user(hashed, "WrongPassword") is False


def test_create_tokens():
    """Test creating both access and refresh tokens."""
    user_id = "123"
    username = "testuser"

    tokens = auth_service.create_tokens(user_id, username)

    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "token_type" in tokens
    assert tokens["token_type"] == "bearer"

    # Verify both tokens are valid
    access_token_data = verify_access_token(tokens["access_token"])
    assert access_token_data is not None
    assert access_token_data.user_id == user_id
    assert access_token_data.username == username

    refresh_token_data = verify_refresh_token(tokens["refresh_token"])
    assert refresh_token_data is not None
    assert refresh_token_data.user_id == user_id
    assert refresh_token_data.username == username


def test_refresh_token_storage_and_revocation():
    """Test refresh token storage and revocation functionality."""
    user_id = "456"
    username = "testuser2"

    # Create tokens
    tokens = auth_service.create_tokens(user_id, username)
    refresh_token = tokens["refresh_token"]

    # Verify the token was stored
    # We can't directly access the storage, but we can test the functionality
    result = refresh_access_token(refresh_token)
    assert result is not None

    # After refresh, the old token should no longer be valid due to rotation
    old_token_result = refresh_access_token(refresh_token)
    assert old_token_result is None

    # Test revoking all user tokens
    tokens2 = auth_service.create_tokens(user_id, username)
    refresh_token2 = tokens2["refresh_token"]

    revoked_count = revoke_all_user_refresh_tokens(user_id)
    assert revoked_count >= 1  # At least one token was revoked

    # The new token should no longer be valid after revocation
    new_token_result = refresh_access_token(refresh_token2)
    assert new_token_result is None


def test_refresh_token_rotation():
    """Test refresh token rotation security feature."""
    user_id = "789"
    username = "testuser3"

    # Create initial tokens
    tokens = auth_service.create_tokens(user_id, username)
    initial_refresh_token = tokens["refresh_token"]

    # Refresh once
    result1 = refresh_access_token(initial_refresh_token)
    assert result1 is not None
    new_refresh_token1 = result1["refresh_token"]

    # Refresh again with the new token
    result2 = refresh_access_token(new_refresh_token1)
    assert result2 is not None
    new_refresh_token2 = result2["refresh_token"]

    # All three refresh tokens should be different
    assert initial_refresh_token != new_refresh_token1
    assert new_refresh_token1 != new_refresh_token2
    assert initial_refresh_token != new_refresh_token2

    # The first two tokens should no longer be valid
    assert refresh_access_token(initial_refresh_token) is None
    assert refresh_access_token(new_refresh_token1) is None

    # But the latest should still work
    assert refresh_access_token(new_refresh_token2) is not None


if __name__ == "__main__":
    # Run tests
    test_password_hashing()
    test_password_strength_validation()
    test_username_validation()
    test_register_user()
    test_access_token_creation()
    test_refresh_token_creation()
    test_token_expiration()
    test_token_refresh()
    test_user_authentication()
    test_create_tokens()
    test_refresh_token_storage_and_revocation()
    test_refresh_token_rotation()

    print("All tests passed!")