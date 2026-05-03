"""Testes unitarios do BaseWorker / WorkerSignals."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def mock_sf():
    """session_factory mockado para injecao direta no BaseWorker."""
    sf = MagicMock()
    sf.return_value = MagicMock()  # chamada sf() retorna session mock
    sf.remove = MagicMock()
    return sf


def _make_concrete_worker(mock_sf, cancel_after: int | None = None):
    from zap_typist.engine.base_worker import BaseWorker

    class ConcreteWorker(BaseWorker):
        def __init__(self, sf) -> None:
            super().__init__(session_factory=sf)
            self.iterations = 0

        def run(self) -> None:
            for i in range(100):
                if self.cancel_requested:
                    break
                self.iterations += 1
                self.signals.progress.emit(i)
                if cancel_after is not None and i == cancel_after:
                    break

    return ConcreteWorker(mock_sf)


def test_worker_signals_exist(qapp):
    from zap_typist.engine.base_worker import WorkerSignals

    sig = WorkerSignals()
    for attr in ("progress", "error", "finished", "log_line", "status_update"):
        assert hasattr(sig, attr), f"missing signal: {attr}"


def test_cancel_sets_flag(qapp, mock_sf):
    worker = _make_concrete_worker(mock_sf)
    assert worker.cancel_requested is False
    worker.cancel()
    assert worker.cancel_requested is True


def test_execute_emits_finished(qapp, mock_sf):
    worker = _make_concrete_worker(mock_sf, cancel_after=5)
    received: list[bool] = []
    worker.signals.finished.connect(lambda: received.append(True))

    worker.execute()

    assert received == [True]


def test_execute_emits_error_on_exception(qapp, mock_sf):
    from zap_typist.engine.base_worker import BaseWorker

    class BrokenWorker(BaseWorker):
        def run(self) -> None:
            raise RuntimeError("algo quebrou")

    worker = BrokenWorker(session_factory=mock_sf)
    errors: list[str] = []
    worker.signals.error.connect(errors.append)

    worker.execute()

    assert len(errors) == 1
    assert "algo quebrou" in errors[0]


def test_cancel_stops_iteration(qapp, mock_sf):
    worker = _make_concrete_worker(mock_sf)
    worker.cancel_requested = True

    worker.execute()

    assert worker.iterations == 0


def test_session_remove_called_on_success(qapp, mock_sf):
    from zap_typist.engine.base_worker import BaseWorker

    class WorkerWithSession(BaseWorker):
        def run(self) -> None:
            self.get_session()

    worker = WorkerWithSession(session_factory=mock_sf)
    worker.execute()

    mock_sf.remove.assert_called_once()


def test_session_remove_called_on_exception(qapp, mock_sf):
    from zap_typist.engine.base_worker import BaseWorker

    class FailingWorker(BaseWorker):
        def run(self) -> None:
            self.get_session()
            raise RuntimeError("falhou apos abrir sessao")

    worker = FailingWorker(session_factory=mock_sf)
    worker.execute()

    mock_sf.remove.assert_called_once()
