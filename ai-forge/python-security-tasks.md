# Python Security Tasks — zap-typist

**Data:** 2026-05-03
**Status:** SEM issues críticas ou altas

## Pontos fortes confirmados

- Nenhum `eval`, `exec`, `pickle.loads`, `yaml.load` (sem `safe_load`), `os.system` ou `subprocess(shell=True)` no código-fonte
- Nenhum secret hardcoded (TruffleHog no CI, grep limpo)
- PII filter em todos os loggers (`PIIFilter` mascara campos sensíveis)
- Permissões 0700/0600 em diretórios e arquivos de dados
- `f"PRAGMA busy_timeout={int(_BUSY_TIMEOUT_MS)}"` — safe: `int()` neutraliza injeção (documentado N-SEC-1)
- `pip-audit` no CI auditando dependências
- Secrets scan com TruffleHog no CI (hashes de actions pinadas)
- Sem autenticação necessária (app desktop single-user, single-instance lock via filesystem)

## SEC-001 — BAIXO — `DEBUG=false` em `.env` lido via `os.environ.get("DEBUG")` sem validação booleana

- **Arquivo:** `src/zap_typist/utils/logger.py:98`
- **Problema:** valor string "false" é truthy em Python; se operador colocar `DEBUG=false` (como no .env), ativa logging de debug inadvertidamente
- **Correção:** usar `os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")` ou mover para Settings com `bool` type (pydantic-settings parseia booleanos corretamente)
- **Prioridade:** Baixo
