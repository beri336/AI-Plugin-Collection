# tests/test_service_manager.py

'''
Unit tests for the Service Manager
  This test suite validates service lifecycle and status management.

- Tests operating system detection (macOS, Linux, Windows)
- Validates Ollama installation check and path detection
- Checks process detection via psutil
- Tests API accessibility via socket connection
- Validates version parsing from CLI output
- Checks health status aggregation
- Tests service start and stop operations
- Mocks all system calls for isolated tests
'''

from modules.service_manager import Service
from unittest.mock import patch, MagicMock
import pytest


# --------------------------------------------------------------------
# Fixture
# --------------------------------------------------------------------
@pytest.fixture
def service():
    return Service()

# --------------------------------------------------------------------
# OS Name detection
# --------------------------------------------------------------------
@patch("modules.service_manager.platform.system", return_value="Darwin")
def test_get_os_name_macos(mock_sys, service):
    assert service.get_os_name() == "macOS"
    mock_sys.assert_called_once()

@patch("modules.service_manager.platform.system", return_value="Linux")
def test_get_os_name_linux(mock_sys, service):
    assert service.get_os_name() == "Linux"

# --------------------------------------------------------------------
# Installation detection
# --------------------------------------------------------------------
@patch("modules.service_manager.shutil.which", return_value="/usr/bin/ollama")
def test_is_installed_true(mock_which, service):
    assert service.is_installed() is True
    assert service.get_installation_path() == "/usr/bin/ollama"

@patch("modules.service_manager.shutil.which", return_value=None)
def test_is_installed_false(mock_which, service):
    assert service.is_installed() is False
    assert service.get_installation_path() is None

# --------------------------------------------------------------------
# Process detection is_running()
# --------------------------------------------------------------------
@patch("modules.service_manager.psutil.process_iter")
def test_is_running_true(mock_iter, service):
    mock_iter.return_value = [MagicMock(info={"name": "Ollama"})]
    assert service.is_running() is True

@patch("modules.service_manager.psutil.process_iter")
def test_is_running_false(mock_iter, service):
    mock_iter.return_value = [MagicMock(info={"name": "python"})]
    assert service.is_running() is False

# --------------------------------------------------------------------
# API reachability via socket
# --------------------------------------------------------------------
@patch("modules.service_manager.socket.socket")
def test_is_api_reachable_true(mock_socket, service):
    mock_sock_instance = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock_instance
    assert service.is_api_reachable() is True
    mock_sock_instance.connect.assert_called_once()

@patch("modules.service_manager.socket.socket", side_effect=OSError)
def test_is_api_reachable_fail(mock_socket, service):
    result = service.is_api_reachable()
    assert result is False

# --------------------------------------------------------------------
# Version parsing
# --------------------------------------------------------------------
@patch("modules.service_manager.subprocess.run")
def test_get_version_parses_output(mock_run, service):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="ollama version 1.2.3\n"
    )
    version = service.get_version()
    assert version == "1.2.3"

@patch("modules.service_manager.subprocess.run")
def test_get_version_no_match(mock_run, service):
    mock_run.return_value = MagicMock(returncode=0, stdout="no version info")
    assert service.get_version() is None

# --------------------------------------------------------------------
# Health check aggregation
# --------------------------------------------------------------------
def test_get_health_status_compiles(monkeypatch, service):
    monkeypatch.setattr(service, "get_os_name", lambda: "Linux")
    monkeypatch.setattr(service, "is_installed", lambda: True)
    monkeypatch.setattr(service, "get_installation_path", lambda: "/bin/ollama")
    monkeypatch.setattr(service, "is_running", lambda: True)
    monkeypatch.setattr(service, "is_api_reachable", lambda: True)
    monkeypatch.setattr(service, "is_operatable", lambda: True)
    monkeypatch.setattr(service, "get_version", lambda: "1.0.0")

    info = service.get_health_status()
    assert info["os"] == "Linux"
    assert info["installed"]
    assert "version" in info

# --------------------------------------------------------------------
# Start / Stop service (mocked subprocess + psutil)
# --------------------------------------------------------------------
@patch("modules.service_manager.subprocess.Popen")
@patch.object(Service, "is_api_reachable", return_value=True)
@patch.object(Service, "is_running", return_value=False)
def test_start_service_success(mock_run, mock_reach, mock_popen, service):
    res = service.start(timeout=1)
    assert res is True

@patch.object(Service, "is_running", return_value=False)
@patch("modules.service_manager.subprocess.Popen", side_effect=OSError)
def test_start_service_fail(mock_popen, mock_running, service):
    assert service.start(timeout=1) is False

@patch("modules.service_manager.psutil.process_iter")
def test_stop_service_terminates(mock_iter, service):
    mock_proc = MagicMock()
    mock_proc.info = {"name": "ollama", "pid": 999}
    mock_iter.return_value = [mock_proc]

    result = service.stop()
    mock_proc.terminate.assert_called_once()
    assert result is True

@patch("modules.service_manager.psutil.process_iter", return_value=[])
def test_stop_service_none_found(mock_iter, service):
    assert service.stop() is False
