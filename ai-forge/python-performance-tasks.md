# Python Performance Tasks — zap-typist

**Data:** 2026-05-03
**Status:** SEM issues críticas ou altas

## Pontos fortes confirmados

- SQLite WAL mode + `synchronous=NORMAL` configurado (bom para throughput de reads)
- Nenhum N+1 identificado (scoped_session por thread)
- Nenhum `list(...)` desnecessário em hot paths visíveis
- `RotatingFileHandler(maxBytes=10MB, backupCount=5)` bem dimensionado
- Indexes declarados nos campos de lookup frequente (`status`, `numero_e164`, `status+created_at`)

## PERF-001 — BAIXO — Sem profiling / benchmarking instrumentado

- **Arquivo:** ausente
- **Problema:** sem decorators de `perf_counter` ou fixtures de benchmark; hot paths futuros (engine de dispatch, geração de queries) não têm baseline de latência
- **Correção:** criar `tests/unit/shared/test_benchmarks_*.py` (já existem placeholders) com `pytest-benchmark` ou `timeit`; medir antes de otimizar
- **Prioridade:** Baixo
