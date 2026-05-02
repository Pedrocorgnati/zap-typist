from __future__ import annotations

import contextlib
import json
import logging
import logging.handlers
import os
from typing import Any

from zap_typist.config.paths import LOG_DIR

PII_KEYS = frozenset(
    {
        "nome",
        "numero_e164",
        "desire",
        "info_extra",
        "observacao",
        "mensagem",
        "template_render",
        "desire_adaptado",
        "ddd",
        "prefixo",
        "sufixo",
    }
)

_INTERNAL_RECORD_FIELDS = {
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "exc_info",
    "exc_text",
}


class PIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for field in PII_KEYS:
            if field in record.__dict__:
                record.__dict__[field] = "***FILTRADO***"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        for k, v in record.__dict__.items():
            if k in _INTERNAL_RECORD_FIELDS or k.startswith("_"):
                continue
            payload[k] = v
        return json.dumps(payload, default=str, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        # filesystem sem suporte a chmod (tmpfs em CI) e silenciado
        os.chmod(LOG_DIR, 0o700)

    fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "zap-typist.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(JsonFormatter())
    fh.addFilter(PIIFilter())
    logger.addHandler(fh)

    if os.environ.get("DEBUG"):
        sh = logging.StreamHandler()
        sh.setFormatter(JsonFormatter())
        sh.addFilter(PIIFilter())
        logger.addHandler(sh)

    return logger
