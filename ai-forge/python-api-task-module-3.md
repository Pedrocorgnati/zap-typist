# Python API — module-3-aba1-queries (check mode)

**Status:** N/A

## Justificativa
Aplicação desktop, sem API HTTP exposta. As "interfaces" do módulo são:
- API Python interna (funções públicas: `create_lead`, `generate_queries`, `get_aba1_widget`) — coberta nos audits Architecture e Typing.
- Qt Signals como contratos UI (`submit_requested`, `discard_requested`, `lead_added`, `imbound_query_clicked`) — coberta no Architecture.
- Arquivo de saída `CACHE_DIR/imbound-queries.txt` — formato textual humano determinístico, especificado no INTAKE/FDD.

Não há OpenAPI, REST, GraphQL, webhooks. RFC 7807 não aplicável.

## Veredicto
Não aplicável.
