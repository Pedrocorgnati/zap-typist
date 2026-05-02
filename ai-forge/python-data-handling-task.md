# Python Data Handling — Plan (module-1-setup)

**Modo:** `--plan`
**Equivalente MODULE-META:** check `boundaries` (validação em fronteiras de dados)
**Comando equivalente:** `/python:data-handling plan .claude/projects/zap-typist.json`

---

## FASE 1 — Auditoria

### Boundaries identificados em module-1

1. **Persistência (DB ↔ ORM):** `db/models.py` declara colunas `Text`/`Integer`/`Boolean`/`DateTime`. CHECK constraints existem para enums (`status`, `mode`) e para `rate_limit_per_hour <= 30`. Triggers de `updated_at` via DDL.
2. **Filesystem (arquivo ↔ memória):** `utils/cache.py` lê/grava arquivos em CACHE_DIR (UTF-8). `utils/single_instance.py` lê/grava PID em LOCK_FILE.
3. **ENV vars (processo ↔ aplicação):** `os.environ.get(...)` em `db/models.py:41`, `app.py:43`, `utils/logger.py:95`.
4. **Settings (table ↔ runtime config):** `db/seed.py:42-72` faz `json.dumps(...)` para serializar listas (`feminine_names`, `desire_rules`, `default_window_days`). Reidratação esperada em modules 3-5 (não coberta por module-1).

### Estado atual

**ORM (`db/models.py`):**
- `DateTime` SEM `timezone=True` em todos os timestamps:
  - `Lead.whatsapp_validated_at` (linha 123)
  - `Lead.created_at`, `Lead.updated_at` (127, 130)
  - `Setting.updated_at` (142)
  - `Flow.paused_at` (180), `Flow.created_at`, `Flow.updated_at` (184, 187)
  - `ContactHistory.touched_at` (210)
- SQLite armazena via `CURRENT_TIMESTAMP` (UTC naive). Comparações em Python: aspirações naive vs aware são erro.
- `Lead.numero_e164: Mapped[str | None]` (linha 117) — `Text nullable=True`, **sem CHECK constraint** para formato `^\+\d{10,15}$`.
- `Flow.time_window_days: Mapped[str]` (linha 164) — `Text` sem schema. Em `seed.py:61` é `json.dumps(["1","2","3","4","5"])`. Em `test_models.py:70` é `"1,2,3,4,5"` (CSV). **Inconsistência de formato canônico.**
- `Setting.value: Mapped[str]` (linha 141) — schema fraco; valores são strings que requerem parse separado.

**Configuração:**
- `pydantic-settings>=2.0` em `requirements.txt:4` mas zero imports de `pydantic_settings` em `src/`.
- ENV vars consumidas direto (sem schema, sem validação, sem defaults centralizados).

**Seed (`db/seed.py`):**
- `_build_defaults()` retorna `dict[str, str]` (linha 42). Todos os valores são strings — listas viram JSON via `json.dumps`, ints viram `str(N)`.
- Reidratação ausente em module-1: nenhum boundary parser `Setting.value -> typed`.

### Gaps identificados

| # | Sev | Categoria | Achado | Evidência |
|---|-----|-----------|--------|-----------|
| D-01 | P0 | datetime tz | Todos os timestamps sem `timezone=True`. SQLite armazena naive UTC. Comparações futuras com `datetime.now(tz=UTC)` quebram. | `db/models.py:123,127,130,142,180,184,187,210` |
| D-02 | P1 | env schema | `pydantic-settings` declarado mas não usado. ENV consumidas direto sem validação central. | `requirements.txt:4`, `db/models.py:41`, `app.py:43`, `utils/logger.py:95` |
| D-03 | P1 | format inconsistency | `Flow.time_window_days` aceita CSV (`"1,2,3,4,5"`) e JSON (`["1","2",...]`) — formato não canonizado. | `db/seed.py:65` (JSON) vs `tests/unit/test_models.py:70` (CSV) |
| D-04 | P1 | settings parser | Sem boundary parser `Setting.value -> typed`. Reidratação dispersa em consumers. | (ausência) |
| D-05 | P2 | e164 validation | `Lead.numero_e164` sem CHECK e sem validação Pydantic. Inputs podem entrar mal-formatados. | `db/models.py:117` |
| D-06 | P2 | json.dumps inline | Listas serializadas inline via `json.dumps(...)` em `seed.py:55,56,65`. Sem schema-de-volta documentado. | `db/seed.py:55-65` |
| D-07 | P3 | Setting tipado | `Setting.value: Text` é totalmente livre. Considerar tabela de defaults tipados (numéricos/listas/strings) ou `JSON Schema` por chave. | `db/models.py:141` |

