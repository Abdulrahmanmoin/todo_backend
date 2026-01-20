import sys
import os
# Ensure the current directory is in the path
sys.path.append(os.getcwd())
# Also add src to path if needed, though usually '.' is enough for packages
try:
    from src.api.chat import router
    print("IMPORT_SUCCESSFUL")
except Exception as e:
    import traceback
    print("IMPORT_FAILED")
    print(traceback.format_exc())
