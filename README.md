# AI-Plugin-Collection [English]

![Banner (created by ChatGPT)](<pictures/Banner (created by ChatGPT).png>)

A comprehensive Python plugin for managing and controlling Ollama via API and CLI. This plugin provides a unified interface for model management, service control, and AI generation.

## Language / Sprache

- 🇬🇧 English (this file)
- 🇩🇪 [Deutsch](README.de.md)

## Features

- **Dual Backend Support**: Control via Ollama API or CLI
- **Model Management**: List, load, delete, and monitor models
- **Service Control**: Start, stop, and monitor Ollama service
- **AI Generation**: Text generation with and without streaming
- **Cross-Platform**: Support for Windows, macOS, and Linux
- **Installation Helper**: Automatic installation of Ollama on various platforms
- **Logging System**: Flexible logging with various configuration options

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Usage](#usage)
   - [Manager Setup](#manager-setup)
   - [Model Management](#model-management)
   - [Running Models](#running-models)
   - [AI Text Generation](#ai-text-generation)
   - [Service Management](#service-management)
   - [API-specific Functions](#api-specific-functions)
   - [Logging Configuration](#logging-configuration)
   - [Installation Helper](#installation-helper)
   - [Utility Functions](#utility-functions)
4. [Architecture](#architecture)
5. [Backend Comparison](#backend-comparison)
6. [Best Practices](#best-practices)
7. [Example Workflow](#example-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Contributors](#contributors)
10. [License](#license)
11. [Supported Platforms](#supported-platforms)

## Installation

### Prerequisites

- Python 3.8+
- Ollama must be installed (or use the helper functions for installation)

### Install Dependencies

```
pip install -r requirements.txt
```

Or directly:

```
pip install psutil requests
```

Required packages:

- `psutil` - For process management
- `requests` - For HTTP requests to Ollama API

## Quick Start

See also [example file](ollama_manager_usage_example.py) for more examples.

```
from ollama_manager import OllamaManager, OllamaBackend

# Initialize manager (default: API backend)
manager = OllamaManager()

# Load model
manager.load_new_model("llama3.2:3b")

# Generate text
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()
```

## Usage

### Manager Setup

```
# Standard setup (API backend, localhost:11434)
manager = OllamaManager()

# Custom setup (CLI backend, custom host/port)
custom_manager = OllamaManager(
    backend=OllamaBackend.CMD,
    host="127.0.0.1",
    port=12345
)
```

### Model Management

```
# List available models
models = manager.get_list_of_models()
detailed = manager.get_list_of_models_detailed()

# Get model information
info = manager.get_information_for_model("llama3.2:3b")

# Load new model
success = manager.load_new_model("llama3.2:3b")

# Load model with progress
for progress in manager.load_new_model_with_progress("llama3.2:3b"):
    print(f"{progress}")
    if progress.get('status') == 'completed':
        print("Ready to use!")
        break

# Remove model
manager.remove_model("llama3.2:3b")

# Check if model exists
exists = manager.check_if_model_exists("llama3.2:3b")
```

### Running Models

```
# Show running models
running = manager.get_all_running_models()
names = manager.get_only_names_of_all_running_models()

# Start model
manager.start_running_model("llama3.2:3b")

# Stop model
manager.stop_running_model("llama3.2:3b")

# Refresh lists
manager.refresh_list_of_models()
manager.refresh_list_of_all_running_models()
```

### AI Text Generation

```
# Simple generation (non-streamed)
response = manager.generate_response(
    model="llama3.2:3b",
    prompt="Explain Python in simple terms"
)

# Streaming generation
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()
```

### Service Management

```
# Get Ollama version
version = manager.get_version()

# Check operating system
os_name = manager.get_operating_system()

# Check status
is_installed = manager.get_is_installed()
is_running = manager.get_is_process_running()
api_ready = manager.get_api_status()

# Installation path
path = manager.get_installation_path()

# Start/stop service
manager.start_ollama()
manager.stop_ollama()

# Health check
status = manager.health_check()
```

### API-specific Functions

```
# Check API connection
manager.check_api_connection()

# API configuration
url = manager.get_api_url("/endpoint")
host = manager.get_api_host()
manager.set_api_host("new_host")

port = manager.get_api_port()
manager.set_api_port(11434)

base_url = manager.get_api_base_url()
```

### Logging Configuration

```
# Standard setup
manager.setup_logging_default()

# Debug mode
manager.setup_logging_debug()

# File logging only
manager.setup_logging_file_only()

# Quiet mode
manager.setup_logging_quiet()

# Verbose mode
manager.setup_logging_verbose()

# Custom configuration
import logging
manager.setup_logging_custom(
    level=logging.DEBUG,
    log_file="logs/my_app.log",
    console=True
)

# Disable logging
manager.disable_logging()

# Get status
status = manager.get_logging_status()

# Use logger
logger = manager.get_logger()
logger.info("Application started")
```

### Installation Helper

```
# macOS installation
manager.check_if_homebrew_is_installed()
manager.try_installing_homebrew()
manager.install_on_macos()

# Linux installation
manager.try_installing_curl()
manager.install_on_linux()

# Windows installation
manager.check_if_winget_is_installed()
manager.check_if_chocolatey_is_installed()
manager.try_installing_winget()
manager.try_installing_choco()
manager.try_installing_direct_on_windows_only()
manager.install_on_windows()

# Show manual instructions
manager.show_manual_installation_instruction()
```

### Utility Functions

```
# Validate model name
is_valid = manager.validate_name_is_correct_for_model("llama3.2:3b")

# Estimate tokens
token_count = manager.estimate_prompt_tokenizer("Your prompt text here")

# Search models
models_list = manager.get_list_of_models()
results = manager.search_models("llama", models_list)
```

## Architecture

The plugin consists of several specialized components:

### OllamaManager

Main interface that unifies all functions and supports two backend modes.

### OllamaAPIManager

Communication with Ollama via REST API with the following endpoints:

- `/api/tags` - List models
- `/api/show` - Model information
- `/api/pull` - Download models
- `/api/delete` - Delete models
- `/api/generate` - Generate text
- `/api/ps` - Running models

### OllamaCMDManager

Control via CLI commands:

- `ollama list` - List models
- `ollama show` - Model details
- `ollama pull` - Load models
- `ollama rm` - Delete models
- `ollama run` - Generate text
- `ollama ps` - Running models
- `ollama stop` - Stop model

### OllamaService

Service management for:

- Installation check
- Process monitoring
- API reachability
- Service start/stop
- Version information

### OllamaHelper

Helper functions for:

- Platform-specific installation
- Package manager integration
- Model name validation
- Token estimation
- Model search

## Backend Comparison

| Feature | API Backend | CMD Backend |
|---------|------------|-------------|
| Performance | ⚡ Faster | ⏱️ Slower |
| Streaming | ✅ Native | ✅ Line-based |
| Progress Info | ✅ Detailed | ⚠️ Parsing required |
| Parameter Control | ✅ Full | ❌ Limited |
| Dependencies | requests | subprocess |

## Best Practices

- Use **API backend** for performance-critical applications
- Use **CMD backend** when API is not available
- Use `generate_streamed_response()` for interactive UIs
- Enable logging during development with `setup_logging_debug()`
- Check `health_check()` before important operations
- Use `pull_model_with_progress()` for better user experience

## Example Workflow

```
from ollama_manager import OllamaManager

# Setup
manager = OllamaManager()
manager.setup_logging_default()

# Health check
if not manager.health_check():
    print("Ollama is not running. Starting...")
    manager.start_ollama()

# Prepare model
model = "llama3.2:3b"
if not manager.check_if_model_exists(model):
    print(f"Downloading {model}...")
    manager.load_new_model(model)

# Use model
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model=model,
    prompt="Hello! How are you?"
)
print("\n")

# Cleanup
manager.stop_running_model(model)
```

## Troubleshooting

### Ollama won't start

```
# Check installation
if not manager.get_is_installed():
    manager.install_on_macos()  # or install_on_linux() / install_on_windows()

# Check status
status = manager.health_check()
print(status)
```

### API not reachable

```
# Check host and port
print(manager.get_api_host())
print(manager.get_api_port())

# Set custom values
manager.set_api_host("127.0.0.1")
manager.set_api_port(11434)
```

### Model won't load

```
# Check if model exists
exists = manager.check_if_model_exists("model-name")

# Validate name
is_valid = manager.validate_name_is_correct_for_model("model-name")
```

## Contributors

![created-by](pictures/created-by.svg)

## License

This project is open source. Please note Ollama's license terms.

## Supported Platforms

- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)
- ✅ Windows 10/11