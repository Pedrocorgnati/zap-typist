#!/usr/bin/env python3
"""MIGRATION-v1.0.1 — timestamps timezone-aware (UTC).

Per politica de migration manual (db/session.py:1-7), v1.x+ sao scripts Python
versionados executados pelo proprio usuario antes do upgrade do app.

Este script:
  1. Faz backup do `zap_typist.db` em `zap_typist.db.bak-v1.0.0`.
  2. Remove os triggers SQL `trg_<table>_updated_at` (substituidos por
     SQLAlchemy onupdate=_utc_now).
  3. Re-formata todos os timestamps (created_at/updated_at/touched_at/paused_at/
     whatsapp_validated_at) garantindo formato ISO sem offset (que UTCDateTime
     interpreta como UTC ao reler).
  4. Atualiza `settings.app_version` para 0.1.1 e `seed_version` para 2.

Compatibilidade: idempotente — pode rodar em DB ja migrado (re-aplica os UPDATEs
sem efeito visivel). Se nao houver `zap_typist.db`, sai com codigo 0 (boot do app
recriara o schema novo).

Uso:
    python scripts/MIGRATION-v1.0.1.py [--dry-run]

Saida 0 = sucesso ou no-op; 1 = erro (DB inexistente nao e erro).
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "zap-typist" / "zap_typist.db"


def _log(msg: str) -> None:
    print(f"[migration v1.0.1] {msg}")


def _drop_legacy_triggers(conn: sqlite3.Connection) -> int:
    """Remove triggers `trg_<table>_updated_at` que existiam em v1.0.0."""
    triggers = ("trg_leads_updated_at", "trg_settings_updated_at", "trg_flows_updated_at")
    dropped = 0
    for name in triggers:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (name,),
        )
        if cur.fetchone() is not None:
            conn.execute(f"DROP TRIGGER {name}")
            dropped += 1
    return dropped


def _normalize_timestamps_table(
    conn: sqlite3.Connection,
    table: str,
    pk: str,
    columns: tuple[str, ...],
) -> int:
    """Le cada linha de `table` e reescreve os timestamps em formato ISO sem offset.

    SQLite armazena DateTime como TEXT; rows escritas pre-migration podem ter
    `'2026-04-30 22:30:00'` (CURRENT_TIMESTAMP) ou `'2026-04-30T22:30:00'` ou
    com offset. Normalizamos para `'YYYY-MM-DD HH:MM:SS'` (assumindo UTC).
    Linhas com NULL em timestamps continuam NULL.
    """
    affected = 0
    for col in columns:
        cur = conn.execute(
            f"SELECT {pk}, {col} FROM {table} WHERE {col} IS NOT NULL"  # noqa: S608
        )
        rows = cur.fetchall()
        for pk_val, ts in rows:
            normalized = _normalize_iso(ts)
            if normalized != ts:
                conn.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {pk} = ?",  # noqa: S608
                    (normalized, pk_val),
                )
                affected += 1
    return affected


def _normalize_iso(ts: str) -> str:
    """Normaliza timestamp para `'YYYY-MM-DD HH:MM:SS[.ffffff]'` sem offset."""
    cleaned = ts.replace("T", " ")
    for marker in ("+00:00", "+0000", "Z"):
        if cleaned.endswith(marker):
            cleaned = cleaned[: -len(marker)]
            break
    return cleaned.rstrip()


def migrate(db_path: Path, *, dry_run: bool = False) -> int:
    if not db_path.exists():
        _log(f"DB nao existe em {db_path}; nada a migrar.")
        return 0

    backup_path = db_path.with_name(db_path.name + ".bak-v1.0.0")
    if not backup_path.exists():
        if dry_run:
            _log(f"[dry-run] Backup seria criado em {backup_path}")
        else:
            shutil.copy2(db_path, backup_path)
            _log(f"Backup criado: {backup_path}")
    else:
        _log(f"Backup ja existe: {backup_path} (preservado)")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN")

        triggers_dropped = _drop_legacy_triggers(conn)
        _log(f"Triggers legacy removidos: {triggers_dropped}")

        leads = _normalize_timestamps_table(
            conn,
            "leads",
            "id",
            ("created_at", "updated_at", "whatsapp_validated_at"),
        )
        settings = _normalize_timestamps_table(conn, "settings", "name", ("updated_at",))
        flows = _normalize_timestamps_table(
            conn,
            "flows",
            "id",
            ("created_at", "updated_at", "paused_at"),
        )
        ch = _normalize_timestamps_table(conn, "contact_history", "id", ("touched_at",))
        _log(
            f"Timestamps normalizados: leads={leads}, settings={settings}, "
            f"flows={flows}, contact_history={ch}"
        )

        # Bump version markers em settings (best-effort).
        conn.execute(
            "UPDATE settings SET value = '0.1.1' WHERE name = 'app_version'"
        )
        conn.execute(
            "UPDATE settings SET value = '2' WHERE name = 'seed_version'"
        )

        if dry_run:
            conn.execute("ROLLBACK")
            _log("[dry-run] Rollback aplicado; DB inalterado.")
        else:
            conn.execute("COMMIT")
            _log("Migration v1.0.1 aplicada com sucesso.")
        return 0
    except Exception as exc:
        conn.execute("ROLLBACK")
        _log(f"ERRO: {exc}; rollback aplicado. Restaure de {backup_path} se necessario.")
        return 1
    finally:
        conn.close()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Migration v1.0.1 (timezone-aware UTC).")
    p.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Caminho do DB (default: {DEFAULT_DB_PATH})",
    )
    p.add_argument("--dry-run", action="store_true", help="Nao aplica COMMIT")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    return migrate(args.db, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
