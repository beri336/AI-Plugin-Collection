# src/ollama_manager.py

from ollama_cmd_manager import OllamaCMDManager, PullMode
from ollama_api_manager import OllamaAPIManager
from ollama_cmd_manager import OllamaCMDManager
from ollama_service import OllamaService
from ollama_helper import OllamaHelper

from enum import Enum


class OllamaBackend(Enum):
    API = "api"
    CMD = "cmd"


class OllamaManager():
    def __init__(
        self,
        backend: OllamaBackend = OllamaBackend.API,
        host: str = "localhost",
        port: int = 11434
    ) -> None:
        self.service = OllamaService()
        self.cmd = OllamaCMDManager()
        self.api = OllamaAPIManager()
        self.helper = OllamaHelper()
        self.logger = None
        
        # Init backend
        if backend == OllamaBackend.API:
            self._backend = OllamaAPIManager(host, port)
        else:
            self._backend = OllamaCMDManager()
        
        self.backend_type = backend

    def get_backend_type(self):
        print("Set backend type: '{self.backend_type}'")

    def switch_backend(self, mode: OllamaBackend):
        self.backend_type = mode
        print(f"New backend type: '{mode}'")

# OllamaCMDManager & OllamaAPIManager
    def get_list_of_models(self) -> None:
        models: list[str] = self._backend.list_model_names()
        
        print("All available (downlaoded) models:")
        for i in models:
            print(f"- '{i}'")

    def get_list_of_models_detailed(self) -> None:
        models: list[str] = self._backend.list_models_detailed()
        
        print("All available (downloaded) models with details:")
        if models:
            for i in models:
                print(f"- Modelname: '{i["name"]}'")
                print(f"    - ID: '{i["id"]}'")
                print(f"    - Size: '{i["size"]}'")
                print(f"    - Last modified: '{i["modified"]}'")

    def get_information_for_model(self, model: str):
        model_exists = self._backend.get_model_info(model)
        if not model_exists:
            print(f"'{model}' does not exist.")
            return
        
        model_info = self.cmd.get_model_info(model)
        
        if model_info is None:
            return
        
        print(f"\n=== Model Info: {model_info['model_name']} ===\n")
        
        # iterate over 'model' dictionary
        for section_name, section_data in model_info.items():
            if section_name == 'model_name':
                continue  # skip, already printed
            
            print(f"[{section_name.upper()}]")
            
            if isinstance(section_data, dict):
                # if it is a dictionary (such as ‘model’)
                for key, value in section_data.items():
                    if key == 'items' and isinstance(value, list):
                        # items are a list
                        for item in value:
                            print(f"  - {item}")
                    else:
                        print(f"  {key}: {value}")
            elif isinstance(section_data, list):
                # if it is a list directly
                for item in section_data:
                    print(f"  - {item}")
            else:
                # simple value
                print(f"  {section_data}")
            
            print()

    def load_new_model(self, model: str, stream: bool = True, mode: PullMode = PullMode.FOREGROUND) -> None:
        if self.backend_type == OllamaBackend.API:
            result = self.api.pull_model(model, stream)
            
            if result:
                print(f"Model '{model}' successfully downloaded (via {mode}).")
            else:
                print(f"Error: While downloading Model '{model}' (via {mode}).")
        else:
            result = self.cmd.pull_model(model, mode)
            
            if result:
                print(f"Model '{model}' successfully downloaded (via {mode}).")
            else:
                print(f"Error: While downloading Model '{model}' (via {mode}).")

    def load_new_model_with_progress(self, model: str):
        print(f"Starting download of '{model}'...")
        
        try:
            for progress in self._backend.pull_model_with_progress(model):
                status = progress.get('status', 'unknown')
                
                if status == 'downloading':
                    percent = progress.get('percent', 0)
                    size = progress.get('size', '')
                    print(f"\rDownloading: {percent:.1f}% {size}", end='', flush=True)
                
                elif status == 'pulling_manifest':
                    print(f"\r{progress.get('message', 'Pulling manifest...')}", flush=True)
                
                elif status == 'verifying':
                    print(f"\r{progress.get('message', 'Verifying...')}", flush=True)
                
                elif status == 'completed':
                    print(f"\n✓ Model '{model}' successfully downloaded.")
                    return True
                
                elif status == 'failed':
                    print(f"\n✗ Error: {progress.get('error', 'Unknown error')}")
                    return False
                
                elif status == 'error':
                    print(f"\n✗ Error: {progress.get('error', 'Unknown error')}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error while downloading model '{model}': {e}")
            return False

    def remove_model(self, model: str, force: bool = False) -> None:
        status = self._backend.delete_model(model, force)
        
        if status:
            print(f"Model '{model}' was successfully removed.")
        else:
            print(f"Error: While removing Model '{model}'.")

    def check_if_model_exists(self, model: str) -> None:
        model_exists = self._backend.model_exists(model)
    
        if model_exists:
            print(f"Model '{model}' is installed.")
        else:
            print(f"Model '{model}' is not installed.")

    def refresh_list_of_models(self):
        self._backend.refresh_list_of_models()
        print("Refreshed the list of models.")
