import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.curdir))

from src.database.connection import init_db
from src.models import * # Ensure all models are imported

async def main():
    print("Starting manual database initialization...")
    try:
        await init_db()
        print("Database initialized successfully from script.")
    except Exception as e:
        print(f"Error during manual database initialization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
