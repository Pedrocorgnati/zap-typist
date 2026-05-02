"""Factories factory-boy para Lead e Flow.

Estes builders produzem instancias com defaults sanos; sobrescreva qualquer
campo via kwargs (ex: `LeadFactory(status=LeadStatus.enviado.value)`).
"""

from __future__ import annotations

import json

import factory

from zap_typist.db.models import Flow, Lead, LeadStatus


class LeadFactory(factory.Factory):
    class Meta:
        model = Lead

    nome = factory.Faker("name", locale="pt_BR")
    origem = "getNinjas"
    status = LeadStatus.pendente.value


class FlowFactory(factory.Factory):
    class Meta:
        model = Flow

    nome = factory.Sequence(lambda n: f"flow-{n}")
    chrome_profile = "default"
    mode = "manual"
    time_window_days = json.dumps(["1", "2", "3", "4", "5"])
    time_window_start = "09:00"
    time_window_end = "18:00"
    rate_limit_per_hour = 12
    rate_limit_min_interval = 240
    rate_limit_max_interval = 720
    rate_limit_batch_size = 10
    rate_limit_batch_pause_min = 900
    rate_limit_batch_pause_max = 1800
