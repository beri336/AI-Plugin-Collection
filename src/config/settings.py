# src/config/settings.py

from dataclasses import field, dataclass
from pathlib import Path

import json


@dataclass
class Config:
# Connection Settings
    host: str = "localhost"
    port: int = 11434
    base_url = f"http://{host}:{port}"

# Timeout Settings (in seconds)
    timeout_default: int = 120
    timeout_short: int = 5
    timeout_long: int = 300
    timeout_generation = 500
    timeout_connection: int = 2
    timeout_download: int = 600

# Directory Settings
    log_directory: Path = field(default_factory=lambda: Path('logs'))
    cache_directory: Path = field(default_factory=lambda: Path('.cache/ollama'))

# Model Settings
    default_model: str = "llama3.2:3b"
    keep_alive_minutes: int = 5

# Retry Settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.3

# API Endpoints
    _endpoints: dict = field(default_factory=lambda: {
        'version': '/api/version',
        'tags': '/api/tags',
        'show': '/api/show',
        'pull': '/api/pull',
        'delete': '/api/delete',
        'generate': '/api/generate',
        'ps': '/api/ps',
    })

# Methods
    def get_endpoint(self, name: str) -> str:
        if name not in self._endpoints:
            raise KeyError(f"Unkown endpoint: {name}")
        return f"{self.base_url}{self._endpoints[name]}"

    def ensure_directories(self) -> None:
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.cache_directory.mkdir(parents=True, exist_ok=True)

# Getter and Setter
    def get_host(self) -> str:
        return self.host
    
    def get_port(self) -> int:
        return self.port
    
    def set_host(self, new_host: str) -> None:
        self.host = new_host
    
    def set_port(self, new_port: int) -> None:
        self.port = new_port

    @property
    def get_base_url(self) -> str:
        return self.base_url

    @classmethod
    def load_from_json(cls, filepath: str | Path) -> "Config":
        """ Load configuration values from a JSON file """
        path = Path(filepath)
        
        if path.is_dir():
            raise IsADirectoryError("Given path is a directory, not a JSON file.")
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
