"""Testes das constantes de path — absolutos, derivados e override por env var."""
import importlib


def test_default_paths_under_home():
    from zap_typist.db.models import (
        APP_DATA_DIR,
        CACHE_DIR,
        CHROME_PROFILES_DIR,
        DB_PATH,
        LOCK_FILE,
        LOG_DIR,
    )

    assert APP_DATA_DIR.is_absolute()
    for p in (DB_PATH, CACHE_DIR, CHROME_PROFILES_DIR, LOCK_FILE, LOG_DIR):
        assert p.is_relative_to(APP_DATA_DIR)


def test_db_path_is_zap_typist_db():
    from zap_typist.db.models import APP_DATA_DIR, DB_PATH

    assert DB_PATH == APP_DATA_DIR / "zap_typist.db"


def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ZAP_TYPIST_DATA_DIR", str(tmp_path))
    import zap_typist.db.models as m

    importlib.reload(m)
    assert m.APP_DATA_DIR == tmp_path.resolve()
    assert m.DB_PATH == tmp_path.resolve() / "zap_typist.db"
    monkeypatch.delenv("ZAP_TYPIST_DATA_DIR", raising=False)
    importlib.reload(m)


def test_origem_padrao_aba1_constant():
    from zap_typist.db.models import ORIGEM_PADRAO_ABA1

    assert ORIGEM_PADRAO_ABA1 == "getNinjas"
