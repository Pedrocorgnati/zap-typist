"""Testes da função pura query_generator.generate_queries."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zap_typist.db.models import Base, Lead, LeadStatus
from zap_typist.imbound import query_generator as qg


@pytest.fixture
def Factory(tmp_path, monkeypatch):
    monkeypatch.setattr(qg, "CACHE_DIR", tmp_path)
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _add_lead(session, **kw) -> Lead:
    defaults = dict(
        desire="",
        nome="X",
        ddd="11",
        prefixo="9000",
        info_extra="",
        origem="getNinjas",
        status=LeadStatus.pendente,
    )
    defaults.update(kw)
    lead = Lead(**defaults)
    session.add(lead)
    session.flush()
    return lead


# --- Formato e cabeçalho ---


def test_zero_pending_writes_header_footer_only(Factory):
    with Factory() as s:
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    assert result.leads == 0
    assert result.queries == 0
    content = Path(result.output_path).read_text(encoding="utf-8")
    assert "IMBOUND — Dorks Google" in content
    assert "2026-05-04 | 0 leads | 0 queries" in content
    assert "FIM — 0 leads, 0 queries geradas" in content


def test_one_lead_no_info_extra_renders_one_query(Factory):
    with Factory() as s:
        _add_lead(s, nome="Igor", ddd="21", prefixo="9795", desire="criar site", info_extra="")
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    assert result.leads == 1
    assert result.queries == 1
    content = Path(result.output_path).read_text(encoding="utf-8")
    assert "Igor | (21) 9795" in content
    assert "criar site" in content
    assert '"Igor" ("21 9795" OR "(21) 9795")' in content


def test_one_lead_with_info_extra_renders_two_queries(Factory):
    with Factory() as s:
        _add_lead(s, nome="Maria", ddd="11", prefixo="98765", info_extra="confeiteira")
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    assert result.queries == 2
    content = Path(result.output_path).read_text(encoding="utf-8")
    assert '"Maria" ("11 98765" OR "(11) 98765")' in content
    assert '"confeiteira" ("11 98765" OR "(11) 98765")' in content


def test_lead_without_desire_omits_desire_line(Factory):
    with Factory() as s:
        _add_lead(s, nome="Ana", ddd="31", prefixo="9111", desire="", info_extra="")
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    ana_block = Path(result.output_path).read_text(encoding="utf-8")
    # Bloco tem 2 linhas (header_lead + main_query), sem linha de desire vazia
    assert "Ana | (31) 9111\n\"Ana\"" in ana_block.replace("\r", "")


def test_three_leads_mixed_count_queries(Factory):
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001", info_extra="")
        _add_lead(s, nome="B", ddd="21", prefixo="9002", info_extra="bio")
        _add_lead(s, nome="C", ddd="31", prefixo="9003", info_extra="cargo")
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    assert result.leads == 3
    assert result.queries == 5
    content = Path(result.output_path).read_text(encoding="utf-8")
    assert "3 leads | 5 queries" in content
    assert "FIM — 3 leads, 5 queries geradas" in content


def test_blocks_separated_by_blank_line(Factory):
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001", info_extra="")
        _add_lead(s, nome="B", ddd="21", prefixo="9002", info_extra="")
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    content = Path(result.output_path).read_text(encoding="utf-8")
    # Formato determinístico: último token do bloco A é '("11 9001" OR "(11) 9001")'
    # seguido por \n\n (linha em branco) antes do início do bloco B
    assert '9001")\n\nB |' in content


# --- Estado do banco ---


def test_pending_leads_become_query_gerada(Factory):
    with Factory() as s:
        l1 = _add_lead(s, nome="A", ddd="11", prefixo="9001")
        l2 = _add_lead(s, nome="B", ddd="21", prefixo="9002")
        qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    with Factory() as s:
        statuses = {lead.id: lead.status for lead in s.query(Lead).all()}
        assert statuses[l1.id] == LeadStatus.query_gerada
        assert statuses[l2.id] == LeadStatus.query_gerada


def test_idempotency_skips_query_gerada(Factory):
    # Lead + first generate_queries in same session so commit persists the insert
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001")
        first = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    with Factory() as s:
        second = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    assert first.leads == 1 and first.queries == 1
    assert second.leads == 0 and second.queries == 0


def test_ordering_is_by_id_asc(Factory, tmp_path, monkeypatch):
    monkeypatch.setattr(qg, "CACHE_DIR", tmp_path)
    with Factory() as s:
        _add_lead(s, nome="C", ddd="11", prefixo="9001")
        _add_lead(s, nome="A", ddd="21", prefixo="9002")
        _add_lead(s, nome="B", ddd="31", prefixo="9003")
        qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
        content = Path(qg.CACHE_DIR / qg.OUTPUT_FILENAME).read_text(encoding="utf-8")
    pos_c = content.index("C |")
    pos_a = content.index("A |")
    pos_b = content.index("B |")
    assert pos_c < pos_a < pos_b


def test_other_statuses_are_untouched(Factory):
    with Factory() as s:
        kept = _add_lead(
            s, nome="K", ddd="11", prefixo="9001", status=LeadStatus.descartado
        )
        _add_lead(s, nome="P", ddd="21", prefixo="9002")
        qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    with Factory() as s:
        assert s.query(Lead).filter_by(id=kept.id).one().status == LeadStatus.descartado


# --- Atomicidade e IOError ---


def test_io_error_triggers_rollback(Factory, monkeypatch):
    """IOError no write_text → rollback, DB intacto, exceção propagada, on_progress notificado."""
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001")
        s.commit()

    def _raise_io(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(qg.Path, "write_text", _raise_io)

    msgs: list[str] = []
    with Factory() as s:
        with pytest.raises(OSError, match="disk full"):
            qg.generate_queries(
                s,
                today_provider=lambda: date(2026, 5, 4),
                on_progress=msgs.append,
            )

    # on_progress recebeu mensagem de erro sem PII
    assert any("falha ao gravar" in m for m in msgs)
    for m in msgs:
        assert "9001" not in m  # PII out mesmo em erro
    # DB intacto — lead continua pendente após rollback
    with Factory() as s:
        assert s.query(Lead).filter_by(status=LeadStatus.pendente).count() == 1


# --- Cancelamento ---


def test_cancel_before_processing_returns_cancelled(Factory):
    # Persist lead first (generate_queries won't commit on cancel path)
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001")
        s.commit()
    with Factory() as s:
        result = qg.generate_queries(
            s,
            today_provider=lambda: date(2026, 5, 4),
            cancel_check=lambda: True,
        )
    assert result.cancelled is True
    assert result.leads == 0
    with Factory() as s:
        assert s.query(Lead).filter_by(status=LeadStatus.pendente).count() == 1


# --- US-012: PII em logs ---


def test_logs_no_pii(Factory):
    # get_logger() sets propagate=False, so we install a handler directly
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    target = logging.getLogger("zap_typist.imbound.query_generator")
    target.addHandler(handler)
    try:
        with Factory() as s:
            _add_lead(
                s,
                nome="Igor Confidencial",
                ddd="21",
                prefixo="9795",
                desire="segredo do desire",
                info_extra="info secreta",
            )
            qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
    finally:
        target.removeHandler(handler)

    full = "\n".join(r.getMessage() + str(r.__dict__) for r in records)
    assert "Igor Confidencial" not in full
    assert "segredo do desire" not in full
    assert "info secreta" not in full
    assert "9795" not in full
    assert any("query_generation_done" in r.getMessage() for r in records)


# --- on_progress ---


def test_on_progress_emits_start_and_finish(Factory):
    msgs: list[str] = []
    with Factory() as s:
        _add_lead(s, nome="A", ddd="11", prefixo="9001")
        qg.generate_queries(
            s,
            today_provider=lambda: date(2026, 5, 4),
            on_progress=msgs.append,
        )
    assert any("Processando 1 leads pendentes" in m for m in msgs)
    assert any("Concluído: 1 leads, 1 queries" in m for m in msgs)
    for m in msgs:
        assert "9001" not in m  # PII out


def test_on_progress_zero_pending_emits_friendly_message(Factory):
    msgs: list[str] = []
    with Factory() as s:
        qg.generate_queries(
            s,
            today_provider=lambda: date(2026, 5, 4),
            on_progress=msgs.append,
        )
    assert any("Nenhum lead pendente" in m for m in msgs)


# ---------------------------------------------------------------------------
# ST004 — Performance check de generate_queries com 100 leads (defensivo)
# G1 anti-flakiness: fresh engine por run + warm-up + mediana de 3 runs
# ---------------------------------------------------------------------------

import os  # noqa: E402
import statistics  # noqa: E402
import time  # noqa: E402

PERF_TOLERANCE_FACTOR = float(os.getenv("PERF_TOLERANCE_FACTOR", "1.0"))
BASELINE_100_LEADS_S = 2.0


def _create_fresh_factory(tmp_path):
    """Engine in-memory dedicada por run — sem acúmulo de state entre medições."""
    import uuid
    engine = create_engine(f"sqlite:///{tmp_path / f'perf_{uuid.uuid4().hex}.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_100_leads(session):
    for i in range(100):
        session.add(Lead(
            nome=f"Lead-{i:03d}",
            ddd="11",
            prefixo="98765",
            desire=None,
            info_extra=None,
            status=LeadStatus.pendente,
            origem="test",
        ))
    session.commit()


def _measure_generate(tmp_path, monkeypatch_fn) -> tuple[float, int]:
    """Cria engine fresca, popula com 100 leads, mede generate_queries."""
    import uuid
    cache_dir = tmp_path / f"cache_{uuid.uuid4().hex}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch_fn(qg, "CACHE_DIR", cache_dir)

    factory = _create_fresh_factory(tmp_path)
    with factory() as s:
        _seed_100_leads(s)
        start = time.perf_counter()
        result = qg.generate_queries(s, today_provider=lambda: date(2026, 5, 4))
        elapsed = time.perf_counter() - start
    return elapsed, result.leads


def test_generate_queries_100_leads_under_2s(tmp_path, monkeypatch):
    """generate_queries processa 100 leads em <2s (mediana de 3 runs; defensivo)."""

    def _patch(obj, attr, val):
        monkeypatch.setattr(obj, attr, val)

    # Warm-up
    _measure_generate(tmp_path, _patch)
    # Mediana de 3 runs
    samples = [_measure_generate(tmp_path, _patch) for _ in range(3)]
    elapsed_samples = [s[0] for s in samples]
    median_s = statistics.median(elapsed_samples)
    threshold = BASELINE_100_LEADS_S * PERF_TOLERANCE_FACTOR

    for _elapsed, leads in samples:
        assert leads == 100, f"esperava 100 leads processados, obteve {leads}"

    assert median_s < threshold, (
        f"generate_queries(100 leads) mediana={median_s:.3f}s "
        f"(threshold={threshold:.2f}s = {BASELINE_100_LEADS_S}s"
        f" * tolerance={PERF_TOLERANCE_FACTOR}); "
        f"samples={[f'{s:.3f}' for s in elapsed_samples]}"
    )
