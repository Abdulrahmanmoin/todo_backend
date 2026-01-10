#!/usr/bin/env python3
"""
Script to run database migrations for the Todo application.
This script provides command-line interface to manage database migrations.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alembic.config import Config
from alembic import command
from backend.src.database.connection import get_database_config


def run_migrations(alembic_cfg, revision="head"):
    """Run migrations to the specified revision."""
    print(f"Running migrations to revision: {revision}")
    command.upgrade(alembic_cfg, revision)
    print("Migrations completed successfully!")


def create_migration(alembic_cfg, message):
    """Create a new migration file."""
    print(f"Creating new migration: {message}")
    command.revision(alembic_cfg, autogenerate=True, message=message)
    print("Migration created successfully!")


def downgrade_migrations(alembic_cfg, revision):
    """Downgrade migrations to the specified revision."""
    print(f"Downgrading migrations to revision: {revision}")
    command.downgrade(alembic_cfg, revision)
    print("Downgrade completed successfully!")


def show_current_revision(alembic_cfg):
    """Show the current revision."""
    command.current(alembic_cfg)


def show_migration_history(alembic_cfg):
    """Show migration history."""
    command.history(alembic_cfg, verbose=True)


def main():
    parser = argparse.ArgumentParser(description="Manage database migrations")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade", "create", "current", "history"],
        help="Action to perform: upgrade, downgrade, create, current, or history"
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="Revision to upgrade/downgrade to (default: head for upgrade)"
    )
    parser.add_argument(
        "--message",
        help="Message for new migration (required for create action)"
    )

    args = parser.parse_args()

    # Create alembic config
    alembic_cfg = Config("backend/alembic.ini")

    # Get database configuration and set the URL
    config_values = get_database_config()
    alembic_cfg.set_main_option("sqlalchemy.url", config_values["sqlalchemy.url"])

    try:
        if args.action == "upgrade":
            run_migrations(alembic_cfg, args.revision)
        elif args.action == "downgrade":
            if args.revision == "head":
                print("Error: You must specify a revision for downgrade action.")
                sys.exit(1)
            downgrade_migrations(alembic_cfg, args.revision)
        elif args.action == "create":
            if not args.message:
                print("Error: You must provide a message for the new migration.")
                sys.exit(1)
            create_migration(alembic_cfg, args.message)
        elif args.action == "current":
            show_current_revision(alembic_cfg)
        elif args.action == "history":
            show_migration_history(alembic_cfg)
    except Exception as e:
        print(f"Error executing migration command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()