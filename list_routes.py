import sys
import os
# Ensure root is in path
sys.path.append(os.path.abspath(os.curdir))

from src.main import app

print("Registered Routes:")
for route in app.routes:
    # Most routes have methods and path
    methods = getattr(route, "methods", ["ANY"])
    path = getattr(route, "path", "UNKNOWN")
    print(f"  {methods} {path}")
