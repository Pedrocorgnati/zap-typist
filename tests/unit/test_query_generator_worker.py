"""Testes do QueryGeneratorWorker."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtCore import QThread
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus
from zap_typist.engine.query_generator_worker import QueryGeneratorWorker
from zap_typist.imbound import query_generator as qg


@pytest.fixture
def Factory(tmp_path, monkeypatch):
    """scoped_session factory, mirroring contrato real de SessionFactory (module-1/TASK-2).

    Importante: ``BaseWorker.execute()`` chama ``self._session_factory.remove()`` no
    finally — usar ``scoped_session`` (não ``sessionmaker`` puro) garante fidelidade
    de contrato e evita silenciar ``AttributeError`` no try/except interno do base.
    """
    monkeypatch.setattr(qg, "CACHE_DIR", tmp_path)
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = scoped_session(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    yield factory
    factory.remove()


def _seed(Factory):
    """Insere lead e LIBERA o registry do scoped_session.

    Crítico: ``Factory.remove()`` ao final garante que a próxima chamada a
    ``Factory()`` (feita pelo worker via ``self.get_session()``) retorne uma
    sessão NOVA — caso contrário o scoped_session devolveria a mesma instância
    cacheada (já fechada pelo ``with``), causando ``ResourceClosedError``.
    """
    with Factory() as s:
        s.add(
            Lead(
                nome="A",
                ddd="11",
                prefixo="9001",
                desire="",
                info_extra="",
                origem="getNinjas",
                status=LeadStatus.pendente,
            )
        )
        s.commit()
    Factory.remove()


def test_worker_run_emits_log_lines(qtbot, Factory):
    _seed(Factory)
    worker = QueryGeneratorWorker(session_factory=Factory)
    msgs: list[str] = []
    worker.signals.log_line.connect(msgs.append)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.execute)
    worker.signals.finished.connect(thread.quit)
    thread.start()
    qtbot.waitUntil(lambda: not thread.isRunning(), timeout=3000)
    assert any("Processando 1 leads" in m for m in msgs)
    assert any("Concluído: 1 leads, 1 queries" in m for m in msgs)


def test_worker_emits_status_update_on_success(qtbot, Factory):
    _seed(Factory)
    worker = QueryGeneratorWorker(session_factory=Factory)
    statuses: list[str] = []
    worker.signals.status_update.connect(statuses.append)
    with qtbot.waitSignal(worker.signals.finished, timeout=3000):
        worker.execute()
    assert any("Queries: +1" in s for s in statuses)


def test_worker_cancel_before_run_emits_cancelled(qtbot, Factory):
    _seed(Factory)
    worker = QueryGeneratorWorker(session_factory=Factory)
    worker.cancel()  # marca cancel_requested antes de execute
    msgs: list[str] = []
    worker.signals.log_line.connect(msgs.append)
    with qtbot.waitSignal(worker.signals.finished, timeout=3000):
        worker.execute()
    assert any("Cancelado" in m for m in msgs)
    with Factory() as s:
        assert s.query(Lead).filter_by(status=LeadStatus.pendente).count() == 1


def test_worker_isolates_exceptions(qtbot, Factory):
    worker = QueryGeneratorWorker(session_factory=Factory)
    msgs: list[str] = []
    statuses: list[str] = []
    worker.signals.log_line.connect(msgs.append)
    worker.signals.status_update.connect(statuses.append)
    with patch(
        "zap_typist.engine.query_generator_worker.generate_queries",
        side_effect=RuntimeError("boom"),
    ):
        with qtbot.waitSignal(worker.signals.finished, timeout=3000):
            worker.execute()
    assert any("Erro" in m for m in msgs)
    assert any("Erro na geração" in s for s in statuses)
    # Mensagem não vaza detalhes do exception
    for m in msgs:
        assert "boom" not in m


def test_worker_does_not_log_pii_via_signals(qtbot, Factory):
    with Factory() as s:
        s.add(
            Lead(
                nome="Igor Sigiloso",
                ddd="21",
                prefixo="9795",
                desire="desejo confidencial",
                info_extra="info top",
                origem="getNinjas",
                status=LeadStatus.pendente,
            )
        )
        s.commit()
    Factory.remove()  # libera registry — ver _seed() para racional
    worker = QueryGeneratorWorker(session_factory=Factory)
    msgs: list[str] = []
    worker.signals.log_line.connect(msgs.append)
    with qtbot.waitSignal(worker.signals.finished, timeout=3000):
        worker.execute()
    blob = "\n".join(msgs)
    assert "Igor Sigiloso" not in blob
    assert "desejo confidencial" not in blob
    assert "info top" not in blob
    assert "9795" not in blob
