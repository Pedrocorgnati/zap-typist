"""Testes unit de LeadCardWidget (pytest-qt)."""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus
from zap_typist.ui.aba1.lead_card import LeadCardWidget, _build_dork_lines


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing  # type: ignore[return-value]
    return QApplication([])


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Factory() as s:
        yield s


@pytest.fixture(scope="module")
def lead_full(db_session: Session) -> Lead:
    lead = Lead(
        nome="Igor",
        ddd="21",
        prefixo="97951",
        desire="quer site para padaria",
        info_extra="padeiro",
        origem="getNinjas",
        status=LeadStatus.query_gerada.value,
        created_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)  # noqa: UP017,
    )
    db_session.add(lead)
    db_session.commit()
    return lead


@pytest.fixture(scope="module")
def lead_minimal(db_session: Session) -> Lead:
    lead = Lead(
        nome="Giovana",
        ddd="43",
        prefixo="9992",
        desire=None,
        info_extra=None,
        origem="getNinjas",
        status=LeadStatus.query_gerada.value,
        created_at=datetime(2026, 5, 4, 11, 0, 0, tzinfo=timezone.utc)  # noqa: UP017,
    )
    db_session.add(lead)
    db_session.commit()
    return lead


def test_card_renders_full_format(qapp: QApplication, qtbot: object, lead_full: Lead) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    labels = card.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert any("Igor" in t and "21" in t and "97951" in t for t in texts), "Header não encontrado"
    assert any("quer site para padaria" in t for t in texts), "Desire não encontrado"
    assert any('"Igor"' in t for t in texts), "Dork principal não encontrada"
    assert any('"padeiro"' in t for t in texts), "Dork info_extra não encontrada"


def test_card_omits_desire_when_empty(
    qapp: QApplication, qtbot: object, lead_minimal: Lead
) -> None:
    card = LeadCardWidget(lead_minimal)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    labels = card.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert not any(t == "None" or t == "" for t in texts), "Label com valor None/vazio encontrado"
    assert not any("quer site" in t for t in texts), "desire não deveria aparecer"


def test_card_omits_info_extra_dork_when_empty(
    qapp: QApplication, qtbot: object, lead_minimal: Lead
) -> None:
    card = LeadCardWidget(lead_minimal)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    labels = card.findChildren(QLabel)
    dork_labels = [lbl for lbl in labels if '"Giovana"' in lbl.text()]
    assert len(dork_labels) == 1, "Deveria haver apenas 1 dork line para lead sem info_extra"


def test_copy_without_info_extra_copies_one_line(
    qapp: QApplication, qtbot: object, lead_minimal: Lead
) -> None:
    card = LeadCardWidget(lead_minimal)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    clip = QGuiApplication.clipboard().text()
    assert "\n" not in clip, "Não deveria haver quebra de linha para lead sem info_extra"
    assert clip.startswith('"Giovana"'), f"Clipboard inicia com conteúdo errado: {clip!r}"


