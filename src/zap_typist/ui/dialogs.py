"""Dialogs de modal blocking utilizados em fluxos de boot/erro do Zap Typist."""

from __future__ import annotations

import sys


def show_blocking_modal(title: str, text: str, level: str = "critical") -> None:
    """Exibe um QMessageBox modal bloqueante.

    Cria QApplication caso ainda nao exista; os callers que ja inicializaram
    QApplication continuam reutilizando a instancia.
    """
    from PySide6.QtWidgets import QApplication, QMessageBox

    _app = QApplication.instance() or QApplication(sys.argv)
    box = QMessageBox()
    box.setWindowTitle(title)
    box.setText(text)
    if level == "critical":
        box.setIcon(QMessageBox.Icon.Critical)
    else:
        box.setIcon(QMessageBox.Icon.Warning)
    box.exec()
