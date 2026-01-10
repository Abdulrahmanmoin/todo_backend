import pytest
import os
from unittest.mock import patch
from backend.src.database.connection import (
    DATABASE_URL,
    async_engine,
    sync_engine,
    get_async_session,
    get_sync_session,
    is_development,
    get_database_config,
    get_engine
)
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session


def test_database_url_configuration():
    """Test that DATABASE_URL is properly configured."""
    assert DATABASE_URL is not None
    assert "postgresql" in DATABASE_URL
    assert "asyncpg" in DATABASE_URL


def test_engines_created():
    """Test that both async and sync engines are created."""
    assert async_engine is not None
    assert sync_engine is not None


def test_get_engine_function():
    """Test the get_engine function returns appropriate engines."""
    async_eng = get_engine(is_async=True)
    sync_eng = get_engine(is_async=False)

    assert async_eng == async_engine
    assert sync_eng == sync_engine


def test_development_mode():
    """Test the is_development function."""
    # Test default behavior (should be development by default)
    assert is_development() == True

    # Test with explicit development environment
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        assert is_development() == True

    # Test with production environment
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        assert is_development() == False


def test_database_config():
    """Test the get_database_config function."""
    config = get_database_config()

    assert "sqlalchemy.url" in config
    assert config["pool_pre_ping"] is True
    assert config["pool_recycle"] == 300
    assert "postgresql://" in config["sqlalchemy.url"]  # Should be sync URL for migrations


@pytest.mark.asyncio
async def test_async_session_generator():
    """Test that the async session generator works."""
    async_gen = get_async_session()
    session = await async_gen.__anext__()

    assert isinstance(session, AsyncSession)

    # Close the generator
    try:
        await async_gen.__anext__()
    except StopAsyncIteration:
        pass  # Expected when generator is exhausted


def test_sync_session_generator():
    """Test that the sync session generator works."""
    sync_gen = get_sync_session()
    session = next(sync_gen)

    assert isinstance(session, Session)