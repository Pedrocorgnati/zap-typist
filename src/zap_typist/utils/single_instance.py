from __future__ import annotations

import os
from pathlib import Path

from zap_typist.db.models import LOCK_FILE


class SingleInstanceLock:
    def __init__(self, lock_file: Path = LOCK_FILE) -> None:
        self.lock_file = lock_file
        self._acquired = False

    def acquire(self) -> bool:
        if self.lock_file.exists():
            try:
                pid = int(self.lock_file.read_text().strip())
                if self._is_pid_alive(pid):
                    return False
            except (ValueError, OSError):
                pass  # lock corrompido → sobrescrever
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.write_text(str(os.getpid()))
        self._acquired = True
        return True

    def release(self) -> None:
        if self._acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except OSError:
                pass
        self._acquired = False

    def get_existing_pid(self) -> int | None:
        try:
            return int(self.lock_file.read_text().strip())
        except (ValueError, OSError):
            return None

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        return Path(f"/proc/{pid}/status").exists()

    def __enter__(self) -> SingleInstanceLock:
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
