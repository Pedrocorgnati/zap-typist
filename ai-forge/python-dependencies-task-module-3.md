# Python Dependencies — module-3-aba1-queries (check mode)

**Status:** WARN
**Tools:** deptry, pip-audit

## deptry
```
[tool.deptry] DEP002 'hypothesis' defined as a dependency but not used in the codebase
Found 1 dependency issue.
```
**Ação:** ou remover `hypothesis` do bloco `dev` ou adicionar ao `[tool.deptry.per_rule_ignores] DEP002`.

## pip-audit (não acionável dentro do módulo)
A run reportou vulnerabilidades em `pip` e `setuptools`, mas refere-se à instalação do **system Python** (apt). Dentro do `.venv` do projeto as versões são modernas (declaradas em `pyproject.toml >=61` para setuptools build-backend e `>=8.0` pytest). Sem ação no escopo de module-3.

## Pinagem
- `PySide6>=6.6,<7`
- `SQLAlchemy>=2.0,<3`
- `pydantic>=2.0,<3`
- `pydantic-settings>=2.0,<3`
- `python-dotenv>=1.0,<2`

Pinagem maior+menor com upper bound — adequado para app desktop com lock via `uv.lock` (presente em `output/workspace/zap-typist/uv.lock`).

## Veredicto
1 fix trivial em `pyproject.toml`. Nenhum CVE no escopo do venv.
