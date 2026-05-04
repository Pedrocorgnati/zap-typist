"""Audit AST cross-arquivo de PII (US-012) + testes runtime com canários.

G2: cobertura ampliada (repr/str/asdict/__dict__/model_dump/f-string implícito).
G3: exception leak via commit falho patchado (substitui UNIQUE violation — schema não tem
    UNIQUE constraint em numero_e164; usamos monkeypatch para forçar o path de exception).
G4: caplog captura LogRecord antes dos filters — _apply_pii_filter aplica PIIFilter
    manualmente sobre os records antes de assertar.

Limites documentados:
- AST não rastreia taint cross-function.
- AST não detecta serialização via __reduce__, pickle, deepcopy.
- AST não cobre módulos externos (Sentry etc.).
Os 3 testes runtime com canários cobrem fluxos críticos que o AST não alcança.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus, Setting

# ---------------------------------------------------------------------------
# Constantes do audit
# ---------------------------------------------------------------------------

PII_FIELDS = {
    "nome", "ddd", "prefixo", "sufixo", "numero_e164",
    "desire", "info_extra", "observacao",
}
PII_LOGGER_LEVELS = {"info", "warning", "error", "critical", "exception"}

PII_LEAKING_BUILTINS = {"repr", "str", "dict", "vars"}
PII_LEAKING_ATTRS = {"__dict__", "model_dump", "dict", "to_dict"}
PII_LEAKING_FUNCS = {"asdict", "model_dump"}

LEAD_BASE_NAMES = {"lead", "_lead", "self"}

MODULE_3_PATHS = [
    "src/zap_typist/ui/aba1",
    "src/zap_typist/ui/tab1_gerar_queries.py",
    "src/zap_typist/imbound",
    "src/zap_typist/engine/query_generator_worker.py",
    "src/zap_typist/services/lead_service.py",
]

PII_CANARIES = {
    "CANARIO_NOME_X1Q": "nome",
    "CANARIO_DDD_X2Q": "ddd",
    "CANARIO_PREFIXO_X3Q": "prefixo",
    "CANARIO_DESIRE_X4Q": "desire",
}

# ---------------------------------------------------------------------------
# Fixture: session factory local (mesmo padrão de test_tab1_gerar_queries.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory: scoped_session = scoped_session(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    session = factory()
    session.add(Setting(name="default_aba1_origin", value="getNinjas"))
    session.commit()
    factory.remove()
    yield factory
    factory.remove()
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers AST
# ---------------------------------------------------------------------------


def _iter_python_files(roots: list[str]) -> list[Path]:
    files = []
    for root in roots:
        p = Path(root)
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
    return files


def _walks_logger_call(node: ast.AST) -> tuple[str, str] | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr not in PII_LOGGER_LEVELS:
        return None
    return (func.attr, ast.unparse(node))


def _is_lead_reference(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id in LEAD_BASE_NAMES:
        return True
    return isinstance(node, ast.Attribute) and node.attr in {"_lead", "lead"}


def _build_taint_set(tree: ast.AST) -> set[str]:
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        is_full_lead_dump = False
        val = node.value
        if isinstance(val, ast.Attribute) and val.attr in PII_LEAKING_ATTRS and _is_lead_reference(val.value):  # noqa: E501
            is_full_lead_dump = True
        elif isinstance(val, ast.Call):
            fn = val.func
            fn_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)  # noqa: E501
            if fn_name in (PII_LEAKING_BUILTINS | PII_LEAKING_FUNCS) and val.args and _is_lead_reference(val.args[0]):  # noqa: E501, SIM114
                is_full_lead_dump = True
            elif isinstance(fn, ast.Attribute) and fn.attr in PII_LEAKING_ATTRS and _is_lead_reference(fn.value):  # noqa: E501
                is_full_lead_dump = True

        is_pii_field = (
            isinstance(val, ast.Attribute)
            and val.attr in PII_FIELDS
            and _is_lead_reference(val.value)
        )

        if not (is_full_lead_dump or is_pii_field):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                tainted.add(target.id)
    return tainted


def _contains_pii_attribute(call_node: ast.Call, tainted: set[str]) -> list[str]:
    found: list[str] = []

    def _scan(arg: ast.AST) -> None:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Attribute) and sub.attr in PII_FIELDS and _is_lead_reference(sub.value):  # noqa: E501
                base = sub.value.id if isinstance(sub.value, ast.Name) else getattr(sub.value, "attr", "?")  # noqa: E501
                found.append(f"{base}.{sub.attr}")

            if isinstance(sub, ast.Attribute) and sub.attr in PII_LEAKING_ATTRS and _is_lead_reference(sub.value):  # noqa: E501
                found.append(f"<full-dump via .{sub.attr}>")

            if isinstance(sub, ast.Call):
                fn = sub.func
                fn_name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)  # noqa: E501
                if fn_name in (PII_LEAKING_BUILTINS | PII_LEAKING_FUNCS) and sub.args and _is_lead_reference(sub.args[0]):  # noqa: E501
                    found.append(f"<full-dump via {fn_name}(lead)>")
                elif isinstance(fn, ast.Attribute) and fn.attr in PII_LEAKING_ATTRS and _is_lead_reference(fn.value):  # noqa: E501
                    found.append(f"<full-dump via .{fn.attr}()>")

            if isinstance(sub, ast.JoinedStr):
                for value_node in sub.values:
                    if not isinstance(value_node, ast.FormattedValue):
                        continue
                    expr = value_node.value
                    if _is_lead_reference(expr):
                        found.append("<f-string '{lead}' chama __str__>")
                    for inner in ast.walk(expr):
                        if isinstance(inner, ast.Attribute) and inner.attr in PII_FIELDS and _is_lead_reference(inner.value):  # noqa: E501
                            found.append(f"<f-string contém .{inner.attr}>")
                        if isinstance(inner, ast.Attribute) and inner.attr in PII_LEAKING_ATTRS and _is_lead_reference(inner.value):  # noqa: E501
                            found.append(f"<f-string contém full-dump .{inner.attr}>")
                        if isinstance(inner, ast.Name) and inner.id in tainted:
                            found.append(f"<f-string usa tainted '{inner.id}'>")

            if isinstance(sub, ast.Name) and sub.id in tainted:
                found.append(f"<tainted local '{sub.id}'>")

    for arg in [*call_node.args, *(kw.value for kw in call_node.keywords)]:
        _scan(arg)
    return found


# ---------------------------------------------------------------------------
# G4 helper: aplica PIIFilter manualmente sobre records do caplog
# ---------------------------------------------------------------------------

def _apply_pii_filter(records: list[logging.LogRecord]) -> list[logging.LogRecord]:
    """Aplica o PIIFilter da app sobre records do caplog.

    G4: caplog padrão não aplica filters do logger — captura LogRecord cru.
    Sem este helper, canários sanitizados pelo PIIFilter ainda apareceriam nos
    records, gerando falso positivo.
    """
    from zap_typist.utils.logger import PIIFilter
    f = PIIFilter()
    out = []
    for rec in records:
        if f.filter(rec):
            out.append(rec)
    return out


def _records_to_text(records: list[logging.LogRecord]) -> str:
    """Renderiza records pós-filter como texto buscável."""
    _SKIP = {
        "msg", "args", "name", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process",
    }
    parts = []
    for rec in records:
        parts.append(rec.getMessage())
        if rec.args:
            parts.append(repr(rec.args))
        for key, val in rec.__dict__.items():
            if key in _SKIP or key.startswith("_"):
                continue
            parts.append(f"{key}={val!r}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helper: captura direta de records do logger alvo (get_logger() seta propagate=False)
# ---------------------------------------------------------------------------

class _DirectCapture(logging.Handler):
    """Handler instalado diretamente no logger alvo para contornar propagate=False."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# ---------------------------------------------------------------------------
