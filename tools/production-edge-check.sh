#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

env_file="${CSP_ENV_FILE:-.env.production}"
base_url="${CSP_SMOKE_BASE_URL:-http://127.0.0.1:8180}"
expected_version="${RELEASE_VERSION:-0.9.0-rc1}"
expected_revision="${CSP_EXPECT_BUILD_REVISION:-$(git rev-parse HEAD 2>/dev/null || printf unknown)}"

fail() {
  printf 'production-edge-check: %s\n' "$*" >&2
  exit 1
}

[[ -r "$env_file" ]] || fail "$env_file is missing or unreadable"

read_env() {
  local key="$1"
  sed -n "s/^${key}=//p" "$env_file" | tail -1
}

origin="$(read_env CORS_ALLOW_ORIGINS)"
bind="$(read_env CSP_WEB_BIND)"

[[ -n "$origin" ]] || fail 'CORS_ALLOW_ORIGINS is empty'
[[ "$origin" != *'support.example.com'* ]] || fail 'CORS_ALLOW_ORIGINS still uses support.example.com placeholder'
[[ "$origin" == https://* ]] || fail 'CORS_ALLOW_ORIGINS must use HTTPS in production'
[[ "$bind" == 127.0.0.1:* || "$bind" == '[::1]:'* ]] || fail 'CSP_WEB_BIND must remain loopback-only behind the edge'

health="$(curl -fsS --max-time 10 "$base_url/health")" || fail "local health failed at $base_url"
ready="$(curl -fsS --max-time 10 "$base_url/ready")" || fail "local readiness failed at $base_url"

python3 - "$health" "$ready" "$expected_version" "$expected_revision" <<'PY'
import json
import sys
health = json.loads(sys.argv[1])
ready = json.loads(sys.argv[2])
expected_version = sys.argv[3]
expected_revision = sys.argv[4]
assert health.get("status") == "ok", health
assert ready.get("status") == "ok", ready
assert health.get("version") == expected_version, health
assert ready.get("version") == expected_version, ready
if expected_revision != "unknown":
    assert health.get("build_revision") == expected_revision, health
    assert ready.get("build_revision") == expected_revision, ready
assert ready.get("checks", {}).get("database") == "ok", ready
assert ready.get("checks", {}).get("redis") == "ok", ready
PY

public_origin="${CSP_PUBLIC_ORIGIN:-$origin}"
[[ "$public_origin" == https://* ]] || fail 'CSP_PUBLIC_ORIGIN must use HTTPS'

curl -fsS --max-time 15 "$public_origin/health" >/dev/null || fail "public health failed at $public_origin"
curl -fsS --max-time 15 "$public_origin/ready" >/dev/null || fail "public readiness failed at $public_origin"

for path in /docs /openapi.json /redoc; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$public_origin$path" || true)"
  [[ "$code" == 404 ]] || fail "$public_origin$path returned HTTP $code, expected 404"
done

printf 'production-edge-check: PASS origin=%s version=%s revision=%s\n' \
  "$public_origin" "$expected_version" "$expected_revision"
