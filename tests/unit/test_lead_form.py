"""Testes do LeadFormWidget."""
from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus, Setting
from zap_typist.ui.aba1.lead_form import LeadFormWidget


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    Factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with Factory() as s:
        s.add(Setting(name="default_aba1_origin", value="getNinjas"))
        s.commit()
    return Factory


@pytest.fixture
def widget(qtbot, session_factory):
    w = LeadFormWidget(session_factory=session_factory)
    qtbot.addWidget(w)
    w.show()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        QApplication.setActiveWindow(w)
    w.input_nome.setFocus()
    QApplication.processEvents()
    return w


def test_initial_focus_on_nome(widget):
    assert widget.input_nome.hasFocus()


def test_submit_empty_nome_shows_warning(qtbot, widget):
    with patch("zap_typist.ui.aba1.lead_form.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(widget.btn_submit, Qt.MouseButton.LeftButton)
        assert mock_warn.called
        args = mock_warn.call_args[0]
        assert "nome" in args[2]


def test_submit_empty_ddd_shows_warning(qtbot, widget):
    widget.input_nome.setText("Igor")
    with patch("zap_typist.ui.aba1.lead_form.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(widget.btn_submit, Qt.MouseButton.LeftButton)
        assert mock_warn.called
        assert "ddd" in mock_warn.call_args[0][2]


def test_submit_empty_prefixo_shows_warning(qtbot, widget):
    widget.input_nome.setText("Igor")
    widget.input_ddd.setText("21")
    with patch("zap_typist.ui.aba1.lead_form.QMessageBox.warning") as mock_warn:
        qtbot.mouseClick(widget.btn_submit, Qt.MouseButton.LeftButton)
        assert mock_warn.called
        assert "prefixo" in mock_warn.call_args[0][2]


def test_ddd_validator_rejects_letters(widget):
    widget.input_ddd.setText("ab21cd")
    assert widget.input_ddd.text() == "21"


def test_prefixo_validator_rejects_letters(widget):
    widget.input_prefixo.setText("a9b7c95")
    assert widget.input_prefixo.text() == "9795"


def test_submit_valid_inserts_lead_and_emits_signal(qtbot, widget, session_factory):
    widget.input_desire.setText("criar site")
    widget.input_nome.setText("Igor")
    widget.input_ddd.setText("21")
    widget.input_prefixo.setText("9795")
    widget.input_info.setText("confeiteiro")

    with qtbot.waitSignal(widget.lead_added, timeout=2000):
        qtbot.mouseClick(widget.btn_submit, Qt.MouseButton.LeftButton)

    with session_factory() as s:
        leads = s.query(Lead).all()
        assert len(leads) == 1
        lead = leads[0]
        assert lead.nome == "Igor"
        assert lead.ddd == "21"
        assert lead.prefixo == "9795"
        assert lead.desire == "criar site"
        assert lead.info_extra == "confeiteiro"
        assert lead.origem == "getNinjas"
        assert lead.status == LeadStatus.pendente


def test_form_resets_after_success(qtbot, widget):
    widget.input_nome.setText("Igor")
    widget.input_ddd.setText("21")
    widget.input_prefixo.setText("9795")

    with qtbot.waitSignal(widget.lead_added, timeout=2000):
        qtbot.mouseClick(widget.btn_submit, Qt.MouseButton.LeftButton)

    assert widget.input_nome.text() == ""
    assert widget.input_ddd.text() == ""
    assert widget.input_prefixo.text() == ""
    assert widget.input_desire.text() == ""
    assert widget.input_info.text() == ""
    assert widget.input_nome.hasFocus()


def test_enter_in_field_triggers_submit(qtbot, widget):
    widget.input_nome.setText("Igor")
    widget.input_ddd.setText("21")
    widget.input_prefixo.setText("9795")

    with qtbot.waitSignal(widget.lead_added, timeout=2000):
        qtbot.keyClick(widget.input_prefixo, Qt.Key.Key_Return)
