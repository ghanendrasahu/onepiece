.PHONY: install lint test run-identity run-catalog run-streaming run-ai-guide run-all

install:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

run-identity:
	uv run --directory services/identity uvicorn worldview_identity.main:app --reload --port 8001

run-catalog:
	uv run --directory services/catalog uvicorn worldview_catalog.main:app --reload --port 8002

run-streaming:
	uv run --directory services/streaming uvicorn worldview_streaming.main:app --reload --port 8003

run-ai-guide:
	uv run --directory services/ai_guide uvicorn worldview_ai_guide.main:app --reload --port 8004

run-all:
	docker compose up --build
