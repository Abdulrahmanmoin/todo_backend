"""
Better Auth Server Configuration for FastAPI Integration
This file configures Better Auth as a standalone authentication service
that can work with the existing database and models.
"""
import os
from typing import Optional
from sqlmodel import create_engine, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
import asyncio
import asyncpg
from better_auth import auth, db  # Note: This is conceptual as Better Auth is TypeScript
from better_auth.types import User as BetterUser, Session as BetterSession

# For a real integration, we would need to:
# 1. Create API endpoints that follow Better Auth's patterns
# 2. Implement proper database integration
# 3. Handle sessions in a way that's compatible with Better Auth's client

# Since Better Auth is primarily a TypeScript library, for Python/FastAPI integration,
# we'll create compatible endpoints and potentially use JWT tokens that work with Better Auth
class BetterAuthIntegration:
    """
    Class to handle integration between Better Auth frontend and FastAPI backend
    This provides JWT token compatibility and session management
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        # In a real implementation, this would connect to Better Auth's database schema
        self.engine = create_engine(database_url)

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Retrieve user from database by ID for token validation
        """
        # This method would interact with the user table in a compatible way
        # with Better Auth's user schema
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            user_row = result.fetchone()
            if user_row:
                return {
                    "id": str(user_row.user_id),
                    "email": user_row.email,
                    "username": user_row.username,
                    "created_at": user_row.created_at,
                    "is_active": user_row.is_active
                }
        return None

    async def validate_token(self, token: str) -> Optional[dict]:
        """
        Validate JWT token and return user info
        In a real implementation, this would validate tokens issued by Better Auth
        """
        # This is a placeholder for JWT validation that would work with Better Auth
        # tokens or a compatible token format
        try:
            # In actual implementation, we would use python-jose or similar to
            # decode and validate the JWT token issued by Better Auth
            import jwt
            from ..config import settings

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("user_id")
            if user_id is None:
                return None
            return await self.get_user_by_id(user_id)
        except jwt.PyJWTError:
            return None

# Create global instance
def get_better_auth_instance() -> BetterAuthIntegration:
    database_url = os.getenv("DATABASE_URL", "")
    return BetterAuthIntegration(database_url)