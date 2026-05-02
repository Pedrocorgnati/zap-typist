"""Testes do validador E.164 e do CHECK ck_leads_numero_e164_format."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError

from zap_typist.db.models import Lead, LeadStatus
from zap_typist.domain.validators import PhoneE164, validate_e164


def test_validate_e164_accepts_canonical():
    assert validate_e164("+5511987654321") == "+5511987654321"


def test_validate_e164_rejects_missing_plus():
    with pytest.raises(ValueError):
        validate_e164("5511987654321")


def test_validate_e164_rejects_letters():
    with pytest.raises(ValueError):
        validate_e164("+551198ABC4321")


def test_validate_e164_rejects_too_short():
    with pytest.raises(ValueError):
        validate_e164("+551")


def test_validate_e164_rejects_too_long():
    with pytest.raises(ValueError):
        validate_e164("+5511987654321987")  # 16 digits


def test_phone_e164_pydantic_field_works():
    class M(BaseModel):
        phone: PhoneE164

    M(phone="+5511999999999")
    with pytest.raises(ValidationError):
        M(phone="123")


def test_lead_check_e164_rejects_no_plus(in_memory_session):
    bad = Lead(
        nome="X",
        origem="getNinjas",
        status=LeadStatus.pendente.value,
        numero_e164="5511999999999",
    )
    in_memory_session.add(bad)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_lead_check_e164_rejects_too_short(in_memory_session):
    bad = Lead(
        nome="X",
        origem="getNinjas",
        status=LeadStatus.pendente.value,
        numero_e164="+551",
    )
    in_memory_session.add(bad)
    with pytest.raises(IntegrityError):
        in_memory_session.commit()
    in_memory_session.rollback()


def test_lead_check_e164_accepts_null(in_memory_session):
    ok = Lead(nome="X", origem="getNinjas", status=LeadStatus.pendente.value)
    in_memory_session.add(ok)
    in_memory_session.commit()
    assert ok.id is not None


def test_lead_check_e164_accepts_canonical(in_memory_session):
    ok = Lead(
        nome="Y",
        origem="getNinjas",
        status=LeadStatus.pendente.value,
        numero_e164="+5511987654321",
    )
    in_memory_session.add(ok)
    in_memory_session.commit()
    assert ok.id is not None
