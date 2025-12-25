# src/modules/api_manager.py

'''
Ollama API Manager for Model and Generation Operations
  This module provides the main interface to the Ollama REST API and manages models and generations.

- Checks API connection and availability with retry logic
- Lists installed and running models with detailed information
- Downloads (pulls) models with progress tracking
- Deletes, starts, and stops models
- Generates text with streaming and non-streaming modes
- Caches frequently used data (model lists) for performance optimization
- Formats timestamps, sizes, and other metadata in a user-friendly way
'''

from core.decorators import (
    require_running, 
    retry_on_failure, 
    validate_model_name, 
    handle_exceptions, 
    cache_result, 
    log_execution
)
from .service_manager import Service
from config.settings import Config

from typing import List, Dict, Any, Optional, Generator
from datetime import datetime

import json

import requests

class APIManager:
    """Manager for Ollama REST API operations.
    
    Provides high-level interface for model management and text generation
    via Ollama's REST API. Handles connection checking, model listing,
    pulling, deletion and text generation with both streaming and
    non-streaming modes.
    
    Features:
        - Automatic retry logic for transient failures
        - Caching of model lists for performance
        - Human-readable formatting of sizes and timestamps
        - Progress tracking for model downloads
        - Management of running models and memory
        
    Attributes:
        config: Configuration instance with API endpoints and timeouts
        service: Service manager for checking Ollama availability
        list_of_models: Cached list of installed model names
        list_of_running_models: Cached list of currently running models
    
    Note:
        Requires 'ollama' CLI to be installed and available in PATH.
    """
    
    def __init__(self) -> None:
        """ Initialize API manager with configuration and empty caches """
        self.config = Config()
        self.service = Service()
        
        self.list_of_models: List[str] = []
        self.list_of_running_models: List[Dict[str, str]] = []

