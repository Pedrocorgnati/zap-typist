"""Testes do script MIGRATION-v1.0.1.py.

Estrategia: importar `migrate()` por path absoluto (script .py em scripts/),
preparar DB v1.0.0-style (com triggers + timestamps mistos) em tmp, rodar
migrate() e validar pos-condicoes.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "MIGRATION-v1.0.1.py"


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_v1_0_1", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def legacy_db(tmp_path: Path) -> Path:
    """Cria DB minimal com schema v1.0.0-like (apenas tabelas que migration toca)."""
    db_path = tmp_path / "zap_typist.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                origem TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                whatsapp_validated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE settings (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                paused_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE contact_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_e164 TEXT NOT NULL,
                flow_id INTEGER NOT NULL,
                touched_at TEXT NOT NULL
            );
            CREATE TRIGGER trg_leads_updated_at AFTER UPDATE ON leads FOR EACH ROW
            BEGIN UPDATE leads SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id; END;
            CREATE TRIGGER trg_settings_updated_at AFTER UPDATE ON settings FOR EACH ROW
            BEGIN UPDATE settings SET updated_at = CURRENT_TIMESTAMP WHERE name = OLD.name; END;
            CREATE TRIGGER trg_flows_updated_at AFTER UPDATE ON flows FOR EACH ROW
            BEGIN UPDATE flows SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id; END;
            INSERT INTO leads(nome, origem, created_at, updated_at) VALUES
                ('Joao', 'getNinjas', '2026-04-30T10:00:00+00:00', '2026-04-30 10:00:00');
            INSERT INTO settings(name, value, updated_at) VALUES
                ('app_version', '0.1.0', '2026-04-30 10:00:00Z'),
                ('seed_version', '1', '2026-04-30 10:00:00');
            INSERT INTO flows(nome, created_at, updated_at) VALUES
                ('flow-x', '2026-04-30 10:00:00', '2026-04-30 10:00:00');
            INSERT INTO contact_history(numero_e164, flow_id, touched_at) VALUES
                ('+5511999999999', 1, '2026-04-30T10:00:00Z');
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_migration_drops_legacy_triggers(legacy_db: Path) -> None:
    mod = _load_migration_module()
    rc = mod.migrate(legacy_db, dry_run=False)
    assert rc == 0

    conn = sqlite3.connect(str(legacy_db))
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'trg_%'"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [], f"triggers nao removidos: {rows}"


def test_migration_normalizes_timestamps(legacy_db: Path) -> None:
    mod = _load_migration_module()
    mod.migrate(legacy_db, dry_run=False)

    conn = sqlite3.connect(str(legacy_db))
    try:
        leads = conn.execute("SELECT created_at, updated_at FROM leads").fetchone()
        settings = conn.execute(
            "SELECT updated_at FROM settings WHERE name = 'app_version'"
        ).fetchone()
        ch = conn.execute("SELECT touched_at FROM contact_history").fetchone()
    finally:
        conn.close()

    for ts in (*leads, settings[0], ch[0]):
        assert "+00:00" not in ts and "+0000" not in ts and not ts.endswith("Z")
        assert "T" not in ts


def test_migration_bumps_app_version(legacy_db: Path) -> None:
    mod = _load_migration_module()
    mod.migrate(legacy_db, dry_run=False)

    conn = sqlite3.connect(str(legacy_db))
    try:
        ver = conn.execute("SELECT value FROM settings WHERE name = 'app_version'").fetchone()[0]
        seed = conn.execute("SELECT value FROM settings WHERE name = 'seed_version'").fetchone()[0]
    finally:
        conn.close()
    assert ver == "0.1.1"
    assert seed == "2"


def test_migration_creates_backup(legacy_db: Path) -> None:
    mod = _load_migration_module()
    mod.migrate(legacy_db, dry_run=False)

    backup = legacy_db.with_name(legacy_db.name + ".bak-v1.0.0")
    assert backup.exists(), f"backup nao criado em {backup}"


def test_migration_idempotent(legacy_db: Path) -> None:
    mod = _load_migration_module()
    rc1 = mod.migrate(legacy_db, dry_run=False)
    rc2 = mod.migrate(legacy_db, dry_run=False)
    assert rc1 == 0
    assert rc2 == 0


def test_migration_dry_run_does_not_change(legacy_db: Path) -> None:
    mod = _load_migration_module()
    rc = mod.migrate(legacy_db, dry_run=True)
    assert rc == 0

    conn = sqlite3.connect(str(legacy_db))
    try:
        triggers = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'trigger'"
        ).fetchone()[0]
        ver = conn.execute("SELECT value FROM settings WHERE name = 'app_version'").fetchone()[0]
    finally:
        conn.close()
    assert triggers == 3, "dry-run nao deve dropar triggers"
    assert ver == "0.1.0", "dry-run nao deve bumpar version"


def test_migration_no_db_returns_zero(tmp_path: Path) -> None:
    mod = _load_migration_module()
    rc = mod.migrate(tmp_path / "nonexistent.db", dry_run=False)
    assert rc == 0
