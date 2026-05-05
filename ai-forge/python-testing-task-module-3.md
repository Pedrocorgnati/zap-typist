# Python Testing — module-3-aba1-queries (check mode)

**Status:** WARN (108/109 passing, 1 failed)
**Tools:** pytest, pytest-cov, pytest-qt

## Test inventory
```
tests/unit/test_lead_form.py
tests/unit/test_lead_service.py
tests/unit/test_query_generator.py
tests/unit/test_query_generator_worker.py     ← 1 fail
tests/unit/test_aba1_lead_card.py
tests/unit/test_aba1_lead_card_list.py
tests/unit/test_aba1_pii_audit.py
tests/unit/test_aba1_terminal_perf.py
tests/unit/test_tab1_gerar_queries.py
tests/integration/test_aba1_e2e.py
```

## Resultado run
```
1 failed, 108 passed in 14.27s
FAILED tests/unit/test_query_generator_worker.py::test_worker_isolates_exceptions
```

## Cobertura (escopo module-3, branch on)
| Arquivo | Stmts | Cover |
|---------|-------|-------|
| `services/lead_service.py` | 21 | **100%** |
| `imbound/query_generator.py` | 82 | **99%** (branch 124→126) |
| `engine/query_generator_worker.py` | 15 | **100%** |
| `engine/base_worker.py` | 43 | **98%** |
| `domain/constants.py` | 5 | 100% |

UI (`ui/aba1/*`, `ui/tab1_gerar_queries.py`) é **omit** no `[tool.coverage.run]` — testes Qt rodam mas linhas não contam para o gate.

Cov global do projeto: **49%** (FAIL contra `cov-fail-under=80`). Dentro do escopo de module-3 lógico (services + imbound + engine) está acima de 95%.

## Pontos fortes
- Separação clara `unit/integration` via marcadores (`unit`, `integration`, `qt`, `boot`).
- `test_aba1_pii_audit.py` reforça US-012 (sem PII em logs) — guard regression-test.
- `test_aba1_terminal_perf.py` testa a métrica de DoD "TerminalWidget 1000 linhas < 500ms".
- `test_aba1_e2e.py` cobre os 11 passos do INTAKE (smoke runtime).

## Issues
- 🚨 **FAIL** `test_query_generator_worker.py::test_worker_isolates_exceptions` (ver §Error Handling para detalhes).
- **INFO** `cov-fail-under=80` global × `module DoD = 85` × cov real do projeto = **49%**. O gate `--cov-fail-under=80` falharia em CI hoje. Confirmar: o omit de `ui/**` é deliberado e atende ao DoD do módulo? Se sim, o gate pyproject deveria refletir somente o subset não-UI. Caso contrário, cobertura precisa subir.

## Veredicto
Estrutura de testes excelente, MAS um teste vermelho e o gate global de cobertura quebrado contra fail-under=80 (49% atual). Bloqueador para um sign-off limpo.