---

## FASE 2 — Correções propostas (NÃO APLICADAS)

### Fix D-01: timezone-aware datetime em todos os timestamps

```python
# src/zap_typist/db/models.py
from sqlalchemy import DateTime

class Lead(Base):
    ...
    whatsapp_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
# repetir em Setting.updated_at, Flow.*, ContactHistory.touched_at
```

**Atenção SQLite:** `DateTime(timezone=True)` em SQLite armazena ISO8601 com offset (preserva tz). Triggers `CURRENT_TIMESTAMP` retornam UTC naive, mas SQLAlchemy lê de volta como aware se a coluna for `DateTime(timezone=True)`. Validar com integration test `test_timestamps_are_aware`.

ADR pendente: documentar política de timezone (sempre UTC armazenado; conversão para horário local apenas na UI).

### Fix D-02: schema central de ENV via pydantic-settings

(Coordenado com Fix C-06 do `python-configuration-task.md` — não duplicar. Adicional aqui:)

```python
# src/zap_typist/config/settings.py — adicional
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZAP_TYPIST_", ...)

    data_dir: Path | None = None
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    rate_limit_max: int = 30  # mirror RATE_LIMIT_MAX_POR_HORA, override via ENV
    contact_history_window_days: int = 60
```

`db.models.RATE_LIMIT_MAX_POR_HORA` se torna `settings.rate_limit_max` (ou mantém constante e `Settings` valida que não excede).

### Fix D-03: canonizar formato de `time_window_days`

Decidir formato canônico. Recomendação: **JSON list de strings**, batendo com `seed.py:65`.

Adicionar CHECK constraint:

```python
class Flow(Base):
    __table_args__ = (
        CheckConstraint(
            "json_valid(time_window_days) AND json_type(time_window_days) = 'array'",
            name="ck_flows_time_window_days_json",
        ),
        ...
    )
```

E criar Pydantic model em `domain/flow.py`:

```python
from pydantic import BaseModel, Field, field_validator

class TimeWindow(BaseModel):
    days: list[Literal["1", "2", "3", "4", "5", "6", "7"]] = Field(min_length=1)
    start: str  # HH:MM
    end: str

    @field_validator("start", "end")
    @classmethod
    def _validate_hhmm(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"^[0-2]\d:[0-5]\d$", v):
            raise ValueError(f"esperado HH:MM, recebi {v!r}")
        return v
```

Atualizar `tests/unit/test_models.py:70` para usar JSON em vez de CSV.

### Fix D-04: parser tipado `Setting.value -> typed`

Criar `src/zap_typist/domain/settings_schema.py`:

