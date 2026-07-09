import urllib.request
import json
import ssl
import certifi
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
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Launcher/1.0'})

            with urllib.request.urlopen(req, timeout=15, context=context) as response:
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

class SingleServerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class SingleServerWorker(QRunnable):
    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port
        self.signals = SingleServerSignals()

    def run(self):
        url = f"https://dayzsalauncher.com/api/v1/launcher/server/{self.ip}:{self.port}"
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Launcher/1.0'})
            
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                server_data = data.get("result", data)
                
                if isinstance(server_data, list) and len(server_data) > 0:
                    self.signals.finished.emit(server_data[0])
                elif isinstance(server_data, dict):
                    self.signals.finished.emit(server_data)
                else:
                    self.signals.error.emit("Invalid data format")
        except Exception as e:
            self.signals.error.emit(str(e))