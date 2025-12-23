# src/ollama_service.py

import platform
import shutil

from typing import Optional

class OllamaService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_os_name() -> str:
        system = platform.system()
        if system == "Darwin":
            return "MacOS"
        return system

    def is_installed(self) -> bool:
        path = shutil.which("ollama")
        if path:
            return True
        return False

    def get_installation_path(self) -> Optional[str]:
        return shutil.which("ollama")
