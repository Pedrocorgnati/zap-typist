"""Testes do PIIFilter — garante que campos PII sao redactados nos logs (LLD §8.2)."""

from __future__ import annotations

import logging

import pytest

from zap_typist.utils.logger import PII_KEYS, PIIFilter


@pytest.fixture()
def pii_logger(caplog):
    logger = logging.getLogger("test_pii_filter_unit")
    logger.handlers.clear()
    logger.addFilter(PIIFilter())
    logger.setLevel(logging.DEBUG)
    return logger


def test_pii_keys_count():
    assert len(PII_KEYS) == 11  # LLD §8.2 especifica exatamente 11 campos


def test_redaction_string_value(pii_logger, caplog):
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt", extra={"nome": "Maria Silva"})
    record = caplog.records[-1]
    assert record.__dict__.get("nome") == "***FILTRADO***"


def test_pii_fields_redacted(pii_logger, caplog):
    extra = {field: f"valor_{field}" for field in PII_KEYS}
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt_all_pii", extra=extra)
    record = caplog.records[-1]
    for field in PII_KEYS:
        assert record.__dict__.get(field) == "***FILTRADO***", f"campo '{field}' nao foi redactado"


def test_non_pii_fields_preserved(pii_logger, caplog):
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt", extra={"duration_ms": 42, "rows_inserted": 7})
    record = caplog.records[-1]
    assert record.__dict__.get("duration_ms") == 42
    assert record.__dict__.get("rows_inserted") == 7


def test_desire_field_redacted(pii_logger, caplog):
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt", extra={"desire": "Comprar imovel"})
    record = caplog.records[-1]
    assert record.__dict__.get("desire") == "***FILTRADO***"


def test_info_extra_field_redacted(pii_logger, caplog):
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt", extra={"info_extra": "dado sensivel"})
    record = caplog.records[-1]
    assert record.__dict__.get("info_extra") == "***FILTRADO***"


def test_observacao_field_redacted(pii_logger, caplog):
    with caplog.at_level(logging.DEBUG, logger="test_pii_filter_unit"):
        pii_logger.debug("evt", extra={"observacao": "cliente vip"})
    record = caplog.records[-1]
    assert record.__dict__.get("observacao") == "***FILTRADO***"
