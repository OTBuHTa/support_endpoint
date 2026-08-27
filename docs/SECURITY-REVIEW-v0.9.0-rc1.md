# Security review — v0.9.0-rc1

## Authentication and sessions

- Operator and customer browser refresh tokens are stored only in HttpOnly, SameSite=Strict cookies.
- Browser refresh sessions rotate server-side and logout revokes the session.
- Non-browser token-pair endpoints remain available for explicit API/CLI clients.
- Production startup fails closed when bootstrap is enabled, auth rate limiting is disabled or JWT secret quality is insufficient.

## Authorization and tenancy

- Operator endpoints remain workspace-scoped and deny-by-default through explicit permissions.
- Customer portal authorization derives scope from explicit User↔Client ownership links.
- Cross-workspace and cross-customer object lookups use not-found semantics where appropriate.
- Internal notes are stored separately from customer-visible messages.

## Edge and runtime

- Production API is not published directly on a host port.
- Backend network is private and separate from AI-project-SRV.
- API docs, OpenAPI and ReDoc are disabled in FastAPI production mode and explicitly blocked before the nginx SPA fallback.
- Application containers use no-new-privileges, reduced capabilities and read-only root filesystems where applicable.
- Health endpoints publish release version and deployed build revision for deployment identity verification.

## AI boundary

- AI is disabled by default and is advisory-only when enabled.
- No database mutation, message sending, shell, network administration or infrastructure execution tools are exposed to the model.
- Email/phone redaction occurs before LLM transport.
- Rate limiting and a Redis-backed distributed circuit breaker bound unhealthy model behavior; local circuit fallback protects operation if Redis access fails inside the gateway.

## Storage and recovery

- Attachment uploads are capped per file and per workspace.
- Workspace quota allocation is serialized to prevent parallel over-allocation.
- Attachment filenames are normalized before persistence/download metadata use.
- PostgreSQL backup files are checksummed and CI restores them into an isolated temporary database.
- Off-host encrypted retention remains a deployment-host responsibility.

## RC1 findings resolved

1. The production web Dockerfile omitted `portal.html`, causing the customer portal entrypoint to fail during image build. Fixed and guarded by `tools/release-check.sh`.
2. nginx SPA fallback returned HTTP 200/index.html for disabled `/docs`. Exact `/docs`, `/openapi.json` and `/redoc` locations now return 404 and are guarded by the release check.

## Environment-specific checks before public exposure

- Real TLS termination and HSTS behavior at the external endpoint.
- DNS/reverse-proxy or tunnel routing to loopback web bind only.
- Host firewall rules and SSH administration policy.
- PostgreSQL/Redis host resource limits and Redis `vm.overcommit_memory=1` where required by the target Linux host.
- Encrypted off-host backup destination plus retention/rotation policy.
- Real production secrets and CORS origin.

No unresolved repository-level security blocker is known at the time this RC document was written. Environment-specific checks are intentionally not represented as repository CI success.
