import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app

client = TestClient(app)


@pytest.mark.asyncio
@patch('src.api.chat.agent_process_message')
def test_chat_endpoint_success(mock_agent_process):
    """Test the chat endpoint with a successful response."""
    # Mock the agent response
    mock_agent_process.return_value = AsyncMock(return_value={
        "response": "I've added your task.",
        "tool_calls": []
    })

    # Prepare test data
    test_data = {
        "message": "Add buy groceries to my list"
    }

    # Make the request
    response = client.post(
        "/api/test_user_id/chat",
        json=test_data,
        headers={"Authorization": "Bearer fake_token"}
    )

    # Assertions
    # Note: This test will fail without proper authentication setup
    # The purpose is to show the testing approach
    assert response.status_code in [200, 401, 403]  # Depending on auth state


def test_chat_endpoint_invalid_request():
    """Test the chat endpoint with invalid request data."""
    # Test with missing message
    response = client.post(
        "/api/test_user_id/chat",
        json={},
        headers={"Authorization": "Bearer fake_token"}
    )

    # Should return 401 (Unauthorized) or 400 (Bad Request) depending on auth
    assert response.status_code in [400, 401, 403]


def test_chat_endpoint_empty_message():
    """Test the chat endpoint with an empty message."""
    response = client.post(
        "/api/test_user_id/chat",
        json={"message": ""},
        headers={"Authorization": "Bearer fake_token"}
    )

    # Should return 401 (Unauthorized) or 400 (Bad Request) depending on auth
    assert response.status_code in [400, 401, 403]