# src/ollama_manager.py

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
