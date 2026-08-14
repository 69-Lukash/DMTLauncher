import time
from PyQt6.QtCore import QObject, QTimer

class TableLoader(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.table = main_window.tab_servers.table_servers
        self.servers_queue = []
        self.timer = QTimer()
        self.timer.timeout.connect(self._insert_batch)
        self.batch_size = 100

    def load_servers(self, servers_data):
        self.timer.stop()
        self.servers_queue = servers_data
        self.table.setRowCount(0)
        self.mw.pinged_servers.clear()
        
        if not self.servers_queue:
            self.mw.table_builder.insert_server_row(False, "No servers found.", "", "", "", "")
            return
            
        self.timer.start(5)

    def format_time(self, ts):
        if not ts: return "Never"
        diff = time.time() - ts
        if diff < 60: return "Just now"
        if diff < 3600: return f"{int(diff/60)}m ago"
        if diff < 86400: return f"{int(diff/3600)}h ago"
        return f"{int(diff/86400)}d ago"

    def _insert_batch(self):
        if not self.servers_queue:
            self.timer.stop()
            self.mw.ping_visible_servers()
            return

        batch = self.servers_queue[:self.batch_size]
        self.servers_queue = self.servers_queue[self.batch_size:]

        self.table.setUpdatesEnabled(False)
        
        for s in batch:
            name = str(s.get("name", "Unknown Server"))
            ip = str(s.get("ip", ""))
            port = str(s.get("port", 0))
            players = f"{s.get('players', 0)}/{s.get('maxplayers', 0)}"
            map_name = str(s.get("map", "Chernarus")).title()
            full_address = f"{ip}:{port}"
            is_fav = (getattr(self.mw, "favorites", []) is not None) and (full_address in self.mw.favorites)
            
            lp_ts = getattr(self.mw.config_manager, "last_played", {}).get(full_address, 0)
            lp_str = self.format_time(lp_ts)
            
            self.mw.table_builder.insert_server_row(is_fav, name, map_name, full_address, "-", players, lp_str)
            
        self.table.setUpdatesEnabled(True)
        
        if self.table.rowCount() == len(batch):
            self.mw.ping_visible_servers()