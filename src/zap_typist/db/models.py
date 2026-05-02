"""Modelos SQLAlchemy 2.x do Zap Typist.

RISCO PII (US-012) — R-05:
---------------------------------
Os campos `leads.nome`, `leads.numero_e164`, `leads.desire`, `leads.info_extra`
e `leads.observacao` armazenam PII de terceiros em cleartext. A protecao se da
exclusivamente pelo filesystem (~/.local/share/zap-typist com permissao 0700).
Nao logar nenhum desses campos. Nao serializar para fora do processo.
Risco aceito e documentado em PRD.md (NFR Seguranca) e THREAT-MODEL.md.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    TypeDecorator,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Re-export de paths e constantes operacionais (compat com consumers que
# ainda importam de zap_typist.db.models). Fontes canonicas:
#   - paths        -> zap_typist.config.paths
#   - operacionais -> zap_typist.domain.constants
from zap_typist.config.paths import APP_DATA_DIR as APP_DATA_DIR
from zap_typist.config.paths import CACHE_DIR as CACHE_DIR
from zap_typist.config.paths import CHROME_PROFILES_DIR as CHROME_PROFILES_DIR
from zap_typist.config.paths import DB_PATH as DB_PATH
from zap_typist.config.paths import LOCK_FILE as LOCK_FILE
from zap_typist.config.paths import LOG_DIR as LOG_DIR
from zap_typist.domain.constants import (
    CONTACT_HISTORY_WINDOW_DAYS as CONTACT_HISTORY_WINDOW_DAYS,
)
from zap_typist.domain.constants import ORIGEM_PADRAO_ABA1 as ORIGEM_PADRAO_ABA1
from zap_typist.domain.constants import RATE_LIMIT_MAX_POR_HORA as RATE_LIMIT_MAX_POR_HORA


def _utc_now() -> datetime:
    """Helper para defaults Python tz-aware. UTC e politica do projeto."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """DateTime que preserva UTC em SQLite (que nao armazena tz nativamente).

    On bind: normaliza aware->UTC e escreve naive UTC (formato ISO sem offset).
    On result: re-anexa tzinfo=UTC ao naive lido do banco.
    Politica do projeto: todo timestamp e UTC; conversao para horario local
    acontece apenas na UI.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            # Aceita naive como UTC (tolerante para defaults SQL legacy).
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy 2.x."""


# ---------------------------------------------------------------------------
# Enums (INT-028, INT-031)
# ---------------------------------------------------------------------------


class LeadStatus(enum.StrEnum):
    """Estado do ciclo de vida de um lead (10 valores canonicos)."""

    pendente = "pendente"
    query_gerada = "query_gerada"
    telefone_preenchido = "telefone_preenchido"
    descartado = "descartado"
    mensagem_pronta = "mensagem_pronta"
    whatsapp_inexistente = "whatsapp_inexistente"
    whatsapp_valido = "whatsapp_valido"
    enviado = "enviado"
    falhou = "falhou"
    invalido = "invalido"


class FlowMode(enum.StrEnum):
    """Modo de operacao de um fluxo de envio (2 valores canonicos)."""

    manual = "manual"
    automatico = "automatico"


# ---------------------------------------------------------------------------
# Modelos (LLD §2.1, INT-027..INT-032)
# ---------------------------------------------------------------------------


class Lead(Base):
    """Registro de um lead capturado via Aba 1 (query) ou importado."""

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendente','query_gerada','telefone_preenchido',"
            "'descartado','mensagem_pronta','whatsapp_inexistente',"
            "'whatsapp_valido','enviado','falhou','invalido')",
            name="ck_leads_status_enum",
        ),
        # E.164: '+' seguido de 10-15 digitos. SQLite GLOB nao valida tamanho;
        # length() complementa. Validacao forte ocorre no boundary Pydantic.
        CheckConstraint(
            "numero_e164 IS NULL OR ("
            "  numero_e164 GLOB '+[0-9]*' "
            "  AND length(numero_e164) BETWEEN 11 AND 16"
            ")",
            name="ck_leads_numero_e164_format",
        ),
        Index("idx_leads_status", "status"),
        Index("idx_leads_numero_e164", "numero_e164"),
        Index("idx_leads_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    desire: Mapped[str | None] = mapped_column(Text, nullable=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    ddd: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefixo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sufixo: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_e164: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default=LeadStatus.pendente.value)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    send_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class Setting(Base):
    """Par chave/valor de configuracao persistida (Aba 4)."""

    __tablename__ = "settings"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class Flow(Base):
    """Fluxo de envio configurado pelo usuario (Aba 3)."""

    __tablename__ = "flows"
    __table_args__ = (
        CheckConstraint("mode IN ('manual','automatico')", name="ck_flows_mode_enum"),
        CheckConstraint(
            f"rate_limit_per_hour <= {RATE_LIMIT_MAX_POR_HORA}",
            name="ck_flows_rate_limit_max",
        ),
        CheckConstraint(
            "json_valid(time_window_days) AND json_type(time_window_days) = 'array'",
            name="ck_flows_time_window_days_json",
        ),
        Index("idx_flows_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    chrome_profile: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    time_window_days: Mapped[str] = mapped_column(Text, nullable=False)
    time_window_start: Mapped[str] = mapped_column(Text, nullable=False)
    time_window_end: Mapped[str] = mapped_column(Text, nullable=False)
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_min_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_max_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_batch_pause_min: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_limit_batch_pause_max: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    is_paused: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_lead_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )

    contact_history: Mapped[list[ContactHistory]] = relationship(back_populates="flow")


class ContactHistory(Base):
    """Registro de contato enviado (janela de 60 dias, INT-032)."""

    __tablename__ = "contact_history"
    __table_args__ = (
        Index(
            "idx_contact_history_numero_touched",
            "numero_e164",
            text("touched_at DESC"),
        ),
        Index("idx_contact_history_flow_id", "flow_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_e164: Mapped[str] = mapped_column(Text, nullable=False)
    flow_id: Mapped[int] = mapped_column(Integer, ForeignKey("flows.id"), nullable=False)
    touched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=_utc_now)

    flow: Mapped[Flow] = relationship(back_populates="contact_history")


# ---------------------------------------------------------------------------
# Politica de timestamps (D-01, ADR pendente):
#   - Todos os DateTime sao timezone=True; armazenamento em UTC (politica unica).
#   - Inserts e updates usam Python `default=_utc_now` / `onupdate=_utc_now`,
#     substituindo os triggers SQL CURRENT_TIMESTAMP que produziam naive UTC.
#   - DBs migrados de v1.0.0 (timestamps naive em texto) sao reescritos pelo
#     script `MIGRATION-v1.0.1.py` antes do primeiro boot pos-upgrade.
# ---------------------------------------------------------------------------
