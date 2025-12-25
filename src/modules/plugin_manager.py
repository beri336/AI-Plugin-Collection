# src/modules/plugin_manager.py

'''
Ollama Plugin Manager – Unified access to all subsystems
  This module provides a central interface for all Ollama functionalities and modules.

- Unifies API and CLI backend access with dynamic switching
- Manages model operations (list, pull, delete, info)
- Controls service lifecycle (start, stop, health checks)
- Integrates caching system for performance optimization
- Provides helper functions for installation and validation
- Enables context-based multi-turn conversations
- Exports conversations to various formats
- Provides logging and verbose modes
- Loads configurations from JSON files
'''

from __future__ import annotations

from .conversation_manager import ConversationManager
from .cmd_manager import CMDManager, PullMode
from .service_manager import Service
from .api_manager import APIManager
from core.cache_manager import Cache
from config.settings import Config
from core.helpers import Helper

from typing import Optional, Dict, Any, List
from enum import Enum

import logging


# Core Types
class OllamaBackend(str, Enum):
    """Enum for backend selection.
    
    Attributes:
        API: Use REST API backend (recommended for most use cases)
        CMD: Use CLI subprocess backend (for terminal operations)
    """
    API = "api"
    CMD = "cmd"


# Main Manager Class
class OllamaManager:
    """Unified facade providing simplified access to all Ollama modules.
    
    This is the main entry point for interacting with Ollama. It provides
    a high-level API that abstracts away the complexity of managing multiple
    subsystems (API, CLI, cache, service, etc.).
    
    Features:
        - Dynamic backend switching (API ↔ CLI)
        - Automatic caching with TTL support
        - Integrated service lifecycle management
        - Multi-turn conversation support
        - Model management and generation
        - Comprehensive health monitoring
        - Installation helpers
        
    Attributes:
        config: Configuration instance with settings and endpoints
        cache: Optional cache manager for performance optimization
        service: Service manager for Ollama lifecycle control
        api: API manager for REST API operations
        cmd: CMD manager for CLI operations
        helpers: Helper utilities for installation and validation
        backend_type: Currently active backend (API or CMD)
        logger: Logger instance for debug/info messages
        verbose: Whether to print verbose output
    """

    def __init__(
        self,
        backend: OllamaBackend = OllamaBackend.API,
        config: Optional[Config] = None,
        enable_cache: bool = True,
        verbose: bool = True,
    ) -> None:
        """Initialize the Ollama manager with configuration.
        
        Args:
            backend: Backend to use (API or CMD, default: API)
            config: Optional custom configuration (creates default if None)
            enable_cache: Enable response caching (default: True)
            verbose: Print verbose output and logs (default: True)
        """
        self.config = config or Config()
        self.config.ensure_directories()
        self.verbose = verbose

        # Cache
        self.cache: Optional[Cache] = None
        if enable_cache:
            self.cache = Cache(
                cache_dir=self.config.cache_directory,
                max_size_mb=100,
                default_ttl_seconds=3600,
            )

        # Sub-Managers
        self.service = Service()
        self.cmd = CMDManager()
        self.api = APIManager()
        self.helpers = Helper()

        # Backend
        self.backend_type: OllamaBackend = backend
        self._backend = self.api if backend == OllamaBackend.API else self.cmd

        # Logging
        self.logger = logging.getLogger("OllamaManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
            )
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        if self.verbose:
            self.logger.info(f"OllamaManager initialized (backend: {backend.value})")

# Backend control
    def switch_backend(self, mode: OllamaBackend) -> None:
        """Switch between API and CLI backends dynamically.
        
        Args:
            mode: Backend mode to switch to (API or CMD)
        """
        self.backend_type = mode
        self._backend = self.api if mode == OllamaBackend.API else self.cmd
        if self.verbose:
            self.logger.info(f"Switched backend to '{mode.value}'")

    def get_backend_type(self) -> OllamaBackend:
        """Get currently active backend type.
        
        Returns:
            Current backend (OllamaBackend.API or OllamaBackend.CMD)
        """
        return self.backend_type

