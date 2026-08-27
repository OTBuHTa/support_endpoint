FROM python:3.12-slim

ARG APP_BUILD_REVISION=unknown
ENV APP_BUILD_REVISION=${APP_BUILD_REVISION}
LABEL org.opencontainers.image.revision=${APP_BUILD_REVISION}

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-date-header"]
