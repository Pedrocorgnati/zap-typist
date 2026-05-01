"""Factories de dados sintéticos para testes (sem PII real)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from zap_typist.db.models import (
    Flow,
    FlowMode,
    Lead,
    LeadStatus,
    Setting,
)


def make_lead(**overrides) -> Lead:
    defaults = dict(
        desire="criar um site",
        nome="Joao Silva",
        ddd="11",
        prefixo="98765",
        sufixo="4321",
        info_extra="",
        numero_e164="+551198765432",
        origem="getNinjas",
        status=LeadStatus.pendente,
        observacao="",
        send_attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Lead(**defaults)


def make_flow(**overrides) -> Flow:
    defaults = dict(
        nome="fluxo-teste",
        chrome_profile="profile-teste",
        mode=FlowMode.manual,
        time_window_days=json.dumps(["1", "2", "3", "4", "5"]),
        time_window_start="09:00",
        time_window_end="18:00",
        rate_limit_per_hour=12,
        rate_limit_min_interval=240,
        rate_limit_max_interval=720,
        rate_limit_batch_size=10,
        rate_limit_batch_pause_min=900,
        rate_limit_batch_pause_max=1800,
        is_active=False,
        is_paused=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Flow(**defaults)


def make_setting(name: str, value: str) -> Setting:
    return Setting(
        name=name, value=value, updated_at=datetime.now(timezone.utc)
    )
