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
            ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
            port = str(s.get("port", s.get("endpoint", {}).get("port", 0)))
            players = f"{s.get('players', 0)}/{s.get('maxplayers', s.get('maxPlayers', 0))}"
            
            map_name = str(s.get("map", s.get("mission", "Chernarus"))).title()
            
            full_address = f"{ip}:{port}"
            is_fav = (getattr(self.mw, "favorites", []) is not None) and (full_address in self.mw.favorites)
            
            self.mw.table_builder.insert_server_row(is_fav, name, map_name, full_address, "-", players)
            
        self.table.setUpdatesEnabled(True)
        
        if self.table.rowCount() == len(batch):
            self.mw.ping_visible_servers()