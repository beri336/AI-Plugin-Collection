# src/modules/service_manager.py

'''
Ollama Service Manager for process and API control
  This module manages the Ollama service lifecycle and monitors its status.

- Detects Ollama installation and returns installation path
- Checks whether Ollama process is running via psutil
- Tests API availability via socket connection
- Starts Ollama service platform-specific (Windows/Unix)
- Safely stops running Ollama processes
- Extracts version number from CLI output
- Provides comprehensive health status with all metrics
- Cached service status for performance optimization
'''

from core.decorators import (
    retry_on_failure,
    handle_exceptions,
    log_execution,
)
from config.settings import Config

from typing import Optional, Dict, Any

import subprocess
import platform
import logging
import shutil
import socket
import time
import re

import psutil


class Service:
    """Manager for Ollama service lifecycle and status monitoring.
    
    Provides comprehensive service management including installation detection,
    process monitoring, API connectivity checks, and lifecycle control.
    
    Features:
        - Cross-platform service detection and control
        - Process monitoring via psutil
        - API reachability testing via socket
        - Platform-specific service startup (Windows/Unix)
        - Safe process termination
        - Version extraction from CLI
        - Health status aggregation
        - Status caching for performance
        
    Attributes:
        config: Configuration instance with connection settings
        _is_installed: Cached installation status
        _is_running: Cached process running status
        _is_api_reachable: Cached API reachability status
    """
    
    def __init__(self) -> None:
        """ Initialize service manager with configuration and empty cache """
        self.config = Config()
        
        self._is_installed: bool=False
        self._is_running: bool=False
        self._is_api_reachable: bool=False

    @log_execution()
    def refresh_status(self) -> None:
        """Refresh all cached service status flags.
        
        Updates installation, running, and API reachability status by
        calling their respective check methods.
        
        Side Effects:
            Updates _is_installed, _is_running, _is_api_reachable
        """
        self._is_installed = self.is_installed()
        self._is_running = self.is_running()
        self._is_api_reachable = self.is_api_reachable()

    @staticmethod
    def get_os_name() -> str:
        """Get human-readable operating system name.
        
        Returns:
            OS name string: 'macOS', 'Linux', or 'Windows'
        """
        system = platform.system()
        if system == 'Darwin':
            return 'macOS'
        return system

    def is_installed(self) -> bool:
        """Check if Ollama is installed and available in PATH.
        
        Returns:
            True if 'ollama' command is found, False otherwise
        """
        return shutil.which('ollama') is not None

    def get_installation_path(self) -> Optional[str]:
        """Get full path to Ollama executable.
        
        Returns:
            Full path string if installed, None if not found
        """
        path = shutil.which('ollama')
        return path

    @handle_exceptions(default_return=False, log_error=True)
    def is_running(self) -> bool:
        """Check if Ollama process is currently running.
        
        Searches for processes with 'ollama' in their name using psutil.
        Case-insensitive search.
        
        Returns:
            True if at least one Ollama process found, False otherwise
        """
        for process in psutil.process_iter(['name']):
            name = process.info.get('name', '').lower()
            if 'ollama' in name:
                return True
        return False

    @retry_on_failure(max_attempts=3, delay=0.5)
    @handle_exceptions(default_return=False, log_error=True)
    def is_api_reachable(self) -> bool:
        """Check if Ollama API endpoint is reachable via socket.
        
        Attempts TCP connection to configured host/port with retry logic.
        
        Returns:
            True if connection succeeded, False otherwise
        
        Note:
            Uses timeout from config and retries up to 3 times with 0.5s delay.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.config.timeout_default)
            sock.connect((self.config.host, self.config.port))
            return True

    def is_operatable(self) -> bool:
        """Check if Ollama is fully operational (running AND reachable).
        
        Combines process check and API reachability test.
        
        Returns:
            True if both running and API reachable, False otherwise
        """
        return self.is_running() and self.is_api_reachable()
    
    @handle_exceptions(default_return=None, log_error=True)
    def get_version(self) -> Optional[str]:
        """Extract Ollama version number from CLI output.
        
        Executes 'ollama --version' and parses semantic version number
        using regex pattern.
        
        Returns:
            Version string (e.g., '0.1.17') or None if not found/failed
        """
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            version_string = result.stdout.strip()
            match = re.search(r'(\d+\.\d+\.\d+)', version_string)
            return match.group(1) if match else None
        return None

    @log_execution()
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status with all service metrics.
        
        Aggregates all status checks into single dictionary.
        
        Returns:
            Dictionary with keys:
                - os: Operating system name
                - installed: Installation status (bool)
                - installation_path: Path to executable (str or None)
                - process_running: Process running status (bool)
                - api_reachable: API connectivity status (bool)
                - fully_operational: Combined operational status (bool)
                - version: Version string (str or None)
        """
        return {
            "os": self.get_os_name(),
            "installed": self.is_installed(),
            "installation_path": self.get_installation_path(),
            "process_running": self.is_running(),
            "api_reachable": self.is_api_reachable(),
            "fully_operational": self.is_operatable(),
            "version": self.get_version()
        }

    @log_execution()
    @handle_exceptions(default_return=False, log_error=True)
    def start(self, timeout: int = 10) -> bool:
        """Start Ollama service in background.
        
        Launches 'ollama serve' as detached process and waits for API
        to become reachable. Platform-specific handling for Windows vs Unix.
        
        Args:
            timeout: Maximum seconds to wait for API (default: 10)
            
        Returns:
            True if service started and API became reachable, False otherwise
            
        Side Effects:
            - Spawns detached background process
            - Waits up to timeout seconds for API
        
        Note:
            On Windows, uses DETACHED_PROCESS flag to prevent console window.
            Returns True immediately if service already running.
        """
        if self.is_running():
            return True
        try:
            if self.get_os_name() == 'Windows':
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            for _ in range(timeout):
                if self.is_api_reachable():
                    return True
                time.sleep(1)
            return False
        except Exception:
            return False

    @log_execution()
    @handle_exceptions(default_return=False, log_error=True)
    def stop(self, stop_all: bool = True) -> bool:
        """Stop running Ollama process(es) gracefully.

        Searches for all Ollama processes and terminates them with optional
        selective stopping. Waits up to 5 seconds per process for clean exit.
        
        Args:
            stop_all: Stop all Ollama processes if True (default), only first if False
        
        Returns:
            True if at least one process was found and terminated, False if no
            Ollama processes were found or all termination attempts failed
        
        Note:
            Handles NoSuchProcess (process disappeared during termination) and
            TimeoutExpired (process didn't exit within 5 seconds) gracefully.
            Continues with remaining processes if one fails.
        """
        stopped = False
        for process in psutil.process_iter(['name', 'pid']):
            try:
                if 'ollama' in process.info['name'].lower():
                    process.terminate()
                    process.wait(timeout=5)
                    stopped = True
                    if not stop_all:
                        break
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                # known issues - process disappeared or didn't exit in time
                # continue with next process
                continue
        return stopped
