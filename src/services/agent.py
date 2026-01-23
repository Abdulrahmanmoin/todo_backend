"""Agent service using OpenAI Agent SDK to integrate with MCP tools for task management."""

import json
import os
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

try:
    from agents import Agent, Runner, OpenAIChatCompletionsModel
    from agents.tool import function_tool
    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    # Mock function_tool decorator
    def function_tool(func):
        return func
    print("Warning: 'openai-agents' module not found. Agent functionality will be disabled.")

from ..mcp_server.tools import (
    add_task, list_tasks, complete_task, update_task, delete_task
)


@function_tool
async def add_task_tool(title: str, user_id: str, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a new task to the user's todo list.

    Args:
        title: Title of the task
        user_id: ID of the user creating the task
        description: Description of the task (optional)
    """
    params = {"title": title, "description": description, "user_id": user_id}
    try:
        result = await add_task(params)
    except Exception as e:
        print(f"DEBUG: Error in add_task_tool: {e}")
        import traceback
        traceback.print_exc()
        raise

    # If the result is already a dictionary (direct core function call), return it
    if isinstance(result, dict):
        return result

    # Parse the result from the CallToolResult content (if it's an MCP result)
    if hasattr(result, 'content') and result.content:
        text_content = result.content[0]  # Get first content item
        content = json.loads(text_content.text)
        if hasattr(result, 'isError') and result.isError:
            raise Exception(content.get("error", "Failed to add task"))
        return content
    else:
        raise Exception("Failed to add task - no content in result")


@function_tool
async def list_tasks_tool(user_id: str, completed: Optional[bool] = None) -> Dict[str, Any]:
    """
    List all tasks for a specific user.

    Args:
        user_id: ID of the user whose tasks to list
        completed: Filter by completion status (optional)
    """
    filters = {}
    if completed is not None:
        filters["completed"] = completed
    params = {"user_id": user_id, "filters": filters}
    try:
        result = await list_tasks(params)
    except Exception as e:
        print(f"DEBUG: Error in list_tasks_tool: {e}")
        import traceback
        traceback.print_exc()
        raise

    # If the result is already a dictionary (direct core function call), return it
    if isinstance(result, dict):
        return result

    # Parse the result from the CallToolResult content
    if hasattr(result, 'content') and result.content:
        text_content = result.content[0]  # Get first content item
        content = json.loads(text_content.text)
        if hasattr(result, 'isError') and result.isError:
            raise Exception(content.get("error", "Failed to list tasks"))
        return content
    else:
        raise Exception("Failed to list tasks - no content in result")


@function_tool
async def complete_task_tool(task_id: int, user_id: str, completed: bool) -> Dict[str, Any]:
    """
    Mark a task as completed or not completed.

    Args:
        task_id: ID of the task to update
        user_id: ID of the user who owns the task
        completed: Whether the task is completed or not
    """
    params = {"task_id": task_id, "user_id": user_id, "completed": completed}
    try:
        result = await complete_task(params)
    except Exception as e:
        print(f"DEBUG: Error in complete_task_tool: {e}")
        import traceback
        traceback.print_exc()
        raise

    # If the result is already a dictionary (direct core function call), return it
    if isinstance(result, dict):
        return result

    # Parse the result from the CallToolResult content
    if hasattr(result, 'content') and result.content:
        text_content = result.content[0]  # Get first content item
        content = json.loads(text_content.text)
        if hasattr(result, 'isError') and result.isError:
            raise Exception(content.get("error", "Failed to complete task"))
        return content
    else:
        raise Exception("Failed to complete task - no content in result")


@function_tool
async def update_task_tool(task_id: int, user_id: str, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Update an existing task.

    Args:
        task_id: ID of the task to update
        user_id: ID of the user who owns the task
        title: New title for the task (optional)
        description: New description for the task (optional)
    """
    params = {"task_id": task_id, "user_id": user_id}
    if title is not None:
        params["title"] = title
    if description is not None:
        params["description"] = description

    try:
        result = await update_task(params)
    except Exception as e:
        print(f"DEBUG: Error in update_task_tool: {e}")
        import traceback
        traceback.print_exc()
        raise

    # If the result is already a dictionary (direct core function call), return it
    if isinstance(result, dict):
        return result

    # Parse the result from the CallToolResult content
    if hasattr(result, 'content') and result.content:
        text_content = result.content[0]  # Get first content item
        content = json.loads(text_content.text)
        if hasattr(result, 'isError') and result.isError:
            raise Exception(content.get("error", "Failed to update task"))
        return content
    else:
        raise Exception("Failed to update task - no content in result")


@function_tool
async def delete_task_tool(task_id: int, user_id: str) -> Dict[str, Any]:
    """
    Delete a task.

    Args:
        task_id: ID of the task to delete
        user_id: ID of the user who owns the task
    """
    params = {"task_id": task_id, "user_id": user_id}
    try:
        result = await delete_task(params)
    except Exception as e:
        print(f"DEBUG: Error in delete_task_tool: {e}")
        import traceback
        traceback.print_exc()
        raise

    # If the result is already a dictionary (direct core function call), return it
    if isinstance(result, dict):
        return result

    # Parse the result from the CallToolResult content
    if hasattr(result, 'content') and result.content:
        text_content = result.content[0]  # Get first content item
        content = json.loads(text_content.text)
        if hasattr(result, 'isError') and result.isError:
            raise Exception(content.get("error", "Failed to delete task"))
        return content
    else:
        raise Exception("Failed to delete task - no content in result")


def create_todo_agent(user_id: str):
    """Create a Todo management agent using the OpenAI Agent SDK tailored for a specific user."""
    if not HAS_AGENTS:
        return None
        
    # Ensure environment variables are loaded
    if not os.environ.get("GEMINI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv()
        print("Explicitly loaded dotenv in create_todo_agent")

    model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("CRITICAL ERROR: GEMINI_API_KEY not found in environment!")
    else:
        # Debug print (partial key)
        print(f"Using Gemini API Key: {api_key[:10]}... Model: {model_name}")

    # Static client for direct OpenAI-like calls
    gemini_client = AsyncOpenAI(
        api_key=api_key or "missing_key_placeholder", # Prevent immediate crash to allow logging
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    return Agent(
        name="TodoManager",
        instructions=f"""
        You are a helpful todo list manager that helps users manage their tasks.
        The current user's ID is: {user_id}. 
        IMPORTANT: You MUST always provide this user_id when calling any of the task management tools.
        
        Capabilities:
        - Add tasks: Use 'add_task_tool' with title and optional description.
        - List tasks: Use 'list_tasks_tool' to see current tasks.
        - Complete tasks: Use 'complete_task_tool' with task_id and completed=True.
        - Update tasks: Use 'update_task_tool' to change title or description.
        - Delete tasks: Use 'delete_task_tool' with task_id.
        
        Guidelines:
        - Always ask for confirmation before deleting a task.
        - When listing tasks, provide a summary of what the user has to do.
        - Be friendly and encouraging.
        """,
        tools=[
            add_task_tool,
            list_tasks_tool,
            complete_task_tool,
            update_task_tool,
            delete_task_tool
        ],
        model=OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=gemini_client
        )
    )



async def process_message(message: str, user_id: str) -> Dict[str, Any]:
    """
    Process a single user message using the todo agent.
    
    Args:
        message: The user's message in natural language
        user_id: The ID of the user making the request
        
    Returns:
        Dictionary containing the agent's response and any tool results
    """
    messages = [{"role": "user", "content": message}]
    return await run_agent_with_context(messages, user_id)


async def run_agent_with_context(messages: List[Dict[str, str]], user_id: str) -> Dict[str, Any]:
    """
    Run the agent with a conversation history and user context.
    
    Args:
        messages: List of messages in the conversation (role and content)
        user_id: The ID of the user making the request
        
    Returns:
        Dictionary with agent's response, tool calls, and success status
    """
    try:
        if not HAS_AGENTS:
            return {
                "response": "I'm sorry, the AI agent service is currently unavailable (missing 'openai-agents' package). Please contact the administrator or install the package using 'pip install openai-agents'.",
                "tool_calls": [],
                "success": False
            }
            
        agent = create_todo_agent(user_id)
        result = await Runner.run(agent, messages)
        
        return {
            "response": result.final_output if hasattr(result, 'final_output') else "I've processed your request.",
            "tool_calls": [
                {
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                } for tc in result.tool_calls
            ] if hasattr(result, 'tool_calls') and result.tool_calls else [],
            "success": True
        }
    except Exception as e:
        import traceback
        print(f"Agent execution error: {str(e)}\n{traceback.format_exc()}")
        return {
            "response": "I'm sorry, I encountered an error while processing your request.",
            "tool_calls": [],
            "success": False,
            "error": str(e)
        }