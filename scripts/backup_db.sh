#!/bin/bash
# Backup criptografado do banco de dados zap-typist
# SEC-009: backup com criptografia GPG (THREAT-013)
# Uso: ./scripts/backup_db.sh [destino]
#      destino: diretorio onde salvar o .db.gpg (padrao: ~/backups/zap-typist)

set -euo pipefail

APP_DATA_DIR="$HOME/.local/share/zap-typist"
DB_PATH="$APP_DATA_DIR/zap_typist.db"
BACKUP_DIR="${1:-"$HOME/backups/zap-typist"}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
TMP_COPY="/tmp/zap_typist_backup_$TIMESTAMP.db"
OUTPUT_FILE="$BACKUP_DIR/zap_typist_$TIMESTAMP.db.gpg"

echo "Backup criptografado do banco de dados — zap-typist"
echo "DB de origem : $DB_PATH"
echo "Destino      : $OUTPUT_FILE"
echo ""

# Verificar que o DB existe
if [ ! -f "$DB_PATH" ]; then
    echo "ERRO: banco de dados nao encontrado em $DB_PATH"
    echo "      Certifique-se de que o app foi executado ao menos uma vez."
    exit 1
fi

# Verificar que gpg esta instalado
if ! command -v gpg &>/dev/null; then
    echo "ERRO: gpg nao encontrado. Instale com: sudo apt install gnupg"
    exit 1
fi

# Criar diretorio de destino
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# Copiar DB via sqlite3 .backup (consistente mesmo com WAL ativo)
if command -v sqlite3 &>/dev/null; then
    echo "Copiando DB via sqlite3 .backup (WAL-safe)..."
    sqlite3 "$DB_PATH" ".backup '$TMP_COPY'"
else
    echo "sqlite3 nao encontrado; usando cp (pode ser inconsistente se app estiver rodando)..."
    cp "$DB_PATH" "$TMP_COPY"
fi

# Criptografar com GPG simetrico (AES-256)
echo "Criptografando com GPG (AES256)..."
gpg --symmetric \
    --cipher-algo AES256 \
    --batch \
    --yes \
    --output "$OUTPUT_FILE" \
    "$TMP_COPY"

# Remover copia temporaria
rm -f "$TMP_COPY"

# Verificar que o arquivo foi criado
if [ -f "$OUTPUT_FILE" ]; then
    SIZE="$(du -h "$OUTPUT_FILE" | cut -f1)"
    echo ""
    echo "Backup concluido com sucesso!"
    echo "Arquivo : $OUTPUT_FILE ($SIZE)"
    echo ""
    echo "Para restaurar:"
    echo "  gpg --decrypt $OUTPUT_FILE > zap_typist_restaurado.db"
else
    echo "ERRO: backup falhou — arquivo de saida nao encontrado."
    exit 1
fi
