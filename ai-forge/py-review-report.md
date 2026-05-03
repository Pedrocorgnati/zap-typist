# Python Complete Review Report — zap-typist (project-wide)

**Projeto:** zap-typist (Zap Typist)
**Config:** `.claude/projects/zap-typist.json` (alternativa)
**Modo:** legacy project-wide (validate-stack sem --module)
**Escopo:** full project scan — 16 sub-comandos Python
**Data:** 2026-05-03
**Versao Python:** 3.11 / 3.12
**Stack:** Python 3.11/3.12 + PySide6 6.6 + SQLAlchemy 2.x + SQLite WAL + pydantic-settings 2.x

---

## Resumo Executivo

| Severidade | Qtde |
|------------|------|
| CRITICO    | 0    |
| ALTO       | 1    |
| MEDIO      | 6    |
| BAIXO      | 25   |
| **TOTAL**  | **32** |

**Cobertura de testes:** 95.1% (threshold: 80%) ✅
**Segurança:** sem vetores de injeção; PII filtrado; TruffleHog e pip-audit no CI ✅
**CI/CD:** 5 jobs bem estruturados com actions SHA-pinadas ✅

---

## CONF — Configuração (5 issues)

### CONF-001 — MEDIO — `DEBUG` lido via `os.environ` fora do Settings
- **Arquivo:** `src/zap_typist/utils/logger.py`
- **Problema:** `if os.environ.get("DEBUG"):` — string `"false"` é truthy em Python; ignora validação Pydantic
- **Correção:** usar `settings.debug` via injeção ou import lazy; adicionar `debug: bool` ao `Settings`
- **Prioridade:** Médio

### CONF-002 — MEDIO — `ZAP_TYPIST_DATA_DIR` lido via `os.environ` fora do Settings
- **Arquivo:** `src/zap_typist/config/paths.py`
- **Problema:** `os.environ.get("ZAP_TYPIST_DATA_DIR")` sem validação Pydantic; path injection possível
- **Correção:** mover para `settings.data_dir: Path | None` com `Optional[Path]` em Settings; ajustar `paths.py` para consumir `settings`
- **Prioridade:** Médio

### CONF-003 — BAIXO — `settings = Settings()` sem `lru_cache`
- **Arquivo:** `src/zap_typist/config/settings.py`
- **Problema:** singleton module-level instanciado na importação; dificulta teste e reload
- **Correção:** `@lru_cache(maxsize=1)` em `def get_settings() -> Settings:` e substituir usos diretos por `get_settings()`
- **Prioridade:** Baixo

### CONF-004 — BAIXO — `.env.example` sem instrução de validação
- **Arquivo:** `.env.example` (ausente ou incompleto)
- **Problema:** desenvolvedores novos sem referência clara de variáveis obrigatórias
- **Correção:** criar `.env.example` com todos os campos de `Settings` comentados
- **Prioridade:** Baixo

### CONF-005 — BAIXO — `mypy` não strict globalmente
- **Arquivo:** `pyproject.toml:[tool.mypy]`
- **Problema:** `strict = false` globalmente; overrides apenas em `db.*` e `utils.*`; erros de tipo em outros módulos passam silenciosamente
- **Correção:** habilitar `strict = true` globalmente e corrigir violações incrementalmente
- **Prioridade:** Baixo

---

## TYP — Tipagem (4 issues)

### TYP-001 — MEDIO — `session_factory: Any` em `BaseWorker`
- **Arquivo:** `src/zap_typist/engine/base_worker.py`
- **Problema:** `Any` anula checagem de tipo na integração Qt/SQLAlchemy
- **Correção:** `session_factory: Callable[[], Session]` ou Protocol `SessionFactory`
- **Prioridade:** Médio

### TYP-002 — BAIXO — mypy overrides só em `db.*` e `utils.*`
- **Arquivo:** `pyproject.toml:[tool.mypy]`
- **Problema:** módulos `engine.*`, `ui.*`, `config.*` sem `strict` — erros de tipo latentes
- **Correção:** ampliar overrides ou habilitar `strict = true` global
- **Prioridade:** Baixo

### TYP-003 — BAIXO — Ausência de `reveal_type` tests ou mypy baseline
- **Arquivo:** CI — ausente
- **Problema:** sem baseline de erros mypy no CI; regressões de tipo passam silenciosamente
- **Correção:** `mypy --strict --ignore-missing-imports 2>&1 | tee mypy-baseline.txt` no CI; comparar delta
- **Prioridade:** Baixo

