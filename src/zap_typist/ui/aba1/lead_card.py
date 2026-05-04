"""LeadCardWidget — card de lead com status query_gerada (Aba 1, Bloco 3)."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zap_typist.db.models import Lead
from zap_typist.ui.styles import COLOR_FEEDBACK_SUCCESS
from zap_typist.ui.widgets.form_validators import PhoneSegmentValidator
from zap_typist.utils.e164 import format_e164
from zap_typist.utils.logger import get_logger

COPIED_FEEDBACK_MS = 2000
SUFIXO_LEN = 4

logger = get_logger(__name__)


def _build_dork_lines(lead: Lead) -> list[str]:
    """Retorna 1 ou 2 linhas de dork conforme presença de info_extra."""
    base = f'"{lead.nome}" ("{lead.ddd} {lead.prefixo}" OR "({lead.ddd}) {lead.prefixo}")'
    if not lead.info_extra:
        return [base]
    extra = f'"{lead.info_extra}" ("{lead.ddd} {lead.prefixo}" OR "({lead.ddd}) {lead.prefixo}")'
    return [base, extra]


class LeadCardWidget(QWidget):
    """Widget que renderiza um lead query_gerada no formato do INTAKE Bloco 3."""

    submit_requested: Signal = Signal(int, str)
    discard_requested: Signal = Signal(int)

    def __init__(self, lead: Lead, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lead = lead
        self._dork_lines = _build_dork_lines(lead)
        self._copied_label: QLabel | None = None
        self._copied_timer: QTimer | None = None
        self._footer_layout: QHBoxLayout | None = None
        self._build_layout()

    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        self.setMinimumWidth(450)

        header = QLabel(f"{self._lead.nome} | ({self._lead.ddd}) {self._lead.prefixo}")
        header.setStyleSheet("font-weight: bold;")
        acc_name = (
            f"Lead {self._lead.nome}, telefone parcial"
            f" DDD {self._lead.ddd} prefixo {self._lead.prefixo}"
        )
        header.setAccessibleName(acc_name)
        root.addWidget(header)

        if self._lead.desire:
            root.addWidget(QLabel(self._lead.desire))

        dork_main = QLabel(self._dork_lines[0])
        dork_main.setStyleSheet("font-family: monospace;")
        root.addWidget(dork_main)

        if len(self._dork_lines) > 1:
            dork_extra = QLabel(self._dork_lines[1])
            dork_extra.setStyleSheet("font-family: monospace;")
            root.addWidget(dork_extra)

        footer = QHBoxLayout()
        self._footer_layout = footer

        self._copy_btn = QPushButton("Copiar query")
        self._copy_btn.setAccessibleName("Copiar dork Google para clipboard")
        self._copy_btn.setAccessibleDescription(
            "Copia 1 ou 2 strings de pesquisa Google para a área de transferência"
        )
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        footer.addWidget(self._copy_btn)

        footer.addWidget(QLabel("Sufixo:"))

        self._sufixo_input = QLineEdit()
        self._sufixo_input.setValidator(PhoneSegmentValidator(SUFIXO_LEN, SUFIXO_LEN))
        self._sufixo_input.setMaxLength(SUFIXO_LEN)
        self._sufixo_input.setPlaceholderText("____")
        self._sufixo_input.setAccessibleName("Sufixo do telefone, 4 dígitos")
        self._sufixo_input.returnPressed.connect(self._on_submit_clicked)
        footer.addWidget(self._sufixo_input)

        self._submit_btn = QPushButton("Submit")
        self._submit_btn.setAccessibleName("Submeter sufixo e mover lead para fase de envio")
        self._submit_btn.clicked.connect(self._on_submit_clicked)
        footer.addWidget(self._submit_btn)

        self._discard_btn = QPushButton("Descartar")
        self._discard_btn.setAccessibleName("Descartar lead — exige confirmação")
        self._discard_btn.clicked.connect(self._on_discard_clicked)
        footer.addWidget(self._discard_btn)

        footer.addStretch()
        root.addLayout(footer)

    def _on_copy_clicked(self) -> None:
        text_to_copy = "\n".join(self._dork_lines)
        QGuiApplication.clipboard().setText(text_to_copy)
        self._show_copied_feedback()

    def _show_copied_feedback(self) -> None:
        if self._copied_timer is not None and self._copied_timer.isActive():
            self._copied_timer.stop()
            if self._copied_label is not None:
                self._copied_label.deleteLater()
                self._copied_label = None

        self._copied_label = QLabel("Copiado!")
        self._copied_label.setStyleSheet(f"color: {COLOR_FEEDBACK_SUCCESS}; font-weight: bold;")
        if self._footer_layout is not None:
            self._footer_layout.insertWidget(1, self._copied_label)

        self._copied_timer = QTimer(self)
        self._copied_timer.setSingleShot(True)
        self._copied_timer.timeout.connect(self._clear_copied_feedback)
        self._copied_timer.start(COPIED_FEEDBACK_MS)

    def _clear_copied_feedback(self) -> None:
        if self._copied_label is not None:
            self._copied_label.deleteLater()
            self._copied_label = None
        self._copied_timer = None

    def _lock_footer_widgets(self) -> None:
        self._sufixo_input.setEnabled(False)
        self._submit_btn.setEnabled(False)
        self._discard_btn.setEnabled(False)

    def _on_submit_clicked(self) -> None:
        sufixo = self._sufixo_input.text().strip()
        if len(sufixo) != SUFIXO_LEN or not sufixo.isdigit():
            QMessageBox.warning(
                self,
                "Sufixo inválido",
                "Informe os 4 dígitos finais do telefone.",
            )
            return
        ddd = self._lead.ddd or ""
        prefixo = self._lead.prefixo or ""
        e164 = format_e164(ddd, prefixo, sufixo)
        if e164 is None:
            QMessageBox.warning(
                self,
                "Telefone inválido",
                "Combinação DDD + prefixo + sufixo não forma um número E.164 válido.",
            )
            return
        logger.debug("submit_requested_emitted", extra={"lead_id": self._lead.id})
        self.submit_requested.emit(self._lead.id, sufixo)
        self._lock_footer_widgets()

    def _on_discard_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar descarte",
            "Descartar este lead permanentemente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        logger.debug("discard_requested_emitted", extra={"lead_id": self._lead.id})
        self.discard_requested.emit(self._lead.id)
        self._lock_footer_widgets()
