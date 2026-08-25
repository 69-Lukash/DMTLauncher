from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

def apply_local_filters(all_servers, search_text, map_text, favorites, last_played_dict, sort_mode=0, sort_lp=False):
    if not all_servers: return []

    query = search_text.strip().lower()
    map_q = map_text.strip().lower()

    filtered = []
    for s in all_servers:
        name = str(s.get("name", "")).lower()
        map_val = str(s.get("map", "")).lower()

        if query and query not in name: continue
        if map_q and map_q not in map_val: continue
        
        filtered.append(s)

    def sort_key(s):
        ip = str(s.get("ip", ""))
        port = str(s.get("port", 0))
        addr = f"{ip}:{port}"
        
        fav = -1 if addr in favorites else 0
        lp = -last_played_dict.get(addr, 0) if sort_lp else 0
        
        if sort_mode == 0:
            try: p = -int(s.get("players", 0))
            except (ValueError, TypeError): p = 0
            return (fav, lp, p)
        else:
            name = str(s.get("name", "")).lower()
            return (fav, lp, name)
    filtered.sort(key=sort_key)
    
    return filtered

class FilterSignals(QObject):
    finished = pyqtSignal(list)

class FilterWorker(QRunnable):
    def __init__(self, all_servers, search_text, map_text, favorites, last_played_dict, sort_mode=0, sort_lp=False):
        super().__init__()
        self.all_servers = all_servers
        self.search_text = search_text
        self.map_text = map_text
        self.favorites = favorites
        self.last_played_dict = last_played_dict
        self.sort_mode = sort_mode
        self.sort_lp = sort_lp
        self.signals = FilterSignals()

    def run(self):
        filtered = apply_local_filters(
            self.all_servers, self.search_text, self.map_text, 
            self.favorites, self.last_played_dict, self.sort_mode, self.sort_lp
        )
        self.signals.finished.emit(filtered)