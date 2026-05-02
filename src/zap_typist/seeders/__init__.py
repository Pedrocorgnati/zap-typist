"""Seeders: agregam defaults canonicos por consumer.

Este modulo e o ponto de inversao para evitar que `db/seed.py` (camada de infra)
puxe direto de `imbound/` (camada de dominio externa). O caller passa os defaults
explicitamente para `db.seed.run_seed(defaults=...)`.
"""

from __future__ import annotations

import json

from zap_typist.domain.constants import CONTACT_HISTORY_WINDOW_DAYS
from zap_typist.imbound.constants.desire_rules import DESIRE_RULES_SEED
from zap_typist.imbound.constants.feminine_names import FEMININE_NAMES_SEED
from zap_typist.imbound.constants.message_templates import (
    MSG_TEMPLATE_1,
    MSG_TEMPLATE_2,
    MSG_TEMPLATE_3,
    MSG_TEMPLATE_4,
    MSG_TEMPLATE_5,
)


def build_settings_defaults() -> dict[str, str]:
    """Monta o dict canonico de defaults para a tabela `settings`."""
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
        "contact_history_window_days": str(CONTACT_HISTORY_WINDOW_DAYS),
        "app_version": "0.1.0",
        "seed_version": "1",
    }


__all__ = ["build_settings_defaults"]
