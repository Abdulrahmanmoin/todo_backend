import os
from dotenv import load_dotenv
from pathlib import Path
from pydantic_settings import BaseSettings

# Load environment variables from .env file
# Try current working directory first
load_dotenv()

# If critical variables are missing, try to find .env in the backend root relative to this file
if not os.environ.get("DATABASE_URL") and not os.environ.get("JWT_SECRET_KEY"):
    # Path to d:\todo_phase1\backend from d:\todo_phase1\backend\src\config.py
    backend_root = Path(__file__).resolve().parent.parent
    dotenv_path = backend_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
    else:
        # Try root project directory (one level up from backend)
        root_dir = backend_root.parent
        root_dotenv = root_dir / ".env"
        if root_dotenv.exists():
            load_dotenv(dotenv_path=root_dotenv)


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/todo_db"
    DATABASE_ECHO: bool = False

    # JWT settings
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:7860"

    # Better Auth settings (if using)
    BETTER_AUTH_SECRET: str = ""
    BETTER_AUTH_URL: str = "http://localhost:8080"


settings = Settings()