"""Fixtures de integracao: SQLite file-based em tmp dir + WAL real + triggers.

Diferente de tests/conftest.py (in-memory), aqui usamos arquivo real para
exercitar `journal_mode=WAL`, `foreign_keys=ON` e os triggers `updated_at`
que sao registrados no `Base.metadata.create_all`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from zap_typist.db.models import Base


@pytest.fixture
def file_engine(tmp_path: Path) -> Iterator[Engine]:
    """Engine SQLite file-based com WAL + FK + triggers."""
    db_path = tmp_path / "zap_typist.db"
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"timeout": 5, "check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn: object, _record: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def file_session(file_engine: Engine) -> Iterator[Session]:
    """Session factory file-based; rollback ao final."""
    SessionFactory = sessionmaker(bind=file_engine, expire_on_commit=False)
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
