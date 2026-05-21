import socket
import time
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class PingerSignals(QObject):
    finished = pyqtSignal(str, str, str) 

class PingWorker(QRunnable):
    def __init__(self, ip, port):
        super().__init__()
        self.address = (ip, port)
        self.signals = PingerSignals()

    def run(self):
        start = time.perf_counter()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', self.address)
            data, _ = sock.recvfrom(2048)
            
            ping = int((time.perf_counter() - start) * 1000)
            
            players_str = ""
            if data.startswith(b'\xff\xff\xff\xffI'):
                idx = 6
                def read_string(d, start_idx):
                    end_idx = d.find(b'\x00', start_idx)
                    if end_idx == -1: return "", start_idx
                    return d[start_idx:end_idx].decode('utf-8', 'ignore'), end_idx + 1

                name, idx = read_string(data, idx)
                map_name, idx = read_string(data, idx)
                folder, idx = read_string(data, idx)
                game, idx = read_string(data, idx)
                
                idx += 2
                
                players = data[idx]
                max_players = data[idx+1]
                players_str = f"{players}/{max_players}"
            
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", str(ping), players_str)
        except Exception:
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", "999", "")