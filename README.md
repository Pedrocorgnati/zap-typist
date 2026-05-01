# Zap Typist

Digitador determinístico de WhatsApp para leads (desktop, Linux/X11).

## Visão geral

App PySide6 + SQLite local, single-user, zero cloud. Opera em 4 abas: gerador de queries (Aba 1), gerador de contatos e mensagens (Aba 2), motor de envio (Aba 3) e central de configurações (Aba 4).

## Pré-requisitos

Ubuntu 22.04 X11, Python 3.11, Chrome instalado. Detalhes completos em INSTALL.md.

## Instalação

```bash
git clone git@github.com:Pedrocorgnati/zap-typist.git
cd zap-typist
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Como rodar

```bash
python -m zap_typist
```

A janela principal abre com 4 abas e a barra de status exibe "DB pronto, 0 leads".

## Comandos disponíveis (Makefile)

Para acelerar o ciclo de desenvolvimento, use o `Makefile` na raiz:

```bash
make setup       # cria .venv, instala dependências (chama scripts/bootstrap.sh)
make dev         # equivale a `python -m zap_typist`
make test        # roda pytest -v
make lint        # ruff check src tests
make type-check  # mypy src
make clean       # remove .venv e caches
make help        # lista todos os targets
```

O `scripts/bootstrap.sh` cuida da criação do venv, instalação editável e checagem de pré-requisitos.

## Estrutura

```
src/zap_typist/
  db/        — modelos SQLAlchemy, session WAL, seed de settings
  ui/        — widgets PySide6
  utils/     — logger com PIIFilter, single-instance lock, cache
  imbound/   — motor de leads (constants, desire rules, templates)
  engine/    — orquestrador de envio
tests/
  unit/      — testes unitários (pytest)
  factories/ — factories para fixtures (pytest)
```

## Testes

```bash
pytest tests/unit/
ruff check src/
mypy src/
```

## Configuração

Copiar `.env.example` para `.env` e preencher as variáveis necessárias.

## Licença

Privado / uso interno.
