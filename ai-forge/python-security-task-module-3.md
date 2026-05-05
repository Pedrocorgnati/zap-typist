# Python Security — module-3-aba1-queries (check mode)

**Status:** OK
**Tools:** ruff (S* select via flake8-bandit), grep manual (PII, SQLi, paths)
**Bandit standalone:** não instalado no venv — `ruff lint S*` cobre os checks principais (S101, S106, S311, S701).

## OWASP / categorias relevantes
- **A03 Injection (SQL):** Todas as queries via SQLAlchemy ORM (`session.query(Lead).filter(Lead.status == ...)`). Nenhum `text()` ou string-formatting em SQL. ✓
- **A03 Injection (file content):** `output_path.write_text` grava arquivo dentro de `CACHE_DIR` (XDG). Não controlado por input externo. Mas conteúdo do dork inclui `lead.nome/desire/info_extra` literais — quina de aspas mencionada em Data Handling. Sem injeção de path. ✓
- **A04 Insecure Design (PII):** `LeadCardWidget` exibe nome+DDD+prefixo na UI (necessário). `acc_name` (linha 60-62) inclui PII na propriedade accessibility — mas é local screen-reader, sem persistência externa. ✓
- **A05 Misconfig:** logger config controlado por `utils.logger.get_logger` — module-3 não bypassa; apenas chama com event names + safe extras.
- **A09 Logging Failures:** **Auditoria PII obrigatória** (US-012):
  - grep `logger.\w+\(.*nome|ddd|prefixo|sufixo|desire|info_extra|numero_e164` → **0 matches** ✓
  - Todos os logs usam `extra={"lead_id": ..., "origem": ...}` ou event names puros. Nenhum vazamento de PII detectado.
  - `lead_card._on_submit_clicked` (linha 189) loga apenas `lead_id`. ✓
- **A08 Software & Data Integrity:** Trigger `lead.updated_at` no banco (module-1) — não pode ser bypassado. `LeadStatusGuard.can_transition` valida estado antes de UPDATE. ✓
- **Cryptographic / secrets:** Nenhum segredo no escopo (módulo offline; sem rede, sem hashing). ✓
- **CSRF/XSS/SSRF:** N/A (desktop app, sem HTTP exposto).

## Bare excepts (S110/S112)
- `lead_form.py:160`: `except Exception` em `_on_submit` — captura erros de DB para mostrar QMessageBox crítico ao usuário. **Justificável** (UI handler) e logado via `logger.exception`.
- `tab1_gerar_queries.py:254, 319`: `except Exception` em `finally` para refresh-on-sad-path — também justificável (último recurso para evitar UI travada).

## Issues
- **INFO** Não há Bandit standalone instalado. Sugerir `pip install bandit` no `dev` extras + adicionar passo no CI (já há ruff S*, mas Bandit cobre B604/B605/B608 não cobertos por ruff).
- **INFO** Quina de aspas em `query_generator._render_block` (ver Data Handling) — não é vulnerabilidade no sentido formal mas é input não sanitizado escapando para conteúdo gerado.

## Veredicto
Postura defensiva forte. PII audit limpo. Recomendação: adicionar Bandit ao CI para complementar ruff S*.
