"""query_generator — geração determinística de dorks Google a partir de leads pendentes.

Lê leads em ``status=LeadStatus.pendente``, monta blocos no formato exato do INTAKE
(rock-1 §"Módulo Python Embutido: query_generator"), escreve em
``CACHE_DIR/imbound-queries.txt`` e move os leads para ``status=LeadStatus.query_gerada``
em transação atômica.

Determinístico, sem rede, sem LLM, sem randomização. PII nunca aparece em logs.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from zap_typist.config.paths import CACHE_DIR
from zap_typist.db.models import Lead, LeadStatus
from zap_typist.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_FILENAME = "imbound-queries.txt"
DIVIDER_WIDTH = 28
DIVIDER = "═" * DIVIDER_WIDTH


@dataclass(frozen=True)
class GenerationResult:
    leads: int
    queries: int
    output_path: Path
    cancelled: bool = False


def _render_block(lead: Lead) -> tuple[str, int]:
    """Retorna (texto_do_bloco, n_queries_no_bloco)."""
    lines: list[str] = []
    lines.append(f"{lead.nome} | ({lead.ddd}) {lead.prefixo}")
    if lead.desire:
        lines.append(lead.desire)
    main_query = (
        f'"{lead.nome}" '
        f'("{lead.ddd} {lead.prefixo}" OR "({lead.ddd}) {lead.prefixo}")'
    )
    lines.append(main_query)
    n_queries = 1
    if lead.info_extra:
        info_query = (
            f'"{lead.info_extra}" '
            f'("{lead.ddd} {lead.prefixo}" OR "({lead.ddd}) {lead.prefixo}")'
        )
        lines.append(info_query)
        n_queries = 2
    return "\n".join(lines), n_queries


def _render_header(today: date, n_leads: int, n_queries: int) -> str:
    return (
        "IMBOUND — Dorks Google\n"
        f"{today.isoformat()} | {n_leads} leads | {n_queries} queries\n"
        f"{DIVIDER}"
    )


def _render_footer(n_leads: int, n_queries: int) -> str:
    return f"{DIVIDER}\nFIM — {n_leads} leads, {n_queries} queries geradas"


def generate_queries(
    session: Session,
    *,
    today_provider: Callable[[], date] = date.today,
    cancel_check: Callable[[], bool] = lambda: False,
    on_progress: Callable[[str], None] | None = None,
) -> GenerationResult:
    """Gera dorks Google para leads pendentes e grava em CACHE_DIR/imbound-queries.txt."""
    output_path = Path(CACHE_DIR) / OUTPUT_FILENAME

    leads: list[Lead] = (
        session.query(Lead)
        .filter(Lead.status == LeadStatus.pendente)
        .order_by(Lead.id.asc())
        .all()
    )
    n_leads = len(leads)

    if on_progress:
        on_progress(f"Processando {n_leads} leads pendentes...")

    if cancel_check():
        if on_progress:
            on_progress(f"Cancelado pelo usuário ({n_leads} leads não processados).")
        logger.info("query_generation_cancelled", extra={"n_leads": n_leads})
        return GenerationResult(
            leads=0, queries=0, output_path=output_path, cancelled=True
        )

    blocks: list[str] = []
    total_queries = 0
    for lead in leads:
        block, n = _render_block(lead)
        blocks.append(block)
        total_queries += n

    today = today_provider()
    header = _render_header(today, n_leads, total_queries)
    footer = _render_footer(n_leads, total_queries)
    body = "\n\n".join(blocks)
    parts = [header]
    if blocks:
        parts.append(body)
    parts.append(footer)
    file_content = "\n\n".join(parts) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.write_text(file_content, encoding="utf-8")
    except OSError:
        session.rollback()
        logger.exception("query_generation_io_failed", extra={"n_leads": n_leads})
        if on_progress:
            on_progress("Erro: falha ao gravar arquivo de queries.")
        raise

    if leads:
        ids = [lead.id for lead in leads]
        session.query(Lead).filter(Lead.id.in_(ids)).update(
            {Lead.status: LeadStatus.query_gerada}, synchronize_session=False
        )
    session.commit()

    if on_progress:
        if n_leads == 0:
            on_progress("Nenhum lead pendente para processar.")
        on_progress(f"Concluído: {n_leads} leads, {total_queries} queries")

    logger.info(
        "query_generation_done",
        extra={
            "event": "query_generation_done",
            "n_leads": n_leads,
            "n_queries": total_queries,
            "output_path": str(output_path),
        },
    )
    return GenerationResult(
        leads=n_leads, queries=total_queries, output_path=output_path, cancelled=False
    )


__all__ = ["GenerationResult", "generate_queries"]
