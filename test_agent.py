"""Test script for the todo agent service - imports only function definitions."""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, '/mnt/d/todo_phase1/backend')


def test_agent_imports():
    """Test that the agent service can be imported without database initialization."""
    print("Testing agent service imports...")

    try:
        from src.services.agent import (
            add_task_tool,
            list_tasks_tool,
            complete_task_tool,
            update_task_tool,
            delete_task_tool,
            todo_agent,
            process_message
        )
        print("✓ Successfully imported agent service components")

        # Show that the tools are properly created
        print(f"✓ Agent name: {todo_agent.name}")
        print(f"✓ Number of tools: {len(todo_agent.tools)}")

        for i, tool in enumerate(todo_agent.tools):
            print(f"  Tool {i+1}: {tool.name}")

        return True

    except Exception as e:
        print(f"✗ Failed to import agent service: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_function():
    """Test that individual functions can be imported."""
    print("\nTesting individual function imports...")

    try:
        # Import the functions separately to check they're defined properly
        from src.services.agent import add_task_tool
        print("✓ Successfully imported add_task_tool")

        # Check function tool properties
        print(f"✓ add_task_tool name: {add_task_tool.name}")
        print(f"✓ add_task_tool description: {add_task_tool.description}")
        print(f"✓ add_task_tool parameters: {list(add_task_tool.params_json_schema.get('properties', {}).keys())}")

        return True

    except Exception as e:
        print(f"✗ Failed to import individual functions: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the tests."""
    print("Testing Todo Agent Service...")

    success1 = test_agent_imports()
    success2 = await test_simple_function()

    if success1 and success2:
        print("\n✓ All tests passed! Agent service is properly configured.")
    else:
        print("\n✗ Some tests failed.")


if __name__ == "__main__":
    asyncio.run(main())