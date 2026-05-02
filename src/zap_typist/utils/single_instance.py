"""Lock cooperativo single-instance — Linux-only por design.

Usa `/proc/{pid}/status` (procfs) para detectar se o PID gravado no `.lock`
ainda esta vivo. macOS e Windows nao sao suportados (ver ADR-002:
docs/zap-typist/project/adrs/ADR-002-pid-lock-cooperativo-linux-only.md).
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from zap_typist.config.paths import LOCK_FILE


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
            with contextlib.suppress(OSError):
                self.lock_file.unlink()
        self._acquired = False

    def get_existing_pid(self) -> int | None:
        try:
            return int(self.lock_file.read_text().strip())
        except (ValueError, OSError):
            return None

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        # Linux-only por design — ver ADR-002.
        return Path(f"/proc/{pid}/status").exists()

    def __enter__(self) -> SingleInstanceLock:
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
