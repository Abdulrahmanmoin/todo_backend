import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("DATABASE_URL")
if url and url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://")
elif url and url.startswith("postgresql+asyncpg://"):
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

# Import models to register them
import sys
sys.path.append(os.path.abspath(os.curdir))
from src.models.user import User
from src.models.task import Task
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.token_blacklist import TokenBlacklist

async def create_tables():
    print(f"Connecting to database to create tables...")
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            print("Running create_all...")
            await conn.run_sync(SQLModel.metadata.create_all)
            print("Tables created (if they didn't exist).")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
