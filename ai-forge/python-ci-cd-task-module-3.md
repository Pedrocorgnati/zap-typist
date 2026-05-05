# Python CI/CD — module-3-aba1-queries (check mode)

**Status:** OK

## Pipeline `.github/workflows/ci.yml`
Jobs:
1. `lint-and-type` (matrix py3.11 + 3.12): `ruff check`, `ruff format --check`, `mypy src`.
2. `deps-unused`: `deptry src tests`.
3. `test` (matrix py3.11 + 3.12, depends on lint-and-type): `pytest -v --cov-report=xml` com `QT_QPA_PLATFORM=offscreen`. Upload de `coverage.xml` como artifact.
4. `security-sca`: `pip-audit -r requirements.txt --desc`.
5. `secrets-scan`: TruffleHog `--only-verified` em `pull_request`/`push`.

## Pontos fortes
- Action SHAs pinados (mitiga supply-chain CVE em actions). ✓
- `concurrency.cancel-in-progress: true` evita workflow sobreposto.
- `permissions: contents: read` no workflow (least privilege). ✓
- Matrix py3.11/3.12 cobre versões declaradas em `pyproject.toml` (`requires-python = ">=3.11"`).
- `QT_QPA_PLATFORM=offscreen` permite rodar pytest-qt sem display.

## `release.yml`
- Trigger por tag `v*.*.*`, build via `python -m build` + `twine`. Coerente com versionamento semver.

## Issues
- **WARN** Job `test` falharia hoje em CI:
  - 1 teste vermelho em `test_query_generator_worker.py::test_worker_isolates_exceptions`.
  - Cov global 49% × `cov-fail-under=80`. Pipeline atual de CI passa hoje? Confirmar — se passa, o gate `--cov-fail-under` provavelmente foi reduzido ou o job apenas roda os testes não-UI. (Atual `pyproject.toml addopts` inclui `--cov-fail-under=80` — reproduzir falha em CI.)
- **INFO** `security-sca` audita `requirements.txt` em vez do venv real — bom para evitar ruído mas pode pular vulns em deps transitivas adicionadas via `[dev]` extras. Aceitável.
- **INFO** Não há job de **mutation testing** — fora do baseline mas está no inventário de skills disponível (`/mutation-test-create`).
- **INFO** Não há **deploy automation** — esperado para app desktop pessoal (release manual via tag).

## Veredicto
CI bem estruturado. Quebras atuais em `test` (1 fail + cov 49%) precisam ser endereçadas para sign-off limpo de module-3.
