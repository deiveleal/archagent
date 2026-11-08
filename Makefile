# Comandos do harness (docs/harness.md §3).
COMPOSE ?= docker compose
PY ?= uv run

.PHONY: up down build check lint typecheck secrets paths test test-local test-integration eval eval-full kb-check report

up:
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

## N0 — estática
check: lint typecheck secrets paths

lint:
	$(PY) ruff check .
	$(PY) ruff format --check .

typecheck:
	$(PY) mypy

secrets:
	@if command -v gitleaks >/dev/null; then gitleaks git --no-banner --redact .; \
	else docker run --rm -v "$(CURDIR):/repo" zricethezav/gitleaks:v8.30.1 git --no-banner --redact /repo; fi

paths:
	$(PY) python scripts/check_paths.py

## N1 + N2 — dentro do container de testes (perfil test)
test:
	$(COMPOSE) --profile test run --rm --build tests

## N1 local, sem containers
test-local:
	$(PY) pytest --cov --cov-report=term-missing:skip-covered

test-integration:
	$(PY) pytest -m integration
