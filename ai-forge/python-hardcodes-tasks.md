# Python Hardcodes Tasks — zap-typist

**Data:** 2026-05-03

## HC-001 — BAIXO — UI strings de status hardcoded em `main_window.py`

- **Arquivo:** `src/zap_typist/ui/main_window.py:51` — `"DB pronto, 0 leads"`
- **Problema:** string de UI diretamente no código; não localizável
- **Correção:** mover para `domain/constants.py` ou arquivo de mensagens (`ui/messages.py`)
- **Prioridade:** Baixo

## HC-002 — BAIXO — Regex HH:MM hardcoded inline em `flow.py`

- **Arquivo:** `src/zap_typist/domain/flow.py:28` — `r"^[0-2]\d:[0-5]\d$"`
- **Problema:** regex de validação duplicada pode surgir se outros validators precisarem do mesmo padrão
- **Correção:** extrair para `domain/validators.py` como `HHMM_RE = re.compile(r"^[0-2]\d:[0-5]\d$")`; importar de lá
- **Prioridade:** Baixo

## HC-003 — BAIXO — `_BUSY_TIMEOUT_MS = 5000` sem comentário de por que 5s

- **Arquivo:** `src/zap_typist/db/session.py:29`
- **Problema:** magic number sem justificativa; valor adequado depende do hardware e do caso de uso
- **Correção:** adicionar comentário inline explicando a política (ex: "5s alinhado com busy_timeout recomendado para SQLite WAL com múltiplas abas Qt") ou mover para settings
- **Prioridade:** Baixo
