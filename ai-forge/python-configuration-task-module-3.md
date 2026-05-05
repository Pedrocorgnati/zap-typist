# Python Configuration — module-3-aba1-queries (check mode)

**Status:** OK
**Mode:** check (read-only)
**Scope:** módulo `module-3-aba1-queries` (Aba 1 — Gerar Queries)

## Achados
- `pyproject.toml:1-150` — Build system, project metadata, deps e tooling configurados; classifiers Qt declarados.
- Ruff lint+format configurados (`select` inclui ANN, B, S, RUF, SIM, T20, UP). Per-file ignores apropriados em `tests/**` e `__main__.py`.
- Mypy: estrito apenas em `zap_typist.db.*` e `zap_typist.utils.*`. Override `PySide6.*` com `ignore_missing_imports=True`.
- Pytest: `testpaths`, `pythonpath`, `cov-fail-under=80` (DoD do módulo exige 85 — divergência intencional? ver §Testing).
- Coverage `omit` exclui `src/zap_typist/__main__.py` e `src/zap_typist/ui/**` — UI fica fora da cobertura por escolha consciente.
- BaseSettings (`pydantic-settings`) usado em `config/settings.py` (lido por todos os módulos via `domain/settings_schema.py`). Module-3 lê `default_aba1_origin` em runtime via SQLAlchemy `Setting` table — não via env var.

## Issues
- **WARN** `pyproject.toml:[tool.deptry] DEP002` lista `python-dotenv` mas falta `hypothesis` (dev dep declarada e não usada). Adicionar `hypothesis` à lista de ignore ou remover do `dev` extras.
- **INFO** `pyproject.toml: cov-fail-under=80` global vs `module-3 DoD: 85` — gap documental; o gate global do projeto é mais permissivo que o gate do módulo.

## Veredicto
Configuração saudável, sem bloqueadores. Apenas 1 ajuste de housekeeping no `deptry`.
