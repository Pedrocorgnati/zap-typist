# Python Architecture — Plan (module-1-setup)

**Modo:** `--plan`
**Stack:** src-layout, package `zap_typist`, sub-pacotes `db/`, `engine/`, `imbound/`, `ui/`, `utils/`
**Comando equivalente:** `/python:architecture plan .claude/projects/zap-typist.json`

---

## FASE 1 — Auditoria

### Estado atual

```
src/zap_typist/
├── __init__.py            (vazio)
├── __main__.py            (6 LOC — bootstrap)
├── app.py                 (282 LOC — boot + Qt UI factory + excepthook)
├── db/
│   ├── __init__.py        (52 LOC — re-exports API pública)
│   ├── models.py          (237 LOC — modelos + paths XDG + constantes operacionais)
│   ├── session.py         (119 LOC — engine, sessionmaker, retry_on_locked, init_db, validate_schema)
│   └── seed.py            (124 LOC — first-run seed das settings)
├── engine/
│   └── __init__.py        (vazio — placeholder p/ rock 3)
├── imbound/
│   ├── __init__.py        (vazio)
│   └── constants/
│       ├── __init__.py    (vazio)
│       ├── desire_rules.py
│       ├── feminine_names.py
│       └── message_templates.py
├── ui/
│   ├── __init__.py        (vazio)
│   └── widgets/__init__.py (vazio — placeholder)
└── utils/
    ├── __init__.py        (vazio)
    ├── cache.py           (67 LOC)
    ├── logger.py          (101 LOC — JsonFormatter + PIIFilter)
    └── single_instance.py (49 LOC)
```

**Total:** 19 arquivos `.py`, 1406 LOC.

### Grafo de dependências (resumido)

```
__main__.py ──> app.py
app.py ──> utils.logger ──> db.models (constantes LOG_DIR)
app.py ──> [lazy] PySide6 + utils.single_instance + db.session + db.seed + utils.cache
utils.single_instance ──> db.models (LOCK_FILE)
utils.cache ──> db.models (CACHE_DIR)
utils.logger ──> db.models (LOG_DIR)
db.__init__ ──> db.models + db.session
db.session ──> db.models (Base, APP_DATA_DIR, DB_PATH)
db.seed ──> db.session + db.models (Setting, CONTACT_HISTORY_WINDOW_DAYS) + imbound.constants.*
imbound.constants.* (sem dependências internas)
```

**Ciclos:** nenhum.

### Observações estruturais

1. **`db/models.py` carrega responsabilidades de 3 camadas:**
   - Modelos ORM SQLAlchemy (Lead, Flow, Setting, ContactHistory) — OK, é o domínio.
   - **Paths XDG** (APP_DATA_DIR, CACHE_DIR, DB_PATH, LOCK_FILE, LOG_DIR) — não é "model".
   - **Constantes operacionais** (RATE_LIMIT_MAX_POR_HORA, CONTACT_HISTORY_WINDOW_DAYS, ORIGEM_PADRAO_ABA1) — não é "model".

   `utils/logger.py:8`, `utils/cache.py:12`, `utils/single_instance.py:6` importam `db.models` apenas por causa das constantes. Acoplamento invertido: `utils/` (low-level) depende de `db/` (higher-level).

2. **`db/seed.py` importa diretamente `imbound.constants.*`:** acoplamento outbound de `db/` em direção a uma camada de domínio (`imbound/`). Inverter: `db.seed` deve receber defaults via injeção, não importar.

3. **`app.py:71-117` define `MainWindow` inline dentro de `_build_main_window`:** a classe vive em closure. Funciona para lazy import, mas dificulta teste e manutenção. Padrão melhor: `ui/main_window.py` com `MainWindow` declarado normalmente + import lazy só dentro de `_boot_qt`.

4. **Camadas implícitas presentes:** infra (`db/session.py`), domínio (`db/models.py`), aplicação (`app.py`), utilitários (`utils/`). Falta camada explícita de `services/` ou `repositories/` — aceitável para foundations, mas registrar para próximos modules.

### Gaps identificados