def test_copy_with_info_extra_copies_two_lines(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    clip = QGuiApplication.clipboard().text()
    lines = clip.split("\n")
    assert len(lines) == 2, f"Deveria ter 2 linhas, tem {len(lines)}: {clip!r}"
    assert "21 97951" in lines[0] or "(21) 97951" in lines[0]
    assert "21 97951" in lines[1] or "(21) 97951" in lines[1]


def test_copy_shows_feedback_label_for_2s(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    qtbot.waitUntil(lambda: card._copied_label is not None, timeout=500)  # type: ignore[attr-defined]
    qtbot.waitUntil(lambda: card._copied_label is None, timeout=2500)  # type: ignore[attr-defined]


def test_repeat_copy_resets_timer(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    qtbot.wait(1000)  # type: ignore[attr-defined]
    qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    qtbot.wait(1500)  # type: ignore[attr-defined]
    assert card._copied_label is not None, "Label deveria ainda existir após reset do timer"


def test_widgets_enabled_after_task_4(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    assert card._sufixo_input.isEnabled()
    assert card._submit_btn.isEnabled()
    assert card._discard_btn.isEnabled()


def test_sufixo_validator_rejects_non_digit(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    qtbot.keyClicks(card._sufixo_input, "ab12")  # type: ignore[attr-defined]
    assert card._sufixo_input.text() == "12"


def test_submit_with_valid_sufixo_emits(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    card._sufixo_input.setText("1234")
    with qtbot.waitSignal(card.submit_requested, timeout=500) as blocker:  # type: ignore[attr-defined]
        qtbot.mouseClick(card._submit_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert blocker.args == [lead_full.id, "1234"]


def test_submit_rejects_short_sufixo(
    qapp: QApplication, qtbot: object, lead_full: Lead, monkeypatch: object
) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)  # type: ignore[attr-defined]
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    card._sufixo_input.setText("12")
    spy: list[object] = []
    card.submit_requested.connect(lambda *a: spy.append(a))
    qtbot.mouseClick(card._submit_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert spy == []


def test_submit_rejects_when_e164_invalid(
    qapp: QApplication, qtbot: object, lead_full: Lead, monkeypatch: object
) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)  # type: ignore[attr-defined]
    import zap_typist.ui.aba1.lead_card as lc_module
    monkeypatch.setattr(lc_module, "format_e164", lambda *a: None)  # type: ignore[attr-defined]
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    card._sufixo_input.setText("1234")
    spy: list[object] = []
    card.submit_requested.connect(lambda *a: spy.append(a))
    qtbot.mouseClick(card._submit_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert spy == []


def test_enter_in_sufixo_emits_submit(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    card._sufixo_input.setText("1234")
    with qtbot.waitSignal(card.submit_requested, timeout=500):  # type: ignore[attr-defined]
        qtbot.keyClick(card._sufixo_input, Qt.Key.Key_Return)  # type: ignore[attr-defined]


def test_widgets_disable_after_emit(
    qapp: QApplication, qtbot: object, lead_full: Lead
) -> None:
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    card._sufixo_input.setText("1234")
    qtbot.mouseClick(card._submit_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert not card._sufixo_input.isEnabled()
    assert not card._submit_btn.isEnabled()
    assert not card._discard_btn.isEnabled()


def test_discard_with_yes_emits(
    qapp: QApplication, qtbot: object, lead_full: Lead, monkeypatch: object
) -> None:
    monkeypatch.setattr(  # type: ignore[attr-defined]
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    with qtbot.waitSignal(card.discard_requested, timeout=500) as blocker:  # type: ignore[attr-defined]
        qtbot.mouseClick(card._discard_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert blocker.args == [lead_full.id]


def test_discard_with_no_does_not_emit(
    qapp: QApplication, qtbot: object, lead_full: Lead, monkeypatch: object
) -> None:
    monkeypatch.setattr(  # type: ignore[attr-defined]
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    card = LeadCardWidget(lead_full)
    qtbot.addWidget(card)  # type: ignore[attr-defined]
    spy: list[object] = []
    card.discard_requested.connect(lambda *a: spy.append(a))
    qtbot.mouseClick(card._discard_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
    assert spy == []


def test_no_pii_in_handler_logs(
    qapp: QApplication, qtbot: object, lead_full: Lead, monkeypatch: object
) -> None:
    import logging

    monkeypatch.setattr(  # type: ignore[attr-defined]
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )

    # get_logger() seta propagate=False, então caplog não captura; instalar handler direto.
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    target_logger = logging.getLogger("zap_typist.ui.aba1.lead_card")
    target_logger.addHandler(handler)
    try:
        card = LeadCardWidget(lead_full)
        qtbot.addWidget(card)  # type: ignore[attr-defined]
        card._sufixo_input.setText("1234")
        qtbot.mouseClick(card._submit_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
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
    pii_terms = ["Igor", "97951", "1234", "padeiro", "padaria"]
    for term in pii_terms:
        assert term not in full, f"PII '{term}' encontrado em log: {full}"
    assert any("submit_requested_emitted" in r.getMessage() for r in records), (
        "Log 'submit_requested_emitted' não encontrado — handler direto pode não estar funcionando"
    )


def test_no_pii_in_logs(
    qapp: QApplication, qtbot: object, lead_full: Lead, caplog: object
) -> None:
    import logging

    with caplog.at_level(logging.DEBUG):  # type: ignore[attr-defined]
        card = LeadCardWidget(lead_full)
        qtbot.addWidget(card)  # type: ignore[attr-defined]
        qtbot.mouseClick(card._copy_btn, Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
        qtbot.wait(50)  # type: ignore[attr-defined]

    pii_terms = ["Igor", "97951", "padeiro", "padaria"]
    for record in caplog.records:  # type: ignore[attr-defined]
        for term in pii_terms:
            assert term not in record.getMessage(), (
                f"PII '{term}' encontrado em log: {record.getMessage()}"
            )


def test_build_dork_lines_format(lead_full: Lead) -> None:
    lines = _build_dork_lines(lead_full)
    assert len(lines) == 2
    assert lines[0] == '"Igor" ("21 97951" OR "(21) 97951")'
    assert lines[1] == '"padeiro" ("21 97951" OR "(21) 97951")'
