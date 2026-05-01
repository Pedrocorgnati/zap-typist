"""Testes unitarios da session factory — WAL pragmas, scoped_session, retry_on_locked."""
import threading

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from zap_typist.db.session import (
    SessionFactory,
    engine,
    get_session,
    retry_on_locked,
)


def test_wal_pragma_active():
    with engine.connect() as c:
        assert c.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_busy_timeout_5000():
    with engine.connect() as c:
        assert c.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_foreign_keys_on():
    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_scoped_session_same_thread_returns_same():
    s1 = get_session()
    s2 = get_session()
    assert s1 is s2
    SessionFactory.remove()


def test_scoped_session_different_thread_returns_different():
    main_s = get_session()
    seen = {}

    def worker():
        seen["s"] = get_session()
        SessionFactory.remove()

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen["s"] is not main_s
    SessionFactory.remove()


def test_retry_on_locked_succeeds_after_retries():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise OperationalError("db", {}, Exception("database is locked"))
        return "ok"

    assert retry_on_locked(flaky, retries=3, delays=(0.0, 0.0, 0.0)) == "ok"
    assert calls["n"] == 3


def test_retry_on_locked_propagates_after_max():
    def always_locked():
        raise OperationalError("db", {}, Exception("database is locked"))

    with pytest.raises(OperationalError):
        retry_on_locked(always_locked, retries=2, delays=(0.0, 0.0))


def test_retry_on_locked_propagates_other_errors_immediately():
    def boom():
        raise OperationalError("db", {}, Exception("disk full"))

    with pytest.raises(OperationalError):
        retry_on_locked(boom, retries=3, delays=(0.0,))


def test_validate_schema_passes_after_init(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path))
    import importlib

    import zap_typist.db.models as _m

    importlib.reload(_m)
    import zap_typist.db.session as _s

    importlib.reload(_s)
    _s.init_db()
    _s.validate_schema()


# ---------------------------------------------------------------------------
# ST010 — Performance de init_db / validate_schema
# ---------------------------------------------------------------------------


def test_init_db_under_1s(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path))
    import importlib
    import time

    import zap_typist.db.models as m

    importlib.reload(m)
    import zap_typist.db.session as s

    importlib.reload(s)
    t0 = time.monotonic()
    s.init_db()
    s.validate_schema()
    assert (time.monotonic() - t0) < 1.0


def test_validate_schema_under_200ms_on_rerun(tmp_path, monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path))
    import importlib
    import time

    import zap_typist.db.models as m

    importlib.reload(m)
    import zap_typist.db.session as s

    importlib.reload(s)
    s.init_db()
    t0 = time.monotonic()
    s.validate_schema()
    assert (time.monotonic() - t0) < 0.2


# ---------------------------------------------------------------------------
# ST012 — Ausencia de PII em logs do retry helper
# ---------------------------------------------------------------------------


def test_retry_on_locked_does_not_log_callable_args(caplog):
    import logging

    caplog.set_level(logging.WARNING, logger="zap_typist.db.session")
    calls = {"n": 0}
    PII = "+5511988887777"

    def flaky_with_pii_in_closure():
        calls["n"] += 1
        if calls["n"] < 2:
            raise OperationalError("db", {}, Exception("database is locked"))
        return PII

    retry_on_locked(flaky_with_pii_in_closure, retries=3, delays=(0.0, 0.0, 0.0))
    for record in caplog.records:
        assert PII not in record.getMessage()
        assert PII not in str(record.__dict__)
