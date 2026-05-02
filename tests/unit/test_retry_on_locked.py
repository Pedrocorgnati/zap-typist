"""Cobertura de retry_on_locked — backoff e retry budget.

Cenarios cobertos:
  - Sucesso na 2a tentativa (retry funciona)
  - Esgotamento do orcamento (3 falhas seguidas -> propaga)
  - Erro nao-locked propaga imediatamente
  - Backoff segue a tabela 100ms / 500ms / 2s sem dormir de verdade
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy.exc import OperationalError

from zap_typist.db.session import retry_on_locked


def _locked_error() -> OperationalError:
    return OperationalError("stmt", {}, Exception("database is locked"))


def _patch_sleep(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda secs: waits.append(secs))
    return waits


def test_retry_succeeds_on_second_attempt(monkeypatch):
    _patch_sleep(monkeypatch)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _locked_error()
        return "ok"

    assert retry_on_locked(fn) == "ok"
    assert calls["n"] == 2


def test_retry_exhausts_budget(monkeypatch):
    _patch_sleep(monkeypatch)

    def fn():
        raise _locked_error()

    with pytest.raises(OperationalError):
        retry_on_locked(fn, retries=3)


def test_retry_propagates_non_lock_error_without_sleep(monkeypatch):
    waits = _patch_sleep(monkeypatch)

    def fn():
        raise OperationalError("stmt", {}, Exception("syntax error"))

    with pytest.raises(OperationalError, match="syntax error"):
        retry_on_locked(fn)
    assert waits == [], "non-locked error nao deve disparar sleep"


def test_retry_uses_backoff_table(monkeypatch):
    waits = _patch_sleep(monkeypatch)

    def fn():
        raise _locked_error()

    with pytest.raises(OperationalError):
        retry_on_locked(fn, retries=3)

    # 3 retries -> 2 sleeps entre as 3 tentativas (apos a ultima nao dorme)
    assert waits == [0.1, 0.5], f"esperado [0.1, 0.5], obtido {waits}"
