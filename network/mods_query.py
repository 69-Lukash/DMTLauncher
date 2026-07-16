from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
import dayzquery

class ModsQuerySignals(QObject):
    # address ("ip:port"), mods (list[dict])
    finished = pyqtSignal(str, list)


class ModsQueryWorker(QRunnable):

    def __init__(self, ip, query_port, timeout=2.0):
        super().__init__()
        self.address = (ip, query_port)
        self.timeout = timeout
        self.signals = ModsQuerySignals()

    def run(self):
        mods = []
        try:
            rules = dayzquery.dayz_rules(self.address, timeout=self.timeout)

            for m in rules.mods:
                mods.append({
                    "steamWorkshopId": str(m.workshop_id),
                    "name": m.name,
                })
        except Exception as e:
            print(f"[ModsQuery] Failed to fetch mods for {self.address}: {e}")
        finally:
            self.signals.finished.emit(f"{self.address[0]}:{self.address[1]}", mods)
