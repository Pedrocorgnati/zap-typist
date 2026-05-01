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
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    DDL,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy 2.x."""


# ---------------------------------------------------------------------------
# Constantes de path (XDG, HLD §APP_DATA_DIR, INT-034)
# ---------------------------------------------------------------------------

_DATA_DIR_OVERRIDE = os.environ.get("ZAP_TYPIST_DATA_DIR")
APP_DATA_DIR: Path = (
    Path(_DATA_DIR_OVERRIDE).expanduser().resolve()
    if _DATA_DIR_OVERRIDE
    else Path.home() / ".local" / "share" / "zap-typist"
)
CACHE_DIR: Path = APP_DATA_DIR / "cache"
DB_PATH: Path = APP_DATA_DIR / "zap_typist.db"
CHROME_PROFILES_DIR: Path = APP_DATA_DIR / "chrome-profiles"
LOCK_FILE: Path = APP_DATA_DIR / ".lock"
LOG_DIR: Path = APP_DATA_DIR / "logs"

# ---------------------------------------------------------------------------
# Constantes operacionais (PRD/HLD, FEAT-skel-043)
# ---------------------------------------------------------------------------

RATE_LIMIT_MAX_POR_HORA: int = 30
CONTACT_HISTORY_WINDOW_DAYS: int = 60
ORIGEM_PADRAO_ABA1: str = "getNinjas"


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
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=LeadStatus.pendente.value
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    send_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Setting(Base):
    """Par chave/valor de configuracao persistida (Aba 4)."""

    __tablename__ = "settings"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
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
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_lead_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
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
    touched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    flow: Mapped[Flow] = relationship(back_populates="contact_history")


# ---------------------------------------------------------------------------
# Triggers updated_at (via DDL event, FEAT-skel-034)
# contact_history nao tem updated_at — registro append-only
# ---------------------------------------------------------------------------

_UPDATED_AT_TRIGGERS = [
    ("leads", "id"),
    ("settings", "name"),
    ("flows", "id"),
]
for _table, _pk in _UPDATED_AT_TRIGGERS:
    event.listen(
        Base.metadata,
        "after_create",
        DDL(
            f"CREATE TRIGGER IF NOT EXISTS trg_{_table}_updated_at "
            f"AFTER UPDATE ON {_table} FOR EACH ROW BEGIN "
            f"UPDATE {_table} SET updated_at = CURRENT_TIMESTAMP "
            f"WHERE {_pk} = OLD.{_pk}; END;"
        ),
    )
