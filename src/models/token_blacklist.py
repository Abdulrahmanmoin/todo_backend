from sqlmodel import SQLModel, Field, create_engine, Session
from datetime import datetime
import uuid


class TokenBlacklistBase(SQLModel):
    """Base model for blacklisted tokens"""
    jti: str = Field(unique=True, index=True, nullable=False)  # JWT ID
    token: str = Field(nullable=False)  # The actual token (hashed for security)
    expires_at: datetime = Field(nullable=False)  # When the original token would expire
    blacklisted_at: datetime = Field(default_factory=datetime.utcnow)  # When it was blacklisted
    reason: str = Field(default="logout")  # Reason for blacklisting


class TokenBlacklist(TokenBlacklistBase, table=True):
    """Model for storing blacklisted JWT tokens"""
    __tablename__ = "token_blacklist"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    jti: str = Field(unique=True, index=True, nullable=False)  # JWT ID
    token: str = Field(nullable=False)  # The actual token (hashed for security)
    expires_at: datetime = Field(nullable=False)  # When the original token would expire
    blacklisted_at: datetime = Field(default_factory=datetime.utcnow)  # When it was blacklisted
    reason: str = Field(default="logout")  # Reason for blacklisting


class TokenBlacklistCreate(TokenBlacklistBase):
    """Model for creating a blacklisted token entry"""
    pass


class TokenBlacklistRead(TokenBlacklistBase):
    """Model for reading blacklisted token data"""
    id: uuid.UUID
    blacklisted_at: datetime