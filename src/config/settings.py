# src/config/settings.py

'''
Ollama Configuration Management
  This file defines the central configuration class for Ollama integration.

- Manages connection settings (host, port, base URL)
- Defines timeout values for various API operations
- Configures directories for logs and cache
- Provides API endpoints as central access points
- Enables loading configurations from JSON files
- Provides getters/ setters for dynamic adjustment of connection parameters
'''

from dataclasses import field, dataclass
from pathlib import Path

import json


@dataclass
class Config:
    """Central configuration dataclass for Ollama API integration.
    
    Provides default values for connection settings, timeouts, directories,
    and API endpoints. Supports loading configuration from JSON files and
    dynamic adjustment of connection parameters.
    
    Attributes:
        host: Hostname or IP address of Ollama server
        port: Port number for Ollama API
        base_url: Full base URL constructed from host and port
        timeout_default: Default timeout for API requests in seconds
        timeout_short: Short timeout for quick operations
        timeout_long: Extended timeout for long-running operations
        timeout_generation: Timeout for text generation requests
        timeout_connection: Timeout for connection attempts
        timeout_download: Timeout for model downloads
        log_directory: Directory path for log files
        cache_directory: Directory path for cache storage
        default_model: Default model name for operations
        keep_alive_minutes: Minutes to keep models loaded in memory
        max_retries: Maximum number of retry attempts for failed requests
        retry_backoff_factor: Exponential backoff factor for retries
    """
# Connection Settings
    host: str = "localhost"
    port: int = 11434
    base_url: str = f"http://{host}:{port}"

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
        """Construct full URL for specified API endpoint.
        
        Args:
            name: Name of the endpoint (e.g., 'version', 'tags', 'generate')
            
        Returns:
            Full URL string combining base_url with endpoint path
        """
        if name not in self._endpoints:
            raise KeyError(f"Unkown endpoint: {name}")
        return f"{self.base_url}{self._endpoints[name]}"

    def ensure_directories(self) -> None:
        """Create log and cache directories if they don't exist.
        
        Creates both log_directory and cache_directory with all parent
        directories. Does nothing if directories already exist.
        """
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.cache_directory.mkdir(parents=True, exist_ok=True)

# Getter and Setter
    def get_host(self) -> str:
        """Get current host configuration.
        
        Returns:
            Current hostname or IP address as string
        """
        return self.host
    
    def get_port(self) -> int:
        """Get current port configuration.
        
        Returns:
            Current port number as integer
        """
        return self.port
    
    def set_host(self, new_host: str) -> None:
        """Set new host for Ollama connection.
        
        Args:
            new_host: Hostname or IP address (e.g., 'localhost', '192.168.1.100')
            
        Note:
            This does not automatically update base_url.
        """
        self.host = new_host
    
    def set_port(self, new_port: int) -> None:
        """Set new port for Ollama connection.
        
        Args:
            new_port: Port number (typically 11434 for Ollama)
            
        Note:
            This does not automatically update base_url.
        """
        self.port = new_port

    @property
    def get_base_url(self) -> str:
        """Get base URL for API requests.
        
        Returns:
            Current base_url string
            
        Note:
            This returns the static base_url value set during initialization.
            Changes to host or port via setters will not be reflected here.
        """
        return self.base_url

    @classmethod
    def load_from_json(cls, filepath: str | Path) -> "Config":
        """Load configuration values from a JSON file
        
        Args:
            filepath: Path to JSON configuration file
            
        Returns:
            New Config instance with loaded values
        """
        path = Path(filepath)
        
        if path.is_dir():
            raise IsADirectoryError("Given path is a directory, not a JSON file.")
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
