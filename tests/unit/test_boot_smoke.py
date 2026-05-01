"""Smoke tests do boot sequence: DB, seed, single-instance, logger."""
from __future__ import annotations

import logging
import time
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base


def test_db_init_under_1s():
    """AC-S-01: DB initialization < 1s."""
    start = time.monotonic()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"DB init demorou {elapsed:.2f}s (esperado < 1s)"
    engine.dispose()


def test_seed_populates_settings():
    """AC-S-02: seed popula >= 25 keys em settings."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(bind=engine))

    import zap_typist.db.seed as seed_mod

    original_factory = seed_mod.SessionFactory

    class FakeFactory:
        def __call__(self):
            return Session()

        def remove(self):
            Session.remove()

    seed_mod.SessionFactory = FakeFactory()
    try:
        count = seed_mod.run_seed(force=True)
        assert count >= 25, f"esperado >= 25 keys, obtido {count}"
    finally:
        seed_mod.SessionFactory = original_factory
        Session.remove()
        engine.dispose()


def test_single_instance_blocks_second(tmp_path):
    """AC-S-03: segunda instancia NAO adquire lock enquanto a primeira esta ativa."""
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"

    lock1 = SingleInstanceLock(lock_file)
    assert lock1.acquire() is True

    lock2 = SingleInstanceLock(lock_file)
    with patch.object(lock2, "_is_pid_alive", return_value=True):
        assert lock2.acquire() is False

    lock1.release()

    lock3 = SingleInstanceLock(lock_file)
    assert lock3.acquire() is True
    lock3.release()


def test_logger_creates_log_file(tmp_path, monkeypatch):
    """AC-S-04: logger cria arquivo rotacionado em LOG_DIR."""
    import zap_typist.utils.logger as logger_mod

    monkeypatch.setattr("zap_typist.utils.logger.LOG_DIR", tmp_path)
    logging.getLogger("test_boot_smoke_logger_unique").handlers.clear()

    logger = logger_mod.get_logger("test_boot_smoke_logger_unique")
    logger.info("test_event")

    log_file = tmp_path / "zap-typist.log"
    assert log_file.exists(), f"log_file nao criado em {tmp_path}"
    content = log_file.read_text()
    assert "test_event" in content, f"evento nao gravado: {content!r}"
