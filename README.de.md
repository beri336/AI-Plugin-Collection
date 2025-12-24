# AI-Plugin-Collection [Deutsch]

Ein umfassendes Python-Plugin zur Verwaltung und Steuerung von Ollama über API und CLI. Dieses Plugin bietet eine einheitliche Schnittstelle für Model-Management, Service-Kontrolle und AI-Generierung.

## Language / Sprache

- 🇬🇧 [English](README.md)
- 🇩🇪 Deutsch (diese Datei)

## Features

- **Dual Backend Support**: Wahlweise Steuerung über Ollama API oder CLI
- **Model Management**: Modelle auflisten, laden, löschen und überwachen
- **Service Control**: Ollama-Service starten, stoppen und überwachen
- **AI Generation**: Text-Generierung mit und ohne Streaming
- **Cross-Platform**: Unterstützung für Windows, macOS und Linux
- **Installation Helper**: Automatische Installation von Ollama auf verschiedenen Plattformen
- **Logging System**: Flexibles Logging mit verschiedenen Konfigurationsoptionen

## Inhaltsverzeichnis

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Verwendung](#verwendung)
   - [Manager Setup](#manager-setup)
   - [Model Management](#model-management)
   - [Running Models](#running-models)
   - [AI Text Generation](#ai-text-generation)
   - [Service Management](#service-management)
   - [API-spezifische Funktionen](#api-spezifische-funktionen)
   - [Logging Configuration](#logging-configuration)
   - [Installation Helper](#installation-helper)
   - [Utility-Funktionen](#utility-funktionen)
4. [Architektur](#architektur)
5. [Backend-Vergleich](#backend-vergleich)
6. [Best Practices](#best-practices)
7. [Beispiel-Workflow](#beispiel-workflow)
8. [Troubleshooting](#troubleshooting)
9. [Contributors](#contributors)
10. [Lizenz](#lizenz)
11. [Unterstützte Plattformen](#unterstützte-plattformen)

## Installation

### Voraussetzungen

- Python 3.8+
- Ollama muss installiert sein (oder nutze die Helper-Funktionen zur Installation)

### Dependencies installieren

```bash
pip install -r requirements.txt
```

Oder direkt:

```bash
pip install psutil requests
```

Die benötigten Pakete sind:

- `psutil` - Für Prozess-Management
- `requests` - Für HTTP-Requests zur Ollama API

## Quick Start

Siehe auch [Beispiel-Datei](ollama_manager_usage_example.py) für weitere Beispiele.

```python
from ollama_manager import OllamaManager, OllamaBackend

# Manager initialisieren (Standard: API-Backend)
manager = OllamaManager()

# Modell laden
manager.load_new_model("llama3.2:3b")

# Text generieren
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()
```

## Verwendung

### Manager Setup

```python
# Standard Setup (API-Backend, localhost:11434)
manager = OllamaManager()

# Custom Setup (CLI-Backend, custom Host/Port)
custom_manager = OllamaManager(
    backend=OllamaBackend.CMD,
    host="127.0.0.1",
    port=12345
)
```

### Model Management

```python
# Verfügbare Modelle auflisten
models = manager.get_list_of_models()
detailed = manager.get_list_of_models_detailed()

# Informationen zu einem Modell abrufen
info = manager.get_information_for_model("llama3.2:3b")

# Neues Modell laden
success = manager.load_new_model("llama3.2:3b")

# Modell mit Fortschrittsanzeige laden
for progress in manager.load_new_model_with_progress("llama3.2:3b"):
    print(f"{progress}")
    if progress.get('status') == 'completed':
        print("Ready to use!")
        break

# Modell entfernen
manager.remove_model("llama3.2:3b")

# Prüfen ob Modell existiert
exists = manager.check_if_model_exists("llama3.2:3b")
```

### Running Models

```python
# Laufende Modelle anzeigen
running = manager.get_all_running_models()
names = manager.get_only_names_of_all_running_models()

# Modell starten
manager.start_running_model("llama3.2:3b")

# Modell stoppen
manager.stop_running_model("llama3.2:3b")

# Listen aktualisieren
manager.refresh_list_of_models()
manager.refresh_list_of_all_running_models()
```

### AI Text Generation

```python
# Einfache Generierung (nicht-gestreamt)
response = manager.generate_response(
    model="llama3.2:3b",
    prompt="Explain Python in simple terms"
)

# Streaming-Generierung
print("Assistant: ", end='', flush=True)
manager.generate_streamed_response(
    model="llama3.2:3b",
    prompt="Write a short poem about coding"
)
print()
```

### Service Management

```python
# Ollama-Version abrufen
version = manager.get_version()

# Betriebssystem prüfen
os_name = manager.get_operating_system()

# Status prüfen
is_installed = manager.get_is_installed()
is_running = manager.get_is_process_running()
api_ready = manager.get_api_status()

# Installation Path
path = manager.get_installation_path()

# Service starten/stoppen
manager.start_ollama()
manager.stop_ollama()

# Health Check
status = manager.health_check()
```

### API-spezifische Funktionen

```python
# API-Verbindung prüfen
manager.check_api_connection()

# API-Konfiguration
url = manager.get_api_url("/endpoint")
host = manager.get_api_host()
manager.set_api_host("new_host")

port = manager.get_api_port()
manager.set_api_port(11434)

base_url = manager.get_api_base_url()
```

### Logging Configuration

```python
# Standard Setup
manager.setup_logging_default()

# Debug-Modus
manager.setup_logging_debug()

# Nur in Datei loggen
manager.setup_logging_file_only()

# Stiller Modus
manager.setup_logging_quiet()

# Verbose-Modus
manager.setup_logging_verbose()

# Custom-Konfiguration
import logging
manager.setup_logging_custom(
    level=logging.DEBUG,
    log_file="logs/my_app.log",
    console=True
)

# Logging deaktivieren
manager.disable_logging()

# Status abrufen
status = manager.get_logging_status()

# Logger verwenden
logger = manager.get_logger()
logger.info("Application started")
```

### Installation Helper

```python
# macOS Installation
manager.check_if_homebrew_is_installed()
manager.try_installing_homebrew()
manager.install_on_macos()

# Linux Installation
manager.try_installing_curl()
manager.install_on_linux()

# Windows Installation
manager.check_if_winget_is_installed()
manager.check_if_chocolatey_is_installed()
manager.try_installing_winget()
manager.try_installing_choco()
manager.try_installing_direct_on_windows_only()
manager.install_on_windows()

# Manuelle Anleitung anzeigen
manager.show_manual_installation_instruction()
```

### Utility-Funktionen

```python
# Model-Name validieren
is_valid = manager.validate_name_is_correct_for_model("llama3.2:3b")

# Tokens schätzen
token_count = manager.estimate_prompt_tokenizer("Your prompt text here")

# Modelle suchen
models_list = manager.get_list_of_models()
results = manager.search_models("llama", models_list)
```

## Architektur

Das Plugin besteht aus mehreren spezialisierten Komponenten:

### OllamaManager

Hauptschnittstelle, die alle Funktionen vereint und zwei Backend-Modi unterstützt.

### OllamaAPIManager

Kommunikation mit Ollama über die REST API mit folgenden Endpunkten:

- `/api/tags` - Modelle auflisten
- `/api/show` - Model-Informationen
- `/api/pull` - Modelle herunterladen
- `/api/delete` - Modelle löschen
- `/api/generate` - Text generieren
- `/api/ps` - Laufende Modelle

### OllamaCMDManager

Steuerung über CLI-Befehle:

- `ollama list` - Modelle auflisten
- `ollama show` - Model-Details
- `ollama pull` - Modelle laden
- `ollama rm` - Modelle löschen
- `ollama run` - Text generieren
- `ollama ps` - Laufende Modelle
- `ollama stop` - Modell stoppen

### OllamaService

Service-Management für:

- Installationsprüfung
- Prozess-Überwachung
- API-Erreichbarkeit
- Service Start/Stop
- Versions-Informationen

### OllamaHelper

Hilfsfunktionen für:

- Plattformspezifische Installation
- Package-Manager-Integration
- Model-Name-Validierung
- Token-Schätzung
- Model-Suche

## Backend-Vergleich

| Feature | API Backend | CMD Backend |
|---------|------------|-------------|
| Performance | ⚡ Schneller | ⏱️ Langsamer |
| Streaming | ✅ Nativ | ✅ Zeilen-basiert |
| Progress Info | ✅ Detailliert | ⚠️ Parsing nötig |
| Parameter Control | ✅ Vollständig | ❌ Eingeschränkt |
| Dependencies | requests | subprocess |

## Best Practices

- Nutze das **API-Backend** für Performance-kritische Anwendungen
- Nutze das **CMD-Backend** wenn keine API verfügbar ist
- Verwende `generate_streamed_response()` für interaktive UIs
- Aktiviere Logging während der Entwicklung mit `setup_logging_debug()`
- Prüfe `health_check()` vor wichtigen Operationen
- Nutze `pull_model_with_progress()` für bessere User Experience

## Beispiel-Workflow

```python
from ollama_manager import OllamaManager

# Setup
manager = OllamaManager()
manager.setup_logging_default()

# Health Check
if not manager.health_check():
    print("Ollama is not running. Starting...")
    manager.start_ollama()

# Modell vorbereiten
model = "llama3.2:3b"
if not manager.check_if_model_exists(model):
    print(f"Downloading {model}...")
    manager.load_new_model(model)

# Modell verwenden
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

### Ollama startet nicht

```python
# Prüfe Installation
if not manager.get_is_installed():
    manager.install_on_macos()  # oder install_on_linux() / install_on_windows()

# Prüfe Status
status = manager.health_check()
print(status)
```

### API nicht erreichbar

```python
# Prüfe Host und Port
print(manager.get_api_host())
print(manager.get_api_port())

# Setze custom Werte
manager.set_api_host("127.0.0.1")
manager.set_api_port(11434)
```

### Modell lädt nicht

```python
# Prüfe ob Modell existiert
exists = manager.check_if_model_exists("model-name")

# Validiere Namen
is_valid = manager.validate_name_is_correct_for_model("model-name")
```

## Contributors

![created-by](pictures/created-by.svg)

## Lizenz

Dieses Projekt ist Open Source. Bitte beachte die Lizenzbedingungen von Ollama.

## Unterstützte Plattformen

- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)
- ✅ Windows 10/11