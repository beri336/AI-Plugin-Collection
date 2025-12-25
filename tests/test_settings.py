# tests/test_settings.py

'''
Unit tests for the Config/Settings class
  This test suite validates the central configuration management.

- Tests default values for host, port, and timeouts
- Validates base URL construction
- Checks endpoint URL generation
- Tests directory creation for logs and cache
- Validates getter and setter methods
- Checks JSON config loading with error handling
- Tests edge cases and error scenarios
'''

from config.settings import Config
from pathlib import Path
import pytest
import json


def test_defaults_and_base_url():
    cfg = Config()
    assert cfg.host == "localhost"
    assert cfg.port == 11434
    assert cfg.base_url == "http://localhost:11434"
    assert "version" in cfg._endpoints
    assert isinstance(cfg.timeout_default, int)
    assert isinstance(cfg.log_directory, Path)

def test_get_endpoint_valid():
    cfg = Config()
    url = cfg.get_endpoint("version")
    assert url.startswith("http://localhost:11434/api/")
    assert "/api/version" in url

def test_get_endpoint_invalid_raises():
    cfg = Config()
    with pytest.raises(KeyError):
        cfg.get_endpoint("unknown_endpoint")

def test_ensure_directories(tmp_path):
    cfg = Config(
        log_directory=tmp_path / "logs",
        cache_directory=tmp_path / "cache"
    )
    cfg.ensure_directories()
    assert cfg.log_directory.exists()
    assert cfg.cache_directory.exists()

def test_getter_and_setter():
    cfg = Config()
    cfg.set_host("127.0.0.1")
    cfg.set_port(9999)
    assert cfg.get_host() == "127.0.0.1"
    assert cfg.get_port() == 9999
    assert cfg.get_base_url == "http://localhost:11434"  # unchanged default base_url variable

def test_load_from_json_success(tmp_path):
    file = tmp_path / "config.json"
    data = {"host": "ai.server", "port": 7777}
    file.write_text(json.dumps(data))

    cfg = Config.load_from_json(file)
    assert isinstance(cfg, Config)
    assert cfg.host == "ai.server"
    assert cfg.port == 7777

def test_load_from_json_file_not_found(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        Config.load_from_json(missing)

def test_load_from_json_is_directory(tmp_path):
    with pytest.raises(IsADirectoryError):
        Config.load_from_json(tmp_path)
