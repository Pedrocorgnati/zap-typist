"""Smoke tests dos error paths de boot — US-009 [ERROR], US-013 [SUCCESS].

Estes testes EVITAM importar/usar QApplication. Mockam o `_show_blocking_modal`
de `zap_typist.app` para nao tocar em PySide6 — assim coexistem com a suite
existente sem teardown global.

Cobertura alvo: _boot_os(), _boot_db() e os sad-paths de main() (single-instance
e propagacao de codigos de saida). _boot_qt() nao e testado aqui pois requer
display X11/Wayland — coberto por testes de integracao manuais.

Estrategia de isolamento:
  - APP_DATA_DIR e monkeypatchado via `zap_typist.db.models.APP_DATA_DIR` (nao via
    setenv, pois o valor ja e resolvido em import-time no models.py).
  - _setup_excepthook e neutralizado em todos os testes que chamam main(), evitando
    vazar alteracoes em sys.excepthook entre testes.
  - Sad-paths de mkdir usam um Path mock em vez de patchear pathlib.Path globalmente,
    reduzindo o raio de impacto do patch.
"""

from __future__ import annotations

import errno
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers de mock reutilizaveis
# ---------------------------------------------------------------------------


def _patch_lock(monkeypatch):
    """Mock SingleInstanceLock para sempre adquirir com sucesso."""

    class _FakeLock:
        def __init__(self, *_a, **_k):
            pass

        def acquire(self):
            return True

        def release(self):
            return None

        def get_existing_pid(self):
            return None

    monkeypatch.setattr("zap_typist.utils.single_instance.SingleInstanceLock", _FakeLock)


def _patch_modal(monkeypatch):
    """Captura chamadas de _show_blocking_modal sem tocar Qt."""
    captured: list[tuple[str, str, str]] = []

    def fake_modal(title, text, level="critical"):
        captured.append((title, text, level))

    monkeypatch.setattr("zap_typist.app._show_blocking_modal", fake_modal)
    return captured


def _patch_excepthook(monkeypatch):
    """Neutraliza _setup_excepthook para nao poluir sys.excepthook entre testes."""
    monkeypatch.setattr("zap_typist.app._setup_excepthook", lambda: None)


def _make_failing_path(exc: Exception) -> MagicMock:
    """Retorna um MagicMock de Path cujo .mkdir() levanta `exc`."""
    mock = MagicMock(spec=Path)
    mock.mkdir.side_effect = exc
    return mock


# ---------------------------------------------------------------------------
# Testes originais — DB errors via main()
# ---------------------------------------------------------------------------


def test_db_runtime_error_returns_schema_exit(monkeypatch, tmp_path):
    """US-009 [ERROR]: validate_schema RuntimeError aborta com EXIT_SCHEMA_ERROR."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    _patch_excepthook(monkeypatch)
    modals = _patch_modal(monkeypatch)

    monkeypatch.setattr("zap_typist.db.session.init_db", lambda: None)
    monkeypatch.setattr(
        "zap_typist.db.session.validate_schema",
        lambda: (_ for _ in ()).throw(RuntimeError("Schema invalido: tabelas ausentes=['leads']")),
    )
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", tmp_path / "ok")
    monkeypatch.setattr("zap_typist.utils.cache.ensure_cache_dir", lambda: None)
    monkeypatch.setattr("zap_typist.app._is_wayland", lambda: False)

    code = app_mod.main()
    assert code == app_mod.EXIT_SCHEMA_ERROR
    assert any("corrompido" in t.lower() for t, *_ in modals), modals


def test_db_disk_full_returns_os_exit(monkeypatch, tmp_path):
    """US-013 [SUCCESS]: ENOSPC em init_db exibe QMessageBox de 'Disco cheio' e exit 2."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    _patch_excepthook(monkeypatch)
    modals = _patch_modal(monkeypatch)

    enospc = OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr("zap_typist.db.session.init_db", lambda: (_ for _ in ()).throw(enospc))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", tmp_path / "okdisk")
    monkeypatch.setattr("zap_typist.utils.cache.ensure_cache_dir", lambda: None)
    monkeypatch.setattr("zap_typist.app._is_wayland", lambda: False)

    code = app_mod.main()
    assert code == app_mod.EXIT_OS_ERROR
    assert any("disco cheio" in t.lower() for t, *_ in modals), modals


def test_db_permission_denied_returns_os_exit(monkeypatch, tmp_path):
    """US-013 [SUCCESS]: PermissionError em init_db exibe QMessageBox legivel e exit 2."""
    from zap_typist import app as app_mod

    _patch_lock(monkeypatch)
    _patch_excepthook(monkeypatch)
    modals = _patch_modal(monkeypatch)

    perm = PermissionError(13, "Permission denied")
    monkeypatch.setattr("zap_typist.db.session.init_db", lambda: (_ for _ in ()).throw(perm))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", tmp_path / "okperm")
    monkeypatch.setattr("zap_typist.utils.cache.ensure_cache_dir", lambda: None)
    monkeypatch.setattr("zap_typist.app._is_wayland", lambda: False)

    code = app_mod.main()
    assert code == app_mod.EXIT_OS_ERROR
    assert any("permissao" in t.lower() or "permiss" in t.lower() for t, *_ in modals), modals


