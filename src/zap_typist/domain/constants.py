"""Constantes operacionais do dominio Zap Typist."""

from __future__ import annotations

RATE_LIMIT_MAX_POR_HORA: int = 30
CONTACT_HISTORY_WINDOW_DAYS: int = 60
ORIGEM_PADRAO_ABA1: str = "getNinjas"

__all__ = [
    "CONTACT_HISTORY_WINDOW_DAYS",
    "ORIGEM_PADRAO_ABA1",
    "RATE_LIMIT_MAX_POR_HORA",
]
