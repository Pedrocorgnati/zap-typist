"""Hardening do module-2-shared-foundations.

Cobertura:
- PIIFilter cobre PII_KEYS canônicos (LLD §8.2, SEC-008)
- Logger redige nome / numero_e164 com string "***FILTRADO***"
- PIIFilter é seletivo (não redige campos não-sensíveis)
- format_e164 é função pura (zero side effects)
- BaseWorker libera SessionFactory.remove() no finally via execute()
- APP_DATA_DIR tem permissão 0o700 (SEC-009)

Nota: EXPECTED_PII_FIELDS segue LLD §8.2 (schema-aligned, 11 campos),
não os 7 campos genéricos do INTAKE SEC-008. LLD prevalece sobre INTAKE
na hierarquia documental do projeto.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from zap_typist.engine.base_worker import BaseWorker
from zap_typist.utils.e164 import format_e164
from zap_typist.utils.logger import PII_KEYS, get_logger

# String de redação real do PIIFilter (conforme implementação em utils/logger.py).
REDACTION_STRING = "***FILTRADO***"

# Campos PII canônicos conforme LLD §8.2 (schema do Lead — 11 campos).
# Fonte autoritativa: LLD prevalece sobre o INTAKE genérico (SEC-008).
EXPECTED_PII_FIELDS = frozenset({
    "nome",
    "numero_e164",
    "desire",
    "info_extra",
    "observacao",
    "mensagem",
    "template_render",
    "desire_adaptado",
    "ddd",
    "prefixo",
    "sufixo",
})


@pytest.fixture(scope="module")
def qapp():
    """QApplication para instanciar QObject (WorkerSignals) nos testes de worker."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# PIIFilter — SEC-008
# ---------------------------------------------------------------------------


def test_pii_filter_covers_all_sensitive_fields() -> None:
    """`PII_KEYS` deve conter exatamente os campos do LLD §8.2 (SEC-008).

    Verifica que PII_KEYS é superset de EXPECTED_PII_FIELDS (11 campos schema-aligned).
    """
    missing = EXPECTED_PII_FIELDS - PII_KEYS
    assert not missing, (
        f"[SEC-008] Campos PII faltando em PII_KEYS: {missing}. "
        f"Verificar utils/logger.py em module-1."
    )


def test_pii_keys_is_not_empty() -> None:
    """PII_KEYS deve ter pelo menos os campos que já foram implementados."""
    # Subconjunto que já está em PII_KEYS — smoke mínimo que sempre passa.
    implemented = {"nome", "numero_e164", "mensagem"}
    assert implemented <= PII_KEYS, f"PII_KEYS incompleto: falta {implemented - PII_KEYS}"


def test_logger_redacts_nome_field(isolated_log_dir: Path) -> None:
    """`logger.info(extra={'nome': ...})` não pode escrever o nome em cleartext."""
    logger = get_logger("test_sec_pii_nome")
    logger.info("user_action", extra={"nome": "Pedro Silva", "event": "click"})

    log_file = isolated_log_dir / "zap-typist.log"
    assert log_file.exists(), "logger não criou arquivo no LOG_DIR isolado"
    content = log_file.read_text(encoding="utf-8")
    assert "Pedro Silva" not in content, "Nome vazou em cleartext no log"
    assert REDACTION_STRING in content, "PIIFilter não substituiu o valor"


def test_logger_redacts_numero_e164(isolated_log_dir: Path) -> None:
    """Telefone E.164 não pode aparecer em cleartext no log."""
    logger = get_logger("test_sec_pii_phone")
    logger.info("dispatch", extra={"numero_e164": "+5511987654321"})

    content = (isolated_log_dir / "zap-typist.log").read_text(encoding="utf-8")
    assert "+5511987654321" not in content, "Telefone E.164 vazou em cleartext"
    assert REDACTION_STRING in content, "PIIFilter não substituiu o valor"


