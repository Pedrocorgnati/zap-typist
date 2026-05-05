# Python Web Framework — module-3-aba1-queries (check mode)

**Status:** N/A

## Justificativa
Zap Typist é uma aplicação **desktop PySide6/Qt** rodando localmente com SQLite embedded. Não há FastAPI, Django, Flask ou outro web framework no `pyproject.toml`:

```
dependencies = [
  "PySide6>=6.6,<7",
  "SQLAlchemy>=2.0,<3",
  "pydantic>=2.0,<3",
  "pydantic-settings>=2.0,<3",
  "python-dotenv>=1.0,<2",
]
```

Module-3 é UI Qt (`Tab1GerarQueriesWidget`) + lógica de domínio (`query_generator`) — sem rotas, middlewares, ASGI/WSGI.

## Veredicto
Não aplicável.
