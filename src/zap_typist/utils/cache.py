from __future__ import annotations

import os
from pathlib import Path

from zap_typist.db.models import CACHE_DIR


def ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CACHE_DIR, 0o700)
    except OSError:
        pass  # filesystem sem suporte a chmod (tmpfs em CI)
    return CACHE_DIR


def read_text(filename: str) -> str | None:
    path = ensure_cache_dir() / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def write_text(filename: str, content: str) -> Path:
    path = ensure_cache_dir() / filename
    path.write_text(content, encoding="utf-8")
    return path
