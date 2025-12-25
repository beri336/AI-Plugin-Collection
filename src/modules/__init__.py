# src/modules/__init__.py

"""
Ollama Plugin Modules
  This package provides the core modules for Ollama integration:

- Service Manager: Service lifecycle and health monitoring
- API Manager: REST API-based operations
- CMD Manager: CLI-based operations
- Conversation Manager: Multi-turn conversation handling
- Plugin Manager: Unified facade for all operations
"""

from .conversation_manager import ConversationManager, Message, Conversation
from .plugin_manager import OllamaManager, OllamaBackend
from .cmd_manager import CMDManager, PullMode
from .service_manager import Service
from .api_manager import APIManager


__all__ = [
    # Service Management
    'Service', 
    
    # API & CLI Managers
    'APIManager', 
    'CMDManager', 
    'PullMode', 
    
    # Conversation Management
    'ConversationManager', 
    'Message', 
    'Conversation', 
    
    # Main Plugin Manager
    'OllamaManager', 
    'OllamaBackend',
]
