# src/ollama_helper.py

import shutil


class OllamaHelper:
    def __init__(self) -> None:
        pass

# Package Manager
    @staticmethod
    def _is_homebrew_installed() -> bool:
        """ Checks if Homebrew is installed. """
        return shutil.which("brew") is not None

    @staticmethod
    def _is_winget_installed() -> bool:
        return shutil.which("winget") is not None

    @staticmethod
    def _is_chocolatey_installed() -> bool:
        return shutil.which("choco") is not None
