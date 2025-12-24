# src/ollama_manager.py

from ollama_cmd_manager import OllamaCMDManager, PullMode
from ollama_api_manager import OllamaAPIManager
from ollama_cmd_manager import OllamaCMDManager
from ollama_service import OllamaService
from ollama_helper import OllamaHelper

from enum import Enum

import logging


class OllamaBackend(Enum):
    API = "api"
    CMD = "cmd"


class OllamaManager():
    def __init__(
        self,
        backend: OllamaBackend = OllamaBackend.API,
        host: str = "localhost",
        port: int = 11434
    ) -> None:
        self.service = OllamaService()
        self.cmd = OllamaCMDManager()
        self.api = OllamaAPIManager()
        self.helper = OllamaHelper()
        self.logger = None
        
        # Init backend
        if backend == OllamaBackend.API:
            self._backend = OllamaAPIManager(host, port)
        else:
            self._backend = OllamaCMDManager()
        
        self.backend_type = backend

    def get_backend_type(self):
        print("Set backend type: '{self.backend_type}'")

    def switch_backend(self, mode: OllamaBackend):
        self.backend_type = mode
        print(f"New backend type: '{mode}'")

# OllamaCMDManager & OllamaAPIManager
    def get_list_of_models(self) -> None:
        models: list[str] = self._backend.list_model_names()
        
        print("All available (downlaoded) models:")
        for i in models:
            print(f"- '{i}'")

    def get_list_of_models_detailed(self) -> None:
        models: list[str] = self._backend.list_models_detailed()
        
        print("All available (downloaded) models with details:")
        if models:
            for i in models:
                print(f"- Modelname: '{i["name"]}'")
                print(f"    - ID: '{i["id"]}'")
                print(f"    - Size: '{i["size"]}'")
                print(f"    - Last modified: '{i["modified"]}'")

    def get_information_for_model(self, model: str):
        model_exists = self._backend.get_model_info(model)
        if not model_exists:
            print(f"'{model}' does not exist.")
            return
        
        model_info = self.cmd.get_model_info(model)
        
        if model_info is None:
            return
        
        print(f"\n=== Model Info: {model_info['model_name']} ===\n")
        
        # iterate over 'model' dictionary
        for section_name, section_data in model_info.items():
            if section_name == 'model_name':
                continue  # skip, already printed
            
            print(f"[{section_name.upper()}]")
            
            if isinstance(section_data, dict):
                # if it is a dictionary (such as ‘model’)
                for key, value in section_data.items():
                    if key == 'items' and isinstance(value, list):
                        # items are a list
                        for item in value:
                            print(f"  - {item}")
                    else:
                        print(f"  {key}: {value}")
            elif isinstance(section_data, list):
                # if it is a list directly
                for item in section_data:
                    print(f"  - {item}")
            else:
                # simple value
                print(f"  {section_data}")
            
            print()

    def load_new_model(self, model: str, stream: bool = True, mode: PullMode = PullMode.FOREGROUND) -> None:
        if self.backend_type == OllamaBackend.API:
            result = self.api.pull_model(model, stream)
            
            if result:
                print(f"Model '{model}' successfully downloaded (via {mode}).")
            else:
                print(f"Error: While downloading Model '{model}' (via {mode}).")
        else:
            result = self.cmd.pull_model(model, mode)
            
            if result:
                print(f"Model '{model}' successfully downloaded (via {mode}).")
            else:
                print(f"Error: While downloading Model '{model}' (via {mode}).")

    def load_new_model_with_progress(self, model: str):
        print(f"Starting download of '{model}'...")
        
        try:
            for progress in self._backend.pull_model_with_progress(model):
                status = progress.get('status', 'unknown')
                
                if status == 'downloading':
                    percent = progress.get('percent', 0)
                    size = progress.get('size', '')
                    print(f"\rDownloading: {percent:.1f}% {size}", end='', flush=True)
                
                elif status == 'pulling_manifest':
                    print(f"\r{progress.get('message', 'Pulling manifest...')}", flush=True)
                
                elif status == 'verifying':
                    print(f"\r{progress.get('message', 'Verifying...')}", flush=True)
                
                elif status == 'completed':
                    print(f"\n✓ Model '{model}' successfully downloaded.")
                    return True
                
                elif status == 'failed':
                    print(f"\n✗ Error: {progress.get('error', 'Unknown error')}")
                    return False
                
                elif status == 'error':
                    print(f"\n✗ Error: {progress.get('error', 'Unknown error')}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error while downloading model '{model}': {e}")
            return False

    def remove_model(self, model: str, force: bool = False) -> None:
        status = self._backend.delete_model(model, force)
        
        if status:
            print(f"Model '{model}' was successfully removed.")
        else:
            print(f"Error: While removing Model '{model}'.")

    def check_if_model_exists(self, model: str) -> None:
        model_exists = self._backend.model_exists(model)
    
        if model_exists:
            print(f"Model '{model}' is installed.")
        else:
            print(f"Model '{model}' is not installed.")

    def refresh_list_of_models(self):
        self._backend.refresh_list_of_models()
        print("Refreshed the list of models.")

    def get_all_running_models(self) -> None:
        models = self._backend.get_running_models()
        
        if not models:
            print("No models are currently active.")
            return
        
        print(f"\n=== Currently Running Models ({len(models)}) ===\n")
        for model in models:
            print(f"• {model['name']}")
            print(f"  Size: {model['size']}")
            print(f"  Processor: {model['processor']}")
            print(f"  Expires: {model['until']}\n")

    def get_only_names_of_all_running_models(self) -> None:
        models = self._backend._get_running_model_names()
        
        if len(models) > 0:
            for i in models:
                print(f"Model '{i['name']}' is currently active.")  
        else:
            print("No models are currently active.")

    def start_running_model(self, model: str):
        start = self._backend.start_running_model(model)
        
        if start:
            print(f"Model '{model}' started successfully and is now available.")
        else:
            print(f"Error: While starting Model '{model}' and is not available.")

    def stop_running_model(self, model: str, force: bool = False):
        status = self._backend.stop_running_model(model, force)
        
        if status:
            print(f"Model '{model}' was stopped successfully.")
        else:
            print(f"Error: While stopping Model '{model}'.")

    def refresh_list_of_all_running_models(self):
        self._backend.refresh_list_of_running_models()
        print("Refreshed the list of all running models.")

    def generate_response(self, model: str, prompt: str, options: dict | None = None):
        if not model:
            print("No model specified.")
            return
        if not prompt:
            print("No prompt specified.")
            return
        
        if self.backend_type == OllamaBackend.CMD:
            response = self.cmd.generate(model, prompt)
            
            print("\n=== AI Response to given prompt ===")
            print(f"{response}")
        else:
            response = self.api.generate(model, prompt, options)
            
            print("\n=== AI Response to given prompt ===")
            print(f"{response}")

    def generate_streamed_response(self, model: str, prompt: str, options: dict | None = None):
        if not model:
            print("No model specified.")
            return
        if not prompt:
            print("No prompt specified.")
            return
        
        if self.backend_type == OllamaBackend.CMD:
            response = self.cmd.generate_stream(model, prompt)
            
            print("\n=== AI Response to given prompt ===")
            print(f"{response}")
        else:
            response = self.api.generate_stream(model, prompt, options)
            
            print("\n=== AI Response to given prompt ===")
            print(f"{response}")