# Connection Check
    @retry_on_failure(max_attempts=3, delay=1.0)
    @handle_exceptions(default_return=False, log_error=True)
    def check_connection(self) -> bool:
        """Check if Ollama API is reachable.
        
        Attempts to connect to the version endpoint with retry logic.
        Updates service's _is_api_reachable flag based on result.
        
        Returns:
            True if API is reachable (status 200), False otherwise
        """
        response = requests.get(
            self.config.get_endpoint(name='version'),
            timeout=self.config.timeout_connection
        )
        
        if response.status_code == 200:
            self.service._is_api_reachable = True
            return True
        else:
            self.service._is_api_reachable = False
            return False

    @require_running
    @cache_result(ttl_seconds=60)
    @handle_exceptions(default_return=[], log_error=True)
    def get_detailed_list_models(self) -> List[Dict[str, Any]]:
        """Get detailed information about all installed models.
        
        Fetches model list with metadata and formats it for display.
        Converts sizes to GB/ MB and timestamps to relative time.
        Results are cached for 60 seconds.
        
        Returns:
            List of model dictionaries with keys:
                - name: Model name (e.g., 'llama3.2:3b')
                - id: Short digest (first 12 chars)
                - size: Human-readable size ('4.5 GB' or '500 MB')
                - modified: Relative time ('2 days ago', '5 hours ago')
        """
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
                except Exception:
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
    @retry_on_failure(max_attempts=3, delay=1.0)
    @handle_exceptions(default_return=None, log_error=True)
    def refresh_list_of_model_names(self) -> None:
        """Refresh the cached list of installed model names.
        
        Fetches current model list from API and updates internal cache.
        Called automatically by get_list_model_names() if cache is empty.
        """
        response = requests.get(
            self.config.get_endpoint('tags'),
            timeout=self.config.timeout_connection
        )
        response.raise_for_status()
        
        data = response.json()
        models = [model['name'] for model in data.get('models', [])]
        self.list_of_models = models
    
    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def get_list_model_names(self) -> List[str]:
        """Get list of installed model names.
        
        Returns cached list if available, otherwise refreshes from API.
        
        Returns:
            List of model name strings
        """
        if not self.list_of_models:
            self.refresh_list_of_model_names()
        return self.list_of_models

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=None, log_error=True)
    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model.
        
        Fetches model metadata including architecture, parameters,
        quantization level, template and license information.
        
        Args:
            model: Model name (e.g., 'llama3.2:3b')
            
        Returns:
            Dictionary with model information:
                - model_name: Full model name
                - model: Architecture details (family, parameters, quantization)
                - parameters: Model configuration parameters
                - template: Prompt template (if available)
                - license: License information (if available)
                - modelfile: Modelfile content (if available)
                - system: System message (if available)
            Returns None on error.
        """
        if not self.list_of_models:
            self.refresh_list_of_model_names()
        
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
        """Check if a model is installed.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model is in cached list, False otherwise
            
        Note:
            Uses cached list. Call refresh_list_of_model_names() first
            for most current data.
        """
        return model in self.list_of_models

    @require_running
    @validate_model_name
    @log_execution()
    @handle_exceptions(default_return=False, log_error=True)
    def pull_model(self, model: str, stream: bool = True) -> bool:
        """Download (pull) a model from Ollama registry.
        
        Downloads the specified model with optional progress streaming.
        
        Args:
            model: Model name to pull (e.g., 'llama3.2:3b')
            stream: Whether to stream progress updates (default: True)
            
        Returns:
            True if pull succeeded, False otherwise
        """
        response = requests.post(
            self.config.get_endpoint("pull"),
            timeout=self.config.timeout_download,
            json={"name": model, "stream": stream},
            stream=stream,
        )
        response.raise_for_status()

        if stream:
            for line in response.iter_lines():
                if line:
                    progress = json.loads(line.decode("utf-8"))
                    if progress.get("status") == "success":
                        return True
        return True

    @require_running
    @validate_model_name
    @log_execution()
    @handle_exceptions
    def pull_model_with_progress(self, model: str) -> Generator[Dict[str, Any], None, None]:
        """Download a model with detailed progress updates.
        
        Returns a generator that yields progress dictionaries during download.
        
        Args:
            model: Model name to pull
            
        Yields:
            Progress dictionaries with keys like:
                - status: Current status ('pulling', 'downloading', 'success')
                - digest: Layer digest being downloaded
                - total: Total bytes to download
                - completed: Bytes downloaded so far
        """
        response = requests.post(
            self.config.get_endpoint('pull'),
            timeout=self.config.timeout_download,
            json={"name": model, "stream": True},
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                progress = json.loads(line.decode('utf-8'))
                yield progress
            else:
                continue

    @require_running
    @validate_model_name
    @handle_exceptions(default_return=False, log_error=True)
    def delete_model(self, model: str, force: bool=False) -> bool:
        """Delete an installed model.
        
        Removes model from local storage and refreshes model cache.
        
        Args:
            model: Model name to delete
            force: Skip existence check if True (default: False)
            
        Returns:
            True if deletion succeeded, False if model not found or error
            
        Side Effects:
            Refreshes list_of_models cache after successful deletion
        """
        if not force:  # check if model exists
            if not self.list_of_models:
                self.refresh_list_of_model_names()
            
            if model not in self.list_of_models:
                return False
        
        response = requests.delete(
            self.config.get_endpoint('delete'),
            json={"name": model},
            timeout=self.config.timeout_default
        )
        response.raise_for_status()
        
        self.refresh_list_of_model_names()
        
        return True

    @require_running
    @handle_exceptions(default_return=[], log_error=True)
    def get_list_running_models(self) -> List[Dict[str, str]]:
        """Get list of currently running models.
        
        Returns cached list of running models with their metadata.
        
        Returns:
            List of dictionaries with keys:
                - name: Model name
                - size: Memory usage ('2.0 GB')
                - processor: GPU usage percentage or 'CPU'
                - until: Time until model expires from memory
        """
        return self.list_of_running_models

    @require_running
    @retry_on_failure(max_attempts=3, delay=1.0)
    @handle_exceptions(default_return=None, log_error=True)
    def refresh_list_of_running_models(self) -> None:
        """Refresh the cached list of running models.
        
        Fetches current running models from API and formats their metadata.
        Updates self.list_of_running_models with current data.
        """
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
                exp_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                now = datetime.now(exp_time.tzinfo)
                diff = exp_time - now
                
                minutes = int(diff.total_seconds() / 60)
                if minutes > 0:
                    until = f"{minutes} minute{'s' if minutes != 1 else ''} from now"
                else:
                    until = "expired"
            else:
                until = ''
            
            running_models.append({
                'name': model.get('name', ''),
                'size': size,
                'processor': f"{model.get('size_vram', 0) / size_bytes * 100:.0f}% GPU" if size_bytes > 0 else'CPU',
                'until': until
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
    @handle_exceptions(default_return=False, log_error=True)
    def start_running_model(self, model: str) -> bool:
        """Load a model into memory for faster generation.
        
        Sends empty prompt to load model with configured keep_alive time.
        
        Args:
            model: Model name to start
            
        Returns:
            True if model was loaded successfully, False otherwise
        """
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
    @handle_exceptions(default_return=False, log_error=True)
    def stop_running_model(self, model: str, force: bool = False) -> bool:
        """Unload a model from memory.
        
        Sets keep_alive to 0 to immediately unload the model.
        
        Args:
            model: Model name to stop
            force: Skip running check if True (default: False)
            
        Returns:
            True if model was stopped, False if not running or error
        """
        if not force:  # check if model is actually running
            running_models = self.get_running_model_names()
            
            if model not in running_models:
                return False
            
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

    @require_running
    @log_execution()
    @handle_exceptions(default_return={}, log_error=True)
    def stop_all_running_models(self) -> Dict[str, bool]:
        """Stop all currently running models.
        
        Attempts to stop each running model and returns success status.
        
        Returns:
            Dictionary mapping model names to success status (True/False)
        """
        running_models = self.get_running_model_names()
        results: Dict[str, bool] = {}
        
        for model in running_models:
            results[model] = self.stop_running_model(model, force=True)
        
        return results

# AI Communication
    @require_running
    @validate_model_name
    @handle_exceptions(default_return=None, log_error=True)
    def generate(
        self, 
        model: str, 
        prompt: str, 
        options: Optional[Dict[str, Any]]=None
    ) -> Optional[Dict[str, Any]]:
        """Generate text using a model (non-streaming).
        
        Sends prompt to model and returns complete response.
        
        Args:
            model: Model name to use for generation
            prompt: Input text prompt
            options: Optional generation parameters (temperature, top_p, etc.)
            
        Returns:
            Response dictionary with keys:
                - response: Generated text
                - model: Model name used
                - created_at: Timestamp
                - done: Completion flag
                - context: Context window (for follow-up)
                - total_duration: Generation time in nanoseconds
            Returns None on error.
        """
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
    @log_execution()
    @handle_exceptions(default_return=iter([]), log_error=True)
    def generate_stream(
        self, 
        model: str, 
        prompt: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Generate text using a model (streaming).
        
        Yields response chunks as they are generated for real-time display.
        
        Args:
            model: Model name to use for generation
            prompt: Input text prompt
            options: Optional generation parameters
            
        Yields:
            Response chunk dictionaries with keys:
                - response: Text chunk (partial response)
                - done: False during generation, True when complete
                - context: Context window (in final chunk)
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        if options:
            payload["options"] = options
        
    
        response = requests.post(
            self.config.get_endpoint('generate'),
            timeout=self.config.timeout_generation,
            json=payload,
            stream=True,
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                yield chunk
                
                if chunk.get('done', False):
                    break
