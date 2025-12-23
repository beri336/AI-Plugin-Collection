# src/ollama_api_manager.py

from datetime import datetime

import requests

class OllamaAPIManager:
    def __init__(self, host: str = "localhost", port: int = 11434) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        
        self.is_running: bool = self._check_connection()
        self.list_of_models: list[str] = []

    def get_host(self):
        return self.host
    
    def set_host(self, new_host: str):
        self.host = new_host

    def get_port(self):
        return self.host
    
    def set_port(self, new_port: int):
        self.port = new_port
    
    def get_base_url(self):
        return self.base_url

    def refresh_list_of_models(self):
        self.list_of_models = []
        self.list_of_models = self.list_model_names()

# Model-Management
    def _check_connection(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def _get_url(self, endpoint: str = "") -> str:
        return f"{self.base_url}{endpoint}"

    def list_models_detailed(self):
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get('models', []):
                # Convert size from bytes to readable format
                size_bytes = model.get('size', 0)
                if size_bytes >= 1_000_000_000:
                    size = f"{size_bytes / 1_000_000_000:.1f} GB"
                else:
                    size = f"{size_bytes / 1_000_000:.0f} MB"
                
                # Format modified time
                modified_at = model.get('modified_at', '')
                if modified_at:
                    try:
                        dt = datetime.fromisoformat(modified_at.replace('Z', '+00:00'))
                        now = datetime.now(dt.tzinfo)
                        diff = now - dt
                        
                        if diff.days > 0:
                            if diff.days > 30:
                                months = diff.days // 30
                                modified = f"{months} month{'s' if months > 1 else ''} ago"
                            else:
                                modified = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
                        else:
                            hours = diff.seconds // 3600
                            modified = f"{hours} hour{'s' if hours > 1 else ''} ago"
                    except:
                        modified = modified_at
                else:
                    modified = 'unknown'
                
                models.append({
                    'name': model['name'],
                    'id': model.get('digest', '')[:12],  # short digest like ollama list
                    'size': size,
                    'modified': modified
                })
            
            return models
            
        except requests.RequestException as e:
            return []
        except Exception as e:
            return []

    def list_model_names(self):
        if not self.is_running:
            raise RuntimeError("Ollama is not running!")
        
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            self.list_of_models = models
            
            return models
            
        except requests.RequestException as e:
            return []
        except Exception as e:
            return []

    def get_model_info(self, model: str):
        if not self.list_of_models:
            self.list_model_names()
        
        try:
            response = requests.post(
                "http://localhost:11434/api/show",
                json={"name": model},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Structure the info similar to CLI output
            info = {
                'model_name': model,
                'model': {},
                'parameters': {},
                'details': {}
            }
            
            # Model details
            if 'details' in data:
                details = data['details']
                info['model'] = {
                    'architecture': details.get('family', ''),
                    'parameters': details.get('parameter_size', ''),
                    'quantization': details.get('quantization_level', ''),
                    'format': details.get('format', '')
                }
                if 'parent_model' in details and details['parent_model']:
                    info['model']['parent_model'] = details['parent_model']
            
            # Parameters
            if 'parameters' in data:
                info['parameters'] = data['parameters']
            
            # Template
            if 'template' in data:
                info['template'] = data['template']
            
            # License
            if 'license' in data:
                info['license'] = data['license']
            
            # Modelfile
            if 'modelfile' in data:
                info['modelfile'] = data['modelfile']
            
            # System message
            if 'system' in data:
                info['system'] = data['system']
            
            return info
            
        except requests.RequestException as e:
            return None
        except Exception as e:
            return None

    def model_exists(self, model: str) -> bool:
        return model in self.list_model_names()