# OllamaAPIManager only
    def check_api_connection(self):
        con = self.api._check_connection()

        if con:
            print("API is reachable.")
        else:
            print("API seems to be offline.")

    def get_api_url(self, endpoint: str = ''):
        print(f"API URL: '{self.api._get_url(endpoint)}'")

    def get_api_host(self):
        print(f"API Host: '{self.api.get_host()}'")

    def set_api_host(self, new_host: str):
        self.api.set_host(new_host)
        print(f"New API Host set to: '{new_host}'")

    def get_api_port(self):
        print(f"API Port: '{self.api.get_port()}'")

    def set_api_port(self, new_port: int):
        self.api.set_port(new_port)
        print(f"New API Port set to: '{new_port}'")

    def get_api_base_url(self):
        print(f"API Base URL: '{self.api.get_base_url()}'")

# OllamaService
    def get_version(self):
        print(f"Current installed Ollama Version: '{self.service.get_version()}'.")

    def get_operating_system(self):
        print(f"Current Operating System: '{self.service.get_os_name()}'.")

    def get_is_process_running(self):
        status = self.service.is_process_running()
        
        if status:
            print("Ollama is currently active.")
        else:
            print("Ollama is currently not active.")

    def get_api_status(self):
        status = self.service.is_api_reachable()
        
        if status:
            print("Ollama API is reachable.")
        else:
            print("Ollama API seems to be offline.")

    def get_is_installed(self):
        status = self.service.is_installed()
        
        if status:
            print("Ollama is installed.")
        else:
            print("Ollama is not installed or in PATH.")

    def get_installation_path(self):
        print(f"Ollama installed Path: '{self.service.get_installation_path()}'")

    def start_ollama(self):
        if self.service.is_process_running():
            print("Ollama is already running.")
            return
        
        process = self.service.start()
        
        if process:
            print("Success: Ollama started successfully.")
        else:
            print("Error: Ollama could not be started.")

    def stop_ollama(self):
        stop = self.service.stop()
        
        if stop:
            print("Success: Ollama stopped successfully.")
        else:
            print("Error: Ollama could not be stopped.")

    def health_check(self):
        check = self.service.get_status()
        
        print("\n# Health Check #")
        print(f"Operating System: '{check["os"]}'")
        print(f"Ollama Installed: '{check["installed"]}'")
        print(f"Ollama Installation Path: '{check["installation_path"]}'")
        print(f"Ollama Process Is Running: '{check["process_running"]}'")
        print(f"Ollama API Is Reachable: '{check["api_reachable"]}'")
        print(f"Ollama Is Fully Operational: '{check["fully_operational"]}'")
        print(f"Ollama Version: '{check["version"]}'\n")

    def setup_logging_default(self):
        self.logger = self.service.setup_logger()
        print("Logging configured: INFO level, console output")

    def setup_logging_debug(self, log_file: str = "logs/ollama_debug.log"):
        self.logger = self.service.setup_logger(
            level=logging.DEBUG,
            log_file=log_file,
            console=True
        )
        print(f"Debug logging configured: DEBUG level, console + file '{log_file}'")

    def setup_logging_file_only(self, log_file: str = "logs/ollama.log", level: int = logging.INFO):
        self.logger = self.service.setup_logger(
            level=level,
            log_file=log_file,
            console=False
        )
        print(f"File logging configured: {logging.getLevelName(level)} level, file '{log_file}'")

    def setup_logging_quiet(self):
        self.logger = self.service.setup_logger(
            level=logging.WARNING,
            console=True
        )
        print("Quiet logging configured: WARNING level, console output")

    def setup_logging_verbose(self, log_file: str = "logs/ollama_verbose.log"):
        self.logger = self.service.setup_logger(
            level=logging.DEBUG,
            log_file=log_file,
            console=True
        )
        print(f"Verbose logging configured: DEBUG level, console + file '{log_file}'")

    def setup_logging_custom(
        self, 
        level: int = logging.INFO,
        log_file: str | None = None,
        console: bool = True
    ):
        self.logger = self.service.setup_logger(
            level=level,
            log_file=log_file,
            console=console
        )
        level_name = logging.getLevelName(level)
        output = []
        if console:
            output.append("console")
        if log_file:
            output.append(f"file '{log_file}'")
        print(f"Custom logging configured: {level_name} level, {' + '.join(output)}")

    def disable_logging(self):
        if self.logger:
            self.logger.handlers.clear()
            self.logger.setLevel(logging.CRITICAL + 1)
        print("Logging disabled")

    def get_logging_status(self):
        if self.logger is None:
            print("Logging not configured")
            return
        
        level = logging.getLevelName(self.logger.level)
        handlers = []
        
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handlers.append("console")
            elif isinstance(handler, logging.FileHandler):
                handlers.append(f"file ({handler.baseFilename})")
        
        print(f"Logging Status:")
        print(f"  Level: {level}")
        print(f"  Outputs: {', '.join(handlers) if handlers else 'none'}")

    def get_logger(self) -> logging.Logger:
        if self.logger is None:
            print("Logger not configured. Initializing with defaults...")
            self.setup_logging_default()
        
        # if setup_logging_default() does not succeed, return dummy logger
        if self.logger is None:
            print("Logger not configured. Initializing with dummy logger...")
            return logging.getLogger(__name__)
        
        return self.logger

