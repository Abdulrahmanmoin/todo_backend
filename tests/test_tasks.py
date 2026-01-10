import pytest
import uuid
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from typing import AsyncGenerator

from src.main import app
from src.database import get_async_session
from src.models import User, Task, TaskCreate
from src.utils.auth import hash_password


# Create an in-memory SQLite database for testing
@pytest.fixture(scope="function")
async def async_session():
    """Create an in-memory async session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(async_session):
    """Create a test client with dependency overrides."""
    async def override_get_async_session():
        yield async_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(async_session):
    """Create a test user."""
    from src.models import User
    user = User(
        user_id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpassword"),
        is_active=True
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(test_user):
    """Create authentication headers with a JWT token."""
    # For testing purposes, we'll need to create a valid JWT token
    import jwt
    from datetime import datetime, timedelta
    from src.config import settings

    # Create a token for the test user
    data = {"user_id": str(test_user.user_id)}
    token = jwt.encode(
        data,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_task_success(client, test_user, auth_headers):
    """Test successful task creation."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"
    assert data["is_completed"] is False
    assert "task_id" in data
    assert data["user_id"] == str(test_user.user_id)


@pytest.mark.asyncio
async def test_create_task_unauthorized_user(client, test_user, auth_headers):
    """Test that a user cannot create tasks for another user."""
    # Create a different user ID
    other_user_id = uuid.uuid4()

    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{other_user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )

    assert response.status_code == 403
    assert "Not authorized to create tasks for this user" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_task_invalid_data(client, test_user, auth_headers):
    """Test task creation with invalid data."""
    # Missing required title field
    task_data = {
        "description": "Test Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_task_missing_auth(client, test_user):
    """Test that creating a task without authentication fails."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data
    )

    assert response.status_code == 403  # Or 401 depending on auth setup


@pytest.mark.asyncio
async def test_get_task_success(client, test_user, auth_headers, async_session):
    """Test successful retrieval of a specific task."""
    # First create a task
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    created_task = response.json()
    task_id = created_task["task_id"]

    # Now retrieve the task
    response = await client.get(
        f"/api/{test_user.user_id}/tasks/{task_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"
    assert data["is_completed"] is False
    assert data["user_id"] == str(test_user.user_id)


@pytest.mark.asyncio
async def test_get_task_unauthorized_access(client, test_user, auth_headers):
    """Test that a user cannot access tasks belonging to another user."""
    # Create a different user ID
    other_user_id = uuid.uuid4()
    task_id = uuid.uuid4()

    response = await client.get(
        f"/api/{other_user_id}/tasks/{task_id}",
        headers=auth_headers
    )

    assert response.status_code == 403
    assert "Not authorized to access tasks for this user" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_task_not_found(client, test_user, auth_headers):
    """Test retrieval of a non-existent task."""
    # Use a random task ID that doesn't exist
    non_existent_task_id = uuid.uuid4()

    response = await client.get(
        f"/api/{test_user.user_id}/tasks/{non_existent_task_id}",
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_get_task_missing_auth(client, test_user):
    """Test that retrieving a task without authentication fails."""
    task_id = uuid.uuid4()

    response = await client.get(
        f"/api/{test_user.user_id}/tasks/{task_id}"
    )

    assert response.status_code == 403  # Or 401 depending on auth setup


@pytest.mark.asyncio
async def test_update_task_success(client, test_user, auth_headers, async_session):
    """Test successful task update."""
    # First create a task
    task_data = {
        "title": "Original Task",
        "description": "Original Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    created_task = response.json()
    task_id = created_task["task_id"]

    # Now update the task
    update_data = {
        "title": "Updated Task",
        "description": "Updated Description",
        "is_completed": True
    }

    response = await client.put(
        f"/api/{test_user.user_id}/tasks/{task_id}",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["title"] == "Updated Task"
    assert data["description"] == "Updated Description"
    assert data["is_completed"] is True
    assert data["user_id"] == str(test_user.user_id)


@pytest.mark.asyncio
async def test_update_task_partial_update(client, test_user, auth_headers, async_session):
    """Test partial task update (only updating title)."""
    # First create a task
    task_data = {
        "title": "Original Task",
        "description": "Original Description",
        "is_completed": False
    }

    response = await client.post(
        f"/api/{test_user.user_id}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    created_task = response.json()
    task_id = created_task["task_id"]

    # Now partially update the task (only title)
    update_data = {
        "title": "Partially Updated Task"
    }

    response = await client.put(
        f"/api/{test_user.user_id}/tasks/{task_id}",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["title"] == "Partially Updated Task"
    assert data["description"] == "Original Description"  # Should remain unchanged
    assert data["is_completed"] is False  # Should remain unchanged
    assert data["user_id"] == str(test_user.user_id)


@pytest.mark.asyncio
async def test_update_task_unauthorized_user(client, test_user, auth_headers):
    """Test that a user cannot update tasks belonging to another user."""
    # Create a different user ID
    other_user_id = uuid.uuid4()
    task_id = uuid.uuid4()

    update_data = {
        "title": "Updated Task",
        "description": "Updated Description",
        "is_completed": True
    }

    response = await client.put(
        f"/api/{other_user_id}/tasks/{task_id}",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 403
    assert "Not authorized to update tasks for this user" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_task_not_found(client, test_user, auth_headers):
    """Test updating a non-existent task."""
    # Use a random task ID that doesn't exist
    non_existent_task_id = uuid.uuid4()
    update_data = {
        "title": "Updated Task",
        "description": "Updated Description",
        "is_completed": True
    }

    response = await client.put(
        f"/api/{test_user.user_id}/tasks/{non_existent_task_id}",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.asyncio
async def test_update_task_missing_auth(client, test_user):
    """Test that updating a task without authentication fails."""
    task_id = uuid.uuid4()
    update_data = {
        "title": "Updated Task",
        "description": "Updated Description",
        "is_completed": True
    }

    response = await client.put(
        f"/api/{test_user.user_id}/tasks/{task_id}",
        json=update_data
    )

    assert response.status_code == 403  # Or 401 depending on auth setup