# Core model operations
    def list_models(self) -> List[str]:
        """List all installed model names.
        
        Refreshes model cache and returns list of names with optional
        verbose output.
        
        Returns:
            List of model name strings
        """
        self.refresh_models()
        
        names = self._backend.get_list_model_names()
        if self.verbose:
            for name in names:
                print(f"• {name}")
        if not names:
            print("No Model is currently installed.")
        return names

    def list_models_detailed(self) -> List[Dict[str, Any]]:
        """List all installed models with detailed metadata.
        
        Returns:
            List of dictionaries with keys: name, id, size, modified
        """
        self.refresh_models()
        
        models = self._backend.get_detailed_list_models()
        if self.verbose:
            for m in models:
                print(
                    f"- {m['name']:<20} | {m['size']:<10} | Modified: {m['modified']}"
                )
        return models

    def model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model.
        
        Displays formatted model information including architecture,
        parameters, and metadata.
        
        Args:
            model: Model name to query
            
        Returns:
            Dictionary with model information, None if not found
        """
        info = self._backend.get_model_info(model)

        if not info:
            print(f"\nModel '{model}' not found.")
            return None

        print(f"\n=== 🧠 Model Info: {model} ===")

        for section, data in info.items():
            if section == "model_name":
                continue

            print(f"\n[{section.upper()}]")

            # --- 1) Dictionary case ---
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "items" and isinstance(value, list):
                        print("  • Details:")
                        for line in value:
                            # trim multi-spaces and indent
                            line = " ".join(line.split())
                            print(f"     - {line}")
                    elif isinstance(value, list):
                        print(f"  {key}:")
                        for item in value:
                            print(f"     - {item}")
                    else:
                        print(f"  {key:<5}: {value}")

            # --- 2) List case ---
            elif isinstance(data, list):
                print("  • Items:")
                for idx, item in enumerate(data, start=1):
                    item = " ".join(str(item).split())
                    print(f"     {idx:>2}. {item}")

            # --- 3) Scalar case ---
            else:
                print(f"  • {data}")

        print("\n" + "-" * 50)
        return info

    def check_model_existance(self, model: str) -> str:
        """Check if a model is installed.
        
        Args:
            model: Model name to check
            
        Returns:
            Human-readable status string
        """
        self.refresh_models()
        
        names = self._backend.model_exists(model)
        
        if model:
            return (f"Model '{model}' is installed.")
        else:
            return(f"Model '{model}' is not installed.")

    def pull_model(
        self, model: str, stream: bool = True, mode: PullMode = PullMode.FOREGROUND
    ) -> bool:
        """Download a model from Ollama registry.
        
        Args:
            model: Model name to download
            stream: Stream progress updates (API only)
            mode: Download mode for CLI backend (FOREGROUND or BACKGROUND)
            
        Returns:
            True if download succeeded, False otherwise
        """
        result = (
            self.api.pull_model(model, stream)
            if self.backend_type == OllamaBackend.API
            else self.cmd.pull_model(model, mode)
        )
        if self.verbose:
            print(
                f"{'✅' if result else '❌'} Model '{model}' pulled via {self.backend_type.value}."
            )
        return result

    def pull_model_with_progress(self, model: str) -> bool:
        """Download model with real-time progress display.
        
        Args:
            model: Model name to download
            
        Returns:
            True if download succeeded, False otherwise
            
        Note:
            Progress display only available with CLI backend. 
            API backend falls back to simple pull with stream output.
        """
        # CLI backend supports progress parsing
        if self.backend_type == OllamaBackend.CMD:
            for progress in self.cmd.pull_model_with_progress(model):
                status = progress.get("status", "")
                if status == "downloading":
                    percent = progress.get("percent", 0)
                    size = progress.get("size", "")
                    print(f"\rDownloading {percent:.1f}% ({size})", end="", flush=True)
                elif status in ("completed", "success"):
                    print(f"\n✓ Model '{model}' downloaded successfully.")
                    return True
                elif status in ("failed", "error"):
                    print(f"\n✗ Error: {progress.get('error', 'Unknown issue')}")
                    return False
            return True
        
        # API backend - fallback to simple streaming pull
        else:
            if self.verbose:
                print(f"Pulling model '{model}' via API (no progress available)...")
            return self.api.pull_model(model, stream=True)

    def delete_model(self, model: str, force: bool = False) -> bool:
        """Delete an installed model.
        
        Args:
            model: Model name to delete
            force: Skip existence check if True
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        result = self._backend.delete_model(model, force)
        if self.verbose:
            print(
                f"{'Removed' if result else 'Failed to remove'} model: {model}"
            )
        return result

    def refresh_models(self) -> None:
        """ Refresh cached list of installed models """
        self._backend.refresh_list_of_model_names()
        if self.verbose:
            print("Model list refreshed.")

    def check_api_status(self) -> str:
        """Check if Ollama API is reachable.
        
        Returns:
            Human-readable status string
        """
        status = self.api.check_connection()
        
        if status:
            return "API is reachable."
        else:
            return "API seems to be offline."
        
