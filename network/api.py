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
        import os
        from utils.paths import get_data_dir
        
        url = "https://dayzsalauncher.com/api/v1/launcher/servers/dayz"
        cache_file = os.path.join(get_data_dir(), "dzsa_cache.json")
        logger.info(f"Fetching server list from API: {url}")
        
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            req = urllib.request.Request(url, headers={'User-Agent': 'DMTL-Launcher/1.0'})

            with urllib.request.urlopen(req, timeout=15, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"API Error while fetching servers: {e}")
            if os.path.exists(cache_file):
                logger.info("Loading server list from local cache")
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as cache_e:
                    logger.error(f"Cache load failed: {cache_e}")
                    self.signals.finished.emit([])
                    return
            else:
                self.signals.finished.emit([])
                return

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

        logger.info(f"Successfully loaded {len(server_list)} servers")
        self.signals.finished.emit(server_list)

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
        import re
        try:
            logger.info(f"Checking dependencies for mod {self.mod_id} via HTML parsing...")
            url_html = f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.mod_id}"
            req_html = urllib.request.Request(url_html, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req_html, timeout=5) as resp:
                html = resp.read().decode('utf-8')
                
            dep_ids = []
            if 'id="RequiredItems"' in html:
                matches = re.findall(r'href="https://steamcommunity\.com/workshop/filedetails/\?id=(\d+)"', html)
                dep_ids = [int(m) for m in matches]
                logger.debug(f"Found required items in HTML for {self.mod_id}: {dep_ids}")
            else:
                logger.debug(f"No 'RequiredItems' block found in HTML for {self.mod_id}.")
                    
            dep_ids = list(dict.fromkeys(dep_ids))
            
            if not dep_ids:
                self.signals.finished.emit(self.mod_id, [], [])
                return
                
            url_api = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
            post_deps = {'itemcount': len(dep_ids)}
            for i, d_id in enumerate(dep_ids):
                post_deps[f'publishedfileids[{i}]'] = d_id
                
            data_deps = urllib.parse.urlencode(post_deps).encode('utf-8')
            req_deps = urllib.request.Request(url_api, data=data_deps, headers={'User-Agent': 'DMTL-Launcher/1.0'})
            
            with urllib.request.urlopen(req_deps, timeout=5) as resp_deps:
                deps_api_data = json.loads(resp_deps.read().decode('utf-8'))
                
            dep_names = []
            for d_id in dep_ids:
                title = f"Unknown Mod {d_id}"
                for d in deps_api_data.get("response", {}).get("publishedfiledetails", []):
                    if d.get("publishedfileid") == str(d_id):
                        title = d.get("title", title)
                        break
                dep_names.append(title)

            logger.info(f"Successfully fetched {len(dep_ids)} dependencies for {self.mod_id}: {dep_names}")
            self.signals.finished.emit(self.mod_id, dep_names, dep_ids)
                
        except Exception as e:
            logger.error(f"Failed to fetch dependencies for {self.mod_id}: {e}", exc_info=True)
            self.signals.finished.emit(self.mod_id, [], [])