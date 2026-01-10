#!/usr/bin/env python3
"""
Simple database setup script for the Todo application.
This script handles the complete database setup process.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend/src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def setup_database():
    """Complete database setup process."""
    print("Setting up database for Todo application...")

    # Import after adding to path
    from backend.src.database.init_db import initialize_database

    # Set environment if not already set
    if not os.environ.get("ENVIRONMENT"):
        os.environ["ENVIRONMENT"] = "development"

    success = await initialize_database(use_migrations=True)

    if success:
        print("\n✅ Database setup completed successfully!")
        print("You can now run the application with database connectivity.")
    else:
        print("\n❌ Database setup failed!")
        print("Check the error messages above and try again.")
        return False

    return True


def main():
    """Main entry point for the setup script."""
    print("Todo Application - Database Setup")
    print("=" * 40)

    try:
        # Run the async setup
        success = asyncio.run(setup_database())

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()