# WorldView VR

> Experience the world as if you are physically there — live 360° streaming,
> AI-guided virtual tourism, verified human guides, and social presence.

Monorepo implementing the architecture described in [`docs/`](docs/README.md).
**Python-first** implementation of the control-plane microservices; VR clients
(Unity) and media pipeline are future phases.

## Repository layout

```
├── docs/                      # Architecture & business documentation (14 docs)
├── packages/
│   └── worldview/             # Shared library: config, auth, db, logging, idempotency
├── apps/                      # Deployable FastAPI microservices (each with src/ layout)
│   ├── identity/              #   users, auth (register/login/me/social), MFA, GDPR
│   ├── catalog/               #   tours, POIs, hotspots, geo search, travel lists
│   ├── streaming/             #   live stream state machine, realtime WS, chat moderation
│   ├── ai_guide/              #   RAG-grounded AI World Guide (mock + gateway providers)
│   ├── payments/              #   plans, checkout, pay-per-tour, tips, Stripe webhooks
│   ├── moderation/            #   reports, admin queue/decisions, enterprise admin RBAC
│   ├── creators/              #   applications, verification, loans, payouts, private tours
│   ├── notifications/         #   push subscriptions and delivery
│   └── gateway/               #   API gateway: routing, rate limiting, TLS
├── clients/
│   └── web/                   # Vite + three.js 360° player
├── scripts/
│   └── smoke_test.py          # boots all services and exercises the stack over HTTP
├── infra/
│   ├── docker/Dockerfile.service
│   └── terraform/main.tf      # AWS skeleton (VPC + EKS)
└── .github/workflows/ci.yml   # lint, format, test, smoke, docker build
```

## Prerequisites
- Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 22 (web client), Docker (optional).

## Quick start (local)

```bash
uv sync --all-packages          # install workspace + dev deps

make test                       # run the test suite
make lint                       # ruff check + format check

# Run one service (SQLite by default, zero setup):
make run-identity               # http://localhost:8001/docs
make run-catalog                # http://localhost:8002/docs
make run-streaming              # http://localhost:8003/docs
make run-ai-guide               # http://localhost:8004/docs
make run-payments               # http://localhost:8005/docs
make run-moderation             # http://localhost:8006/docs
make run-creators               # http://localhost:8007/docs
make run-notifications          # http://localhost:8008/docs

# Full end-to-end smoke test across the stack over HTTP:
uv run python scripts/smoke_test.py

# Full stack with Postgres + Redis via Docker:
docker compose up --build
```

## Web player

```bash
cd clients/web && npm install && npm run dev
# open http://localhost:5173/?src=<equirectangular-360-video-url>
```

## Configuration
All settings are environment variables (see `.env.example`): `DATABASE_URL`,
`JWT_SECRET`, `REGION_KEY`, `AI_PROVIDER`, `LOG_LEVEL`. Dev defaults use a
local SQLite file; production uses PostgreSQL (`postgresql+psycopg://`).

## Service inventory & ports (dev)

| Service | Port | Purpose |
|---|---|---|
| gateway | 8000 | Single API entry point, routing, rate limiting |
| identity | 8001 | Registration, login, social login, MFA, GDPR |
| catalog | 8002 | Tour/POI catalog, geo search, travel lists |
| streaming | 8003 | Stream lifecycle state machine, realtime chat |
| ai_guide | 8004 | Grounded Q&A over tour knowledge |
| payments | 8005 | Plans, checkout, tips, pay-per-tour, webhooks |
| moderation | 8006 | Reports, admin queue, enterprise RBAC |
| creators | 8007 | Applications, verification, payouts, private tours |
| notifications | 8008 | Push subscriptions and delivery |

## Status
- 138 tests passing; lint + format + bandit clean; end-to-end smoke passing.
- Passwords hashed with **argon2id** (legacy PBKDF2 hashes auto-upgrade on login);
  PostgreSQL engines use a tuned connection pool (`DB_POOL_*` settings).
- Speculative features from the docs (8K/16K, digital twins, social VR presence) are explicitly **not** implemented yet — see `docs/13-roadmap.md`.
