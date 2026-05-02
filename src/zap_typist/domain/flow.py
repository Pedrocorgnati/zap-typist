"""Modelo de dominio TimeWindow — janela de envio do Flow.

Boundary parser para `Flow.time_window_days` + `time_window_start/end`.
Caller serializa via `TimeWindow.model_dump()` ou `tw.days_json`.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DayLiteral = Literal["1", "2", "3", "4", "5", "6", "7"]


class TimeWindow(BaseModel):
    """Janela de envio: quais dias da semana e qual intervalo HH:MM."""

    days: list[DayLiteral] = Field(min_length=1)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _validate_hhmm(cls, v: str) -> str:
        if not re.fullmatch(r"^[0-2]\d:[0-5]\d$", v):
            raise ValueError(f"esperado HH:MM, recebi {v!r}")
        return v

    @classmethod
    def from_settings_strings(cls, days_json: str, start: str, end: str) -> TimeWindow:
        return cls(days=json.loads(days_json), start=start, end=end)

    @property
    def days_json(self) -> str:
        return json.dumps(self.days)


__all__ = ["DayLiteral", "TimeWindow"]
