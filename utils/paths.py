import sys
import os
from pathlib import Path

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_dir() -> str:
    if sys.platform == "win32":
        app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~')
        data_dir = os.path.join(app_data, "DMTL")
    else:
        data_dir = os.path.join(str(Path.home()), ".config", "DMTL")
    
    os.makedirs(data_dir, exist_ok=True)
    return data_dir