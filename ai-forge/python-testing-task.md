# Python Testing — Plan (module-1-setup)

**Modo:** `--plan`
**Stack:** pytest 8, pytest-qt 4 (declarado), SQLAlchemy 2 in-memory
**Comando equivalente:** `/python:testing plan .claude/projects/zap-typist.json`

---

## FASE 1 — Auditoria

### Estado atual

```
tests/
├── conftest.py              # in_memory_engine, in_memory_session, db_engine, db_session, seeded_session
├── factories/
│   └── __init__.py          # vazio
└── unit/
    ├── __init__.py
    ├── test_app_boot_errors.py
    ├── test_boot_smoke.py
    ├── test_cache_errors.py
    ├── test_excepthook.py
    ├── test_models.py
    ├── test_path_constants.py
    ├── test_pii_filter.py
    ├── test_seed.py
    ├── test_session.py
    └── test_utils.py
```

13 arquivos de teste. Todos em `tests/unit/`. Nenhum em `tests/integration/` ou `tests/e2e/`.

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
# SEM addopts, SEM markers, SEM cov
```

`requirements.txt` declara `pytest-qt>=4.4` mas nenhum teste usa `qtbot` fixture. Factories dir existe mas vazia (sem `factory-boy`).

`tests/conftest.py:65` define `_StubFactory` ad-hoc para mockar `SessionFactory` em `seeded_session`.

### Sample exam (`test_models.py`):

10 testes cobrindo:
- Estrutura de tabelas (`test_all_tables_created`)
- Enums (`test_lead_status_has_10_values`, `test_flow_mode_has_2_values`)
- Constantes operacionais
- Indices
- INSERT minimal + defaults
- CHECK constraints (status enum, rate_limit max, mode enum)
- FK enforcement (`test_contact_history_requires_flow`)

Sem testes de:
- `retry_on_locked` em `db/session.py:69` (apenas exemplificado)
- Triggers `updated_at` (DDL eventos `db/models.py:227-237`)
- WAL/PRAGMA (validar que `journal_mode=WAL` aplica)

### Gaps identificados

| # | Sev | Categoria | Achado | Evidência |
|---|-----|-----------|--------|-----------|
| TEST-01 | P1 | coverage | Sem `pytest-cov` configurado nem gate. Sem visibilidade de coverage. | `pyproject.toml`, `Makefile:21` |
| TEST-02 | P1 | layering | Apenas `tests/unit/`. Falta `tests/integration/` para SQLite real (file-based) e teste de `WAL`/PRAGMA com engine real (não in-memory). | `tests/` (sem dir `integration`) |
| TEST-03 | P1 | markers | Sem `[tool.pytest.ini_options].markers`. Testes Qt (boot, excepthook) e DB rodam misturados sem `-m unit`/`-m integration`. | `pyproject.toml` |
| TEST-04 | P2 | factories | `tests/factories/__init__.py` vazio, `factory-boy` não instalado. `_StubFactory` definido inline em `conftest.py:65`. | `tests/factories/__init__.py`, `tests/conftest.py:65-72` |
| TEST-05 | P2 | retry tests | Falta cobertura de `retry_on_locked` (3 retries, OperationalError 'locked', backoff). | `src/zap_typist/db/session.py:69-97` (sem test) |
| TEST-06 | P2 | trigger tests | Falta cobertura de triggers `updated_at` (auto-update em UPDATE em leads/settings/flows). | `src/zap_typist/db/models.py:222-237` |
| TEST-07 | P3 | randomness | Sem `pytest-randomly` (ordem fixa esconde dependência entre testes). | `requirements.txt` |
| TEST-08 | P3 | qt fixtures | `pytest-qt` declarado mas zero usos de `qtbot`. Validar se realmente é necessário ou remover. | `requirements.txt:7`, `tests/**/*.py` |

---

## FASE 2 — Correções propostas (NÃO APLICADAS)

### Fix TEST-01: cov + gate

(Coordenado com Fix C-04 do `python-configuration-task.md`.)

Validar com:
```bash
pytest --cov=zap_typist --cov-report=term-missing --cov-fail-under=70
```

### Fix TEST-02: dir `tests/integration/`

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

Criar `tests/integration/conftest.py`:

```python
"""Fixtures de integração: SQLite file-based em tmp dir + WAL real."""
from __future__ import annotations
from collections.abc import Iterator
from pathlib import Path
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from zap_typist.db.models import Base


@pytest.fixture
def file_engine(tmp_path: Path) -> Iterator[Engine]:
    """Engine SQLite file-based com WAL — usado em integration tests."""
    db_path = tmp_path / "zap_typist.db"
    eng = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"timeout": 5, "check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _on_connect(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()
```

Mover/criar:
- `tests/integration/test_wal_pragma.py` — valida `PRAGMA journal_mode=wal` ativo após connect.
- `tests/integration/test_session_real.py` — `init_db()`/`validate_schema()` em `tmp_path`.

### Fix TEST-03: markers explícitos

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = [
  "unit: testes unitários puros (DB in-memory, sem Qt)",
  "integration: testes que tocam SQLite file-based ou subprocess",
  "qt: testes que requerem QApplication (lentos, isolados)",
  "boot: cenários de inicialização (single-instance, excepthook)",
]
```

