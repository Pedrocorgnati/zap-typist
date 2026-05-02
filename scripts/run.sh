#!/bin/bash
# Launcher seguro para zap-typist
# SEC-019: ulimit -c 0 previne core dumps (THREAT-024)
# SEC-020: valida hash do .venv/bin/python antes de subir (THREAT-025)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# --- SEC-019: Desabilitar core dumps ---
ulimit -c 0

# --- SEC-020: Validar integridade do venv ---
if [ -f "$PROJECT_DIR/.venv-checksum" ]; then
    EXPECTED="$(cat "$PROJECT_DIR/.venv-checksum")"
    ACTUAL="$(sha256sum "$PROJECT_DIR/.venv/bin/python" | awk '{print $1}')"
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        echo "ERRO: hash do .venv/bin/python divergiu do registrado em .venv-checksum."
        echo "      O venv pode ter sido comprometido ou atualizado."
        echo "      Execute 'make infra-install' para reregistrar o hash apos atualizar."
        exit 1
    fi
else
    echo "AVISO: .venv-checksum nao encontrado. Execute 'make infra-install' para habilitar o hash check."
fi

# --- Garantir que o venv esta ativado ---
if [ -z "${VIRTUAL_ENV:-}" ]; then
    if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
        echo "ERRO: .venv nao encontrado. Execute 'make infra-install' para configurar."
        exit 1
    fi
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
fi

exec python -m zap_typist "$@"
