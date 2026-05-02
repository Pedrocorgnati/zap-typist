"""Paths XDG resolvidos no boot.

Resolve diretorios canonicos do app a partir de `~/.local/share/zap-typist`
ou de override via ENV `ZAP_TYPIST_DATA_DIR`. Modulo folha (sem deps internas)
para evitar acoplamento `utils/` -> `db/`.
"""

from __future__ import annotations

import os
from pathlib import Path

_DATA_DIR_OVERRIDE = os.environ.get("ZAP_TYPIST_DATA_DIR")
APP_DATA_DIR: Path = (
    Path(_DATA_DIR_OVERRIDE).expanduser().resolve()
    if _DATA_DIR_OVERRIDE
    else Path.home() / ".local" / "share" / "zap-typist"
)
CACHE_DIR: Path = APP_DATA_DIR / "cache"
DB_PATH: Path = APP_DATA_DIR / "zap_typist.db"
CHROME_PROFILES_DIR: Path = APP_DATA_DIR / "chrome-profiles"
LOCK_FILE: Path = APP_DATA_DIR / ".lock"
LOG_DIR: Path = APP_DATA_DIR / "logs"

__all__ = [
    "APP_DATA_DIR",
    "CACHE_DIR",
    "CHROME_PROFILES_DIR",
    "DB_PATH",
    "LOCK_FILE",
    "LOG_DIR",
]
