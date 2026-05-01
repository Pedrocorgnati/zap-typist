"""Testes unitarios dos modelos SQLAlchemy — tabelas, enums, indices, CHECKs, defaults."""
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from zap_typist.db.models import (
    CONTACT_HISTORY_WINDOW_DAYS,
    RATE_LIMIT_MAX_POR_HORA,
    ContactHistory,
    Flow,
    FlowMode,
    Lead,
    LeadStatus,
    Setting,
)


def test_all_tables_created(in_memory_engine):
    tables = sorted(inspect(in_memory_engine).get_table_names())
    assert tables == ["contact_history", "flows", "leads", "settings"]


def test_lead_status_has_10_values():
    assert len(list(LeadStatus)) == 10
    assert "pendente" in [s.value for s in LeadStatus]
    assert "invalido" in [s.value for s in LeadStatus]


def test_flow_mode_has_2_values():
    assert {m.value for m in FlowMode} == {"manual", "automatico"}


def test_operational_constants():
    assert RATE_LIMIT_MAX_POR_HORA == 30
    assert CONTACT_HISTORY_WINDOW_DAYS == 60


def test_indexes_exist(in_memory_engine):
    ins = inspect(in_memory_engine)
    leads_idx = {i["name"] for i in ins.get_indexes("leads")}
    assert {"idx_leads_status", "idx_leads_numero_e164", "idx_leads_status_created_at"} <= leads_idx
    flows_idx = {i["name"] for i in ins.get_indexes("flows")}
    assert "idx_flows_is_active" in flows_idx
    ch_idx = {i["name"] for i in ins.get_indexes("contact_history")}
    assert {"idx_contact_history_numero_touched", "idx_contact_history_flow_id"} <= ch_idx


def test_lead_insert_minimal(in_memory_session):
    lead = Lead(nome="Maria Silva", origem="getNinjas", status=LeadStatus.pendente.value)
    in_memory_session.add(lead)
    in_memory_session.commit()
    assert lead.id is not None
    assert lead.send_attempts == 0
    assert lead.created_at is not None


def test_lead_status_check_rejects_invalid(in_memory_session):
    bad = Lead(nome="X", origem="getNinjas", status="STATUS_INEXISTENTE")
    in_memory_session.add(bad)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_flow_rate_limit_check_rejects_above_30(in_memory_session):
    f = Flow(
        nome="t",
        chrome_profile="p",
        mode="manual",
        time_window_days="1,2,3,4,5",
        time_window_start="09:00",
        time_window_end="18:00",
        rate_limit_per_hour=31,
        rate_limit_min_interval=10,
        rate_limit_max_interval=20,
        rate_limit_batch_size=5,
        rate_limit_batch_pause_min=60,
        rate_limit_batch_pause_max=120,
    )
    in_memory_session.add(f)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_flow_mode_check_rejects_invalid(in_memory_session):
    f = Flow(
        nome="t",
        chrome_profile="p",
        mode="bogus",
        time_window_days="1",
        time_window_start="09:00",
        time_window_end="18:00",
        rate_limit_per_hour=10,
        rate_limit_min_interval=10,
        rate_limit_max_interval=20,
        rate_limit_batch_size=5,
        rate_limit_batch_pause_min=60,
        rate_limit_batch_pause_max=120,
    )
    in_memory_session.add(f)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_setting_pk_is_name(in_memory_session):
    in_memory_session.add(Setting(name="msg_template_saudacao", value="Oi {nome}"))
    in_memory_session.commit()
    s = in_memory_session.get(Setting, "msg_template_saudacao")
    assert s is not None and s.value == "Oi {nome}"


def test_contact_history_requires_flow(in_memory_session):
    # FK habilitado via event listener no in_memory_engine
    ch = ContactHistory(numero_e164="+5511999999999", flow_id=999)
    in_memory_session.add(ch)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_lead_default_send_attempts_zero(in_memory_session):
    lead = Lead(nome="X", origem="getNinjas", status=LeadStatus.pendente.value)
    in_memory_session.add(lead)
    in_memory_session.commit()
    assert lead.send_attempts == 0
