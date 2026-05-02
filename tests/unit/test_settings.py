"""Testes basicos de zap_typist.config.settings."""

from __future__ import annotations

import importlib

import pytest


def test_default_settings_debug_false():
    from zap_typist.config.settings import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.debug is False
    assert s.log_level == "INFO"


def test_settings_reads_zap_typist_debug(monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_DEBUG", "true")
    from zap_typist.config.settings import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.debug is True


def test_settings_reads_zap_typist_log_level(monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_LOG_LEVEL", "DEBUG")
    from zap_typist.config.settings import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.log_level == "DEBUG"


def test_settings_rejects_invalid_log_level(monkeypatch):
    monkeypatch.setenv("ZAP_TYPIST_LOG_LEVEL", "VERBOSE")
    from zap_typist.config.settings import Settings

    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_module_singleton_loaded_once():
    import zap_typist.config.settings as s_mod

    importlib.reload(s_mod)
    assert s_mod.settings is not None
    assert isinstance(s_mod.settings.debug, bool)
