"""First-run seed da tabela settings — recebe defaults injetados.

Sequencia canonica (LLD §db/seed.py):
1. SELECT COUNT(*) FROM settings
2. Se 0 -> INSERT defaults
3. Se >0 -> log seed_skipped, return 0
4. force=True -> UPSERT defaults (overwrite total)

A camada `db/` nao mais importa diretamente `imbound.constants.*`; o caller
agrega os defaults via `zap_typist.seeders.build_settings_defaults()` e passa
para `run_seed(defaults=...)`. Quando `defaults` e None (compat), o lazy import
de `seeders` e disparado.
"""

from __future__ import annotations

import logging

from zap_typist.db.models import Setting
from zap_typist.db.session import SessionFactory

logger = logging.getLogger(__name__)


def run_seed(
    defaults: dict[str, str] | None = None,
    *,
    force: bool = False,
) -> int:
    """Popula `settings` com `defaults` recebidos por injecao.

    Args:
        defaults: dict de pares (chave, valor) a inserir. Se None, dispara
            lazy import de `zap_typist.seeders.build_settings_defaults()`.
        force: Se True, faz upsert de TODAS as keys (sobrescreve tudo).
            Se False (default), no-op se a tabela ja tem rows.

    Returns:
        Numero de rows inserted/updated. 0 quando no-op.
    """
    if defaults is None:
        from zap_typist.seeders import build_settings_defaults

        defaults = build_settings_defaults()

    session = SessionFactory()
    try:
        if not force:
            existing_count = session.query(Setting).count()
            if existing_count > 0:
                logger.info(
                    "seed_skipped",
                    extra={
                        "event": "seed_skipped",
                        "existing_count": existing_count,
                    },
                )
                return 0

        affected = 0
        for key, value in defaults.items():
            row = session.query(Setting).filter_by(name=key).first()
            if row is None:
                session.add(Setting(name=key, value=value))
            else:
                row.value = value
            affected += 1

        session.commit()
        logger.info(
            "db_seeded",
            extra={
                "event": "db_seeded",
                "rows_inserted": affected,
                "force": force,
            },
        )
        return affected
    except Exception:
        session.rollback()
        raise
    finally:
        SessionFactory.remove()
