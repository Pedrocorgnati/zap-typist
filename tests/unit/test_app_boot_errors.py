"""Smoke tests dos error paths de boot — US-009 [ERROR], US-013 [SUCCESS].

Estes testes EVITAM importar/usar QApplication. Mockam o `_show_blocking_modal`
de `zap_typist.app` para nao tocar em PySide6 — assim coexistem com a suite
existente sem teardown global.
"""
from __future__ import annotations

import errno


def _patch_lock(monkeypatch):
    """Mock SingleInstanceLock para sempre adquirir."""

    class _FakeLock:
        def __init__(self, *_a, **_k):
            pass

        def acquire(self):
            return True

        def release(self):
            return None

        def get_existing_pid(self):
            return None

    monkeypatch.setattr(
        "zap_typist.utils.single_instance.SingleInstanceLock", _FakeLock
    )


def _patch_modal(monkeypatch):
    """Captura chamadas de _show_blocking_modal sem tocar Qt."""
    captured: list[tuple[str, str, str]] = []

    def fake_modal(title, text, level="critical"):
        captured.append((title, text, level))

    monkeypatch.setattr("zap_typist.app._show_blocking_modal", fake_modal)
    return captured


def test_db_runtime_error_returns_schema_exit(monkeypatch, tmp_path):
    """US-009 [ERROR]: validate_schema RuntimeError aborta com EXIT_SCHEMA_ERROR."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    modals = _patch_modal(monkeypatch)

    # garantir que init_db cria normalmente; validate_schema falha
    monkeypatch.setattr("zap_typist.db.session.init_db", lambda: None)
    monkeypatch.setattr(
        "zap_typist.db.session.validate_schema",
        lambda: (_ for _ in ()).throw(
            RuntimeError("Schema invalido: tabelas ausentes=['leads']")
        ),
    )
    # XDG dirs OK (escopo limpo)
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path / "ok"))

    code = app_mod.main()
    assert code == app_mod.EXIT_SCHEMA_ERROR
    assert any("corrompido" in t.lower() for t, *_ in modals), modals


def test_db_disk_full_returns_os_exit(monkeypatch, tmp_path):
    """US-013 [SUCCESS]: ENOSPC em init_db exibe QMessageBox de 'Disco cheio' e exit 2."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    modals = _patch_modal(monkeypatch)

    enospc = OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(
        "zap_typist.db.session.init_db", lambda: (_ for _ in ()).throw(enospc)
    )
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path / "okdisk"))

    code = app_mod.main()
    assert code == app_mod.EXIT_OS_ERROR
    assert any("disco cheio" in t.lower() for t, *_ in modals), modals


def test_db_permission_denied_returns_os_exit(monkeypatch, tmp_path):
    """US-013 [SUCCESS]: PermissionError em init_db exibe QMessageBox legivel e exit 2."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    modals = _patch_modal(monkeypatch)

    perm = PermissionError(13, "Permission denied")
    monkeypatch.setattr(
        "zap_typist.db.session.init_db", lambda: (_ for _ in ()).throw(perm)
    )
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path / "okperm"))

    code = app_mod.main()
    assert code == app_mod.EXIT_OS_ERROR
    assert any(
        "permissao" in t.lower() or "permiss" in t.lower() for t, *_ in modals
    ), modals