### TYP-004 — BAIXO — `WorkerSignals` sem tipo em `progress` signal
- **Arquivo:** `src/zap_typist/engine/base_worker.py`
- **Problema:** `Signal(int)` sem type alias; callers podem passar float sem erro de runtime
- **Correção:** documentar contrato do signal com comentário de tipo ou Protocol
- **Prioridade:** Baixo

---

## DEP — Dependências (3 issues)

### DEP-001 — ALTO — Sem lockfile
- **Arquivo:** raiz do projeto
- **Problema:** sem `poetry.lock`, `uv.lock`, ou `requirements.lock`; builds não são reprodutíveis; atualização silenciosa de transitive deps pode quebrar builds em CI
- **Correção:** adotar `uv lock` (recomendado por velocidade) ou `pip-compile requirements.in > requirements.lock`; commitar lockfile; CI instala de `--require-hashes`
- **Prioridade:** ALTO

### DEP-002 — BAIXO — Sem upper bounds em dependências críticas
- **Arquivo:** `pyproject.toml:[project.dependencies]`
- **Problema:** sem upper bound em PySide6, SQLAlchemy, pydantic-settings; breaking changes não são bloqueados
- **Correção:** adicionar `PySide6>=6.6,<7`, `SQLAlchemy>=2.0,<3`, `pydantic-settings>=2.0,<3`
- **Prioridade:** Baixo

### DEP-003 — BAIXO — `hypothesis>=6.0` sem upper bound em dev deps
- **Arquivo:** `pyproject.toml:[project.optional-dependencies.dev]`
- **Problema:** hypothesis tem breaking changes entre minor versions; sem upper bound
- **Correção:** `hypothesis>=6.0,<7`
- **Prioridade:** Baixo

---

## ARCH — Arquitetura (3 issues)

### ARCH-001 — BAIXO — Re-exports de paths em `models.py`
- **Arquivo:** `src/zap_typist/db/models.py`
- **Problema:** `models.py` re-exporta constantes de `paths.py` para compat; acoplamento indevido entre camada de modelo e config
- **Correção:** remover re-exports; importar `paths` diretamente onde necessário
- **Prioridade:** Baixo

### ARCH-002 — BAIXO — Ausência de `AppError` hierarchy
- **Arquivo:** `src/zap_typist/` — ausente
- **Problema:** exceções lançadas como `Exception` ou `RuntimeError` genéricos; difícil distinguir erros de domínio de bugs
- **Correção:** criar `src/zap_typist/errors.py` com `ZapTypistError(Exception)` e subclasses `DatabaseError`, `LockError`, `WorkerError`
- **Prioridade:** Baixo

### ARCH-003 — BAIXO — Sem camada de serviço explícita
- **Arquivo:** `src/zap_typist/engine/`
- **Problema:** lógica de negócio misturada nos workers Qt; dificulta teste unitário isolado da UI
- **Correção:** extrair `services/` com funções puras testáveis; workers delegam para serviços
- **Prioridade:** Baixo

---

## HC — Hardcodes (3 issues)

### HC-001 — BAIXO — Constantes de retry hardcoded em `session.py`
- **Arquivo:** `src/zap_typist/db/session.py`
- **Problema:** `backoff=(0.1, 0.5, 2.0)` e `_BUSY_TIMEOUT_MS` como literais; não configurável sem recompilação
- **Correção:** expor via `settings.db_busy_timeout_ms` e `settings.db_retry_backoff`
- **Prioridade:** Baixo

### HC-002 — BAIXO — Tamanho do log hardcoded
- **Arquivo:** `src/zap_typist/utils/logger.py`
- **Problema:** `maxBytes=10MB, backupCount=5` sem configuração externa
- **Correção:** `settings.log_max_bytes` e `settings.log_backup_count`
- **Prioridade:** Baixo

### HC-003 — BAIXO — Exit codes como literais em `app.py`
- **Arquivo:** `src/zap_typist/app.py`
- **Problema:** `EXIT_OK=0`, `EXIT_LOCK=1`, etc. definidos localmente; não reutilizáveis em tests
- **Correção:** mover para `src/zap_typist/errors.py` ou `constants.py` como `IntEnum`
- **Prioridade:** Baixo

---

## DATA — Data Handling (3 issues)

### DATA-001 — MEDIO — Sem Alembic (migrações manuais)
- **Arquivo:** `src/zap_typist/db/`
- **Problema:** migrations manuais documentadas mas sem versionamento automático; risco de divergência schema vs models em campo
- **Correção:** adicionar Alembic com `env.py` apontando para `Base.metadata`; gerar migration inicial; CI roda `alembic upgrade head`
- **Prioridade:** Médio

