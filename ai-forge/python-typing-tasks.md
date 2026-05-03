# Python Typing Tasks — zap-typist

**Data:** 2026-05-03

## TYP-001 — MÉDIO — `BaseWorker.session_factory: Any` e `get_session() -> Any`

- **Arquivo:** `src/zap_typist/engine/base_worker.py:55,62`
- **Problema:** injeção tipada como `Any`; perde verificação estática de chamadas de sessão
- **Correção:** declarar `SessionFactoryProtocol(Protocol)` com `__call__() -> Session` e `remove() -> None`; substituir `Any` pelo Protocol
- **Prioridade:** Médio

## TYP-002 — MÉDIO — mypy não roda em modo strict global

- **Arquivo:** `pyproject.toml:[tool.mypy]` — `strict = false`
- **Problema:** sem `disallow_untyped_defs`, `warn_return_any` globais; erros latentes em módulos não cobertos pelos overrides
- **Correção:** expandir overrides para cobrir `app`, `domain`, `config`, `seeders`; meta: chegar a `strict = true` global em 2-3 iterações
- **Prioridade:** Médio

## TYP-003 — BAIXO — `desire_rules: list[dict[str, Any]]` em SettingsSchema

- **Arquivo:** `src/zap_typist/domain/settings_schema.py:43`
- **Problema:** `dict[str, Any]` não descreve a estrutura dos rules; sem validação de campos
- **Correção:** criar `DesireRule(BaseModel)` com campos typed; substituir `list[dict[str, Any]]` por `list[DesireRule]`
- **Prioridade:** Baixo

## TYP-004 — BAIXO — `type: ignore[attr-defined]` em session.py sem justificativa em doc

- **Arquivo:** `src/zap_typist/db/session.py:47`
- **Problema:** supressão de erro de tipo sem documentação em `docs/typing.md`
- **Correção:** criar `docs/typing.md` com lista de `type: ignore` e justificativas (DBAPI sem stub tipado para `.cursor()`)
- **Prioridade:** Baixo
