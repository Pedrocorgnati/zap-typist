"""Cache local em CACHE_DIR (~/.local/share/zap-typist/cache).

US-017: arquivo criado com modo 0600 dentro de CACHE_DIR/0700; falhas de I/O
em write_text NAO propagam — caller continua sem cache (degradacao graciosa).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from zap_typist.db.models import CACHE_DIR

logger = logging.getLogger(__name__)


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
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "cache_read_failed",
                extra={
                    "event": "cache_read_failed",
                    "cache_filename": filename,
                    "errno": exc.errno,
                },
            )
            return None
    return None


def write_text(filename: str, content: str) -> Path | None:
    """Grava `content` em CACHE_DIR/`filename` com perm 0600.

    US-017 [ERROR]: falhas de I/O sao logadas como `cache_write_failed` (sem PII)
    e a funcao retorna None — o caller continua sem cache.
    """
    path = ensure_cache_dir() / filename
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "cache_write_failed",
            extra={
                "event": "cache_write_failed",
                "cache_filename": filename,
                "errno": exc.errno,
            },
        )
        return None
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # filesystem sem suporte a chmod (tmpfs em CI)
    return path
