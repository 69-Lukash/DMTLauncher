import dmtl_core
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class ModsQuerySignals(QObject):
    finished = pyqtSignal(str, list)

class ModsQueryWorker(QRunnable):
    def __init__(self, ip, query_port, timeout=2.0):
        super().__init__()
        self.address = (ip, query_port)
        self.timeout = timeout
        self.signals = ModsQuerySignals()

    def run(self):
        mods = []
        logger.debug(f"Querying A2S rules (mods) via Rust for {self.address[0]}:{self.address[1]}")
        try:
            _, _, _, rust_mods = dmtl_core.query_server_full(self.address[0], self.address[1])
            
            for ws_id, mod_name in rust_mods:
                mods.append({
                    "steamWorkshopId": ws_id,
                    "name": mod_name,
                })
            logger.info(f"Successfully fetched {len(mods)} mods for {self.address[0]}:{self.address[1]}")
        except Exception as e:
            logger.warning(f"Failed to fetch mods for {self.address[0]}:{self.address[1]}: {e}")
        finally:
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", mods)