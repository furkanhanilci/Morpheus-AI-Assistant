# config/__init__.py
import json
import platform
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "api_keys.json"


def get_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _platform_default() -> str:
    sysname = platform.system().lower()
    if sysname == "darwin":
        return "mac"
    if sysname == "windows":
        return "windows"
    return "linux"


def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    cfg_os = get_config().get("os_system")
    if cfg_os:
        return str(cfg_os).lower()
    return _platform_default()


def is_windows() -> bool:
    return get_os() == "windows"


def is_mac() -> bool:
    return get_os() == "mac"


def is_linux() -> bool:
    return get_os() == "linux"


__all__ = ["get_config", "get_os", "is_windows", "is_mac", "is_linux"]
