"""Testes do boundary parser SettingsSchema.load_settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from zap_typist.domain.settings_schema import SettingsSchema, load_settings
from zap_typist.seeders import build_settings_defaults


def test_load_settings_round_trips_seed_defaults():
    rows = build_settings_defaults()
    parsed = load_settings(rows)
    assert isinstance(parsed, SettingsSchema)
    assert parsed.sender_nome == "Pedro"
    assert parsed.default_mode == "manual"
    assert parsed.default_rate_per_hour == 12
    assert parsed.contact_history_window_days == 60
    assert isinstance(parsed.feminine_names, list)
    assert len(parsed.feminine_names) > 0
    assert parsed.default_window_days == ["1", "2", "3", "4", "5"]


def test_load_settings_rejects_missing_key():
    rows = build_settings_defaults()
    del rows["sender_nome"]
    with pytest.raises(ValidationError):
        load_settings(rows)


def test_load_settings_rejects_invalid_mode():
    rows = build_settings_defaults()
    rows["default_mode"] = "auto-pilot"
    with pytest.raises(ValidationError):
        load_settings(rows)


def test_load_settings_rejects_non_int_for_int_key():
    rows = build_settings_defaults()
    rows["default_rate_per_hour"] = "doze"
    with pytest.raises(ValueError):
        load_settings(rows)
