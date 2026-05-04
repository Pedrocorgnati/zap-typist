"""Smoke E2E da Aba 1 — cadastro → query generator → submit/discard → DB (ST007)."""
from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus, Setting
from zap_typist.services.lead_service import create_lead
from zap_typist.ui.tab1_gerar_queries import Tab1GerarQueriesWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def e2e_session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory: scoped_session = scoped_session(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    session = factory()
    session.add(Setting(name="default_aba1_origin", value="getNinjas"))
    session.commit()
    factory.remove()
    yield factory
    factory.remove()
    engine.dispose()


@pytest.fixture
def e2e_widget(qtbot, e2e_session_factory):
    w = Tab1GerarQueriesWidget(e2e_session_factory)
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Cenário 1: happy path (submit + discard)
# ---------------------------------------------------------------------------


def test_e2e_happy_path(qtbot, e2e_widget, e2e_session_factory, monkeypatch):
    """Cadastra 2 leads → simula query generator → submit 1 → discard 1 → verifica DB + progress."""
    session = e2e_session_factory()
    session.query(Lead).delete()

    lead_a = create_lead(
        session, desire="criar app", nome="Lead-A", ddd="11", prefixo="98765", info_extra=""
    )
    lead_b = create_lead(
        session, desire="vender mais", nome="Lead-B", ddd="21", prefixo="91234", info_extra=""
    )
    lead_a_id = lead_a.id
    lead_b_id = lead_b.id
    e2e_session_factory.remove()

    # Simula o que QueryGeneratorWorker.run() faria: atualiza leads para query_gerada
    def _mock_run(worker_self: Any) -> None:
        s = worker_self.get_session()
        for ld in s.query(Lead).filter(Lead.status == LeadStatus.pendente.value).all():
            ld.status = LeadStatus.query_gerada.value
        s.commit()

    monkeypatch.setattr(
        "zap_typist.engine.query_generator_worker.QueryGeneratorWorker.run", _mock_run
    )
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)

    # Simula clique /imbound:query invocando handler direto (sem thread real)
    # Primeiro chamamos _on_query_generator_finished para simular término
    session2 = e2e_session_factory()
    for ld in session2.query(Lead).filter(Lead.status == LeadStatus.pendente.value).all():
        ld.status = LeadStatus.query_gerada.value
    session2.commit()
    e2e_session_factory.remove()

    e2e_widget._on_query_generator_finished()

    # Verifica que 2 cards foram renderizados
    from PySide6.QtWidgets import QLabel
    layout = e2e_widget._lead_card_list._content_layout
    non_label = [
        layout.itemAt(i).widget()
        for i in range(layout.count())
        if not isinstance(layout.itemAt(i).widget(), QLabel)
    ]
    assert len(non_label) == 2, f"Esperado 2 cards, obtido {len(non_label)}"

    # Submit lead A (ddd=11, prefixo=98765 → E.164 com sufixo=1234 = +55119876512...)
    e2e_widget._on_card_submit(lead_a_id, "1234")

    session3 = e2e_session_factory()
    la = session3.get(Lead, lead_a_id)
    assert la is not None
    assert la.status == LeadStatus.telefone_preenchido.value
    assert la.sufixo == "1234"
    assert la.numero_e164 is not None and la.numero_e164.startswith("+55")
    e2e_session_factory.remove()

    # Discard lead B
    e2e_widget._on_card_discard(lead_b_id)

    session4 = e2e_session_factory()
    lb = session4.get(Lead, lead_b_id)
    assert lb is not None
    assert lb.status == LeadStatus.descartado.value
    e2e_session_factory.remove()

    # Verifica texto do ProgressLabel
    # x=1 (telefone_preenchido), z=1 (descartado), w=0 pendentes, qg=0 → y=2
    e2e_widget._refresh_progress()
    progress_text = e2e_widget._progress_label.text()
    assert "1 de 2 telefones preenchidos" in progress_text
    assert "1 descartados" in progress_text
    assert "0 pendentes" in progress_text


# ---------------------------------------------------------------------------
# Cenário 2: settings live read (sem restart)
# ---------------------------------------------------------------------------


def test_e2e_settings_live_read(qtbot, e2e_widget, e2e_session_factory, monkeypatch):
    """Altera default_aba1_origin em runtime; próximo lead herda nova origem."""
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)

    session = e2e_session_factory()
    session.query(Lead).delete()

    # Origem inicial: getNinjas (já seedada no fixture)
    lead_a = create_lead(
        session, desire="x", nome="A", ddd="11", prefixo="9876", info_extra=""
    )
    lead_a_id = lead_a.id
    e2e_session_factory.remove()

    session2 = e2e_session_factory()
    la = session2.get(Lead, lead_a_id)
    assert la is not None
    assert la.origem == "getNinjas"
    e2e_session_factory.remove()

    # Atualiza setting para workana
    session3 = e2e_session_factory()
    setting = session3.query(Setting).filter_by(name="default_aba1_origin").one()
    setting.value = "workana"
    session3.commit()
    e2e_session_factory.remove()

    # Cria novo lead sem restart — deve pegar "workana"
    session4 = e2e_session_factory()
    lead_b = create_lead(
        session4, desire="y", nome="B", ddd="21", prefixo="9123", info_extra=""
    )
    lead_b_id = lead_b.id
    e2e_session_factory.remove()

    session5 = e2e_session_factory()
    lb = session5.get(Lead, lead_b_id)
    assert lb is not None
    assert lb.origem == "workana", f"Esperado 'workana', obtido '{lb.origem}'"
    e2e_session_factory.remove()
