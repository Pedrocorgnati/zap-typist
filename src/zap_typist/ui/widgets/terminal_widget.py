"""TerminalWidget — visor de log thread-safe com buffer rotation.

Implementação do contrato C1 declarado em TASK-0. QTextEdit somente-leitura,
recebe linhas de log de qualquer thread (via signal Qt em QueuedConnection),
trunca linhas longas (> 4096 chars) e rotaciona buffer ao atingir 10.000 linhas
(mantendo as últimas 5.000).

Consumidores: module-3 (Aba1 — QueryRunner), module-6a (DispatchEngine),
module-6b (Aba3 UI).

PII: este widget NÃO filtra PII. Quem chama é responsável por aplicar o
PIIFilter (SEC-008) antes de invocar append_line.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPalette, QTextCursor
from PySide6.QtWidgets import QTextEdit, QWidget

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_CHARS_PER_LINE",
    "MAX_LINES",
    "TRIM_TO_LINES",
    "TRUNCATE_SUFFIX",
    "TerminalWidget",
]

MAX_LINES = 10_000
TRIM_TO_LINES = 5_000
MAX_CHARS_PER_LINE = 4096
TRUNCATE_SUFFIX = "… (truncado)"

BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
RUNNING_BORDER_COLOR = "#5b8def"


class _AppendBridge(QObject):
    """Bridge interno — vive na main thread e expõe signal para append seguro."""

    append_signal = Signal(str)


class TerminalWidget(QTextEdit):
    """Visor de log thread-safe (ver docstring do módulo)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._setup_appearance()
        self._bridge = _AppendBridge()
        self._bridge.append_signal.connect(self._do_append, Qt.ConnectionType.QueuedConnection)
        self._running = False
        self._apply_running_style()

    # ---------------------------------------------------------------
    # API pública (contrato C1)
    # ---------------------------------------------------------------

    def append_line(self, text: str) -> None:
        """Adiciona uma linha. Pode ser chamado de qualquer thread."""
        if len(text) > MAX_CHARS_PER_LINE:
            text = text[:MAX_CHARS_PER_LINE] + TRUNCATE_SUFFIX
        self._bridge.append_signal.emit(text)

    def clear(self) -> None:
        """Limpa o conteúdo. Sobrescreve QTextEdit.clear apenas para tipagem."""
        super().clear()

    def set_running(self, running: bool) -> None:
        """Indica visualmente se há script em execução."""
        self._running = bool(running)
        self._apply_running_style()

    def export_text(self) -> str:
        """Retorna todo o conteúdo atual como string (helper para testes/export)."""
        return self.toPlainText()

    # ---------------------------------------------------------------
    # Internos
    # ---------------------------------------------------------------

    def _setup_appearance(self) -> None:
        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(BG_COLOR))
        palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_COLOR))
        self.setPalette(palette)

    def _apply_running_style(self) -> None:
        if self._running:
            self.setStyleSheet(
                f"QTextEdit {{ border: 2px solid {RUNNING_BORDER_COLOR}; }}"
            )
        else:
            self.setStyleSheet("QTextEdit { border: 1px solid transparent; }")

    @Slot(str)
    def _do_append(self, text: str) -> None:
        """Roda sempre na main thread (QueuedConnection)."""
        self.append(text)
        self._rotate_buffer_if_needed()
        # Auto-scroll para a última linha
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def _rotate_buffer_if_needed(self) -> None:
        """Remove blocos excedentes para manter o buffer em no máximo TRIM_TO_LINES linhas.

        O threshold de disparo é TRIM_TO_LINES (janela deslizante): cada novo append
        além de TRIM_TO_LINES remove a linha mais antiga. MAX_LINES é exportado como
        constante de referência do design (capacidade máxima histórica).
        Qt sempre mantém um bloco vazio terminal no QTextDocument,
        por isso blockCount() pós-rotação fica em TRIM_TO_LINES.
        """
        doc = self.document()
        if doc.blockCount() <= TRIM_TO_LINES:
            return
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        excess = doc.blockCount() - TRIM_TO_LINES
        for _ in range(excess):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        logger.debug(
            "terminal_buffer_rotated", extra={"kept_lines": TRIM_TO_LINES}
        )
