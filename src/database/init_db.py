#!/usr/bin/env python3
"""
Database initialization script for creating tables and running migrations.
This script provides functionality to initialize the database, run migrations,
and handle various database setup tasks for the Todo application.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add Windows-specific event loop fix for psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlmodel import SQLModel
from sqlalchemy import create_engine, text
from backend.src.database.connection import (
    sync_engine,
    async_engine,
    get_database_config,
    is_development
)


async def create_tables():
    """
    Create all tables in the database using SQLModel metadata.
    This is an alternative to using Alembic migrations for initial setup.
    """
    print("Creating tables using SQLModel...")
    try:
        # Create tables using the async engine
        async with async_engine.begin() as conn:
            # Drop existing tables in development mode (use with caution!)
            if is_development():
                print("Dropping existing tables (development mode)...")
                await conn.run_sync(SQLModel.metadata.drop_all)

            print("Creating new tables...")
            await conn.run_sync(SQLModel.metadata.create_all)

        print("Tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False


def run_alembic_migrations():
    """
    Run alembic migrations to update the database schema.
    This function runs migrations using the alembic command programmatically.
    """
    try:
        # Import alembic here to avoid issues if not installed
        from alembic.config import Config
        from alembic import command
        from backend.src.database.connection import DATABASE_URL

        # Create alembic config
        alembic_cfg = Config("backend/alembic.ini")

        # Override the sqlalchemy.url with our database URL
        config_values = get_database_config()
        alembic_cfg.set_main_option("sqlalchemy.url", config_values["sqlalchemy.url"])

        print("Running alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
        return True
    except ImportError:
        print("Alembic not installed, skipping migration step.")
        print("You can install it with: pip install alembic")
        return False
    except Exception as e:
        print(f"Error running migrations: {e}")
        return False


async def check_database_connection():
    """
    Test the database connection to ensure it's working properly.
    """
    try:
        print("Testing database connection...")
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def initialize_database(use_migrations: bool = True):
    """
    Main function to initialize the database.

    Args:
        use_migrations: If True, use alembic migrations; if False, use direct table creation
    """
    print("Starting database initialization...")

    # Check if database connection works
    if not await check_database_connection():
        print("Cannot proceed without database connection.")
        return False

    if use_migrations:
        # Use alembic migrations
        success = run_alembic_migrations()
    else:
        # Use direct table creation
        success = await create_tables()

    if success:
        print("Database initialization completed successfully!")
        return True
    else:
        print("Database initialization failed!")
        return False


async def create_initial_migration():
    """
    Create an initial migration based on the current models.
    This is useful when setting up migrations for the first time.
    """
    try:
        from alembic.config import Config
        from alembic import command
        from backend.src.database.connection import DATABASE_URL

        # Create alembic config
        alembic_cfg = Config("backend/alembic.ini")

        # Override the sqlalchemy.url with our database URL
        config_values = get_database_config()
        alembic_cfg.set_main_option("sqlalchemy.url", config_values["sqlalchemy.url"])

        print("Creating initial migration...")
        # Create a new revision based on current models
        command.revision(alembic_cfg, autogenerate=True, message="Initial migration")
        print("Initial migration created successfully!")
        return True
    except ImportError:
        print("Alembic not installed, cannot create initial migration.")
        return False
    except Exception as e:
        print(f"Error creating initial migration: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "--migrations",
        action="store_true",
        help="Use alembic migrations instead of direct table creation"
    )
    parser.add_argument(
        "--create-initial",
        action="store_true",
        help="Create initial migration file"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct table creation instead of migrations"
    )

    args = parser.parse_args()

    if args.create_initial:
        # Create initial migration file
        asyncio.run(create_initial_migration())
    elif args.direct:
        # Use direct table creation
        asyncio.run(initialize_database(use_migrations=False))
    else:
        # Use migrations (default)
        asyncio.run(initialize_database(use_migrations=True))