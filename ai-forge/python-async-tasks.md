# Python Async Tasks — zap-typist

**Data:** 2026-05-03
**Status:** N/A — arquitetura Qt-thread, sem asyncio

## Contexto

O projeto usa `QThread` + `BaseWorker` com cancelamento cooperativo (`cancel_requested`), que é o padrão correto para PySide6. Não há `asyncio` event loop e não deveria haver — PySide6 tem seu próprio event loop Qt.

## ASY-001 — BAIXO — `time.sleep()` em `retry_on_locked` pode vazar para main thread

- **Arquivo:** `src/zap_typist/db/session.py:99`
- **Problema:** se `retry_on_locked` for chamado da main Qt thread (não de um worker), `time.sleep` congela a UI
- **Correção:** ver ERH-003 — documentar contrato que `retry_on_locked` só é chamado de QThread workers; considerar emitir um `warning` se `QThread.currentThread() == QCoreApplication.instance().thread()`
- **Prioridade:** Baixo
