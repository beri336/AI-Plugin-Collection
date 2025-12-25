# src/core/helpers.py

'''
Helper functions for Ollama installation and model management
  This module provides cross-platform installation and utility functions.

- Detects available package managers (Homebrew, Winget, Chocolatey)
- Automatically installs Ollama on macOS, Linux, and Windows
- Provides fallback installation methods (curl, direct download)
- Validates model names for validity and file system compatibility
- Estimates token count for text input
- Searches model lists for search terms
- Displays manual installation instructions in case of failure
'''

from .decorators import (
    handle_exceptions
)

from typing import List

import urllib.request
import subprocess
import tempfile
import platform
import shutil
import os


class Helper:
    """Helper utilities for Ollama installation and model management.
    
    Provides cross-platform installation methods with automatic detection
    of available package managers and fallback strategies. Also includes
    utilities for model validation, token estimation, and model search.
    
    Installation Strategy:
        - macOS: Homebrew → curl script → manual instructions
        - Linux: Homebrew → curl script → manual instructions  
        - Windows: Winget → Chocolatey → direct download → manual instructions
    
    Attributes:
        timeout: General subprocess timeout in seconds
        curl_timeout: Timeout for curl downloads in seconds
        install_timeout: Timeout for installation processes in seconds
        install_script_url: URL for Unix installation script
        installer_url: URL for Windows installer executable
    """
    
    def __init__(self) -> None:
        """ Initialize Helper with default timeouts and installation URLs """
        self.timeout: int = 300
        self.curl_timeout = 10
        self.install_timeout = 300
        
        self.install_script_url = "https://ollama.com/install.sh"
        self.installer_url = "https://ollama.com/download/OllamaSetup.exe"

    def install_ollama(self) -> bool:
        """Attempt to install Ollama on the current platform.
        
        Automatically detects the operating system and calls the appropriate
        platform-specific installation method. Shows manual instructions if
        automatic installation fails or OS is unsupported.
        
        Returns:
            True if installation succeeded, False otherwise
        """
        os_name = platform.system()
        
        installers = {
            "Darwin": self._install_macos,
            "Linux": self._install_linux,
            "Windows": self._install_windows
        }
        
        installer = installers.get(os_name)
        if not installer:
            self._show_manual_install_instructions()
            return False
        
        return installer()

# Package Manager
    @staticmethod
    def _is_homebrew_installed() -> bool:
        """Check if Homebrew package manager is installed.
        
        Returns:
            True if 'brew' command is available in PATH, False otherwise
        """
        return shutil.which("brew") is not None

    @staticmethod
    def _is_winget_installed() -> bool:
        """Check if Windows Package Manager (winget) is installed.
        
        Returns:
            True if 'winget' command is available in PATH, False otherwise
        """
        return shutil.which("winget") is not None

    @staticmethod
    def _is_chocolatey_installed() -> bool:
        """Check if Chocolatey package manager is installed.
        
        Returns:
            True if 'choco' command is available in PATH, False otherwise
        """
        return shutil.which("choco") is not None

