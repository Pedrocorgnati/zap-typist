"""Benchmark de TerminalWidget — mede flush real do event loop Qt.

Usa pytest-qt (`qtbot`) para criar QApplication por teste e processar eventos
corretamente. Sem `time.sleep` para sincronização.

Nota de implementação: TerminalWidget não expõe `line_count()` (contrato C1
não incluiu este método); usa-se `widget.document().blockCount()` como proxy.
Qt mantém um bloco vazio terminal, portanto blockCount() = N + 1 após N appends.
"""
from __future__ import annotations

import time

import pytest

pytest_qt = pytest.importorskip("pytestqt")

from zap_typist.ui.widgets.terminal_widget import TerminalWidget  # noqa: E402

TARGET_APPEND_MS = 5.0  # TASK-0 Parte A
ASSERT_MARGIN = 2.0
N_LINES = 1_000


def _block_count(widget: TerminalWidget) -> int:
    """Proxy para contagem de linhas via blockCount (Qt inclui bloco vazio terminal)."""
    return widget.document().blockCount()


def test_terminal_widget_append_batch_meets_target(qtbot) -> None:
    """1 000 chamadas de append_line + flush devem ter média < 5ms/linha (assert < 10ms)."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)

    start = time.monotonic()
    for i in range(N_LINES):
        widget.append_line(f"line {i:04d}")
    # Garantir que o event loop processou todos os signals enfileirados.
    qtbot.waitUntil(lambda: _block_count(widget) >= N_LINES, timeout=10_000)
    elapsed_ms = (time.monotonic() - start) * 1000
    per_line = elapsed_ms / N_LINES
    assert per_line < TARGET_APPEND_MS * ASSERT_MARGIN, (
        f"append_line levou {per_line:.3f}ms/linha "
        f"(target {TARGET_APPEND_MS}ms, limite {TARGET_APPEND_MS * ASSERT_MARGIN}ms)"
    )


def test_terminal_widget_does_not_rotate_under_threshold(qtbot) -> None:
    """Após 1 000 linhas (abaixo do threshold de 5 000) o buffer não rotaciona."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)

    for i in range(N_LINES):
        widget.append_line(f"line {i}")
    # Qt adiciona bloco vazio terminal → tolerância de +5 blocos
    qtbot.waitUntil(lambda: _block_count(widget) >= N_LINES, timeout=10_000)

    assert _block_count(widget) <= N_LINES + 5, (
        f"blockCount={_block_count(widget)} acima do esperado para {N_LINES} inserções"
    )


def test_terminal_widget_set_running_flag_smoke(qtbot) -> None:
    """`set_running(True/False)` não deve travar o event loop nem lançar."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)

    widget.set_running(True)
    widget.append_line("running...")
    widget.set_running(False)
    qtbot.waitUntil(lambda: _block_count(widget) >= 1, timeout=2_000)
    assert _block_count(widget) >= 1
