# Python Performance — module-3-aba1-queries (check mode)

**Status:** OK

## Análise por hot path
### `query_generator.generate_queries`
- Single SELECT (`order_by(Lead.id.asc())`) — sem N+1.
- Bulk UPDATE: `session.query(Lead).filter(Lead.id.in_(ids)).update({...}, synchronize_session=False)` — 1 query para N leads. ✓
- I/O: 1 `write_text` único (não streamed). 100 leads ≈ ~30KB — não é problema.
- DoD: 100 leads < 2s — provável folga ampla (`test_aba1_terminal_perf.py` cobre métrica adjacente).

### `LeadCardList._load_page`
- 1 SELECT count + 1 SELECT page (limit/offset). Threshold 100 leads para paginar.
- Renderiza N cards num loop (for lead in leads). Cada card monta layout — Qt pode degradar > 200 widgets concorrentes; threshold de 100 + paginação 50 mantém budget.

### `_refresh_progress`
- 4 `count()` queries sequenciais (`telefone_preenchido`, `descartado`, `query_gerada`, `pendente`). Poderia ser 1 `GROUP BY status` retornando dict. Acionado em cada lead_added/submit/discard. Para 1000 leads em SQLite local: trivial. Não otimizar prematuramente.

## Índices
- `Lead.status` deveria ter índice (4 counts + 2 filters por status no módulo). Verificar em module-1 (`db/models.py`). Out-of-scope para module-3 mas dependência de performance.

## Comprehensions vs loops
- `_render_block` usa f-strings + list.append — claro e idiomático.
- `_build_dork_lines` retorna list direta — OK.
- `LeadCardList._clear_layout` faz `while layout.count(): layout.takeAt(0)` — necessário para Qt (reverse-iteration sobre QLayoutItems). ✓

## Issues
- **INFO** `_refresh_progress` poderia usar `func.count().filter()` group-by para reduzir 4 round-trips a 1. Otimização potencial mas não urgente.
- **INFO** `find_card_by_id` em `LeadCardList` é O(n) sobre layout items — para N=50 cards/página é trivial. Considerar dict `{lead_id: card}` apenas se a lista crescer. Não bloqueador.

## Veredicto
Performance adequada para escala alvo. Sem N+1, sem bloqueios óbvios. Sugestão pequena de batch counts.
