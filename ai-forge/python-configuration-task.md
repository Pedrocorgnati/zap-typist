# Python Configuration — Plan (module-1-setup)

**Modo:** `--plan` (sem mutação)
**Escopo:** module-1-setup (foundations-lean Python)
**Stack:** Python 3.11, src-layout, ruff, mypy, pytest, SQLAlchemy 2, PySide6, pydantic-settings (declarado, não usado)
**Comando equivalente:** `/python:configuration plan .claude/projects/zap-typist.json`

---

## FASE 1 — Auditoria

### Estado atual (`pyproject.toml`)

```toml
[project]
name = "zap-typist"
version = "0.1.0"
requires-python = ">=3.11"
# SEM [project.dependencies], [project.optional-dependencies]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]
[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
mypy_path = "src"
strict = false
warn_unused_ignores = true
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

`requirements.txt` mistura runtime + dev em pin mínimo (`>=`).

`Makefile` expõe `setup`, `dev`, `test`, `lint`, `type-check`, `clean`. Nenhum target `cov`/`audit`/`format`.

ENV vars consumidas direto via `os.environ.get(...)`:
- `ZAP_TYPIST_DATA_DIR` em `db/models.py:41`
- `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY` em `app.py:43-46`
- `DEBUG` em `utils/logger.py:95`

`pydantic-settings>=2.0` consta no `requirements.txt` mas **nenhum import** em `src/`.

### Gaps identificados

| # | Sev | Categoria | Achado | Evidência |
|---|-----|-----------|--------|-----------|
| C-01 | P1 | PEP 621 | Dependências fora do `pyproject.toml` (vivem em `requirements.txt` mistas runtime+dev). | `pyproject.toml` (sem `[project.dependencies]`) |
| C-02 | P1 | mypy | `strict = false` + `disallow_untyped_defs = false` permitem código untyped passar. Há 4+ `# noqa: ANN001`. | `pyproject.toml:17`, `app.py:20,71`, `db/session.py:44` |
| C-03 | P2 | ruff | Ruleset enxuto (E, F, W, I, B, UP). Falta: `S` (flake8-bandit), `RUF`, `ANN`, `SIM`, `PL` (Pylint subset), `T20` (no print). | `pyproject.toml [tool.ruff.lint]` |
| C-04 | P2 | coverage | Sem `pytest-cov` configurado, sem gate de cobertura. | `pyproject.toml`, `Makefile` |
| C-05 | P2 | pre-commit | Sem `.pre-commit-config.yaml`. Lint/type/test rodam só manual via Makefile. | (ausência) |
| C-06 | P3 | ENV schema | `pydantic-settings` declarado mas não usado. ENV vars lidas direto em 3 módulos sem schema central. | `requirements.txt`, `db/models.py:41`, `app.py:43`, `utils/logger.py:95` |
| C-07 | P3 | ruff format | Sem `[tool.ruff.format]` explícito (usa defaults — OK funcional, mas precisa ser declarado). | `pyproject.toml` |

---

## FASE 2 — Correções propostas (NÃO APLICADAS — modo plan)

### Fix C-01: migrar deps para PEP 621

```toml
# pyproject.toml
[project]
name = "zap-typist"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "PySide6>=6.6,<7",
  "SQLAlchemy>=2.0,<3",
  "pydantic-settings>=2.0,<3",
  "python-dotenv>=1.0,<2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "pytest-qt>=4.4",
  "ruff>=0.4",
  "mypy>=1.10",
  "pip-audit>=2.7",
  "deptry>=0.16",
]
```

`requirements.txt` passa a ter apenas `-e .[dev]` ou ser deletado em favor de `pip install -e .[dev]`.

### Fix C-02: mypy gradual strict por subpacote

```toml
[tool.mypy]
python_version = "3.11"
mypy_path = "src"
strict = false
warn_unused_ignores = true
disallow_untyped_defs = false  # mantido global (relaxado)

# Strict por módulo onde o código já está limpo
[[tool.mypy.overrides]]
module = ["zap_typist.db.*", "zap_typist.utils.*"]
disallow_untyped_defs = true
disallow_any_generics = true
warn_return_any = true

# PySide6 sem stubs oficiais publicados
[[tool.mypy.overrides]]
module = ["PySide6.*"]
ignore_missing_imports = true
```

### Fix C-03: expandir ruleset ruff

```toml
[tool.ruff.lint]
select = [
  "E", "F", "W", "I", "B", "UP",
  "S",      # flake8-bandit (security-lite)
  "RUF",    # ruff-specific
  "SIM",    # flake8-simplify
  "PL",     # Pylint subset
  "T20",    # no print()
  "ANN",    # type annotations (relaxado por categoria abaixo)
]
ignore = [
  "ANN101", # missing-type-self (deprecated)
  "ANN102", # missing-type-cls
  "PLR0913", # too-many-arguments
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN", "S101", "PLR2004"]  # asserts e magic numbers OK em testes

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Fix C-04: pytest-cov + gate

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
  "--cov=zap_typist",
  "--cov-report=term-missing",
  "--cov-report=xml",
  "--cov-fail-under=70",  # foundations: 70%; alvo de evolução para 80%+
]

[tool.coverage.run]
source = ["src/zap_typist"]
branch = true
omit = ["src/zap_typist/__main__.py", "src/zap_typist/ui/**"]

[tool.coverage.report]
exclude_lines = [
  "pragma: no cover",
  "raise NotImplementedError",
  "if TYPE_CHECKING:",
]
```

### Fix C-05: pre-commit

Criar `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: ["sqlalchemy>=2.0", "pydantic-settings>=2.0"]
        files: ^src/
```

Adicionar target `make hooks: pre-commit install`.

### Fix C-06: schema central de ENV via pydantic-settings

Criar `src/zap_typist/config/__init__.py` + `src/zap_typist/config/settings.py`:

```python
from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração resolvida de ENV vars + defaults XDG."""

    model_config = SettingsConfigDict(
        env_prefix="ZAP_TYPIST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path | None = None  # ZAP_TYPIST_DATA_DIR
    debug: bool = False           # ZAP_TYPIST_DEBUG (renomeia DEBUG legacy)
    log_level: str = "INFO"


settings = Settings()
```

Refatorar `db/models.py:41`, `utils/logger.py:95` e `app.py:43-46` para consumir `settings`.
**Atenção:** `XDG_SESSION_TYPE`/`WAYLAND_DISPLAY` são variáveis do desktop (não do app) — manter `os.environ.get` direto, isolado em `utils/desktop.py`.

### Fix C-07: explicitar ruff format

Já incluído em Fix C-03 (`[tool.ruff.format]` block).

---

## FASE 3 — Validação (após aplicar fixes)

```bash
ruff check src tests
ruff format --check src tests
mypy src
pytest --cov-fail-under=70
pip-audit
deptry .
pre-commit run --all-files
```

**Aceite:** todas as 7 verificações PASS, sem warnings de coverage.

---

## Resumo

- **Issues:** 7 (P1: 2 · P2: 3 · P3: 2)
- **Fixes propostos:** 7 (não aplicados — modo plan)
- **Esforço estimado:** 2-3h (PEP 621 migration é o item mais demorado)
- **Bloqueia outros sub-comandos?** C-02 (mypy) e C-04 (cov) habilitam typing-task e testing-task respectivamente
