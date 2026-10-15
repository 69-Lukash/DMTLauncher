import dmtl_core
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class ModsQuerySignals(QObject):
    finished = pyqtSignal(str, list)
    failed = pyqtSignal(str)

class ModsQueryWorker(QRunnable):
    def __init__(self, ip, query_port):
        super().__init__()
        self.address = (ip, query_port)
        self.signals = ModsQuerySignals()

    def run(self):
        addr_str = f"{self.address[0]}:{self.address[1]}"
        logger.debug(f"Querying A2S rules (mods) via Rust for {addr_str}")
        try:
            _, _, _, rust_mods = dmtl_core.query_server_full(self.address[0], self.address[1])
        except Exception as e:
            logger.warning(f"Failed to fetch mods for {addr_str}: {e}")
            self.signals.failed.emit(addr_str)
            return

        mods = [{"steamWorkshopId": ws_id, "name": mod_name} for ws_id, mod_name in rust_mods]
        logger.info(f"Successfully fetched {len(mods)} mods for {addr_str}")
        self.signals.finished.emit(addr_str, mods)