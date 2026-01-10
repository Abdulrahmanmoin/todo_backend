#!/usr/bin/env python3
"""
Database seeding script for the Todo application.
This script populates the database with initial sample data for testing and development.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel, select
from sqlalchemy.exc import IntegrityError
from backend.src.database.connection import AsyncSessionLocal, get_all_models
from backend.src.models.user import User, UserCreate
from backend.src.models.task import Task, TaskCreate
from backend.src.services.auth import hash_password


async def create_sample_users(session):
    """
    Create sample users for testing.
    """
    print("Creating sample users...")

    # Sample users data
    sample_users = [
        {
            "email": "admin@example.com",
            "username": "admin",
            "password": "AdminPass123!"
        },
        {
            "email": "testuser1@example.com",
            "username": "testuser1",
            "password": "TestPass123!"
        },
        {
            "email": "testuser2@example.com",
            "username": "testuser2",
            "password": "TestPass456@"
        },
        {
            "email": "demo@example.com",
            "username": "demo",
            "password": "DemoPass789#"
        }
    ]

    created_users = []

    for user_data in sample_users:
        # Check if user already exists
        existing_user = await session.exec(
            select(User).where(User.email == user_data["email"])
        )
        user = existing_user.first()

        if not user:
            # Hash the password
            hashed_password = hash_password(user_data["password"])

            # Create new user
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=hashed_password
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created user: {user.username} ({user.email})")
        else:
            print(f"User already exists: {user.username} ({user.email})")

        created_users.append(user)

    return created_users


async def create_sample_tasks(session, users: List[User]):
    """
    Create sample tasks for testing.
    """
    print("Creating sample tasks...")

    # Sample tasks data - each user gets some tasks
    sample_tasks = [
        {
            "user_id": users[0].user_id,
            "title": "Setup development environment",
            "description": "Install and configure all necessary development tools and libraries",
            "is_completed": True,
            "completed_at": datetime.utcnow() - timedelta(days=5)
        },
        {
            "user_id": users[0].user_id,
            "title": "Implement authentication system",
            "description": "Create user registration, login, and JWT token handling",
            "is_completed": True,
            "completed_at": datetime.utcnow() - timedelta(days=3)
        },
        {
            "user_id": users[0].user_id,
            "title": "Design database schema",
            "description": "Create SQLModel schemas for users and tasks",
            "is_completed": False
        },
        {
            "user_id": users[1].user_id,
            "title": "Create API endpoints",
            "description": "Build FastAPI endpoints for user and task management",
            "is_completed": False
        },
        {
            "user_id": users[1].user_id,
            "title": "Add unit tests",
            "description": "Write comprehensive unit tests for all API endpoints",
            "is_completed": True,
            "completed_at": datetime.utcnow() - timedelta(days=1)
        },
        {
            "user_id": users[1].user_id,
            "title": "Deploy to production",
            "description": "Deploy the application to the production environment",
            "is_completed": False
        },
        {
            "user_id": users[2].user_id,
            "title": "Write documentation",
            "description": "Create API documentation and user guides",
            "is_completed": False
        },
        {
            "user_id": users[2].user_id,
            "title": "Setup CI/CD pipeline",
            "description": "Configure continuous integration and deployment",
            "is_completed": True,
            "completed_at": datetime.utcnow() - timedelta(hours=12)
        },
        {
            "user_id": users[3].user_id,
            "title": "Review code quality",
            "description": "Run code analysis tools and fix any issues",
            "is_completed": False
        },
        {
            "user_id": users[3].user_id,
            "title": "Performance testing",
            "description": "Run load tests and optimize performance bottlenecks",
            "is_completed": False
        }
    ]

    for task_data in sample_tasks:
        # Check if a similar task already exists
        existing_task = await session.exec(
            select(Task).where(
                Task.user_id == task_data["user_id"],
                Task.title == task_data["title"]
            )
        )
        existing = existing_task.first()

        if not existing:
            task = Task(
                user_id=task_data["user_id"],
                title=task_data["title"],
                description=task_data.get("description"),
                is_completed=task_data.get("is_completed", False),
                completed_at=task_data.get("completed_at")
            )

            session.add(task)
            await session.commit()
            await session.refresh(task)
            status = "completed" if task.is_completed else "pending"
            print(f"Created task: '{task.title}' for user {task.user.username} ({status})")
        else:
            print(f"Task already exists: '{existing.title}' for user {existing.user.username}")


async def seed_database():
    """
    Main function to seed the database with sample data.
    """
    print("Starting database seeding process...")

    async with AsyncSessionLocal() as session:
        # Create sample users
        users = await create_sample_users(session)

        # Create sample tasks
        await create_sample_tasks(session, users)

        print("Database seeding completed successfully!")


async def clear_database():
    """
    Clear all data from the database.
    WARNING: This will delete all data in the database!
    """
    print("Clearing database (this will delete all data)...")

    async with AsyncSessionLocal() as session:
        # Delete tasks first (due to foreign key constraint)
        await session.exec("DELETE FROM tasks")

        # Then delete users
        await session.exec("DELETE FROM users")

        await session.commit()
        print("Database cleared successfully!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database seeding script for Todo application")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the database with sample data"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all data from the database (WARNING: destructive operation)"
    )
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Clear the database and re-seed with sample data"
    )

    args = parser.parse_args()

    if args.clear:
        print("WARNING: You are about to clear all data from the database!")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            asyncio.run(clear_database())
        else:
            print("Operation cancelled.")
    elif args.seed:
        asyncio.run(seed_database())
    elif args.reseed:
        print("WARNING: You are about to clear all data and re-seed the database!")
        confirmation = input("Are you sure you want to continue? (yes/no): ")
        if confirmation.lower() == "yes":
            asyncio.run(clear_database())
            asyncio.run(seed_database())
        else:
            print("Operation cancelled.")
    else:
        print("Please specify an action: --seed, --clear, or --reseed")
        parser.print_help()