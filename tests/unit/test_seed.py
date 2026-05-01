"""Testes unitarios de db.seed.run_seed.

Estrategia: substituir SessionFactory por uma scoped_session em SQLite :memory:
via monkeypatch, cobrindo os 4 cenarios canonicos do LLD.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base, Setting


@pytest.fixture
def seed_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr("zap_typist.db.seed.SessionFactory", Session)
    yield Session
    Session.remove()


def test_seed_populates_25_plus_keys(seed_session):
    from zap_typist.db.seed import run_seed

    count = run_seed(force=False)
    assert count >= 25, f"expected >=25 keys, got {count}"

    s = seed_session()
    assert s.query(Setting).count() >= 25
    s.close()


def test_seed_is_idempotent(seed_session):
    from zap_typist.db.seed import run_seed

    run_seed(force=False)
    second = run_seed(force=False)
    third = run_seed(force=False)
    assert second == 0, "2nd call should be no-op"
    assert third == 0, "3rd call should be no-op"


def test_seed_force_overwrites(seed_session):
    from zap_typist.db.seed import run_seed

    run_seed(force=False)

    s = seed_session()
    row = s.query(Setting).filter_by(name="sender_nome").first()
    row.value = "MUTATED"
    s.commit()
    s.close()

    count = run_seed(force=True)
    assert count >= 25

    s = seed_session()
    row = s.query(Setting).filter_by(name="sender_nome").first()
    assert row.value == "Pedro", "force=True should restore default"
    s.close()


def test_seed_feminine_names_is_valid_json_array(seed_session):
    from zap_typist.db.seed import run_seed

    run_seed(force=False)
    s = seed_session()
    row = s.query(Setting).filter_by(name="feminine_names").first()
    assert row is not None
    parsed = json.loads(row.value)
    assert isinstance(parsed, list)
    assert len(parsed) >= 43
    assert len(set(parsed)) == len(parsed), "no duplicates expected"
    s.close()


def test_seed_desire_rules_has_catchall_last(seed_session):
    from zap_typist.db.seed import run_seed

    run_seed(force=False)
    s = seed_session()
    row = s.query(Setting).filter_by(name="desire_rules").first()
    parsed = json.loads(row.value)
    assert len(parsed) == 5
    assert parsed[-1]["pattern"] == ".*", "last rule must be catch-all"
    s.close()


def test_seed_rollback_on_commit_error(seed_session, monkeypatch):
    from zap_typist.db.seed import run_seed

    def _failing_commit():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(seed_session(), "commit", _failing_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        run_seed(force=False)
