# src/main.py

'''
Ollama Manager Demonstration and Test Suite
  This script demonstrates all the functionalities of the OllamaManager plugin.

- Initializes Manager with API or CLI backend
- Checks system health and service status
- Lists models and displays detailed information
- Generates text with caching demonstration
- Performs multi-turn conversations
- Manages cache and exports statistics
- Demonstrates backend switching between API and CLI
- Shows helper functions for installation and validation
- Tests conversation persistence and export functions
'''

from modules.plugin_manager import OllamaManager, OllamaBackend


def main() -> None:
    print("=== Ollama Unified Manager Demo ===\n")

    # ------------------------------------------------------
    # 1️⃣ Initialization
    # ------------------------------------------------------
    manager = OllamaManager(
        backend=OllamaBackend.API,
        enable_cache=True,
        verbose=True,
    )

    print(f"\n✅ Manager initialized using backend: {manager.get_backend_type().value}\n")

    # ------------------------------------------------------
    # 2️⃣ Health & Service
    # ------------------------------------------------------
    print("\n---- System Health ----")
    manager.health_check()

    # Start Ollama if it's not running
    print("\nChecking service state ...")
    if not manager.service.is_running():
        print("> Ollama service not running. Starting...")
        manager.start_service()
    else:
        print("> Ollama service already running.")

    # ------------------------------------------------------
    # 3️⃣ Models
    # ------------------------------------------------------
    print("\n---- Model Overview ----")
    models = manager.list_models()
    print(f"\nTotal models: {len(models)}")

    print("\n---- Detailed Model List ----")
    manager.list_models_detailed()

    if models:
        model = models[0]
        print(f"\nFetching information for first model: {model}")
        manager.model_info(model)

    # ------------------------------------------------------
    # 4️⃣ AI Response Generation
    # ------------------------------------------------------
    model_name = manager.config.default_model
    print(f"\nGenerating response for model '{model_name}' ...")
    manager.generate(model_name, "Explain recursion in one simple sentence.")
    print("\nRe-running to demonstrate cache:")
    manager.generate(model_name, "Explain recursion in one simple sentence.")

    # ------------------------------------------------------
    # 5️⃣ Conversation Example
    # ------------------------------------------------------
    print("\n---- Conversation Example ----")
    conv = manager.start_conversation(model=model_name, system_message="You are an assistant for code explanation.")

    manager.chat(conv, "What are Python decorators?")
    manager.chat(conv, "Give a simple function example using one.")

    print("\nConversation Info:")
    print(conv.get_conversation_info())

    # ------------------------------------------------------
    # 6️⃣ Cache & Utilities
    # ------------------------------------------------------
    print("\n---- Cache Stats ----")
    manager.cache_stats()

    print("\nClearing expired cache ...")
    if manager.cache:
        manager.cache.clear_expired()

    # ------------------------------------------------------
    # 7️⃣ Helpers
    # ------------------------------------------------------
    print("\n---- Helper Utilities ----")
    manager.validate_model_name("llama3.2:3b")
    manager.estimate_tokens("This is a quick test to estimate token count.")

    # ------------------------------------------------------
    # 8️⃣ Backend Switching (API ↔ CMD)
    # ------------------------------------------------------
    print("\n---- Switching Backend ----")
    manager.switch_backend(OllamaBackend.CMD)
    print(f"Current backend: {manager.get_backend_type().value}")

    print("\n---- CMD Models (if CLI accessible) ----")
    manager.list_models()

    # ------------------------------------------------------
    # ✅ Completed
    # ------------------------------------------------------
    print("\n✅ All demonstrations completed successfully!\n")


if __name__ == "__main__":
    #main()
    
# Backend control
    manager = OllamaManager()
    print(manager.get_backend_type())
    manager.switch_backend(mode=OllamaBackend.API)
    manager.switch_backend(mode=OllamaBackend.CMD)
    print(manager.get_backend_type())

# Core model operations
    models = manager.list_models()
    manager.list_models_detailed()
    manager.model_info("gemma3:4b")
    print(manager.check_model_existance("gemma3:4b"))
    # manager.pull_model("gemma3:4b")
    # manager.pull_model_with_progress("gemma3:4b")
    # manager.delete_model("gemma3:4b")
    manager.refresh_models()
    print(manager.check_api_status())
    
# Model runtime states
    manager.list_running_models()
    # manager.start_model("gemma3:4b")
    # manager.stop_model("gemma3:4b")
    manager.refresh_running_models()

# AI Generation
    # manager.generate("gemma3:4b", "Explain Python.")
    # manager.generate_stream("gemma3:4b", "Explain Python.")

# Service Operations
    # manager.start_service()
    # manager.stop_service()
    print(manager.health_check())
    print(manager.get_version())
    print(manager.get_operating_system())
    print(manager.is_process_active())
    print(manager.get_api_status())
    print(manager.is_installed())
    print(manager.get_installation_path())

# Helpers & Utility
    manager.validate_model_name("gemma")
    manager.estimate_tokens("text text text 123 34 @@@@@")
    print(manager.check_homebrew_installed())
    print(manager.check_winget_installed())
    print(manager.check_chocolatey_installed())
    # print(manager.try_installing_homebrew())
    # print(manager.try_installing_curl())
    # print(manager.try_installing_winget())
    # print(manager.try_installing_choco())
    # print(manager.try_installing_direct_on_windows_only())
    manager.show_manual_installation_instruction()
    # print(manager.install_on_macos())
    # print(manager.install_on_linux())
    # print(manager.install_on_windows())
    manager.search_models("gemma3:4b", models)
    
# Conversation Handling
    conv = manager.start_conversation("gemma3:4b")
    # manager.chat(conv, "Hello Boi")
    manager.chat_with_context(conv, "Hello Boi")
    manager.show_conversation_info(conv)
    # manager.save_conversation(conv, "/Users/beri/Documents/GitHub/--local/AI-Plugin-Collection/ignore/")
    # manager.load_conversation("/Users/beri/Documents/GitHub/--local/AI-Plugin-Collection/ignore/", "gemma3:4b")
    manager.export_conversation_markdown(conv, "/Users/beri/Documents/GitHub/--local/AI-Plugin-Collection/ignore/info.md")

# Cache Tools
    manager.cache_stats()
    manager.clear_cache()
    manager.clear_expired_cache()
    manager.export_cache_info()

# Configuration Access
    print(manager.get_api_host())
    print(manager.get_api_port())
    # manager.set_api_host("localhost")
    # manager.set_api_port(11434)
    print(manager.base_url())
    try:
        manager = OllamaManager.from_config_file("config.json")
    except FileNotFoundError:
        print("⚠️ Config file not found — using default configuration.")
        manager = OllamaManager()

    print(manager.get_api_port())
