# Python Typing — module-3-aba1-queries (check mode)

**Status:** OK
**Mode:** check
**Tool:** mypy

## Resultado
```
mypy src/zap_typist/ui/aba1/ src/zap_typist/services/lead_service.py src/zap_typist/ui/tab1_gerar_queries.py
Success: no issues found in 7 source files
```

## Pontos fortes
- `from __future__ import annotations` em todos os 9 arquivos de module-3.
- `Protocol _ScopedSessionFactory` em `tab1_gerar_queries.py:35-40` — substitui dependência rígida de `sqlalchemy.orm.scoped_session` por contrato.
- Type hints em todas as fns públicas (`create_lead`, `generate_queries`, `_render_block`, `_build_dork_lines`).
- `dataclass(frozen=True) GenerationResult` — DTO imutável tipado.
- `Signal: Signal = Signal(...)` em widgets — anotação explícita do classvar.

## Issues
- **INFO** `mypy.strict=False` global, com strict habilitado apenas em `db.*` e `utils.*`. Module-3 não está em strict mode, mas mypy não reporta nenhum issue mesmo assim — type coverage parece sólida.
- **INFO** `lead_form.py:67` aceita `Callable[[], Any]` — perderá precisão se `session_factory` virar `scoped_session[Session]` no contrato (BaseWorker já usa o tipo concreto, há divergência local). Não bloqueador.

## Veredicto
Sem erros. Módulo respeita boas práticas de tipagem mesmo fora de strict mode.
