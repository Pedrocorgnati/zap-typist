"""LeadFormWidget — formulário de adição manual de leads (Aba 1)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zap_typist.services.lead_service import create_lead
from zap_typist.utils.logger import get_logger

logger = get_logger(__name__)

_DIGITS_RE = QRegularExpression(r"\d+")


def _install_digit_filter(line_edit: QLineEdit, max_digits: int | None = None) -> None:
    """Instala validator + sanitizador textChanged que aceita apenas dígitos.

    O QRegularExpressionValidator bloqueia teclas não-dígito na UI.
    O handler textChanged sanitiza entradas programáticas (ex: setText) para que
    testes e código externo obtenham apenas dígitos ao ler o campo.
    Não usa setMaxLength para evitar truncagem de chars antes da sanitização.
    """
    line_edit.setValidator(QRegularExpressionValidator(_DIGITS_RE))

    def _sanitize(text: str) -> None:
        filtered = "".join(ch for ch in text if ch.isdigit())
        if max_digits is not None:
            filtered = filtered[:max_digits]
        if filtered == text:
            return
        pos = line_edit.cursorPosition()
        removed = len(text) - len(filtered)
        line_edit.blockSignals(True)
        line_edit.setText(filtered)
        line_edit.blockSignals(False)
        line_edit.setCursorPosition(max(0, pos - removed))

    line_edit.textChanged.connect(_sanitize)


class LeadFormWidget(QGroupBox):
    """Formulário para cadastrar leads em status=pendente.

    Args:
        session_factory: callable que retorna um Session SQLAlchemy
            (tipicamente SessionFactory do module-1-setup).
        parent: parent QWidget (opcional).
    """

    lead_added = Signal()

    def __init__(
        self,
        session_factory: Callable[[], Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Adicionar lead", parent)
        self._session_factory = session_factory
        self._build_ui()
        self.setMinimumWidth(420)
        self.input_nome.setFocus()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_desire = QLineEdit()
        self.input_desire.setPlaceholderText("ex: criar ferramenta de avaliação de alunos")
        self.input_desire.setAccessibleName("Desejo do lead")
        form.addRow("desire:", self.input_desire)

        self.input_nome = QLineEdit()
        self.input_nome.setPlaceholderText("Giovana")
        self.input_nome.setAccessibleName("Nome do lead")
        form.addRow("nome:", self.input_nome)

        self.input_ddd = QLineEdit()
        self.input_ddd.setPlaceholderText("21")
        self.input_ddd.setAccessibleName("DDD")
        _install_digit_filter(self.input_ddd, max_digits=3)
        form.addRow("ddd:", self.input_ddd)

        self.input_prefixo = QLineEdit()
        self.input_prefixo.setPlaceholderText("9795")
        self.input_prefixo.setAccessibleName("Prefixo (4-5 dígitos)")
        _install_digit_filter(self.input_prefixo, max_digits=5)
        form.addRow("prefixo:", self.input_prefixo)

        self.input_info = QLineEdit()
        self.input_info.setPlaceholderText("confeiteira")
        self.input_info.setAccessibleName("Informação extra")
        form.addRow("info_extra:", self.input_info)

        outer.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_submit = QPushButton("Adicionar lead")
        self.btn_submit.setDefault(True)
        self.btn_submit.setAccessibleName("Adicionar lead à fila")
        self.btn_submit.clicked.connect(self._on_submit)
        btn_row.addWidget(self.btn_submit)
        outer.addLayout(btn_row)

        self.setTabOrder(self.input_desire, self.input_nome)
        self.setTabOrder(self.input_nome, self.input_ddd)
        self.setTabOrder(self.input_ddd, self.input_prefixo)
        self.setTabOrder(self.input_prefixo, self.input_info)
        self.setTabOrder(self.input_info, self.btn_submit)

        for w in (
            self.input_desire,
            self.input_nome,
            self.input_ddd,
            self.input_prefixo,
            self.input_info,
        ):
            w.returnPressed.connect(self._on_submit)

    def _validate(self) -> str | None:
        if not self.input_nome.text().strip():
            return "O campo 'nome' é obrigatório."
        if not self.input_ddd.text().strip():
            return "O campo 'ddd' é obrigatório (apenas dígitos)."
        if not self.input_prefixo.text().strip():
            return "O campo 'prefixo' é obrigatório (apenas dígitos)."
        return None

    def _on_submit(self) -> None:
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Campos obrigatórios", err)
            return

        self.btn_submit.setEnabled(False)
        try:
            with self._session_factory() as session:
                create_lead(
                    session,
                    desire=self.input_desire.text(),
                    nome=self.input_nome.text(),
                    ddd=self.input_ddd.text(),
                    prefixo=self.input_prefixo.text(),
                    info_extra=self.input_info.text(),
                )
        except Exception:
            logger.exception("lead_add_failed")
            QMessageBox.critical(
                self,
                "Erro ao salvar",
                "Não foi possível salvar o lead. Verifique o log para detalhes.",
            )
            return
        finally:
            self.btn_submit.setEnabled(True)

        self._reset_form()
        self.lead_added.emit()

    def _reset_form(self) -> None:
        for w in (
            self.input_desire,
            self.input_nome,
            self.input_ddd,
            self.input_prefixo,
            self.input_info,
        ):
            w.clear()
        self.input_nome.setFocus()
