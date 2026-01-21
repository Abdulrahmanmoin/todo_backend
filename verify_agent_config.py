import os
import sys
from dotenv import load_dotenv

# Add cwd to path to ensure src is importable
sys.path.append(os.getcwd())

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = "fake_key_for_test"
    print("Set fake GEMINI_API_KEY for testing")

try:
    from src.services.agent import create_todo_agent, HAS_AGENTS
    print(f"HAS_AGENTS: {HAS_AGENTS}")
    
    agent = create_todo_agent("test_user_id")
    if agent:
        print(f"Successfully created agent: {agent.name}")
        print(f"Model type: {type(agent.model)}")
        if hasattr(agent.model, '_client'):
             print(f"Client base_url: {agent.model._client.base_url}")
    else:
        print("Failed to create agent")

except ImportError as e:
    print(f"ImportError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
