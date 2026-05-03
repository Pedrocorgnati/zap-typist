# Python Testing Tasks — zap-typist

**Data:** 2026-05-03
**Cobertura atual:** 95.1% (acima do mínimo de 80%)

## Pontos fortes confirmados

- Testes separados em `unit/` e `integration/`
- `conftest.py` com fixtures de rollback automático (`db_session.rollback()` no finally)
- `seeded_session` fixture com monkeypatch correto
- FactoryBoy em `tests/factories/`
- Markers declarados: `unit`, `integration`, `qt`, `boot`
- `pytest-qt` para testes de widget com `QT_QPA_PLATFORM=offscreen` no CI
- Property-based tests com `hypothesis` em `test_e164_property.py`
- `--cov-fail-under=80` enforced; cobertura real de 95.1%

## TEST-001 — BAIXO — `src/zap_typist/ui/**` excluído da cobertura

- **Arquivo:** `pyproject.toml:[tool.coverage.run]` — `omit = ["src/zap_typist/ui/**"]`
- **Problema:** camada de UI completamente fora da métrica de cobertura; quando os rocks implementarem widgets reais, o omit vai esconder gaps
- **Correção:** manter omit para `main_window.py` e `dialogs.py` (difíceis de testar unitariamente), mas remover o wildcard genérico; adicionar testes de widgets via `pytest-qt` para `form_validators.py` e `terminal_widget.py`
- **Prioridade:** Baixo

## TEST-002 — BAIXO — `hypothesis` não tem profile limitado no CI

- **Arquivo:** `pyproject.toml:[tool.pytest.ini_options]`
- **Problema:** sem `HYPOTHESIS_MAX_EXAMPLES` configurado, testes de property podem ser lentos em CI
- **Correção:** adicionar `env = ["HYPOTHESIS_MAX_EXAMPLES=50"]` no job de CI ou configurar `settings.suppress_health_check` em conftest para CI
- **Prioridade:** Baixo

## TEST-003 — BAIXO — Testes de `seeded_session` não testam `build_settings_defaults` diretamente

- **Arquivo:** `tests/conftest.py` — `seeded_session`
- **Problema:** fixture usa `run_seed(force=True)` sem `defaults=build_settings_defaults()`; pode mascarar divergência entre defaults e seed
- **Correção:** passar `defaults=build_settings_defaults()` explicitamente (como em `app._boot_db()`): `run_seed(defaults=build_settings_defaults(), force=True)`
- **Prioridade:** Baixo
