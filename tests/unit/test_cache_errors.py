"""Testes de error handling do cache utility (US-017)."""
from __future__ import annotations

import logging
import os
import stat
from unittest.mock import patch

from zap_typist.utils import cache as cache_mod


def test_write_text_creates_file_with_mode_0600(monkeypatch, tmp_path):
    """US-017 [SUCCESS]: arquivo de cache criado com mode 0600."""
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")
    path = cache_mod.write_text("teste.txt", "conteudo")
    assert path is not None
    assert path.exists()
    mode = stat.S_IMODE(os.stat(path).st_mode)
    # 0o600 esperado em filesystems com suporte a chmod
    assert mode == 0o600, f"esperado 0600, obtido {oct(mode)}"


def test_write_text_oserror_returns_none_and_logs(monkeypatch, tmp_path, caplog):
    """US-017 [ERROR]: OSError em write capturado, log warning, retorna None sem propagar."""
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")

    def boom(self, *a, **k):
        raise OSError(28, "No space left on device")

    with caplog.at_level(logging.WARNING, logger="zap_typist.utils.cache"):
        with patch("pathlib.Path.write_text", boom):
            result = cache_mod.write_text("teste.txt", "x" * 1000)
    assert result is None
    assert any(
        "cache_write_failed" in (rec.message + str(getattr(rec, "event", "")))
        for rec in caplog.records
    ), caplog.records


def test_read_text_oserror_returns_none(monkeypatch, tmp_path, caplog):
    """US-017 [EDGE]: OSError em read tambem nao propaga."""
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")
    path = cache_mod.write_text("existe.txt", "ok")
    assert path is not None

    def boom(self, *a, **k):
        raise OSError(5, "I/O error")

    with caplog.at_level(logging.WARNING, logger="zap_typist.utils.cache"):
        with patch("pathlib.Path.read_text", boom):
            result = cache_mod.read_text("existe.txt")
    assert result is None
