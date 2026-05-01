"""Fixtures globais de pytest: DB in-memory, sessão e sessão semeada."""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker

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


@pytest.fixture(scope="function")
def db_engine():
    """Engine SQLite in-memory sem FK enforcement; fonte canonica para db_session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Sessao scoped in-memory; rollback automatico ao final do teste."""
    Session = scoped_session(
        sessionmaker(bind=db_engine, expire_on_commit=False)
    )
    session = Session()
    yield session
    session.rollback()
    Session.remove()


@pytest.fixture(scope="function")
def seeded_session(db_session, monkeypatch):
    """Sessao in-memory pre-populada com os defaults canonicos do seed."""

    class _StubFactory:
        def __call__(self):
            return db_session

        def remove(self):
            return None

    monkeypatch.setattr("zap_typist.db.seed.SessionFactory", _StubFactory())
    from zap_typist.db.seed import run_seed

    run_seed(force=True)
    yield db_session
