"""Configuração de paginação para LeadCardList."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LeadCardListConfig:
    """Controla paginação de LeadCardList quando count > 100."""

    page_size: int = 50
    current_page: int = field(default=0)
