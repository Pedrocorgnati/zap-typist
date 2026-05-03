# Python Dependencies Tasks — zap-typist

**Data:** 2026-05-03

## DEP-001 — ALTO — Sem lockfile versionado (poetry.lock ou requirements.txt gerado)

- **Arquivo:** raiz do projeto (nenhum `poetry.lock`, nenhum `requirements.txt` gerado por pip-compile)
- **Problema:** `requirements.txt` é mantido manualmente; pode divergir de `pyproject.toml`; builds não são reprodutíveis exatamente
- **Impacto:** CI instala versões diferentes em runs distintos; vulnerabilidade introduzida em upgrade silencioso
- **Correção:** adotar `pip-compile pyproject.toml --output-file requirements.lock` + `pip-sync` OU migrar para Poetry/uv com lockfile; commitar o lockfile; atualizar CI para usar `pip install -r requirements.lock`
- **Prioridade:** Alto

## DEP-002 — BAIXO — pip-audit audita `requirements.txt` manual (pode divergir de pyproject.toml)

- **Arquivo:** `.github/workflows/ci.yml` — job `security-sca`
- **Problema:** `pip-audit -r requirements.txt` audita o arquivo manual em vez do estado real instalado
- **Correção:** após DEP-001, mudar para `pip-audit` sem `-r` (audita env instalado) ou usar `-r requirements.lock`
- **Prioridade:** Baixo

## DEP-003 — BAIXO — `hypothesis>=6.0` sem upper bound

- **Arquivo:** `pyproject.toml:[project.optional-dependencies.dev]`
- **Problema:** sem limite superior para hypothesis; major bump pode quebrar testes sem aviso
- **Correção:** adicionar `hypothesis>=6.0,<7` (ou `<8` conforme política do projeto)
- **Prioridade:** Baixo
