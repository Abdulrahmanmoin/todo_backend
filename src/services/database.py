from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import os
from ..config import settings


# Engines will be created lazily to avoid initialization issues during import
def get_sync_engine():
    """Get synchronous engine for sync operations."""
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
    )


def get_async_engine():
    """Get asynchronous engine for async operations."""
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# Global engine instances (initialized on first access)
_sync_engine = None
_async_engine = None


def get_sync_engine():
    """Get synchronous engine for sync operations."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
        )
    return _sync_engine


def get_async_engine():
    """Get asynchronous engine for async operations."""
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _async_engine


def get_session() -> Session:
    """Get synchronous database session."""
    with Session(get_sync_engine()) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session."""
    async with AsyncSession(get_async_engine()) as session:
        yield session


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager to create tables on startup."""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    await get_async_engine().dispose()


async def init_db():
    """Initialize the database by creating all tables."""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)