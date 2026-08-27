#!/usr/bin/env bash
set -euo pipefail

expected="${RELEASE_VERSION:-0.9.0-rc1}"
pep440="${expected/-rc/rc}"
release_doc="docs/RELEASE-v${expected}.md"

fail() {
  printf 'release-check: %s\n' "$*" >&2
  exit 1
}

expect_literal() {
  local file="$1"
  local literal="$2"
  [[ -f "$file" ]] || fail "$file is missing"
  grep -Fq -- "$literal" "$file" || fail "$file does not contain: $literal"
}

expect_literal apps/api/app/version.py "API_VERSION = \"$expected\""
expect_literal apps/api/pyproject.toml "version = \"$pep440\""
expect_literal apps/web/package.json "\"version\": \"$expected\""
expect_literal README.md "\`v$expected\`"
expect_literal docs/production.md "v$expected"
expect_literal "$release_doc" "Release v$expected"

expect_literal .env.production.example "BOOTSTRAP_ENABLED=false"
expect_literal .env.production.example "AUTH_RATE_LIMIT_ENABLED=true"
expect_literal .env.production.example "SECURE_HEADERS_HSTS_ENABLED=true"
expect_literal .env.production.example "LLM_ENABLED=false"
expect_literal .env.production.example "ATTACHMENT_MAX_BYTES="
expect_literal .env.production.example "ATTACHMENT_WORKSPACE_QUOTA_BYTES="

expect_literal compose.production.yml "internal: true"
expect_literal compose.production.yml "no-new-privileges:true"
expect_literal compose.production.yml "app.workers.sla_scheduler"

printf 'release-check: %s metadata and production invariants OK\n' "$expected"
