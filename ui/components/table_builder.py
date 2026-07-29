from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton)
from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QFont, QColor

class TableBuilder:
    def __init__(self, table_servers: QTableWidget, table_mods: QTableWidget):
        self.table_servers = table_servers
        self.table_mods = table_mods
        self.current_sort_col = -1
        self.current_sort_order = Qt.SortOrder.AscendingOrder

        self.table_mods.verticalHeader().setDefaultSectionSize(37)
        self.table_servers.verticalHeader().setVisible(False)
        self.table_mods.verticalHeader().setVisible(False)
        self.setup_mod_columns()

    def setup_table_columns(self, sort_callback=None):
        
        headers = [
            QCoreApplication.translate("TableBuilder", "Fav"),
            QCoreApplication.translate("TableBuilder", "Server Name"),
            QCoreApplication.translate("TableBuilder", "Map"),
            QCoreApplication.translate("TableBuilder", "IP"),
            QCoreApplication.translate("TableBuilder", "Ping"),
            QCoreApplication.translate("TableBuilder", "Players"),
            QCoreApplication.translate("TableBuilder", "Sync"),
            QCoreApplication.translate("TableBuilder", "Play")
        ]
        self.table_servers.setColumnCount(len(headers))
        self.table_servers.setHorizontalHeaderLabels(headers)
        
        self.table_servers.setColumnHidden(3, True)

        header = self.table_servers.horizontalHeader()
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        fm = self.table_servers.fontMetrics()
        
        self.table_servers.setColumnWidth(0, max(40, fm.horizontalAdvance(headers[0]) + 15))
        self.table_servers.setColumnWidth(2, max(140, fm.horizontalAdvance(headers[2]) + 30))
        self.table_servers.setColumnWidth(4, max(60, fm.horizontalAdvance(headers[4]) + 30))
        self.table_servers.setColumnWidth(5, max(80, fm.horizontalAdvance(headers[5]) + 30))
        self.table_servers.setColumnWidth(6, max(50, fm.horizontalAdvance(headers[6]) + 30))
        self.table_servers.setColumnWidth(7, max(90, fm.horizontalAdvance(headers[7]) + 30))
        
        if sort_callback:
            header.sectionClicked.connect(sort_callback)

    def setup_mod_columns(self):
        
        headers = [
            QCoreApplication.translate("TableBuilder", "Name"),
            QCoreApplication.translate("TableBuilder", "Author"),
            QCoreApplication.translate("TableBuilder", "Size"),
            QCoreApplication.translate("TableBuilder", "Sync"),
            QCoreApplication.translate("TableBuilder", "Delete")
        ]
        self.table_mods.setHorizontalHeaderLabels(headers)
        
        header = self.table_mods.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        fm = self.table_mods.fontMetrics()
        
        size_content_width = fm.horizontalAdvance("999.9 MB") + 35
        size_header_width = fm.horizontalAdvance(headers[2]) + 30
        
        self.table_mods.setColumnWidth(2, max(size_header_width, size_content_width))
        
        self.table_mods.setColumnWidth(3, max(80, fm.horizontalAdvance(headers[3]) + 60))
        self.table_mods.setColumnWidth(4, max(80, fm.horizontalAdvance(headers[4]) + 55))
        
        self.table_mods.setColumnHidden(1, True)

    def create_item(self, text, center=False):
        item = QTableWidgetItem(str(text))
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return item

    def insert_server_row(self, is_fav: bool, name: str, map_name: str, ip: str, ping: str, players: str, *args):
        row = self.table_servers.rowCount()
        self.table_servers.insertRow(row)
        
        star_font = QFont()
        star_font.setPointSize(18)
        
        fav_icon = "★" if is_fav else "☆"
        item_fav = self.create_item(fav_icon, center=True)
        item_fav.setFont(star_font)
        item_fav.setForeground(QColor("yellow") if is_fav else QColor("gray"))
        
        self.table_servers.setItem(row, 0, item_fav)
        self.table_servers.setItem(row, 1, self.create_item(name))
        self.table_servers.setItem(row, 2, self.create_item(map_name, center=True))
        self.table_servers.setItem(row, 3, self.create_item(ip, center=True))
        self.table_servers.setItem(row, 4, self.create_item(ping, center=True))
        self.table_servers.setItem(row, 5, self.create_item(players, center=True))
        self.table_servers.setItem(row, 6, self.create_item("🔄", center=True))
        self.table_servers.setItem(row, 7, self.create_item(self.table_servers.tr("⚙ Menu"), center=True))

    def insert_mod_row(self, name: str, author: str, size: str, mod_click_callback):
        
        row = self.table_mods.rowCount()
        self.table_mods.insertRow(row)
        self.table_mods.setItem(row, 0, self.create_item(name))
        self.table_mods.setItem(row, 1, self.create_item(author, center=True))
        self.table_mods.setItem(row, 2, self.create_item(size, center=True))

        sync_text = QCoreApplication.translate("TableBuilder", "Sync")
        btn_sync = QPushButton(sync_text)
        btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sync.clicked.connect(lambda checked, b=btn_sync: self._handle_mod_btn(b, 3, mod_click_callback))
        self.table_mods.setCellWidget(row, 3, btn_sync)

        del_text = QCoreApplication.translate("TableBuilder", "Delete")
        btn_delete = QPushButton(del_text)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.clicked.connect(lambda checked, b=btn_delete: self._handle_mod_btn(b, 4, mod_click_callback))
        self.table_mods.setCellWidget(row, 4, btn_delete)

    def _handle_mod_btn(self, btn, col, callback):
        for i in range(self.table_mods.rowCount()):
            if self.table_mods.cellWidget(i, col) == btn:
                callback(i, col)
                break

    def sort_servers_table(self, col):
        if col in [0, 2, 3, 6, 7]:
            return
            
        if self.current_sort_col == col:
            self.current_sort_order = Qt.SortOrder.DescendingOrder if self.current_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self.current_sort_col = col
            self.current_sort_order = Qt.SortOrder.AscendingOrder
            
        rows_data = []
        for row in range(self.table_servers.rowCount()):
            name_item = self.table_servers.item(row, 1)
            if not name_item: continue
            name = name_item.text()
            if "Downloading" in name or "found" in name.lower(): return
                
            fav_item = self.table_servers.item(row, 0)
            is_fav = (fav_item.text() == "★") if fav_item else False
            map_val = self.table_servers.item(row, 2).text() if self.table_servers.item(row, 2) else ""
            ip_val = self.table_servers.item(row, 3).text() if self.table_servers.item(row, 3) else ""
            ping_str = self.table_servers.item(row, 4).text() if self.table_servers.item(row, 4) else "9999"
            players_str = self.table_servers.item(row, 5).text() if self.table_servers.item(row, 5) else "0/0"
            
            try: ping_val = int(ping_str)
            except ValueError: ping_val = 9999
            try: players_val = int(players_str.split('/')[0])
            except (ValueError, IndexError): players_val = -1
            
            sort_key = name.lower() if col == 1 else (ping_val if col == 4 else players_val)
            
            rows_data.append({
                "is_fav": is_fav, "name": name, "map": map_val, 
                "ip": ip_val, "ping": ping_str, "players": players_str, 
                "sort_key": sort_key
            })
            
        rows_data.sort(key=lambda r: r["sort_key"], reverse=(self.current_sort_order == Qt.SortOrder.DescendingOrder))
        rows_data.sort(key=lambda r: r["is_fav"], reverse=True)
        
        self.table_servers.setRowCount(0)
        for r in rows_data:
            self.insert_server_row(r["is_fav"], r["name"], r["map"], r["ip"], r["ping"], r["players"])