# tests/test_helpers.py

'''
Unit tests for helper functions
  This test suite validates installation and utility functions.

- Tests detection of package managers (Homebrew, Winget, Chocolatey)
- Validates installation methods for different platforms
- Checks fallback strategies for installation errors
- Tests direct download installer for Windows
- Validates model name validation
- Checks token estimation for texts
- Tests model search in lists
- Mocks subprocess calls and file system operations
'''

from unittest.mock import patch, MagicMock
from core.helpers import Helper
import pytest


# --------------------------------------------------------------------
# Fixture
# --------------------------------------------------------------------
@pytest.fixture
def helper():
    return Helper()

# --------------------------------------------------------------------
# Package Managers detection
# --------------------------------------------------------------------
@patch("core.helpers.shutil.which", return_value="/usr/local/bin/brew")
def test_homebrew_detected(mock_which, helper):
    assert helper._is_homebrew_installed() is True
    mock_which.assert_called_once_with("brew")

@patch("core.helpers.shutil.which", return_value=None)
def test_homebrew_not_detected(mock_which, helper):
    assert helper._is_homebrew_installed() is False

# --------------------------------------------------------------------
# Brew / Curl / Choco / Winget installs
# --------------------------------------------------------------------
@patch("core.helpers.subprocess.run")
def test_try_brew_install_success(mock_run, helper):
    mock_run.return_value = MagicMock(returncode=0)
    assert helper._try_brew_install() is True

@patch("core.helpers.subprocess.run")
def test_try_brew_install_fail(mock_run, helper):
    mock_run.return_value = MagicMock(returncode=1)
    assert helper._try_brew_install() is False

@patch("core.helpers.subprocess.run")
def test_try_curl_install_success(mock_run, helper):
    # simulate curl + sh installs returning 0 twice
    mock_run.side_effect = [MagicMock(returncode=0, stdout="sh script"), MagicMock(returncode=0)]
    assert helper._try_curl_install() is True

@patch("core.helpers.subprocess.run")
def test_try_curl_install_fail_download(mock_run, helper):
    mock_run.return_value = MagicMock(returncode=1)
    assert helper._try_curl_install() is False

# --------------------------------------------------------------------
# Winget / Chocolatey installs
# --------------------------------------------------------------------
@patch("core.helpers.subprocess.run")
def test_try_winget_install_success(mock_run, helper):
    mock_run.return_value = MagicMock(returncode=0)
    assert helper._try_winget_install() is True

@patch("core.helpers.subprocess.run", side_effect=FileNotFoundError)
def test_try_winget_install_failure(mock_run, helper):
    assert helper._try_winget_install() is False

@patch("core.helpers.subprocess.run")
def test_try_choco_install(mock_run, helper):
    mock_run.return_value = MagicMock(returncode=0)
    assert helper._try_choco_install() is True

# --------------------------------------------------------------------
# Direct Windows download installer
# --------------------------------------------------------------------
@patch("core.helpers.os.remove")
@patch("core.helpers.os.path.exists", return_value=True)
@patch("core.helpers.subprocess.run")
@patch("core.helpers.urllib.request.urlretrieve")
def test_try_direct_download_success(mock_dl, mock_run, mock_exists, mock_remove, helper):
    mock_run.return_value = MagicMock(returncode=0)
    assert helper._try_direct_download_install_windows_only() is True
    mock_dl.assert_called_once()

@patch("core.helpers.urllib.request.urlretrieve", side_effect=Exception)
def test_try_direct_download_fail(mock_dl, helper):
    assert helper._try_direct_download_install_windows_only() is False

# --------------------------------------------------------------------
# Show manual install instructions (prints nicely)
# --------------------------------------------------------------------
@patch("core.helpers.platform.system", return_value="Linux")
def test_manual_install_instructions(mock_sys, helper, capsys):
    helper._show_manual_install_instructions()
    captured = capsys.readouterr().out
    assert "AUTOMATIC INSTALLATION FAILED" in captured
    assert "Linux" in captured

# --------------------------------------------------------------------
# Platform-specific install methods
# --------------------------------------------------------------------
@patch.object(Helper, "_is_homebrew_installed", return_value=True)
@patch.object(Helper, "_try_brew_install", return_value=True)
def test_install_macos_success(mock_brew, mock_homebrew, helper):
    assert helper._install_macos() is True

@patch.object(Helper, "_is_homebrew_installed", return_value=False)
@patch.object(Helper, "_try_brew_install", return_value=False)
@patch.object(Helper, "_try_curl_install", return_value=False)
def test_install_macos_fallback(mock_curl, mock_brew, mock_homebrew, helper):
    assert helper._install_macos() is False

@patch.object(Helper, "_is_winget_installed", return_value=True)
@patch.object(Helper, "_try_winget_install", return_value=True)
def test_install_windows_success(mock_winget, mock_detect, helper):
    assert helper._install_windows() is True

# --------------------------------------------------------------------
# Validation / Tokens / Search
# --------------------------------------------------------------------
def test_validate_model_name(helper):
    assert helper.validate_model_name("llama3") is True
    assert helper.validate_model_name("") is False
    assert helper.validate_model_name("inva|lid") is False

def test_estimate_tokens(helper):
    assert helper.estimate_tokens("eightchars") > 0
    assert helper.estimate_tokens("") == 0

def test_search_models(helper):
    models = ["llama", "gemma", "deepseek"]
    matches = helper.search_models("llama", models)
    assert "llama" in matches
    assert helper.search_models("", models) == []
    assert helper.search_models("none", []) == []
