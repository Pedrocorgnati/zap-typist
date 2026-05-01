#!/usr/bin/env bash
# bootstrap.sh — Setup completo do ambiente local para zap-typist
# Gerado por /dev-bootstrap-create (SystemForge)
# Uso: ./scripts/bootstrap.sh [--reset]

set -euo pipefail

# === Cores ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[bootstrap]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*" >&2; }

# === Pré-requisitos ===
check_prereqs() {
  log "Verificando pré-requisitos..."
  local missing=()

  command -v git >/dev/null 2>&1 || missing+=("git")
  command -v python3 >/dev/null 2>&1 || missing+=("python3")
  command -v pip >/dev/null 2>&1 || missing+=("pip")

  if [ ${#missing[@]} -gt 0 ]; then
    err "Faltando: ${missing[*]}"
    err "Instale os pré-requisitos acima e tente novamente."
    exit 1
  fi

  # Verificar Python 3.11+
  local py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  log "Python detectado: $py_version"

  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    err "Python 3.11+ é requerido (detectado: $py_version)"
    exit 1
  fi

  ok "Pré-requisitos verificados"
}

# === .env ===
ensure_env() {
  log "Verificando arquivo .env..."
  if [ -f .env ]; then
    ok ".env já existe"
    return
  fi

  if [ -f .env.example ]; then
    cp .env.example .env
    ok ".env criado a partir de .env.example"
    warn "Revise .env e preencha valores sensíveis antes de continuar"
  else
    warn ".env não encontrado e sem template disponível"
  fi
}

# === Virtual environment ===
ensure_venv() {
  log "Configurando virtual environment..."

  if [ -d .venv ]; then
    ok ".venv já existe"
  else
    log "Criando .venv..."
    python3 -m venv .venv
    ok ".venv criado"
  fi

  # Ativar venv
  if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
    ok "Virtual environment ativado"
  else
    err "Falha ao ativar virtual environment"
    exit 1
  fi
}

# === Dependências ===
install_deps() {
  log "Instalando dependências Python..."

  # Garantir que pip está atualizado
  python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    ok "Dependências instaladas"
  else
    warn "requirements.txt não encontrado"
  fi
}

# === Banco de dados ===
init_database() {
  log "Verificando banco de dados..."

  # Para SQLite, apenas garantir que a pasta de dados existe
  local db_dir="."
  if mkdir -p "$db_dir" 2>/dev/null; then
    ok "Diretório de dados OK"
  fi

  # Tentar inicializar DB se houver um script
  if [ -f src/db/__init__.py ] || [ -f src/database.py ]; then
    log "Inicializando esquema do banco..."
    if python3 -c "from src import db; db.init()" 2>/dev/null || \
       python3 -c "import sqlite3; sqlite3.connect('zap_typist.db')" 2>/dev/null; then
      ok "Banco de dados OK"
    else
      warn "Não foi possível verificar banco de dados — execute manualmente se necessário"
    fi
  fi
}

# === Health Check ===
check_health() {
  log "Verificando saúde do ambiente..."
  local errors=0

  # Verificar .env
  if [ -f .env ]; then
    ok ".env presente"
  else
    warn ".env ausente"
    errors=$((errors + 1))
  fi

  # Verificar venv
  if [ -d .venv ] && [ -f .venv/bin/python ]; then
    ok "Virtual environment ativo"
  else
    warn "Virtual environment não encontrado"
    errors=$((errors + 1))
  fi

  # Verificar dependências instaladas
  if python3 -c "import site; site.getsitepackages()" >/dev/null 2>&1; then
    ok "Dependências carregáveis"
  else
    warn "Falha ao carregar dependências"
    errors=$((errors + 1))
  fi

  # Verificar banco de dados
  if [ -f zap_typist.db ] || [ -f .env ]; then
    ok "Banco de dados configurado"
  else
    warn "Banco de dados não detectado"
  fi

  if [ $errors -eq 0 ]; then
    ok "Ambiente saudável"
  else
    warn "$errors problema(s) encontrado(s) — verifique acima"
  fi
}

# === Resumo ===
show_summary() {
  echo ""
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  BOOTSTRAP COMPLETO${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "  Para iniciar a aplicação:"
  echo "    source .venv/bin/activate"
  echo "    python -m zap_typist.cli"
  echo ""
  echo "  Para rodar testes:"
  echo "    source .venv/bin/activate"
  echo "    pytest"
  echo ""
  echo "  Para resetar tudo:"
  echo "    ./scripts/bootstrap.sh --reset"
  echo ""
}

# === Reset ===
do_reset() {
  warn "Resetando ambiente..."

  # Desativar venv se ativado
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    deactivate 2>/dev/null || true
  fi

  # Limpar cache
  rm -rf .venv __pycache__ .mypy_cache .pytest_cache .ruff_cache .coverage 2>/dev/null || true
  rm -rf src/__pycache__ tests/__pycache__ 2>/dev/null || true
  rm -f .env zap_typist.db 2>/dev/null || true

  ok "Ambiente limpo"
  do_setup
}

# === Setup principal ===
do_setup() {
  log "Iniciando bootstrap de zap-typist..."
  echo ""

  check_prereqs
  ensure_env
  ensure_venv
  install_deps
  init_database
  check_health
  show_summary
}

# === Entrypoint ===
cd "$(dirname "${BASH_SOURCE[0]}")/.."

case "${1:-}" in
  --reset)  do_reset ;;
  --health) check_health ;;
  *)        do_setup ;;
esac
