from PyQt6.QtWidgets import QMenu
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QColor

from network.api import DZSAWorker
from network.pinger import PingWorker
from utils.server_filter import apply_local_filters
from ui.views.dialog_info import ServerInfoDialog
from ui.components.table_loader import TableLoader

class ServerController:
    def __init__(self, view, config_manager, launch_callback):
        self.view = view
        self.config_manager = config_manager
        self.launch_callback = launch_callback
        
        self.all_servers = []
        self.pinged_servers = set()
        self.active_workers = []
        self.thread_pool = QThreadPool.globalInstance()
        
        self.tab_servers = self.view.tab_servers
        self.table_servers = self.view.tab_servers.table_servers
        self.table_builder = self.view.table_builder
        self.favorites = self.config_manager.get_favorites()
        
        self.table_loader = TableLoader(self)
        
        self._setup_connections()

    def _setup_connections(self):
        self.table_servers.verticalScrollBar().valueChanged.connect(self.ping_visible_servers)
        self.table_servers.cellClicked.connect(self.handle_server_click)
        self.view.tab_servers.search_bar.textChanged.connect(self.trigger_apply_local_filters)
        self.view.tab_servers.search_map.textChanged.connect(self.trigger_apply_local_filters)
        self.view.btn_direct_connect.clicked.connect(self.prompt_direct_connect)

    def fetch_global_database(self):
        self.table_servers.setRowCount(0)
        self.table_builder.insert_server_row(False, "Downloading servers...", "", "", "", "")
        
        worker = DZSAWorker()
        worker.setAutoDelete(False)
        worker.signals.finished.connect(self.on_database_downloaded)
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def on_database_downloaded(self, data):
        self.all_servers = data
        self.trigger_apply_local_filters()

    def trigger_apply_local_filters(self):
        if not self.all_servers: return
        search_text = self.view.tab_servers.search_bar.text()
        map_text = self.view.tab_servers.search_map.text()
        filtered = apply_local_filters(self.all_servers, search_text, map_text, self.favorites)
        self.table_loader.load_servers(filtered)

    def ping_visible_servers(self):
        viewport = self.table_servers.viewport()
        top_row = self.table_servers.indexAt(viewport.rect().topLeft()).row()
        bottom_row = self.table_servers.indexAt(viewport.rect().bottomLeft()).row()
        
        if top_row == -1: return
        if bottom_row == -1: bottom_row = self.table_servers.rowCount() - 1
        
        start_row = max(0, top_row - 10)
        end_row = min(self.table_servers.rowCount() - 1, bottom_row + 10)
        
        for row in range(start_row, end_row + 1):
            if self.table_servers.isRowHidden(row): continue
            ip_item = self.table_servers.item(row, 3)
            if not ip_item: continue
            address = ip_item.text()
            
            if address not in self.pinged_servers and address != ":0":
                self.pinged_servers.add(address)
                try:
                    ip, port = address.split(":")
                    pinger = PingWorker(ip, int(port))
                    pinger.setAutoDelete(False)
                    pinger.signals.finished.connect(
                        lambda addr, p, pl, dt, w=pinger: self.update_ping_in_table(addr, p, pl, dt, w)
                    )
                    self.active_workers.append(pinger)
                    self.thread_pool.start(pinger)
                except ValueError: pass

    def update_ping_in_table(self, address, ping_ms, players_str, day_time, worker=None):
        for row in range(self.table_servers.rowCount()):
            item = self.table_servers.item(row, 3)
            if item and item.text() == address:
                self.table_servers.setItem(row, 4, self.table_builder.create_item(ping_ms, center=True))
                if players_str:
                    self.table_servers.setItem(row, 5, self.table_builder.create_item(players_str, center=True))
                break
                
        if day_time:
            for s in self.all_servers:
                ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
                port = str(s.get("port", s.get("endpoint", {}).get("port", 0)))
                if f"{ip}:{port}" == address:
                    s["dayTime"] = day_time
                    break
                    
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)

    def handle_server_click(self, row, col):
        ip_widget = self.table_servers.item(row, 3)
        if not ip_widget: return
        ip_item = ip_widget.text()

        if col == 0: 
            item = self.table_servers.item(row, col)
            is_currently_fav = (item.text() == "★")
            if is_currently_fav:
                item.setText("☆")
                item.setForeground(QColor("gray"))
                self.config_manager.remove_favorite(ip_item)
            else:
                item.setText("★")
                item.setForeground(QColor("yellow"))
                self.config_manager.add_favorite(ip_item)
            self.favorites = self.config_manager.get_favorites()
            
        elif col == 6:
            try:
                ip, port = ip_item.split(":")
                pinger = PingWorker(ip, int(port))
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, w=pinger: self.update_ping_in_table(addr, p, pl, dt, w)
                ) 
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
            except ValueError: pass
            
        elif col == 7:
            menu = QMenu(self.table_servers)
            menu.setCursor(Qt.CursorShape.PointingHandCursor)
            menu.addAction("▶ Play").triggered.connect(lambda: self.handle_server_action(row, "play"))
            menu.addAction("📂 Load").triggered.connect(lambda: self.handle_server_action(row, "load"))
            menu.addAction("ℹ️ Info").triggered.connect(lambda: self.handle_server_action(row, "info"))
            menu.exec(self.table_servers.cursor().pos())

    def handle_server_action(self, row, action):
        ip_widget = self.table_servers.item(row, 3)
        if not ip_widget: 
            return
            
        ip_item = ip_widget.text()
        
        server_data = None
        for s in self.all_servers:
            ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
            port = str(s.get("port", s.get("endpoint", {}).get("port", 0)))
            if f"{ip}:{port}" == ip_item:
                server_data = s
                break
                
        if not server_data: 
            return

        if action in ("play", "load"):
            self.launch_callback(server_data, action)
            
        elif action == "info":
            try:
                ip, port = ip_item.split(":")
                pinger = PingWorker(ip, int(port))
                pinger.setAutoDelete(True)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, sd=server_data, r_idx=row: 
                    self.show_fresh_info(addr, p, pl, dt, sd, r_idx)
                )
                self.thread_pool.start(pinger)
            except ValueError:
                pass

    def show_fresh_info(self, address, ping, players_str, day_time, server_data, row):
        self.table_servers.setItem(row, 4, self.table_builder.create_item(ping, center=True))
        if players_str:
            self.table_servers.setItem(row, 5, self.table_builder.create_item(players_str, center=True))
            try:
                cur, mx = players_str.split('/')
                server_data['players'] = int(cur)
                server_data['maxplayers'] = int(mx)
            except (ValueError, IndexError):
                pass
                
        if day_time:
            server_data['dayTime'] = day_time
            
        dialog = ServerInfoDialog(server_data, ping, self.view)
        dialog.exec()

    def prompt_direct_connect(self):
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        text, ok = QInputDialog.getText(
            self.view, 
            "Direct Connect", 
            "Enter server IP:Port\n(e.g., 192.168.1.100:2302):"
        )
        
        if ok and text.strip():
            try:
                ip, port_str = text.strip().split(":")
                ip = ip.strip()
                port = int(port_str.strip())
                
                pinger = PingWorker(ip, port)
                pinger.setAutoDelete(True)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, i=ip, po=port: self._process_direct_connect(p, i, po)
                )
                self.thread_pool.start(pinger)
                
            except ValueError:
                QMessageBox.warning(self.view, "Error", "Invalid format! Please use IP:Port")

    def _process_direct_connect(self, ping_str, ip, port):
        from PyQt6.QtWidgets import QMessageBox

        if ping_str == "999":
            QMessageBox.warning(self.view, "Connection Failed", f"Сервер {ip}:{port} не відповідає або вимкнений!")
            return
            
        mock_server = {
            "name": "Direct Connection",
            "ip": ip,
            "port": port,
            "mods": [] 
        }
        
        self.launch_callback(mock_server, "play")