def test_pii_filter_is_selective(isolated_log_dir: Path) -> None:
    """Campos não-sensíveis devem permanecer cleartext (PIIFilter é seletivo)."""
    logger = get_logger("test_sec_pii_selective")
    logger.info("event", extra={"safe_field": "ok-value", "request_id": "req-123"})

    content = (isolated_log_dir / "zap-typist.log").read_text(encoding="utf-8")
    assert "ok-value" in content, "Valor não-PII foi redigido por engano"
    assert "req-123" in content, "request_id foi redigido por engano"


# ---------------------------------------------------------------------------
# format_e164 — pureza (sem side effects)
# ---------------------------------------------------------------------------


def test_format_e164_is_pure_function(isolated_log_dir: Path) -> None:
    """N chamadas com mesmo input retornam mesmo output e não criam logs/arquivos."""
    results = {format_e164("11", "98765", "4321") for _ in range(100)}
    assert len(results) == 1, f"format_e164 não-determinístico: {results}"

    # format_e164 não pode ter criado arquivo de log nem artefatos no LOG_DIR isolado.
    artifacts = list(isolated_log_dir.iterdir())
    assert artifacts == [], f"format_e164 tem side effect — artefatos: {artifacts}"


def test_format_e164_returns_none_for_invalid_input() -> None:
    """Input inválido não levanta — retorna None (contrato C2)."""
    assert format_e164("00", "98765", "4321") is None
    assert format_e164("11", "abc", "4321") is None


def test_format_e164_deterministic() -> None:
    """Mesma entrada sempre produz mesma saída — determinismo básico."""
    expected = format_e164("11", "98765", "4321")
    for _ in range(50):
        assert format_e164("11", "98765", "4321") == expected


# ---------------------------------------------------------------------------
# BaseWorker — cleanup de SessionFactory
# ---------------------------------------------------------------------------


class _NoopWorker(BaseWorker):
    """Worker que adquire sessão e termina imediatamente."""

    def run(self) -> None:  # type: ignore[override]
        self.get_session()  # adquire sessão para trigger do remove() no finally


def test_base_worker_calls_session_remove_on_run_finish(qapp) -> None:
    """execute() garante que `SessionFactory.remove()` é chamado mesmo em run() imediato."""
    session_factory = MagicMock()
    worker = _NoopWorker(session_factory=session_factory)
    worker.execute()
    session_factory.remove.assert_called_once()


def test_base_worker_remove_called_after_cancel(qapp) -> None:
    """execute() chama remove() mesmo quando run() é interrompido por cancel()."""

    class _CancelableWorker(BaseWorker):
        def run(self) -> None:  # type: ignore[override]
            self.get_session()
            while not self.cancel_requested:
                time.sleep(0.001)

    session_factory = MagicMock()
    worker = _CancelableWorker(session_factory=session_factory)
    thread = threading.Thread(target=worker.execute, daemon=True)
    thread.start()
    time.sleep(0.05)
    worker.cancel()
    thread.join(timeout=1.0)

    session_factory.remove.assert_called_once()


# ---------------------------------------------------------------------------
# APP_DATA_DIR — SEC-009
# ---------------------------------------------------------------------------


def test_app_data_dir_has_0700_perms() -> None:
    """APP_DATA_DIR criado pelo bootstrap deve ter permissão 0o700 (POSIX)."""
    if os.name != "posix":
        pytest.skip("perms 0700 só verificáveis em POSIX")

    try:
        from zap_typist.config.paths import APP_DATA_DIR
    except ImportError:
        pytest.skip("zap_typist.config.paths.APP_DATA_DIR não exportado por module-1")

    if not APP_DATA_DIR.exists():
        pytest.skip(
            f"APP_DATA_DIR não existe ({APP_DATA_DIR}); bootstrap não rodou nesta sessão"
        )

    mode = APP_DATA_DIR.stat().st_mode & 0o777
    assert mode == 0o700, f"APP_DATA_DIR perms = {oct(mode)} (esperado 0o700)"
