.PHONY: install lint test migrate migrate-new db-up test-postgres security seed \
	run-gateway run-identity run-catalog run-streaming run-ai-guide run-all smoke

install:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

security:
	uv run bandit -r apps packages -x '*/tests/*,*/migrations/*'
	uv run pip-audit

test:
	uv run pytest

smoke-test:
	uv run python scripts/smoke_test.py

seed:
	uv run python scripts/seed_catalog.py

# --- Database (PostgreSQL via docker) ---
db-up:
	docker compose up -d postgres

migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(m)"

migrate-check:
	uv run alembic check

# Run the whole suite + migrations against real PostgreSQL (needs `make db-up`).
test-postgres:
	set "WORLDVIEW_TEST_DATABASE_URL=postgresql+psycopg://worldview:dev-password@localhost:5432/worldview" && uv run alembic upgrade head && uv run pytest

# --- Local dev (SQLite, zero-setup) ---
run-gateway:
	uv run --directory apps/gateway python -m worldview_gateway

run-identity:
	uv run --directory apps/identity uvicorn worldview_identity.main:app --reload --port 8001

run-catalog:
	uv run --directory apps/catalog uvicorn worldview_catalog.main:app --reload --port 8002

run-streaming:
	uv run --directory apps/streaming uvicorn worldview_streaming.main:app --reload --port 8003

run-ai-guide:
	uv run --directory apps/ai_guide uvicorn worldview_ai_guide.main:app --reload --port 8004

# --- Full stack (Postgres + Redis + gateway + all services) in containers ---
run-all:
	docker compose up --build