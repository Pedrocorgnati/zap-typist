"""LeadCardList — container scrollável de LeadCardWidget (Aba 1, Bloco 3)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from zap_typist.db.models import Lead, LeadStatus
from zap_typist.ui.aba1.lead_card import LeadCardWidget
from zap_typist.ui.aba1.lead_card_list_config import LeadCardListConfig
from zap_typist.ui.styles import COLOR_FEEDBACK_ERROR
from zap_typist.utils.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

EMPTY_STATE_MSG = "Nenhuma query gerada ainda. Cadastre leads e clique /imbound:query."
ERROR_MSG = "Erro ao carregar leads — consulte logs."
PAGINATION_THRESHOLD = 100


class LeadCardList(QWidget):
    """QScrollArea com um LeadCardWidget por lead query_gerada."""

    submit_requested: Signal = Signal(int, str)
    discard_requested: Signal = Signal(int)
    submit_failed: Signal = Signal(int, str)
    page_change_requested: Signal = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        config: LeadCardListConfig | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or LeadCardListConfig()
        self._total_count: int = 0

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._content)

        self._nav_widget = QWidget()
        nav_layout = QHBoxLayout(self._nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        self._prev_btn = QPushButton("Anterior")
        self._prev_btn.setAccessibleName("Página anterior de leads")
        self._prev_btn.clicked.connect(self._on_prev_page)
        self._page_label = QLabel()
        self._next_btn = QPushButton("Próximo")
        self._next_btn.setAccessibleName("Próxima página de leads")
        self._next_btn.clicked.connect(self._on_next_page)
        nav_layout.addWidget(self._prev_btn)
        nav_layout.addWidget(self._page_label)
        nav_layout.addWidget(self._next_btn)
        nav_layout.addStretch()
        self._nav_widget.setVisible(False)

        root = QVBoxLayout(self)
        root.addWidget(self._scroll)
        root.addWidget(self._nav_widget)

        self._show_empty_state()

    def find_card_by_id(self, lead_id: int) -> LeadCardWidget | None:
        """Retorna o card correspondente ao lead_id ou None."""
        for i in range(self._content_layout.count()):
            item = self._content_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if isinstance(widget, LeadCardWidget) and widget._lead.id == lead_id:
                return widget
        return None

    def refresh(self, session: Session) -> None:
        self._config.current_page = 0
        self._load_page(session)

    def _load_page(self, session: Session) -> None:
        self._clear_layout(self._content_layout)
        try:
            self._total_count = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.query_gerada.value)
                .count()
            )
            use_pagination = self._total_count > PAGINATION_THRESHOLD
            query = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.query_gerada.value)
                .order_by(Lead.created_at.desc())
            )
            if use_pagination:
                offset = self._config.current_page * self._config.page_size
                leads: list[Lead] = query.offset(offset).limit(self._config.page_size).all()
            else:
                leads = query.all()
        except SQLAlchemyError:
            logger.error("lead_card_list_query_failed", exc_info=True)
            self._show_error_state()
            return

        if not leads:
            self._show_empty_state()
            self._nav_widget.setVisible(False)
            return

        for lead in leads:
            card = LeadCardWidget(lead, parent=self._content)
            card.submit_requested.connect(self.submit_requested)
            card.discard_requested.connect(self.discard_requested)
            card.submit_failed.connect(self.submit_failed)
            self._content_layout.addWidget(card)

        use_pagination = self._total_count > PAGINATION_THRESHOLD
        self._nav_widget.setVisible(use_pagination)
        if use_pagination:
            total_pages = max(1, -(-self._total_count // self._config.page_size))
            self._page_label.setText(
                f"Página {self._config.current_page + 1} de {total_pages}"
            )
            self._prev_btn.setEnabled(self._config.current_page > 0)
            self._next_btn.setEnabled(
                (self._config.current_page + 1) * self._config.page_size < self._total_count
            )

        logger.debug("rendered_lead_cards", extra={"count": len(leads)})

    def refresh_current_page(self, session: Session) -> None:
        """Recarrega a página atual sem resetar o número de página."""
        self._load_page(session)

    def _on_prev_page(self) -> None:
        if self._config.current_page > 0:
            self._config.current_page -= 1
            self.page_change_requested.emit()

    def _on_next_page(self) -> None:
        if (self._config.current_page + 1) * self._config.page_size < self._total_count:
            self._config.current_page += 1
            self.page_change_requested.emit()

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
