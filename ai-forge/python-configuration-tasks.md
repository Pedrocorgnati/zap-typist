# Python Configuration Tasks — zap-typist

**Data:** 2026-05-03
**Status:** Auditado

## CONF-001 — MÉDIO — `os.environ.get("DEBUG")` fora do Settings

- **Arquivo:** `src/zap_typist/utils/logger.py:98`
- **Tipo:** env lida fora de BaseSettings
- **Impacto:** comportamento de logging não controlado por Settings; não aparece em `.env.example` como variável gerenciada; sem validação de tipo
- **Correção:** adicionar `debug_logging: bool = False` em `Settings` (ou reutilizar `debug`), e ler `settings.debug` no logger
- **Prioridade:** Médio

## CONF-002 — MÉDIO — `os.environ.get("ZAP_TYPIST_DATA_DIR")` fora do Settings

- **Arquivo:** `src/zap_typist/config/paths.py:13`
- **Tipo:** env lida fora de BaseSettings
- **Impacto:** variável de override lida antes do boot do Settings; sem validação de tipo Path; não documentada no Settings
- **Correção:** criar `AppPaths(BaseSettings)` com `data_dir: Path | None = None` ou resolver paths dentro de `Settings` via `@property`
- **Prioridade:** Médio
- **Nota:** é desejável que paths.py seja folha sem deps pydantic para evitar import pesado no boot; alternativa é manter como está e documentar explicitamente que é bootstrap

## CONF-003 — BAIXO — `settings = Settings()` singleton sem lru_cache

- **Arquivo:** `src/zap_typist/config/settings.py:29`
- **Tipo:** factory sem cache
- **Impacto:** testes não podem substituir settings via `monkeypatch` em leitura lazy; instanciação múltipla possível em testes paralelos
- **Correção:** adicionar `from functools import lru_cache` e expor `get_settings() -> Settings` cacheado; manter `settings = get_settings()` por compat
- **Prioridade:** Baixo

## CONF-004 — BAIXO — `ZAP_TYPIST_DEV_MODE` e `DATABASE_URL` em `.env` mas não em `Settings`

- **Arquivo:** `.env`, `.env.example`
- **Tipo:** env não mapeada em BaseSettings (extra="ignore" silencia)
- **Impacto:** operador ajusta variável sem efeito; engana quem mantém o projeto
- **Correção:** adicionar `dev_mode: bool = False` em `Settings`, ou remover `ZAP_TYPIST_DEV_MODE` do `.env.example`; remover `DATABASE_URL` do .env.example (path vem de `paths.py`)
- **Prioridade:** Baixo

## CONF-005 — MÉDIO — mypy `strict = false` globalmente

- **Arquivo:** `pyproject.toml:[tool.mypy]`
- **Tipo:** ferramenta de tipagem não no modo estrito
- **Impacto:** grande parte do código não é verificada estritamente; erros de tipo latentes podem surgir ao adicionar novos módulos
- **Correção:** migrar gradualmente para `strict = true` começando pelos módulos que já têm overrides (`db.*`, `utils.*`); adicionar overrides de exclusão para módulos que ainda não atendem (`ui.*`, `engine.*`)
- **Prioridade:** Médio
