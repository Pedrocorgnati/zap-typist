"""LeadCardList — container scrollável de LeadCardWidget (Aba 1, Bloco 3)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from zap_typist.db.models import Lead, LeadStatus
from zap_typist.ui.aba1.lead_card import LeadCardWidget
from zap_typist.ui.styles import COLOR_FEEDBACK_ERROR
from zap_typist.utils.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

EMPTY_STATE_MSG = "Nenhuma query gerada ainda. Cadastre leads e clique /imbound:query."
ERROR_MSG = "Erro ao carregar leads — consulte logs."


class LeadCardList(QWidget):
    """QScrollArea com um LeadCardWidget por lead query_gerada."""

    submit_requested: Signal = Signal(int, str)
    discard_requested: Signal = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._content)

        root = QVBoxLayout(self)
        root.addWidget(self._scroll)

        self._show_empty_state()

    def refresh(self, session: Session) -> None:
        self._clear_layout(self._content_layout)
        try:
            leads: list[Lead] = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.query_gerada.value)
                .order_by(Lead.created_at.desc())
                .all()
            )
        except SQLAlchemyError:
            logger.error("lead_card_list_query_failed", exc_info=True)
            self._show_error_state()
            return

        if not leads:
            self._show_empty_state()
            return

        for lead in leads:
            card = LeadCardWidget(lead, parent=self._content)
            card.submit_requested.connect(self.submit_requested)
            card.discard_requested.connect(self.discard_requested)
            self._content_layout.addWidget(card)

        logger.debug("rendered_lead_cards", extra={"count": len(leads)})

    def _show_empty_state(self) -> None:
        label = QLabel(EMPTY_STATE_MSG)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(label)

    def _show_error_state(self) -> None:
        label = QLabel(ERROR_MSG)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLOR_FEEDBACK_ERROR};")
        self._content_layout.addWidget(label)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
