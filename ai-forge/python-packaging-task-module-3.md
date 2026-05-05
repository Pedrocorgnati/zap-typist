# Python Packaging — module-3-aba1-queries (check mode)

**Status:** OK

## `pyproject.toml`
- `[project]`: name, version (`0.1.0`), description, readme, license (Proprietary — coerente com `Private :: Do Not Upload`), authors, classifiers Qt/desktop, `requires-python = ">=3.11"`. ✓
- `[project.urls]`: Repository + Issues. ✓
- `[project.scripts]`: `zap-typist = "zap_typist.app:main"` — entry-point CLI ✓.
- `[project.optional-dependencies] dev`: pytest, pytest-cov, pytest-qt, ruff, mypy, factory-boy, deptry, hypothesis. ✓
- `[tool.setuptools.packages.find] where=["src"]` — layout src adequado.
- `[tool.setuptools.package-data] zap_typist = ["py.typed"]` — declara que o pacote é tipado (PEP 561). ✓
- Build backend: `setuptools>=61` + `wheel`.

## Versionamento
- Versão declarada estaticamente (`0.1.0`). Sem auto-versioning via VCS — coerente com app desktop pessoal.
- Release via `release.yml` com tag `v*.*.*` — usuário gerencia manualmente.

## NOTICE.md / README.md / INSTALL.md
- `NOTICE.md`, `README.md`, `INSTALL.md`, `CONTRIBUTING.md` presentes em workspace_root. ✓

## Issues
- **INFO** Nenhum.
- **INFO** Module-3 não introduz novos entry-points ou módulos top-level — apenas adiciona arquivos dentro de pacotes existentes (`zap_typist.ui.aba1`, `zap_typist.imbound`, `zap_typist.engine`). `setuptools.packages.find` os descobre automaticamente. ✓

## Veredicto
Empacotamento sólido e completo. Sem ações para module-3.
