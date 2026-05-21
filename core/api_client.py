import urllib.request
import json
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class ApiSignals(QObject):
    finished = pyqtSignal(list)

class DZSAWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = ApiSignals()

    def run(self):
        url = "https://dayzsalauncher.com/api/v1/launcher/servers/dayz"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Launcher/1.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            server_list = []
            if isinstance(data, list):
                server_list = data
            elif isinstance(data, dict):
                server_list = data.get("result", data.get("servers", data.get("data", [])))
            
            self.signals.finished.emit(server_list)
        except Exception as e:
            print(f"API Error: {e}")
            self.signals.finished.emit([])