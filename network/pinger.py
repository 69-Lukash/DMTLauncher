import socket
import time
import re
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class PingerSignals(QObject):
    # address, ping, players_str, day_time
    finished = pyqtSignal(str, str, str, str) 

class PingWorker(QRunnable):
    def __init__(self, ip, port):
        super().__init__()
        self.address = (ip, port)
        self.signals = PingerSignals()

    def read_string(self, d, start_idx):
        end_idx = d.find(b'\x00', start_idx)
        if end_idx == -1: return "", start_idx
        return d[start_idx:end_idx].decode('utf-8', 'ignore'), end_idx + 1

    def run(self):
        start = time.perf_counter()
        ping_str = "999"
        players_str = ""
        day_time = ""
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            request = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00'
            data = None
            
            for attempt in range(3):
                try:
                    sock.sendto(request, self.address)
                    data, _ = sock.recvfrom(2048)
                    
                    if data.startswith(b'\xff\xff\xff\xffA'):
                        challenge = data[5:9]
                        request = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00' + challenge
                        continue 
                        
                    break
                except socket.timeout:
                    if attempt == 2:
                        print(f"[DEBUG] Timeout pinging {self.address[0]}:{self.address[1]} (server is ignoring requests)")
                        raise
        
            if data:
                ping_str = str(int((time.perf_counter() - start) * 1000))
                
                if data.startswith(b'\xff\xff\xff\xffI'):
                    idx = 6
                    name, idx = self.read_string(data, idx)
                    map_name, idx = self.read_string(data, idx)
                    folder, idx = self.read_string(data, idx)
                    game, idx = self.read_string(data, idx)
                    
                    idx += 2
                    players = data[idx]
                    max_players = data[idx+1]
                    players_str = f"{players}/{max_players}"
                    
                    idx += 7
                    _, idx = self.read_string(data, idx) # Version
                    
                    if idx < len(data):
                        edf = data[idx]
                        idx += 1
                        
                        if edf & 0x80: idx += 2  # Port
                        if edf & 0x10: idx += 8  # SteamID
                        if edf & 0x40:           # SourceTV
                            idx += 2
                            _, idx = self.read_string(data, idx)
                        if edf & 0x20:           # Keywords
                            keywords, _ = self.read_string(data, idx)
                            
                            match = re.search(r'\b(\d{1,2}:\d{2})\b', keywords)
                            if match:
                                day_time = match.group(1)
        
        except Exception as e:
            print(f"[DEBUG] Ping error {self.address[0]}:{self.address[1]} -> {e}")
        
        finally:
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", ping_str, players_str, day_time)