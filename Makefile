# ============================================================
# grocy-reports Makefile
# ============================================================
# Usage: make <target>
# All docker commands use the dev configuration.

COMPOSE      = docker compose -f docker-compose.yml -f docker-compose.dev.yml
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
	$(COMPOSE) exec $(BACKEND_SVC) flake8 app tests
	$(COMPOSE) exec $(BACKEND_SVC) mypy app

lint-js:
	$(COMPOSE) exec $(FRONTEND_SVC) npm run type-check

lint-fix-python:
	$(COMPOSE) exec $(BACKEND_SVC) black app tests
	$(COMPOSE) exec $(BACKEND_SVC) isort app tests

lint-fix-js:
	$(COMPOSE) exec $(FRONTEND_SVC) npm run lint:fix

# ── Coverage ─────────────────────────────────────────────────
coverage-report:
	@echo "Coverage report available at backend/htmlcov/index.html"
	$(COMPOSE) exec $(BACKEND_SVC) python -m http.server 9000 --directory htmlcov

# ── Database Backup ───────────────────────────────────────────
backup-db:
	bash backup-db.sh

# ── Publish Images ────────────────────────────────────────────
publish:
	bash update-docker-images.sh
