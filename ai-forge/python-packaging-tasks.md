# Python Packaging Tasks — zap-typist

**Data:** 2026-05-03

## Pontos fortes confirmados

- `pyproject.toml` completo: name, version, description, readme, license, requires-python, authors, classifiers
- `py.typed` marker incluído via `[tool.setuptools.package-data]`
- entry_point definido: `zap-typist = "zap_typist.app:main"`
- `Private :: Do Not Upload` classifier previne upload acidental ao PyPI
- `project.urls` com `Repository` e `Issues`

## PKG-001 — MÉDIO — Sem workflow de release automatizado

- **Arquivo:** raiz do projeto
- **Problema:** sem `gh release create`, sem `python -m build` no CI, sem checklist de release
- **Correção:** criar `.github/workflows/release.yml` com `python -m build && twine check dist/*` + upload do wheel ao GitHub Release; ver CICD-001
- **Prioridade:** Médio

## PKG-002 — BAIXO — `project.urls` sem `homepage` e `documentation`

- **Arquivo:** `pyproject.toml:[project.urls]`
- **Problema:** apenas `Repository` e `Issues` declarados; PyPI/pip show mostrará informação incompleta
- **Correção:** quando houver documentação ou landing page, adicionar `Documentation = "..."` e `Homepage = "..."`
- **Prioridade:** Baixo

## PKG-003 — BAIXO — Sem `MANIFEST.in` para arquivos não-Python

- **Arquivo:** raiz do projeto
- **Problema:** setuptools pode não incluir `py.typed`, `README.md`, `.env.example` no sdist
- **Correção:** verificar com `python -m build && tar -tzf dist/*.tar.gz` se todos os arquivos necessários estão; adicionar `MANIFEST.in` ou `[tool.setuptools.package-data]` entries conforme necessário
- **Prioridade:** Baixo
