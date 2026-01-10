#!/usr/bin/env python3
"""
Test script to verify the database seeding functionality.
"""

import asyncio
import os
from pathlib import Path
import sys

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import select
from backend.src.database.connection import AsyncSessionLocal
from backend.src.models.user import User
from backend.src.models.task import Task


async def test_seeded_data():
    """
    Test that the seeded data exists in the database.
    """
    print("Testing seeded data...")

    async with AsyncSessionLocal() as session:
        # Count users
        users = await session.exec(select(User))
        user_list = users.all()
        print(f"Found {len(user_list)} users in database")

        # Count tasks
        tasks = await session.exec(select(Task))
        task_list = tasks.all()
        print(f"Found {len(task_list)} tasks in database")

        # Show user details
        for user in user_list:
            user_tasks = await session.exec(select(Task).where(Task.user_id == user.user_id))
            user_tasks_list = user_tasks.all()
            print(f"User: {user.username} ({user.email}) - {len(user_tasks_list)} tasks")

        # Show some task details
        for task in task_list[:5]:  # Show first 5 tasks
            status = "completed" if task.is_completed else "pending"
            print(f"  - {task.title} ({status}) for user {task.user.username}")

    print("Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_seeded_data())