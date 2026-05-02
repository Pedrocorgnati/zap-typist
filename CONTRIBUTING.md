# Guia de Contribuicao — Zap Typist

## Estrategia de Branches

- `main`: versao estavel local (protegida, requer PR aprovado + CI verde)
- `develop`: integracao (deploy automatico em staging — N/A para app desktop)
- `feature/{descricao}`: features em desenvolvimento (PR para develop)
- `hotfix/{descricao}`: correcoes urgentes (PR direto para main)

## Fluxo de Trabalho

1. Criar branch a partir de `develop`: `git checkout -b feature/minha-feature develop`
2. Implementar mudancas
3. Verificar localmente: `make lint && make type-check && make test`
4. Criar PR para `develop` usando o template fornecido
5. CI deve passar (lint, types, testes com 80% cobertura, SCA, secrets-scan)
6. Aguardar aprovacao
7. Merge para `main` quando pronto para uso

## Setup Local

```bash
git clone git@github.com:Pedrocorgnati/zap-typist.git
cd zap-typist
make setup        # cria .venv e instala dependencias
make dev          # executa a aplicacao
```

## Qualidade

```bash
make lint         # ruff check src tests
make type-check   # mypy src
make test         # pytest -v (coverage >= 80% obrigatorio)
```

## Convencoes de Commits

Usar Conventional Commits:
- `feat:` nova funcionalidade
- `fix:` correcao de bug
- `docs:` apenas documentacao
- `refactor:` sem impacto funcional
- `test:` adicao/correcao de testes
- `chore:` deps, config, build

## Seguranca

- Nunca commitar credenciais, tokens ou PII
- Manter `requirements.txt` atualizado (`pip freeze > requirements.txt` apos mudancas)
- Verificar `pip-audit -r requirements.txt` antes de PRs que alteram dependencias
