import sys
import os
import traceback

# Add the current directory to sys.path to allow relative imports
sys.path.append(os.path.abspath(os.curdir))

try:
    print("Attempting to import chat router...")
    # Using absolute import for the test script
    from src.api.chat import router
    print("Success: Chat router imported.")
    print("Routes registered in router:")
    for route in router.routes:
        print(f"  Path: {route.path}, Methods: {route.methods}")
except ImportError as e:
    print(f"ImportError: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    traceback.print_exc()
