# Python Hardcodes — module-3-aba1-queries (check mode)

**Status:** OK (com 1 INFO)

## Constantes nomeadas (boas)
- `lead_card.py:22-23`: `COPIED_FEEDBACK_MS = 2000`, `SUFIXO_LEN = 4`
- `lead_card_list.py:28-30`: `EMPTY_STATE_MSG`, `ERROR_MSG`, `PAGINATION_THRESHOLD = 100`
- `lead_card_list_config.py`: `page_size: int = 50`
- `query_generator.py:25-27`: `OUTPUT_FILENAME`, `DIVIDER_WIDTH = 28`, `DIVIDER`
- `tab1_gerar_queries.py:32`: `TERMINAL_FIXED_HEIGHT = 150`
- `lead_service.py:12`: `DEFAULT_ORIGIN_KEY = "default_aba1_origin"`

## Strings reutilizadas centralizadas
- Cores: `ui.styles` (`COLOR_FEEDBACK_SUCCESS`, `COLOR_FEEDBACK_ERROR`, `COLOR_CMD_BTN`, `COLOR_CMD_BTN_TEXT`).
- Origem padrão: `domain.constants.ORIGEM_PADRAO_ABA1` (lido com fallback explícito em `lead_service._read_default_origin`).

## Hardcodes residuais
- **INFO** `lead_card.py:161`: `setStyleSheet("color: #F6465D; font-weight: bold;")` — cor hex literal. Para coerência com `_show_copied_feedback()` (que usa `COLOR_FEEDBACK_SUCCESS`), trocar por `COLOR_FEEDBACK_ERROR` já existente em `ui.styles`.
- **INFO** `lead_form.py:25`: `_DIGITS_RE = QRegularExpression(r"\d+")` — OK (constante module-level, regex).
- **INFO** `tab1_gerar_queries.py:339`: comentário descreve regra de negócio do INTAKE — adequado.
- Strings de UI em pt-BR aparecem inline (mensagens de QMessageBox, placeholders) — não há i18n no projeto, intencional dado o escopo desktop pessoal.

## Segredos / paths
- Nenhum URL, host, porta, IP, token, senha hardcoded.
- Path único derivado: `Path(CACHE_DIR) / OUTPUT_FILENAME` (`config.paths.CACHE_DIR` resolvido via XDG).

## Veredicto
1 cor hex literal a centralizar. Caso contrário, hardcode hygiene exemplar.
