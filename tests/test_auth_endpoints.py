"""
Test cases for the FastAPI authentication endpoints.
"""
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.pool import StaticPool
from typing import AsyncGenerator
import uuid
from datetime import datetime

from backend.src.main import app
from backend.src.database import get_async_session
from backend.src.models import User
from backend.src.config import settings


# Test database setup for testing
@pytest.fixture(scope="function")
def test_db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import SQLModel

    engine = create_engine(
        "sqlite:///:memory:",
        echo=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(bind=engine)

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession
    )

    yield session_local()


@pytest.fixture(scope="function")
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_register_user_success():
    """Test successful user registration."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert "hashed_password" not in data  # Should not return sensitive data


@pytest.mark.asyncio
async def test_register_user_duplicate_email():
    """Test user registration with duplicate email."""
    # First registration
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "testuser1",
                "password": "TestPass123!"
            }
        )

        # Second registration with same email
        response = await ac.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",  # Same email
                "username": "testuser2",  # Different username
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]


@pytest.mark.asyncio
async def test_register_user_duplicate_username():
    """Test user registration with duplicate username."""
    # First registration
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "test1@example.com",
                "username": "samename",
                "password": "TestPass123!"
            }
        )

        # Second registration with same username
        response = await ac.post(
            "/auth/register",
            json={
                "email": "test2@example.com",  # Different email
                "username": "samename",  # Same username
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Username already taken" in data["detail"]


@pytest.mark.asyncio
async def test_register_user_invalid_email():
    """Test user registration with invalid email format."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/register",
            json={
                "email": "invalid-email",  # Invalid email
                "username": "testuser",
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid email format" in data["detail"]


@pytest.mark.asyncio
async def test_register_user_invalid_username():
    """Test user registration with invalid username."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "username": "ab",  # Too short username
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Username must be 3-30 characters long" in data["detail"]


@pytest.mark.asyncio
async def test_register_user_weak_password():
    """Test user registration with weak password."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Test short password
        response = await ac.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "weak"  # Too short
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Password must be at least 8 characters long" in data["detail"]

        # Test password without complexity
        response = await ac.post(
            "/auth/register",
            json={
                "email": "test2@example.com",
                "username": "testuser2",
                "password": "password123"  # Missing special character and uppercase
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Password must contain at least one uppercase letter" in data["detail"]


@pytest.mark.asyncio
async def test_login_success():
    """Test successful user login."""
    # First register a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "TestPass123!"
            }
        )

        # Then try to login
        response = await ac.post(
            "/auth/login",
            json={
                "email": "login@example.com",
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    # First register a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "login2@example.com",
                "username": "loginuser2",
                "password": "TestPass123!"
            }
        )

        # Try to login with wrong password
        response = await ac.post(
            "/auth/login",
            json={
                "email": "login2@example.com",
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "Incorrect email or password" in data["detail"]

        # Try to login with non-existent email
        response = await ac.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPass123!"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "Incorrect email or password" in data["detail"]


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user with valid token."""
    # Register and login a user to get a token
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "current@example.com",
                "username": "currentuser",
                "password": "TestPass123!"
            }
        )

        login_response = await ac.post(
            "/auth/login",
            json={
                "email": "current@example.com",
                "password": "TestPass123!"
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]

        # Use the token to get current user
        response = await ac.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == "current@example.com"
        assert user_data["username"] == "currentuser"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test getting current user with invalid token."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout():
    """Test user logout endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/auth/logout")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"