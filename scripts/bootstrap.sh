#!/usr/bin/env bash
# bootstrap.sh — Setup completo do ambiente local para zap-typist
# Gerado por /dev-bootstrap-create (SystemForge)
# Uso: ./scripts/bootstrap.sh [--reset] [--health]

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

# Detecta o primeiro binário Python >= 3.11 disponível no PATH.
# Tenta versões explícitas antes do genérico python3 para evitar
# falha silenciosa em máquinas onde python3 aponta para 3.10 ou inferior.
PYTHON_BIN=""
for _py in python3.13 python3.12 python3.11 python3; do
  if command -v "$_py" >/dev/null 2>&1; then
    if "$_py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PYTHON_BIN="$_py"
      break
    fi
  fi
done

APP_DATA_DIR="${HOME}/.local/share/zap-typist"
DB_PATH="${APP_DATA_DIR}/zap_typist.db"

# === Pré-requisitos ===
check_prereqs() {
  log "Verificando pré-requisitos..."
  local missing=()

  command -v git >/dev/null 2>&1 || missing+=("git")

  if [ -z "$PYTHON_BIN" ]; then
    missing+=("python3.11+")
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    err "Faltando: ${missing[*]}"
    if [[ " ${missing[*]} " == *" python3.11+ "* ]]; then
      err "Python 3.11+ é requerido. Instale com:"
      err "  sudo apt install python3.11        # Ubuntu/Debian"
      err "  brew install python@3.11           # macOS"
      err "  sudo dnf install python3.11        # Fedora/RHEL"
    fi
    exit 1
  fi

  local py_version
  py_version=$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  log "Python detectado: $py_version (usando $PYTHON_BIN)"
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
    log "Criando .venv com $PYTHON_BIN..."
    "$PYTHON_BIN" -m venv .venv
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

  # Validar versão do Python dentro da venv recém-ativada.
  # Necessário quando .venv pré-existente foi criado com Python inferior ao requerido.
  if ! python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    local venv_ver
    venv_ver=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    err ".venv existente usa Python $venv_ver (requer 3.11+). Execute:"
    err "  rm -rf .venv && ./scripts/bootstrap.sh"
    exit 1
  fi
}

# === Dependências ===
install_deps() {
  log "Instalando dependências Python..."

  # Verificar que pip está disponível na venv ativa
  if ! python -m pip --version >/dev/null 2>&1; then
    log "pip ausente na venv — instalando via ensurepip..."
    python -m ensurepip --upgrade >/dev/null 2>&1 || {
      err "Não foi possível instalar pip. Execute: python -m ensurepip --upgrade"
      exit 1
    }
  fi

  python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

  if [ -f requirements.txt ]; then
    python -m pip install -r requirements.txt
    ok "Dependências instaladas"
  else
    warn "requirements.txt não encontrado"
  fi
}

# === Banco de dados ===
init_database() {
  log "Verificando banco de dados..."

  # Criar diretório de dados se não existir
  if mkdir -p "$APP_DATA_DIR" 2>/dev/null; then
    ok "Diretório de dados ($APP_DATA_DIR) OK"
  else
    warn "Não foi possível criar diretório de dados"
    return
  fi

  # Tentar inicializar DB se houver um módulo de banco
  if [ -f src/zap_typist/db/__init__.py ] || [ -f src/zap_typist/database.py ]; then
    log "Inicializando esquema do banco..."
    if python -c "from zap_typist import db; db.init()" 2>/dev/null; then
      ok "Banco de dados inicializado"
    else
      # Fallback: apenas criar conexão SQLite (cria o arquivo se não existir)
      if python -c "import sqlite3; sqlite3.connect('${DB_PATH}')" 2>/dev/null; then
        ok "Banco de dados (SQLite) pronto em ${DB_PATH}"
      else
        warn "Não foi possível inicializar banco de dados — execute manualmente se necessário"
      fi
    fi
  else
    # Criar arquivo SQLite vazio
    if python -c "import sqlite3; sqlite3.connect('${DB_PATH}')" 2>/dev/null; then
      ok "Banco de dados (SQLite) pronto em ${DB_PATH}"
    else
      warn "Não foi possível criar arquivo SQLite"
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

  # Verificar dependências instaladas (usa `python` da venv se ativa, senão PYTHON_BIN)
  local _py_check="${VIRTUAL_ENV:+python}"
  _py_check="${_py_check:-${PYTHON_BIN:-python3}}"
  if "$_py_check" -c "import site; site.getsitepackages()" >/dev/null 2>&1; then
    ok "Dependências carregáveis"
  else
    warn "Falha ao carregar dependências"
    errors=$((errors + 1))
  fi

  # Verificar banco de dados
  if [ -f "$DB_PATH" ] || [ -f .env ]; then
    ok "Banco de dados (SQLite) configurado"
  else
    warn "Banco de dados não detectado (será criado na primeira execução)"
  fi

  # Verificar que src/zap_typist é importável
  if python -c "import zap_typist" 2>/dev/null; then
    ok "Módulo zap_typist importável"
  else
    warn "Módulo zap_typist não importável — verifique instalação de dependências"
    errors=$((errors + 1))
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
  echo "    python -m zap_typist"
  echo ""
  echo "  Ou via Makefile:"
  echo "    make dev"
  echo ""
  echo "  Para rodar testes:"
  echo "    source .venv/bin/activate"
  echo "    pytest -v"
  echo ""
  echo "  Ou via Makefile:"
  echo "    make test"
  echo ""
  echo "  Para resetar tudo:"
  echo "    ./scripts/bootstrap.sh --reset"
  echo ""
  echo "  Banco de dados SQLite:"
  echo "    ${DB_PATH}"
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
  rm -f .env 2>/dev/null || true

  # Limpar arquivo .venv-checksum se existir
  rm -f .venv-checksum 2>/dev/null || true

  # Avisar sobre banco de dados
  if [ -f "$DB_PATH" ]; then
    warn "Banco de dados em ${DB_PATH} não foi removido — delete manualmente se necessário"
  fi

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
