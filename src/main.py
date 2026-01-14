import os
import sys
import asyncio

# Add Windows-specific event loop fix for psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from .database import get_session, get_async_session
from .models import User, Task  # Import your models
from .routers import auth, tasks  # Import your routers
from .api import auth as api_auth, tasks as api_tasks  # Import the new API endpoints
from .config import settings


# Create async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle application startup and shutdown events.
    """
    # Startup
    print("Application starting up...")

    # Initialize database
    # Note: In a real application, you'd typically run migrations here

    yield

    # Shutdown
    print("Application shutting down...")


# Create FastAPI app instance with proper configuration
app = FastAPI(
    title="Todo API",
    description="A FastAPI application for managing todos with authentication",
    version="1.0.0",
    lifespan=lifespan
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Security scheme for JWT
security = HTTPBearer()


# Basic health check route
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint to verify the API is running.
    """
    return {"status": "ok", "message": "Todo API is running"}


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(api_auth.router, prefix="/api/v1/api", tags=["API Authentication"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(api_tasks.router, prefix="/api", tags=["API Tasks"])


# Global error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# JWT authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current authenticated user from JWT token.
    This function is currently not used directly - the auth utility function is used instead.
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str = payload.get("user_id")

        if user_id_str is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )

        # Convert string to UUID
        try:
            import uuid
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid user ID format"
            )

        # Fetch user from database
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )


# Root route
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint for the API.
    """
    return {
        "message": "Welcome to the Todo API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7860,
        reload=True,
        log_level="info"
    )