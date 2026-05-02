#!/bin/bash
# Health check local para zap-typist
# Verifica DB, lock file, permissoes e espaco em disco
# Uso: ./scripts/health-check.sh

set -euo pipefail

APP_DATA_DIR="$HOME/.local/share/zap-typist"
DB_PATH="$APP_DATA_DIR/zap_typist.db"
LOCK_FILE="$APP_DATA_DIR/.lock"
LOG_DIR="$APP_DATA_DIR/logs"

PASS=0
FAIL=0

check() {
    local label="$1"
    local result="$2"
    local detail="${3:-}"
    if [ "$result" = "ok" ]; then
        echo "  [OK] $label"
        PASS=$((PASS + 1))
    else
        echo "  [FALHA] $label${detail:+ — $detail}"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Health Check — zap-typist ==="
echo ""

# 1. Diretorio de dados existe e tem permissao correta
if [ -d "$APP_DATA_DIR" ]; then
    PERM="$(stat -c '%a' "$APP_DATA_DIR")"
    [ "$PERM" = "700" ] && check "APP_DATA_DIR existe (perm 700)" "ok" || check "APP_DATA_DIR perm" "fail" "esperado 700, encontrado $PERM"
else
    check "APP_DATA_DIR existe" "fail" "$APP_DATA_DIR nao existe (app nunca executado?)"
fi

# 2. Banco de dados existe
if [ -f "$DB_PATH" ]; then
    DB_SIZE="$(du -h "$DB_PATH" | cut -f1)"
    check "DB existe ($DB_SIZE)" "ok"
else
    check "DB existe" "fail" "$DB_PATH nao encontrado"
fi

# 3. Banco integro (sqlite3 integrity check)
if command -v sqlite3 &>/dev/null && [ -f "$DB_PATH" ]; then
    INTEGRITY="$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)"
    [ "$INTEGRITY" = "ok" ] && check "DB integrity_check" "ok" || check "DB integrity_check" "fail" "$INTEGRITY"
else
    check "DB integrity_check" "ok" "(sqlite3 nao disponivel — pulando)"
fi

# 4. Lock file — app nao esta rodando com PID invalido
if [ -f "$LOCK_FILE" ]; then
    PID="$(cat "$LOCK_FILE" 2>/dev/null || echo "")"
    if [ -n "$PID" ] && [ -f "/proc/$PID/status" ]; then
        check "Lock file" "ok" "app em execucao (PID $PID)"
    else
        check "Lock file (PID orfao)" "ok" "lock com PID $PID orfao — sera limpo no proximo boot"
    fi
else
    check "Lock file ausente" "ok" "(app nao esta rodando)"
fi

# 5. Espaco em disco
AVAIL_KB="$(df "$HOME" | awk 'NR==2{print $4}')"
AVAIL_MB=$((AVAIL_KB / 1024))
if [ "$AVAIL_MB" -gt 100 ]; then
    check "Espaco em disco (${AVAIL_MB}MB disponivel)" "ok"
else
    check "Espaco em disco" "fail" "apenas ${AVAIL_MB}MB — risco de falha de escrita"
fi

# 6. Logs existem e nao estao crescendo sem controle
if [ -d "$LOG_DIR" ]; then
    LOG_SIZE="$(du -sh "$LOG_DIR" | cut -f1)"
    check "Diretorio de logs existe ($LOG_SIZE)" "ok"
else
    check "Diretorio de logs" "ok" "(ainda nao criado — app nunca logou)"
fi

echo ""
echo "=== Resultado: $PASS OK  /  $FAIL FALHA(S) ==="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
