# src/ollama_cmd_manager.py

from typing import Any
from enum import Enum

import subprocess
import platform
import re


class PullMode(Enum):
    BACKGROUND = "background"
    FOREGROUND = "foreground"


class OllamaCMDManager:
    def __init__(self) -> None:
        self.is_installed: bool
        self.is_running: bool=True
        self.list_of_models: list[str] = []

    def refresh_list_of_models(self):
        self.list_of_models = []
        self.list_of_models = self.list_model_names()

# Model-Management
    def list_model_names(self) -> list[str]:
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        try:
            result = subprocess.run (
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')[1:]  # skip header
            models = [line.split()[0] for line in lines if line.strip()]
            self.list_of_models = models
            
            return models
        
        except subprocess.CalledProcessError as e:
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return []

    def list_models_detailed(self):
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5,
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
        
        except subprocess.CalledProcessError as e:
            return []
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return []

    def get_model_info(self, model: str):
        if not self.list_of_models:
            self.list_model_names()
        
        try:
            result = subprocess.run(
                ["ollama", "show", model],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            info: dict[str, Any] = {'model_name': model}
            output = result.stdout.strip().splitlines()
            
            current_section: str | None = None
            
            for line in output:
                stripped = line.strip()
                
                if line and not line.startswith(' ') and stripped:
                    current_section = stripped.lower().replace(' ', '_')
                    info[current_section] = {}
                    continue
                
                if stripped and current_section and isinstance(info[current_section], dict):
                    if ':' in stripped:
                        # Key-Value pair
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
        
        except subprocess.CalledProcessError as e:
            return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return None

    def model_exists(self, model: str) -> bool:
        return model in self.list_model_names()

    def pull_model(self, model, mode: PullMode = PullMode.FOREGROUND):
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        try:
            if mode == PullMode.BACKGROUND:
                return self._pull_model_background(model)
            else:
                return self._pull_model_foreground(model)
        except Exception as e:
            return False

    def _pull_model_foreground(self, model: str) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=600
            )
            return result.returncode == 0
        except Exception as e:
            return False

    def _pull_model_background(self, model: str) -> bool:
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

    def pull_model_with_progress(self, model: str):
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
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
                    'percent': 100.0,
                }
            else:
                yield {
                    'status': 'failed',
                    'error': process.stderr.read(),
                }
                
        except Exception as e:
            yield {
                'status': 'error',
                'error': str(e),
            }

    def _parse_pull_progress(self, line: str) -> dict | None:
        # extracting percentage from lines like "pulling xyz... 45%"
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

    def delete_model(self, model: str, force: bool = False) -> bool:
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        # check if model exists
        if not force:
            if not self.list_of_models:
                self.list_model_names()
            
            if model not in self.list_of_models:
                return False
        
        try:
            result = subprocess.run(
                ["ollama", "rm", model],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            # update internal model list
            if model in self.list_of_models:
                self.list_of_models.remove(model)
            
            return True
            
        except subprocess.CalledProcessError as e:
            return False
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return False
