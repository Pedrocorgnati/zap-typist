# Python Error Handling — module-3-aba1-queries (check mode)

**Status:** WARN (1 falha funcional em test_worker_isolates_exceptions)

## Padrões observados
- Exceções específicas no fast-path: `SQLAlchemyError` (lead_card_list:114; tab1:231,303), `ValueError` (tab1:192,276), `OSError` (query_generator:121).
- `Exception` reservado para boundary handlers de UI: `lead_form:160` e `tab1:254,319` — sempre acompanhado de `logger.exception` ou `logger.error(exc_info=True)`.
- `BaseWorker.execute()` (module-2) já isola exceptions de `run()`, loga `worker_failed` e emite `signals.error` + `signals.log_line.emit("Erro: {exc_type}.")` + `signals.finished` no `finally`.

## Logging estruturado
- `logger.info("event_name", extra={...})` — pattern consistente.
- `logger.error("event_name", exc_info=True, extra={"lead_id": ...})` em rollback paths.
- Nenhum `print` ou `traceback.print_exc()` em código de produção.

## Rollback semântico
- `tab1._on_card_submit:232` — `session.rollback()` antes de `card.unlock_after_failure(...)` para reabilitar inputs.
- `query_generator:122` — `session.rollback()` antes de `raise` quando `OSError` no `write_text`. ✓
- Nenhum `commit` órfão sem rollback complementar em path de erro.

## Issues
### 🚨 BLOQUEADOR FUNCIONAL — Test failure
- `tests/unit/test_query_generator_worker.py::test_worker_isolates_exceptions` **falha** com:
  ```
  assert any("Erro" in m for m in msgs)
  E   assert False
  ```
  Contexto: `BaseWorker.execute` emite `self.signals.log_line.emit(f"Erro: {type(exc).__name__}.")`. O log do test mostra `worker_failed` sendo logado, mas o assertion sobre `msgs` (capturado de `signals.log_line`) retorna `False`.
  Hipóteses:
  1. Race entre `signals.log_line.emit` e `signals.finished.emit` no contexto do `qtbot.waitSignal` — emit acontece DENTRO do `try/except` antes do `finally` que emite `finished`, mas o teste pode estar capturando `finished` antes do dispatch do `log_line`.
  2. O segundo assertion (`"Erro na geração" in s for s in statuses`) implica que o teste espera que `QueryGeneratorWorker.run()` ALSO emita `signals.status_update.emit("Erro na geração")` — porém `QueryGeneratorWorker.run` não tem try/except próprio para isso.
  
  Module-3 está em `state=done` mas test está vermelho — drift entre TASK e implementação.

### Sugestão (não-bloqueador)
- Considerar adicionar try/except em `QueryGeneratorWorker.run` que emita `signals.status_update.emit("Erro na geração de queries")` antes de re-raise para BaseWorker — alinharia com o teste e com a Zero Silencio rule no nível worker (não apenas no parent que mostra QMessageBox).

## Veredicto
Padrão de error handling sólido EXCETO pela falha do `test_worker_isolates_exceptions`. Investigar antes de re-fazer release de module-3.
