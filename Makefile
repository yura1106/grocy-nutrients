# ============================================================
# grocy-reports Makefile
# ============================================================
# Usage: make <target>
# All docker commands use the dev configuration.

COMPOSE      = docker compose
BACKEND_SVC  = backend
FRONTEND_SVC = frontend

.PHONY: up down build logs \
        backend-shell frontend-shell \
        test-backend test-frontend test-all \
        migrate \
        lint-python lint-js \
        lint-fix-python lint-fix-js \
        coverage-report \
        backup-db \
        publish

# ── Lifecycle ────────────────────────────────────────────────
up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

# ── Shell Access ─────────────────────────────────────────────
backend-shell:
	$(COMPOSE) exec $(BACKEND_SVC) /bin/bash

frontend-shell:
	$(COMPOSE) exec $(FRONTEND_SVC) /bin/sh

# ── Testing ──────────────────────────────────────────────────
test-backend:
	$(COMPOSE) exec $(BACKEND_SVC) pytest

test-frontend:
	$(COMPOSE) exec $(FRONTEND_SVC) npm run test

test-all: test-backend test-frontend

# ── Database ─────────────────────────────────────────────────
migrate:
	$(COMPOSE) exec $(BACKEND_SVC) alembic upgrade head

# ── Linting ──────────────────────────────────────────────────
lint-python:
	$(COMPOSE) exec $(BACKEND_SVC) ruff check app tests
	$(COMPOSE) exec $(BACKEND_SVC) mypy app

lint-js:
	$(COMPOSE) exec $(FRONTEND_SVC) npm run type-check
	$(COMPOSE) exec $(FRONTEND_SVC) npm run lint

lint-fix-python:
	$(COMPOSE) exec $(BACKEND_SVC) ruff check --fix app tests
	$(COMPOSE) exec $(BACKEND_SVC) ruff format app tests

lint-fix-js:
	$(COMPOSE) exec $(FRONTEND_SVC) npm run lint:fix

# ── Coverage ─────────────────────────────────────────────────
coverage-report:
	-$(COMPOSE) exec $(BACKEND_SVC) pytest --cov=app --cov-report=html
	@echo "Coverage report available at http://localhost:9001"
	$(COMPOSE) exec $(BACKEND_SVC) python -m http.server 9001 --directory htmlcov

# ── Database Backup ───────────────────────────────────────────
backup-db:
	bash backup-db.sh

# ── Publish Images ────────────────────────────────────────────
publish:
	bash update-docker-images.sh
