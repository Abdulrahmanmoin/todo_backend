import asyncio
import os
import sys
import traceback
import importlib

# Windows event loop fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add path
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv()

async def test_list_tasks_core():
    import src.mcp_server.tools as tools
    print(f"Imported tools from: {tools.__file__}")
    
    # Check if we can find list_tasks_core
    if not hasattr(tools, 'list_tasks_core'):
        print("ERROR: tools.py does not have list_tasks_core!")
        return

    # Inspect source of list_tasks_core if possible
    import inspect
    print(f"Source file of list_tasks_core: {inspect.getfile(tools.list_tasks_core)}")
    
    from src.mcp_server.tools import list_tasks_core
    
    print(f"\n=== Testing list_tasks_core directly ===")
    user_id = "f74b2682-2a67-48d3-b1f8-9d6bbce83294"
    params = {"user_id": user_id, "filters": {}}
    
    print(f"Calling list_tasks_core with params: {params}")
    
    try:
        result = await list_tasks_core(params)
        print(f"list_tasks_core Success: {result['success']}")
        print(f"Tasks count: {len(result.get('tasks', []))}")
        if result.get('tasks'):
            print(f"First task: {result['tasks'][0]}")
    except Exception as e:
        print(f"list_tasks_core Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_list_tasks_core())