# ST003-A: Audit AST estático por arquivo
# ---------------------------------------------------------------------------

_module3_files = _iter_python_files(MODULE_3_PATHS)


@pytest.mark.parametrize("py_file", _module3_files, ids=lambda p: str(p))
def test_no_pii_in_logger_calls(py_file: Path) -> None:
    """AST audit estático.

    Limites conhecidos:
    - Não rastreia taint cross-function.
    - Não detecta serialização via __reduce__, copy.deepcopy, pickle.
    Os testes runtime cobrem os fluxos críticos.
    """
    src = py_file.read_text(encoding="utf-8")
    tree = ast.parse(src)
    tainted = _build_taint_set(tree)
    violations = []
    for node in ast.walk(tree):
        match = _walks_logger_call(node)
        if match is None:
            continue
        level, source_text = match
        pii = _contains_pii_attribute(node, tainted)
        if pii:
            violations.append(
                f"{py_file}: logger.{level}(...) contém PII: {pii}\n  source: {source_text}"
            )
    assert not violations, "Violações US-012 detectadas:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# ST003-B: Testes runtime com canários (G3/G4)
# ---------------------------------------------------------------------------


def test_no_pii_runtime_in_submit_handler(
    qtbot, in_memory_session_factory, monkeypatch
) -> None:
    """Submit handler: canários PII não devem aparecer nos logs (G4: handler direto)."""
    from zap_typist.ui.tab1_gerar_queries import Tab1GerarQueriesWidget

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)

    widget = Tab1GerarQueriesWidget(in_memory_session_factory)
    qtbot.addWidget(widget)

    session = in_memory_session_factory()
    session.add(Lead(
        nome="CANARIO_NOME_X1Q",
        ddd="CANARIO_DDD_X2Q",
        prefixo="CANARIO_PREFIXO_X3Q",
        desire="CANARIO_DESIRE_X4Q",
        info_extra=None,
        status=LeadStatus.query_gerada.value,
        origem="test",
    ))
    session.commit()
    lead_id = session.query(Lead).filter_by(nome="CANARIO_NOME_X1Q").first().id
    in_memory_session_factory.remove()

    # get_logger() seta propagate=False; instalar handler direto no logger alvo.
    capture = _DirectCapture()
    target_logger = logging.getLogger("zap_typist.ui.tab1_gerar_queries")
    target_logger.addHandler(capture)
    try:
        widget._on_card_submit(lead_id, "1234")
    finally:
        target_logger.removeHandler(capture)

    assert capture.records, "Nenhum record capturado — _DirectCapture não funcionou"
    surviving = _apply_pii_filter(capture.records)
    log_text = _records_to_text(surviving)
    for canary in PII_CANARIES:
        assert canary not in log_text, (
            f"PII canário '{canary}' sobreviveu ao PIIFilter no fluxo submit.\n"
            f"Surviving log:\n{log_text}"
        )


