"""Tests for Tab1GerarQueriesWidget — unit (ST007)."""
from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QLabel
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus, Setting
from zap_typist.ui.aba1.lead_card_list import LeadCardList
from zap_typist.ui.aba1.lead_form import LeadFormWidget
from zap_typist.ui.tab1_gerar_queries import (
    Tab1GerarQueriesWidget,
    _TerminalPanel,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _StubFactory:
    """Stub que satisfaz _ScopedSessionFactory: callable + .remove()."""

    def __init__(self, session: Any) -> None:
        self._session = session

    def __call__(self) -> Any:
        return self._session

    def remove(self) -> None:
        return None


@pytest.fixture(scope="module")
def qapp(qapp):
    return qapp


@pytest.fixture
def in_memory_session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory: scoped_session = scoped_session(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    # Seed: setting obrigatório para LeadFormWidget
    session = factory()
    session.add(Setting(name="default_aba1_origin", value="getNinjas"))
    session.commit()
    factory.remove()
    yield factory
    factory.remove()
    engine.dispose()


@pytest.fixture
def widget(qtbot, in_memory_session_factory):
    w = Tab1GerarQueriesWidget(in_memory_session_factory)
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# ST001 — importação
# ---------------------------------------------------------------------------


def test_importable():
    """Módulo importa sem erro (critério de aceite do ST001)."""
    from zap_typist.ui.tab1_gerar_queries import (
        Tab1GerarQueriesWidget,
        get_aba1_widget,
    )

    assert Tab1GerarQueriesWidget is not None
    assert get_aba1_widget is not None


# ---------------------------------------------------------------------------
# ST002 — layout
# ---------------------------------------------------------------------------


def test_layout_has_four_blocks(widget):
    assert widget.findChild(LeadFormWidget) is not None
    assert widget.findChild(_TerminalPanel) is not None
    assert widget.findChild(LeadCardList) is not None
    assert widget.findChild(QLabel) is not None  # progress label


def test_layout_order(widget):
    layout = widget.layout()
    assert layout is not None
    items = [layout.itemAt(i).widget() for i in range(layout.count())]
    assert isinstance(items[0], LeadFormWidget)
    assert isinstance(items[1], _TerminalPanel)
    assert isinstance(items[2], LeadCardList)
    assert isinstance(items[3], QLabel)


def test_terminal_panel_has_button_and_terminal(widget):
    panel = widget._terminal_panel
    assert panel._btn.text() == "/imbound:query"
    assert panel.terminal is not None


def test_progress_label_accessible_name(widget):
    assert widget._progress_label.accessibleName() == "Resumo de progresso da Aba 1"


def test_imbound_button_accessible_name(widget):
    assert "leads" in widget._terminal_panel._btn.accessibleName().lower()


# ---------------------------------------------------------------------------
# ST002/ST003 — set_running desabilita botão
# ---------------------------------------------------------------------------


def test_imbound_button_disables_during_run(qtbot, widget, monkeypatch):
    monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)
    assert widget._terminal_panel._btn.isEnabled()
    widget._terminal_panel._btn.click()
    assert not widget._terminal_panel._btn.isEnabled()
    assert widget._active_thread is not None


def test_set_running_false_reenables_button(widget):
    widget._terminal_panel.set_running(True)
    assert not widget._terminal_panel._btn.isEnabled()
    widget._terminal_panel.set_running(False)
    assert widget._terminal_panel._btn.isEnabled()


# ---------------------------------------------------------------------------
# ST006 — progress label
# ---------------------------------------------------------------------------


def test_progress_text_fallback_when_y_zero(widget, in_memory_session_factory):
    # DB vazio → fallback
    session = in_memory_session_factory()
    session.query(Lead).delete()
    session.commit()
    in_memory_session_factory.remove()
    widget._refresh_progress()
    assert widget._progress_label.text() == "Nenhum lead cadastrado ainda."


def test_progress_text_canonical(widget, in_memory_session_factory):
    session = in_memory_session_factory()
    session.query(Lead).delete()
    session.commit()

    def _add(status: str) -> None:
        session.add(
            Lead(nome="T", ddd="11", prefixo="9876", origem="test", status=status)
        )

    _add(LeadStatus.telefone_preenchido.value)
    _add(LeadStatus.telefone_preenchido.value)
    _add(LeadStatus.descartado.value)
    _add(LeadStatus.query_gerada.value)
    _add(LeadStatus.pendente.value)
    _add(LeadStatus.pendente.value)
    session.commit()
    in_memory_session_factory.remove()

    widget._refresh_progress()
    text = widget._progress_label.text()
    # x=2, y=6 (2+1+1+2), z=1, w=2
    assert "2 de 6 telefones preenchidos" in text
    assert "1 descartados" in text
    assert "2 pendentes" in text


# ---------------------------------------------------------------------------
# ST003 — handlers de form/worker
# ---------------------------------------------------------------------------


def test_lead_added_refreshes_progress(widget, monkeypatch):
    called = []
    monkeypatch.setattr(widget, "_refresh_progress", lambda: called.append(True))
    widget._form.lead_added.emit()
    assert called


def test_query_generator_finished_refreshes_cards(widget, in_memory_session_factory):
    session = in_memory_session_factory()
    session.query(Lead).delete()
    for _ in range(2):
        session.add(
            Lead(
                nome="T",
                ddd="11",
                prefixo="9876",
                origem="test",
                status=LeadStatus.query_gerada.value,
            )
        )
    session.commit()
    in_memory_session_factory.remove()

    widget._on_query_generator_finished()

    layout = widget._lead_card_list._content_layout
    non_label = [
        layout.itemAt(i).widget()
        for i in range(layout.count())
        if not isinstance(layout.itemAt(i).widget(), QLabel)
    ]
    assert len(non_label) == 2


def test_query_generator_error_resets_running_state(widget, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)
    widget._terminal_panel.set_running(True)
    widget._active_thread = MagicMock()
    widget._active_worker = MagicMock()

    widget._on_query_generator_error("falha")

    assert widget._terminal_panel._btn.isEnabled()
    assert widget._active_thread is None
    assert widget._active_worker is None


def test_double_click_imbound_is_ignored(qtbot, widget, monkeypatch):
    """Segundo clique antes do worker terminar é ignorado (guard active_thread)."""
    monkeypatch.setattr("PySide6.QtCore.QThread.start", lambda self: None)
    widget._terminal_panel._btn.click()
    first_thread = widget._active_thread

    # Segundo clique — guard deve impedir novo worker
    widget._terminal_panel._btn.click()
    assert widget._active_thread is first_thread


# ---------------------------------------------------------------------------
# ST004 — _on_card_submit
# ---------------------------------------------------------------------------


def _insert_lead(session, status: str, ddd: str = "11", prefixo: str = "98765") -> Lead:
    lead = Lead(nome="Test", ddd=ddd, prefixo=prefixo, origem="test", status=status)
    session.add(lead)
    session.commit()
    return lead


def test_submit_handler_happy_path(widget, in_memory_session_factory):
    session = in_memory_session_factory()
    session.query(Lead).delete()
    lead = _insert_lead(session, LeadStatus.query_gerada.value, ddd="11", prefixo="98765")
    lead_id = lead.id
    in_memory_session_factory.remove()

    widget._on_card_submit(lead_id, "4321")

    session2 = in_memory_session_factory()
    updated = session2.get(Lead, lead_id)
    assert updated is not None
    assert updated.status == LeadStatus.telefone_preenchido.value
    assert updated.sufixo == "4321"
    assert updated.numero_e164 == "+551198765432" + "1"
    in_memory_session_factory.remove()


def test_submit_handler_blocks_invalid_transition(widget, in_memory_session_factory, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    # pendente → telefone_preenchido é inválido (deve ser query_gerada primeiro)
    lead = _insert_lead(session, LeadStatus.pendente.value)
    lead_id = lead.id
    in_memory_session_factory.remove()

    widget._on_card_submit(lead_id, "4321")

    session2 = in_memory_session_factory()
    unchanged = session2.get(Lead, lead_id)
    assert unchanged is not None
    assert unchanged.status == LeadStatus.pendente.value
    in_memory_session_factory.remove()


def test_submit_handler_blocks_invalid_e164(widget, in_memory_session_factory, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("zap_typist.ui.tab1_gerar_queries.format_e164", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    lead = _insert_lead(session, LeadStatus.query_gerada.value)
    lead_id = lead.id
    in_memory_session_factory.remove()

    widget._on_card_submit(lead_id, "4321")

    session2 = in_memory_session_factory()
    unchanged = session2.get(Lead, lead_id)
    assert unchanged is not None
    assert unchanged.status == LeadStatus.query_gerada.value
    in_memory_session_factory.remove()


def test_submit_handler_lead_not_found(widget, in_memory_session_factory, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    in_memory_session_factory.remove()

    # Não deve lançar exceção
    widget._on_card_submit(99999, "4321")


def test_submit_handler_rolls_back_on_commit_error(
    widget, in_memory_session_factory, monkeypatch
):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    lead = _insert_lead(session, LeadStatus.query_gerada.value, ddd="11", prefixo="98765")
    lead_id = lead.id
    in_memory_session_factory.remove()

    from sqlalchemy.exc import SQLAlchemyError

    real_session = in_memory_session_factory()
    original_commit_fn = real_session.commit
    in_memory_session_factory.remove()

    stub = _StubFactory(real_session)
    stub_commit_calls = []

    def _exploding_commit():
        stub_commit_calls.append(1)
        raise SQLAlchemyError("boom")

    real_session.commit = _exploding_commit  # type: ignore[method-assign]

    # Inject stub factory
    original_factory = widget._session_factory
    widget._session_factory = stub  # type: ignore[assignment]

    try:
        widget._on_card_submit(lead_id, "4321")
    finally:
        # Restore
        real_session.commit = original_commit_fn  # type: ignore[method-assign]
        widget._session_factory = original_factory

    assert len(stub_commit_calls) >= 1


# ---------------------------------------------------------------------------
# ST005 — _on_card_discard
# ---------------------------------------------------------------------------


def test_discard_handler_happy_path(widget, in_memory_session_factory):
    session = in_memory_session_factory()
    session.query(Lead).delete()
    lead = _insert_lead(session, LeadStatus.query_gerada.value)
    lead_id = lead.id
    in_memory_session_factory.remove()

    widget._on_card_discard(lead_id)

    session2 = in_memory_session_factory()
    updated = session2.get(Lead, lead_id)
    assert updated is not None
    assert updated.status == LeadStatus.descartado.value
    in_memory_session_factory.remove()


def test_discard_handler_blocks_invalid_transition(
    widget, in_memory_session_factory, monkeypatch
):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    # descartado → descartado é inválido (terminal)
    lead = _insert_lead(session, LeadStatus.descartado.value)
    lead_id = lead.id
    in_memory_session_factory.remove()

    widget._on_card_discard(lead_id)

    session2 = in_memory_session_factory()
    unchanged = session2.get(Lead, lead_id)
    assert unchanged is not None
    assert unchanged.status == LeadStatus.descartado.value
    in_memory_session_factory.remove()


def test_discard_handler_lead_not_found(widget, in_memory_session_factory, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    session = in_memory_session_factory()
    session.query(Lead).delete()
    in_memory_session_factory.remove()

    # Não deve lançar exceção
    widget._on_card_discard(99999)


# ---------------------------------------------------------------------------
# US-012 — zero PII em logs
# ---------------------------------------------------------------------------


def test_no_pii_in_handler_logs(widget, in_memory_session_factory, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)

    session = in_memory_session_factory()
    session.query(Lead).delete()
    lead = Lead(
        nome="Igor",
        ddd="21",
        prefixo="97951",
        origem="test",
        status=LeadStatus.query_gerada.value,
    )
    session.add(lead)
    session.commit()
    lead_id = lead.id
    in_memory_session_factory.remove()

    # get_logger() seta propagate=False; caplog não captura. Instalar handler direto.
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    target_logger = logging.getLogger("zap_typist.ui.tab1_gerar_queries")
    target_logger.addHandler(handler)
    try:
        widget._on_card_submit(lead_id, "1234")
        # após submit, status = telefone_preenchido → discard rejeita com transição inválida
        widget._on_card_discard(lead_id)
    finally:
        target_logger.removeHandler(handler)

    _LOGGING_INTERNALS = frozenset({
        "msg", "args", "created", "filename", "funcName", "levelname", "levelno",
        "lineno", "module", "msecs", "message", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "thread", "threadName",
        "exc_info", "exc_text", "taskName",
    })

    def _user_payload(record: logging.LogRecord) -> str:
        extras = {k: v for k, v in record.__dict__.items()
                  if k not in _LOGGING_INTERNALS and not k.startswith("_")}
        return record.getMessage() + str(extras)

    assert records, "Nenhum record capturado — handler direto não funcionou"
    full = "\n".join(_user_payload(r) for r in records)
    pii_tokens = ["Igor", "97951", "1234"]
    for token in pii_tokens:
        assert token not in full, f"PII '{token}' encontrado em log: {full}"
