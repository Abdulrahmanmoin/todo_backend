
import asyncio
import os
import sys
import uuid
from sqlmodel import select, text

# Windows event loop fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add path
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from src.database import get_async_session
from src.models.task import Task

async def check_db():
    print("Checking database...")
    async with get_async_session() as session:
        try:
            # Check if tasks table exists and has columns
            result = await session.exec(text("SELECT count(*) FROM tasks"))
            count = result.scalar()
            print(f"Task count: {count}")
            
            # Check a few tasks
            result = await session.exec(select(Task).limit(5))
            tasks = result.all()
            for t in tasks:
                print(f"Task: {t.task_id}, Title: {t.title}, User: {t.user_id}, Completed: {t.is_completed}")
                
            # Check specific user
            test_user_id = "f74b2682-2a67-48d3-b1f8-9d6bbce83294"
            test_uuid = uuid.UUID(test_user_id)
            result = await session.exec(select(Task).where(Task.user_id == test_uuid))
            user_tasks = result.all()
            print(f"Tasks for user {test_user_id}: {len(user_tasks)}")
            
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_db())
