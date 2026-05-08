# CerradoWatch — comandos de desenvolvimento
# Uso: make <comando>
# Requer: Docker, Python 3.11+, make

.PHONY: help up down db-init install test lint format pipeline dashboard clean

# ── Variáveis ─────────────────────────────────────────────────────────────────
PYTHON     = python
PIP        = pip
PYTEST     = pytest
DBT        = dbt
STREAMLIT  = streamlit
COMPOSE    = docker compose
IMAGE_DASH = cerradowatch-dashboard
IMAGE_PIPE = cerradowatch-pipeline

# ── Ajuda ─────────────────────────────────────────────────────────────────────
help: ## Mostra este menu
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Banco de dados ────────────────────────────────────────────────────────────
up: ## Sobe PostgreSQL + pgAdmin via Docker Compose
	$(COMPOSE) up -d
	@echo "✅  PostgreSQL em localhost:5432 | pgAdmin em http://localhost:5050"

down: ## Para os containers
	$(COMPOSE) down

db-init: ## Cria schemas e tabelas no banco local
	$(PYTHON) -c "\
from sqlalchemy import text; \
from ingestion.database import engine; \
from ingestion.models import *; \
from ingestion.firms.models import *; \
from ingestion.database import Base; \
with engine.begin() as c: \
  c.execute(text('CREATE SCHEMA IF NOT EXISTS raw')); \
  c.execute(text('CREATE SCHEMA IF NOT EXISTS staging')); \
  c.execute(text('CREATE SCHEMA IF NOT EXISTS mart')); \
Base.metadata.create_all(engine); \
print('Banco inicializado!')"

db-shell: ## Abre psql no banco local
	$(COMPOSE) exec postgres psql -U cerrado_user -d cerradowatch

# ── Python ────────────────────────────────────────────────────────────────────
install: ## Instala dependências de desenvolvimento
	$(PIP) install -e ".[dev]"
	$(PIP) install openpyxl streamlit-folium folium dbt-postgres
	cd dbt && $(DBT) deps

test: ## Roda testes com cobertura
	$(PYTEST) -v

test-fast: ## Roda testes sem coverage (mais rápido)
	$(PYTEST) -v --no-cov

lint: ## Lint com ruff
	ruff check ingestion/ orchestration/ dashboard/

format: ## Formata código com ruff
	ruff format ingestion/ orchestration/ dashboard/

typecheck: ## Type check com mypy
	mypy ingestion/

# ── Pipeline ──────────────────────────────────────────────────────────────────
pipeline: ## Roda o pipeline completo localmente
	$(PYTHON) -m orchestration.run_pipeline

firms-only: ## Roda apenas a ingestão FIRMS (queimadas)
	$(PYTHON) -c "from ingestion.firms.connector import run; run(days=7)"

prodes-only: ## Roda apenas a ingestão PRODES (desmatamento)
	$(PYTHON) -c "from ingestion.prodes.connector import run; run()"

inmet-only: ## Roda apenas a ingestão INMET (clima)
	$(PYTHON) -c "from ingestion.inmet.connector import run; run(days_back=7)"

conab-only: ## Roda apenas a ingestão CONAB (preços)
	$(PYTHON) -c "from ingestion.conab.connector import run; run()"

dbt-run: ## Materializa mart tables via dbt
	cd dbt && $(DBT) run --profiles-dir . --target dev

dbt-test: ## Roda testes do dbt
	cd dbt && $(DBT) test --profiles-dir . --target dev

dbt-docs: ## Gera documentação dbt e abre no browser
	cd dbt && $(DBT) docs generate --profiles-dir . --target dev
	cd dbt && $(DBT) docs serve

# ── Dashboard ─────────────────────────────────────────────────────────────────
dashboard: ## Abre o dashboard Streamlit localmente
	$(STREAMLIT) run dashboard/app.py

# ── Docker ────────────────────────────────────────────────────────────────────
docker-build: ## Build das imagens Docker
	docker build -f Dockerfile -t $(IMAGE_DASH):latest .
	docker build -f Dockerfile.pipeline -t $(IMAGE_PIPE):latest .

docker-run: ## Roda o dashboard em Docker (necessita DB rodando)
	docker run --rm -p 8501:8501 \
	  --env-file .env \
	  $(IMAGE_DASH):latest

# ── Limpeza ───────────────────────────────────────────────────────────────────
clean: ## Remove arquivos temporários
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dbt/target dbt/dbt_packages
	@echo "Limpeza concluída."
