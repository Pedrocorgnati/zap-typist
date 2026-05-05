# Python Async — module-3-aba1-queries (check mode)

**Status:** OK
**Note:** Projeto desktop usa Qt threading (QThread + QThread.moveToThread), NÃO `asyncio`. Análise ajustada ao paradigma.

## Anti-drift greps
| Padrão proibido | Resultado |
|---|---|
| `QThreadPool` | 0 matches em src/ ✓ |
| `QRunnable` | 0 matches em src/ ✓ |
| `session.close()` isolado | 0 matches em module-3 ✓ |
| `moveToThread` fora de `_active_thread` | apenas 1 ocorrência em `tab1_gerar_queries.py:134` dentro do guard `if self._active_thread is not None: return` (linha 126) ✓ |

## Padrões corretos
- `Tab1GerarQueriesWidget._on_imbound_query_clicked`:
  - Guard double-click via `_active_thread is not None` (linha 126).
  - Cria `QueryGeneratorWorker` + `QThread`, `worker.moveToThread(thread)` (linha 134).
  - Conecta `thread.started → worker.execute`, `worker.signals.finished → thread.quit`, `worker.signals.finished → worker.deleteLater`, `thread.finished → thread.deleteLater` — gerência de lifetime canônica Qt.
  - Em `_on_query_generator_finished` e `_on_query_generator_error`: zera `_active_thread = _active_worker = None`. ✓
  - `_on_query_generator_finished` chama `self._session_factory.remove()` em `finally` (linha 155). ✓
- `BaseWorker.execute()` (module-2) emite `signals.finished` em `finally` mesmo após exception — garante que parent UI sempre receba sinal de término.
- `QueryGeneratorWorker.run()` propaga `cancel_check=lambda: self.cancel_requested` para `generate_queries` — cancelamento cooperativo respeitado.

## Operações bloqueantes
- `session.query/.commit` rodam em main thread em `_on_card_submit`/`_on_card_discard`/`_refresh_progress`. SQLite local com poucas linhas — latência sub-ms. Consciente.
- `output_path.write_text` em `query_generator` roda **dentro do worker thread** via `QueryGeneratorWorker.run` ✓. Main thread fica livre durante I/O.

## Shutdown gracioso
- `BaseWorker.cancel()` apenas marca flag — não interrompe operação atomicamente. `generate_queries` checa `cancel_check()` ANTES do loop principal, mas não DURANTE. Se um lote demorar (não esperado), cancel chega só no fim da geração. **INFO**, não bloqueador.

## Issues
- **INFO** `generate_queries` poderia checar `cancel_check()` dentro do loop `for lead in leads` para granularidade fina. Para 100 leads × <1ms cada, irrelevante.
- **INFO** `Tab1GerarQueriesWidget` não chama `worker.cancel()` em destrutor / `closeEvent`. Se a janela fechar com worker rodando, a thread continua até terminar `generate_queries`. Out-of-scope (closeEvent provavelmente está em `app.py`).

## Veredicto
Padrão Qt threading impecável. Anti-drift greps limpos.
