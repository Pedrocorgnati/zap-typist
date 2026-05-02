"""Testes do TimeWindow domain model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from zap_typist.domain.flow import TimeWindow


def test_time_window_round_trip_from_settings():
    tw = TimeWindow.from_settings_strings('["1","2","3","4","5"]', "09:00", "18:00")
    assert tw.days == ["1", "2", "3", "4", "5"]
    assert tw.start == "09:00"
    assert tw.end == "18:00"
    assert tw.days_json == '["1", "2", "3", "4", "5"]'


def test_time_window_rejects_empty_days():
    with pytest.raises(ValidationError):
        TimeWindow(days=[], start="09:00", end="18:00")


def test_time_window_rejects_invalid_day():
    with pytest.raises(ValidationError):
        TimeWindow(days=["8"], start="09:00", end="18:00")  # type: ignore[list-item]


def test_time_window_rejects_invalid_time():
    with pytest.raises(ValidationError):
        TimeWindow(days=["1"], start="09:60", end="18:00")
    with pytest.raises(ValidationError):
        TimeWindow(days=["1"], start="9-00", end="18:00")
