# src/ollama_api_manager.py

from decorators import (
    require_running, 
    retry_on_failure, 
    validate_model_name, 
    handle_exceptions, 
    cache_result
)
from ollama_config import OllamaConfig

from typing import Optional, List, Dict, Any, Generator
from datetime import datetime

import json
import requests

class OllamaAPIManager:
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 11434,
        config: Optional[OllamaConfig] = None
    ) -> None:
        """Initialize the Ollama API Manager
        
        Args:
            host: Hostname where Ollama is running
            port: Port number for Ollama API
            config: Optional OllamaConfig instance (overrides host/port)
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        
        self.is_running: bool = self._check_connection()
        self.list_of_models: list[str] = []
        self.list_of_running_models: list[str] = []
        
        if config:
            self.config = config
            self.host: str = config.host
            self.port: int = config.port
        else:
            self.config = OllamaConfig(host=host, port=port)
            self.host: str = host
            self.port: int = port
        
        self.base_url: str = self.config.base_url
        self.is_running: bool #= self._check_connection()
        self.list_of_models: List[str] = []
        self.list_of_running_models: List[str] = []

# Getter and Setter
    def get_host(self):
        return self.host
    
    def set_host(self, new_host: str):
        """ Set a new API host """
        self.host = new_host
        self.config.host = new_host
        self.base_url = self.config.base_url
        self.is_running = self._check_connection()

    def get_port(self) -> int:
        """ Get the current API port """
        return self.port
    
    def set_port(self, new_port: int) -> None:
        """ Set a new API port """
        self.port = new_port
        self.config.port = new_port
        self.base_url = self.config.base_url  # update base_url too
        self.is_running = self._check_connection()
    
    def get_base_url(self) -> str:
        """ Get the complete base URL """
        return self.base_url

    def refresh_list_of_models(self) -> None:
        """ Refresh the cached list of available models """
        self.list_of_models = []
        self.list_of_models = self.list_model_names()

    def refresh_list_of_running_models(self) -> None:
        """ Refresh the cached list of running models """
        self.list_of_running_models = []
        self.list_of_running_models = self._get_running_model_names()

# Connection Check
    @retry_on_failure(max_attempts=3, delay=1.0)
    def _check_connection(self) -> bool:
        """ Check if Ollama API is reachable """
        try:
            response = requests.get(
                f"{self.base_url}/api/version",
                self.config.get_endpoint('version'),
                timeout=self.config.timeout_connection
            )
            return response.status_code == 200
        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            return False
        except:
            if response.status_code == 200:
                self.is_running = True
                return True
            else:
                self.is_running = False
                return False

# Model-Management
    @require_running
    @cache_result(ttl_seconds=60)
    @handle_exceptions(default_return=[], log_error=True)
    def list_models_detailed(self) -> List[Dict[str, Any]]:
        """ List all available models with detailed information """
        response = requests.get(
            self.config.get_endpoint('tags'),
            timeout=self.config.timeout_short
        )
        response.raise_for_status()
        
        data = response.json()
        models = []
        
        for model in data.get('models', []):
            # convert size from bytes to readable format
            size_bytes = model.get('size', 0)
            if size_bytes >= 1_000_000_000:
                size = f"{size_bytes / 1_000_000_000:.1f} GB"
            else:
                size = f"{size_bytes / 1_000_000:.0f} MB"
            
            # format modified time
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

    @require_running
    @cache_result(ttl_seconds=60)
    @handle_exceptions(default_return=[], log_error=True)
    def list_model_names(self) -> List[str]:
        """ List names of all available models """
        response = requests.get(
            self.config.get_endpoint('tags'),
            timeout=self.config.timeout_connection
        )
        response.raise_for_status()
        
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        self.list_of_models = models
        
        return models

    @handle_exceptions(default_return=None, log_error=True)
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """ Get detailed information about a specific model """
        if not self.list_of_models:
            self.list_model_names()
            
        response = requests.post(
            self.config.get_endpoint('show'),
            timeout=self.config.timeout_short,
            json={"name": model}
        )
        response.raise_for_status()
        
        data = response.json()
        # structure the info similar to CLI output
        info = {
            'model_name': model,
            'model': {},
            'parameters': {},
            'details': {}
        }
        
        # model details
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
        
        if 'parameters' in data:
            info['parameters'] = data['parameters']
        if 'template' in data:
            info['template'] = data['template']
        if 'license' in data:
            info['license'] = data['license']
        if 'modelfile' in data:
            info['modelfile'] = data['modelfile']
        if 'system' in data:
            info['system'] = data['system']
        
        return info

    def model_exists(self, model: str) -> bool:
        """ Check if a model is installed locally """
        return model in self.list_model_names()

    @require_running
    @validate_model_name
    def pull_model(self, model: str, stream: bool = True) -> bool:
        """ Download a model from Ollama registry """
        try:
            response = requests.post(
                self.config.get_endpoint('pull'),
                timeout=self.config.timeout_download,
                json={"name": model, "stream": stream},
                stream=stream,
            )
            response.raise_for_status()
            
            if stream:
                # process streaming response
                for line in response.iter_lines():
                    if line:
                        try:
                            progress = json.loads(line.decode('utf-8'))
                            # yield or callback for progress
                            if progress.get('status') == 'success':
                                return True
                        except json.JSONDecodeError:
                            continue
            
            return True
        except requests.RequestException as e:
            return False

    @require_running
    @validate_model_name
    def pull_model_with_progress(self, model: str) -> Generator[Dict[str, Any], None, None]:
        """ Download a model with progress updates """
        try:
            response = requests.post(
                self.config.get_endpoint('pull'),
                timeout=self.config.timeout_download,
                json={"name": model, "stream": True},
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        progress = json.loads(line.decode('utf-8'))
                        yield progress
                    except json.JSONDecodeError:
                        continue
        
        except requests.RequestException as e:
            yield {"status": "error", "error": str(e)}

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False, log_error=True)
    def delete_model(self, model: str, force: bool = False) -> bool:
        if not force:  # check if model exists
            if not self.list_of_models:
                self.list_model_names()
            
            if model not in self.list_of_models:
                return False
        
        response = requests.delete(
            self.config.get_endpoint('delete'),
            json={"name": model},
            timeout=self.config.timeout_default
        )
        response.raise_for_status()
        
        if model in self.list_of_models:
            self.list_of_models.remove(model)
        
        return True

    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def get_running_models(self) -> List[Dict[str, str]]:
        """ Get list of currently running models """
        response = requests.get(
            self.config.get_endpoint('ps'),
            timeout=self.config.timeout_short
        )
        response.raise_for_status()
        
        data = response.json()
        running_models = []
        
        for model in data.get('models', []):
            # convert size from bytes to readable format
            size_bytes = model.get('size', 0)
            if size_bytes >= 1_000_000_000:
                size = f"{size_bytes / 1_000_000_000:.1f} GB"
            else:
                size = f"{size_bytes / 1_000_000:.0f} MB"
            
            # format expires_at to relative time
            expires_at = model.get('expires_at', '')
            if expires_at:
                try:
                    exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    now = datetime.now(exp_time.tzinfo)
                    diff = exp_time - now
                    
                    minutes = int(diff.total_seconds() / 60)
                    if minutes > 0:
                        until = f"{minutes} minute{'s' if minutes != 1 else ''} from now"
                    else:
                        until = "expired"
                except (ValueError, AttributeError):
                    until = expires_at
            else:
                until = ''
            
            running_models.append({
                'name': model.get('name', ''),
                'size': size,
                'processor': f"{model.get('size_vram', 0) / size_bytes * 100:.0f}% GPU" if size_bytes > 0 else'CPU',
                'until': until
            })
        
        self.list_of_running_models = running_models
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
        response = requests.post(
            self.config.get_endpoint('generate'),
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": f"{self.config.keep_alive_minutes}m"
            },
            timeout=self.config.timeout_default
        )
        response.raise_for_status()
        return True

    @require_running
    @validate_model_name
    def stop_running_model(self, model: str, force: bool = False) -> bool:
        """ Unload a model from memory """
        if not force:  # check if model is actually running
            running_models = self._get_running_model_names()
            
            if model not in running_models:
                return False
        
        try:
            response = requests.post(
                self.config.get_endpoint('generate'),
                json={
                    "model": model,
                    "keep_alive": 0
                },
                timeout=self.config.timeout_short
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            return False

    @require_running
    def stop_all_running_models(self) -> Dict[str, bool]:
        """ Stop all currently running models """
        running_models = self._get_running_model_names()
        results: Dict[str, bool] = {}
        
        for model in running_models:
            results[model] = self.stop_running_model(model, force=True)
        
        return results

# AI-Communication
    @require_running
    @validate_model_name
    @handle_exceptions(default_return=None, log_error=True)
    def generate(
        self, 
        model: str, 
        prompt: str, 
        options: Optional[Dict[str, Any]]=None
    ) -> Optional[Dict[str, Any]]:
        """ Generate text using a model (non-streaming) """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if options:
            payload["options"] = options
        
        response = requests.post(
            self.config.get_endpoint('generate'),
            json=payload,
            timeout=self.config.timeout_generation
        )
        response.raise_for_status()
        
        data = response.json()
        return data

    @require_running
    @validate_model_name
    def generate_stream(
        self, 
        model: str, 
        prompt: str, 
        options: dict | None = None
    ) -> Generator[Dict[str, Any], None, None]:
        """ Generate text using a model (streaming) """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        if options:
            payload["options"] = options
        
        try:
            response = requests.post(
                self.config.get_endpoint('generate'),
                timeout=self.config.timeout_generation,
                json=payload,
                stream=True,
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        yield chunk
                        
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.RequestException as e:
            yield {"error": str(e), "done": True}
