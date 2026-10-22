# WorldView single-service image for Hugging Face Spaces.
#
# Spaces cannot pass --build-args, so SERVICE defaults to `identity`; other
# services still build via infra/docker/Dockerfile.service with their ARGOCD
# / compose pipelines (see infra/argocd/).
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps ./apps

RUN uv sync --locked --all-packages --no-dev

FROM python:3.11-slim-bookworm AS runtime

ARG SERVICE=identity
ENV SERVICE=${SERVICE} \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv

RUN test -n "$SERVICE" || (echo 'ERROR: SERVICE must not be empty' && exit 1)

WORKDIR /app

COPY packages ./packages
COPY apps ./apps
COPY alembic.ini ./
COPY migrations ./migrations

RUN addgroup --system appuser && adduser --system --group appuser \
    && chown -R appuser:appuser /app /opt/venv
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request, os, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz', timeout=3.0).status == 200 else 1)"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn worldview_${SERVICE}.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
