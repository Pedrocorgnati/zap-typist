#!/usr/bin/env bash
# SLO Check — Zap Typist
# Verifica conformidade com os SLOs definidos em docs/project/SLO.md
# Uso: ./scripts/slo-check.sh
# Saida: 0 = nenhuma violacao | 1 = violacoes encontradas
#
# Instalar em ~/.local/share/zap-typist/slo-check.sh para uso ad-hoc:
#   cp scripts/slo-check.sh ~/.local/share/zap-typist/slo-check.sh
#   chmod +x ~/.local/share/zap-typist/slo-check.sh

set -euo pipefail

LOG="$HOME/.local/share/zap-typist/logs/zap-typist.log"
DB="$HOME/.local/share/zap-typist/zap_typist.db"
THIS_MONTH=$(date +%Y-%m)
VIOLATIONS=0

echo "=== SLO Check — Zap Typist === $(date)"
echo "Mes de referencia: $THIS_MONTH"
echo ""

# ─── SLO 1: app-boot — latencia < 3000ms, max 1 falha/mes ───────────────────
echo "[app-boot] Verificando startups com latencia > 3s..."
if [ -f "$LOG" ]; then
    SLOW_BOOTS=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "app_started" and (.ts | startswith($m)) and .duration_ms > 3000) | .duration_ms' \
        "$LOG" 2>/dev/null | wc -l)
    if [ "$SLOW_BOOTS" -gt 1 ]; then
        echo "  [WARN] $SLOW_BOOTS boot(s) acima de 3s este mes (budget: <= 1)"
        VIOLATIONS=$((VIOLATIONS + 1))
    elif [ "$SLOW_BOOTS" -eq 1 ]; then
        echo "  [WARN] 1 boot acima de 3s este mes (budget consumido — monitorar)"
    else
        echo "  [OK] Todos os boots dentro de 3s"
    fi
else
    echo "  [INFO] Log nao encontrado — app nunca executado"
fi

# ─── SLO 2: db-init-rerun — latencia < 200ms, max 1 falha/mes ───────────────
echo "[db-init-rerun] Verificando validacoes de schema > 200ms..."
if [ -f "$LOG" ]; then
    SLOW_DBREINIT=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "db_validated" and (.ts | startswith($m)) and .duration_ms > 200) | .duration_ms' \
        "$LOG" 2>/dev/null | wc -l)
    if [ "$SLOW_DBREINIT" -gt 1 ]; then
        echo "  [WARN] $SLOW_DBREINIT validacao(oes) de schema acima de 200ms (budget: <= 1)"
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo "  [OK] Re-init de DB dentro de 200ms"
    fi
fi

# ─── SLO 3: worker-execution — taxa de falha < 2% (max 2 falhas/mes) ─────────
echo "[worker-execution] Verificando falhas de worker este mes..."
if [ -f "$LOG" ]; then
    WORKER_TOTAL=$(jq -r --arg m "$THIS_MONTH" \
        'select((.event == "worker_completed" or .event == "worker_failed") and (.ts | startswith($m))) | .event' \
        "$LOG" 2>/dev/null | wc -l)
    WORKER_FAILED=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "worker_failed" and (.ts | startswith($m))) | .event' \
        "$LOG" 2>/dev/null | wc -l)
    if [ "$WORKER_TOTAL" -gt 0 ]; then
        echo "  Workers: $WORKER_FAILED falhas / $WORKER_TOTAL execucoes"
        if [ "$WORKER_FAILED" -gt 2 ]; then
            echo "  [WARN] Mais de 2 falhas de worker este mes — revisar logs (budget: <= 2)"
            VIOLATIONS=$((VIOLATIONS + 1))
        else
            echo "  [OK] Taxa de falha dentro do SLO (< 2%)"
        fi
    else
        echo "  [INFO] Sem execucoes de worker registradas este mes"
    fi
fi

# ─── SLO 4: single-instance — tolerancia zero ────────────────────────────────
echo "[single-instance] Verificando tentativas de segunda instancia..."
if [ -f "$LOG" ]; then
    BLOCKED=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "single_instance_lock_blocked" and (.ts | startswith($m))) | .event' \
        "$LOG" 2>/dev/null | wc -l)
    echo "  $BLOCKED tentativa(s) de segunda instancia bloqueada(s)"
    ORPHANS=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "single_instance_orphan_detected" and (.ts | startswith($m))) | .event' \
        "$LOG" 2>/dev/null | wc -l)
    if [ "$ORPHANS" -gt 0 ]; then
        echo "  [INFO] $ORPHANS lock(s) orfao(s) detectado(s) na boot — normal apos kill -9"
    fi
fi

# ─── SLO 5: crash-recovery — integridade do SQLite ───────────────────────────
echo "[crash-recovery] Verificando integridade do SQLite..."
if command -v sqlite3 &>/dev/null && [ -f "$DB" ]; then
    INTEGRITY=$(sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null || echo "ERRO")
    if [ "$INTEGRITY" = "ok" ]; then
        echo "  [OK] integrity_check = ok"
    else
        echo "  [CRITICAL] integrity_check falhou: $INTEGRITY"
        echo "  ACAO IMEDIATA: backup do DB e investigacao de corrupcao"
        echo "  Executar: ./scripts/backup_db.sh"
        VIOLATIONS=$((VIOLATIONS + 3))
    fi
else
    echo "  [INFO] sqlite3 nao disponivel ou DB nao encontrado — pulando"
fi

# ─── SLO 6: WAL mode ativo ───────────────────────────────────────────────────
echo "[db-wal] Verificando WAL mode..."
if command -v sqlite3 &>/dev/null && [ -f "$DB" ]; then
    WAL=$(sqlite3 "$DB" "PRAGMA journal_mode;" 2>/dev/null || echo "ERRO")
    if [ "$WAL" = "wal" ]; then
        echo "  [OK] journal_mode = wal"
    else
        echo "  [WARN] journal_mode = $WAL (esperado: wal)"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
fi

# ─── SLO 7: db-lock retries — indicador de contencao ────────────────────────
echo "[db-lock-retry] Verificando retries de lock este mes..."
if [ -f "$LOG" ]; then
    LOCK_RETRIES=$(jq -r --arg m "$THIS_MONTH" \
        'select(.event == "db_lock_retry" and (.ts | startswith($m))) | .attempt' \
        "$LOG" 2>/dev/null | wc -l)
    if [ "$LOCK_RETRIES" -gt 5 ]; then
        echo "  [WARN] $LOCK_RETRIES retries de DB lock este mes — possivel contencao de escrita"
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo "  [OK] $LOCK_RETRIES retries (dentro do normal)"
    fi
fi

echo ""
echo "=== Resultado: $VIOLATIONS violacao(oes) de SLO detectada(s) ==="
if [ "$VIOLATIONS" -gt 0 ]; then
    echo "Consulte output/docs/zap-typist/project/SLO.md para politica de acao."
    exit 1
fi
exit 0
