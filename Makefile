.PHONY: up down logs migrate test lint check

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:
	docker compose --profile tools run --rm --build migration

test:
	cd apps/api && pytest -q

lint:
	cd apps/api && ruff check app tests

check: lint test
