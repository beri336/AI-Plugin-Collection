# tests/test_api_manager.py

'''
Unit tests for APIManager
  This test suite validates the core functionality of the APIManager module.

- Tests API connection verification with success and failure scenarios
- Validates model list retrieval and data formatting
- Checks text generation with mocked responses
- Tests model existence check
- Validates running model management
- Uses pytest and unittest.mock for isolated tests
- Mocks HTTP requests for fast, deterministic tests
'''

from modules.api_manager import APIManager
from unittest.mock import patch, MagicMock
import pytest


# --------------------------------------------------------------------
# Test: check_connection()
# --------------------------------------------------------------------
@patch("modules.api_manager.requests.get")
def test_check_connection_success(mock_get):
    # prepare mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    manager = APIManager()
    ok = manager.check_connection()

    mock_get.assert_called_once()
    assert ok is True
    assert manager.service._is_api_reachable is True

@patch("modules.api_manager.requests.get")
def test_check_connection_fail(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_get.return_value = mock_resp

    manager = APIManager()
    ok = manager.check_connection()

    mock_get.assert_called_once()
    assert ok is False
    assert manager.service._is_api_reachable is False


# --------------------------------------------------------------------
# Test: get_detailed_list_models()
# --------------------------------------------------------------------
@patch("modules.api_manager.requests.get")
def test_get_detailed_list_models(mock_get):
    fake_models = {
        "models": [
            {
                "name": "llama3.2:3b",
                "digest": "1234567890abcdef",
                "size": 1_050_000_000,
                "modified_at": "2025-12-23T00:00:00Z",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_models
    mock_get.return_value = mock_resp

    manager = APIManager()
    result = manager.get_detailed_list_models()

    mock_get.assert_called_once()
    assert isinstance(result, list)
    assert result[0]["name"] == "llama3.2:3b"
    assert "size" in result[0]
    assert "modified" in result[0]


# --------------------------------------------------------------------
# Test: generate()
# --------------------------------------------------------------------
@patch("modules.api_manager.requests.post")
def test_generate(mock_post):
    fake_response = {"response": "Hello world!"}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response
    mock_post.return_value = mock_resp

    manager = APIManager()
    data = manager.generate("llama3.2:3b", "Hi!")

    mock_post.assert_called_once()
    assert isinstance(data, dict)
    assert data["response"] == "Hello world!"

# --------------------------------------------------------------------
# Test: model_exists()
# --------------------------------------------------------------------
def test_model_exists():
    manager = APIManager()
    manager.list_of_models = ["llama3.2:3b"]
    assert manager.model_exists("llama3.2:3b")
    assert not manager.model_exists("nonexistent:model")

# --------------------------------------------------------------------
# Test: stop_running_model() with mock names
# --------------------------------------------------------------------
@patch("modules.api_manager.requests.post")
@patch.object(APIManager, "get_running_model_names", return_value=["llama3.2:3b"])
def test_stop_running_model(mock_names, mock_post):
    mock_resp = MagicMock(status_code=200)
    mock_post.return_value = mock_resp

    manager = APIManager()
    result = manager.stop_running_model("llama3.2:3b")
    assert result is True
