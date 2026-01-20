from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class MessageBase(SQLModel):
    conversation_id: int
    sender_type: str  # "user", "assistant", or "tool"
    content: str


class Message(MessageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Add indexes for better query performance
    __table_args__ = (
        {'extend_existing': True}
    )


class MessageRead(MessageBase):
    id: int
    timestamp: datetime


class MessageCreate(SQLModel):
    conversation_id: int
    sender_type: str  # "user", "assistant", or "tool"
    content: str