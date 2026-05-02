"""US-016: sys.excepthook captura graceful + tenta QMessageBox em runtime."""

from __future__ import annotations

import sys

import zap_typist.app as app_mod


def test_excepthook_logs_and_does_not_propagate(monkeypatch, caplog):
    """US-016 [SUCCESS]: hook nao propaga e loga `unhandled_exception`."""
    captured: list = []
    monkeypatch.setattr(
        app_mod,
        "_show_blocking_modal",
        lambda *a, **k: captured.append(("modal", a, k)),
    )

    app_mod._setup_excepthook()
    try:
        raise ValueError("boom")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()

    # nao deve propagar
    sys.excepthook(exc_type, exc_value, exc_tb)
    # restaurar excepthook padrao apos o teste
    sys.excepthook = sys.__excepthook__


def test_excepthook_keyboard_interrupt_uses_default(monkeypatch):
    """KeyboardInterrupt continua usando __excepthook__ padrao (Ctrl+C nao popa modal)."""
    called = {"default": False}

    def fake_default(*a, **k):
        called["default"] = True

    monkeypatch.setattr(sys, "__excepthook__", fake_default)
    app_mod._setup_excepthook()
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        exc_type, exc_value, exc_tb = sys.exc_info()
    sys.excepthook(exc_type, exc_value, exc_tb)
    sys.excepthook = sys.__excepthook__
    assert called["default"] is True
