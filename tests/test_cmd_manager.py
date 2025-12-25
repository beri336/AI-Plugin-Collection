# tests/test_cmd_manager.py

'''
Unit tests for CMDManager
  This test suite validates CLI-based Ollama operations via subprocess.

- Tests model list retrieval and parsing of CLI output
- Validates model info extraction from `ollama show`
- Checks foreground and background pull modes
- Tests progress parsing for download tracking
- Validates text generation via CLI
- Mocks subprocess calls for isolated tests
- Checks platform-specific behaviors
'''

from modules.cmd_manager import CMDManager, PullMode
from unittest.mock import patch, MagicMock
import pytest


# --------------------------------------------------------------------
# Test: refresh_list_of_model_names()
# --------------------------------------------------------------------
@patch("modules.cmd_manager.subprocess.run")
def test_refresh_list_of_model_names(mock_run):
    # simulate the terminal output format of `ollama list`
    fake_output = "NAME   ID   SIZE   MODIFIED\nllama3.2:3b 123abc 2GB yesterday"
    mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)

    manager = CMDManager()
    manager.refresh_list_of_model_names()

    mock_run.assert_called_once_with(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=manager.config.timeout_short,
        check=True,
    )
    # the name should now have been adopted
    assert "llama3.2:3b" in manager.list_of_models

# --------------------------------------------------------------------
# Test: get_detailed_list_models()
# --------------------------------------------------------------------
@patch("modules.cmd_manager.subprocess.run")
def test_get_detailed_list_models(mock_run):
    fake_output = (
        "NAME   ID   SIZE   MODIFIED\n"
        "llama3.2:3b 123abc 4GB 2025-12-01\n"
        "gemma3:4b 456def 2.1GB 2025-10-10"
    )
    mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)

    manager = CMDManager()
    result = manager.get_detailed_list_models()

    mock_run.assert_called_once()
    assert isinstance(result, list)
    assert result[0]["name"] == "llama3.2:3b"
    assert "size" in result[0]
    assert "modified" in result[0]

# --------------------------------------------------------------------
# Test: get_model_info()
# --------------------------------------------------------------------
@patch("modules.cmd_manager.subprocess.run")
def test_get_model_info_single_call(mock_run):
    fake_output = (
        "model info\n"
        "architecture Gemma\n"
        "parameters 4.3B\n"
    )
    mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)

    manager = CMDManager()
    manager.list_of_models = ["llama3.2:3b"]  # Verhindert zusätzlichen "list"-Aufruf

    info = manager.get_model_info("llama3.2:3b")
    mock_run.assert_called_once_with(
        ["ollama", "show", "llama3.2:3b"],
        capture_output=True,
        text=True,
        timeout=manager.config.timeout_default,
        check=True,
    )
    assert "model_name" in info

# --------------------------------------------------------------------
# Test: pull_model() (Foreground and Background)
# --------------------------------------------------------------------
@patch("modules.cmd_manager.subprocess.run")
@patch("modules.cmd_manager.subprocess.Popen")
def test_pull_model_foreground(mock_popen, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    manager = CMDManager()

    # foreground
    result = manager.pull_model("llama3.2:3b", mode=PullMode.FOREGROUND)
    assert result is True

@patch("modules.cmd_manager.subprocess.Popen")
def test_pull_model_background(mock_popen):
    mock_popen.return_value = MagicMock()
    manager = CMDManager()

    # simulate macOS / Linux (e.g. Darwin)
    with patch("modules.cmd_manager.platform.system", return_value="Darwin"):
        result = manager._pull_model_background("llama3.2:3b")

    mock_popen.assert_called_once()
    assert result is True

# --------------------------------------------------------------------
# Test: _parse_pull_progress()
# --------------------------------------------------------------------
def test_parse_pull_progress():
    manager = CMDManager()

    # percentage
    line = "Downloading 77% 2.4GB/3.0GB"
    progress = manager._parse_pull_progress(line)
    assert progress["status"] == "downloading"
    assert progress["percent"] == 77.0
    assert "size" in progress

    # manifest
    assert manager._parse_pull_progress("Pulling manifest")["status"] == "pulling_manifest"
    # verifying
    assert manager._parse_pull_progress("Verifying layers")["status"] == "verifying"
    # success
    assert manager._parse_pull_progress("Success!")["status"] == "success"
    # unrecognized
    assert manager._parse_pull_progress("Random text") is None

# --------------------------------------------------------------------
# Test: generate()
# --------------------------------------------------------------------
@patch("modules.cmd_manager.subprocess.run")
def test_generate(mock_run):
    mock_run.return_value = MagicMock(stdout="Hello world", returncode=0)
    manager = CMDManager()
    text = manager.generate("llama3.2:3b", "Say hello.")
    mock_run.assert_called_once_with(
        ["ollama", "run", "llama3.2:3b", "Say hello."],
        capture_output=True,
        text=True,
        timeout=manager.config.timeout_default,
        check=True,
    )
    assert text == "Hello world"
