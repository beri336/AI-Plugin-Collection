# src/ollama_helper.py

from typing import List

import urllib.request
import subprocess
import tempfile
import platform
import shutil
import os


class OllamaHelper:
    def __init__(self) -> None:
        self.timeout: int = 300
        self.install_script_url = "https://ollama.com/install.sh"
        self.curl_timeout = 10
        self.install_timeout = 300
        self.installer_url = "https://ollama.com/download/OllamaSetup.exe"

# Package Manager
    @staticmethod
    def _is_homebrew_installed() -> bool:
        """ Checks if Homebrew is installed. """
        return shutil.which("brew") is not None

    @staticmethod
    def _is_winget_installed() -> bool:
        return shutil.which("winget") is not None

    @staticmethod
    def _is_chocolatey_installed() -> bool:
        return shutil.which("choco") is not None

# Installation Method Helpers
    def _try_brew_install(self) -> bool:
        try:
            result = subprocess.run(
                ["brew", "install", "ollama"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            pass
        return False

    def _try_curl_install(self) -> bool:
        try:
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
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            pass
        return False

    def _try_winget_install(self) -> bool:
        """ Attempts installation via winget """
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

    def _try_choco_install(self) -> bool:
        try:
            result = subprocess.run(
                ["choco", "install", "ollama", "-y"],
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

    def _try_direct_download_install_windows_only(self) -> bool:
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
    def _install_macos(self) -> bool:
        if self._is_homebrew_installed() and self._try_brew_install():
            return True
        
        if self._try_curl_install():
            return True
        
        self._show_manual_install_instructions()
        return False

    def _install_linux(self) -> bool:
        if self._is_homebrew_installed() and self._try_brew_install():
            return True
        
        if self._try_curl_install():
            return True
        
        self._show_manual_install_instructions()
        return False

    def _install_windows(self) -> bool:
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
        if not text or not isinstance(text, str):
            return 0
        
        AVG_CHARS_PER_TOKEN = 4
        return max(1, len(text.strip()) // AVG_CHARS_PER_TOKEN)

    def search_models(self, query: str, models: List[str]) -> List[str]:
        if not query:
            return []
        
        if not models:
            return []
        
        try:
            query_lower = query.lower()
            matching = [m for m in models if query_lower in m.lower()]
            return matching
        except (AttributeError, TypeError) as e:
            return []
