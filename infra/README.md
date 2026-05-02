# Infraestrutura — zap-typist

**Ferramenta IaC:** Scripts (Makefile + bash)
**Ambiente:** Dev = Prod (maquina pessoal Ubuntu 22.04 LTS X11)
**Cloud:** Nenhuma — app desktop local, sem servidor, sem containers

---

## Estrutura

```
scripts/
  bootstrap.sh          — Setup inicial do venv (gerado por /dev-bootstrap-create)
  run.sh                — Launcher seguro (SEC-019/020: ulimit + hash check do venv)
  backup_db.sh          — Backup criptografado do DB via GPG (SEC-009)
  health-check.sh       — Verifica saude local: DB, lock, permissoes, disco
Makefile                — Targets de operacao (run, backup, audit-deps, check-venv...)
infra/
  README.md             — Este arquivo
  INFRA-COST-ESTIMATE.md — Estimativa de custos (local = $0)
```

---

## Setup Inicial

```bash
# 1. Clonar e entrar no projeto
git clone git@github.com:Pedrocorgnati/zap-typist.git
cd zap-typist

# 2. Setup completo (cria venv, instala deps, registra hash do venv)
make infra-install
```

O `make infra-install` executa `bootstrap.sh` e registra o hash SHA-256 do `.venv/bin/python`
em `.venv-checksum` — usado pelo `run.sh` para verificar integridade antes de subir o app.

---

## Executar o App

```bash
# Via launcher seguro (recomendado — aplica guardrails SEC-019/020)
make run

# Ou diretamente (sem guardrails)
make dev
```

O `make run` chama `scripts/run.sh` que:
1. Aplica `ulimit -c 0` para desabilitar core dumps (previne vazamento de PII/cookies em crash)
2. Valida hash do `.venv/bin/python` contra `.venv-checksum`
3. Ativa o venv se necessario
4. Executa `python -m zap_typist`

---

## Backup do Banco de Dados

```bash
# Backup no diretorio padrao (~/backups/zap-typist/)
make backup

# Backup em diretorio personalizado
./scripts/backup_db.sh /mnt/usb/backups

# Restaurar backup
gpg --decrypt ~/backups/zap-typist/zap_typist_20260501-120000.db.gpg > restaurado.db
```

**IMPORTANTE:** Nunca copie `~/.local/share/zap-typist/zap_typist.db` raw para storage externo.
Use sempre `make backup` que criptografa com GPG AES-256. O DB contem PII de terceiros (LGPD).

---

## Health Check

```bash
./scripts/health-check.sh
```

Verifica:
- Permissao `0700` no diretorio de dados
- Existencia e integridade do banco (SQLite `PRAGMA integrity_check`)
- Lock file (PID orfao vs app rodando)
- Espaco em disco disponivel
- Diretorio de logs

---

## Auditoria de Dependencias

```bash
make audit-deps
```

Executa `pip-audit` contra `requirements.txt` para detectar CVEs conhecidos em dependencias.
Recomendado rodar mensalmente (THREAT-010/011).

---

## Validar Integridade do Venv

```bash
make check-venv
```

Compara o hash SHA-256 do `.venv/bin/python` atual contra o registrado em `.venv-checksum`.
Se divergir, recriar o venv com `make infra-install`.

---

## Variaveis de Ambiente

| Variavel | Valor | Descricao |
|----------|-------|-----------|
| `VIRTUAL_ENV` | (path do venv) | Ativado automaticamente pelo `run.sh` se ausente |
| `ZAP_DEV` | `1` (opcional) | Habilita modo DEV: log StreamHandler + opcoes de debug |
| `ZAP_LOG_TO_SYSLOG` | `1` (opcional) | Redireciona logs para journald (v1.1+) |

Nenhuma variavel de ambiente contem secrets. O app nao usa credenciais de cloud.

---

## Seguranca

| Controle | Implementado em | Threat |
|----------|-----------------|--------|
| `ulimit -c 0` (sem core dumps) | `scripts/run.sh` | T-024 |
| Hash check do `.venv/bin/python` | `scripts/run.sh` + `make check-venv` | T-025 |
| Backup GPG AES-256 | `scripts/backup_db.sh` | T-013 |
| Permissao `0700` em `APP_DATA_DIR` | `db/session.py:init_database` | T-001/002 |
| Auditoria de CVEs | `make audit-deps` (pip-audit) | T-010/011 |

Ver `output/docs/zap-typist/project/THREAT-MODEL.md` para o modelo completo de ameacas.

---

## Acesso e Credenciais

Nao ha credenciais de infraestrutura. O app e single-user local sem cloud, sem API keys
de servicos externos no skeleton. As unicas credenciais relevantes sao:

- **Sessao WhatsApp** (Rock 3): armazenada nos perfis Chrome em
  `~/.local/share/zap-typist/chrome-profiles/` com permissao `0700`.
  Em caso de suspeita de comprometimento: revogar sessao pelo celular vinculado + novo QR scan.

---

<!-- Gerado por /infra-create em 2026-05-01 a partir de HLD.md, LLD.md e THREAT-MODEL.md -->
