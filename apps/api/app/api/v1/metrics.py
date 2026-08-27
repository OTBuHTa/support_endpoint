import secrets

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.middleware.request_metrics import request_metrics

router = APIRouter(tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics(authorization: str | None = Header(default=None)) -> PlainTextResponse:
    settings = get_settings()
    expected = settings.metrics_bearer_token
    if not expected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid metrics credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return PlainTextResponse(
        request_metrics.render_prometheus(),
        media_type="text/plain; version=0.0.4",
    )
