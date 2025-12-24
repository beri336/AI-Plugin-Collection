# src/ollama_config.py

"""
Configuration management for Ollama Manager.
  This module provides a centralized configuration system using dataclasses and environment variable support.
"""

from dataclasses import dataclass, field
from pathlib import Path

import os


@dataclass
class OllamaConfig:
    """Configuration for Ollama Manager.
    
    Attributes:
        host: Hostname where Ollama is running
        port: Port number for Ollama API
        timeout_default: Default timeout for operations in seconds
        timeout_connection: Connection check timeout in seconds
        timeout_download: Model download timeout in seconds
        log_dir: Directory for log files
        cache_dir: Directory for cache files
        default_model: Default model to use
        max_retries: Maximum number of retries for failed requests
        keep_alive_minutes: Minutes to keep models loaded in memory
    """

    # connection settings
    host: str = "localhost"
    port: int = 11434
    
    # timeout settings (in seconds)
    timeout_default: int = 120
    timeout_connection: int = 2
    timeout_download: int = 600
    timeout_short: int = 5
    timeout_long: int = 300
    timeout_generation = 500

    # directory settings
    log_dir: Path = field(default_factory=lambda: Path('logs'))
    cache_dir: Path = field(default_factory=lambda: Path('.cache/ollama'))

    # model settings
    default_model: str = "llama3.2:3b"
    keep_alive_minutes: int = 5

    # retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.3
    
    # API endpoints
    _endpoints: dict = field(default_factory=lambda: {
        'version': '/api/version',
        'tags': '/api/tags',
        'show': '/api/show',
        'pull': '/api/pull',
        'delete': '/api/delete',
        'generate': '/api/generate',
        'ps': '/api/ps',
    })

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def get_endpoint(self, name: str) -> str:
        if name not in self._endpoints:
            raise KeyError(f"Unkown endpoint: {name}")
        return f"{self.base_url}{self._endpoints[name]}"

    def ensure_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Load configuration from environment variables.
        
        Environment variables:
            OLLAMA_HOST: Hostname (default: localhost)
            OLLAMA_PORT: Port number (default: 11434)
            OLLAMA_TIMEOUT: Default timeout (default: 120)
            OLLAMA_LOG_DIR: Log directory (default: logs)
            OLLAMA_CACHE_DIR: Cache directory (default: .cache/ollama)
            OLLAMA_DEFAULT_MODEL: Default model (default: llama3.2:3b)
            
        Returns:
            OllamaConfig instance with environment variable values
        """
        return cls(
            host=os.getenv("OLLAMA_HOST", "localhost"),
            port=int(os.getenv("OLLAMA_PORT", "11434")),
            timeout_default=int(os.getenv("OLLAMA_TIMEOUT", "120")),
            timeout_connection=int(os.getenv("OLLAMA_TIMEOUT_CONNECTION", "2")),
            timeout_download=int(os.getenv("OLLAMA_TIMEOUT_DOWNLOAD", "600")),
            log_dir=Path(os.getenv("OLLAMA_LOG_DIR", "logs")),
            cache_dir=Path(os.getenv("OLLAMA_CACHE_DIR", ".cache/ollama")),
            default_model=os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:3b"),
            keep_alive_minutes=int(os.getenv("OLLAMA_KEEP_ALIVE", "5")),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary with all configuration values
        """
        return {
            'host': self.host,
            'port': self.port,
            'base_url': self.base_url,
            'timeout_default': self.timeout_default,
            'timeout_connection': self.timeout_connection,
            'timeout_download': self.timeout_download,
            'log_dir': str(self.log_dir),
            'cache_dir': str(self.cache_dir),
            'default_model': self.default_model,
            'keep_alive_minutes': self.keep_alive_minutes,
            'max_retries': self.max_retries,
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"OllamaConfig(host={self.host}, port={self.port}, "
            f"default_model={self.default_model})"
        )
