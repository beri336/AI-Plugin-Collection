# src/ollama_service.py

from typing import Optional

import subprocess
import platform
import shutil
import socket
import time
import re

import psutil


class OllamaService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_os_name() -> str:
        system = platform.system()
        if system == "Darwin":
            return "MacOS"
        return system

    def is_installed(self) -> bool:
        path = shutil.which("ollama")
        if path:
            return True
        return False

    def get_installation_path(self) -> Optional[str]:
        return shutil.which("ollama")

    def is_process_running(self) -> bool:
        for proc in psutil.process_iter(['name']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def is_api_reachable(self) -> bool:
        host: str = "127.0.0.1"
        port: int = 11434
        timeout: float = 1.0
    
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((host, port))
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            return False

    def _is_running(self) -> bool:
        return self.is_process_running() and self.is_api_reachable()

    def get_status(self) -> dict:
        return {
            "os": self.get_os_name(),
            "installed": self.is_installed(),
            "installation_path": self.get_installation_path(),
            "process_running": self.is_process_running(),
            "api_reachable": self.is_api_reachable(),
            "fully_operational": self._is_running(),
            "version": self.get_version()
        }

    def get_version(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False
            )
            
            if result.returncode == 0:
                version_string = result.stdout.strip()
                # Extract version number
                match = re.search(r'(\d+\.\d+\.\d+)', version_string)
                return match.group(1) if match else None
            
            return None
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return None

    def start(self, timeout: int = 10) -> bool:
        if self._is_running():
            return True
        
        try:
            if platform.system() == "Windows":
                # Option 1: With CREATE_NO_WINDOW flag (Windows-specific)
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Unix/Linux/macOS
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Wait until service is available
            for _ in range(timeout):
                if self.is_api_reachable():
                    return True
                time.sleep(1)
            
            return False
            
        except (OSError, subprocess.SubprocessError) as e:
            return False

    def stop(self) -> bool:
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if 'ollama' in proc.info['name'].lower():
                    proc.terminate()
                    proc.wait(timeout=5)
                    return True
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                continue
        return False
