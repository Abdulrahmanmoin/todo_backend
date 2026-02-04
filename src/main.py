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

from .database import get_session, get_async_session, init_db
from .models import *  # Import all models to ensure they are registered
from .routers import auth, tasks  # Import your routers
from .api import auth as api_auth, tasks as api_tasks  # Import the new API endpoints
from .api.chat import router as chat_router # Import chat API
from .config import settings


# Create async context manager for lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle application startup and shutdown events.
    """
    # Startup
    print("Application starting up...")
    loop = asyncio.get_running_loop()
    print(f"Current event loop: {type(loop)}")
    try:
        await init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    yield
    # Shutdown
    print("Application shutting down...")


# Create FastAPI app instance
app = FastAPI(
    title="Todo API",
    description="A FastAPI application for managing todos with AI assistance",
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


# Include routers
# Note: AI chat router included FIRST to ensure no shadowing by other routers using /api prefix
app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(api_tasks.router, prefix="/api", tags=["API Tasks"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(api_auth.router, prefix="/api/v1/api", tags=["API Authentication"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for Kubernetes liveness and readiness probes.
    Returns 200 OK with healthy status when the API is running.
    """
    return {"status": "healthy"}


@app.get("/api/test-route")
async def test_route():
    return {"message": "API prefix is working"}


# Global error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Root route
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the Todo API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment or default to 8000 for consistency with Docker
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )