import time
from PyQt6.QtWidgets import QMenu, QMessageBox, QInputDialog
from PyQt6.QtCore import Qt, QThreadPool, QTimer, QCoreApplication
from PyQt6.QtGui import QColor

from network.mods_query import ModsQueryWorker
from network.api import DZSAWorker
from network.pinger import PingWorker
from utils.server_filter import apply_local_filters, FilterWorker
from ui.views.dialog_info import ServerInfoDialog
from ui.components.table_loader import TableLoader
from utils.logger import logger


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
        
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.ping_visible_servers)

        self._setup_connections()

    def _setup_connections(self):
        self.table_servers.verticalScrollBar().valueChanged.connect(lambda: self.scroll_timer.start(400))
        self.table_servers.cellClicked.connect(self.handle_server_click)
        self.view.tab_servers.search_bar.textChanged.connect(self.trigger_apply_local_filters)
        self.view.tab_servers.search_map.textChanged.connect(self.trigger_apply_local_filters)
        self.view.btn_direct_connect.clicked.connect(self.prompt_direct_connect)
        self.view.tab_servers.btn_refresh.clicked.connect(self.fetch_global_database)
        self.view.tab_servers.check_last_played.stateChanged.connect(self.trigger_apply_local_filters)

    def fetch_global_database(self):
        self.table_servers.setRowCount(0)
        self.table_builder.insert_server_row(False, QCoreApplication.translate("ServerController", "Downloading servers..."), "", "", "", "", "")
        
        worker = DZSAWorker()
        worker.setAutoDelete(False)
        worker.signals.finished.connect(lambda data, w=worker: self.on_database_downloaded(data, w))
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def on_database_downloaded(self, data, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)
            
        self.all_servers = data
        
        self.trigger_apply_local_filters()
        
    def trigger_apply_local_filters(self):
        if not self.all_servers: return
        search_text = self.view.tab_servers.search_bar.text()
        map_text = self.view.tab_servers.search_map.text()
        sort_lp = self.view.tab_servers.check_last_played.isChecked()
        
        worker = FilterWorker(
            self.all_servers, 
            search_text, 
            map_text, 
            self.favorites, 
            self.config_manager.last_played,
            self.config_manager.default_sort,
            sort_lp
        )
        worker.setAutoDelete(False)
        worker.signals.finished.connect(
            lambda filtered, w=worker: self._on_filters_applied(filtered, w)
        )
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def _on_filters_applied(self, filtered_servers, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)
            
        self.table_loader.load_servers(filtered_servers)

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
                except ValueError: 
                    logger.warning(f"Invalid IP:Port format encountered: {address}")
                

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
            
        elif col == 7:
            try:
                ip, port = ip_item.split(":")
                pinger = PingWorker(ip, int(port))
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, w=pinger: self.update_ping_in_table(addr, p, pl, dt, w)
                ) 
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
            except ValueError:
                logger.warning(f"Invalid IP:Port format encountered: {ip_item}")
            
        elif col == 8:
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
            self.config_manager.last_played[ip_item] = time.time()
            self.config_manager.save()

            self._fetch_mods_then(ip_item, server_data,
                lambda sd, act=action: self.launch_callback(sd, act))

        elif action == "info":
            try:
                ip, port = ip_item.split(":")
                pinger = PingWorker(ip, int(port))
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, sd=server_data, r_idx=row, w=pinger: 
                    self.show_fresh_info(addr, p, pl, dt, sd, r_idx, w)
                )
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
            except ValueError:
                logger.warning(f"Invalid IP:Port format encountered: {ip_item}")

    def _fetch_mods_then(self, address, server_data, on_done):
        try:
            ip, port = address.split(":")
            port = int(port)
        except ValueError:
            logger.warning(f"Invalid IP:Port format encountered: {address}")
            on_done(server_data)
            return

        mods_worker = ModsQueryWorker(ip, port)
        mods_worker.setAutoDelete(False)
        mods_worker.signals.finished.connect(
            lambda addr, mods, sd=server_data, cb=on_done, w=mods_worker:
            self._on_live_mods(mods, sd, cb, w)
        )
        self.active_workers.append(mods_worker)
        self.thread_pool.start(mods_worker)

    def _on_live_mods(self, mods, server_data, on_done, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)

        merged = dict(server_data)
        merged["mods"] = mods
        on_done(merged)

    def show_fresh_info(self, address, ping, players_str, day_time, server_data, row, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)
            
        self.table_servers.setItem(row, 4, self.table_builder.create_item(ping, center=True))
        if players_str:
            self.table_servers.setItem(row, 5, self.table_builder.create_item(players_str, center=True))
            try:
                cur, mx = players_str.split('/')
                server_data['players'] = int(cur)
                server_data['maxplayers'] = int(mx)
            except (ValueError, IndexError):
                logger.warning(f"Invalid players format encountered: {players_str}")
                
        if day_time:
            server_data['dayTime'] = day_time

        self._fetch_mods_then(address, server_data, self._show_info_dialog_with_ping(ping))

    def _show_info_dialog_with_ping(self, ping):
        def _show(server_data):
            dialog = ServerInfoDialog(server_data, ping, self.view)
            dialog.exec()
        return _show

    def prompt_direct_connect(self):
        
        text, ok = QInputDialog.getText(
            self.view, 
            "Direct Connect", 
            "Enter server IP:Port\n(e.g., 192.168.1.100:2302):"
        )
        
        if ok and text.strip():
            try:
                ip, port_str = text.strip().split(":")
                ip = ip.strip()
                game_port = int(port_str.strip())
                
                found_query_port = None
                for s in self.all_servers:
                    s_ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
                    s_gp = str(s.get("gamePort", s.get("port", 0)))
                    if s_ip == ip and s_gp == str(game_port):
                        found_query_port = int(s.get("queryPort", s.get("port", 0)))
                        if found_query_port:
                            break
                
                if found_query_port:
                    query_port = found_query_port
                    fallback = False
                else:
                    query_port = 27016 if game_port == 2302 else game_port + 24714
                    fallback = True
                
                pinger = PingWorker(ip, query_port)
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, i=ip, gp=game_port, qp=query_port, fb=fallback, w=pinger: 
                    self._process_direct_connect(p, i, gp, qp, fb, w)
                )
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
                
            except ValueError:
                logger.warning(f"Invalid IP:Port format encountered: {text.strip()}")
                QMessageBox.warning(self.view, "Error", "Invalid format! Please use IP:Port")

    def _process_direct_connect(self, ping_str, ip, game_port, query_port, fallback, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)

        if ping_str == "999":
            if fallback:
                new_query = game_port + 1
                pinger = PingWorker(ip, new_query)
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(
                    lambda addr, p, pl, dt, i=ip, gp=game_port, qp=new_query, fb=False, w=pinger: 
                    self._process_direct_connect(p, i, gp, qp, fb, w)
                )
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
                return
            else:
                QMessageBox.warning(self.view, "Connection Failed", f"Server {ip}:{game_port} is not responding or offline!")
                return

        mods_worker = ModsQueryWorker(ip, query_port)
        mods_worker.setAutoDelete(False)
        mods_worker.signals.finished.connect(
            lambda addr, mods, i=ip, gp=game_port, w=mods_worker: self._finalize_direct_connect(mods, i, gp, w)
        )
        self.active_workers.append(mods_worker)
        self.thread_pool.start(mods_worker)

    def _finalize_direct_connect(self, mods, ip, game_port, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)

        mock_server = {
            "name": "Direct Connection",
            "ip": ip,
            "gamePort": game_port,
            "mods": mods
        }

        self.launch_callback(mock_server, "play")