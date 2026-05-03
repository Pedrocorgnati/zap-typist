# Python Error Handling Tasks — zap-typist

**Data:** 2026-05-03

## Pontos fortes confirmados

- `_setup_excepthook()` captura unhandled exceptions com QMessageBox visual
- Boot functions retornam exit codes tipados (`EXIT_OK=0`, `EXIT_LOCK=1`, `EXIT_OS_ERROR=2`, `EXIT_SCHEMA_ERROR=3`)
- `BaseWorker.execute()` envelopa `run()` com try/except/finally garantindo `finished.emit()` sempre
- Exceções específicas capturadas: `PermissionError`, `OSError` com `errno`, `OperationalError` com retry
- Logging estruturado JSON com `PIIFilter`
- `retry_on_locked` com backoff determinístico e propagação do erro original

## ERH-001 — MÉDIO — Sem hierarquia de exceções de domínio (`AppError`)

- **Arquivo:** toda a base de código
- **Problema:** exceptions são `RuntimeError`, `ValueError`, `PermissionError` nativas — sem `AppError(code=..., message=...)` padronizado; dificulta tratamento diferenciado na UI
- **Correção:** criar `src/zap_typist/domain/exceptions.py` com `ZapTypistError(Exception)` e subclasses (`SchemaError`, `LockError`, `IOError`) contendo `code: str` e `user_message: str`; UI converte em QMessageBox com base no type
- **Prioridade:** Médio

## ERH-002 — BAIXO — `logger.critical("db_disk_full")` sem `exc_info=True` em alguns casos

- **Arquivo:** `src/zap_typist/app.py:145-147`
- **Problema:** `logger.critical("db_disk_full")` não passa `exc_info=True`; stack trace não chega ao log de arquivo para debugging
- **Correção:** adicionar `exc_info=True` em todos os `logger.critical/error` dentro de blocos `except`
- **Prioridade:** Baixo

## ERH-003 — BAIXO — `time.sleep()` em `retry_on_locked` bloqueia thread Qt

- **Arquivo:** `src/zap_typist/db/session.py:99`
- **Problema:** `time.sleep(wait)` dentro do contexto da thread Qt pode congelar a UI se chamado na thread principal
- **Correção:** garantir (via docstring e comentário) que `retry_on_locked` só é chamado de QThread workers; adicionar assert ou warning se detectado na main thread
- **Prioridade:** Baixo
