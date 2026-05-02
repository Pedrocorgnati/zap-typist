"""Validadores de boundary do dominio Zap Typist."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

_E164_RE = re.compile(r"^\+\d{10,15}$")


def validate_e164(v: str) -> str:
    """Valida que `v` esta em formato E.164 (`+` seguido de 10-15 digitos)."""
    if not _E164_RE.fullmatch(v):
        raise ValueError(f"numero nao esta em E.164: {v!r}")
    return v


PhoneE164 = Annotated[str, AfterValidator(validate_e164)]


__all__ = ["PhoneE164", "validate_e164"]
