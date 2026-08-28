#!/usr/bin/env bash
set -euo pipefail

base_url="${CSP_SMOKE_BASE_URL:-http://127.0.0.1:8180}"
attempts="${CSP_SMOKE_ATTEMPTS:-40}"
sleep_seconds="${CSP_SMOKE_SLEEP_SECONDS:-2}"
expected_version="${RELEASE_VERSION:-0.9.0}"
expected_revision="${CSP_EXPECT_BUILD_REVISION:-}"

wait_for_200() {
  local path="$1"
  local i
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 5 "$base_url$path" >/dev/null; then
      return 0
    fi
    sleep "$sleep_seconds"
  done
  printf 'smoke: %s did not become ready after %s attempts\n' "$path" "$attempts" >&2
  return 1
}

expect_status() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$base_url$path")"
  [[ "$actual" == "$expected" ]] || {
    printf 'smoke: %s expected HTTP %s, got %s\n' "$path" "$expected" "$actual" >&2
    exit 1
  }
}

wait_for_200 /health
wait_for_200 /ready

health="$(curl -fsS --max-time 5 "$base_url/health")"
[[ "$health" == *"\"version\":\"$expected_version\""* ]] || {
  printf 'smoke: /health does not report expected version %s: %s\n' "$expected_version" "$health" >&2
  exit 1
}
if [[ -n "$expected_revision" ]]; then
  [[ "$health" == *"\"build_revision\":\"$expected_revision\""* ]] || {
    printf 'smoke: /health does not report expected build revision %s: %s\n' \
      "$expected_revision" "$health" >&2
    exit 1
  }
fi

expect_status / 200
expect_status /portal.html 200
expect_status /docs 404
expect_status /openapi.json 404
expect_status /api/v1/metrics 401

printf 'smoke: production edge, version and build identity OK at %s\n' "$base_url"
