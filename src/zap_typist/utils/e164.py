"""Normalização E.164 brasileira para campos do Lead.

Contrato C2 do module-2-shared-foundations. Consumido por modules 3, 4, 6a.
Função pura: sem I/O, sem logging, sem dependência externa.
"""
from __future__ import annotations

import re

# DDDs ativos pela ANATEL (67 valores). Fonte: gov.br/anatel/pt-br/regulado/numeracao
# Última atualização: 2026-04-30. Adicionar aqui quando ANATEL alocar novo DDD.
_DDD_VALID: frozenset[str] = frozenset({
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
})

_STRIP_RE = re.compile(r"[\s\-\(\)\+]")
_BR_COUNTRY = "55"

# Nome público canônico (contrato C2); alias de _DDD_VALID para import externo.
DDDS_VALIDOS_BR: frozenset[str] = _DDD_VALID

__all__ = [
    "DDDS_VALIDOS_BR",
    "_DDD_VALID",
    "e164_from_lead_fields",
    "format_e164",
    "parse_raw_phone",
    "validate_e164",
]


def format_e164(ddd: str, prefixo: str, sufixo: str) -> str | None:
    """Monta número E.164 a partir dos campos do Lead.

    Args:
        ddd: 2 dígitos do DDD (ex: "11").
        prefixo: 4 ou 5 primeiros dígitos do número (ex: "98765" para móvel).
        sufixo: últimos 4 dígitos (ex: "4321").

    Returns:
        String no formato "+55{ddd}{numero}" ou None se algum campo for inválido.
    """
    ddd = ddd.strip()
    prefixo = prefixo.strip()
    sufixo = sufixo.strip()

    if ddd not in _DDD_VALID:
        return None
    if not prefixo.isdigit() or not sufixo.isdigit():
        return None
    if len(sufixo) < 4:
        return None

    numero = prefixo + sufixo
    if len(numero) not in (8, 9):
        return None
    if len(numero) == 9 and numero[0] != "9":
        return None

    return f"+{_BR_COUNTRY}{ddd}{numero}"


def validate_e164(phone: str) -> bool:
    """Valida se a string já está no formato E.164 brasileiro.

    Args:
        phone: String a validar.

    Returns:
        True se o formato for +55 seguido de 10 ou 11 dígitos.
    """
    if not phone.startswith("+55"):
        return False
    digits = phone[1:]
    return digits.isdigit() and len(digits) in (12, 13)


def parse_raw_phone(raw: str) -> tuple[str, str, str] | None:
    """Tenta extrair (ddd, prefixo, sufixo) de string com formatação livre.

    Aceita "+55 (11) 9 8765-4321", "(11) 98765-4321", "11987654321" etc.
    Retorna None se não conseguir parsear.

    Args:
        raw: String bruta com número de telefone.

    Returns:
        Tupla (ddd, prefixo, sufixo) ou None se o formato for inválido.
    """
    cleaned = _STRIP_RE.sub("", raw)
    if cleaned.startswith("55") and len(cleaned) > 11:
        cleaned = cleaned[2:]
    if not cleaned.isdigit():
        return None
    if len(cleaned) not in (10, 11):
        return None
    ddd = cleaned[:2]
    numero = cleaned[2:]
    if ddd not in _DDD_VALID:
        return None
    if len(numero) == 9:
        return ddd, numero[:5], numero[5:]
    return ddd, numero[:4], numero[4:]


def e164_from_lead_fields(ddd: str, prefixo: str, sufixo: str) -> str:
    """Versão estrita de format_e164: levanta ValueError em vez de retornar None.

    Args:
        ddd: 2 dígitos do DDD.
        prefixo: 4 ou 5 primeiros dígitos do número.
        sufixo: últimos 4 dígitos.

    Returns:
        String E.164 no formato "+55{ddd}{numero}".

    Raises:
        ValueError: Se qualquer campo for inválido.
    """
    result = format_e164(ddd, prefixo, sufixo)
    if result is None:
        raise ValueError(
            f"Campos inválidos para E.164: ddd={ddd!r}, prefixo={prefixo!r}, sufixo={sufixo!r}"
        )
    return result
