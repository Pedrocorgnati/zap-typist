"""QueryGeneratorWorker — wrapper Qt para query_generator (Aba 1)."""
from __future__ import annotations

from typing import Any

from zap_typist.engine.base_worker import BaseWorker
from zap_typist.imbound.query_generator import GenerationResult, generate_queries


class QueryGeneratorWorker(BaseWorker):
    """Executa ``generate_queries`` em thread, emitindo progresso pelo TerminalWidget.

    Contrato (module-2/TASK-3 §BaseWorker):
        - ``__init__(session_factory, parent=None)`` injeta o ``scoped_session``;
          ``super().__init__(session_factory, parent)`` registra a factory na base.
        - ``run()`` é o método override; ``execute()`` (entry-point Qt) ja chama
          ``run()`` em try/except e roda ``self._session_factory.remove()`` no finally.
        - Obter sessao via ``self.get_session()`` — NAO usar
          ``with self._session_factory() as session:`` (factory e ``scoped_session``,
          nao context manager).
        - Cooperative cancel via ``self.cancel_requested`` (propagado a
          ``generate_queries`` por ``cancel_check``).
        - Excecoes nao tratadas propagam para BaseWorker.execute(), que loga
          ``worker_failed`` e emite ``signals.error`` para a UI.
    """

    def __init__(self, session_factory: Any, parent: Any = None) -> None:
        super().__init__(session_factory, parent)

    def run(self) -> None:
        session = self.get_session()
        result: GenerationResult = generate_queries(
            session,
            cancel_check=lambda: self.cancel_requested,
            on_progress=lambda msg: self.signals.log_line.emit(msg),
        )

        if result.cancelled:
            self.signals.status_update.emit("Geração cancelada")
            return

        self.signals.status_update.emit(
            f"Queries: +{result.queries} ({result.leads} leads)"
        )


__all__ = ["QueryGeneratorWorker"]