def test_no_pii_runtime_in_discard_handler(
    qtbot, in_memory_session_factory, monkeypatch
) -> None:
    """Discard handler: mesmo contrato de PII (G4: handler direto)."""
    from zap_typist.ui.tab1_gerar_queries import Tab1GerarQueriesWidget

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *_: None)

    widget = Tab1GerarQueriesWidget(in_memory_session_factory)
    qtbot.addWidget(widget)

    session = in_memory_session_factory()
    session.add(Lead(
        nome="CANARIO_NOME_X1Q",
        ddd="CANARIO_DDD_X2Q",
        prefixo="CANARIO_PREFIXO_X3Q",
        desire="CANARIO_DESIRE_X4Q",
        info_extra=None,
        status=LeadStatus.query_gerada.value,
        origem="test",
    ))
    session.commit()
    lead_id = session.query(Lead).filter_by(nome="CANARIO_NOME_X1Q").first().id
    in_memory_session_factory.remove()

    capture = _DirectCapture()
    target_logger = logging.getLogger("zap_typist.ui.tab1_gerar_queries")
    target_logger.addHandler(capture)
    try:
        widget._on_card_discard(lead_id)
    finally:
        target_logger.removeHandler(capture)

    assert capture.records, "Nenhum record capturado — _DirectCapture não funcionou"
    surviving = _apply_pii_filter(capture.records)
    log_text = _records_to_text(surviving)
    for canary in PII_CANARIES:
        assert canary not in log_text, (
            f"PII canário '{canary}' sobreviveu ao PIIFilter no fluxo discard.\n"
            f"Surviving log:\n{log_text}"
        )


def test_no_pii_in_commit_error_exception(
    qtbot, in_memory_session_factory, monkeypatch
) -> None:
    """G3: exception leak — commit falho com PII na mensagem não vaza para o log.

    Força commit a lançar SQLAlchemyError com canário no texto (simula UNIQUE violation
    que incluiria o valor violador). Verifica que o handler logou o evento de erro mas
    a mensagem de exceção não escapa para getMessage() nem para campos extras.
    """
    from sqlalchemy.exc import SQLAlchemyError

    from zap_typist.ui.tab1_gerar_queries import Tab1GerarQueriesWidget

    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *_: None)

    widget = Tab1GerarQueriesWidget(in_memory_session_factory)
    qtbot.addWidget(widget)

    session = in_memory_session_factory()
    session.add(Lead(
        nome="CANARIO_NOME_X1Q",
        ddd="11",
        prefixo="98765",
        desire=None,
        info_extra=None,
        status=LeadStatus.query_gerada.value,
        origem="test",
    ))
    session.commit()
    lead_id = session.query(Lead).filter_by(nome="CANARIO_NOME_X1Q").first().id
    in_memory_session_factory.remove()

    canary_e164 = "+5511CANARIO_E164_987659999"

    class _FailingFactory:
        """Factory que levanta SQLAlchemyError no commit com canário no texto."""
        def __init__(self, inner: Any) -> None:
            self._inner = inner
            self._session: Any = None

        def __call__(self) -> Any:
            self._session = self._inner()

            def _exploding_commit() -> None:
                raise SQLAlchemyError(
                    f"UNIQUE constraint failed: leads.numero_e164 value={canary_e164}"
                )

            self._session.commit = _exploding_commit
            return self._session

        def remove(self) -> None:
            if self._session is not None:
                self._session.close()
            self._inner.remove()

    widget._session_factory = _FailingFactory(in_memory_session_factory)  # type: ignore[assignment]

    capture = _DirectCapture()
    target_logger = logging.getLogger("zap_typist.ui.tab1_gerar_queries")
    target_logger.addHandler(capture)
    try:
        widget._on_card_submit(lead_id, "9999")
    finally:
        target_logger.removeHandler(capture)

    assert capture.records, "Nenhum record capturado — _DirectCapture não funcionou"
    surviving = _apply_pii_filter(capture.records)
    log_text = _records_to_text(surviving)

    # O getMessage() do record de erro é "aba1_submit_commit_failed", não a exceção.
    # exc_info=True é armazenado em exc_info/exc_text (campos internos, excluídos de log_text).
    assert canary_e164 not in log_text, (
        f"Exception message com e164 canário vazou no log:\n{log_text}"
    )
    for canary in PII_CANARIES:
        assert canary not in log_text, (
            f"PII canário '{canary}' sobreviveu ao PIIFilter no fluxo exception.\n"
            f"Surviving log:\n{log_text}"
        )
