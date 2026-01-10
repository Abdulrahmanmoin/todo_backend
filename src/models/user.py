from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
import uuid


class UserBase(SQLModel):
    """Base model for User with common fields"""
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)


class User(UserBase, table=True):
    """User model for the application"""
    __tablename__ = "users"

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    is_active: bool = Field(default=True)

    # Relationship to tasks
    tasks: list["Task"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """Model for creating a new user"""
    password: str  # Plain text password for creation/validation


class UserRead(UserBase):
    """Model for reading user data (without sensitive information)"""
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool


class UserUpdate(SQLModel):
    """Model for updating user data"""
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None


class UserLogin(SQLModel):
    """Model for user login"""
    email: str
    password: str