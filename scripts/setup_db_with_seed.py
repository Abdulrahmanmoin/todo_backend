#!/usr/bin/env python3
"""
Combined database setup script for the Todo application.
This script initializes the database tables and seeds them with sample data.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.src.database.init_db import initialize_database
from backend.src.database.seed_db import seed_database


async def setup_database_with_seed(use_migrations: bool = True):
    """
    Initialize the database and seed it with sample data.

    Args:
        use_migrations: If True, use alembic migrations; if False, use direct table creation
    """
    print("Starting database setup with seeding...")

    # Initialize the database (create tables)
    success = await initialize_database(use_migrations=use_migrations)

    if not success:
        print("Database initialization failed. Cannot proceed with seeding.")
        return False

    # Seed the database with sample data
    try:
        await seed_database()
        print("Database setup with seeding completed successfully!")
        return True
    except Exception as e:
        print(f"Error during seeding: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Combined database setup and seeding script")
    parser.add_argument(
        "--migrations",
        action="store_true",
        help="Use alembic migrations instead of direct table creation"
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct table creation instead of migrations"
    )

    args = parser.parse_args()

    use_migrations = True  # Default to using migrations
    if args.direct:
        use_migrations = False
    elif args.migrations:
        use_migrations = True

    asyncio.run(setup_database_with_seed(use_migrations=use_migrations))