### DATA-002 — BAIXO — `UTCDateTime` sem validação de timezone na leitura
- **Arquivo:** `src/zap_typist/db/models.py`
- **Problema:** `TypeDecorator.process_result_value` retorna `datetime` sem garantir `tzinfo=UTC`; SQLite armazena sem tz
- **Correção:** `return value.replace(tzinfo=UTC)` no `process_result_value`
- **Prioridade:** Baixo

### DATA-003 — BAIXO — Sem política de soft-delete documentada
- **Arquivo:** `src/zap_typist/db/models.py`
- **Problema:** `Lead.deleted_at` existe mas sem query filter global; queries podem retornar leads deletados
- **Correção:** adicionar `@event.listens_for` ou filter default em `session.query(Lead)` para excluir `deleted_at IS NOT NULL`
- **Prioridade:** Baixo

---

## SEC — Segurança (1 issue)

### SEC-001 — MEDIO — `DEBUG=false` é truthy em `logger.py`
- **Arquivo:** `src/zap_typist/utils/logger.py`
- **Problema:** `os.environ.get("DEBUG")` retorna string `"false"` que é truthy em Python; ativa modo debug mesmo quando configurado como `false`
- **Correção:** `os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")` ou usar `settings.debug`
- **Prioridade:** Médio

**Pontos fortes de segurança:**
- `PIIFilter` mascara dados sensíveis em todos os log records ✅
- `TruffleHog` no CI para secrets scan ✅
- `pip-audit` no CI para SCA ✅
- `f"PRAGMA busy_timeout={int(_BUSY_TIMEOUT_MS)}"` — usa `int()` para prevenir SQL injection ✅
- `foreign_keys=ON` no SQLite ✅

---

## ERH — Error Handling (3 issues)

### ERH-001 — BAIXO — Sem hierarchy de `AppError`
- **Arquivo:** `src/zap_typist/` — ausente
- **Problema:** exceções genéricas sem distinção de domínio (ver ARCH-002)
- **Correção:** criar `ZapTypistError` base e subclasses
- **Prioridade:** Baixo

### ERH-002 — BAIXO — `_setup_excepthook()` sem logging estruturado
- **Arquivo:** `src/zap_typist/app.py`
- **Problema:** `QMessageBox` exibe exceção não tratada mas não persiste em log; perde stack trace
- **Correção:** `logger.critical("Unhandled exception", exc_info=exc_value)` antes do QMessageBox
- **Prioridade:** Baixo

### ERH-003 — BAIXO — `retry_on_locked()` usa `time.sleep()` na thread principal
- **Arquivo:** `src/zap_typist/db/session.py`
- **Problema:** se chamado na thread principal Qt, bloqueia event loop durante retry (0.1–2.0s)
- **Correção:** garantir que `retry_on_locked` só seja chamado de workers; ou usar `asyncio.sleep` em contexto async
- **Prioridade:** Baixo

---

## TEST — Testes (3 issues)

### TEST-001 — BAIXO — Sem testes de integração para `retry_on_locked`
- **Arquivo:** `tests/`
- **Problema:** backoff de 0.1–2.0s testável apenas com mock; sem teste de integração com SQLite real sob lock concorrente
- **Correção:** teste com dois threads, um mantendo lock, outro tentando adquirir
- **Prioridade:** Baixo

### TEST-002 — BAIXO — Sem testes para `PIIFilter`
- **Arquivo:** `tests/`
- **Problema:** filtro de PII é crítico para conformidade; sem cobertura de casos edge (nested dict, lista)
- **Correção:** adicionar `tests/test_logger.py` com casos de PII em nested structures
- **Prioridade:** Baixo

### TEST-003 — BAIXO — `seeded_session` sem `defaults=build_settings_defaults()`
- **Arquivo:** `tests/conftest.py`
- **Problema:** `run_seed(force=True)` sem defaults explícitos; seed pode falhar silenciosamente se `Setting` table vazia
- **Correção:** `run_seed(force=True, defaults=build_settings_defaults())`
- **Prioridade:** Baixo

---

## PERF — Performance (1 issue)

### PERF-001 — BAIXO — Sem pooling de conexões configurado
- **Arquivo:** `src/zap_typist/db/session.py`
- **Problema:** SQLite single-file; `NullPool` ou `StaticPool` podem ser mais adequados para desktop single-user
- **Correção:** avaliar `create_engine(..., poolclass=StaticPool)` para evitar overhead de pool em app single-user
- **Prioridade:** Baixo

---

## ASY — Async (1 issue)

### ASY-001 — BAIXO — `time.sleep()` em `retry_on_locked` bloqueia thread Qt
- **Arquivo:** `src/zap_typist/db/session.py`
- **Problema:** `time.sleep()` em worker thread Qt não bloqueia UI, mas impede processamento de sinais Qt no worker (ver ERH-003)
- **Correção:** documentar explicitamente que `retry_on_locked` só pode ser chamado de `QThread`; adicionar assert
- **Prioridade:** Baixo

