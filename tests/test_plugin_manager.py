# tests/test_plugin_manager.py

'''
Unit tests for OllamaManager (plugin facade)
  This test suite validates the central manager class and its integration.

- Tests backend switching between API and CLI
- Validates model management operations (list, pull, delete)
- Checks service health checks and status queries
- Tests conversation management
- Validates cache operations and statistics
- Checks helper function integration
- Tests configuration access
- Mocks all dependencies for isolated tests
'''

from modules.plugin_manager import OllamaManager, OllamaBackend
from unittest.mock import patch, MagicMock
import pytest

# --------------------------------------------------------------------
# Fixture: Basic manager instance
# --------------------------------------------------------------------
@pytest.fixture
def manager():
    return OllamaManager(verbose=False)

# --------------------------------------------------------------------
# Backend Control
# --------------------------------------------------------------------
def test_switch_backend(manager):
    assert manager.get_backend_type() == OllamaBackend.API
    manager.switch_backend(OllamaBackend.CMD)
    assert manager.get_backend_type() == OllamaBackend.CMD

# --------------------------------------------------------------------
# Model Listing
# --------------------------------------------------------------------
@patch.object(OllamaManager, "refresh_models")
def test_list_models(mock_refresh, manager):
    manager._backend.get_list_model_names = MagicMock(return_value=["llama", "gemma"])

    names = manager.list_models()

    mock_refresh.assert_called_once()
    manager._backend.get_list_model_names.assert_called_once()
    assert names == ["llama", "gemma"]

@patch.object(OllamaManager, "refresh_models")
def test_list_models_detailed(mock_refresh, manager):
    fake_models = [{"name": "llama", "size": "2GB", "modified": "yesterday"}]
    manager._backend.get_detailed_list_models = MagicMock(return_value=fake_models)

    models = manager.list_models_detailed()

    assert isinstance(models, list)
    assert models[0]["name"] == "llama"

# --------------------------------------------------------------------
# Model Info
# --------------------------------------------------------------------
def test_model_info_prints(manager, capsys):
    fake_info = {
        "model_name": "llama",
        "details": {"architecture": "LLaMA", "parameters": "4B"},
        "parameters": {"temp": 1},
    }
    manager._backend.get_model_info = MagicMock(return_value=fake_info)

    info = manager.model_info("llama")
    assert info == fake_info
    captured = capsys.readouterr().out
    assert "Model Info" in captured

# --------------------------------------------------------------------
# Pull / Delete / Existence
# --------------------------------------------------------------------
def test_pull_model_via_api(manager):
    manager.api.pull_model = MagicMock(return_value=True)
    result = manager.pull_model("llama3.2:3b", stream=True)
    assert result is True

def test_delete_model(manager):
    manager._backend.delete_model = MagicMock(return_value=True)
    result = manager.delete_model("llama3.2:3b")
    assert result is True

# --------------------------------------------------------------------
# Check API / Service / System
# --------------------------------------------------------------------
def test_check_api_status(manager):
    manager.api.check_connection = MagicMock(return_value=True)
    assert "reachable" in manager.check_api_status()

def test_health_check(manager):
    manager.service.get_health_status = MagicMock(return_value={"os": "macOS"})
    info = manager.health_check()
    assert info["os"] == "macOS"

def test_version_and_os(manager):
    manager.service.get_version = MagicMock(return_value="1.0.1")
    manager.service.get_os_name = MagicMock(return_value="macOS")
    assert "1.0.1" in manager.get_version()
    assert "macOS" in manager.get_operating_system()

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def test_validate_model_name(manager):
    manager.helpers.validate_model_name = MagicMock(return_value=True)
    assert manager.validate_model_name("llama3")

def test_estimate_tokens(manager):
    manager.helpers.estimate_tokens = MagicMock(return_value=42)
    assert manager.estimate_tokens("prompt") == 42

# --------------------------------------------------------------------
# Conversations
# --------------------------------------------------------------------
@patch("modules.plugin_manager.ConversationManager")
def test_start_conversation(MockConv, manager):
    mock_instance = MagicMock()
    MockConv.return_value = mock_instance
    conv = manager.start_conversation("llama")
    assert conv is mock_instance

@patch("modules.plugin_manager.ConversationManager")
def test_chat(MockConv, manager):
    mock_conv = MagicMock()
    mock_conv.conversation.model = "llama"
    manager.generate = MagicMock(return_value="Hi user")

    resp = manager.chat(mock_conv, "Hello")
    manager.generate.assert_called_once()
    assert resp == "Hi user"

# --------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------
def test_cache_stats(manager):
    fake_stats = {"total_entries": 1}
    manager.cache = MagicMock()
    manager.cache.get_stats.return_value = fake_stats
    result = manager.cache_stats()
    assert result == fake_stats

def test_clear_cache(manager):
    manager.cache = MagicMock()
    manager.cache.clear.return_value = 99
    manager.clear_cache()
    manager.cache.clear.assert_called_once()

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
def test_config_access(manager):
    manager.config.get_host = MagicMock(return_value="localhost")
    manager.config.get_port = MagicMock(return_value=11434)
    assert manager.get_api_host() == "localhost"
    assert isinstance(manager.get_api_port(), int)
