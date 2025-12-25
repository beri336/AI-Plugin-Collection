# AI Plugin Collection [English]

![Banner (created by ChatGPT)](<docs/pictures/Banner (created by ChatGPT).png>)

A comprehensive Python plugin for managing and controlling Ollama via API and CLI. This plugin provides a unified interface for model management, service control, and AI generation.

## 🌐 Language / Sprache

- 🇬🇧 English (this file)
- 🇩🇪 [Deutsch](docs/README.de.md)

<br>

## ⚡ Key Features

- **Dual Backend:** Seamless switch between API or CLI command execution
- **Unified Manager:** One interface (`OllamaManager`) controlling all subsystems
- **Model Management:** List, pull, delete and inspect models
- **AI Generation:** Text generation (streamed or cached)
- **Service Control:** Start/stop and perform system health checks
- **Cache Integration:** Optional caching layer for repeated prompts
- **Conversation Management:** Maintain contextual chat sessions
- **Helper Tools:** Platform installation, model validation, token estimation
- **Config Loader:** Load settings directly from JSON config files
- **Cross‑Platform:** Works on macOS, Linux and Windows

<br>

## 📚 Table of Contents

1. [Installation](#-installation)
    - [Prerequisites](#-prerequisites)
    - [Install Dependencies](#-install-dependencies)
2. [Quick Start](#-quick-start)
3. [Usage](#-usage)
   - [Setup & Configuration](#️-setup--configuration)
   - [Model Management](#-model-management)
   - [Running Models](#-running-models)
   - [AI Generation](#-ai-generation)
   - [Conversation Example](#-conversation-example)
   - [Service Management](#-service-management)
   - [Helper Tools](#️-helper-tools)
   - [Cache](#-cache)
   - [Backend Control](#-backend-control)
4. [Architecture Overview](#-architecture-overview)
5. [Backend Comparison](#️-backend-comparison)
6. [Best Practices](#-best-practices)
7. [License](#-license)
8. [Contributors](#-contributors)
9. [Troubleshooting](#-troubleshooting)
10. [Supported Platforms](#-supported-platforms)

<hr><br>

## 🧩 Installation

### 🧱 Prerequisites

- Python 3.8+
- Ollama must be installed (or use the helper functions for installation)

### 📦 Install Dependencies

Locally or in a virtual environment:

```bash
pip install -r requirements.txt
```

Or directly:

```bash
pip install psutil requests pytest pytest-cov
```

Required packages:

| Package    | Purpose / Description                                                 |
| ---------- | --------------------------------------------------------------------  |
| psutil     | Process and system management (e.g., to check whether Ollama is running) |
| requests   | HTTP client for calling the Ollama API                             |
| pytest     | Framework for unit and integration testing                           |
| pytest‑cov | Extension for measuring test coverage                           |

### 🧪 Run Tests

For complete tests (including decorators, caching, helpers, etc.):

```bash
pytest -v
```

Run a specific test:
```bash
pytest tests/test_service_manager.py
```

With **coverage report**:

```bash
pytest --cov=src --cov-report=term-missing
```

Optional detailed reports (HTML in the `htmlcov/` folder):

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # or `start htmlcov/index.html` on Windows
```

<hr><br>

## 🚀 Quick Start

See also [example file](src/main.py) for a full demonstration.

```py
from modules.plugin_manager import OllamaManager

# Initialize with API backend (default)
manager = OllamaManager()

# Run health check
manager.health_check()

# List models
models = manager.list_models()

# Generate text
manager.generate("llama3.2:3b", "Explain object‑oriented programming.")
```

<hr><br>

## 💡 Usage

### ⚙️ Setup & Configuration

#### 🗂️ From JSON Config

```py
manager = OllamaManager.from_config_file("config.json", backend=OllamaBackend.API)
```

Config file example:

```json
{
  "host": "localhost",
  "port": 11434,
  "default_model": "llama3.2:3b"
}
```

<br>

### 🤖 Model Management

```py
# List models
manager.list_models()

# Detailed list
manager.list_models_detailed()

# Model info
manager.model_info("llama3.2:3b")

# Pull and delete
manager.pull_model("llama3.2:3b")
manager.delete_model("llama3.2:3b")
```

<br>

### 🟢 Running Models

```py
# Show running models
manager.list_running_models()

# Start / stop model
manager.start_model("llama3.2:3b")
manager.stop_model("llama3.2:3b")

# Refresh lists
manager.refresh_running_models()
```

<br>

### 🧠 AI Generation

```py
# Generate once
manager.generate("gemma3:4b", "Explain Python.")

# Cached call (faster second time)
manager.generate("llama3.2:3b", "Explain Python classes.", use_cache=True)

# Stream output
manager.generate_stream("llama3.2:3b", "Write a short poem about programming.")
```

<br>

### 💬 Conversation Example

```py
conv = manager.start_conversation(
    "llama3.2:3b",
    system_message="You are a friendly assistant."
)
manager.chat(conv, "What is recursion?")
manager.chat(conv, "Give me an example in Python.")
```

<br>

### 🧩 Service Management

```py
# Get Ollama version
print(manager.get_version())

# Check operating system
print(manager.get_operating_system())

# Check status
is_installed = manager.is_installed()
print(is_installed)
is_running = manager.is_process_active()
print(is_running)
api_ready = manager.get_api_status()
print(api_ready)

# Installation path
path = manager.get_installation_path()
print(path)

# Start/stop service
manager.start_service()
manager.stop_service()

# Health check
status = manager.health_check()
print(status)
```

<br>

### 🛠️ Helper Tools

```py
manager.validate_model_name("llama3.2:3b")
manager.estimate_tokens("Sample prompt text")

# macOS installation
manager.check_homebrew_installed()
manager.try_installing_homebrew()
manager.install_on_macos()

# Linux installation
manager.try_installing_curl()
manager.install_on_linux()

# Windows installation
manager.check_winget_installed()
manager.check_chocolatey_installed()
manager.try_installing_winget()
manager.try_installing_choco()
manager.try_installing_direct_on_windows_only()
manager.install_on_windows()

# Show manual instructions
manager.show_manual_installation_instruction()
```

<br>

### 🧮 Cache

```py
manager.cache_stats()
manager.clear_expired_cache()
manager.export_cache_info()
```

<br>

### 🔀 Backend Control

```py
# Switch between API and CMD
manager.switch_backend(mode=OllamaBackend.API)
manager.switch_backend(mode=OllamaBackend.CMD)
print(manager.get_backend_type())
```

<hr><br>

## 🧭 Architecture Overview

### 🧩 Module
```bash
modules/
├── api_manager.py              # REST API interactions
├── cmd_manager.py              # CLI commands
├── conversation_manager.py     # Contextual conversation system
├── plugin_manager.py           # Unified OllamaManager facade
└── service_manager.py          # Process & service control
```

### 🧠 Core
```bash
modules/
├── cache_manager.py            # Cache system
├── decorators.py               # Decorators & validation
└── helpers.py                  # OS utilities & installers
```

### ⚙️ Config
```bash
modules/
└── settings.py                 # All modifiable settings
```

### ⚙️ Tests
```bash
tests/
├── test_api_manager.py             # Tests for REST API calls
├── test_cache_manager.py           # Checks cache system and SQLite logic
├── test_cmd_manager.py             # CLI commands and parameter parsing
├── test_conversation_manager.py    # Context management and conversation flow
├── test_decorators.py              # All decorator and validation functions
├── test_helpers.py                 # Installation routines, Brew/Winget, etc.
├── test_plugin_manager.py          # Integration of OllamaManager / plugins
├── test_service_manager.py         # Process control and status checking
└── test_settings.py                # Configuration and JSON loading functions
```

<hr><br>

> The plugin consists of several specialized components:

- **OllamaManager:** Unified interface combining all modules into one facade.
- **OllamaAPIManager:** REST API communication through:
  `/api/tags`, `/api/show`, `/api/pull`, `/api/delete`, `/api/generate`, `/api/ps`
- **OllamaCMDManager:** Command-line execution:
  `ollama list`, `ollama show`, `ollama pull`, `ollama rm`, `ollama run`, `ollama ps`, `ollama stop`
- **OllamaService:** Service lifecycle management and health monitoring.
- **OllamaHelper:** Platform installers, validation, and utility functions.

<hr><br>

## ⚖️ Backend Comparison

| Feature | API Backend | CMD Backend |
|---------|------------|-------------|
| Performance | ⚡ Faster | ⏱️ Slower |
| Streaming | ✅ Native | ✅ Line-based |
| Progress Info | ✅ Detailed | ⚠️ Parsing required |
| Parameter Control | ✅ Full | ❌ Limited |
| Dependencies | requests | subprocess |

<hr><br>

## 💎 Best Practices

- Use **API backend** for production or async apps
- Use **CMD backend** when the local API isn’t reachable
- Run `health_check()` before critical operations
- Cache repeated generations for better performance
- Keep `verbose=True` during development for logs and printouts

<hr><br>

## 📜 License

This project is open source. See [License](LICENSE).

<hr><br>

## 🙌 Contributors

![created-by](docs/pictures/created-by.svg)

<hr><br>

## 🧯 Troubleshooting

### 🧰 Development Installation

If you encounter import issues (e.g. modules not found), try:

```bash
pip install -e .
```

This installs the project in **editable mode**, linking your local `src/` folder so that changes take effect immediately.

Then you can import directly:
```py
from modules.service_manager import Service
```

<hr><br>

## 💻 Supported Platforms

- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (Ubuntu, Debian, Fedora…)
- ✅ Windows 10 / 11