# Installation Method Helpers
    @handle_exceptions(default_return=False, log_error=True)
    def _try_brew_install(self) -> bool:
        """Attempt to install Ollama using Homebrew.
        
        Executes 'brew install ollama' and waits for completion.
        
        Returns:
            True if installation succeeded (return code 0), False otherwise
            
        Note:
            Requires Homebrew to be installed. Use _is_homebrew_installed()
            to check availability first.
        """
        result = subprocess.run(
            ["brew", "install", "ollama"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False
        )
        if result.returncode == 0:
            return True
        
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _try_curl_install(self) -> bool:
        """Attempt to install Ollama using official curl installation script.
        
        Downloads the installation script from ollama.com and executes it
        via shell. This is the recommended installation method for Linux
        and fallback for macOS.
        
        Returns:
            True if both download and installation succeeded, False otherwise
            
        Note:
            Requires curl and sh to be available. Script is executed with
            shell privileges.
        """
        # download install script
        download_result = subprocess.run(
            ["curl", "-fsSL", self.install_script_url],
            capture_output=True,
            text=True,
            timeout=self.curl_timeout,
            check=False
        )
        
        if download_result.returncode != 0:
            return False
        
        # execute install script
        install_result = subprocess.run(
            ["sh", "-c", download_result.stdout],
            capture_output=True,
            text=True,
            timeout=self.install_timeout,
            check=False
        )
        
        if install_result.returncode == 0:
            return True
        
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _try_winget_install(self) -> bool:
        """Attempt to install Ollama using Windows Package Manager.
        
        Executes 'winget install Ollama.Ollama' to install from Microsoft Store.
        
        Returns:
            True if installation succeeded, False otherwise
            
        Note:
            Requires Windows 10/11 with winget installed.
        """
        try:
            result = subprocess.run(
                ["winget", "install", "Ollama.Ollama"],
                capture_output=True,
                text=True,
                timeout=self.install_timeout,
                check=False
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            pass
        
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _try_choco_install(self) -> bool:
        """Attempt to install Ollama using Chocolatey.
        
        Executes 'choco install ollama -y' with automatic confirmation.
        
        Returns:
            True if installation succeeded, False otherwise
            
        Note:
            Requires Chocolatey to be installed and may require administrator
            privileges.
        """
        result = subprocess.run(
            ["choco", "install", "ollama", "-y"],
            capture_output=True,
            text=True,
            timeout=self.install_timeout,
            check=False
        )
        if result.returncode == 0:
            return True
        
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _try_direct_download_install_windows_only(self) -> bool:
        """Attempt to install Ollama by downloading Windows installer directly.
        
        Downloads OllamaSetup.exe to temp directory and executes silent
        installation (/S flag).
        
        Returns:
            True if download and installation succeeded, False otherwise
            
        Warning:
            This is a fallback method and should only be used when package
            managers are unavailable. Silent installation may require
            administrator privileges.
            
        Note:
            Installer is downloaded to system temp directory and deleted
            after installation attempt, regardless of success or failure.
        """
        installer_path = None
        
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "OllamaSetup.exe")
            
            urllib.request.urlretrieve(self.installer_url, installer_path)
            
            result = subprocess.run(
                [installer_path, "/S"],
                capture_output=True,
                timeout=self.install_timeout,
                check=False
            )
            
            if result.returncode == 0:
                return True
            
        except (urllib.error.URLError, subprocess.SubprocessError, OSError) as e:
            pass
        finally:
            # cleanup installer file
            if installer_path and os.path.exists(installer_path):
                try:
                    os.remove(installer_path)
                except OSError:
                    pass
                
        return False

    def _show_manual_install_instructions(self) -> None:
        """Display platform-specific manual installation instructions.
        
        Prints formatted instructions to stdout with download links and
        alternative installation commands. Called when automatic installation
        fails or is unavailable for the current platform.
        """
        os_name = platform.system()
        
        instructions = {
            "Darwin": """
macOS:
  1. Download from https://ollama.com/download
  2. Or use: brew install ollama
  3. Or run: curl -fsSL https://ollama.com/install.sh | sh
""",
            "Linux": """
Linux:
  Run: curl -fsSL https://ollama.com/install.sh | sh
""",
            "Windows": """
Windows:
  1. Download installer from https://ollama.com/download
  2. Or use: winget install Ollama.Ollama
  3. Or use: choco install ollama
"""
        }
        
        separator = "=" * 60
        print(f"\n{separator}")
        print("AUTOMATIC INSTALLATION FAILED")
        print(separator)
        print("\nPlease install Ollama manually:")
        print("\n📥 Visit: https://ollama.com/download")
        print("\nPlatform-specific instructions:")
        print(instructions.get(os_name, "\nNo instructions available for this OS."))
        print(f"{separator}\n")

# Platform-Specific Installation
    @handle_exceptions(default_return=False, log_error=True)
    def _install_macos(self) -> bool:
        """Install Ollama on macOS using available methods.
        
        Installation order:
            1. Homebrew (if installed)
            2. curl script (official installation method)
            3. Manual instructions (if both fails)
        
        Returns:
            True if installation succeeded, False otherwise
        """
        if self._is_homebrew_installed() and self._try_brew_install():
            return True
        
        if self._try_curl_install():
            return True
        
        self._show_manual_install_instructions()
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _install_linux(self) -> bool:
        """Install Ollama on Linux using available methods.
        
        Installation order:
            1. Homebrew (if installed, e.g., on Linuxbrew systems)
            2. curl script (official installation method)
            3. Manual instructions (if both fails)
        
        Returns:
            True if installation succeeded, False otherwise
        """
        if self._is_homebrew_installed() and self._try_brew_install():
            return True
        
        if self._try_curl_install():
            return True
        
        self._show_manual_install_instructions()
        return False

    @handle_exceptions(default_return=False, log_error=True)
    def _install_windows(self) -> bool:
        """Install Ollama on Windows using available methods.
        
        Installation order:
            1. Windows Package Manager (winget)
            2. Chocolatey
            3. Direct download and silent installation
            4. Manual instructions (if all else fails)
        
        Returns:
            True if installation succeeded, False otherwise
        """
        if self._is_winget_installed() and self._try_winget_install():
            return True
        
        if self._is_chocolatey_installed() and self._try_choco_install():
            return True
        
        if self._try_direct_download_install_windows_only():
            return True
        
        self._show_manual_install_instructions()
        return False

# Utility-Methods
    def validate_model_name(self, model: str) -> bool:
        """Validate model name for filesystem compatibility.
        
        Checks that model name is a non-empty string without invalid
        filesystem characters that could cause issues when caching or
        storing model data.
        
        Args:
            model: Model name to validate (e.g., 'llama3.2:3b')
            
        Returns:
            True if model name is valid, False otherwise
            
        Invalid Characters:
            < > " | ? *
        """
        if not model or not isinstance(model, str):
            return False
        
        if not model.strip():
            return False
        
        # check for invalid filesystem characters
        invalid_chars = {'<', '>', '"', '|', '?', '*'}
        if any(char in model for char in invalid_chars):
            return False
        
        return True

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text input.
        
        Uses simple heuristic of 4 characters per token on average.
        This is a rough approximation suitable for quick estimates
        and not a replacement for proper tokenization.
        
        Args:
            text: Input text to estimate tokens for
            
        Returns:
            Estimated token count (minimum 1 for non-empty text)
        
        Note:
            The 4:1 character-to-token ratio is approximate and varies
            by language and tokenizer. Use actual tokenizer for precise counts.
        """
        if not text or not isinstance(text, str):
            return 0
        
        AVG_CHARS_PER_TOKEN = 4
        return max(1, len(text.strip()) // AVG_CHARS_PER_TOKEN)

    @handle_exceptions(default_return=[], log_error=True)
    def search_models(self, query: str, models: List[str]) -> List[str]:
        """Search model list for matching entries.
        
        Performs case-insensitive substring search through model list.
        Returns all models where the query appears anywhere in the model name.
        
        Args:
            query: Search term (case-insensitive)
            models: List of model names to search through
        
        Returns:
            List of matching model names, empty list if no matches or on error
        """
        if not query:
            return []
        
        if not models:
            return []
        
        query_lower = query.lower()
        matching = [m for m in models if query_lower in m.lower()]
        
        return matching
