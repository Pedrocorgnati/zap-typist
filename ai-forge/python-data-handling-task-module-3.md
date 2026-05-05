# Python Data Handling — module-3-aba1-queries (check mode)

**Status:** OK

## Validação de input (UI → DB)
- `lead_form.LeadFormWidget._validate()` rejeita `nome/ddd/prefixo` vazios.
- `_install_digit_filter` (lead_form.py:28-51) — sanitiza tanto entrada de teclado (validator) quanto programática (textChanged handler), com clamp por `max_digits`. Defesa em profundidade.
- `lead_card.LeadCardWidget._on_submit_clicked` valida `len(sufixo)==4 and sufixo.isdigit()` antes de emitir signal.
- `tab1_gerar_queries._on_card_submit` revalida E.164 (`format_e164`) e transição (`LeadStatusGuard.can_transition`) antes de UPDATE — defesa em camadas.

## Modelagem
- `LeadStatus` é Enum (acesso `.value` consistente em UPDATEs).
- `GenerationResult` é `dataclass(frozen=True)` (DTO imutável, 4 campos).
- `LeadCardListConfig` é dataclass simples para paginação.
- Pydantic v2 (`pydantic-settings`) usado em `config/settings.py` — fora do escopo do módulo.

## Datetime
- Único uso: `query_generator._render_header` recebe `today` como `date` via `today_provider: Callable[[], date] = date.today` — DI permite injeção determinística em testes. `date.today()` é date naive (sem timezone) — OK para header de relatório local.
- `lead.created_at` e `lead.updated_at` controlados por trigger SQLite (module-1) — não setados manualmente em module-3 (consistente com DoD).

## Sanitização de strings em DB
- `lead_service.create_lead` aplica `.strip()` em todos os campos textuais; converte `desire`/`info_extra` vazios para `None` (idempotência semântica).

## Issues
- **INFO** `query_generator._render_block` interpola `lead.nome`, `lead.info_extra` em strings com aspas duplas literais (linhas 44-47, 51-53). Se um valor contiver `"` interno, o dork resultante será malformado. Não há sanitização. Probabilidade baixa (nomes humanos raramente têm aspas), mas é uma quina não validada. Considerar `.replace('"', '\\"')` ou rejeição na entrada.
- **INFO** Encoding: `output_path.write_text(file_content, encoding="utf-8")` — explícito, OK.

## Veredicto
Validação multicamadas robusta. Apenas 1 corner-case de aspas em `_render_block`.
