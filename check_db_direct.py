import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("DATABASE_URL")
if url and url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://")
elif url and url.startswith("postgresql+asyncpg://"):
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

async def check():
    print(f"Connecting to {url.split('@')[-1]}...")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result]
            print(f"Found tables: {tables}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
