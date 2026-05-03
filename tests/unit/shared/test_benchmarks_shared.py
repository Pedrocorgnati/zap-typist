"""Benchmarks de performance dos componentes shared puros (sem Qt).

Targets — fonte da verdade: TASK-0 Parte A "Performance Targets".
Asserts usam margem 2x para tolerar jitter de CI.
"""
from __future__ import annotations

import time

import pytest

from zap_typist.db.models import LeadStatus
from zap_typist.ui.widgets.form_validators import LeadStatusGuard
from zap_typist.utils.e164 import DDDS_VALIDOS_BR, format_e164

# Targets declarados em TASK-0 Parte A.
TARGET_E164_MS = 1.0
TARGET_GUARD_MS = 0.1
# Margem de 2x para CI.
ASSERT_MARGIN = 2.0

ITER_E164 = 10_000
ITER_GUARD = 10_000


def _measure_per_call_ms(fn, iterations: int) -> float:
    """Executa `fn()` `iterations` vezes e retorna o custo médio em milissegundos."""
    start = time.monotonic()
    for _ in range(iterations):
        fn()
    elapsed_ms = (time.monotonic() - start) * 1000
    return elapsed_ms / iterations


def test_format_e164_meets_performance_target() -> None:
    """`format_e164` deve executar em < 1ms por chamada (assert < 2ms)."""
    per_call = _measure_per_call_ms(
        lambda: format_e164("11", "98765", "4321"),
        ITER_E164,
    )
    assert per_call < TARGET_E164_MS * ASSERT_MARGIN, (
        f"format_e164 levou {per_call:.4f}ms/chamada "
        f"(target {TARGET_E164_MS}ms, limite {TARGET_E164_MS * ASSERT_MARGIN}ms)"
    )


def test_format_e164_works_for_all_valid_ddds() -> None:
    """Sanity: todos os DDDs canônicos retornam string `+55...` sem erro."""
    assert DDDS_VALIDOS_BR, "DDDS_VALIDOS_BR não pode estar vazio"
    for ddd in DDDS_VALIDOS_BR:
        result = format_e164(ddd, "98765", "4321")
        assert result is not None and result.startswith("+55"), (
            f"format_e164 falhou para DDD {ddd!r}: {result!r}"
        )


def test_lead_status_guard_can_transition_meets_target() -> None:
    """`LeadStatusGuard.can_transition` deve ser < 0.1ms por chamada (assert < 0.2ms)."""
    pairs: list[tuple[LeadStatus, LeadStatus]] = [
        (LeadStatus.pendente, LeadStatus.query_gerada),
        (LeadStatus.query_gerada, LeadStatus.telefone_preenchido),
        (LeadStatus.enviado, LeadStatus.pendente),  # transição inválida
        (LeadStatus.descartado, LeadStatus.invalido),  # terminal
    ]

    def call() -> None:
        for current, next_s in pairs:
            LeadStatusGuard.can_transition(current, next_s)

    per_call = _measure_per_call_ms(call, ITER_GUARD) / len(pairs)
    assert per_call < TARGET_GUARD_MS * ASSERT_MARGIN, (
        f"can_transition levou {per_call:.5f}ms/chamada "
        f"(target {TARGET_GUARD_MS}ms, limite {TARGET_GUARD_MS * ASSERT_MARGIN}ms)"
    )


def test_lead_status_guard_allowed_next_returns_copy() -> None:
    """`allowed_next` deve retornar nova lista — mutar o resultado não pode afetar
    chamadas subsequentes (isolamento da máquina de estados)."""
    first = LeadStatusGuard.allowed_next(LeadStatus.pendente)
    first.clear()
    second = LeadStatusGuard.allowed_next(LeadStatus.pendente)
    assert second, "Mutação no resultado de allowed_next vazou para _TRANSITIONS"


def test_lead_status_guard_allowed_next_meets_target() -> None:
    """`allowed_next` para todos os estados deve ser < 0.1ms/chamada."""
    states = list(LeadStatus)

    def call() -> None:
        for s in states:
            LeadStatusGuard.allowed_next(s)

    per_call = _measure_per_call_ms(call, ITER_GUARD) / len(states)
    assert per_call < TARGET_GUARD_MS * ASSERT_MARGIN, (
        f"allowed_next levou {per_call:.5f}ms/chamada (limite {TARGET_GUARD_MS * ASSERT_MARGIN}ms)"
    )


@pytest.mark.parametrize(
    "current,next_status,expected",
    [
        (LeadStatus.pendente, LeadStatus.query_gerada, True),
        (LeadStatus.enviado, LeadStatus.pendente, False),
        (LeadStatus.descartado, LeadStatus.invalido, False),
        (LeadStatus.falhou, LeadStatus.mensagem_pronta, True),
    ],
)
def test_lead_status_guard_correctness_smoke(
    current: LeadStatus, next_status: LeadStatus, expected: bool
) -> None:
    """Smoke de correção complementando o benchmark — não substitui TASK-4 testes."""
    assert LeadStatusGuard.can_transition(current, next_status) is expected
