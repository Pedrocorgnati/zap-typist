"""QueryGeneratorWorker — wrapper Qt para query_generator (Aba 1)."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject

from zap_typist.engine.base_worker import BaseWorker
from zap_typist.imbound.query_generator import GenerationResult, generate_queries
from zap_typist.utils.logger import get_logger

logger = get_logger(__name__)


class QueryGeneratorWorker(BaseWorker):
    """Executa ``generate_queries`` em thread, emitindo progresso pelo TerminalWidget.

    Contrato (module-2/TASK-3 §BaseWorker):
        - ``__init__(session_factory, parent=None)`` injeta o ``scoped_session``;
          ``super().__init__(session_factory, parent)`` registra a factory na base.
        - ``run()`` é o método override; ``execute()`` (entry-point Qt) já chama
          ``run()`` em try/except e roda ``self._session_factory.remove()`` no finally.
        - Obter sessão via ``self.get_session()`` — NÃO usar
          ``with self._session_factory() as session:`` (factory é ``scoped_session``,
          não context manager).
        - Cooperative cancel via ``self.cancel_requested`` (propagado a
          ``generate_queries`` por ``cancel_check``).
    """

    def __init__(
        self, session_factory: Any, parent: QObject | None = None
    ) -> None:
        super().__init__(session_factory, parent)

    def run(self) -> None:
        session = self.get_session()
        try:
            result: GenerationResult = generate_queries(
                session,
                cancel_check=lambda: self.cancel_requested,
                on_progress=lambda msg: self.signals.log_line.emit(msg),
            )
        except Exception as exc:
            # Logger captura stacktrace; UI recebe apenas tipo da exceção (sem PII, sem detalhe).
            logger.exception("query_generator_worker_failed")
            self.signals.log_line.emit(f"Erro: {type(exc).__name__}.")
            self.signals.status_update.emit("Erro na geração de queries")
            # NÃO re-raise: tratamos aqui para preservar mensagem amigável e evitar
            # duplicação com o handler genérico de BaseWorker.execute().
            return

        if result.cancelled:
            self.signals.status_update.emit("Geração cancelada")
            return

        self.signals.status_update.emit(
            f"Queries: +{result.queries} ({result.leads} leads)"
        )


__all__ = ["QueryGeneratorWorker"]
