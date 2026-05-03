# Python Scalability Tasks — zap-typist

**Data:** 2026-05-03
**Status:** N/A — aplicação desktop single-user; requisitos de escalabilidade não se aplicam

## Contexto

O zap-typist é uma aplicação desktop de usuário único em SQLite. Não há requisitos de escalabilidade horizontal, filas distribuídas, cache distribuído ou health endpoints HTTP.

## SCL-001 — BAIXO — Sem rate-limit de UI para prevenção de double-submit

- **Arquivo:** `src/zap_typist/engine/base_worker.py`
- **Problema:** quando os rocks implementarem actions de disparo, o UI pode disparar múltiplos workers simultâneos se o usuário clicar repetidamente antes do feedback
- **Correção:** usar flag `_running: bool` por worker ou desabilitar botão de ação enquanto worker estiver ativo (emitir sinal para UI no `signals.progress` + `signals.finished`)
- **Prioridade:** Baixo (preventivo — aplicar ao implementar rock-3)
