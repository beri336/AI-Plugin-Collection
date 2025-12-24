# src/ollama_helper.py

import urllib.request
import subprocess
import tempfile
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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print()
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
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print()
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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print()
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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print()
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
            
        except Exception as e:
            print()
        finally:
            # cleanup installer file
            if installer_path and os.path.exists(installer_path):
                try:
                    os.remove(installer_path)
                except OSError:
                    pass
        return False
