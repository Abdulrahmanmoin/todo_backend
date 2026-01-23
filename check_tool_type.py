
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from src.mcp_server.tools import add_task, list_tasks

async def test_tool_return_type():
    print(f"add_task is: {add_task}")
    print(f"Type of add_task: {type(add_task)}")
    
    # Mock params
    params = {"user_id": "test_user", "title": "Test Task"}
    try:
        # We need a running loop or async call, but since we just want to check the return TYPE of the function,
        # we can't easily inspect the return type of an async function without running it or inspecting signature.
        # But we know from reading the code that add_task = add_task_core.
        
        # Let's try to run it (it might fail due to DB, but the exception trace will show us where we are)
        # However, it needs a DB session.
        pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool_return_type())
