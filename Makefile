# Makefile para zap-typist
# Gerado por /dev-bootstrap-create (SystemForge)

.PHONY: setup reset dev test lint type-check clean help

# === Targets de Setup ===
setup:
	@./scripts/bootstrap.sh

reset:
	@./scripts/bootstrap.sh --reset

# === Targets de Desenvolvimento ===
dev:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Ativando virtual environment..."; \
		. .venv/bin/activate; \
	fi; \
	python -m zap_typist

test:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. .venv/bin/activate; \
	fi; \
	pytest -v

# === Targets de Qualidade ===
lint:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. .venv/bin/activate; \
	fi; \
	ruff check src tests

type-check:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. .venv/bin/activate; \
	fi; \
	mypy src

# === Targets de Limpeza ===
clean:
	@rm -rf .venv __pycache__ .mypy_cache .pytest_cache .ruff_cache .coverage
	@rm -rf src/__pycache__ tests/__pycache__
	@echo "Ambiente limpo"

help:
	@echo "Targets disponíveis:"
	@echo "  setup       — Instalar dependências e configurar ambiente"
	@echo "  reset       — Limpar e reinstalar tudo"
	@echo "  dev         — Executar a aplicação"
	@echo "  test        — Rodar testes"
	@echo "  lint        — Verificar código com ruff"
	@echo "  type-check  — Verificar tipos com mypy"
	@echo "  clean       — Limpar caches"
	@echo "  help        — Mostrar esta mensagem"
