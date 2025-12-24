# src/ollama_cmd_manager.py

from decorators import (
    require_running, 
    validate_model_name, 
    handle_exceptions
)
from ollama_service import OllamaService
from ollama_config import OllamaConfig

from typing import Optional, List, Dict, Any, Generator
from enum import Enum

import subprocess
import platform
import re


class PullMode(Enum):
    """ Mode for pulling models """
    BACKGROUND = "background"
    FOREGROUND = "foreground"


class OllamaCMDManager:
    """Manager for Ollama CLI interactions
    
    Handles all command-line based communication with Ollama service,
    including model management and text generation
    """
    
    def __init__(self) -> None:
        """ Initialize the Ollama CMD Manager """
        self._service = OllamaService()
        self.is_installed: bool = self._service.is_installed()
        self.is_running: bool = self._service.is_process_running()
        
        self.list_of_models: List[str] = []
        self.list_of_running_models: List[str] = []
        
        self.config = OllamaConfig()

    def refresh_list_of_models(self) -> None:
        """ Refresh the cached list of models """
        self.list_of_models = self.list_model_names()

    def refresh_list_of_running_models(self) -> None:
        """ Refresh the cached list of running models """
        self.list_of_running_models = self._get_running_model_names()

# Model-Management
    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def list_model_names(self) -> List[str]:
        """ List names of all available models """
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
        return models

    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def list_models_detailed(self) -> List[Dict[str, str]]:
        """ List all models with detailed information """
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

    @handle_exceptions(default_return=None, log_error=True)
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """ Get detailed information about a specific model """
        if not self.list_of_models:
            self.list_model_names()
        
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
                    # key-Value pair
                    parts = stripped.split(None, 1)  # split on first Whitespace
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
        """ Check if a model is installed locally """
        return model in self.list_model_names()

    @require_running
    @validate_model_name
    def pull_model(self, model, mode: PullMode = PullMode.FOREGROUND) -> bool:
        """ Download a model from Ollama registry """
        try:
            if mode == PullMode.BACKGROUND:
                return self._pull_model_background(model)
            else:
                return self._pull_model_foreground(model)
        except Exception as e:
            return False

    def _pull_model_foreground(self, model: str) -> bool:
        """ Pull model in foreground (blocking) """
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_download
            )
            return result.returncode == 0
        except Exception as e:
            return False

    def _pull_model_background(self, model: str) -> bool:
        """ Pull model in background (new terminal window) """
        system = platform.system().lower()
        command = f"ollama pull {model}"
        
        commands = {
            "darwin": ["osascript", "-e", f'tell app "Terminal" to do script "{command}"'],
            "windows": ["start", "cmd", "/k", command],
            "linux": ["gnome-terminal", "--", "bash", "-c", command]
        }
        
        cmd = commands.get(system)
        if not cmd:
            return False
        
        try:
            subprocess.Popen(cmd, shell=(system == "windows"))
            return True
        except Exception as e:
            return False

    @require_running
    @validate_model_name
    def pull_model_with_progress(self, model: str) -> Generator[Dict[str, Any], None, None]:
        """ Download a model with progress updates """
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
            yield {
                'status': 'error',
                'error': str(e)
            }

    def _parse_pull_progress(self, line: str) -> Optional[Dict[str, Any]]:
        """ Parse progress information from CLI output """
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
        """ Delete a model from local storage """
        if not force:  # check if model exists
            if not self.list_of_models:
                self.list_model_names()
        
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
    @handle_exceptions(default_return=[], log_error=True)
    def get_running_models(self) -> List[Dict[str, str]]:
        """ Get list of currently running models """
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
        
        return running_models

    def _get_running_model_names(self) -> List[str]:
        """ Get names of currently running models """
        running = self.get_running_models()
        return [model['name'] for model in running]

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False, log_error=True)
    def start_running_model(self, model: str) -> bool:
        """ Load a model into memory """
        result = subprocess.run(
            ["ollama", "run", model, ""],  # send empty prompt to load model into memory
            capture_output=True,
            text=True,
            timeout=self.config.timeout_default,
            check=True
        )
        return True

    @require_running
    @validate_model_name
    def stop_running_model(self, model: str, force: bool = False) -> bool:
        """ Unload a model from memory """
        if not force:
            running_models = self._get_running_model_names()
            if model not in running_models:
                return False
        
        try:
            result = subprocess.run(
                ["ollama", "stop", model],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            return True
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return False

    @require_running
    def stop_all_running_models(self) -> Dict[str, bool]:
        """ Stop all currently running models """
        running_models = self._get_running_model_names()
        results: Dict[str, bool] = {}
        
        for model in running_models:
            results[model] = self.stop_running_model(model)
        
        return results


# AI-Communication
    @require_running
    @validate_model_name
    @handle_exceptions(default_return=None, log_error=True)
    def generate(self, model: str, prompt: str) -> Optional[str]:
        """ Generate text using a model (non-streaming) """
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
    def generate_stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        """ Generate text using a model (streaming) """
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
            yield f"[Error: {e}]"
