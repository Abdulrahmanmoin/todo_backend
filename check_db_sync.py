import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("DATABASE_URL")
if url:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("sslmode=require", "sslmode=require")

print(f"Connecting to {url.split('@')[-1]}...")
engine = create_engine(url)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        tables = [row[0] for row in result]
        print(f"Found tables: {tables}")
except Exception as e:
    print(f"Error: {e}")
finally:
    engine.dispose()
