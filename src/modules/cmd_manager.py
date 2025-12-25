# src/modules/cmd_manager.py

'''
Ollama CLI Manager for Subprocess-based Model Operations
  This module provides an alternative interface to the Ollama CLI via subprocess.

- Executes Ollama CLI commands as subprocesses
- Lists installed and running models with metadata
- Downloads models in the foreground or background
- Parses CLI output for progress tracking during download
- Deletes, starts, and stops models via CLI
- Generates text with streaming and non-streaming modes
- Supports platform-specific terminal integration (macOS, Linux, Windows)
- Provides fallback option to REST API in case of network issues
'''

from core.decorators import (
    require_running, 
    validate_model_name, 
    handle_exceptions, 
    log_execution
)
from .service_manager import Service
from config.settings import Config

from typing import List, Dict, Any, Optional, Generator
from enum import Enum

import subprocess
import platform
import logging
import re


class PullMode(Enum):
    """Enum for model download modes.
    
    Attributes:
        BACKGROUND: Download model in separate terminal window
        FOREGROUND: Download model in current process (blocking)
    """
    BACKGROUND = "background"
    FOREGROUND = "foreground"


class CMDManager:
    """Manager for Ollama CLI operations via subprocess.
    
    Provides subprocess-based interface to Ollama CLI as alternative to
    REST API. Useful when API is unavailable or for operations that work
    better via CLI (like background downloads in terminal windows).
    
    Features:
        - Direct CLI command execution via subprocess
        - Progress parsing from CLI output
        - Platform-specific terminal integration
        - Background model downloads in separate windows
        - Streaming text generation
        
    Attributes:
        config: Configuration instance with timeouts
        service: Service manager for checking Ollama availability
        list_of_models: Cached list of installed model names
        list_of_running_models: Cached list of currently running models
        
    Note:
        Requires 'ollama' CLI to be installed and available in PATH.
    """
    
    def __init__(self) -> None:
        """ Initialize CMD manager with configuration and empty caches """
        self.config = Config()
        self.service = Service()
        
        self.list_of_models: List[str] = []
        self.list_of_running_models: List[Dict[str, str]] = []

