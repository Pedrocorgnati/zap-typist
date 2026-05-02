"""Garante que timestamps escritos pelos defaults Python e pelo onupdate
hook sao tz-aware (UTC) quando lidos de volta.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from zap_typist.db.models import Lead, LeadStatus, Setting

pytestmark = [pytest.mark.integration]


def _is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def test_lead_created_at_is_aware(file_engine: Engine) -> None:
    SessionFactory = sessionmaker(bind=file_engine)
    with SessionFactory() as s:
        lead = Lead(nome="Z", origem="getNinjas", status=LeadStatus.pendente.value)
        s.add(lead)
        s.commit()
        s.refresh(lead)

    assert _is_aware(lead.created_at), f"created_at naive: {lead.created_at!r}"
    assert _is_aware(lead.updated_at), f"updated_at naive: {lead.updated_at!r}"
    assert lead.created_at.utcoffset() == UTC.utcoffset(lead.created_at)


def test_setting_updated_at_is_aware_after_onupdate(file_engine: Engine) -> None:
    SessionFactory = sessionmaker(bind=file_engine)
    with SessionFactory() as s:
        setting = Setting(name="ts_test_key", value="v1")
        s.add(setting)
        s.commit()
        s.refresh(setting)

    with SessionFactory() as s:
        target = s.get(Setting, "ts_test_key")
        assert target is not None
        target.value = "v2"
        s.commit()
        s.refresh(target)

    assert _is_aware(target.updated_at), f"updated_at naive: {target.updated_at!r}"


def test_utc_now_helper_is_tz_aware() -> None:
    from zap_typist.db.models import _utc_now

    now = _utc_now()
    assert _is_aware(now)
    assert now.tzinfo == UTC
