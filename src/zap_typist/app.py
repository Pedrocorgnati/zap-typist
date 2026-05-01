from __future__ import annotations

import os
import sys
import time

from zap_typist.utils.logger import get_logger

logger = get_logger("zap_typist.app")


def _setup_excepthook() -> None:
    def handle_exception(exc_type, exc_value, exc_tb):  # noqa: ANN001
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("unhandled_exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = handle_exception


def _is_wayland() -> bool:
    return (
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        or bool(os.environ.get("WAYLAND_DISPLAY"))
    )


def _show_blocking_modal(title: str, text: str, level: str = "critical") -> None:
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


def _build_main_window():  # noqa: ANN201
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

    class MainWindow(QMainWindow):
        TAB_LABELS = (
            ("Gerar Queries", "Em desenvolvimento — aguardando rock 1 (aba1-queries)"),
            ("Gerar Contatos", "Em desenvolvimento — aguardando rock 2 (aba2-contatos)"),
            ("Enviar Mensagens", "Em desenvolvimento — aguardando rock 3 (aba3-envio)"),
            ("Configurações", "Em desenvolvimento — aguardando rock 4 (aba4-config)"),
        )

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Zap Typist")
            self.setMinimumSize(1280, 800)

            self.tabs = QTabWidget(self)
            for label, placeholder in self.TAB_LABELS:
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

    return MainWindow


def main() -> int:
    start_ts = time.monotonic()

    # BOOT-001: excepthook antes de qualquer Qt
    _setup_excepthook()

    # BOOT-002: single-instance
    from zap_typist.utils.single_instance import SingleInstanceLock

    lock = SingleInstanceLock()
    if not lock.acquire():
        existing_pid = lock.get_existing_pid()
        logger.warning("single_instance_blocked", extra={"existing_pid": existing_pid})
        _show_blocking_modal(
            "Zap Typist já está rodando",
            f"Outra instância está ativa (PID: {existing_pid}).\n"
            "Feche-a antes de abrir uma nova.",
            level="critical",
        )
        return 1

    try:
        # BOOT-003: XDG dirs 0700
        from zap_typist.db.models import APP_DATA_DIR
        from zap_typist.utils.cache import ensure_cache_dir

        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(APP_DATA_DIR, 0o700)
        except OSError:
            pass
        ensure_cache_dir()  # cria CACHE_DIR + 0700; LOG_DIR já criado por get_logger

        # Wayland warning (informativo, não bloqueia)
        if _is_wayland():
            logger.warning("wayland_detected")
            _show_blocking_modal(
                "Sessão Wayland detectada",
                "Zap Typist requer X11 para reparenting do Chrome.\n"
                "A Aba 3 ficará inoperante. Faça logout e selecione "
                "'Ubuntu on Xorg' no login para usar todas as funcionalidades.",
                level="warning",
            )

        # BOOT-004: DB init + seed
        from zap_typist.db.seed import run_seed
        from zap_typist.db.session import init_db

        init_db()
        run_seed(force=False)

        # QApplication + MainWindow
        from PySide6.QtWidgets import QApplication

        qt_app = QApplication.instance() or QApplication(sys.argv)
        MainWindow = _build_main_window()
        window = MainWindow()  # showMaximized() acontece no __init__
        _ = window  # supress unused warning

        elapsed_ms = int((time.monotonic() - start_ts) * 1000)
        logger.info("app_started", extra={"duration_ms": elapsed_ms})

        exit_code = qt_app.exec()
        return exit_code
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