# Model runtime states
    def list_running_models(self) -> List[Dict[str, Any]]:
        """List currently running models in memory.
        
        Returns:
            List of dictionaries with name, processor, size, until
        """
        self.refresh_running_models()
        models = self._backend.get_list_running_models()
        if self.verbose:
            print("\n=== Running Models ===")
            for m in models:
                print(f"• {m['name']} ({m['processor']} / {m['size']})")
        if not models:
            print("No Model is currently running.")
        return models

    def start_model(self, model: str) -> bool:
        """Load a model into memory for faster generation.
        
        Args:
            model: Model name to start
            
        Returns:
            True if model was loaded successfully
        """
        result = self._backend.start_running_model(model)
        if self.verbose:
            print(
                f"{'✅ Started' if result else '❌ Failed to start'} model '{model}'."
            )
        return result

    def stop_model(self, model: str, force: bool = False) -> bool:
        """Unload a model from memory.
        
        Args:
            model: Model name to stop
            force: Skip running check if True
            
        Returns:
            True if model was stopped successfully
        """
        result = self._backend.stop_running_model(model, force)
        if self.verbose:
            print(
                f"{'✅ Stopped' if result else '❌ Failed to stop'} model '{model}'."
            )
        return result
    
    def refresh_running_models(self) -> None:
        """ Refresh cached list of running models """
        self._backend.refresh_list_of_running_models()
        if self.verbose:
            print("Running Model list refreshed.")

