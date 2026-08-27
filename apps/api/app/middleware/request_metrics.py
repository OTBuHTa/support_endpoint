import threading
import time
from collections import Counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = Counter()
        self._in_flight = 0
        self._duration_seconds = 0.0

    def started(self) -> None:
        with self._lock:
            self._in_flight += 1

    def finished(self, *, method: str, status_code: int, duration_seconds: float) -> None:
        status_class = f"{status_code // 100}xx"
        with self._lock:
            self._in_flight -= 1
            self._requests[(method, status_class)] += 1
            self._duration_seconds += duration_seconds

    def render_prometheus(self) -> str:
        with self._lock:
            requests = list(self._requests.items())
            in_flight = self._in_flight
            duration = self._duration_seconds

        lines = [
            "# HELP csp_http_requests_total Total HTTP requests by method and status class.",
            "# TYPE csp_http_requests_total counter",
        ]
        for (method, status_class), count in sorted(requests):
            labels = f'method="{method}",status_class="{status_class}"'
            lines.append(f"csp_http_requests_total{{{labels}}} {count}")
        lines.extend(
            [
                "# HELP csp_http_requests_in_flight Current in-flight HTTP requests.",
                "# TYPE csp_http_requests_in_flight gauge",
                f"csp_http_requests_in_flight {in_flight}",
                "# HELP csp_http_request_duration_seconds_sum Cumulative HTTP request duration.",
                "# TYPE csp_http_request_duration_seconds_sum counter",
                f"csp_http_request_duration_seconds_sum {duration:.6f}",
            ]
        )
        return "\n".join(lines) + "\n"


request_metrics = RequestMetrics()


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started_at = time.perf_counter()
        request_metrics.started()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            request_metrics.finished(
                method=request.method,
                status_code=status_code,
                duration_seconds=time.perf_counter() - started_at,
            )
