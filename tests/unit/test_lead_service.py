"""Testes do lead_service.create_lead."""
from __future__ import annotations

import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus, Setting
from zap_typist.services.lead_service import (
    DEFAULT_ORIGIN_KEY,
    FALLBACK_ORIGIN,
    create_lead,
)


@pytest.fixture
def Factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _seed_origin(Factory, value: str) -> None:
    with Factory() as s:
        s.add(Setting(name=DEFAULT_ORIGIN_KEY, value=value))
        s.commit()


def test_create_lead_uses_settings_origin(Factory):
    _seed_origin(Factory, "getNinjas")
    with Factory() as s:
        lead = create_lead(
            s,
            desire="x",
            nome="Igor",
            ddd="21",
            prefixo="9795",
            info_extra="",
        )
    with Factory() as s:
        persisted = s.query(Lead).filter_by(id=lead.id).one()
        assert persisted.origem == "getNinjas"
        assert persisted.status == LeadStatus.pendente
        assert persisted.desire == "x"
        assert persisted.info_extra is None  # vazio → NULL


def test_origin_change_at_runtime_reflects(Factory):
    _seed_origin(Factory, "getNinjas")
    with Factory() as s:
        create_lead(s, desire="", nome="A", ddd="11", prefixo="1111", info_extra="")
    with Factory() as s:
        s.query(Setting).filter_by(name=DEFAULT_ORIGIN_KEY).update({"value": "manual"})
        s.commit()
    with Factory() as s:
        create_lead(s, desire="", nome="B", ddd="22", prefixo="2222", info_extra="")
    with Factory() as s:
        leads = s.query(Lead).order_by(Lead.id).all()
        assert leads[0].origem == "getNinjas"
        assert leads[1].origem == "manual"


def test_missing_setting_falls_back(Factory):
    with Factory() as s:
        lead = create_lead(
            s, desire="", nome="A", ddd="11", prefixo="1111", info_extra=""
        )
    with Factory() as s:
        assert s.query(Lead).filter_by(id=lead.id).one().origem == FALLBACK_ORIGIN


def test_logs_no_pii(Factory):
    _seed_origin(Factory, "getNinjas")

    # get_logger() seta propagate=False; instalar handler direto no logger alvo.
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    target_logger = logging.getLogger("zap_typist.services.lead_service")
    target_logger.addHandler(handler)
    try:
        with Factory() as s:
            create_lead(
                s,
                desire="segredo do desire",
                nome="Igor Confidencial",
                ddd="21",
                prefixo="99887",
                info_extra="info secreta",
            )
    finally:
        target_logger.removeHandler(handler)

    assert records, "Nenhum record capturado — handler direto pode não estar funcionando"
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

    full_log = "\n".join(_user_payload(r) for r in records)
    assert "Igor Confidencial" not in full_log
    assert "segredo do desire" not in full_log
    assert "99887" not in full_log
    assert "info secreta" not in full_log
    assert any(r.getMessage() == "lead_added" for r in records)
