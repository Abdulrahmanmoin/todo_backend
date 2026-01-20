from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid


class ConversationBase(SQLModel):
    user_id: uuid.UUID  # Using UUID to match User model


class Conversation(ConversationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_activity: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Add indexes for better query performance
    __table_args__ = (
        {'extend_existing': True}
    )


class ConversationRead(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_activity: datetime


class ConversationCreate(SQLModel):
    user_id: str


class ConversationUpdate(SQLModel):
    updated_at: Optional[datetime] = None