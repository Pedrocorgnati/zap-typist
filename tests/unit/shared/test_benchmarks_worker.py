"""Benchmark de cooperative-cancel do BaseWorker (STOP-003).

Spawn um worker em loop, dispara cancel() e mede o tempo até o thread terminar.
Não usa QThread.terminate (proibido por STOP-003).

Nota de implementação: workers rodam em threading.Thread (não QThread) para
isolar o teste do Qt event loop — o que se mede é o mecanismo cooperativo
(flag cancel_requested), não o transporte de signal Qt.
cleanup (session_factory.remove()) é chamado por execute(), não por run() direto.
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from zap_typist.engine.base_worker import BaseWorker

TARGET_CANCEL_MS = 200.0  # TASK-0 Parte A
ASSERT_MARGIN = 2.0


@pytest.fixture(scope="module")
def qapp():
    """QApplication necessária para instanciar QObject (WorkerSignals)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _LoopingWorker(BaseWorker):
    """Worker mínimo que adquire sessão e itera até cancel_requested ser True."""

    def run(self) -> None:  # type: ignore[override]
        self.get_session()  # adquire sessão para trigger do remove() no finally
        while not self.cancel_requested:
            time.sleep(0.001)


def test_base_worker_cancel_responds_within_target(qapp) -> None:
    """`cancel()` deve interromper o worker em < 200ms (assert < 400ms)."""
    worker = _LoopingWorker(session_factory=MagicMock())

    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()
    time.sleep(0.05)

    start = time.monotonic()
    worker.cancel()
    thread.join(timeout=1.0)
    elapsed_ms = (time.monotonic() - start) * 1000

    assert not thread.is_alive(), "Worker não respondeu ao cancel — loop não cooperativo"
    assert elapsed_ms < TARGET_CANCEL_MS * ASSERT_MARGIN, (
        f"cancel respondeu em {elapsed_ms:.1f}ms "
        f"(target {TARGET_CANCEL_MS}ms, limite {TARGET_CANCEL_MS * ASSERT_MARGIN}ms)"
    )


def test_base_worker_calls_session_remove_on_finish(qapp) -> None:
    """Após `cancel()` o `SessionFactory.remove()` deve ser chamado via execute()."""
    session_factory = MagicMock()
    worker = _LoopingWorker(session_factory=session_factory)

    # execute() wraps run() com finally que chama session_factory.remove()
    thread = threading.Thread(target=worker.execute, daemon=True)
    thread.start()
    time.sleep(0.05)
    worker.cancel()
    thread.join(timeout=1.0)

    session_factory.remove.assert_called_once()


def test_base_worker_cancel_requested_starts_false(qapp) -> None:
    """`cancel_requested` inicializa False — sanity smoke."""
    worker = _LoopingWorker(session_factory=MagicMock())
    assert worker.cancel_requested is False


def test_no_qthread_terminate_in_production_code() -> None:
    """STOP-003: codebase de produção NÃO pode chamar QThread.terminate().

    Linhas de comentário (# ...) e bullets de docstring (- ...) são ignoradas;
    somente código executável é auditado.
    """
    import pathlib

    src_root = pathlib.Path(__file__).parents[3] / "src" / "zap_typist"
    if not src_root.exists():
        pytest.skip(f"src root not found: {src_root}")
    offending: list[str] = []
    for py in src_root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.lstrip()
            # Ignora linhas de comentário e bullets de docstring.
            if stripped.startswith(("#", "-", "*")):
                continue
            if "QThread.terminate" in line or "self.terminate()" in line:
                offending.append(f"{py.relative_to(src_root)}:{line.rstrip()}")
                break
    assert not offending, f"STOP-003 violado em: {offending}"
