"""First-run seed da tabela settings.

Sequencia canonica (LLD §db/seed.py):
1. SELECT COUNT(*) FROM settings
2. Se 0 -> INSERT 25 defaults
3. Se >0 -> log seed_skipped, return 0
4. force=True -> UPSERT 25 defaults (overwrite total)

Falha em importar uma constante de seed = log.critical + raise (nao popular parcialmente).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from zap_typist.db.models import Setting
from zap_typist.db.session import SessionFactory

logger = logging.getLogger(__name__)

try:
    from zap_typist.imbound.constants.feminine_names import FEMININE_NAMES_SEED
    from zap_typist.imbound.constants.desire_rules import DESIRE_RULES_SEED
    from zap_typist.imbound.constants.message_templates import (
        MSG_TEMPLATE_1,
        MSG_TEMPLATE_2,
        MSG_TEMPLATE_3,
        MSG_TEMPLATE_4,
        MSG_TEMPLATE_5,
    )
except ImportError as exc:
    logger.critical(
        "seed_constant_missing",
        extra={"event": "seed_constant_missing", "missing": str(exc)},
    )
    raise


def _build_defaults() -> dict[str, str]:
    """Monta o dict canonico de defaults. Separado para facilitar teste."""
    return {
        "msg_template_1": MSG_TEMPLATE_1,
        "msg_template_2": MSG_TEMPLATE_2,
        "msg_template_3": MSG_TEMPLATE_3,
        "msg_template_4": MSG_TEMPLATE_4,
        "msg_template_5": MSG_TEMPLATE_5,
        "sender_nome": "Pedro",
        "sender_profissao": "desenvolvedor",
        "sender_portfolio_url": "",
        "msg_fallback_block": (
            "Desculpe o contato caso nao seja voce a pessoa certa para isso. "
            "Fico a disposicao caso queira remover seu contato."
        ),
        "feminine_names": json.dumps(FEMININE_NAMES_SEED, ensure_ascii=False),
        "desire_rules": json.dumps(DESIRE_RULES_SEED, ensure_ascii=False),
        "default_aba1_origin": "getNinjas",
        "default_mode": "manual",
        "default_rate_per_hour": "12",
        "default_min_interval": "240",
        "default_max_interval": "720",
        "default_batch_size": "10",
        "default_batch_pause_min": "900",
        "default_batch_pause_max": "1800",
        "default_window_days": json.dumps(["1", "2", "3", "4", "5"]),
        "default_window_start": "09:00",
        "default_window_end": "18:00",
        "contact_history_window_days": "60",
        "app_version": "0.1.0",
        "seed_version": "1",
    }


SEED_DEFAULTS: dict[str, str] = _build_defaults()


def run_seed(force: bool = False) -> int:
    """Popula `settings` com defaults canonicos.

    Args:
        force: Se True, faz upsert de TODAS as keys (sobrescreve tudo).
               Se False (default), no-op se a tabela ja tem rows.

    Returns:
        Numero de rows inserted/updated. 0 quando no-op.
    """
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
        for key, value in SEED_DEFAULTS.items():
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
