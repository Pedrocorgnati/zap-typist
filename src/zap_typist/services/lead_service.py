"""Service para operações de domínio sobre Lead."""
from __future__ import annotations

from sqlalchemy.orm import Session

from zap_typist.db.models import Lead, LeadStatus, Setting
from zap_typist.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ORIGIN_KEY = "default_aba1_origin"
FALLBACK_ORIGIN = "getNinjas"


def _read_default_origin(session: Session) -> str:
    """Lê settings.default_aba1_origin em runtime; fallback se ausente."""
    setting = session.query(Setting).filter_by(name=DEFAULT_ORIGIN_KEY).one_or_none()
    if setting is None or not setting.value:
        logger.warning(
            "default_origin_missing",
            extra={"key": DEFAULT_ORIGIN_KEY, "fallback": FALLBACK_ORIGIN},
        )
        return FALLBACK_ORIGIN
    return setting.value


def create_lead(
    session: Session,
    *,
    desire: str,
    nome: str,
    ddd: str,
    prefixo: str,
    info_extra: str,
) -> Lead:
    """INSERT um novo Lead em status=pendente, com origem lida das settings.

    Não loga valores PII (nome/ddd/prefixo/info_extra) — apenas evento e id.
    """
    origem = _read_default_origin(session)
    lead = Lead(
        desire=desire.strip() or None,
        nome=nome.strip(),
        ddd=ddd.strip(),
        prefixo=prefixo.strip(),
        info_extra=info_extra.strip() or None,
        origem=origem,
        status=LeadStatus.pendente,
    )
    session.add(lead)
    session.flush()  # garante lead.id antes de logar
    logger.info("lead_added", extra={"lead_id": lead.id, "origem": origem})
    session.commit()
    return lead