```python
"""Schema de parse para Setting.value — boundary table -> Python typed."""
from __future__ import annotations
import json
from typing import Any
from pydantic import BaseModel


class SettingsSchema(BaseModel):
    """Reflete defaults conhecidos em SEED_DEFAULTS, com tipos corretos."""

    msg_template_1: str
    msg_template_2: str
    msg_template_3: str
    msg_template_4: str
    msg_template_5: str
    sender_nome: str
    sender_profissao: str
    sender_portfolio_url: str
    msg_fallback_block: str
    feminine_names: list[str]
    desire_rules: list[dict[str, Any]]  # tightening em module-3
    default_aba1_origin: str
    default_mode: Literal["manual", "automatico"]
    default_rate_per_hour: int
    default_min_interval: int
    default_max_interval: int
    default_batch_size: int
    default_batch_pause_min: int
    default_batch_pause_max: int
    default_window_days: list[str]
    default_window_start: str
    default_window_end: str
    contact_history_window_days: int
    app_version: str
    seed_version: int


def load_settings(rows: dict[str, str]) -> SettingsSchema:
    """Reidrata Setting.value — converte JSON e ints onde aplicável."""
    parsed: dict[str, Any] = {}
    json_keys = {"feminine_names", "desire_rules", "default_window_days"}
    int_keys = {
        "default_rate_per_hour", "default_min_interval", "default_max_interval",
        "default_batch_size", "default_batch_pause_min", "default_batch_pause_max",
        "contact_history_window_days", "seed_version",
    }
    for k, v in rows.items():
        if k in json_keys:
            parsed[k] = json.loads(v)
        elif k in int_keys:
            parsed[k] = int(v)
        else:
            parsed[k] = v
    return SettingsSchema(**parsed)
```

Consumers em modules 3-5 chamam `load_settings(dict(session.query(Setting).all()))`.

### Fix D-05: validar e164 antes de persistir

Adicionar CHECK constraint:

```python
class Lead(Base):
    __table_args__ = (
        ...
        CheckConstraint(
            "numero_e164 IS NULL OR numero_e164 GLOB '+[0-9]*'",
            name="ck_leads_numero_e164_format",
        ),
    )
```

E Pydantic field:

```python
# src/zap_typist/domain/validators.py
from typing import Annotated
from pydantic import AfterValidator
import re

_E164_RE = re.compile(r"^\+\d{10,15}$")


def _validate_e164(v: str) -> str:
    if not _E164_RE.fullmatch(v):
        raise ValueError(f"numero não está em E.164: {v!r}")
    return v


PhoneE164 = Annotated[str, AfterValidator(_validate_e164)]
```

Atenção: SQLite GLOB é fraco (não valida tamanho). Validação forte fica no Pydantic, CHECK é defesa em profundidade.

### Fix D-06: documentar contract de serialização

Criar `docs/contracts/settings.md` com:
- Quais keys são JSON-encoded (`feminine_names`, `desire_rules`, `default_window_days`).
- Quais são ints stringified.
- Tipos canônicos (mirror de `SettingsSchema`).
- Versionamento via `seed_version`.

### Fix D-07: avaliar redesign de Setting

Registrar dívida (não resolver agora):
> Module-X deve avaliar substituir `Setting (name, value: Text)` por tabela polimórfica ou múltiplas tabelas tipadas (`SenderProfile`, `RateLimitDefaults`, `MessageTemplates`). Trade-off: complexidade de schema vs. type safety.

---

## FASE 3 — Validação

```bash
# Lint Pydantic / mypy
mypy src/zap_typist/domain/

# Tests timezone-aware
pytest tests/integration/test_timestamps_are_aware.py

# Tests boundary parser
pytest tests/unit/test_settings_schema.py

# Tests e164 validator
pytest tests/unit/test_e164_validator.py
```

**Aceite:** `Setting.value` parseável via `load_settings()`; todos timestamps `tzinfo is not None` ao retornar do DB; `Lead.numero_e164` valida E.164 antes de commit.

---

## Resumo

- **Issues:** 7 (P0: 1 · P1: 3 · P2: 2 · P3: 1)
- **Fixes propostos:** 7
- **Esforço:** 3-5h (Fix D-04 boundary parser é o mais demorado)
- **Risco alto:** D-01 muda colunas — requer migration script (`MIGRATION-v1.0.1.py` per ADR-007 planejado em `db/session.py:1-7`)
- **Coordena com:** module-3 (Aba 1 valida e164 ao gerar query) e module-5 (Aba 4 grava settings parseando schema)
