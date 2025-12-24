# src/ollama_manager_usage_example.py

from ollama_manager import (
    OllamaManager, 
    OllamaBackend,
)

import logging


example_model = "llama3.2:3b"
example_prompt = "Explain Python"

# === Setup Manager Class
# Setup Standard 
# - backend is using API version
# - Host for Ollama API is is localhost
# - Port for Ollama API is is 11434
manager = OllamaManager()

# Setup Custom Manager
# - backend is using CMD version
# - Host for Ollama API is 127.1.1.1
# - Port for Ollama API is 12345
custom_manager = OllamaManager(OllamaBackend.CMD, "127.1.1.1", 12345)

# === Functionality for CMD & API
# Get information of installed models
manager.get_list_of_models()
manager.get_list_of_models_detailed()
manager.get_information_for_model(example_model)

# Loading new models
manager.load_new_model(example_model)
manager.load_new_model_with_progress(example_model)

# Simple call
success = manager.load_new_model_with_progress(example_model)
if success:
    print("Ready to use!")

# Oder direkter Zugriff auf Generator: Direkter Zugriff für Custom UI
for progress in manager.cmd.pull_model_with_progress("llama3.2:3b"):
    print(f"{progress}")  # Raw progress data
    
    if progress.get('status') == 'completed':
        print("Ready to use!")
        break

# Removing model
manager.remove_model(example_model)

# Check if model exists (installed)
manager.check_if_model_exists(example_model)

# Get running models
manager.get_all_running_models()
manager.get_only_names_of_all_running_models()

# Start and stop running model
manager.stop_running_model(example_model)
manager.start_running_model(example_model)

# Get response from AI
# Normal generation
print("Assistant: ", end='', flush=True)
manager.generate_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()

# Streaming generation
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()

# Reload installed models
manager.refresh_list_of_models()
manager.refresh_list_of_all_running_models()

# === API Only
# Check if API connection is ready
manager.check_api_connection()

# Get and set API -URL -HOST -PORT
manager.get_api_url("/")
manager.get_api_host()
manager.set_api_host("new_host")
manager.get_api_url()
manager.set_api_port(1)
manager.get_api_port()
manager.get_api_base_url()

# === Ollama Service
# Get currently installed Ollama Version
manager.get_version()

# Get Operating System of current system
manager.get_operating_system()

# Check if Ollama is running and API is ready to use
manager.get_is_process_running()
manager.get_api_status()

# Check if Ollama is installed and its Path
manager.get_is_installed()
manager.get_installation_path()

# Start and stop Ollama process
manager.start_ollama()
manager.stop_ollama()

# Check if Ollama is ready
manager.health_check()

# === Setup Logging
# Default setup
manager.setup_logging_default()

# Debug mode
manager.setup_logging_debug()

# Production mode (file only)
manager.setup_logging_file_only()

# Quiet mode
manager.setup_logging_quiet()

# Verbose mode
manager.setup_logging_verbose()

# Custom configuration
manager.setup_logging_custom(
    level=logging.DEBUG,
    log_file="logs/my_app.log",
    console=True
)

# Disable logging completly
manager.disable_logging()

# Check current config
manager.get_logging_status()

# Working with logger
manager.get_logger()
manager.get_logger().info("Hello")  # Auto-init on first call

# === Ollama Helper
## MacOS and Linux: Check if downloaded and download Tools/ Ollama
manager.check_if_homebrew_is_installed()
manager.try_installing_homebrew()
manager.try_installing_curl()
manager.install_on_macos()
manager.install_on_linux()

## Windows: Check if downloaded and download Tools/ Ollama
manager.check_if_winget_is_installed()
manager.check_if_chocolatey_is_installed()
manager.try_installing_winget()
manager.try_installing_choco()
manager.try_installing_direct_on_windows_only()
manager.install_on_windows()

# Show manual guide to install Ollama
manager.show_manual_installation_instruction()

# Check if given name is a valid model name
manager.validate_name_is_correct_for_model("llama3.2:3b")

# Estimate the tokens for given prompt
manager.estimate_prompt_tokenizer("Tokenizer tokenizer tokenssss 123")

# Search if model is in installed model list
manager.search_models("llama3.2:1b", ["list of all models here", "llama3.2:1b"])
