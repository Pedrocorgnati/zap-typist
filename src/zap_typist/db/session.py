"""Session factory + engine SQLite WAL.

MIGRATION POLICY (ADR-007 planejado, FEAT-skel-034):
v1.0: apenas `Base.metadata.create_all(engine)` — sem Alembic.
Mudancas de schema futuras (v1.x+): scripts Python manuais nomeados
`MIGRATION-vX.Y.Z.py`, executados pelo proprio Pedro antes da nova versao.
Rollback: `git checkout vX.Y.Z && python -m zap_typist`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from zap_typist.config.paths import APP_DATA_DIR, DB_PATH
from zap_typist.db.models import Base

logger = logging.getLogger(__name__)
T = TypeVar("T")

_BUSY_TIMEOUT_MS = 5000

_EXPECTED_TABLES = {"leads", "settings", "flows", "contact_history"}


def _ensure_app_dir() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)


def _create_engine() -> Engine:
    _ensure_app_dir()
    eng = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"timeout": 5, "check_same_thread": False},
        future=True,
    )

    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn: object, _record: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            # PRAGMA nao aceita bindparams; int() garante tipo e neutraliza N-SEC-1.
            cursor.execute(f"PRAGMA busy_timeout={int(_BUSY_TIMEOUT_MS)}")
        finally:
            cursor.close()

    return eng


engine: Engine = _create_engine()

SessionFactory: scoped_session[Session] = scoped_session(
    sessionmaker(engine, expire_on_commit=False, autoflush=False)
)


def get_session() -> Session:
    """Retorna a sessao da thread atual (scoped). Caller fecha com .close() ou try/finally."""
    session: Session = SessionFactory()
    return session


def retry_on_locked(
    fn: Callable[[], T],
    *,
    retries: int = 3,
    delays: tuple[float, ...] = (0.1, 0.5, 2.0),
) -> T:
    """Executa `fn`, fazendo retry em OperationalError 'database is locked'.

    Backoff fixo determinístico: 100ms, 500ms, 2s. Apos `retries` tentativas
    falhadas, propaga a excecao. NUNCA loga `fn` ou seus argumentos (PII).
    """
    last_exc: OperationalError | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            last_exc = exc
            if attempt >= retries:
                break
            wait = delays[min(attempt - 1, len(delays) - 1)]
            logger.warning(
                "db_lock_retry",
                extra={"attempt": attempt, "wait_ms": int(wait * 1000)},
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def init_db() -> None:
    """Cria as 4 tabelas e indices se ainda nao existirem (idempotente)."""
    Base.metadata.create_all(engine)


def validate_schema() -> None:
    """Confirma que as 4 tabelas canonicas existem.

    Raises:
        RuntimeError: se faltar qualquer tabela. App deve abortar com QMessageBox
        legivel (ver TASK-3 / US-009 cenario [ERROR] DB corrompido).
    """
    insp = inspect(engine)
    found = set(insp.get_table_names())
    missing = _EXPECTED_TABLES - found
    if missing:
        raise RuntimeError(
            f"Schema invalido: tabelas ausentes={sorted(missing)}; "
            f"presentes={sorted(found)}. DB pode estar corrompido."
        )
