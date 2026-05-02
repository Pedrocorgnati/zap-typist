from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pytest

# ---------- single_instance ----------


def test_single_instance_acquires_lock(tmp_path: Path) -> None:
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"
    lock = SingleInstanceLock(lock_file)
    assert lock.acquire() is True
    assert lock_file.exists()
    assert int(lock_file.read_text()) == os.getpid()
    lock.release()
    assert not lock_file.exists()


def test_single_instance_blocks_second_when_pid_alive(tmp_path: Path) -> None:
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"
    a = SingleInstanceLock(lock_file)
    b = SingleInstanceLock(lock_file)
    assert a.acquire() is True
    assert b.acquire() is False  # PID atual está vivo
    a.release()


def test_single_instance_overrides_orphan_lock(tmp_path: Path) -> None:
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"
    # PID que muito provavelmente não existe (acima do default máximo do Linux)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text("9999999")

    lock = SingleInstanceLock(lock_file)
    assert lock.acquire() is True, "lock órfão deve ser sobrescrito silenciosamente"
    assert int(lock_file.read_text()) == os.getpid()
    lock.release()


def test_single_instance_context_manager(tmp_path: Path) -> None:
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"
    with SingleInstanceLock(lock_file) as lock:
        acquired = lock.acquire()
        assert acquired is True
        assert lock_file.exists()
    # Após __exit__, release() é chamado mas _acquired pode já ter sido setado
    # Garantir que o arquivo foi removido
    lock.release()  # idempotente


def test_single_instance_get_existing_pid(tmp_path: Path) -> None:
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock_file = tmp_path / ".lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text("12345")

    lock = SingleInstanceLock(lock_file)
    assert lock.get_existing_pid() == 12345


# ---------- logger / PIIFilter ----------


def test_pii_filter_redacts_canonical_fields() -> None:
    from zap_typist.utils.logger import PII_KEYS, PIIFilter

    f = PIIFilter()
    record = logging.LogRecord(
        "x",
        logging.INFO,
        "p",
        1,
        "msg",
        None,
        None,
    )
    for field in PII_KEYS:
        record.__dict__[field] = "valor sensivel"
    record.__dict__["safe"] = "ok"

    assert f.filter(record) is True
    for field in PII_KEYS:
        assert record.__dict__[field] == "***FILTRADO***"
    assert record.__dict__["safe"] == "ok"


def test_json_formatter_emits_valid_json_with_extras() -> None:
    from zap_typist.utils.logger import JsonFormatter

    fmt = JsonFormatter()
    record = logging.LogRecord(
        "zap_typist.test",
        logging.INFO,
        "p",
        1,
        "boot",
        None,
        None,
    )
    record.__dict__["duration_ms"] = 123
    record.__dict__["event"] = "app_started"

    out = fmt.format(record)
    payload = json.loads(out)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "zap_typist.test"
    assert payload["event"] == "app_started"
    assert payload["duration_ms"] == 123


def test_get_logger_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("zap_typist.utils.logger.LOG_DIR", tmp_path)
    # Clear any existing logger with this name to ensure fresh state
    logging.root.manager.loggerDict.pop("zap_typist.idempotent_test", None)
    existing = logging.getLogger("zap_typist.idempotent_test")
    for h in existing.handlers[:]:
        existing.removeHandler(h)

    from zap_typist.utils.logger import get_logger

    a = get_logger("zap_typist.idempotent_test")
    initial_count = len(a.handlers)
    b = get_logger("zap_typist.idempotent_test")
    assert a is b
    # Não duplicou handlers em chamada repetida
    assert len(a.handlers) == initial_count


# ---------- cache ----------


def test_cache_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("zap_typist.utils.cache.CACHE_DIR", tmp_path)
    from zap_typist.utils import cache

    p = cache.write_text("t.txt", "conteudo-utf8-áéí")
    assert p.exists()
    assert cache.read_text("t.txt") == "conteudo-utf8-áéí"
    assert cache.read_text("inexistente.txt") is None
