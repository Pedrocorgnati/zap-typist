# Python Scalability — module-3-aba1-queries (check mode)

**Status:** OK (escala alvo: app local desktop pessoal)

## Paginação
- `LeadCardList`: paginação automática quando `total_count > 100` (`PAGINATION_THRESHOLD`). `page_size=50`. Botões prev/next + label "Página X de Y". ✓
- `query_generator.generate_queries` processa leads pendentes em lote único (sem paginação) — ok porque a geração é write-once e o usuário controla o tamanho do lote.

## Connection pooling / scoped session
- Pattern canônico: `session = self._session_factory(); try: ...; finally: self._session_factory.remove()`.
- Verificado em **7 call sites** (`tab1_gerar_queries.py:155, 258, 323, 330, 375` + `lead_form.py:170` + worker via `BaseWorker.execute` finally).
- Worker usa `BaseWorker.get_session()` que cacheia `self._session = self._session_factory()` — `BaseWorker.execute` finally faz `self._session_factory.remove()`. ✓
- Nenhum `session.close()` solto — sempre via `scoped_session.remove()`. ✓

## Bulk operations
- `query_generator` faz `session.query(Lead).filter(Lead.id.in_(ids)).update(...)` em vez de N updates. ✓

## Jobs assíncronos
- N/A. Aplicação desktop, sem fila externa (Celery/RQ). Worker QThread atende ao caso de uso.

## Issues
- **INFO** `_refresh_progress` faz 4 counts sequenciais (ver Performance). Em escala maior poderia ser 1 query agregada.
- **INFO** Sem retry/backoff para falha de DB (`SQLAlchemyError`) — política é mostrar erro ao usuário e deixar retry manual. Adequado para SQLite local single-writer.
- **INFO** Sem write-lock cooperativo entre Aba1/Aba2 — para SQLite local monoinstância a single-instance guard (`utils.single_instance`) já evita concorrência multi-process. Consistente com escopo.

## Veredicto
Padrões adequados ao escopo (single-user desktop). Cleanups de session corretos em 100% dos paths.