| # | Sev | Categoria | Achado | Evidência |
|---|-----|-----------|--------|-----------|
| A-01 | P0 | placeholders | `engine/__init__.py` e `ui/widgets/__init__.py` vazios. **Esperado para foundations** (rocks 3 e 1 vão popular). Validar que MODULE-META.json declara essa expectativa. | `src/zap_typist/engine/`, `src/zap_typist/ui/widgets/` |
| A-02 | P1 | layering invertido | `utils/{logger,cache,single_instance}` importam constantes de path de `db.models`. `utils/` deveria ser folha. Mover paths para `config/paths.py`. | `utils/logger.py:8`, `utils/cache.py:12`, `utils/single_instance.py:6` |
| A-03 | P1 | god module | `db/models.py` mistura ORM + paths XDG + constantes operacionais (3 responsabilidades). | `src/zap_typist/db/models.py:37-59` |
| A-04 | P1 | acoplamento direto | `db/seed.py` importa `imbound.constants.*` direto — `db/` (camada de infra) puxa `imbound/` (camada de domínio). Inversão. | `src/zap_typist/db/seed.py:23-31` |
| A-05 | P2 | inline class | `MainWindow` declarado dentro de `_build_main_window` closure (282 LOC em `app.py` por isso). | `src/zap_typist/app.py:71-117` |
| A-06 | P2 | excepthook | `handle_exception` definido inline em `_setup_excepthook`. Extrair para `utils/exceptions.py` para teste isolado. | `src/zap_typist/app.py:18-37` |
| A-07 | P3 | services layer | Sem camada `services/` ou `domain/` explícita. Aceitável agora (foundations); registrar dívida para module-3+. | (estrutura geral) |

---

## FASE 2 — Correções propostas (NÃO APLICADAS)

### Fix A-01: confirmar placeholders são esperados

Inspecionar `output/wbs/zap-typist/modules/module-1-setup/MODULE-META.json` e `_INVENTORY.md`. Se ambos vazios constam como "expected for module-1, populated by module-3/6", manter. Caso contrário, registrar gap em PENDING-ACTIONS.

### Fix A-02: criar `config/paths.py` (folha)

```python
# src/zap_typist/config/__init__.py
from zap_typist.config.paths import (
    APP_DATA_DIR, CACHE_DIR, CHROME_PROFILES_DIR,
    DB_PATH, LOCK_FILE, LOG_DIR,
)

__all__ = ["APP_DATA_DIR", "CACHE_DIR", "CHROME_PROFILES_DIR",
           "DB_PATH", "LOCK_FILE", "LOG_DIR"]
```

```python
# src/zap_typist/config/paths.py
from __future__ import annotations
import os
from pathlib import Path

_DATA_DIR_OVERRIDE = os.environ.get("ZAP_TYPIST_DATA_DIR")
APP_DATA_DIR: Path = (
    Path(_DATA_DIR_OVERRIDE).expanduser().resolve()
    if _DATA_DIR_OVERRIDE
    else Path.home() / ".local" / "share" / "zap-typist"
)
CACHE_DIR: Path = APP_DATA_DIR / "cache"
DB_PATH: Path = APP_DATA_DIR / "zap_typist.db"
CHROME_PROFILES_DIR: Path = APP_DATA_DIR / "chrome-profiles"
LOCK_FILE: Path = APP_DATA_DIR / ".lock"
LOG_DIR: Path = APP_DATA_DIR / "logs"
```

Refatorar:
- `db/models.py:38-51` → remover paths, importar `from zap_typist.config.paths import APP_DATA_DIR, DB_PATH`
- `utils/logger.py:8` → `from zap_typist.config.paths import LOG_DIR`
- `utils/cache.py:12` → `from zap_typist.config.paths import CACHE_DIR`
- `utils/single_instance.py:6` → `from zap_typist.config.paths import LOCK_FILE`

`db/__init__.py` continua re-exportando paths (compat) com `# deprecated: import from zap_typist.config.paths`.

### Fix A-03: extrair constantes operacionais

Criar `src/zap_typist/domain/constants.py`:

```python
"""Constantes operacionais do domínio Zap Typist."""

RATE_LIMIT_MAX_POR_HORA: int = 30
CONTACT_HISTORY_WINDOW_DAYS: int = 60
ORIGEM_PADRAO_ABA1: str = "getNinjas"
```

`db/models.py:54-59` → remover, importar de `zap_typist.domain.constants`.
`db/seed.py:17` → idem.

### Fix A-04: inverter dependência seed → imbound

Refatorar `db/seed.py` aceitando defaults injetados:

