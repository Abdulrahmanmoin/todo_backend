import asyncio
import logging
from typing import Any, Dict, List, Optional
try:
    from mcp.server import Server
    from mcp.types import Tool, CallToolResult, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    # Mock classes for type hints and initialization
    class Server:
        def __init__(self, *args, **kwargs): pass
    class Tool:
        def __init__(self, *args, **kwargs): pass
    class CallToolResult:
        def __init__(self, *args, **kwargs): pass
    class TextContent:
        def __init__(self, *args, **kwargs): pass
    print("Warning: 'mcp' module not found. MCP tool server functionality will be limited.")
import json
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import and_
from ..models.task import Task
from ..database.connection import get_async_session
from ..config import settings
from contextlib import asynccontextmanager
import time
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting implementation
class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        """Check if a user is allowed to make a request."""
        current_time = time.time()
        # Clean old requests outside the window
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if current_time - req_time < self.window_seconds
        ]

        # Check if user has exceeded the limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False

        # Add current request
        self.requests[user_id].append(current_time)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)  # Allow 20 requests per minute per user


# Initialize MCP server
server = Server("todo-mcp-server")


@asynccontextmanager
async def get_db_session():
    """Get database session for use in tools."""
    try:
        # get_async_session is a plain async generator
        session_gen = get_async_session()
        session = await anext(session_gen)
        try:
            yield session
        finally:
            await session_gen.aclose()
    except Exception as e:
        logger.error(f"Error in get_db_session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def validate_user_access(session: AsyncSession, user_id: str, task_id: Optional[int] = None) -> bool:
    """Validate that the user has access to the task or resource."""
    # In a real implementation, you would verify user permissions
    # For now, we just check that the user_id is valid
    return user_id is not None and len(user_id) > 0


# Define core functions that can be used by both agent and MCP tools
async def add_task_core(params: Dict[str, Any]) -> Dict[str, Any]:
    """Core function to add a task."""
    title = params["title"]
    description = params.get("description")
    user_id = params["user_id"]

    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise ValueError("Rate limit exceeded. Please slow down your requests.")

    logger.info(f"Adding task for user {user_id}: {title}")

    async with get_db_session() as session:
        if not await validate_user_access(session, user_id):
            logger.warning(f"Invalid user access for user {user_id}")
            raise ValueError("Invalid user access")

        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)

        # Create the task
        task = Task(
            title=title,
            description=description,
            user_id=user_id
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info(f"Successfully added task {task.task_id} for user {user_id}")

        return {
            "success": True,
            "task_id": str(task.task_id),
            "task": {
                "id": str(task.task_id),
                "title": task.title,
                "description": task.description,
                "completed": task.is_completed,
                "user_id": str(task.user_id),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        }


async def list_tasks_core(params: Dict[str, Any]) -> Dict[str, Any]:
    """Core function to list tasks."""
    user_id = params["user_id"]
    filters = params.get("filters", {})

    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise ValueError("Rate limit exceeded. Please slow down your requests.")

    logger.info(f"Listing tasks for user {user_id} with filters: {filters}")

    async with get_db_session() as session:
        if not await validate_user_access(session, user_id):
            logger.warning(f"Invalid user access for user {user_id}")
            raise ValueError("Invalid user access")

        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)

        # Build query with filters
        query = select(Task).where(Task.user_id == user_id)

        if "completed" in filters:
            query = query.where(Task.is_completed == filters["completed"])
            logger.debug(f"Applying completed filter: {filters['completed']}")

        result = await session.exec(query)
        tasks = result.all()

        logger.info(f"Found {len(tasks)} tasks for user {user_id}")

        tasks_list = []
        for task in tasks:
            tasks_list.append({
                "id": str(task.task_id),
                "title": task.title,
                "description": task.description,
                "completed": task.is_completed,
                "user_id": str(task.user_id),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            })

        return {
            "success": True,
            "tasks": tasks_list
        }


async def complete_task_core(params: Dict[str, Any]) -> Dict[str, Any]:
    """Core function to complete a task."""
    task_id = params["task_id"]
    user_id = params["user_id"]
    completed = params["completed"]

    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise ValueError("Rate limit exceeded. Please slow down your requests.")

    logger.info(f"Updating task {task_id} completion status to {completed} for user {user_id}")

    async with get_db_session() as session:
        if not await validate_user_access(session, user_id):
            logger.warning(f"Invalid user access for user {user_id}")
            raise ValueError("Invalid user access")

        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)
            
        if isinstance(task_id, str):
            import uuid
            task_id = uuid.UUID(task_id)

        # Get the task
        result = await session.exec(select(Task).where((Task.task_id == task_id) & (Task.user_id == user_id)))
        task = result.first()

        if not task:
            logger.warning(f"Task {task_id} not found or access denied for user {user_id}")
            raise ValueError("Task not found or access denied")

        # Update the task
        task.is_completed = completed
        if completed:
            from datetime import datetime
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None
            
        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info(f"Successfully updated task {task.task_id} completion status for user {user_id}")

        return {
            "success": True,
            "task": {
                "id": str(task.task_id),
                "title": task.title,
                "description": task.description,
                "completed": task.is_completed,
                "user_id": str(task.user_id),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        }


async def update_task_core(params: Dict[str, Any]) -> Dict[str, Any]:
    """Core function to update a task."""
    task_id = params["task_id"]
    user_id = params["user_id"]
    title = params.get("title")
    description = params.get("description")

    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise ValueError("Rate limit exceeded. Please slow down your requests.")

    logger.info(f"Updating task {task_id} for user {user_id} with title: {title}, description: {description}")

    async with get_db_session() as session:
        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)
            
        if isinstance(task_id, str):
            import uuid
            task_id = uuid.UUID(task_id)

        # Get the task
        result = await session.exec(select(Task).where((Task.task_id == task_id) & (Task.user_id == user_id)))
        task = result.first()

        if not task:
            logger.warning(f"Task {task_id} not found or access denied for user {user_id}")
            raise ValueError("Task not found or access denied")

        # Update the task fields if provided
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description

        session.add(task)
        await session.commit()
        await session.refresh(task)

        logger.info(f"Successfully updated task {task.task_id} for user {user_id}")

        return {
            "success": True,
            "task": {
                "id": str(task.task_id),
                "title": task.title,
                "description": task.description,
                "completed": task.is_completed,
                "user_id": str(task.user_id),
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
        }


async def delete_task_core(params: Dict[str, Any]) -> Dict[str, Any]:
    """Core function to delete a task."""
    task_id = params["task_id"]
    user_id = params["user_id"]

    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        logger.warning(f"Rate limit exceeded for user {user_id}")
        raise ValueError("Rate limit exceeded. Please slow down your requests.")

    logger.info(f"Deleting task {task_id} for user {user_id}")

    async with get_db_session() as session:
        if not await validate_user_access(session, user_id):
            logger.warning(f"Invalid user access for user {user_id}")
            raise ValueError("Invalid user access")

        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)
            
        if isinstance(task_id, str):
            import uuid
            task_id = uuid.UUID(task_id)

        # Get the task
        result = await session.exec(select(Task).where((Task.task_id == task_id) & (Task.user_id == user_id)))
        task = result.first()

        if not task:
            logger.warning(f"Task {task_id} not found or access denied for user {user_id}")
            raise ValueError("Task not found or access denied")

        # Delete the task
        await session.delete(task)
        await session.commit()

        logger.info(f"Successfully deleted task {task_id} for user {user_id}")

        return {
            "success": True,
            "message": "Task deleted successfully"
        }


