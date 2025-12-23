# src/ollama_cmd_manager.py

from typing import Any

import subprocess


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
