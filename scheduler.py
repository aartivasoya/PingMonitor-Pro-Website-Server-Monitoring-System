import threading
import time

from monitor import run_monitor_cycle


class MonitorScheduler:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            run_monitor_cycle()
            time.sleep(self.interval_seconds)