---

## SCL — Escalabilidade (1 issue)

### SCL-001 — BAIXO — N/A para app single-user desktop
- Sem problemas de escalabilidade aplicáveis. App PySide6 single-user local por design.

---

## CICD — CI/CD (3 issues)

### CICD-001 — MEDIO — Sem automatização de release e tagging semântico
- **Arquivo:** `.github/workflows/` — nenhum job de release
- **Problema:** sem workflow para criar tags `vX.Y.Z`, gerar CHANGELOG, ou publicar binário/wheel
- **Correção:** criar `.github/workflows/release.yml` com job em push de tag `v*.*.*`; `python -m build`, checksums, upload como GitHub Release asset
- **Prioridade:** Médio

### CICD-002 — BAIXO — Coverage report só para Python 3.11
- **Arquivo:** `.github/workflows/ci.yml:89`
- **Problema:** `if: always() && matrix.python-version == '3.11'`; coverage de 3.12 nunca capturada
- **Correção:** remover condição ou usar `codecov/codecov-action` que agrega as duas
- **Prioridade:** Baixo

### CICD-003 — BAIXO — `pre-commit` não rodado no CI
- **Arquivo:** `.pre-commit-config.yaml` existe mas não invocado no workflow
- **Problema:** hooks locais podem divergir do CI
- **Correção:** adicionar step `pre-commit run --all-files` no job `lint-and-type` usando `pre-commit/action@v3`
- **Prioridade:** Baixo

---

## PKG — Packaging (3 issues)

### PKG-001 — MEDIO — Sem workflow de release automatizado
- **Arquivo:** raiz do projeto
- **Problema:** sem `gh release create`, sem `python -m build` no CI, sem checklist de release
- **Correção:** criar `.github/workflows/release.yml` com `python -m build && twine check dist/*` + upload do wheel ao GitHub Release; ver CICD-001
- **Prioridade:** Médio

### PKG-002 — BAIXO — `project.urls` sem `homepage` e `documentation`
- **Arquivo:** `pyproject.toml:[project.urls]`
- **Problema:** apenas `Repository` e `Issues` declarados
- **Correção:** adicionar `Documentation` e `Homepage` quando disponíveis
- **Prioridade:** Baixo

### PKG-003 — BAIXO — Sem `MANIFEST.in` para arquivos não-Python
- **Arquivo:** raiz do projeto
- **Problema:** setuptools pode não incluir `py.typed`, `README.md`, `.env.example` no sdist
- **Correção:** verificar com `python -m build && tar -tzf dist/*.tar.gz`; adicionar `MANIFEST.in` conforme necessário
- **Prioridade:** Baixo

---

## WEB-FRAMEWORK / API

**Status:** N/A — aplicação desktop PySide6, sem web framework nem API HTTP.

---

## Checklist de Priorização

### Ação imediata (ALTO)
- [ ] DEP-001 — criar lockfile (`uv lock` ou `pip-compile`)

### Próximo sprint (MÉDIO)
- [ ] CONF-001 — corrigir `DEBUG=false` truthy em `logger.py`
- [ ] CONF-002 — mover `ZAP_TYPIST_DATA_DIR` para Settings
- [ ] TYP-001 — tipar `session_factory` em `BaseWorker`
- [ ] DATA-001 — adicionar Alembic para migrações versionadas
- [ ] SEC-001 — corrigir leitura de `DEBUG` (mesma fix do CONF-001)
- [ ] CICD-001 / PKG-001 — criar workflow de release

### Backlog (BAIXO)
- Demais 25 issues de baixa prioridade listados acima

---

## Pontos Fortes do Projeto

- Cobertura de testes: **95.1%** (threshold 80%) ✅
- SQLAlchemy 2.x com `Mapped[]` e `mapped_column` modernos ✅
- `UTCDateTime` TypeDecorator para tz-aware datetimes ✅
- `PIIFilter` em todos os log records ✅
- CI com 5 jobs, SHA-pinados, matrix 3.11/3.12 ✅
- `QT_QPA_PLATFORM: offscreen` para testes headless ✅
- `TruffleHog` + `pip-audit` no CI ✅
- SQLite WAL + `foreign_keys=ON` + `busy_timeout` ✅
- `pyproject.toml` completo com `Private :: Do Not Upload` classifier ✅
- `BaseWorker` com cooperative cancel e `finished` garantido em finally ✅
- Exit codes explícitos no `main()` ✅
- Single-instance lock via lockfile ✅
