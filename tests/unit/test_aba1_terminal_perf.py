"""Testes de performance do TerminalWidget (US-005).

G1 anti-flakiness: warm-up dedicado + mediana de 3 runs + PERF_TOLERANCE_FACTOR.
"""
from __future__ import annotations

import os
import statistics
import time

from PySide6.QtWidgets import QApplication

from zap_typist.ui.widgets.terminal_widget import TerminalWidget

PERF_TOLERANCE_FACTOR = float(os.getenv("PERF_TOLERANCE_FACTOR", "1.0"))
BASELINE_1K_MS = 500.0
BASELINE_100_MS = 50.0


def _run_append(qtbot, n: int) -> float:
    """Mede um único run de append_line x n. Retorna ms."""
    app = QApplication.instance() or QApplication([])
    terminal = TerminalWidget()
    qtbot.addWidget(terminal)
    start = time.perf_counter()
    for i in range(n):
        terminal.append_line(f"linha {i}")
    app.processEvents()
    return (time.perf_counter() - start) * 1000.0


def test_terminal_widget_1k_lines_under_500ms(qtbot):
    """US-005: TerminalWidget renderiza 1000 linhas em <500ms (mediana de 3 runs)."""
    # Warm-up: descarta primeira run (import lazy, allocator, etc.)
    _run_append(qtbot, 1000)
    # Mediana de 3 runs: resiliente a GC pause / jitter de scheduler
    samples = [_run_append(qtbot, 1000) for _ in range(3)]
    median_ms = statistics.median(samples)
    threshold = BASELINE_1K_MS * PERF_TOLERANCE_FACTOR
    assert median_ms < threshold, (
        f"TerminalWidget.append_line x1000 mediana={median_ms:.1f}ms "
        f"(threshold={threshold:.1f}ms = {BASELINE_1K_MS}ms * tolerance={PERF_TOLERANCE_FACTOR}); "
        f"samples={[f'{s:.1f}' for s in samples]}; viola US-005"
    )


def test_terminal_widget_100_lines_under_50ms(qtbot):
    """Verificação de escala: 100 linhas em <50ms."""
    _run_append(qtbot, 100)  # warm-up
    samples = [_run_append(qtbot, 100) for _ in range(3)]
    median_ms = statistics.median(samples)
    threshold = BASELINE_100_MS * PERF_TOLERANCE_FACTOR
    assert median_ms < threshold, (
        f"100 linhas mediana={median_ms:.1f}ms (threshold={threshold:.1f}ms); "
        f"samples={[f'{s:.1f}' for s in samples]}"
    )
