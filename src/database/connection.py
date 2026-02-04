import os
import socket
import urllib.parse
from dotenv import load_dotenv
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from sqlmodel import create_engine, Session, SQLModel
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


def resolve_hostname_to_ipv4(hostname: str) -> str:
    """
    Resolve a hostname to its IPv4 address.

    This is useful in containerized environments where IPv6 resolution
    may be attempted but not properly supported, causing connection failures.

    Args:
        hostname: The hostname to resolve (e.g., 'ep-name.us-east-1.aws.neon.tech')

    Returns:
        The resolved IPv4 address as a string

    Raises:
        socket.gaierror: If hostname resolution fails
    """
    # Use getaddrinfo to resolve hostname, forcing IPv4 (AF_INET)
    addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
    # addr_info is a list of tuples: (family, type, proto, canonname, sockaddr)
    # sockaddr for IPv4 is (address, port), so we take [0][4][0]
    ipv4_address = addr_info[0][4][0]
    return ipv4_address


def apply_ipv4_resolution(db_url: str) -> str:
    """
    Replace hostname in database URL with its IPv4 address if FORCE_IPV4 is set.

    This is needed in Kubernetes/containerized environments where DNS may resolve
    to IPv6 addresses that cannot be reached, causing connection failures.

    For Neon databases, also adds the endpoint ID parameter required for SNI support
    when connecting via IP address.

    Args:
        db_url: The original database URL with hostname

    Returns:
        Database URL with hostname replaced by IPv4 address if FORCE_IPV4=true,
        otherwise returns original URL unchanged
    """
    force_ipv4 = os.environ.get("FORCE_IPV4", "false").lower() == "true"

    if not force_ipv4:
        return db_url

    import logging
    logger = logging.getLogger(__name__)

    # Parse the URL to extract hostname
    # Format: postgresql+psycopg://user:pass@hostname:port/dbname?params
    try:
        # Extract the hostname part between @ and / (or : for port)
        if "@" in db_url:
            # Split at @ to get the part after credentials
            after_at = db_url.split("@", 1)[1]
            # The hostname is before the next / or : (for port)
            if "/" in after_at:
                hostname_part = after_at.split("/", 1)[0]
            else:
                hostname_part = after_at

            # If there's a port, extract just the hostname
            if ":" in hostname_part:
                hostname = hostname_part.split(":", 1)[0]
                port_part = ":" + hostname_part.split(":", 1)[1]
            else:
                hostname = hostname_part
                port_part = ""

            # Resolve hostname to IPv4
            ipv4_address = resolve_hostname_to_ipv4(hostname)
            logger.info(f"Resolved {hostname} to IPv4 address: {ipv4_address}")

            # Replace hostname with IPv4 address in URL
            modified_url = db_url.replace(f"@{hostname_part}", f"@{ipv4_address}{port_part}")

            # For Neon databases, add endpoint ID parameter for SNI support
            # Extract endpoint ID (first part before first dot) from hostname
            if "neon.tech" in hostname or "aws.neon" in hostname:
                endpoint_id = hostname.split(".")[0]
                logger.info(f"Detected Neon database, adding endpoint ID: {endpoint_id}")

                # Add or append the endpoint parameter
                if "?" in modified_url:
                    # Parameters already exist, append with &
                    modified_url += f"&options=endpoint%3D{endpoint_id}"
                else:
                    # No parameters yet, add with ?
                    modified_url += f"?options=endpoint%3D{endpoint_id}"

            logger.info(f"Database URL updated to use IPv4 address")

            return modified_url
    except Exception as e:
        logger.warning(f"Failed to resolve hostname to IPv4: {e}. Using original URL.")
        return db_url

    return db_url


# Apply IPv4 resolution if FORCE_IPV4 environment variable is set
async_db_url = apply_ipv4_resolution(async_db_url)
sync_db_url = apply_ipv4_resolution(sync_db_url)

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

def get_sync_session() -> Generator[Session, None, None]:
    """Get a synchronous session for sync operations like migrations."""
    with Session(sync_engine) as session:
        yield session

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an asynchronous session for async operations."""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """
    Initialize the database with exponential backoff retry logic.
    Retries connection failures with increasing delays (1s, 2s, 4s, 8s, 16s).
    """
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    max_retries = 5
    retry_count = 0
    base_delay = 1  # Start with 1 second delay

    while retry_count < max_retries:
        try:
            logger.info(f"Attempting database initialization (attempt {retry_count + 1}/{max_retries})")
            async with async_engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to initialize database after {max_retries} attempts: {e}")
                raise

            delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff: 1, 2, 4, 8, 16
            logger.warning(f"Database connection failed (attempt {retry_count}/{max_retries}): {e}")
            logger.info(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)

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