"""Triggers SQL devem atualizar `updated_at` automaticamente em UPDATE."""

from __future__ import annotations

import time

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from zap_typist.db.models import Flow, Lead, LeadStatus, Setting

pytestmark = [pytest.mark.integration]


def test_lead_updated_at_advances_on_update(file_engine: Engine) -> None:
    SessionFactory = sessionmaker(bind=file_engine)
    with SessionFactory() as s:
        lead = Lead(nome="X", origem="getNinjas", status=LeadStatus.pendente.value)
        s.add(lead)
        s.commit()
        s.refresh(lead)
        original = lead.updated_at
        lead_id = lead.id

    # SQLite CURRENT_TIMESTAMP tem granularidade 1s — espera para diferenca observavel
    time.sleep(1.05)

    with SessionFactory() as s:
        target = s.get(Lead, lead_id)
        assert target is not None
        target.status = LeadStatus.query_gerada.value
        s.commit()
        s.refresh(target)
        assert target.updated_at > original


def test_setting_updated_at_advances_on_update(file_engine: Engine) -> None:
    SessionFactory = sessionmaker(bind=file_engine)
    with SessionFactory() as s:
        setting = Setting(name="trg_test_key", value="v1")
        s.add(setting)
        s.commit()
        s.refresh(setting)
        original = setting.updated_at

    time.sleep(1.05)

    with SessionFactory() as s:
        target = s.get(Setting, "trg_test_key")
        assert target is not None
        target.value = "v2"
        s.commit()
        s.refresh(target)
        assert target.updated_at > original


def test_flow_updated_at_advances_on_update(file_engine: Engine) -> None:
    SessionFactory = sessionmaker(bind=file_engine)
    with SessionFactory() as s:
        import json as _json

        flow = Flow(
            nome="trg-test",
            chrome_profile="default",
            mode="manual",
            time_window_days=_json.dumps(["1", "2", "3"]),
            time_window_start="09:00",
            time_window_end="18:00",
            rate_limit_per_hour=10,
            rate_limit_min_interval=60,
            rate_limit_max_interval=120,
            rate_limit_batch_size=5,
            rate_limit_batch_pause_min=300,
            rate_limit_batch_pause_max=600,
        )
        s.add(flow)
        s.commit()
        s.refresh(flow)
        original = flow.updated_at
        flow_id = flow.id

    time.sleep(1.05)

    with SessionFactory() as s:
        target = s.get(Flow, flow_id)
        assert target is not None
        target.is_active = True
        s.commit()
        s.refresh(target)
        assert target.updated_at > original


def test_wal_mode_active(file_engine: Engine) -> None:
    """PRAGMA journal_mode deve refletir WAL apos connect listener rodar."""
    with file_engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
    assert isinstance(result, str)
    assert result.lower() == "wal"


def test_foreign_keys_pragma_active(file_engine: Engine) -> None:
    """PRAGMA foreign_keys deve estar ativado pelo listener."""
    with file_engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
    assert int(result) == 1


def _unused_session_param_fixture_check(file_session: Session) -> None:
    """Sanity check de fixture file_session — usada apenas como contrato."""
    _ = file_session
