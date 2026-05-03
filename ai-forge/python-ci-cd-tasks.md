# Python CI/CD Tasks — zap-typist

**Data:** 2026-05-03

## Pontos fortes confirmados

- 5 jobs bem estruturados: `lint-and-type`, `deps-unused`, `test`, `security-sca`, `secrets-scan`
- Matrix de Python 3.11 e 3.12 para lint e testes
- Actions com hashes SHA pinados (segurança supply chain)
- `concurrency` com `cancel-in-progress: true` para economizar runners
- `permissions: contents: read` (least privilege)
- `needs: lint-and-type` em `test` garante gate de qualidade
- `QT_QPA_PLATFORM: offscreen` para testes Qt headless
- Coverage XML uploadado como artifact

## CICD-001 — MÉDIO — Sem automatização de release e tagging semântico

- **Arquivo:** `.github/workflows/` — nenhum job de release
- **Problema:** não há workflow para criar tags `vX.Y.Z`, gerar CHANGELOG, ou publicar binário/wheel
- **Correção:** criar `.github/workflows/release.yml` com job que roda em push de tag `v*.*.*`; usar `python -m build`, checksums, upload como GitHub Release asset
- **Prioridade:** Médio

## CICD-002 — BAIXO — Coverage report só para Python 3.11

- **Arquivo:** `.github/workflows/ci.yml:89` — `if: always() && matrix.python-version == '3.11'`
- **Problema:** coverage de 3.12 nunca é capturada; pode haver divergência entre versões
- **Correção:** remover condição ou usar `codecov/codecov-action` que agrega os dois
- **Prioridade:** Baixo

## CICD-003 — BAIXO — `pre-commit` não rodado no CI

- **Arquivo:** `.pre-commit-config.yaml` existe mas não é invocado no workflow
- **Problema:** hooks locais podem ser diferentes dos checks do CI; novos contributors podem não ter pre-commit instalado
- **Correção:** adicionar step `pre-commit run --all-files` no job `lint-and-type` usando `pre-commit/action@v3`
- **Prioridade:** Baixo
