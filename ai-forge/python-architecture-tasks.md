# Python Architecture Tasks — zap-typist

**Data:** 2026-05-03

## ARCH-001 — BAIXO — Re-exports de compat em `db/models.py` criando acoplamento transversal

- **Arquivo:** `src/zap_typist/db/models.py:35-46`
- **Problema:** `models.py` re-exporta `APP_DATA_DIR`, `CACHE_DIR`, `DB_PATH`, `LOCK_FILE`, `LOG_DIR` (de `config/paths`) e `RATE_LIMIT_MAX_POR_HORA` (de `domain/constants`) apenas para compatibilidade com consumers antigos; cria acoplamento desnecessário entre camada DB e camadas config/domain
- **Impacto:** qualquer import de `zap_typist.db.models` puxa paths e constants; dificulta teste unitário puro de models
- **Correção:** atualizar os consumers identificados (comentário diz "compat com consumers que ainda importam de zap_typist.db.models") para importar diretamente de `config.paths` e `domain.constants`; remover re-exports após migração
- **Prioridade:** Baixo

## ARCH-002 — BAIXO — `MainWindow.TAB_LABELS` contém lógica de placeholder em UI layer

- **Arquivo:** `src/zap_typist/ui/main_window.py:27-32`
- **Problema:** strings de placeholder ("Em desenvolvimento — aguardando rock N") estão hardcoded na classe UI; deveriam ser controladas por estado de feature flags ou constants
- **Impacto:** acoplamento da UI ao estado de desenvolvimento; dificulta internacionalização futura
- **Correção:** mover strings para `domain/constants.py` ou arquivo de i18n; opcional: usar feature flag para controlar visibilidade dos tabs
- **Prioridade:** Baixo

## ARCH-003 — BAIXO — Sem camada `services/` explícita

- **Arquivo:** estrutura do projeto
- **Problema:** lógica de orquestração ainda não existe (skeleton em desenvolvimento); à medida que os rocks são implementados, risco de lógica de negócio vazar para camada `ui/`
- **Impacto:** violação de SRP quando rocks 1-4 forem implementados
- **Correção:** criar `src/zap_typist/services/` antes de implementar os rocks; cada rock cria seu service correspondente; UI coordena apenas via signals/slots
- **Prioridade:** Baixo (preventivo — aplicar ao implementar rock-1)
