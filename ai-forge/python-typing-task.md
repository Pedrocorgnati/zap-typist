# Python Typing — Plan (module-1-setup)

**Modo:** `--plan`
**Stack:** mypy 1.10, Python 3.11, src-layout
**Comando equivalente:** `/python:typing plan .claude/projects/zap-typist.json`

---

## FASE 1 — Auditoria

### Estado atual

`pyproject.toml`:
- `strict = false`
- `disallow_untyped_defs = false`
- `warn_unused_ignores = true` (✓)
- Sem `[[tool.mypy.overrides]]` por módulo

**Modelos (`db/models.py`):** tipagem exemplar — `Mapped[int]`, `Mapped[str | None]`, `enum.StrEnum` (Python 3.11+). Nada a corrigir.

**Sessão (`db/session.py`):** `TypeVar T`, `Callable[[], T]`, `Engine`, `OperationalError | None`. Boa cobertura. 1 escape: linha 44 `def _on_connect(dbapi_conn, _record):  # noqa: ANN001`.

**Utils:** `cache.py`, `single_instance.py`, `logger.py` — type hints completas em assinaturas públicas.

**App (`app.py`):** lazy imports de PySide6 dentro de funções. 2 escapes:
- linha 20 `def handle_exception(exc_type, exc_value, exc_tb):  # noqa: ANN001`
- linha 71 `def _build_main_window():  # noqa: ANN201`

### Gaps identificados

| # | Sev | Categoria | Achado | Evidência |
|---|-----|-----------|--------|-----------|
| T-01 | P0 | distribuição | Falta `py.typed` marker — pacote não declara suporte a type hints para consumidores externos. | `src/zap_typist/` (ausência de `py.typed`) |
| T-02 | P1 | strictness | `strict=false` global desabilita várias checagens (`disallow_untyped_calls`, `warn_return_any`, `no_implicit_optional`). | `pyproject.toml:17-19` |
| T-03 | P1 | excepthook | `handle_exception` sem assinatura tipada (`exc_type: type[BaseException]`, `exc_value: BaseException`, `exc_tb: TracebackType`). Ignorado via `# noqa: ANN001`. | `src/zap_typist/app.py:20` |
| T-04 | P2 | factory return | `_build_main_window()` retorna classe local `MainWindow` mas declarado sem retorno (`# noqa: ANN201`). Tipar como `type[QMainWindow]`. | `src/zap_typist/app.py:71` |
| T-05 | P2 | sqlalchemy event | `_on_connect(dbapi_conn, _record)` sem hint. Tipar `dbapi_conn: Any` (DBAPI Connection) ou `sqlalchemy.engine.interfaces.DBAPIConnection`. | `src/zap_typist/db/session.py:44` |
| T-06 | P2 | dict generic | `payload: dict = {...}` sem parametrização. Trocar por `payload: dict[str, Any]`. | `src/zap_typist/utils/logger.py:59` |
| T-07 | P3 | tests | `tests/conftest.py` e fixtures sem hints de retorno (`Iterator[Engine]`). | `tests/conftest.py:9-77` |

---

## FASE 2 — Correções propostas (NÃO APLICADAS)

### Fix T-01: py.typed marker

```bash
touch src/zap_typist/py.typed
```

E em `pyproject.toml`:
```toml
[tool.setuptools.package-data]
"zap_typist" = ["py.typed"]
```

### Fix T-02: strict gradual via overrides

(Coordenado com Fix C-02 do `python-configuration-task.md` — não duplicar.)

### Fix T-03: tipar excepthook

```python
from types import TracebackType
from typing import Type

def handle_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    ...
```

Remover o `# noqa: ANN001`.

### Fix T-04: tipar factory de MainWindow

```python
from PySide6.QtWidgets import QMainWindow  # apenas para hint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


def _build_main_window() -> type[QMainWindow]:
    from PySide6.QtWidgets import QMainWindow as _QMainWindow
    ...
    class MainWindow(_QMainWindow):
        ...
    return MainWindow
```

`TYPE_CHECKING` evita import eager de PySide6 (necessário para `_boot_qt` lazy boot).

### Fix T-05: tipar event listener SQLAlchemy

```python
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry

@event.listens_for(eng, "connect")
def _on_connect(dbapi_conn: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    cursor = dbapi_conn.cursor()
    ...
```

### Fix T-06: payload dict tipado

```python
from typing import Any

def format(self, record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
        ...
    }
```

### Fix T-07: tipar fixtures conftest

```python
from collections.abc import Iterator
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

@pytest.fixture
def in_memory_engine() -> Iterator[Engine]:
    ...

@pytest.fixture
def in_memory_session(in_memory_engine: Engine) -> Iterator[Session]:
    ...
```

---

## FASE 3 — Validação

```bash
mypy src --strict-equality --warn-redundant-casts --warn-unused-ignores
mypy tests
ruff check src tests --select ANN
```

**Aceite:** mypy sem erros sob overrides do Fix C-02; zero `# noqa: ANN*` em `src/`.

---

## Resumo

- **Issues:** 7 (P0: 1 · P1: 2 · P2: 3 · P3: 1)
- **Fixes propostos:** 7
- **Esforço:** 1-2h
- **Depende de:** Fix C-02 (mypy overrides) do `python-configuration-task.md`
