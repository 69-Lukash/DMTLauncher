import sys
import os

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMenu, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThreadPool
from PyQt6.QtGui import QColor, QIcon

from core.api_client import DZSAWorker
from core.table_loader import TableLoader
from core.config_manager import ConfigManager  
from core.pinger import PingWorker
from core.mod_controller import ModController
from core.mod_parser import ModParserWorker
from core.server_filter import apply_local_filters
from core.runner import GameRunner
from ui.dialog_info import ServerInfoDialog
from ui.icon_factory import create_gear_icon
from ui.table_builder import TableBuilder

class DMTLMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(DMTLMainWindow, self).__init__(*args, **kwargs)

        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        assets_dir = os.path.join(BASE_DIR, "assets")
        self.setWindowIcon(QIcon(os.path.join(assets_dir, "icon.png")))

        if sys.platform == "win32":
            app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
            DATA_DIR = os.path.join(app_data, "DMTL")
        else:
            DATA_DIR = os.path.join(str(Path.home()), ".config", "DMTL")

        os.makedirs(DATA_DIR, exist_ok=True)
        
        config_path = os.path.join(DATA_DIR, "config.json")

        uic.loadUi(os.path.join(assets_dir, "main.ui"), self)
        self.tab_servers = uic.loadUi(os.path.join(assets_dir, "tab_servers.ui"))
        self.tab_mods = uic.loadUi(os.path.join(assets_dir, "tab_mods.ui"))
        self.settings_panel = uic.loadUi(os.path.join(assets_dir, "panel_settings.ui"))

        self.tabs.addTab(self.tab_servers, "Servers")
        self.tabs.addTab(self.tab_mods, "Mods")
        
        self.tab_mods.btn_reload.clicked.connect(self.fetch_local_mods)
        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setIcon(create_gear_icon())
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.toggle_settings)
        self.tabs.setCornerWidget(self.btn_settings, Qt.Corner.TopRightCorner)

        self.main_layout.addWidget(self.settings_panel)
        self.settings_panel.setMaximumWidth(0)

        if not sys.platform.startswith("linux") and hasattr(self.settings_panel, 'linux_warning'):
            self.settings_panel.linux_warning.hide()

        self.config_manager = ConfigManager(config_path)
        self.favorites = self.config_manager.get_favorites()
        self.all_servers = []
        self.pinged_servers = set()
        self.active_workers = []

        self.table_loader = TableLoader(self)
        self.table_builder = TableBuilder(self.tab_servers.table_servers, self.tab_mods.table_mods)
        self.mod_controller = ModController(self.tab_mods.table_mods)

        self.thread_pool = QThreadPool.globalInstance()

        self.tab_servers.table_servers.verticalScrollBar().valueChanged.connect(self.ping_visible_servers)
        self.tab_servers.table_servers.cellClicked.connect(self.handle_server_click)
        
        self.tab_servers.search_bar.textChanged.connect(self.trigger_apply_local_filters)
        self.tab_servers.search_map.textChanged.connect(self.trigger_apply_local_filters)

        self.apply_stylesheet()
        self.table_builder.setup_table_columns(self.sort_servers_table)
        self.load_config()
        
        self.settings_panel.input_nick.editingFinished.connect(self.save_config)
        self.settings_panel.input_path.editingFinished.connect(self.save_config)
        self.settings_panel.btn_browse.clicked.connect(self.browse_path)
        
        self.fetch_global_database()
        self.fetch_local_mods()
        
    def fetch_global_database(self):
        self.tab_servers.table_servers.setRowCount(0)
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
        if not hasattr(self, "all_servers") or not self.all_servers:
            return

        search_text = self.tab_servers.search_bar.text()
        map_text = self.tab_servers.search_map.text()
        
        filtered = apply_local_filters(self.all_servers, search_text, map_text, self.favorites)
        self.table_loader.load_servers(filtered)

    def ping_visible_servers(self):
        table = self.tab_servers.table_servers
        viewport = table.viewport()
        
        top_row = table.indexAt(viewport.rect().topLeft()).row()
        bottom_row = table.indexAt(viewport.rect().bottomLeft()).row()
        
        if top_row == -1: return
        if bottom_row == -1: bottom_row = table.rowCount() - 1
        
        start_row = max(0, top_row - 10)
        end_row = min(table.rowCount() - 1, bottom_row + 10)
        
        for row in range(start_row, end_row + 1):
            if table.isRowHidden(row): 
                continue
                
            ip_item = table.item(row, 3)
            if not ip_item: 
                continue
                
            address = ip_item.text()
            
            if address not in self.pinged_servers and address != ":0":
                self.pinged_servers.add(address)
                
                try:
                    ip, port = address.split(":")
                    pinger = PingWorker(ip, int(port))
                    pinger.setAutoDelete(False)
                    pinger.signals.finished.connect(self.update_ping_in_table)
                    self.active_workers.append(pinger)
                    self.thread_pool.start(pinger)
                except ValueError:
                    pass

    def update_ping_in_table(self, address, ping_ms, players_str):
        table = self.tab_servers.table_servers
        for row in range(table.rowCount()):
            item = table.item(row, 3)
            if item and item.text() == address:
                table.setItem(row, 4, self.table_builder.create_item(ping_ms, center=True))
                if players_str:
                    table.setItem(row, 5, self.table_builder.create_item(players_str, center=True))
                break

    def toggle_settings(self):
        width = self.settings_panel.width()
        target_width = 300 if width == 0 else 0
        self.animation = QPropertyAnimation(self.settings_panel, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(width)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.animation.start()

    def browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select DayZ Folder")
        if folder:
            self.settings_panel.input_path.setText(folder)
            self.save_config()
            self.fetch_local_mods()

    def apply_stylesheet(self):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        stylesheet_path = os.path.join(BASE_DIR, "assets", "style.qss")
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except IOError:
            pass

    def load_config(self):
        self.settings_panel.input_nick.setText(self.config_manager.nickname)
        self.settings_panel.input_path.setText(self.config_manager.game_path)

    def save_config(self):
        self.config_manager.nickname = self.settings_panel.input_nick.text() or "Survivor"
        self.config_manager.game_path = self.settings_panel.input_path.text()
        self.config_manager.save()

    def handle_server_action(self, row, action_type):
        ip_item = self.tab_servers.table_servers.item(row, 3).text()

        if action_type in ("play", "load"):
            target_server = None
            for s in self.all_servers:
                s_ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
                s_port = str(s.get("port", s.get("endpoint", {}).get("port", 0)))
                if f"{s_ip}:{s_port}" == ip_item:
                    target_server = s
                    break
            
            if target_server:
                self.pending_launch = (target_server, action_type)
                print("[Launcher] Refreshing mods before launch...")
                self.fetch_local_mods()
                
        elif action_type == "info":
            target_server = None
            for s in self.all_servers:
                s_ip = str(s.get("ip", s.get("endpoint", {}).get("ip", "")))
                s_port = str(s.get("port", s.get("endpoint", {}).get("port", 0)))
                if f"{s_ip}:{s_port}" == ip_item:
                    target_server = s
                    break
            
            if target_server:
                ping_widget = self.tab_servers.table_servers.item(row, 4)
                ping_str = ping_widget.text() if ping_widget else "?"
                dialog = ServerInfoDialog(target_server, ping_str, self)
                dialog.exec()
            else:
                print(f"[INFO] Error: Data for {ip_item} not found in cache.")

    def handle_server_click(self, row, col):
        ip_widget = self.tab_servers.table_servers.item(row, 3)
        if not ip_widget: return
        ip_item = ip_widget.text()

        if col == 0: 
            item = self.tab_servers.table_servers.item(row, col)
            is_currently_fav = (item.text() == "★")
            
            if is_currently_fav:
                item.setText("☆")
                item.setForeground(QColor("gray"))
                self.config_manager.remove_favorite(ip_item)
            else:
                item.setText("★")
                item.setForeground(QColor("yellow"))
                self.config_manager.add_favorite(ip_item)

        elif col == 6:
            print(f"[REFRESH] Fetching live data for {ip_item}...")
            try:
                ip, port = ip_item.split(":")
                pinger = PingWorker(ip, int(port))
                pinger.setAutoDelete(False)
                pinger.signals.finished.connect(self.update_ping_in_table) 
                self.active_workers.append(pinger)
                self.thread_pool.start(pinger)
            except ValueError:
                pass

        elif col == 7:
            menu = QMenu(self.tab_servers.table_servers)
            menu.setCursor(Qt.CursorShape.PointingHandCursor)
            
            action_play = menu.addAction("▶ Play")
            action_load = menu.addAction("📂 Load")
            action_info = menu.addAction("ℹ️ Info")
            
            action_play.triggered.connect(lambda: self.handle_server_action(row, "play"))
            action_load.triggered.connect(lambda: self.handle_server_action(row, "load"))
            action_info.triggered.connect(lambda: self.handle_server_action(row, "info"))
            
            menu.exec(self.sender().cursor().pos())

    def handle_mod_click(self, row, col):
        if col == 3:
            mod_name = self.tab_mods.table_mods.item(row, 0).text()

    def sort_servers_table(self, col):
        self.table_builder.sort_servers_table(col)

    def fetch_local_mods(self):
        self.tab_mods.table_mods.setRowCount(0)

        game_path = self.config_manager.game_path
        if not game_path:
            return 

        worker = ModParserWorker(game_path)
        worker.setAutoDelete(False)
        worker.signals.finished.connect(self.on_mods_loaded)
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def on_mods_loaded(self, mods_data):
        self.tab_mods.table_mods.setRowCount(0)
        self.mod_controller.set_mods_data(mods_data)

        for mod in mods_data:
            self.table_builder.insert_mod_row(
                mod["display_name"], 
                mod["author"], 
                mod["size"], 
                self.mod_controller.handle_mod_action 
            )
            
        if hasattr(self, 'pending_launch') and self.pending_launch:
            target_server, action_type = self.pending_launch
            self.pending_launch = None
            
            if hasattr(self, 'check_and_launch'):
                self.check_and_launch(target_server, action_type)
    
    def check_and_launch(self, server_data, action_type):
        server_mods = server_data.get("mods", [])
        
        local_mod_ids = {
            str(m.get("published_id")) 
            for m in self.mod_controller.mods_data 
            if m.get("published_id")
        }
        
        missing_mods = []
        for sm in server_mods:
            mod_id = str(sm.get("fileId", sm.get("steamWorkshopId", "")))
            if mod_id and mod_id not in local_mod_ids:
                missing_mods.append(sm)
                
        if missing_mods:
            self.show_missing_mods_dialog(missing_mods, server_data, action_type)
        else:
            self.launch_game(server_data, action_type)

    def show_missing_mods_dialog(self, missing_mods, server_data, action_type):
        mods_text = "\n".join([m.get("name", m.get("title", "Unknown Mod")) for m in missing_mods])
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Missing Mods")
        msg.setText(f"Missing {len(missing_mods)} mods for this server. Download them via Steam?")
        msg.setDetailedText(mods_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Ok:
            mod_ids = []
            for sm in missing_mods:
                mod_id = str(sm.get("fileId", sm.get("steamWorkshopId", "")))
                if mod_id.isdigit():
                    mod_ids.append(int(mod_id))
            
            if mod_ids:
                print(f"[Steamworks] Batch subscribing to {len(mod_ids)} mods")
                self.mod_controller.steam_mgr.sync_mods_batch(mod_ids)
            
            QMessageBox.information(self, "Downloading", "Mods added to Steam downloads! Wait for them to finish and try connecting again.")
            
    def launch_game(self, server_data, action_type):
        GameRunner.launch(
            config_manager=self.config_manager,
            mod_controller=self.mod_controller,
            server_data=server_data,
            action=action_type
        )
