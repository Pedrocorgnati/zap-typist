# Python Complete Review Report — module-3-aba1-queries

**Projeto:** Zap Typist
**Módulo:** `module-3-aba1-queries` (Aba 1 — Gerador de Queries)
**Data:** 2026-05-04
**Versão Python:** 3.11 (matrix CI 3.11/3.12)
**Modo:** `check` (read-only)
**Config:** `.claude/projects/zap-typist.json`

---

## Resumo Executivo

| Camada | Comandos | Status | Issues | Fixes (check) |
|--------|----------|--------|--------|--------------|
| Fundação | Configuration, Typing, Dependencies | OK / OK / **WARN** | 2 | 0 (read-only) |
| Arquitetura | Architecture, Hardcodes | OK / OK | 3 INFO | 0 |
| Dados | Data Handling | OK | 1 INFO | 0 |
| Segurança | Security | OK | 0 críticas, 2 INFO | 0 |
| Qualidade | Error Handling, Testing | **WARN / WARN** | 2 críticos | 0 |
| Otimização | Performance, Async, Scalability | OK / OK / OK | 4 INFO | 0 |
| DevOps | CI/CD, Packaging | **WARN** / OK | 1 | 0 |
| Frameworks | Web Framework, API | N/A / N/A | — | — |

**Total de Issues acionáveis:** 2 bloqueadores + 1 WARN dependência + ~13 INFO/sugestões.
**Total de Fixes aplicados:** 0 (modo `check`).
**Cobertura medida (escopo módulo):** lógica core 95%+ ; global pyproject `cov-fail-under=80` quebra com **49%** real.

---

## Achados Críticos (Bloqueadores)

### 🚨 1. Test failure: `test_query_generator_worker.py::test_worker_isolates_exceptions`
- 108 passed, **1 failed** ao rodar a suíte do módulo.
- Assertion: `assert any("Erro" in m for m in msgs)` retorna `False`.
- `BaseWorker.execute()` chama `self.signals.log_line.emit(f"Erro: {type(exc).__name__}.")`, mas o teste não captura o emit.
- Hipóteses: race entre `log_line` e `finished` no `qtbot.waitSignal`, ou contrato esperado de `QueryGeneratorWorker.run` (também espera `signals.status_update.emit("Erro na geração ...")`).
- **Module-3 está em `state=done` com teste vermelho** — drift entre TASK-6 e implementação atual. Investigar antes de assinar entrega.

### 🚨 2. Cobertura global × `cov-fail-under=80`
- `pytest --cov` reporta **49.14%** total (`omit ui/**` + alguns módulos não cobertos como `domain.flow`, `domain.settings_schema`, `domain.validators`, `seeders`, `utils.cache`, `utils.single_instance`, `db.seed`, `app.py`).
- Job `test` do CI (`.github/workflows/ci.yml`) usa o mesmo gate `cov-fail-under=80` declarado em `pyproject.toml addopts`. Pipeline atual quebraria.
- DoD do módulo exige **85%** — referência 100% atingida em `services` + `imbound` + `engine`, mas a métrica global do projeto está distorcida pelo escopo de outros módulos.

### ⚠️ 3. `deptry` DEP002: `hypothesis` declarada e não usada
- Single fix: adicionar a `[tool.deptry.per_rule_ignores] DEP002` ou remover de `[project.optional-dependencies] dev`.

---

## Resultados por Comando

### 1. Configuration — OK
- `pyproject.toml` saudável, ruff/mypy/pytest bem configurados.
- Coverage `omit` exclui `src/zap_typist/ui/**` e `__main__.py` — escolha consciente.
- **Task file:** `python-configuration-task-module-3.md`

### 2. Typing — OK
- `mypy` em arquivos do módulo: 0 erros (`Success: no issues found in 7 source files`).
- `Protocol _ScopedSessionFactory` desacopla widget de `scoped_session`.
- **Task file:** `python-typing-task-module-3.md`

### 3. Dependencies — WARN
- `deptry` DEP002 hypothesis (corrigível em 1 linha).
- `pip-audit` reporta vulns em pip/setuptools do system Python — não afeta o venv. Sem ação.
- **Task file:** `python-dependencies-task-module-3.md`

### 4. Architecture — OK
- Camadas limpas: `db → domain → services / imbound → engine → ui`.
- Sem imports circulares.
- 2 INFO: encapsulamento de `_lead.id` em `find_card_by_id`; complexidade de `_on_card_submit` (early-returns + finally).
- **Task file:** `python-architecture-task-module-3.md`

