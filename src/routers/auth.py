from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Annotated, Optional
import jwt
import re
from datetime import datetime, timedelta
from sqlmodel import select
import logging

from ..database import get_async_session
from ..models import User, UserCreate, UserRead, UserLogin
from ..config import settings
from ..utils.auth import verify_password, hash_password, create_access_token, get_current_user
from ..auth.better_auth_integration import BetterAuthJWTBearer


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user with validation and security best practices.

    This endpoint is compatible with Better Auth patterns and can work alongside
    Better Auth's authentication system.
    """
    try:
        # Validate input data with more robust validation
        # Email validation: basic format check
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        # Username validation: alphanumeric and underscore/hyphen only, 3-30 chars
        username_pattern = r'^[a-zA-Z0-9_-]{3,30}$'
        if not re.match(username_pattern, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be 3-30 characters long and contain only letters, numbers, underscores, and hyphens"
            )

        # Password validation: minimum complexity
        password = user_data.password
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )

        # Additional password complexity checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character"
            )

        # Check if user already exists (email)
        existing_user = await session.exec(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if username already exists
        existing_username = await session.exec(
            select(User).where(User.username == user_data.username)
        )
        if existing_username.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Hash the password securely
        hashed_password = hash_password(user_data.password)

        # Create new user
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password
        )
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)

        logger.info(f"New user registered: {db_user.email}")

        return db_user

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login")
async def login_user(
    user_credentials: UserLogin,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Authenticate user and return access token.
    Compatible with Better Auth patterns for token format and response structure.
    """
    try:
        # Find user by email
        result = await session.exec(
            select(User).where(User.email == user_credentials.email)
        )
        user = result.first()

        if not user or not verify_password(user_credentials.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token with user information
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": str(user.user_id)}, expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            "user": UserRead.model_validate(user)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


@router.post("/logout")
async def logout_user():
    """
    Logout user - in a real Better Auth integration, this would invalidate the session.
    For now, this is a placeholder that returns a success response.
    """
    # In a real Better Auth integration, this would communicate with the Better Auth
    # service to invalidate the session/cookie
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info.
    """
    return current_user