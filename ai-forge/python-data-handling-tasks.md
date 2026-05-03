# Python Data Handling Tasks — zap-typist

**Data:** 2026-05-03

## DATA-001 — MÉDIO — Sem Alembic: migrações só por scripts manuais

- **Arquivo:** `src/zap_typist/db/session.py:4-8` (comentário ADR-007)
- **Problema:** só `Base.metadata.create_all(engine)` no boot; mudanças de schema requerem scripts Python manuais nomeados `MIGRATION-vX.Y.Z.py`; sem `downgrade` automatizado; risco de drift de schema entre instâncias
- **Impacto:** risco de corrupção de dados ao fazer upgrade/downgrade; usuário sem instruções claras pode perder dados
- **Correção:** avaliar adoção de Alembic em iteração pós-rock-4; por enquanto, documentar o processo de migração no INSTALL.md com checklist explícito; criar script de smoke-test de schema pós-migração
- **Prioridade:** Médio

## DATA-002 — BAIXO — `get_session()` sem context manager

- **Arquivo:** `src/zap_typist/db/session.py:67-70`
- **Problema:** `get_session()` retorna sessão sem garantir fechamento; caller deve chamar `.close()` manualmente; scoped_session faz cleanup, mas é fácil de esquecer
- **Correção:** expor também `@contextmanager def session_scope()` que faz `yield session; session.close()` no finally
- **Prioridade:** Baixo

## DATA-003 — BAIXO — `Flow.time_window_days` armazenado como JSON TEXT em vez de coluna separada

- **Arquivo:** `src/zap_typist/db/models.py:202`, `src/zap_typist/domain/flow.py`
- **Problema:** `time_window_days` é JSON array em coluna Text com `CHECK(json_valid(...))`; sem indexação; parsing manual em toda leitura
- **Correção:** avaliar armazenar como tabela de relacionamento `flow_days(flow_id, day)` em versão futura do schema; por ora, documentar no comentário do modelo que é intencional e limitado ao uso atual
- **Prioridade:** Baixo