# AI Generation / Cache
    def generate(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> str:
        """Generate text using a model (non-streaming).
        
        Checks cache first if enabled, generates response, then caches it.
        
        Args:
            model: Model name to use
            prompt: Input text prompt
            options: Optional generation parameters (API backend only)
            use_cache: Use cached response if available
            
        Returns:
            Generated text string
        """
        if not model or not prompt:
            return ""

        # use cached response
        if use_cache and self.cache:
            cached = self.cache.get_cached_response(model, prompt)
            if cached:
                if self.verbose:
                    print("\n=== Response (cached) ===\n", cached)
                return cached

        # Generate via backend
        response = (
            self.cmd.generate(model, prompt)
            if self.backend_type == OllamaBackend.CMD
            else self.api.generate(model, prompt, options).get("response", "")
        )

        if response and self.cache and use_cache:
            self.cache.cache_response(model, prompt, response)
        if self.verbose:
            print("\n=== AI Response ===\n", response)
        return response

    def generate_stream(
        self, 
        model: str, 
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        """Generate text with real-time streaming output.
    
    Prints response as it's generated for immediate feedback.
    
    Args:
        model: Model name to use
        prompt: Input text prompt
        options: Optional generation parameters (API backend only)
    """
        if self.backend_type == OllamaBackend.CMD:
            for text in self.cmd.generate_stream(model, prompt):
                print(text, end="")
        else:
            for chunk in self.api.generate_stream(model, prompt, options):
                if "response" in chunk:
                    print(chunk["response"], end="")
        print()

# Service Operations
    def start_service(self) -> bool:
        """Start Ollama service.
        
        Returns:
            True if service started successfully
        """
        result = self.service.start()
        if self.verbose:
            print("Started" if result else "Failed to start service")
        return result

    def stop_service(self) -> bool:
        """Stop Ollama service.
        
        Returns:
            True if service stopped successfully
        """
        result = self.service.stop()
        if self.verbose:
            print("Stopped" if result else "Failed to stop service")
        return result

    def health_check(self) -> Dict[str, Any]:
        """Get comprehensive system health information.
        
        Returns:
            Dictionary with OS, version, installation status, etc.
        """
        info = self.service.get_health_status()
        if self.verbose:
            print("\n=== System Health ===")
            for k, v in info.items():
                print(f"- {k:<20}: {v}")
        return info

    def get_version(self) -> str:
        """Get installed Ollama version.
        
        Returns:
            Version string with message
        """
        return f"Current installed Ollama Version: '{self.service.get_version()}'."

    def get_operating_system(self) -> str:
        """Get current operating system name.
        
        Returns:
            OS name string with message
        """
        return f"Current Operating System: '{self.service.get_os_name()}'."

    def is_process_active(self) -> str:
        """Check if Ollama process is running.
        
        Returns:
            Human-readable status string
        """
        status = self.service.is_running()
        
        if status:
            return "Ollama is currently active."
        else:
            return "Ollama is currently not active."

    def get_api_status(self) -> str:
        """Check if Ollama API endpoint is reachable.
        
        Returns:
            Human-readable status string
        """
        status = self.service.is_api_reachable()
        
        if status:
            return "Ollama API is reachable."
        else:
            return "Ollama API seems to be offline."

    def is_installed(self) -> str:
        """Check if Ollama is installed on the system.
        
        Returns:
            Human-readable status string
        """
        status = self.service.is_installed()
        
        if status:
            return "Ollama is installed."
        else:
            return "Ollama is not installed or in PATH."

    def get_installation_path(self) -> str:
        """Get path where Ollama is installed.
        
        Returns:
            Installation path string with message
        """
        return f"Ollama installed Path: '{self.service.get_installation_path()}'"

# Helpers & Utility
    def validate_model_name(self, name: str) -> bool:
        """Validate model name for filesystem compatibility.
        
        Checks that model name is non-empty and doesn't contain invalid
        filesystem characters (< > " | ? *).
        
        Args:
            name: Model name to validate
            
        Returns:
            True if valid, False otherwise
        """
        valid = self.helpers.validate_model_name(name)
        if self.verbose:
            print(f"Model name '{name}' is valid.")
        return valid

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text using ~4 chars per token heuristic.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count (minimum 1 for non-empty text)
        """
        count = self.helpers.estimate_tokens(text)
        if self.verbose:
            print(f"Estimated tokens: {count}")
        return count

    def check_homebrew_installed(self) -> str:
        """Check if Homebrew package manager is installed.
        
        Returns:
            Human-readable status string
        """
        installed = self.helpers._is_homebrew_installed()
        
        if installed:
            return "Homebrew is installed on system."
        else:
            return "Homebrew not found."

    def check_winget_installed(self) -> str:
        """Check if Windows Package Manager (winget) is installed.
        
        Returns:
            Human-readable status string
        """
        installed = self.helpers._is_winget_installed()
        
        if installed:
            return "Winget is installed on system."
        else:
            return "Winget not found."

    def check_chocolatey_installed(self) -> str:
        """Check if Chocolatey package manager is installed.
        
        Returns:
            Human-readable status string
        """
        installed = self.helpers._is_chocolatey_installed()
        
        if installed:
            return "Chocolatey is installed on system."
        else:
            return "Chocolatey not found."

    def try_installing_via_homebrew(self) -> str:
        """Attempt to install Ollama using Homebrew.
        
        Requires Homebrew to be installed on the system.
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._try_brew_install()
        
        if installed:
            return "Ollama was successfully installed via Homebrew."
        else:
            return "Error: While installing Ollama via Homebrew."

    def try_installing_via_curl(self) -> str:
        """Attempt to install Ollama using curl installation script.
        
        Downloads and executes official Ollama installation script.
        Works on macOS and Linux.
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._try_curl_install()
        
        if installed:
            return "Ollama was successfully installed via Curl."
        else:
            return "Error: While installing Ollama via Curl."

    def try_installing_via_winget(self) -> str:
        """Attempt to install Ollama using Windows Package Manager.
        
        Requires Windows 10/11 with winget installed.
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._try_winget_install()
        
        if installed:
            return "Ollama was successfully installed via Winget."
        else:
            return "Error: While installing Ollama via Winget."

    def try_installing_via_choco(self) -> str:
        """Attempt to install Ollama using Chocolatey.
        
        Requires Chocolatey to be installed on Windows.
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._try_choco_install()
        
        if installed:
            return "Ollama was successfully installed via Chocolatey."
        else:
            return "Error: While installing Ollama via Chocolatey."

    def try_installing_direct_on_windows_only(self) -> str:
        """Attempt to install Ollama by direct download on Windows.
        
        Downloads OllamaSetup.exe and runs silent installation.
        Falls back method when package managers are unavailable.
        
        Returns:
            Success or error message string
            
        Warning:
            Downloads executable from internet and runs with elevated privileges.
            Only use on trusted networks.
        """
        installed = self.helpers._try_direct_download_install_windows_only()
        
        if installed:
            return "Ollama successfully installed."
        else:
            return "Error: While installing Ollama."

    def show_manual_installation_instruction(self) -> None:
        """Display platform-specific manual installation instructions.
        
        Shows formatted instructions for installing Ollama manually when
        automatic installation fails or is unavailable.
        """
        self.helpers._show_manual_install_instructions()

    def install_on_macos(self) -> str:
        """Install Ollama on macOS using available methods.
        
        Tries installation in order:
        1. Homebrew (if installed)
        2. curl script (official method)
        3. Shows manual instructions
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._install_macos()
        
        if installed:
            return "Ollama successfully installed on MacOS."
        else:
            return "Error: While installing Ollama on MacOS."

    def install_on_linux(self) -> str:
        """Install Ollama on Linux using available methods.
        
        Tries installation in order:
        1. Homebrew (if installed, e.g., Linuxbrew)
        2. curl script (official method)
        3. Shows manual instructions
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._install_linux()
        
        if installed:
            return "Ollama successfully installed on Linux."
        else:
            return "Error: While installing Ollama on Linux."

    def install_on_windows(self) -> str:
        """Install Ollama on Windows using available methods.
        
        Tries installation in order:
        1. Windows Package Manager (winget)
        2. Chocolatey
        3. Direct download and silent installation
        4. Shows manual instructions
        
        Returns:
            Success or error message string
        """
        installed = self.helpers._install_windows()
        
        if installed:
            return "Ollama successfully installed on Windows."
        else:
            return "Error: While installing Ollama on Windows."

    def search_models(self, model: str, models: List[str]) -> str:
        """Search for models matching query string.
        
        Performs case-insensitive substring search through model list.
        
        Args:
            model: Search query string
            models: List of model names to search through
            
        Returns:
            List of matching model names (empty if none found)
        """
        status = self.helpers.search_models(model, models)
        
        if status:
            return f"Model '{model}' is installed."
        else:
            return f"Model '{model}' is not installed."

# Conversation Handling
    def start_conversation(
        self,
        model: str,
        system_message: Optional[str] = None,
        max_history: int = 20,
    ) -> ConversationManager:
        """Start a new multi-turn conversation.
        
        Args:
            model: Model name to use for conversation
            system_message: Optional system instructions
            max_history: Maximum messages to keep in context
            
        Returns:
            ConversationManager instance
        """
        conv = ConversationManager(
            model=model, 
            system_message=system_message, 
            max_history=max_history
        )
        if self.verbose:
            print(f"New conversation started for model '{model}'")
        return conv

    def chat(
        self, 
        conversation: ConversationManager, 
        message: str, 
        stream: bool = False
    ) -> str:
        """Send a message in an ongoing conversation.
        
        Args:
            conversation: ConversationManager instance
            message: User's message
            stream: Whether to stream response (not implemented)
            
        Returns:
            Assistant's response
        """
        conversation.add_user_message(message)
        prompt = conversation.build_prompt(message)
        response = self.generate(conversation.conversation.model, prompt)
        conversation.add_assistant_message(response)
        return response

    def chat_with_context(
        self,
        conversation: ConversationManager,
        user_message: str,
        stream: bool = False, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send message in conversation context with streaming support.
        
        Args:
            conversation: ConversationManager instance
            user_message: User's message
            stream: Whether to stream response
            
        Returns:
            Assistant's complete response
        """
        # add user message to conversation
        conversation.add_user_message(user_message)
        
        # build prompt with context
        prompt = conversation.build_prompt(user_message)
        
        # generate response
        if stream:
            print("Assistant: ", end='', flush=True)
            response_parts = []
            
            if self.backend_type == OllamaBackend.API:
                for chunk in self.api.generate_stream(conversation.conversation.model, prompt, options):
                    if 'response' in chunk:
                        text = chunk['response']
                        print(text, end='', flush=True)
                        response_parts.append(text)
            else:
                for text in self.cmd.generate_stream(conversation.conversation.model, prompt):
                    print(text, end='', flush=True)
                    response_parts.append(text)
            
            print()
            response = ''.join(response_parts)
        else:
            if self.backend_type == OllamaBackend.API:
                result = self.api.generate(conversation.conversation.model, prompt)
                response = result.get('response', '') if result else ''
            else:
                response = self.cmd.generate(conversation.conversation.model, prompt) or ''
        
        # add assistant response to conversation
        conversation.add_assistant_message(response)
        
        return response

    def show_conversation_info(self, conversation: ConversationManager) -> None:
        """Display formatted conversation statistics.
        
        Args:
            conversation: ConversationManager instance
        """
        info = conversation.get_conversation_info()
        
        print("\n=== Conversation Info ===")
        print(f"Title: {info['title']}")
        print(f"Model: {info['model']}")
        print(f"Total messages: {info['message_count']}")
        print(f"  - User: {info['user_messages']}")
        print(f"  - Assistant: {info['assistant_messages']}")
        print(f"  - System: {info['system_messages']}")
        print(f"Estimated tokens: {info['estimated_tokens']}")
        print(f"Created: {info['created_at']}")
        print()

    def save_conversation(
        self,
        conversation: ConversationManager,
        filepath: str
    ) -> None:
        """Save conversation to JSON file.
        
        Args:
            conversation: ConversationManager instance
            filepath: Path to save file
        """
        from pathlib import Path
        conversation.save_to_file(Path(filepath))
        print(f"Conversation saved to: {filepath}")

    def load_conversation(self, filepath: str, model: str) -> ConversationManager:
        """Load conversation from JSON file.
        
        Args:
            filepath: Path to load file
            model: Model to use for loaded conversation
            
        Returns:
            ConversationManager instance
        """
        from pathlib import Path
        conversation = ConversationManager(model=model)
        conversation.load_from_file(Path(filepath))
        print(f"Conversation loaded from: {filepath}")
        return conversation

    def export_conversation_markdown(
        self,
        conversation: ConversationManager,
        filepath: str
    ) -> None:
        """Export conversation to Markdown format.
        
        Args:
            conversation: ConversationManager instance
            filepath: Path to save file
        """
        from pathlib import Path
        conversation.export_to_markdown(Path(filepath))
        print(f"Conversation exported to Markdown: {filepath}")

# Cache Tools
    def cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats, None if cache disabled
        """
        if not self.cache:
            print("Cache is disabled.")
            return None
        
        stats = self.cache.get_stats()
        if self.verbose:
            print("\n=== Cache Stats ===")
            for k, v in stats.items():
                print(f"- {k:<20}: {v}")
        return stats

    def clear_cache(self) -> None:
        """ Clear all cache entries """
        if self.cache:
            deleted = self.cache.clear()
            print(f"Cleared {deleted} cache entries.")

    def clear_expired_cache(self) -> None:
        """ Clear only expired cache entries """
        if not self.cache:
            print("Cache is disabled.")
            return
        
        count = self.cache.clear_expired()
        print(f"Cleared {count} expired cache entries.")

    def export_cache_info(self, filepath: str = "cache_info.json") -> None:
        """Export cache metadata to JSON file.
        
        Args:
            filepath: Path to save cache info (default: 'cache_info.json')
        """
        if not self.cache:
            print("Cache is disabled.")
            return
        
        from pathlib import Path
        self.cache.export_to_json(Path(filepath))
        print(f"Cache info exported to: {filepath}")

# Configuration Access
    def get_api_host(self) -> str:
        """Get configured API host.
        
        Returns:
            Host string (e.g., 'localhost')
        """
        return self.config.get_host()

    def get_api_port(self) -> int:
        """Get configured API port.
        
        Returns:
            Port number (e.g., 11434)
        """
        return self.config.get_port()

    def set_api_host(self, host: str) -> None:
        """Set API host.
        
        Args:
            host: Hostname or IP address
        """
        self.config.set_host(host)

    def set_api_port(self, port: int) -> None:
        """Set API port.
        
        Args:
            port: Port number
        """
        self.config.set_port(port)

    def base_url(self) -> str:
        """Get current API base URL.
        
        Returns:
            Base URL string (e.g., 'http://localhost:11434')
        """
        return self.config.get_base_url

# Static Convenience
    @classmethod
    def from_config_file(cls, path: str, backend: OllamaBackend = OllamaBackend.API) -> "OllamaManager":
        """Create manager from JSON configuration file.
        
        Args:
            path: Path to JSON config file
            backend: Backend to use (default: API)
            
        Returns:
            OllamaManager instance with loaded configuration
        """
        cfg = Config.load_from_json(path)
        return cls(config=cfg, backend=backend)
