import time

from prometheus_client import Counter, Histogram
from starlette.types import ASGIApp, Message, Receive, Scope, Send

METRICS_PATH = "/metrics"
UNMATCHED_ROUTE = "unmatched"

HTTP_REQUESTS = Counter(
    "http_requests",
    "HTTP requests by method, route template and status",
    ["method", "route", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration by route template",
    ["route"],
)


def route_template(scope: Scope) -> str:
    root_path = scope.get("root_path") or ""
    route_path = getattr(scope.get("route"), "path", None)
    if isinstance(route_path, str):
        return f"{root_path}{route_path}" if root_path else route_path
    return root_path or UNMATCHED_ROUTE


class HttpMetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        started = time.perf_counter()
        status = 500

        async def send_and_capture_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, send_and_capture_status)
        finally:
            route = route_template(scope)
            if route != METRICS_PATH:
                HTTP_REQUESTS.labels(scope["method"], route, str(status)).inc()
                HTTP_REQUEST_DURATION.labels(route).observe(
                    time.perf_counter() - started
                )
