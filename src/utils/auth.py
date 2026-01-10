from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid
import hashlib

from ..config import settings
from ..models import User, TokenBlacklist
from ..database import get_async_session


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash a plain password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


# Security scheme for JWT
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current authenticated user from JWT token.
    """
    try:
        # Decode the JWT token first to get the payload
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Check if the token is blacklisted
        if await is_token_blacklisted(credentials.credentials, session):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        user_id_str: str = payload.get("user_id")

        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        # Convert string to UUID
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format"
            )

        # Fetch user from database
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def hash_token(token: str) -> str:
    """
    Hash a JWT token for secure storage in the blacklist.
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def is_token_blacklisted(token: str, session: AsyncSession) -> bool:
    """
    Check if a token is in the blacklist.

    Args:
        token: The JWT token to check
        session: Database session for querying

    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        # Hash the token for comparison
        hashed_token = hash_token(token)

        # Query for the blacklisted token
        statement = select(TokenBlacklist).where(TokenBlacklist.token == hashed_token)
        result = await session.exec(statement)
        blacklisted_token = result.first()

        if blacklisted_token:
            # Check if the blacklisted token has expired
            if blacklisted_token.expires_at < datetime.utcnow():
                # Token has expired, remove it from blacklist (cleanup)
                await session.delete(blacklisted_token)
                await session.commit()
                return False
            return True
        return False
    except Exception:
        # If there's an error checking the blacklist, treat it as not blacklisted
        # to avoid blocking valid requests due to database issues
        return False


async def blacklist_token(token: str, session: AsyncSession, reason: str = "logout"):
    """
    Add a token to the blacklist.

    Args:
        token: The JWT token to blacklist
        session: Database session for storing
        reason: Reason for blacklisting (default: "logout")
    """
    try:
        # Decode the token to get its expiration time
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Get the expiration time from the token
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            expires_at = datetime.utcfromtimestamp(exp_timestamp)
        else:
            # If no expiration in token, set a default (e.g., 1 hour from now)
            expires_at = datetime.utcnow() + timedelta(hours=1)

        # Generate a unique ID for the token (using the jti claim if available, otherwise hash)
        jti = payload.get("jti", hash_token(token))

        # Hash the token for secure storage
        hashed_token = hash_token(token)

        # Create a new blacklisted token entry
        blacklisted_token = TokenBlacklist(
            jti=jti,
            token=hashed_token,
            expires_at=expires_at,
            blacklisted_at=datetime.utcnow(),
            reason=reason
        )

        # Add to database
        session.add(blacklisted_token)
        await session.commit()
    except jwt.ExpiredSignatureError:
        # Token is already expired, no need to blacklist
        pass
    except jwt.JWTError:
        # If token can't be decoded, we can't blacklist it properly
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format"
        )
    except Exception as e:
        # Log the error but don't expose internal details to the user
        print(f"Error blacklisting token: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to blacklist token"
        )