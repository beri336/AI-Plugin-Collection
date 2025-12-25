# AI Plugin Collection [Deutsch]

![Banner (created by ChatGPT)](<pictures/Banner (created by ChatGPT).png>)

Ein umfassendes Python-Plugin zur Verwaltung und Steuerung von Ollama über API und CLI. Dieses Plugin bietet eine einheitliche Schnittstelle für die Modellverwaltung, Service-Steuerung und KI-Generierung.

## 🌐 Sprache / Language

- 🇬🇧 [English](../README.md)
- 🇩🇪 Deutsch (diese Datei)

<br>

## ⚡ Wichtigsten Merkmale

- **Dual Backend:** Nahtloser Wechsel zwischen API- oder CLI-Befehlsausführung
- **Unified Manager:** Eine Schnittstelle (`OllamaManager`) zur Steuerung aller Subsysteme
- **Model Management:** Modelle auflisten, abrufen, löschen und überprüfen
- **AI Generation:** Textgenerierung (gestreamt oder zwischengespeichert)
- **Service Control:** Starten/ stoppen und Durchführen von Systemzustandsprüfungen
- **Cache Integration:** Optionale Caching-Ebene für wiederholte Eingabeaufforderungen
- **Conversation Management:** Aufrechterhaltung kontextbezogener Chat-Sitzungen
- **Helper Tools:** Plattforminstallation, Modellvalidierung, Token-Schätzung
- **Config Loader:** Laden von Einstellungen direkt aus JSON-Konfigurationsdateien
- **Cross‑Platform:** Funktioniert unter MacOS, Linux und Windows

<br>

## 📚 Inhaltsverzeichnis

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

### 🧱 Voraussetzungen

- Python 3.8+
- Ollama muss installiert sein (oder verwende die Hilfsfunktionen für die Installation)

### 📦 Abhängigkeiten installieren

Lokal oder in einem virtuellen Environment:

```bash
pip install -r requirements.txt
```

Oder direkt:

```bash
pip install psutil requests pytest pytest‑cov
```

Erforderliche Pakete:

| Package    | Zweck / Beschreibung                                                 |
| ---------- | -------------------------------------------------------------------- |
| psutil     | Prozess‑ und System‑Management (z. B. zur Prüfung, ob Ollama läuft) |
| requests   | HTTP‑Client zum Aufrufen der Ollama‑API                             |
| pytest     | Framework für Unit‑ und Integration‑Tests                           |
| pytest‑cov | Erweiterung zur Messung der Test‑Coverage                           |

### 🧪 Run Tests

Für vollständige Tests (inklusive Decorators, Caching, Helpers etc.):

```bash
pytest -v
```

Führen einen bestimmten Test aus:
```bash
pytest tests/test_service_manager.py
```

mit **Coverage‑Report**:

```bash
pytest --cov=src --cov-report=term-missing
```

Optionale Detailberichte (HTML im `htmlcov/`‑Ordner):

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # oder `start htmlcov/index.html` unter Windows
```

<hr><br>

## 🚀 Schnellstart

Siehe auch [Beispieldatei](src/main.py) für eine vollständige Vorführung.

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

## 💡 Verwendung

### ⚙️ Einrichtung & Konfiguration

#### 🗂️ Aus JSON-Konfiguration

```py
manager = OllamaManager.from_config_file("config.json", backend=OllamaBackend.API)
```

Beispiel für eine Konfigurationsdatei:

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

### 🟢 Ausführen der Modelle

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

### 🧠 AI-Generation

```py
# Generate once
manager.generate("gemma3:4b", "Explain Python.")

# Cached call (faster second time)
manager.generate("llama3.2:3b", "Explain Python classes.", use_cache=True)

# Stream output
manager.generate_stream("llama3.2:3b", "Write a short poem about programming.")
```

<br>

### 💬 Beispiel für eine AI-Konversation

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

### 🛠️ Werkzeuge

```py
manager.validate_model_name("llama3.2:3b")
manager.estimate_tokens("Sample prompt text")

# MacOS installation
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

### 🔀 Backend Steuerung

```py
# Switch between API and CMD
manager.switch_backend(mode=OllamaBackend.API)
manager.switch_backend(mode=OllamaBackend.CMD)
print(manager.get_backend_type())
```

