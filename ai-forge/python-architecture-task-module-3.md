# Python Architecture — module-3-aba1-queries (check mode)

**Status:** OK
**Tool:** análise estrutural manual

## Camadas (de baixo para cima)
1. `db.models` (`Lead`, `LeadStatus`, `Setting`) — module-1.
2. `domain.constants` (`ORIGEM_PADRAO_ABA1`) — module-2.
3. `services.lead_service.create_lead` — orquestra ORM + settings.
4. `imbound.query_generator.generate_queries` — pure-ish (entrada session, side effect: arquivo + UPDATE batch).
5. `engine.query_generator_worker.QueryGeneratorWorker` — extends `engine.base_worker.BaseWorker` (module-2 contract).
6. `ui.aba1.lead_form.LeadFormWidget` → chama `services.create_lead`.
7. `ui.aba1.lead_card.LeadCardWidget` → puro (não toca DB; emite signals).
8. `ui.aba1.lead_card_list.LeadCardList` → consulta read-only (count + select page).
9. `ui.tab1_gerar_queries.Tab1GerarQueriesWidget` → orchestrator: fan-in de signals, único ponto que faz UPDATE de status (Submit/Discard) e chama `LeadStatusGuard`.

## Pontos fortes
- Separação clara `imbound` (geração pura) ↔ `engine` (Qt wrapper) ↔ `ui` (UI). `query_generator.py` não importa Qt — testável sem QApplication.
- DI via `session_factory` em todos os widgets que tocam DB (lead_form, tab1).
- `_ScopedSessionFactory` Protocol desacopla widget do tipo concreto `scoped_session`.
- Política rígida: somente `Tab1GerarQueriesWidget` faz UPDATE de status; `LeadCardWidget` apenas emite sinais (princípio: card é dumb view).

## Imports circulares
Nenhum detectado. Direção: `ui → services → db`, `ui → engine → imbound → db`. Sem ciclos.

## Issues
- **INFO** `LeadCardWidget._lead.id` é acessado em `LeadCardList.find_card_by_id` via atributo privado (`widget._lead.id` — `lead_card_list.py:87`). Quebra encapsulamento. Opções: expor `lead_id` property em `LeadCardWidget`, ou aceitar como deliberado (mesmo módulo, baixo blast-radius).
- **INFO** `Tab1GerarQueriesWidget._on_card_submit` tem 80 linhas e múltiplos returns precoces — alta complexidade ciclomática. Funciona porque cada early-return define `refresh_needed=True` e relegada ao `finally`. Considerar extrair `_validate_and_prepare(lead, sufixo) -> Optional[Tuple[Lead, str]]` para SRP. Não bloqueador.

## Veredicto
Arquitetura limpa, dependências inversas isoladas, testabilidade alta. 2 melhorias de leitura/encapsulamento opcionais.
