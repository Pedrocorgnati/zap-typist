from __future__ import annotations

import contextlib
import errno
import os
import sys
import time
from types import TracebackType

from zap_typist.utils.logger import get_logger

logger = get_logger("zap_typist.app")

EXIT_OK = 0
EXIT_LOCK = 1
EXIT_OS_ERROR = 2
EXIT_SCHEMA_ERROR = 3


def _setup_excepthook() -> None:
    def handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("unhandled_exception", exc_info=(exc_type, exc_value, exc_tb))
        # US-016 [SUCCESS]: se ja ha QApplication, mostrar QMessageBox legivel.
        # Falhas no proprio hook NUNCA podem propagar (caso contrario ficamos em loop).
        with contextlib.suppress(Exception):
            from PySide6.QtWidgets import QApplication

            if QApplication.instance() is not None:
                _show_blocking_modal(
                    "Erro inesperado",
                    "Ocorreu um erro inesperado. Verifique o log em "
                    "~/.local/share/zap-typist/logs/zap-typist.log",
                    level="critical",
                )

    sys.excepthook = handle_exception


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


def _show_blocking_modal(title: str, text: str, level: str = "critical") -> None:
    """Wrapper que delega para zap_typist.ui.dialogs.show_blocking_modal.

    Mantido com prefixo _ no zap_typist.app para preservar monkeypatches dos
    testes que substituem zap_typist.app._show_blocking_modal.
    """
    from zap_typist.ui.dialogs import show_blocking_modal

    show_blocking_modal(title, text, level=level)


def _boot_os() -> int | None:
    """BOOT-003: cria dirs XDG com permissao 0700 e emite warning Wayland.

    Returns:
        EXIT_OS_ERROR em falha de I/O ou permissao; None em sucesso.
    """
    from zap_typist.db.models import APP_DATA_DIR
    from zap_typist.utils.cache import ensure_cache_dir

    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(APP_DATA_DIR, 0o700)
        ensure_cache_dir()  # cria CACHE_DIR + 0700; LOG_DIR ja criado por get_logger
    except PermissionError as exc:
        logger.critical(
            "xdg_permission_denied",
            extra={"path": str(APP_DATA_DIR), "error": str(exc)},
        )
        _show_blocking_modal(
            "Permissao negada",
            f"Nao foi possivel criar o diretorio de dados:\n{APP_DATA_DIR}\n\n"
            "Ajuste as permissoes (chmod u+w) e tente novamente.",
            level="critical",
        )
        return EXIT_OS_ERROR
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            logger.critical("xdg_disk_full", extra={"path": str(APP_DATA_DIR)})
            _show_blocking_modal(
                "Disco cheio",
                "Disco cheio - nao foi possivel criar o diretorio de dados. "
                "Libere espaco em disco e tente novamente.",
                level="critical",
            )
        else:
            logger.critical(
                "xdg_io_error",
                extra={"path": str(APP_DATA_DIR), "errno": exc.errno},
            )
            _show_blocking_modal(
                "Erro de I/O",
                f"Erro ao acessar diretorio de dados:\n{APP_DATA_DIR}\n\nDetalhe: {exc}",
                level="critical",
            )
        return EXIT_OS_ERROR

    if _is_wayland():
        logger.warning("wayland_detected")
        _show_blocking_modal(
            "Sessao Wayland detectada",
            "Zap Typist requer X11 para reparenting do Chrome.\n"
            "A Aba 3 ficara inoperante. Faca logout e selecione "
            "'Ubuntu on Xorg' no login para usar todas as funcionalidades.",
            level="warning",
        )

    return None


def _boot_db() -> int | None:
    """BOOT-004: init_db + validate_schema + seed.

    Returns:
        EXIT_OS_ERROR em falha de I/O, EXIT_SCHEMA_ERROR em schema invalido; None em sucesso.
    """
    from zap_typist.db.seed import run_seed
    from zap_typist.db.session import init_db, validate_schema
    from zap_typist.seeders import build_settings_defaults

    try:
        init_db()
    except PermissionError as exc:
        logger.critical("db_permission_denied", extra={"error": str(exc)})
        _show_blocking_modal(
            "Permissao negada",
            f"Nao foi possivel criar o banco de dados.\n\nDetalhe: {exc}",
            level="critical",
        )
        return EXIT_OS_ERROR
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            logger.critical("db_disk_full")
            _show_blocking_modal(
                "Disco cheio",
                "Disco cheio - nao foi possivel criar o banco de dados. "
                "Libere espaco em disco e tente novamente.",
                level="critical",
            )
        else:
            logger.critical("db_io_error", extra={"errno": exc.errno})
            _show_blocking_modal(
                "Erro ao inicializar o banco",
                f"Erro de I/O ao criar o banco de dados.\nDetalhe: {exc}",
                level="critical",
            )
        return EXIT_OS_ERROR

    try:
        validate_schema()
    except RuntimeError as exc:
        logger.critical("schema_invalid", extra={"error": str(exc)})
        _show_blocking_modal(
            "Banco corrompido",
            "O banco de dados parece corrompido (faltam tabelas esperadas).\n\n"
            f"Detalhe: {exc}\n\n"
            "Ultima saida: feche o app e mova ~/.local/share/zap-typist/zap_typist.db "
            "para um backup; o app vai recriar o banco no proximo boot.",
            level="critical",
        )
        return EXIT_SCHEMA_ERROR

    run_seed(defaults=build_settings_defaults(), force=False)
    return None


def _boot_qt(start_ts: float) -> int:
    """Cria QApplication + MainWindow e entra no event loop."""
    from PySide6.QtWidgets import QApplication

    from zap_typist.ui.main_window import MainWindow

    qt_app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()  # showMaximized() acontece no __init__
    _ = window  # supress unused warning

    elapsed_ms = int((time.monotonic() - start_ts) * 1000)
    logger.info("app_started", extra={"duration_ms": elapsed_ms})

    return qt_app.exec()


def main() -> int:
    start_ts = time.monotonic()

    _setup_excepthook()

    from zap_typist.utils.single_instance import SingleInstanceLock

    lock = SingleInstanceLock()
    if not lock.acquire():
        existing_pid = lock.get_existing_pid()
        logger.warning("single_instance_blocked", extra={"existing_pid": existing_pid})
        _show_blocking_modal(
            "Zap Typist ja esta rodando",
            f"Outra instancia esta ativa (PID: {existing_pid}).\nFeche-a antes de abrir uma nova.",
            level="critical",
        )
        return EXIT_LOCK

    try:
        if (code := _boot_os()) is not None:
            return code
        if (code := _boot_db()) is not None:
            return code
        return _boot_qt(start_ts)
    finally:
        lock.release()


if __name__ == "__main__":
    sys.exit(main())
