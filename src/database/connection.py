import os
import urllib.parse
from dotenv import load_dotenv
from typing import AsyncGenerator
from sqlmodel import create_engine, Session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from pathlib import Path

# Load environment variables from .env file
# Try current working directory first
load_dotenv()

# If critical variables are missing, try to find .env in the backend root relative to this file
if not os.environ.get("DATABASE_URL") and not os.environ.get("DB_USER"):
    # Path to d:\todo_phase1\backend from d:\todo_phase1\backend\src\database\connection.py
    backend_root = Path(__file__).resolve().parent.parent.parent
    dotenv_path = backend_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
    else:
        # Try root project directory (one level up from backend)
        root_dir = backend_root.parent
        root_dotenv = root_dir / ".env"
        if root_dotenv.exists():
            load_dotenv(dotenv_path=root_dotenv)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to separate environment variables if DATABASE_URL is not provided
    db_user = os.environ.get("DB_USER", "todo_user")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_host = os.environ.get("DB_HOST", "ep-todo-db.us-east-1.aws.neon.tech")
    db_name = os.environ.get("DB_NAME", "todo_db")
    db_ssl_mode = os.environ.get("DB_SSL_MODE", "require")

    # URL encode the password in case it contains special characters
    encoded_password = urllib.parse.quote_plus(db_password) if db_password else ""

    # Switch to psycopg as the primary driver for both async and sync.
    # It is more stable on Python 3.13 and Windows than asyncpg.
    async_db_url = f"postgresql+psycopg://{db_user}:{encoded_password}@{db_host}/{db_name}?sslmode={db_ssl_mode}"
    sync_db_url = f"postgresql+psycopg://{db_user}:{encoded_password}@{db_host}/{db_name}?sslmode={db_ssl_mode}"
else:
    # If DATABASE_URL is provided, normalize it to use psycopg
    # replacing any asyncpg or plain postgresql prefixes.
    base_url = DATABASE_URL
    if "postgresql+asyncpg://" in base_url:
        base_url = base_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    elif "postgresql://" in base_url and "postgresql+psycopg://" not in base_url:
        base_url = base_url.replace("postgresql://", "postgresql+psycopg://")
    
    # Ensure sslmode is used instead of ssl (asyncpg-specific)
    if "ssl=" in base_url and "sslmode=" not in base_url:
        base_url = base_url.replace("ssl=", "sslmode=")
    if "sslmode=true" in base_url:
        base_url = base_url.replace("sslmode=true", "sslmode=require")
        
    async_db_url = base_url
    sync_db_url = base_url

# Create async engine
async_engine = create_async_engine(
    async_db_url,
    echo=os.environ.get("DB_ECHO", "False").lower() == "true",  # Set to True for debugging
    pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
    max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "300")),  # Recycle connections after 5 minutes
)


# Create sync engine for sync operations (migrations, etc.)
# Using psycopg (v3) driver for Python 3.13 compatibility
sync_engine = create_engine(
    sync_db_url,
    echo=os.environ.get("DB_ECHO", "False").lower() == "true",
    pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
    max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,
    pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "300")),
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create sync session maker for sync operations
SyncSessionLocal = Session

def get_sync_session():
    """Get a synchronous session for sync operations like migrations."""
    with Session(sync_engine) as session:
        yield session

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an asynchronous session for async operations."""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize the database - typically used for testing or initial setup."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# Function to get the correct engine based on environment
def get_engine(is_async: bool = True):
    """
    Get the appropriate engine based on whether async operations are needed.

    Args:
        is_async: If True, returns async engine; if False, returns sync engine
    """
    return async_engine if is_async else sync_engine

# Function to check if running in development mode
def is_development():
    """Check if running in development mode."""
    return os.environ.get("ENVIRONMENT", "development").lower() == "development"

# Function to get database configuration for migrations
def get_database_config():
    """Get database configuration for migration tools."""
    return {
        "sqlalchemy.url": DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://"),
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


async def drop_db():
    """Drop all tables in the database - USE WITH CAUTION in development only!"""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


def get_all_models():
    """Return all SQLModel models for migration autogenerate."""
    from backend.src.models.user import User
    from backend.src.models.task import Task
    return [User, Task]