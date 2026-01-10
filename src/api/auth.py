"""Authentication API endpoints for user login and management.

This module implements the user login and logout endpoints with JWT token generation
and follows security best practices for authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import timedelta
import logging
import re

from ..database import get_async_session
from ..models import User, UserLogin
from ..config import settings
from ..utils.auth import verify_password, create_access_token, blacklist_token, security


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/user/login")
async def login_user(
    user_credentials: UserLogin,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return JWT access token.

    This endpoint handles user login requests with email and password,
    validates credentials against stored data, and generates JWT tokens
    upon successful authentication.

    Args:
        user_credentials: UserLogin object containing email and password
        session: Database session for user lookup

    Returns:
        dict: Response containing access token, token type, expiration, and user data

    Raises:
        HTTPException: 401 if credentials are invalid, 500 for internal errors
    """
    try:
        # Find user by email
        statement = select(User).where(User.email == user_credentials.email)
        result = await session.exec(statement)
        user = result.first()

        # Validate credentials
        if not user or not verify_password(user_credentials.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate that the user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token with user information
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": str(user.user_id)}, expires_delta=access_token_expires
        )

        logger.info(f"User successfully logged in: {user.email}")

        # Return response with token and user information
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "is_active": user.is_active
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/user/logout")
async def logout_user(
    token_credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Logout user and invalidate JWT token.

    This endpoint blacklists the user's current JWT token, preventing it from being used
    for future authentication requests. The token will be stored in a blacklist table
    and checked on subsequent requests.

    Args:
        token_credentials: JWT token from authorization header
        session: Database session for storing blacklisted token

    Returns:
        dict: Success message confirming logout
    """
    try:
        # Blacklist the token
        await blacklist_token(token_credentials.credentials, session, reason="logout")

        logger.info("User successfully logged out and token blacklisted")

        return {
            "message": "Successfully logged out",
            "detail": "Token has been invalidated and cannot be used for future requests"
        }

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )


