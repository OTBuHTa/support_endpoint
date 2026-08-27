import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

CORRELATION_HEADER = "X-Correlation-ID"


def get_correlation_id() -> str:
    return _correlation_id_ctx.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = incoming or str(uuid.uuid4())
        token = _correlation_id_ctx.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            _correlation_id_ctx.reset(token)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