```python
def run_seed(*, defaults: dict[str, str], force: bool = False) -> int:
    """Popula `settings` com `defaults` recebidos por injeção."""
    ...
```

E criar `src/zap_typist/seeders/__init__.py`:

```python
"""Seeders: agregação de defaults vindos de imbound + domain."""
from __future__ import annotations
import json
from zap_typist.domain.constants import CONTACT_HISTORY_WINDOW_DAYS
from zap_typist.imbound.constants.desire_rules import DESIRE_RULES_SEED
from zap_typist.imbound.constants.feminine_names import FEMININE_NAMES_SEED
from zap_typist.imbound.constants.message_templates import (
    MSG_TEMPLATE_1, MSG_TEMPLATE_2, MSG_TEMPLATE_3, MSG_TEMPLATE_4, MSG_TEMPLATE_5,
)


def build_settings_defaults() -> dict[str, str]:
    return {
        "msg_template_1": MSG_TEMPLATE_1,
        ...
        "feminine_names": json.dumps(FEMININE_NAMES_SEED, ensure_ascii=False),
        "desire_rules": json.dumps(DESIRE_RULES_SEED, ensure_ascii=False),
        "contact_history_window_days": str(CONTACT_HISTORY_WINDOW_DAYS),
        ...
    }
```

E em `app.py:_boot_db`:

```python
from zap_typist.seeders import build_settings_defaults
from zap_typist.db.seed import run_seed

run_seed(defaults=build_settings_defaults(), force=False)
```

### Fix A-05: extrair MainWindow para `ui/main_window.py`

```python
# src/zap_typist/ui/main_window.py
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)
from zap_typist.utils.logger import get_logger

logger = get_logger("zap_typist.ui.main_window")


class MainWindow(QMainWindow):
    TAB_LABELS = (
        ("Gerar Queries", "Em desenvolvimento — aguardando rock 1 (aba1-queries)"),
        ...
    )

    def __init__(self) -> None:
        ...
```

`app.py` fica:

```python
def _boot_qt(start_ts: float) -> int:
    from PySide6.QtWidgets import QApplication
    from zap_typist.ui.main_window import MainWindow

    qt_app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    ...
```

`_build_main_window()` é deletada.

### Fix A-06: extrair excepthook

```python
# src/zap_typist/utils/exceptions.py
from __future__ import annotations
import sys
from types import TracebackType
from zap_typist.utils.logger import get_logger

logger = get_logger("zap_typist.exceptions")


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("unhandled_exception", exc_info=(exc_type, exc_value, exc_tb))
    try:
        from PySide6.QtWidgets import QApplication
        from zap_typist.ui.dialogs import show_blocking_modal

        if QApplication.instance() is not None:
            show_blocking_modal("Erro inesperado", ..., level="critical")
    except Exception:  # noqa: BLE001
        pass


def setup_excepthook() -> None:
    sys.excepthook = handle_exception
```

Em `app.py`:
```python
from zap_typist.utils.exceptions import setup_excepthook
...
def main() -> int:
    setup_excepthook()
    ...
```

`_show_blocking_modal` também migra para `ui/dialogs.py`.

### Fix A-07: registrar dívida (sem ação imediata)

Adicionar nota em `MODULES-PROGRESS.md` ou ADR:
> Module-3+ deve introduzir camada `services/` (UseCases) e `repositories/` (queries SQLAlchemy isoladas) para evitar acoplamento direto Qt ↔ db.session em ações de UI.

---

## FASE 3 — Validação

```bash
# Sem ciclos
python -m pip install pydeps
pydeps src/zap_typist --max-bacon 4 --noshow

# Sem imports cruzados utils → db
ruff check src --select TID  # tidy-imports
mypy src

# Boot smoke
python -m zap_typist  # exit 0 esperado
pytest tests/unit/ -m boot
```

**Aceite:** `utils/` não importa `db.*`; `db/seed.py` não importa `imbound.*`; `MainWindow` em arquivo próprio; `handle_exception` testável fora de `app.py`.

---

## Resumo

- **Issues:** 7 (P0: 1 [validação] · P1: 3 · P2: 2 · P3: 1)
- **Fixes propostos:** 7
- **Esforço:** 3-4h (refactor estrutural com risco médio — coberto por testes existentes)
- **Bloqueador:** Fix A-04 muda assinatura de `run_seed` (breaking) — coordenar com module-3/4 antes de aplicar