# ---------------------------------------------------------------------------
# Sad paths de main() — single-instance e lock.release() no finally
# ---------------------------------------------------------------------------


def test_single_instance_blocked_returns_lock_exit(monkeypatch):
    """EXIT_LOCK quando outra instancia ja esta rodando (lock.acquire() = False)."""
    from zap_typist import app as app_mod

    class _BlockedLock:
        def __init__(self, *_a, **_k):
            pass

        def acquire(self):
            return False

        def release(self):
            return None

        def get_existing_pid(self):
            return 9999

    monkeypatch.setattr("zap_typist.utils.single_instance.SingleInstanceLock", _BlockedLock)
    _patch_excepthook(monkeypatch)
    modals = _patch_modal(monkeypatch)

    code = app_mod.main()
    assert code == app_mod.EXIT_LOCK
    assert len(modals) == 1
    assert modals[0][2] == "critical"
    assert "9999" in modals[0][1]


def test_lock_released_when_boot_os_fails(monkeypatch, tmp_path):
    """lock.release() e chamado no finally mesmo quando _boot_os retorna erro."""
    from zap_typist import app as app_mod

    release_calls = []

    class _TrackingLock:
        def __init__(self, *_a, **_k):
            pass

        def acquire(self):
            return True

        def release(self):
            release_calls.append(True)

        def get_existing_pid(self):
            return None

    monkeypatch.setattr("zap_typist.utils.single_instance.SingleInstanceLock", _TrackingLock)
    _patch_excepthook(monkeypatch)
    _patch_modal(monkeypatch)

    failing_dir = _make_failing_path(PermissionError(13, "Permission denied"))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", failing_dir)

    code = app_mod.main()
    assert code == app_mod.EXIT_OS_ERROR
    assert len(release_calls) == 1, "lock.release() deve ser chamado exatamente uma vez"


# ---------------------------------------------------------------------------
# Sad paths de _boot_os() — XDG dirs
# ---------------------------------------------------------------------------


def test_boot_os_xdg_permission_denied(monkeypatch, tmp_path):
    """_boot_os retorna EXIT_OS_ERROR quando mkdir levanta PermissionError."""
    from zap_typist import app as app_mod

    modals = _patch_modal(monkeypatch)
    failing_dir = _make_failing_path(PermissionError(13, "Permission denied"))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", failing_dir)

    result = app_mod._boot_os()
    assert result == app_mod.EXIT_OS_ERROR
    assert any("permissao" in t.lower() or "permiss" in t.lower() for t, *_ in modals), modals


def test_boot_os_xdg_disk_full(monkeypatch, tmp_path):
    """_boot_os retorna EXIT_OS_ERROR quando mkdir levanta ENOSPC."""
    from zap_typist import app as app_mod

    modals = _patch_modal(monkeypatch)
    failing_dir = _make_failing_path(OSError(errno.ENOSPC, "No space left on device"))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", failing_dir)

    result = app_mod._boot_os()
    assert result == app_mod.EXIT_OS_ERROR
    assert any("disco cheio" in t.lower() for t, *_ in modals), modals


def test_boot_os_xdg_generic_oserror(monkeypatch, tmp_path):
    """_boot_os retorna EXIT_OS_ERROR para OSError generica (errno != ENOSPC)."""
    from zap_typist import app as app_mod

    modals = _patch_modal(monkeypatch)
    failing_dir = _make_failing_path(OSError(errno.EIO, "Input/output error"))
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", failing_dir)

    result = app_mod._boot_os()
    assert result == app_mod.EXIT_OS_ERROR
    assert any("i/o" in t.lower() or "erro" in t.lower() for t, *_ in modals), modals


def test_boot_os_wayland_shows_warning_modal_and_continues(monkeypatch, tmp_path):
    """_boot_os retorna None (nao bloqueia) e exibe modal de aviso ao detectar Wayland."""
    from zap_typist import app as app_mod

    modals = _patch_modal(monkeypatch)
    monkeypatch.setattr("zap_typist.db.models.APP_DATA_DIR", tmp_path)
    monkeypatch.setattr("zap_typist.app._is_wayland", lambda: True)
    monkeypatch.setattr("zap_typist.utils.cache.ensure_cache_dir", lambda: None)

    result = app_mod._boot_os()
    assert result is None
    assert len(modals) == 1
    assert modals[0][2] == "warning"
    assert "wayland" in modals[0][0].lower()


# ---------------------------------------------------------------------------
# Sad paths de _boot_db() — init_db erro de I/O nao-ENOSPC
# ---------------------------------------------------------------------------


def test_boot_db_generic_io_error_returns_os_exit(monkeypatch):
    """_boot_db retorna EXIT_OS_ERROR para OSError nao-ENOSPC em init_db."""
    from zap_typist import app as app_mod

    modals = _patch_modal(monkeypatch)

    io_err = OSError(errno.EIO, "Input/output error")
    monkeypatch.setattr("zap_typist.db.session.init_db", lambda: (_ for _ in ()).throw(io_err))

    result = app_mod._boot_db()
    assert result == app_mod.EXIT_OS_ERROR
    assert any("erro ao inicializar" in t.lower() or "i/o" in t.lower() for t, *_ in modals), modals
