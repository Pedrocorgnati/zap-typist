"""Fixtures compartilhadas da suite de testes do Zap Typist.

TASK-4 expandira este arquivo com factories (LeadFactory, FlowFactory, SettingFactory)
e smoke tests de boot.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from zap_typist.db.models import Base


@pytest.fixture
def in_memory_engine():
    """Engine SQLite in-memory com foreign_keys=ON (via event listener)."""
    _engine = create_engine("sqlite:///:memory:")

    @event.listens_for(_engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture
def in_memory_session(in_memory_engine):
    """Sessao SA 2.x sem bind= legado; use in_memory_engine quando precisar de inspect()."""
    Session = sessionmaker(in_memory_engine, expire_on_commit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()
