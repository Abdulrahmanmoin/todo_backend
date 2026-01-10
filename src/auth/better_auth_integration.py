"""
Better Auth Integration for FastAPI Backend
This module provides utilities to work with Better Auth in a FastAPI application.
"""
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import jwt
from ..config import settings
from ..models.user import User
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import logging

logger = logging.getLogger(__name__)

class BetterAuthJWTBearer(HTTPBearer):
    """
    Custom security scheme to handle Better Auth JWT tokens
    """
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[Dict[str, Any]]:
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
            token = credentials.credentials
            # For now, we're not implementing full JWT validation as Better Auth is TypeScript-based
            # In a real implementation, this would validate tokens issued by Better Auth
            return {"token": token}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )


# Better Auth compatible user dependency
async def get_current_user_from_token(
    session: AsyncSession = None
) -> Optional[User]:
    """
    Get current user from Better Auth compatible token
    This is a placeholder implementation for Better Auth integration.
    In a real implementation, this would validate the token against Better Auth service.
    """
    # This is a placeholder - in a real Better Auth integration,
    # we would validate the token against Better Auth's authentication service
    return None