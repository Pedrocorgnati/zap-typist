"""Seed inicial das settings keys `msg_template_1`..`msg_template_5`.

Cada template usa Python str.format placeholders. Lista canonica:
{artigo}, {tratamento}, {primeiro_nome}, {nome_remetente},
{profissao_remetente}, {origem}, {desire_adaptado}, {portfolio_url},
{numero_e164}

Cada template DEVE conter no minimo 3 placeholders distintos da lista canonica.
"""

MSG_TEMPLATE_1 = (
    "Ola, bom dia {tratamento} {primeiro_nome}.\n"
    "Vi {artigo} sua publicacao no {origem}.\n"
    "Sou {nome_remetente}, {profissao_remetente}.\n"
    "Posso te ajudar com {desire_adaptado}?\n"
    "Portfolio: {portfolio_url}"
)

MSG_TEMPLATE_2 = (
    "Oi {primeiro_nome}, tudo bem?\n"
    "Encontrei {artigo} seu pedido no {origem}.\n"
    "Me chamo {nome_remetente} e atuo como {profissao_remetente}.\n"
    "Topa conversar sobre {desire_adaptado}?\n"
    "{portfolio_url}"
)

MSG_TEMPLATE_3 = (
    "{tratamento} {primeiro_nome}, tudo certo?\n"
    "Vi {artigo} sua demanda em {origem} e quis me apresentar.\n"
    "Sou {nome_remetente}, {profissao_remetente}.\n"
    "Tenho experiencia com {desire_adaptado} e posso enviar referencias.\n"
    "Portfolio: {portfolio_url}"
)

MSG_TEMPLATE_4 = (
    "Bom dia {primeiro_nome}!\n"
    "Achei {artigo} sua publicacao no {origem}.\n"
    "Sou {nome_remetente} ({profissao_remetente}) e trabalho exatamente com {desire_adaptado}.\n"
    "Posso enviar uma proposta?\n"
    "{portfolio_url}"
)

MSG_TEMPLATE_5 = (
    "Ola {primeiro_nome}!\n"
    "Vi sua solicitacao no {origem} sobre {desire_adaptado}.\n"
    "Sou {nome_remetente}, {profissao_remetente}, e gostaria de te ajudar.\n"
    "Da uma olhada no meu trabalho: {portfolio_url}"
)
