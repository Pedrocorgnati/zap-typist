"""Tab1GerarQueriesWidget — Aba 1 completa (Gerar Queries)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from zap_typist.db.models import Lead, LeadStatus
from zap_typist.engine.query_generator_worker import QueryGeneratorWorker
from zap_typist.ui.aba1.lead_card_list import LeadCardList
from zap_typist.ui.aba1.lead_form import LeadFormWidget
from zap_typist.ui.widgets.form_validators import LeadStatusGuard
from zap_typist.ui.widgets.terminal_widget import TerminalWidget
from zap_typist.utils.e164 import format_e164
from zap_typist.utils.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

TERMINAL_FIXED_HEIGHT = 150


class _ScopedSessionFactory(Protocol):
    """Protocol que casa com sqlalchemy.orm.scoped_session."""

    def __call__(self) -> Session: ...

    def remove(self) -> None: ...


class _TerminalPanel(QGroupBox):
    """Painel interno com TerminalWidget + botão /imbound:query."""

    imbound_query_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Terminal /imbound:query", parent)
        layout = QVBoxLayout(self)
        self.terminal = TerminalWidget()
        self.terminal.setFixedHeight(TERMINAL_FIXED_HEIGHT)
        layout.addWidget(self.terminal)
        self._btn = QPushButton("/imbound:query")
        self._btn.setStyleSheet("font-family: monospace; font-weight: bold;")
        self._btn.setAccessibleName(
            "Disparar geração de queries Google para leads pendentes"
        )
        self._btn.clicked.connect(self.imbound_query_clicked.emit)
        layout.addWidget(self._btn)

    def set_running(self, running: bool) -> None:
        self._btn.setEnabled(not running)
        self.terminal.set_running(running)


class Tab1GerarQueriesWidget(QWidget):
    """Widget principal da Aba 1 — layout vertical canônico.

    Layout:
        LeadFormWidget  (cadastro de leads)
        _TerminalPanel  (TerminalWidget + botão /imbound:query)
        LeadCardList    (cards de leads query_gerada, stretch=1)
        ProgressLabel   (contagens X/Y/Z/W)
    """

    def __init__(
        self,
        session_factory: _ScopedSessionFactory,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session_factory = session_factory
        self._active_thread: QThread | None = None
        self._active_worker: QueryGeneratorWorker | None = None
        self._setup_ui()
        self._connect_signals()
        self._refresh_progress()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._form = LeadFormWidget(self._session_factory)
        layout.addWidget(self._form)
        self._terminal_panel = _TerminalPanel()
        layout.addWidget(self._terminal_panel)
        self._lead_card_list = LeadCardList()
        layout.addWidget(self._lead_card_list, stretch=1)
        self._progress_label = QLabel()
        self._progress_label.setAccessibleName("Resumo de progresso da Aba 1")
        layout.addWidget(self._progress_label)

    def _connect_signals(self) -> None:
        self._form.lead_added.connect(self._on_lead_added)
        self._terminal_panel.imbound_query_clicked.connect(self._on_imbound_query_clicked)
        self._lead_card_list.submit_requested.connect(self._on_card_submit)
        self._lead_card_list.discard_requested.connect(self._on_card_discard)

    # ------------------------------------------------------------------
    # Handlers de form e worker
    # ------------------------------------------------------------------

    def _on_lead_added(self) -> None:
        logger.debug("aba1_lead_added")
        self._refresh_progress()

    def _on_imbound_query_clicked(self) -> None:
        if self._active_thread is not None:
            return
        logger.info("aba1_imbound_query_dispatched")
        self._terminal_panel.terminal.append_line("> /imbound:query")
        self._terminal_panel.set_running(True)

        worker = QueryGeneratorWorker(self._session_factory)
        thread = QThread(self)
        worker.moveToThread(thread)

        worker.signals.log_line.connect(self._terminal_panel.terminal.append_line)
        worker.signals.status_update.connect(self._terminal_panel.terminal.append_line)
        worker.signals.finished.connect(self._on_query_generator_finished)
        worker.signals.error.connect(self._on_query_generator_error)

        thread.started.connect(worker.execute)
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._active_thread = thread
        self._active_worker = worker
        thread.start()

    def _on_query_generator_finished(self) -> None:
        session = self._session_factory()
        try:
            self._lead_card_list.refresh(session)
        finally:
            self._session_factory.remove()
        self._refresh_progress()
        self._terminal_panel.set_running(False)
        self._active_thread = None
        self._active_worker = None
        logger.info("aba1_imbound_query_completed")

    def _on_query_generator_error(self, msg: str) -> None:
        logger.error("aba1_imbound_query_failed", extra={"error": msg})
        QMessageBox.critical(
            self,
            "Erro ao gerar queries",
            "Falha ao executar /imbound:query — consulte logs.",
        )
        self._terminal_panel.set_running(False)
        # CRÍTICO: limpar refs — BaseWorker pode emitir error sem emitir finished,
        # bloqueando cliques futuros (ver QueryGeneratorWorker — em prática finished
        # é sempre emitido pelo BaseWorker.execute(), mas defendemos aqui também).
        self._active_thread = None
        self._active_worker = None

    # ------------------------------------------------------------------
    # Handlers de card: Submit
    # ------------------------------------------------------------------

    def _on_card_submit(self, lead_id: int, sufixo: str) -> None:
        session = self._session_factory()
        refresh_needed = False
        try:
            lead = session.get(Lead, lead_id)
            if lead is None:
                logger.error("aba1_submit_lead_not_found", extra={"lead_id": lead_id})
                refresh_needed = True
                QMessageBox.warning(self, "Lead não encontrado", "Recarregue a lista.")
                return
            try:
                current_status = LeadStatus(lead.status)
            except ValueError:
                logger.error(
                    "aba1_submit_invalid_status_value",
                    extra={"lead_id": lead_id, "status_raw": lead.status},
                )
                refresh_needed = True
                QMessageBox.critical(
                    self, "Status inválido", "Estado do lead corrompido — consulte logs."
                )
                return
            if not LeadStatusGuard.can_transition(current_status, LeadStatus.telefone_preenchido):
                logger.warning(
                    "aba1_submit_invalid_transition",
                    extra={
                        "lead_id": lead_id,
                        "from": current_status.value,
                        "to": "telefone_preenchido",
                    },
                )
                refresh_needed = True
                QMessageBox.warning(
                    self, "Transição inválida", "Status atual não permite Submit."
                )
                return
            e164 = format_e164(lead.ddd or "", lead.prefixo or "", sufixo)
            if e164 is None:
                logger.warning("aba1_submit_invalid_e164", extra={"lead_id": lead_id})
                refresh_needed = True
                QMessageBox.warning(
                    self,
                    "Telefone inválido",
                    "Combinação DDD + prefixo + sufixo não forma um número E.164 válido.",
                )
                return
            lead.sufixo = sufixo
            lead.numero_e164 = e164
            lead.status = LeadStatus.telefone_preenchido.value
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                logger.error(
                    "aba1_submit_commit_failed", exc_info=True, extra={"lead_id": lead_id}
                )
                refresh_needed = True
                QMessageBox.critical(self, "Erro ao salvar", "Falha ao persistir — consulte logs.")
                return
            logger.info("aba1_submit_succeeded", extra={"lead_id": lead_id})
            self._lead_card_list.refresh(session)
            self._refresh_progress()
        finally:
            if refresh_needed:
                try:
                    self._lead_card_list.refresh(session)
                    self._refresh_progress()
                except Exception:
                    logger.exception(
                        "aba1_submit_sad_path_refresh_failed", extra={"lead_id": lead_id}
                    )
            self._session_factory.remove()

    # ------------------------------------------------------------------
    # Handlers de card: Descartar
    # ------------------------------------------------------------------

    def _on_card_discard(self, lead_id: int) -> None:
        session = self._session_factory()
        refresh_needed = False
        try:
            lead = session.get(Lead, lead_id)
            if lead is None:
                logger.error("aba1_discard_lead_not_found", extra={"lead_id": lead_id})
                refresh_needed = True
                QMessageBox.warning(self, "Lead não encontrado", "Recarregue a lista.")
                return
            try:
                current_status = LeadStatus(lead.status)
            except ValueError:
                logger.error(
                    "aba1_discard_invalid_status_value",
                    extra={"lead_id": lead_id, "status_raw": lead.status},
                )
                refresh_needed = True
                QMessageBox.critical(
                    self, "Status inválido", "Estado do lead corrompido — consulte logs."
                )
                return
            if not LeadStatusGuard.can_transition(current_status, LeadStatus.descartado):
                logger.warning(
                    "aba1_discard_invalid_transition",
                    extra={
                        "lead_id": lead_id,
                        "from": current_status.value,
                        "to": "descartado",
                    },
                )
                refresh_needed = True
                QMessageBox.warning(
                    self, "Transição inválida", "Status atual não permite Descartar."
                )
                return
            lead.status = LeadStatus.descartado.value
            try:
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                logger.error(
                    "aba1_discard_commit_failed", exc_info=True, extra={"lead_id": lead_id}
                )
                refresh_needed = True
                QMessageBox.critical(self, "Erro ao salvar", "Falha ao persistir — consulte logs.")
                return
            logger.info("aba1_discard_succeeded", extra={"lead_id": lead_id})
            self._lead_card_list.refresh(session)
            self._refresh_progress()
        finally:
            if refresh_needed:
                try:
                    self._lead_card_list.refresh(session)
                    self._refresh_progress()
                except Exception:
                    logger.exception(
                        "aba1_discard_sad_path_refresh_failed", extra={"lead_id": lead_id}
                    )
            self._session_factory.remove()

    # ------------------------------------------------------------------
    # Progress label
    # ------------------------------------------------------------------

    def _refresh_progress(self) -> None:
        """Atualiza ProgressLabel com contagens canônicas do INTAKE.

        Y = total geral de leads (todos os status), conforme INTAKE §"Caso de Uso
        Completo" passo 10: "1 de 12 preenchidos, 1 descartado, 10 pendentes" → Y=12
        inclui pendentes.
        """
        session = self._session_factory()
        try:
            x = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.telefone_preenchido.value)
                .count()
            )
            z = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.descartado.value)
                .count()
            )
            qg = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.query_gerada.value)
                .count()
            )
            w = (
                session.query(Lead)
                .filter(Lead.status == LeadStatus.pendente.value)
                .count()
            )
            y = x + z + qg + w
            if y == 0:
                text = "Nenhum lead cadastrado ainda."
            else:
                text = f"{x} de {y} telefones preenchidos, {z} descartados, {w} pendentes"
            self._progress_label.setText(text)
            logger.debug(
                "aba1_progress_refreshed", extra={"x": x, "y": y, "z": z, "w": w, "qg": qg}
            )
        finally:
            self._session_factory.remove()


def get_aba1_widget(
    session_factory: _ScopedSessionFactory,
    parent: QWidget | None = None,
) -> Tab1GerarQueriesWidget:
    """Factory para injetar no MainWindow sem expor o construtor diretamente."""
    return Tab1GerarQueriesWidget(session_factory, parent)
