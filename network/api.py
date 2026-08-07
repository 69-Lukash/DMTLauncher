import urllib.request
import json
import ssl
import certifi
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class ApiSignals(QObject):
    finished = pyqtSignal(list)

class DZSAWorker(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = ApiSignals()

    def run(self):
        url = "https://dayzsalauncher.com/api/v1/launcher/servers/dayz"
        logger.info(f"Fetching server list from API: {url}")
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Launcher/1.0'})

            with urllib.request.urlopen(req, timeout=15, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))

            raw_list = []
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict):
                raw_list = data.get("result", data.get("servers", data.get("data", [])))

            server_list = []
            for s in raw_list:
                endpoint = s.get("endpoint", {})
                server_list.append({
                    "name": s.get("name", "Unknown Server"),
                    "ip": s.get("ip", endpoint.get("ip", "")),
                    "port": s.get("port", endpoint.get("port", 0)),
                    "gamePort": s.get("gamePort", s.get("port", endpoint.get("port", 0))),
                    "queryPort": s.get("queryPort", s.get("port", 0)),
                    "players": s.get("players", 0),
                    "maxplayers": s.get("maxplayers", s.get("maxPlayers", 0)),
                    "map": s.get("map", s.get("mission", "Chernarus")),
                    "password": s.get("password", False),
                    "country": s.get("country", "Unknown")
                })

            logger.info(f"Successfully loaded {len(server_list)} servers from API")
            self.signals.finished.emit(server_list)
        except Exception as e:
            logger.error(f"API Error while fetching servers: {e}", exc_info=True)
            self.signals.finished.emit([])

class SingleServerSignals(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)