# MCP Server Handlers
async def add_task_handler(context, params: Dict[str, Any]) -> CallToolResult:
    """MCP handler for adding a task."""
    try:
        result = await add_task_core(params)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": str(e)}))],
            isError=True
        )


async def list_tasks_handler(context, params: Dict[str, Any]) -> CallToolResult:
    """MCP handler for listing tasks."""
    try:
        result = await list_tasks_core(params)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": str(e)}))],
            isError=True
        )


async def complete_task_handler(context, params: Dict[str, Any]) -> CallToolResult:
    """MCP handler for completing a task."""
    try:
        result = await complete_task_core(params)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": str(e)}))],
            isError=True
        )


async def update_task_handler(context, params: Dict[str, Any]) -> CallToolResult:
    """MCP handler for updating a task."""
    try:
        result = await update_task_core(params)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": str(e)}))],
            isError=True
        )


async def delete_task_handler(context, params: Dict[str, Any]) -> CallToolResult:
    """MCP handler for deleting a task."""
    try:
        result = await delete_task_core(params)
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": str(e)}))],
            isError=True
        )


# Register tools with the MCP server using the available method
# Since we don't know the exact registration mechanism, we'll use a placeholder approach
# and focus on having the core functions available for the agent

# Export the core functions for use in the agent service
add_task = add_task_core
list_tasks = list_tasks_core
complete_task = complete_task_core
update_task = update_task_core
delete_task = delete_task_core


# Define the tools list separately for MCP server
async def list_all_tools(context) -> List[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="add_task",
            description="Add a new task to the user's todo list",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "description": {"type": "string", "description": "Description of the task (optional)"},
                    "user_id": {"type": "string", "description": "ID of the user creating the task"}
                },
                "required": ["title", "user_id"]
            }
        ),
        Tool(
            name="list_tasks",
            description="List all tasks for a specific user",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "ID of the user whose tasks to list"},
                    "filters": {
                        "type": "object",
                        "properties": {
                            "completed": {"type": "boolean", "description": "Filter by completion status (optional)"}
                        }
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="complete_task",
            description="Mark a task as completed or not completed",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to update"},
                    "user_id": {"type": "string", "description": "ID of the user who owns the task"},
                    "completed": {"type": "boolean", "description": "Whether the task is completed or not"}
                },
                "required": ["task_id", "user_id", "completed"]
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to update"},
                    "user_id": {"type": "string", "description": "ID of the user who owns the task"},
                    "title": {"type": "string", "description": "New title for the task (optional)"},
                    "description": {"type": "string", "description": "New description for the task (optional)"}
                },
                "required": ["task_id", "user_id"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a task",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to delete"},
                    "user_id": {"type": "string", "description": "ID of the user who owns the task"}
                },
                "required": ["task_id", "user_id"]
            }
        )
    ]


# Register the tools list function with the server if it supports it
# The actual registration depends on the specific MCP implementation


# Also register the handlers for tool calls if the server supports it
# Note: The actual registration mechanism depends on the specific MCP implementation