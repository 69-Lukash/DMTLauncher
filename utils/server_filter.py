from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

def apply_local_filters(all_servers, search_text, map_text, favorites, sort_mode=0):
    if not all_servers:
        return []

    query = search_text.strip().lower()
    map_q = map_text.strip().lower()

    filtered = []
    for s in all_servers:
        name = str(s.get("name", "")).lower()
        map_val = str(s.get("map", "")).lower()

        if query and query not in name:
            continue
        if map_q and map_q not in map_val:
            continue
        
        filtered.append(s)

    if sort_mode == 0:
        filtered.sort(key=lambda x: int(x.get("players", 0)), reverse=True)
    elif sort_mode == 1:
        filtered.sort(key=lambda x: str(x.get("name", "")).lower())
    
    def is_favorite(server_dict):
        ip = str(server_dict.get("ip", ""))
        port = str(server_dict.get("port", 0))
        address = f"{ip}:{port}"
        return address in favorites
        
    filtered.sort(key=is_favorite, reverse=True)
    
    return filtered

class FilterSignals(QObject):
    finished = pyqtSignal(list)

class FilterWorker(QRunnable):
    def __init__(self, all_servers, search_text, map_text, favorites, sort_mode=0):
        super().__init__()
        self.all_servers = all_servers
        self.search_text = search_text
        self.map_text = map_text
        self.favorites = favorites
        self.sort_mode = sort_mode
        self.signals = FilterSignals()

    def run(self):
        filtered = apply_local_filters(
            self.all_servers, 
            self.search_text, 
            self.map_text, 
            self.favorites, 
            self.sort_mode
        )
        self.signals.finished.emit(filtered)