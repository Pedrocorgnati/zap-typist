# Makefile para zap-typist
# Gerado por /dev-bootstrap-create (SystemForge)
# Atualizado por /infra-create (SystemForge)

APP_DATA_DIR := $(HOME)/.local/share/zap-typist
DB_PATH      := $(APP_DATA_DIR)/zap_typist.db

.PHONY: setup reset dev run test lint type-check audit-deps check-venv backup infra-install clean help

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

run:
	@./scripts/run.sh

backup:
	@./scripts/backup_db.sh

audit-deps:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		. .venv/bin/activate; \
	fi; \
	pip-audit --requirement requirements.txt

check-venv:
	@if [ ! -f .venv-checksum ]; then \
		echo "AVISO: .venv-checksum nao encontrado. Execute 'make infra-install' primeiro."; \
	else \
		EXPECTED=$$(cat .venv-checksum); \
		ACTUAL=$$(sha256sum .venv/bin/python | awk '{print $$1}'); \
		if [ "$$EXPECTED" != "$$ACTUAL" ]; then \
			echo "ERRO: hash do .venv/bin/python divergiu! Recrie o venv."; \
			exit 1; \
		else \
			echo "venv OK"; \
		fi; \
	fi

infra-install:
	@./scripts/bootstrap.sh
	@sha256sum .venv/bin/python | awk '{print $$1}' > .venv-checksum
	@echo "Hash do venv registrado em .venv-checksum"

help:
	@echo "Targets disponíveis:"
	@echo "  setup         — Instalar dependências e configurar ambiente"
	@echo "  reset         — Limpar e reinstalar tudo"
	@echo "  infra-install — Setup completo + registrar hash do venv (SEC-020)"
	@echo "  run           — Executar app via launcher seguro (scripts/run.sh)"
	@echo "  dev           — Executar app direto (sem guardrails de seguranca)"
	@echo "  test          — Rodar testes"
	@echo "  lint          — Verificar código com ruff"
	@echo "  type-check    — Verificar tipos com mypy"
	@echo "  audit-deps    — Auditar CVEs em dependencias (pip-audit)"
	@echo "  check-venv    — Validar hash do .venv/bin/python"
	@echo "  backup        — Backup criptografado do DB (scripts/backup_db.sh)"
	@echo "  clean         — Limpar caches"
	@echo "  help          — Mostrar esta mensagem"