Adicionar marker no topo de `tests/unit/test_app_boot_errors.py` e `test_excepthook.py`:

```python
import pytest
pytestmark = [pytest.mark.unit, pytest.mark.boot]
```

### Fix TEST-04: factory-boy + relocate StubFactory

Adicionar `factory-boy>=3.3` em `[project.optional-dependencies] dev`.

Criar `tests/factories/db.py`:

```python
"""Factories canônicas para Lead, Flow, ContactHistory, Setting."""
from __future__ import annotations
from typing import Any
import factory
from zap_typist.db.models import Lead, Flow, ContactHistory, Setting, LeadStatus


class LeadFactory(factory.Factory):
    class Meta:
        model = Lead

    nome = factory.Faker("name", locale="pt_BR")
    origem = "getNinjas"
    status = LeadStatus.pendente.value


class FlowFactory(factory.Factory):
    class Meta:
        model = Flow

    nome = factory.Sequence(lambda n: f"flow-{n}")
    chrome_profile = "default"
    mode = "manual"
    time_window_days = "1,2,3,4,5"
    time_window_start = "09:00"
    time_window_end = "18:00"
    rate_limit_per_hour = 12
    rate_limit_min_interval = 240
    rate_limit_max_interval = 720
    rate_limit_batch_size = 10
    rate_limit_batch_pause_min = 900
    rate_limit_batch_pause_max = 1800
```

Mover `_StubFactory` de `tests/conftest.py:65` para `tests/factories/session.py`:

```python
class StubSessionFactory:
    """Stub minimo de SessionFactory: callable retorna sessão fixa, .remove() no-op."""

    def __init__(self, session) -> None:  # noqa: ANN001
        self._session = session

    def __call__(self):  # noqa: ANN204
        return self._session

    def remove(self) -> None:
        return None
```

E em `conftest.py`:

```python
from tests.factories.session import StubSessionFactory

@pytest.fixture
def seeded_session(db_session, monkeypatch):
    monkeypatch.setattr("zap_typist.db.seed.SessionFactory", StubSessionFactory(db_session))
    from zap_typist.db.seed import run_seed
    run_seed(force=True)
    yield db_session
```

### Fix TEST-05: cobrir `retry_on_locked`

Criar `tests/unit/test_retry_on_locked.py`:

```python
"""Cobertura de retry_on_locked — backoff e retry budget."""
from __future__ import annotations
import time
import pytest
from sqlalchemy.exc import OperationalError
from zap_typist.db.session import retry_on_locked


def _locked_error() -> OperationalError:
    return OperationalError("stmt", {}, Exception("database is locked"))


def test_retry_succeeds_on_second_attempt(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] == 1:
            raise _locked_error()
        return "ok"

    assert retry_on_locked(fn) == "ok"
    assert calls["n"] == 2


def test_retry_exhausts_budget(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    def fn():
        raise _locked_error()
    with pytest.raises(OperationalError):
        retry_on_locked(fn, retries=3)


def test_retry_propagates_non_lock_errors():
    def fn():
        raise OperationalError("stmt", {}, Exception("syntax error"))
    with pytest.raises(OperationalError, match="syntax error"):
        retry_on_locked(fn)
```

### Fix TEST-06: cobrir triggers updated_at

Adicionar em `tests/integration/test_triggers_updated_at.py`:

```python
"""Triggers SQL devem atualizar updated_at automaticamente em UPDATE."""
from __future__ import annotations
import time
from sqlalchemy.orm import sessionmaker
from zap_typist.db.models import Lead, LeadStatus


def test_lead_updated_at_advances_on_update(file_engine):
    Session = sessionmaker(file_engine)
    with Session() as s:
        lead = Lead(nome="X", origem="getNinjas", status=LeadStatus.pendente.value)
        s.add(lead)
        s.commit()
        s.refresh(lead)
        original = lead.updated_at

    time.sleep(1.1)  # SQLite CURRENT_TIMESTAMP tem granularidade 1s

    with Session() as s:
        target = s.get(Lead, lead.id)
        target.status = LeadStatus.query_gerada.value
        s.commit()
        s.refresh(target)
        assert target.updated_at > original
```

### Fix TEST-07: pytest-randomly

Adicionar `pytest-randomly>=3.15` em deps de dev.

### Fix TEST-08: validar pytest-qt

Levantar uso real:
```bash
grep -rn "qtbot\|qt_app\|pytestqt" tests/
```

Se zero matches, decisão: (a) escrever 1 smoke test com `qtbot` para `_build_main_window`, ou (b) remover `pytest-qt` do requirements e re-adicionar quando module-3 (Aba 1 UI) entrar.

---

## FASE 3 — Validação

```bash
pytest -m unit --cov-fail-under=70
pytest -m integration --cov-fail-under=60  # integration tem menos cov esperada
pytest --collect-only  # confirma todos os markers reconhecidos
```

**Aceite:** `pytest --cov` ≥70% global, `tests/integration/` rodando, factories em uso, retry_on_locked coberto.

---

## Resumo

- **Issues:** 8 (P1: 3 · P2: 3 · P3: 2)
- **Fixes propostos:** 8
- **Esforço:** 3-4h (criação de integration tests é o mais demorado)
- **Depende de:** Fix C-04 (cov config)
