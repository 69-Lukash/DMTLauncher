import sys
import os
from pathlib import Path

def get_data_dir() -> str:
    if sys.platform == "win32":
        app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~')
        data_dir = os.path.join(app_data, "DMTL")
    else:
        data_dir = os.path.join(str(Path.home()), ".config", "DMTL")
    
    os.makedirs(data_dir, exist_ok=True)
    return data_dir



_RESERVED_WIN_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

def sanitize_filename(name: str, fallback: str = "Preset", max_bytes: int = 120) -> str:
    """Make a user/server-provided name safe to use as a file name on any OS."""
    cleaned = "".join("_" if (c in '<>:"/\\|?*' or ord(c) < 32) else c for c in str(name))
    cleaned = cleaned.strip().strip(". ")
    while len(cleaned.encode("utf-8")) > max_bytes:
        cleaned = cleaned[:-1]
    cleaned = cleaned.strip().strip(". ")
    if not cleaned:
        return fallback
    if cleaned.split(".")[0].upper() in _RESERVED_WIN_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned