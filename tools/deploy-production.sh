#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${CSP_ENV_FILE:-.env.production}"
COMPOSE_FILE="${CSP_COMPOSE_FILE:-compose.production.yml}"
EXPECTED_VERSION="${RELEASE_VERSION:-0.9.0-rc1}"
WEB_URL="${CSP_SMOKE_BASE_URL:-http://127.0.0.1:8180}"

fail() {
  printf 'deploy-production: %s\n' "$*" >&2
  exit 1
}

[[ -f "$ENV_FILE" ]] || fail "$ENV_FILE is missing"
[[ -f "$COMPOSE_FILE" ]] || fail "$COMPOSE_FILE is missing"
[[ -x tools/backup.sh ]] || fail "tools/backup.sh is not executable"
[[ -x tools/restore-verify.sh ]] || fail "tools/restore-verify.sh is not executable"
[[ -x tools/smoke-production.sh ]] || fail "tools/smoke-production.sh is not executable"

mode="$(stat -c '%a' "$ENV_FILE")"
[[ "$mode" == "600" ]] || fail "$ENV_FILE must have mode 600 (found $mode)"

head_sha="$(git rev-parse HEAD)"
branch="$(git branch --show-current)"
[[ -n "$head_sha" ]] || fail "cannot determine git HEAD"
[[ -z "$(git status --porcelain)" ]] || fail "working tree is not clean"

export CSP_ENV_FILE="$ENV_FILE"
export CSP_BUILD_REVISION="$head_sha"
export RELEASE_VERSION="$EXPECTED_VERSION"
export CSP_SMOKE_BASE_URL="$WEB_URL"

printf 'deploy-production: preflight version=%s revision=%s branch=%s\n' \
  "$EXPECTED_VERSION" "$head_sha" "${branch:-detached}"

bash tools/release-check.sh
docker compose -f "$COMPOSE_FILE" config --quiet

backup_file="initial-install"
if docker compose -f "$COMPOSE_FILE" ps -a --services | grep -qx postgres; then
  printf 'deploy-production: existing PostgreSQL container detected; backup is mandatory\n'
  docker compose -f "$COMPOSE_FILE" up -d --wait postgres
  backup_output="$(bash tools/backup.sh)"
  printf '%s\n' "$backup_output"
  backup_file="$(printf '%s\n' "$backup_output" | grep -Eo '([^[:space:]]+\.dump)' | tail -1 || true)"
  [[ -n "$backup_file" && -f "$backup_file" ]] \
    || fail "could not identify backup dump from tools/backup.sh output"
  bash tools/restore-verify.sh "$backup_file"
else
  printf 'deploy-production: no existing PostgreSQL container; treating as initial install\n'
fi

previous_revision="$(curl -fsS "$WEB_URL/health" 2>/dev/null | sed -n 's/.*"build_revision":"\([^"]*\)".*/\1/p' || true)"
if [[ -n "$previous_revision" ]]; then
  printf 'deploy-production: previous deployed revision=%s\n' "$previous_revision"
else
  printf 'deploy-production: no healthy previous deployment detected at %s\n' "$WEB_URL"
fi

printf 'deploy-production: deploying revision=%s\n' "$head_sha"
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

bash tools/smoke-production.sh

health="$(curl -fsS "$WEB_URL/health")"
printf '%s\n' "$health" | grep -Fq "\"version\":\"$EXPECTED_VERSION\"" \
  || fail "health version does not match $EXPECTED_VERSION"
printf '%s\n' "$health" | grep -Fq "\"build_revision\":\"$head_sha\"" \
  || fail "health build_revision does not match deployed git HEAD"

printf 'deploy-production: SUCCESS version=%s revision=%s backup=%s\n' \
  "$EXPECTED_VERSION" "$head_sha" "$backup_file"
if [[ -n "$previous_revision" && "$previous_revision" != "$head_sha" ]]; then
  printf 'deploy-production: rollback checkpoint previous_revision=%s\n' "$previous_revision"
fi