# OllamaHelper
    def check_if_homebrew_is_installed(self):
        installed = self.helper._is_homebrew_installed()
        
        if installed:
            print("Homebrew is installed on system.")
        else:
            print("Homebrew not found.")

    def check_if_winget_is_installed(self):
        installed = self.helper._is_winget_installed()
        
        if installed:
            print("Winget is installed on system.")
        else:
            print("Winget not found.")

    def check_if_chocolatey_is_installed(self):
        installed = self.helper._is_chocolatey_installed()
        
        if installed:
            print("Chocolatey is installed on system.")
        else:
            print("Chocolatey not found.")

    def try_installing_homebrew(self):
        installed = self.helper._try_brew_install()
        
        if installed:
            print("Homebrew successfully installed.")
        else:
            print("Error: While installing Homebrew.")

    def try_installing_curl(self):
        installed = self.helper._try_curl_install()
        
        if installed:
            print("Curl successfully installed.")
        else:
            print("Error: While installing Curl.")

    def try_installing_winget(self):
        installed = self.helper._try_winget_install()
        
        if installed:
            print("Winget successfully installed.")
        else:
            print("Error: While installing Winget.")

    def try_installing_choco(self):
        installed = self.helper._try_choco_install()
        
        if installed:
            print("Chocolatey successfully installed.")
        else:
            print("Error: While installing Chocolatey.")

    def try_installing_direct_on_windows_only(self):
        installed = self.helper._try_direct_download_install_windows_only()
        
        if installed:
            print("Ollama successfully installed.")
        else:
            print("Error: While installing Ollama.")

    def show_manual_installation_instruction(self):
        self.helper._show_manual_install_instructions()

    def install_on_macos(self):
        installed = self.helper._install_macos()
        
        if installed:
            print("Ollama successfully installed on MacOS.")
        else:
            print("Error: While installing Ollama on MacOS.")

    def install_on_linux(self):
        installed = self.helper._install_linux()
        
        if installed:
            print("Ollama successfully installed on Linux.")
        else:
            print("Error: While installing Ollama on Linux.")

    def install_on_windows(self):
        installed = self.helper._install_windows()
        
        if installed:
            print("Ollama successfully installed on Windows.")
        else:
            print("Error: While installing Ollama on Windows.")

    def validate_name_is_correct_for_model(self, model: str):
        valid = self.helper.validate_model_name(model)
        
        if valid:
            print(f"Model '{model}' is a valid name.")
        else:
            print(f"Model '{model}' is not a valid name.")

    def estimate_prompt_tokenizer(self, text: str):
        counter = self.helper.estimate_tokens(text)
        print(f"Estimated Token: '{counter}'")

    def search_models(self, model: str, models: list[str]):
        status = self.helper.search_models(model, models)
        
        if status:
            print(f"Model '{model}' is installed.")
        else:
            print(f"Model '{model}' is not installed.")
