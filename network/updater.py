import urllib.request
import json
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class UpdaterSignals(QObject):
    update_available = pyqtSignal(str, str)

class UpdateCheckWorker(QRunnable):
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.signals = UpdaterSignals()

    def run(self):
        if self.current_version == "dev":
            return
            
        url = "https://api.github.com/repos/69-Lukash/DMTLauncher/releases/latest"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Updater'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_tag = data.get("tag_name", "").strip("vV")
                release_url = data.get("html_url", "")
                
                if not latest_tag:
                    return
                    
                curr_parts = tuple(map(int, self.current_version.split(".")))
                latest_parts = tuple(map(int, latest_tag.split(".")))
                
                if latest_parts > curr_parts:
                    self.signals.update_available.emit(latest_tag, release_url)
                    
        except Exception as e:
            logger.debug(f"Update check failed: {e}")