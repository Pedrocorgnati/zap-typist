"""BaseWorker — padrao canonico de workers Qt para zap-typist.

Contrato (STOP-003 enforcement):
    - Cancelamento e SEMPRE cooperativo via self.cancel_requested.
    - QThread.terminate() / QThread.quit() proibidos.
    - session_factory injetado no __init__ (nao importado diretamente de db.session).
    - Scoped session criada via session_factory() (thread-local) e
      removida em finally via session_factory.remove().

Consumidores: module-3 (QueryRunner), module-6a (DispatchEngine).
"""
from __future__ import annotations

import contextlib
import logging
from abc import abstractmethod
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Canal Qt cross-thread para workers do projeto."""

    progress = Signal(int)         # 0-100
    error = Signal(str)            # mensagem human-readable
    finished = Signal()            # sempre emitido (normal | erro | cancel)
    log_line = Signal(str)         # linha para TerminalWidget
    status_update = Signal(str)    # linha curta para QStatusBar


class BaseWorker(QObject):
    """Worker base com cooperative cancel + scoped_session por thread.

    Args:
        session_factory: scoped_session factory injetado (ex: SessionFactory de db/session.py).
                         Injetado para desacoplar o worker do modulo db e facilitar mocking.

    Uso:
        from zap_typist.db.session import SessionFactory

        class MeuWorker(BaseWorker):
            def run(self):
                session = self.get_session()
                for item in items:
                    if self.cancel_requested:
                        break
                    ...

        worker = MeuWorker(session_factory=SessionFactory)
    """

    def __init__(self, session_factory: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._session_factory = session_factory
        self.signals = WorkerSignals()
        self.cancel_requested: bool = False
        self._session: Any = None

    def get_session(self) -> Any:
        """Cria (ou retorna) sessao scoped para a thread atual."""
        self._session = self._session_factory()
        return self._session

    def cancel(self) -> None:
        """Sinaliza cancelamento cooperativo (STOP-003)."""
        self.cancel_requested = True
        logger.info(
            "worker_cancel_requested",
            extra={"worker": type(self).__name__},
        )

    @abstractmethod
    def run(self) -> None:
        """Subclasses implementam. DEVE checar self.cancel_requested em loops."""
        raise NotImplementedError

    def execute(self) -> None:
        """Envelopa run() com try/except/finally para cleanup garantido."""
        try:
            self.run()
        except Exception as exc:
            logger.exception(
                "worker_error",
                extra={"worker": type(self).__name__, "error": str(exc)},
            )
            self.signals.error.emit(str(exc))
        finally:
            if self._session is not None:
                with contextlib.suppress(Exception):
                    self._session_factory.remove()
            self.signals.finished.emit()


__all__ = ["BaseWorker", "WorkerSignals"]