<hr><br>

## 🧭 Architekturübersicht

### 🧩 Module
```bash
modules/
├── api_manager.py                  # REST-API-Interaktionen
├── cmd_manager.py                  # CLI-Befehle
├── conversation_manager.py         # Kontextuelle Konversation
├── plugin_manager.py               # Einheitlicher OllamaManager
└── service_manager.py              # Prozess- und Service-Kontrolle
```

### 🧠 Core
```bash
modules/
├── cache_manager.py                # Cache-System
├── decorators.py                   # Dekoratoren & Validierung
└── helpers.py                      # Betriebssystem-Dienstprogramme und Installationsprogramme
```

### ⚙️ Config
```bash
modules/
└── settings.py                     # Alle veränderbaren Einstellungen
```

### ⚙️ Tests
```bash
tests/
├── test_api_manager.py             # Tests für REST-API-Aufrufe
├── test_cache_manager.py           # Prüft Cache-System und SQLite-Logik
├── test_cmd_manager.py             # CLI-Befehle und Parameter-Parsing
├── test_conversation_manager.py    # Kontextverwaltung und Gesprächsfluss
├── test_decorators.py              # Alle Dekorator- und Validierungsfunktionen
├── test_helpers.py                 # Installationsroutinen, Brew/Winget u.a.
├── test_plugin_manager.py          # Integration von OllamaManager / Plugins
├── test_service_manager.py         # Prozesskontrolle und Statusprüfung
└── test_settings.py                # Konfiguration und JSON-Ladefunktionen
```

<hr><br>

Das Plugin besteht aus mehreren spezialisierten Komponenten:

- **OllamaManager:** Einheitliche Schnittstelle, die alle Module in einer Fassade vereint
- **OllamaAPIManager:** REST-API-Kommunikation über:
  `/api/tags`, `/api/show`, `/api/pull`, `/api/delete`, `/api/generate`, `/api/ps`
- **OllamaCMDManager:** Befehlszeilenausführung:
  `ollama list`, `ollama show`, `ollama pull`, `ollama rm`, `ollama run`, `ollama ps`, `ollama stop`
- **OllamaService:** Verwaltung des Lebenszyklus von Diensten und Überwachung des Zustands
- **OllamaHelper:** Plattform-Installationsprogramme, Validierung und Hilfsfunktionen

<hr><br>

## ⚖️ Backend-Vergleich

| Funktion | API-Backend | CMD-Backend |
|---------|------------|-------------|
| Leistung | ⚡ Schneller | ⏱️ Langsamer |
| Streaming | ✅ Nativ | ✅ Zeilenbasiert |
| Fortschrittsinformationen | ✅ Detailliert | ⚠️ Parsing erforderlich |
| Parametersteuerung | ✅ Vollständig | ❌ Eingeschränkt |
| Abhängigkeiten | requests | subprocess |

<hr><br>

## 💎 Best Practices

- Verwende **API-Backend** für Produktions- oder asynchrone Anwendungen
- Verwende **CMD-Backend**, wenn die lokale API nicht erreichbar ist
- Führe `health_check()` vor kritischen Vorgängen aus
- Speichere wiederholte Generierungen im Cache, um die Leistung zu verbessern
- Behalte während der Entwicklung `verbose=True` für Protokolle und Ausdrucke bei

<hr><br>

## 📜 Lizenz

Dieses Projekt ist Open Source. Siehe [Lizenz](../LICENSE).

<hr><br>

## 🙌 Mitwirkende

![created-by](pictures/created-by.svg)

<hr><br>

## 🧯 Fehlerbehebung

### 🧰 Entwicklungsinstallation

Bei Problemen beim Importieren (zB. Module nicht gefunden), versuche:

```bash
pip install -e .
```

Dadurch wird das Projekt im **bearbeitbaren Modus** installiert und mit dem lokalen Ordner „src/“ verknüpft, sodass Änderungen sofort wirksam werden.

Dann kann direkt importiert werden:
```py
from modules.service_manager import Service
```

<hr><br>

## 💻 Unterstützte Plattformen

- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (Ubuntu, Debian, Fedora…)
- ✅ Windows 10 / 11
