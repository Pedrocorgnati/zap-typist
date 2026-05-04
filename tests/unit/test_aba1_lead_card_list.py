"""Testes unit de LeadCardList (pytest-qt)."""
from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QLabel
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus
from zap_typist.ui.aba1.lead_card import LeadCardWidget
from zap_typist.ui.aba1.lead_card_list import EMPTY_STATE_MSG, ERROR_MSG, LeadCardList


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing  # type: ignore[return-value]
    return QApplication([])


@pytest.fixture
def in_memory_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Factory() as s:
        yield s


def _insert_lead(
    session: Session,
    nome: str,
    status: str,
    created_at: datetime,
    *,
    ddd: str = "11",
    prefixo: str = "9999",
) -> Lead:
    lead = Lead(
        nome=nome,
        ddd=ddd,
        prefixo=prefixo,
        origem="getNinjas",
        status=status,
        created_at=created_at,
    )
    session.add(lead)
    session.commit()
    return lead


def test_empty_state_when_no_leads(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]
    widget.refresh(in_memory_session)
    labels = widget.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert any(EMPTY_STATE_MSG in t for t in texts), "Empty state não exibido"


def test_refresh_filters_by_query_gerada(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    t = datetime(2026, 5, 4, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    _insert_lead(in_memory_session, "A", LeadStatus.pendente.value, t)
    _insert_lead(in_memory_session, "B", LeadStatus.query_gerada.value, t)
    _insert_lead(in_memory_session, "C", LeadStatus.query_gerada.value, t)
    _insert_lead(in_memory_session, "D", LeadStatus.descartado.value, t)

    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]
    widget.refresh(in_memory_session)

    cards = widget.findChildren(LeadCardWidget)
    assert len(cards) == 2, f"Esperava 2 cards, encontrou {len(cards)}"


def test_refresh_orders_by_created_at_desc(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    t1 = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    t2 = datetime(2026, 5, 2, 0, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    t3 = datetime(2026, 5, 3, 0, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    _insert_lead(in_memory_session, "Oldest", LeadStatus.query_gerada.value, t1)
    _insert_lead(in_memory_session, "Middle", LeadStatus.query_gerada.value, t2)
    _insert_lead(in_memory_session, "Newest", LeadStatus.query_gerada.value, t3)

    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]
    widget.refresh(in_memory_session)

    cards = widget.findChildren(LeadCardWidget)
    assert len(cards) >= 3
    assert cards[0]._lead.nome == "Newest", "Primeiro card deveria ser o mais recente"


def test_signals_propagate_to_list(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    t = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    lead = _insert_lead(in_memory_session, "Teste", LeadStatus.query_gerada.value, t)

    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]
    widget.refresh(in_memory_session)

    received: list[tuple[int, str]] = []
    widget.submit_requested.connect(lambda lid, suf: received.append((lid, suf)))

    cards = widget.findChildren(LeadCardWidget)
    target = next(c for c in cards if c._lead.nome == "Teste")
    target.submit_requested.emit(lead.id, "1234")

    assert received == [(lead.id, "1234")], f"Signal não propagou: {received}"


def test_error_state_on_query_exception(
    qapp: QApplication, qtbot: object, caplog: object
) -> None:
    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]

    mock_session = MagicMock(spec=Session)
    mock_session.query.side_effect = SQLAlchemyError("boom")

    with caplog.at_level(logging.ERROR):  # type: ignore[attr-defined]
        widget.refresh(mock_session)  # type: ignore[arg-type]

    labels = widget.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert any(ERROR_MSG in t for t in texts), "Error state não exibido"

    for record in caplog.records:  # type: ignore[attr-defined]
        assert "Igor" not in record.getMessage()


def test_refresh_clears_previous_cards(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    t = datetime(2026, 5, 4, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    leads = [
        _insert_lead(in_memory_session, f"X{i}", LeadStatus.query_gerada.value, t)
        for i in range(3)
    ]

    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]
    widget.refresh(in_memory_session)
    before_count = len(widget.findChildren(LeadCardWidget))
    assert before_count >= 3

    in_memory_session.delete(leads[1])
    in_memory_session.delete(leads[2])
    in_memory_session.commit()

    widget.refresh(in_memory_session)
    after_cards = [
        c for c in widget.findChildren(LeadCardWidget) if c._lead.nome.startswith("X")
    ]
    assert len(after_cards) == 1, "Segundo refresh deveria ter apenas 1 card X*"


def test_no_pii_in_container_logs(
    qapp: QApplication, qtbot: object, in_memory_session: Session
) -> None:
    t = datetime(2026, 5, 4, 10, 0, 0, tzinfo=timezone.utc)  # noqa: UP017
    _insert_lead(in_memory_session, "MarceloPII", LeadStatus.query_gerada.value, t)

    widget = LeadCardList()
    qtbot.addWidget(widget)  # type: ignore[attr-defined]

    # get_logger() seta propagate=False, então caplog não captura; instalar handler direto.
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    target_logger = logging.getLogger("zap_typist.ui.aba1.lead_card_list")
    target_logger.addHandler(handler)
    try:
        widget.refresh(in_memory_session)
    finally:
        target_logger.removeHandler(handler)

    # Verifica apenas mensagem + campos extras do usuário (não metadados internos do logging).
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

    full = "\n".join(_user_payload(r) for r in records)
    assert "MarceloPII" not in full, f"PII 'MarceloPII' encontrado em log: {full}"
    assert any("rendered_lead_cards" in r.getMessage() for r in records), (
        "Log 'rendered_lead_cards' não encontrado — handler direto pode não estar funcionando"
    )
