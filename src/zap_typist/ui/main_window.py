"""Janela principal do Zap Typist (placeholder com 4 abas, FEAT-skel-022).

Lazy import garantido pelo caller: este modulo so deve ser importado dentro de
funcoes que ja vao instanciar QApplication, para evitar custo de carregar Qt em
testes que mockam UI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from zap_typist.db.session import SessionFactory
from zap_typist.ui.tab1_gerar_queries import get_aba1_widget
from zap_typist.utils.logger import get_logger

logger = get_logger("zap_typist.ui.main_window")

_PLACEHOLDER_TABS: tuple[tuple[str, str], ...] = (
    ("Gerar Contatos", "Em desenvolvimento — aguardando rock 2 (aba2-contatos)"),
    ("Enviar Mensagens", "Em desenvolvimento — aguardando rock 3 (aba3-envio)"),
    ("Configurações", "Em desenvolvimento — aguardando rock 4 (aba4-config)"),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Zap Typist")
        self.setMinimumSize(1280, 800)

        self.tabs = QTabWidget(self)

        # Aba 1 — funcional (module-3-aba1-queries)
        self.tabs.addTab(get_aba1_widget(SessionFactory), "Gerar Queries")

        # Abas 2/3/4 — placeholders
        for label, placeholder in _PLACEHOLDER_TABS:
            container = QWidget()
            layout = QVBoxLayout(container)
            lbl = QLabel(placeholder)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            self.tabs.addTab(container, label)

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status.showMessage("DB pronto, 0 leads")

        for i in range(4):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda idx=i: self.tabs.setCurrentIndex(idx))

        stop_sc = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        stop_sc.activated.connect(self._emergency_stop_stub)

        self.showMaximized()

    def _emergency_stop_stub(self) -> None:
        logger.warning("emergency_stop_triggered", extra={"phase": "stub"})

    def update_lead_count(self, n: int) -> None:
        self.status.showMessage(f"DB pronto, {n} leads")