# Model-Management
    def get_list_model_names(self) -> List[str]:
        """Get list of installed model names.
        
        Returns cached list. Use refresh_list_of_model_names() to update.
        
        Returns:
            List of model name strings
        """
        return self.list_of_models

    @require_running
    @handle_exceptions(default_return=None)
    def refresh_list_of_model_names(self) -> None:
        """Refresh cached list of installed models via 'ollama list'.
        
        Executes 'ollama list' command and parses output to extract model 
        names. Updates self.list_of_models cache with current model names.
        """
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_short,
            check=True
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # skip header
        models = [line.split()[0] for line in lines if line.strip()]
        self.list_of_models = models

    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def get_detailed_list_models(self) -> List[Dict[str, str]]:
        """Get detailed information about all installed models.
        
        Executes 'ollama list' and parses output into structured format.
        
        Returns:
            List of model dictionaries with keys:
                - name: Model name
                - id: Model digest/ID
                - size: Human-readable size
                - modified: Last modification time
        """
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_short,
            check=True
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # skip header
        models = []
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    models.append({
                        'name': parts[0],
                        'id': parts[1],
                        'size': ' '.join(parts[2:4]),
                        'modified': ' '.join(parts[4:])
                    })
        
        return models

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=None, log_error=True)
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model.
        
        Executes 'ollama show <model>' and parses structured output
        into nested dictionary format.
        
        Args:
            model: Model name to query
            
        Returns:
            Dictionary with model information organized by sections.
            Returns None on error.
        """
        if not self.list_of_models:
            self.get_list_model_names()
        
        result = subprocess.run(
            ["ollama", "show", model],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_default,
            check=True
        )
        
        info: Dict[str, Any] = {'model_name': model}
        output = result.stdout.strip().splitlines()
        
        current_section: Optional[str] = None
        
        for line in output:
            stripped = line.strip()
            
            if line and not line.startswith(' ') and stripped:
                current_section = stripped.lower().replace(' ', '_')
                info[current_section] = {}
                continue
            
            if stripped and current_section and isinstance(info[current_section], dict):
                if ':' in stripped:
                    # key-value pair
                    parts = stripped.split(None, 1)  # split on first Wwitespace
                    if len(parts) == 2:
                        key = parts[0].lower().replace(' ', '_')
                        value = parts[1].strip()
                        info[current_section][key] = value
                else:
                    section_dict = info[current_section]
                    if 'items' not in section_dict:
                        section_dict['items'] = []
                    if isinstance(section_dict['items'], list):
                        section_dict['items'].append(stripped)
        
        return info

    def model_exists(self, model: str) -> bool:
        """Check if a model is installed.
        
        Uses cached list. Call refresh_list_of_model_names() first
        for most current data.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model is in cached list, False otherwise
        """
        return model in self.get_list_model_names()

    @require_running
    @validate_model_name
    @log_execution()
    @handle_exceptions(default_return=False, log_error=True)
    def pull_model(self, model: str, mode: PullMode = PullMode.FOREGROUND) -> bool:
        """Download a model via CLI.
        
        Downloads model either in current process (foreground) or in
        separate terminal window (background).
        
        Args:
            model: Model name to download
            mode: Download mode (FOREGROUND or BACKGROUND)
            
        Returns:
            True if download initiated successfully, False otherwise
        """
        if mode == PullMode.BACKGROUND:
            return self._pull_model_background(model)
        else:
            return self._pull_model_foreground(model)

    @handle_exceptions(default_return=False, log_error=True)
    def _pull_model_foreground(self, model: str) -> bool:
        """Download model in current process (blocking).
        
        Args:
            model: Model name to download
            
        Returns:
            True if download succeeded (return code 0), False otherwise
        """
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_download
        )
        return result.returncode == 0

    @handle_exceptions(default_return=False, log_error=True)
    def _pull_model_background(self, model: str) -> bool:
        """Download model in separate terminal window (non-blocking).
        
        Opens platform-specific terminal emulator and runs download there.
        
        Args:
            model: Model name to download
            
        Returns:
            True if terminal was opened successfully, False otherwise
            
        Platform Support:
            - macOS: Opens Terminal.app via AppleScript
            - Windows: Opens cmd.exe
            - Linux: Opens gnome-terminal
            
        Note:
            Success only means terminal was opened. Actual download
            success is not tracked when using background mode.
        """
        system = platform.system().lower()
        command = f"ollama pull {model}"
        
        commands = {
            "darwin": ["osascript", "-e", f'tell app "Terminal" to do script "{command}"'],
            "windows": ["cmd", "/k", "ollama", "pull", model],
            "linux": ["gnome-terminal", "--", "bash", "-c", command]
        }
        
        cmd = commands.get(system)
        if not cmd:
            return False
        
        subprocess.Popen(cmd, shell=False)
        return True

    @require_running
    @validate_model_name
    @log_execution()
    def pull_model_with_progress(self, model: str) -> Generator[Dict[str, Any], None, None]:
        """Download a model with real-time progress updates.
        
        Executes 'ollama pull' and parses output to yield progress updates.
        
        Args:
            model: Model name to download
            
        Yields:
            Progress dictionaries with keys:
                - status: Current status ('pulling_manifest', 'downloading', 
                         'verifying', 'completed', 'failed')
                - message: Raw CLI output line
                - percent: Download progress percentage (0-100)
                - size: Downloaded size (if available)
                - error: Error message (on failure)
        """
        try:
            process = subprocess.Popen(
                ["ollama", "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                
                # parse Ollama output
                progress_info = self._parse_pull_progress(line)
                if progress_info:
                    yield progress_info
            
            process.wait()
            
            if process.returncode == 0:
                yield {
                    'status': 'completed',
                    'total': 100,
                    'completed': 100,
                    'percent': 100.0
                }
            else:
                yield {
                    'status': 'failed',
                    'error': process.stderr.read()
                }
                
        except Exception as e:
            # yield error state instead of just logging and returning
            yield {
                'status': 'error',
                'error': str(e)
            }

    def _parse_pull_progress(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse CLI output line to extract download progress.
        
        Uses regex to extract percentage, size, and status from
        'ollama pull' output.
        
        Args:
            line: Single line of CLI output
            
        Returns:
            Progress dictionary or None if line doesn't contain progress info
            
        Recognized Patterns:
            - "pulling manifest" → status='pulling_manifest', percent=0
            - "verifying" → status='verifying', percent=95
            - "XX%" → status='downloading', percent=XX
            - "success" → status='success', percent=100
        """
        percent_match = re.search(r'(\d+)%', line)
        
        if 'pulling manifest' in line.lower():
            return {
                'status': 'pulling_manifest',
                'message': line,
                'percent': 0.0
            }
        elif 'verifying' in line.lower():
            return {
                'status': 'verifying',
                'message': line,
                'percent': 95.0
            }
        elif percent_match:
            percent = float(percent_match.group(1))
            
            # extract size if present
            size_match = re.search(r'([\d.]+\s*[KMGT]?B)', line)
            size = size_match.group(1) if size_match else None
            
            return {
                'status': 'downloading',
                'message': line,
                'percent': percent,
                'size': size
            }
        elif 'success' in line.lower():
            return {
                'status': 'success',
                'message': line,
                'percent': 100.0
            }
        
        return None

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False, log_error=True)
    def delete_model(self, model: str, force: bool = False) -> bool:
        """Delete an installed model via 'ollama rm'.
        
        Args:
            model: Model name to delete
            force: Skip existence check if True (default: False)
            
        Returns:
            True if deletion succeeded, False if model not found or error
            
        Side Effects:
            Removes model from self.list_of_models cache
        """
        if not force:  # check if model exists
            if not self.list_of_models:
                self.get_list_model_names()
            
            if model not in self.list_of_models:
                return False
    
        result = subprocess.run(
            ["ollama", "rm", model],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_default,
            check=True
        )
        
        if model in self.list_of_models:
            self.list_of_models.remove(model)
        
        return True

    @require_running
    def get_list_running_models(self) -> List[Dict[str, str]]:
        """Get list of currently running models.
        
        Returns cached list. Use refresh_list_of_running_models() to update.
        
        Returns:
            List of dictionaries with model metadata
        """
        return self.list_of_running_models

    @require_running
    @handle_exceptions(default_return=None, log_error=True)
    def refresh_list_of_running_models(self) -> None:
        """Refresh cached list of running models via 'ollama ps'.
        
        Executes 'ollama ps' and parses output to extract running model
        information including size, processor usage, and expiration.
        Updates self.list_of_running_models cache.
        """
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_short,
            check=True
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # skip header
        running_models = []
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 4:
                    running_models.append({
                        'name': parts[0],
                        'size': ' '.join(parts[1:3]),
                        'processor': parts[3],
                        'until': ' '.join(parts[4:]) if len(parts) > 4 else ''
                    })
        
        self.list_of_running_models = running_models

    def get_running_model_names(self) -> List[str]:
        """Get list of names of currently running models.
        
        Returns:
            List of model name strings
        """
        running = self.get_list_running_models()
        return [model['name'] for model in running]

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False)
    def start_running_model(self, model: str) -> bool:
        """Load a model into memory via 'ollama run'.
        
        Sends empty prompt to load model without generating text.
        
        Args:
            model: Model name to start
            
        Returns:
            True if model was loaded (return code 0), False otherwise
        """
        result = subprocess.run(
            ["ollama", "run", model, ""],  # send empty prompt to load model into memory
            capture_output=True,
            text=True,
            timeout=self.config.timeout_default,
            check=True
        )
        return result.returncode == 0

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False)
    def stop_running_model(self, model: str, force: bool = False) -> bool:
        """Unload a model from memory via 'ollama stop'.
        
        Args:
            model: Model name to stop
            force: Skip running check if True (default: False)
            
        Returns:
            True if model was stopped, False if not running or error
        """
        if not force:
            running_models = self.get_running_model_names()
            if model not in running_models:
                return False

        result = subprocess.run(
            ["ollama", "stop", model],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_short,
            check=True
        )
        return True

    @require_running
    @log_execution()
    def stop_all_running_models(self) -> Dict[str, bool]:
        """Stop all currently running models.
        
        Returns:
            Dictionary mapping model names to success status (True/False)
        """
        running_models = self.get_running_model_names()
        results: Dict[str, bool] = {}
        
        for model in running_models:
            results[model] = self.stop_running_model(model)
        
        return results


# AI Communication
    @require_running
    @validate_model_name
    @log_execution()
    @handle_exceptions(default_return=None)
    def generate(self, model: str, prompt: str) -> Optional[str]:
        """Generate text using a model (non-streaming).
        
        Executes 'ollama run' and returns complete response.
        
        Args:
            model: Model name to use for generation
            prompt: Input text prompt
            
        Returns:
            Generated text as string, or None on error
        """
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=self.config.timeout_default,
            check=True
        )
        
        response = result.stdout.strip()
        return response

    @require_running
    @validate_model_name
    @log_execution()
    def generate_stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        """Generate text using a model (streaming).
        
        Executes 'ollama run' and yields output line by line as it's generated.
        
        Args:
            model: Model name to use for generation
            prompt: Input text prompt
            
        Yields:
            Lines of generated text as they appear
            5
        """
        try:
            process = subprocess.Popen(
                ["ollama", "run", model, prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line.rstrip('\n')
            
            process.wait()
            
            if process.returncode != 0:
                error = process.stderr.read()
                yield f"[Error: {error}]"
                
        except Exception as e:
            # yield error message to caller instead of just logging
            yield f"[Error: {e}]"
