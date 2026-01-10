from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as SQLAlchemyAsyncSession
from sqlalchemy.pool import QueuePool
import os

from .config import settings


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for debugging SQL queries
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session.
    """
    async with AsyncSession(engine) as session:
        yield session


# For sync operations if needed
from sqlmodel import create_engine as sync_create_engine
from sqlmodel import Session

sync_engine = sync_create_engine(
    settings.DATABASE_URL.replace("+asyncpg", "+psycopg2"),
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)


def get_session() -> Session:
    """
    Get sync database session.
    """
    with Session(sync_engine) as session:
        yield session