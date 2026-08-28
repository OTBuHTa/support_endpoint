#!/usr/bin/env bash
set -euo pipefail

expected="${RELEASE_VERSION:-0.9.0-rc1}"
pep440="${expected/-rc/rc}"
release_doc="docs/RELEASE-v${expected}.md"
security_doc="docs/SECURITY-REVIEW-v${expected}.md"

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
expect_literal "$security_doc" "Security review — v$expected"

expect_literal .env.production.example "BOOTSTRAP_ENABLED=false"
expect_literal .env.production.example "AUTH_RATE_LIMIT_ENABLED=true"
expect_literal .env.production.example "SECURE_HEADERS_HSTS_ENABLED=true"
expect_literal .env.production.example "LLM_ENABLED=false"
expect_literal .env.production.example "ATTACHMENT_MAX_BYTES="
expect_literal .env.production.example "ATTACHMENT_WORKSPACE_QUOTA_BYTES="

expect_literal compose.production.yml "internal: true"
expect_literal compose.production.yml "no-new-privileges:true"
expect_literal compose.production.yml "app.workers.sla_scheduler"
expect_literal apps/web/Dockerfile "index.html portal.html"
expect_literal apps/web/nginx.conf "location = /docs"
expect_literal apps/web/nginx.conf "location = /openapi.json"
expect_literal apps/web/nginx.conf "location = /redoc"

expect_literal tools/production-edge-check.sh "support.example.com placeholder"
expect_literal tools/production-edge-check.sh "CSP_WEB_BIND must remain loopback-only"
expect_literal tools/backup-offhost.sh "CSP_BACKUP_SSH_REMOTE is required"
expect_literal tools/backup-and-offhost.sh "restore-verify.sh"
expect_literal deploy/systemd/cloudflared-support-endpoint.service "/etc/support-endpoint/cloudflared.yml"
expect_literal deploy/systemd/support-endpoint-backup.service "/etc/support-endpoint/backup-offhost.env"
expect_literal deploy/systemd/support-endpoint-backup.timer "OnCalendar="
expect_literal deploy/cloudflared-support-endpoint.yml.example "http://127.0.0.1:8180"

printf 'release-check: %s metadata and production invariants OK\n' "$expected"
