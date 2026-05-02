"""Schema tipado de Setting.value — boundary de reidratacao.

Os defaults vivem em `zap_typist.seeders.build_settings_defaults()` como
`dict[str, str]` (texto puro armazenado em `settings.value`). Modules consumers
(rocks 1-4) reidratam via `load_settings(rows)` que valida tipos e parseia JSON.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel

_JSON_KEYS: frozenset[str] = frozenset({"feminine_names", "desire_rules", "default_window_days"})
_INT_KEYS: frozenset[str] = frozenset(
    {
        "default_rate_per_hour",
        "default_min_interval",
        "default_max_interval",
        "default_batch_size",
        "default_batch_pause_min",
        "default_batch_pause_max",
        "contact_history_window_days",
        "seed_version",
    }
)


class SettingsSchema(BaseModel):
    """Reflete defaults conhecidos em SEED_DEFAULTS, com tipos canonicos."""

    msg_template_1: str
    msg_template_2: str
    msg_template_3: str
    msg_template_4: str
    msg_template_5: str
    sender_nome: str
    sender_profissao: str
    sender_portfolio_url: str
    msg_fallback_block: str
    feminine_names: list[str]
    desire_rules: list[dict[str, Any]]
    default_aba1_origin: str
    default_mode: Literal["manual", "automatico"]
    default_rate_per_hour: int
    default_min_interval: int
    default_max_interval: int
    default_batch_size: int
    default_batch_pause_min: int
    default_batch_pause_max: int
    default_window_days: list[str]
    default_window_start: str
    default_window_end: str
    contact_history_window_days: int
    app_version: str
    seed_version: int


def load_settings(rows: dict[str, str]) -> SettingsSchema:
    """Reidrata `Setting.value` em SettingsSchema typed.

    Args:
        rows: dict de pares (chave, valor-texto) lidos da tabela `settings`.

    Returns:
        SettingsSchema validada (Pydantic levanta `ValidationError` se faltar
        chave obrigatoria ou tipo nao bater).
    """
    parsed: dict[str, Any] = {}
    for key, value in rows.items():
        if key in _JSON_KEYS:
            parsed[key] = json.loads(value)
        elif key in _INT_KEYS:
            parsed[key] = int(value)
        else:
            parsed[key] = value
    return SettingsSchema(**parsed)


__all__ = ["SettingsSchema", "load_settings"]
