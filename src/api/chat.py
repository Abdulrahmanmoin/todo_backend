from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid
from datetime import datetime
import json
import logging

from ..models.conversation import Conversation, ConversationCreate
from ..models.message import Message, MessageCreate
from ..models.task import Task
from ..database import get_async_session
from ..services.agent import process_message as agent_process_message, run_agent_with_context
from ..config import settings
from ..services.auth import verify_token

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class ChatRequest:
    def __init__(self, message: str, conversation_id: Optional[int] = None):
        self.message = message
        self.conversation_id = conversation_id


class ChatResponse:
    def __init__(self, conversation_id: int, response: str, tool_calls: Optional[List[Dict]] = None):
        self.conversation_id = conversation_id
        self.response = response
        self.tool_calls = tool_calls or []


@router.post("/{user_id}/chat", response_model=Dict[str, Any])
async def chat_endpoint(
    user_id: uuid.UUID,
    request: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Chat endpoint for managing todo tasks through natural language conversation with the AI assistant.

    Args:
        user_id: String - Unique identifier of the authenticated user
        request: Contains 'message' (required) and 'conversation_id' (optional)
        credentials: Bearer token for authentication
        session: Database session

    Returns:
        ChatResponse with conversation_id, response, and tool_calls
    """
    try:
        # Verify the token and ensure the user is authenticated
        token_payload = verify_token(credentials.credentials)

        # Verify that the user_id in the token matches the one in the path
        if str(token_payload.get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: User ID mismatch"
            )

        # Validate request body
        message = request.get("message")
        if not message or not isinstance(message, str) or len(message.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required and must be a non-empty string"
            )

        conversation_id = request.get("conversation_id")
        if conversation_id is not None and not isinstance(conversation_id, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation ID must be an integer if provided"
            )

        # If no conversation_id provided, create a new conversation
        if conversation_id is None:
            conversation = Conversation(user_id=user_id)
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            conversation_id = conversation.id
        else:
            # Verify that the conversation belongs to the user
            conversation_query = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            conversation_result = await session.exec(conversation_query)
            conversation = conversation_result.first()

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or access denied"
                )

        # Update the conversation's last activity timestamp
        conversation.last_activity = datetime.utcnow()
        session.add(conversation)
        await session.commit()

        # Create and save the user message
        user_message = Message(
            conversation_id=conversation_id,
            sender_type="user",
            content=message
        )
        session.add(user_message)
        await session.commit()
        await session.refresh(user_message)

        # Fetch conversation history to provide context to the agent
        history_query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc())
        history_result = await session.exec(history_query)
        history_messages = history_result.all()
        
        # Convert history messages to the format expected by the agent (OpenAI-style role/content)
        formatted_history = [
            {"role": "user" if msg.sender_type == "user" else "assistant" if msg.sender_type == "assistant" else "system", 
             "content": msg.content}
            for msg in history_messages
        ]

        # Process the message with the agent using full context
        try:
            agent_result = await run_agent_with_context(formatted_history, user_id)
            response_text = agent_result.get("response", "I processed your request.")
            tool_calls = agent_result.get("tool_calls", [])

            # Record tool calls in the database if any
            if tool_calls:
                for tool_call in tool_calls:
                    tool_call_message = Message(
                        conversation_id=conversation_id,
                        sender_type="tool",
                        content=f"Tool '{tool_call.get('name', 'unknown')}' called with arguments: {tool_call.get('arguments', {})}"
                    )
                    session.add(tool_call_message)

                await session.commit()
        except Exception as e:
            # Log the error for debugging
            import traceback
            logger.error(f"Error processing message with agent for user {user_id}: {str(e)}\n{traceback.format_exc()}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing your request. Please try again."
            )

        # Create and save the assistant message
        assistant_message = Message(
            conversation_id=conversation_id,
            sender_type="assistant",
            content=response_text
        )
        session.add(assistant_message)
        await session.commit()
        await session.refresh(assistant_message)

        # Return the response
        return {
            "conversation_id": conversation_id,
            "response": response_text,
            "tool_calls": tool_calls
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        import traceback
        logger.error(f"Unexpected error in chat endpoint for user {user_id}: {str(e)}\n{traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/{user_id}/conversations", response_model=List[Dict[str, Any]])
async def get_user_conversations(
    user_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all conversations for a user.

    Args:
        user_id: String - Unique identifier of the authenticated user
        credentials: Bearer token for authentication
        session: Database session

    Returns:
        List of conversations with their details
    """
    # Verify the token and ensure the user is authenticated
    token_payload = verify_token(credentials.credentials)

    # Verify that the user_id in the token matches the one in the path
    if str(token_payload.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User ID mismatch"
        )

    # Get all conversations for the user
    conversation_query = select(Conversation).where(Conversation.user_id == user_id)
    conversation_result = await session.exec(conversation_query)
    conversations = conversation_result.all()

    return [
        {
            "id": conv.id,
            "user_id": conv.user_id,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at
        }
        for conv in conversations
    ]


@router.get("/{user_id}/conversations/{conversation_id}/messages", response_model=List[Dict[str, Any]])
async def get_conversation_messages(
    user_id: uuid.UUID,
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get messages in a specific conversation with pagination support.

    Args:
        user_id: String - Unique identifier of the authenticated user
        conversation_id: Integer - ID of the conversation
        skip: Integer - Number of messages to skip (for pagination)
        limit: Integer - Maximum number of messages to return (for pagination)
        credentials: Bearer token for authentication
        session: Database session

    Returns:
        List of messages in the conversation ordered by timestamp
    """
    # Verify the token and ensure the user is authenticated
    token_payload = verify_token(credentials.credentials)

    # Verify that the user_id in the token matches the one in the path
    if str(token_payload.get("user_id")) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: User ID mismatch"
        )

    # Verify that the conversation belongs to the user
    conversation_query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id
    )
    conversation_result = await session.exec(conversation_query)
    conversation = conversation_result.first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )

    # Get messages in the conversation with pagination and proper ordering
    message_query = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(Message.timestamp.asc()).offset(skip).limit(limit)

    message_result = await session.exec(message_query)
    messages = message_result.all()

    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_type": msg.sender_type,
            "content": msg.content,
            "timestamp": msg.timestamp
        }
        for msg in messages
    ]