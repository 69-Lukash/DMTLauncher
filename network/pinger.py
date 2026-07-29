import dmtl_net
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class PingerSignals(QObject):
    finished = pyqtSignal(str, str, str, str) 

class PingWorker(QRunnable):
    def __init__(self, ip, port):
        super().__init__()
        self.address = (ip, port)
        self.signals = PingerSignals()

    def run(self):
        ping_str = "999"
        players_str = ""
        day_time = ""
        
        logger.debug(f"Pinging server {self.address[0]}:{self.address[1]} via Rust (Fast)")
        try:
            ping_str, players_str, day_time = dmtl_net.ping_server(self.address[0], self.address[1])
            logger.debug(f"Ping successful for {self.address[0]}:{self.address[1]} - Ping: {ping_str}ms, Players: {players_str}")
        except Exception as e:
            logger.debug(f"Ping error for {self.address[0]}:{self.address[1]}: {e}")
        finally:
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", ping_str, players_str, day_time)