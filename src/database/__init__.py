"""
Database package for the Todo application.

This package contains database connection utilities and setup for Neon PostgreSQL.
"""

from .connection import (
    get_async_session,
    get_sync_session,
    async_engine,
    sync_engine,
    init_db,
    drop_db,
    get_engine,
    is_development,
    get_database_config,
)

# Alias for backward compatibility
get_session = get_sync_session

__all__ = [
    "get_async_session",
    "get_sync_session",
    "get_session",
    "async_engine",
    "sync_engine",
    "init_db",
    "drop_db",
    "get_engine",
    "is_development",
    "get_database_config",
]