"""Observability for every service: Prometheus metrics, optional Sentry, optional OTel.

- Metrics: always available at ``/metrics`` (Prometheus text format) via
  ``MetricsMiddleware`` + ``metrics_router``.
- Sentry: enabled only when ``SENTRY_DSN`` is set (lazy import, no hard dep).
- OpenTelemetry: enabled only when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set
  (lazy import, no hard dep).
"""

import logging
import os
import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("worldview.observability")

_HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests served",
    ["service", "method", "path", "status"],
)
_HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "path"],
)

metrics_router = APIRouter()


@metrics_router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Count and time every request (except the metrics endpoint itself)."""

    def __init__(self, app, service_name: str) -> None:
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path) if route else request.url.path
        labels = (self.service_name, request.method, path, response.status_code)
        _HTTP_REQUESTS.labels(*labels).inc()
        _HTTP_LATENCY.labels(self.service_name, request.method, path).observe(duration)
        return response


def init_observability(service_name: str, settings) -> None:
    """Configure optional Sentry + OpenTelemetry; metrics are always available."""
    if getattr(settings, "sentry_dsn", None):
        _init_sentry(service_name, settings)
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        _init_tracing(service_name)


def instrument_app(app: FastAPI, service_name: str) -> None:
    """Add the /metrics router and metrics middleware to an app."""
    app.include_router(metrics_router)
    app.add_middleware(MetricsMiddleware, service_name=service_name)


def _init_sentry(service_name: str, settings) -> None:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            traces_sample_rate=0.1,
            release=f"worldview-{service_name}",
        )
        log.info("sentry enabled")
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("sentry unavailable: %s", exc)


def _init_tracing(service_name: str) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        log.info("opentelemetry tracing enabled")
    except Exception as exc:  # pragma: no cover - optional dependency
        log.warning("opentelemetry unavailable: %s", exc)
