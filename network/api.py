import urllib.request
import json
import ssl
import certifi
import urllib.parse
import re

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

class DependencySignals(QObject):
    # mod_id, list of names, list of ids
    finished = pyqtSignal(int, list, list)

class DependencyWorker(QRunnable):
    def __init__(self, mod_id):
        super().__init__()
        self.mod_id = mod_id
        self.signals = DependencySignals()

    def run(self):
        try:
            # 1. Scrape required items from HTML
            url_html = f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.mod_id}"
            req_html = urllib.request.Request(url_html, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req_html, timeout=5) as response:
                html = response.read().decode('utf-8')
                
            start_idx = html.find('id="RequiredItems"')
            if start_idx == -1:
                self.signals.finished.emit(self.mod_id, [], [])
                return
                
            end_idx = html.find('class="rightDetailsBlock"', start_idx)
            if end_idx == -1:
                end_idx = start_idx + 5000 
                
            block = html[start_idx:end_idx]
            found_ids = re.findall(r'filedetails/\?id=(\d+)', block)
            dep_ids = list(set([int(x) for x in found_ids]))
            
            if not dep_ids:
                self.signals.finished.emit(self.mod_id, [], [])
                return

            # 2. Get real display names via legacy API
            url_api = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
            post_data = {'itemcount': len(dep_ids)}
            for i, d_id in enumerate(dep_ids):
                post_data[f'publishedfileids[{i}]'] = d_id
                
            data_api = urllib.parse.urlencode(post_data).encode('utf-8')
            req_api = urllib.request.Request(url_api, data=data_api, headers={'User-Agent': 'DMTL-Launcher/1.0'})
            
            with urllib.request.urlopen(req_api, timeout=3) as resp_api:
                api_data = json.loads(resp_api.read().decode('utf-8'))
                dep_details = api_data.get("response", {}).get("publishedfiledetails", [])
                
                dep_names = []
                for d in dep_details:
                    dep_names.append(d.get("title", f"Unknown Mod {d.get('publishedfileid')}"))

                self.signals.finished.emit(self.mod_id, dep_names, dep_ids)
                
        except Exception as e:
            logger.error(f"Failed to fetch dependencies for {self.mod_id}: {e}")
            self.signals.finished.emit(self.mod_id, [], [])