### 5. Hardcodes — OK
- Constantes nomeadas (`COPIED_FEEDBACK_MS`, `SUFIXO_LEN`, `PAGINATION_THRESHOLD`, `OUTPUT_FILENAME`, `DEFAULT_ORIGIN_KEY`).
- 1 INFO: cor hex literal `#F6465D` em `lead_card.py:161` deveria usar `COLOR_FEEDBACK_ERROR` de `ui.styles`.
- **Task file:** `python-hardcodes-task-module-3.md`

### 6. Data Handling — OK
- Validação multicamadas (UI form → card → tab orchestrator).
- `dataclass(frozen=True) GenerationResult`, `today_provider` injetável, `.strip()` sistemático.
- 1 INFO: aspas internas em `lead.nome/info_extra` quebrariam o dork (low-prob, mas sem sanitização).
- **Task file:** `python-data-handling-task-module-3.md`

### 7. Security — OK
- PII audit limpo: 0 ocorrências de `nome|ddd|prefixo|sufixo|desire|info_extra|numero_e164` em parâmetros de logger.
- ORM-only (zero raw SQL).
- 1 INFO: Bandit standalone não instalado (cobertura via ruff S* parcial).
- **Task file:** `python-security-task-module-3.md`

### 8. Error Handling — **WARN**
- 🚨 `test_worker_isolates_exceptions` falha (ver Achado #1).
- Excepts específicos no fast path (`SQLAlchemyError`, `ValueError`, `OSError`).
- Logging estruturado com `extra` (sem PII).
- **Task file:** `python-error-handling-task-module-3.md`

### 9. Testing — **WARN**
- 108 pass / 1 fail.
- Cov real do escopo do módulo (services/imbound/engine): 95%+.
- Cov global do projeto: **49%** quebra `cov-fail-under=80`.
- **Task file:** `python-testing-task-module-3.md`

### 10. Performance — OK
- Sem N+1, bulk update via `IN (ids)`, paginação automática a partir de 100 leads.
- 1 INFO: 4 counts sequenciais em `_refresh_progress` poderiam ser 1 group-by.
- **Task file:** `python-performance-task-module-3.md`

### 11. Async (Qt threading) — OK
- Anti-drift: 0 matches de `QThreadPool`/`QRunnable`/`session.close()` solto.
- `moveToThread` apenas em `_on_imbound_query_clicked` sob guard `_active_thread`.
- **Task file:** `python-async-task-module-3.md`

### 12. Scalability — OK
- `scoped_session.remove()` em 7 call sites (todos os finally apropriados).
- Bulk update + paginação threshold.
- **Task file:** `python-scalability-task-module-3.md`

### 13. CI/CD — **WARN**
- Pipeline robusto: matrix py311/py312, ruff/mypy/deptry/pytest/pip-audit/TruffleHog.
- Action SHAs pinados, `permissions: contents: read`.
- ⚠️ Job `test` falharia hoje (ver Achados #1 e #2).
- **Task file:** `python-ci-cd-task-module-3.md`

### 14. Packaging — OK
- `pyproject.toml` completo, entry-point CLI, `py.typed` presente.
- **Task file:** `python-packaging-task-module-3.md`

### 15. Web Framework — N/A
- Desktop PySide6, sem framework web.
- **Task file:** `python-web-framework-task-module-3.md`

### 16. API — N/A
- Sem API HTTP/OpenAPI exposta.
- **Task file:** `python-api-task-module-3.md`

---

## Issues Críticas Pendentes

| # | Categoria | Arquivo | Descrição | Severidade |
|---|-----------|---------|-----------|------------|
| 1 | Testing | `tests/unit/test_query_generator_worker.py` | `test_worker_isolates_exceptions` falha; conflito com contrato `BaseWorker.execute` | **CRÍTICO** |
| 2 | Testing/CI | `pyproject.toml [tool.pytest.ini_options]` | `cov-fail-under=80` × cov real 49% — CI quebra | **ALTO** |
| 3 | Dependencies | `pyproject.toml [tool.deptry]` | hypothesis listada e não usada | MÉDIO |
| 4 | Hardcodes | `src/zap_typist/ui/aba1/lead_card.py:161` | cor hex literal `#F6465D` em vez de `COLOR_FEEDBACK_ERROR` | BAIXO |
| 5 | Data Handling | `src/zap_typist/imbound/query_generator.py:_render_block` | aspas internas em `lead.nome/info_extra` não escapadas | BAIXO |
| 6 | Performance | `src/zap_typist/ui/tab1_gerar_queries.py:_refresh_progress` | 4 counts sequenciais (otimização opcional) | BAIXO |

---

## Métricas de Qualidade

| Métrica | Valor | Meta | Status |
|---------|-------|------|--------|
| Type Coverage (mypy strict subset) | 100% (0 erros) | 0 erros | ✓ |
| Test Pass Rate | 108/109 (99.08%) | 100% | ✗ |
| Cov projeto (omit ui) | 49.14% | 80% pyproject / 85% DoD | ✗ |
| Cov core lógica module-3 | services 100% / imbound 99% / engine 100% | 85% | ✓ |
| Vulnerabilidades CVE no venv | 0 | 0 | ✓ |
| Hardcodes (paths/IPs/secrets) | 0 | 0 | ✓ |
| PII em logs | 0 ocorrências | 0 | ✓ |
| Anti-drift (QThreadPool/QRunnable) | 0 matches | 0 | ✓ |
| Bare except sem log | 0 | 0 | ✓ |
| Ruff lint module-3 | 0 erros | 0 | ✓ |

---

## Arquivos do Módulo (1223 LOC)

```
src/zap_typist/services/lead_service.py             54 LOC
src/zap_typist/imbound/query_generator.py          154 LOC
src/zap_typist/imbound/__init__.py                   0 LOC
src/zap_typist/engine/query_generator_worker.py     47 LOC
src/zap_typist/engine/__init__.py                    2 LOC (exports BaseWorker)
src/zap_typist/ui/aba1/__init__.py                   6 LOC
src/zap_typist/ui/aba1/lead_form.py                185 LOC
src/zap_typist/ui/aba1/lead_card.py                205 LOC
src/zap_typist/ui/aba1/lead_card_list.py           177 LOC
src/zap_typist/ui/aba1/lead_card_list_config.py     12 LOC
src/zap_typist/ui/tab1_gerar_queries.py            383 LOC
```

Modificado: `src/zap_typist/app.py` (uso de `get_aba1_widget`).

## Tests (10 arquivos)
```
tests/unit/test_lead_form.py
tests/unit/test_lead_service.py
tests/unit/test_query_generator.py
tests/unit/test_query_generator_worker.py        ← 1 fail
tests/unit/test_aba1_lead_card.py
tests/unit/test_aba1_lead_card_list.py
tests/unit/test_aba1_pii_audit.py
tests/unit/test_aba1_terminal_perf.py
tests/unit/test_tab1_gerar_queries.py
tests/integration/test_aba1_e2e.py
```

---

## Task Files Gerados

Salvos em `output/workspace/zap-typist/ai-forge/`:

- `python-configuration-task-module-3.md`
- `python-typing-task-module-3.md`
- `python-dependencies-task-module-3.md`
- `python-architecture-task-module-3.md`
- `python-hardcodes-task-module-3.md`
- `python-data-handling-task-module-3.md`
- `python-security-task-module-3.md`
- `python-error-handling-task-module-3.md`
- `python-testing-task-module-3.md`
- `python-performance-task-module-3.md`
- `python-async-task-module-3.md`
- `python-scalability-task-module-3.md`
- `python-ci-cd-task-module-3.md`
- `python-packaging-task-module-3.md`
- `python-web-framework-task-module-3.md`
- `python-api-task-module-3.md`

---

## Próximos Passos Recomendados

1. **Investigar `test_worker_isolates_exceptions`.** Determinar se é race em `qtbot.waitSignal` ou contrato faltante em `QueryGeneratorWorker.run` (emit `status_update("Erro na geração ...")`). Considere `/qa-remediate` ou `/python:error-handling --module 3` em modo write.
2. **Reconciliar gate de cobertura.** Decidir entre:
   - Reduzir `cov-fail-under` no `pyproject.toml` para refletir realidade do escopo testado (UI omit), ou
   - Aumentar cov nos módulos órfãos (`domain.flow`, `seeders`, `utils.cache`, `utils.single_instance`, `app.py`) — provavelmente escopo de futuros modules.
3. **Fix `deptry` DEP002 hypothesis** (1-linha em `pyproject.toml`).
4. **Substituir cor hex literal** em `lead_card.py:161` por `COLOR_FEEDBACK_ERROR`.
5. **Sanitizar aspas** em `query_generator._render_block` (defesa em profundidade contra nomes com `"`).

---

## Próximos comandos sugeridos (DCP loop)

- `/qa-remediate .claude/projects/zap-typist.json` — converter os 2 bloqueadores em tasks executáveis.
- `/python:error-handling .claude/projects/zap-typist.json` (modo write, escopo módulo 3) — fix #1.
- `/delivery:reopen --module 3 --reason "test_worker_isolates_exceptions failure + cov gate"` — se for confirmado que o módulo precisa rework.

---

PYTHON COMPLETE REVIEW (CHECK MODE) FINALIZADO
