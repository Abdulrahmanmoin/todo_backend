from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional
import uuid


class TaskBase(SQLModel):
    """Base model for Task with common fields"""
    title: str = Field(max_length=200, nullable=False)
    description: Optional[str] = Field(default=None)
    is_completed: bool = Field(default=False)


class Task(TaskBase, table=True):
    """Task model for the application"""
    __tablename__ = "tasks"

    task_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id", nullable=False)
    title: str = Field(max_length=200, nullable=False)
    description: Optional[str] = Field(default=None)
    is_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    completed_at: Optional[datetime] = Field(default=None, nullable=True)

    # Relationship to User
    user: "User" = Relationship(back_populates="tasks")


class TaskCreate(TaskBase):
    """Model for creating a new task"""
    pass


class TaskRead(TaskBase):
    """Model for reading task data"""
    task_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskUpdate(SQLModel):
    """Model for updating task data"""
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    completed_at: Optional[datetime] = None


class TaskUpdateStatus(SQLModel):
    """Model for updating task completion status"""
    is_completed: bool