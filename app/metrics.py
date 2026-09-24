"""Prometheus metrics for the HTTP API, exposed on GET /metrics.

Request rate, error rate and response time all derive from two series:

    http_requests_total{method, path, status}           counter
    http_request_duration_seconds{method, path}         histogram

`path` is the route template (/api/v1/modules/{module_id}), never the concrete URL, so a
series is created per endpoint and not per module id. Requests that match no route share the
single value "<unmatched>" for the same reason.
"""

import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

# Probes and scrapes arrive every few seconds; counting them would bury the real traffic.
EXCLUDED_PATHS = ("/metrics", "/health/")
UNMATCHED = "<unmatched>"

REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by route template and status code.",
    ["method", "path", "status"],
)
DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds, by route template.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being handled.",
    ["method"],
)


def _route_template(scope: Scope) -> str:
    # The router stores the matched route in the scope while handling the request, so this
    # is read after the call. It also covers routes of included routers, prefix and all.
    route = scope.get("route")
    return getattr(route, "path_format", None) or UNMATCHED


class PrometheusMiddleware:
    """Pure ASGI middleware: records every request, including those that end in an exception."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(EXCLUDED_PATHS):
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        status = 500

        async def send_wrapper(message: dict) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        IN_PROGRESS.labels(method).inc()
        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = _route_template(scope)
            DURATION.labels(method, path).observe(time.perf_counter() - start)
            REQUESTS.labels(method, path, str(status)).inc()
            IN_PROGRESS.labels(method).dec()


def metrics_endpoint(_: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
