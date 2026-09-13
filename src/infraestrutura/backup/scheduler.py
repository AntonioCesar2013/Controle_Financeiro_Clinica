import threading
from datetime import datetime, timezone
import time


class BackupScheduler:
    def __init__(self, service):
        self.service = service
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name='agendador-backup', daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)

    def _run(self):
        due, previous = 0, None
        while not self.stop_event.is_set():
            try:
                config = self.service.config.load()
                signature = (config['backup_enabled'], config['interval_hours'])
                if signature != previous:
                    interval = config['interval_hours'] * 3600
                    try:
                        last = datetime.fromisoformat(self.service.status()['last_attempt'])
                        remaining = max(0, interval - (datetime.now(timezone.utc) - last).total_seconds())
                    except (KeyError, ValueError, TypeError):
                        remaining = 0
                    due, previous = time.monotonic() + remaining, signature
                if config['backup_enabled'] and time.monotonic() >= due:
                    self.service.start()
                    due = time.monotonic() + config['interval_hours'] * 3600
            except Exception:
                self.service._update(scheduler_warning='Agendamento indisponível. Verifique a configuração local.')
            self.stop_event.wait(5)
