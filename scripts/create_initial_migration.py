#!/usr/bin/env python3
"""
Script to create the initial database migration for the Todo application.
This script will generate the first migration based on the existing models.
"""

import os
import sys
from pathlib import Path

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up environment for alembic
os.environ.setdefault("ENVIRONMENT", "development")

from alembic.config import Config
from alembic import command
from backend.src.database.connection import get_database_config


def create_initial_migration():
    """Create the initial migration based on existing models."""
    print("Creating initial migration...")

    # Create alembic config
    alembic_cfg = Config("backend/alembic.ini")

    # Get database configuration and set the URL
    config_values = get_database_config()
    alembic_cfg.set_main_option("sqlalchemy.url", config_values["sqlalchemy.url"])

    # Create the versions directory if it doesn't exist
    versions_dir = Path("backend/alembic/versions")
    versions_dir.mkdir(exist_ok=True)

    # Create initial migration
    try:
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Initial migration for User and Task models",
            sql=False  # Generate Python file, not raw SQL
        )
        print("Initial migration created successfully!")
        print("You can find it in backend/alembic/versions/")
    except Exception as e:
        print(f"Error creating initial migration: {e}")
        return False

    return True


if __name__ == "__main__":
    create_initial_migration()