# src/ollama_api_manager.py

import requests

class OllamaAPIManager:
    def __init__(self, host: str = "localhost", port: int = 11434) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        
        self.is_running: bool = self._check_connection()

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
