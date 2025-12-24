# src/ollama_service.py

from typing import Optional, Dict, Any
from pathlib import Path

import subprocess
import platform
import logging
import shutil
import socket
import time
import re

import psutil


class OllamaService:
    logger: logging.Logger | None = None

    def __init__(self) -> None:
        if OllamaService.logger is None:
            OllamaService.setup_logger()

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

    def get_status(self) -> Dict[str, Any]:
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
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
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
            
        except (OSError, subprocess.SubprocessError, FileNotFoundError) as e:
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

# Logger
    @classmethod
    def setup_logger(
        cls,
        level: int = logging.INFO,
        log_file: str | None = None,
        console: bool = True
    ) -> logging.Logger:
        cls.logger = logging.getLogger(__name__)
        cls.logger.setLevel(level)
        
        # Remove existing handlers
        cls.logger.handlers.clear()
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            cls.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            cls.logger.addHandler(file_handler)
        
        return cls.logger

    @classmethod
    def get_logger(cls) -> Optional[logging.Logger]:
        if cls.logger is None:
            cls.setup_logger()
        return cls.logger
