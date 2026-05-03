"""Fixtures compartilhadas dos testes de module-2-shared-foundations."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def isolated_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Aponta LOG_DIR do logger para diretório temporário e limpa handlers cacheados.

    Garante que get_logger() re-inicializa handlers apontando para tmp_path,
    evitando vazamento de estado entre testes.
    """
    import zap_typist.utils.logger as logger_mod

    monkeypatch.setattr(logger_mod, "LOG_DIR", tmp_path)

    # Limpa handlers de todos os loggers nomeados para que get_logger
    # recrie o RotatingFileHandler apontando para tmp_path.
    manager = logging.Logger.manager
    saved: dict[str, list[logging.Handler]] = {}
    for name, lgr in list(manager.loggerDict.items()):
        if isinstance(lgr, logging.Logger) and lgr.handlers:
            saved[name] = list(lgr.handlers)
            lgr.handlers.clear()

    root = logging.getLogger()
    saved_root = list(root.handlers)

    yield tmp_path

    root.handlers[:] = saved_root
    for name, handlers in saved.items():
        logging.getLogger(name).handlers[:] = handlers
