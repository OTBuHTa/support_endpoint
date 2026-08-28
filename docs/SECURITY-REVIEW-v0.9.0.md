# Security review — v0.9.0

## Authentication and sessions

- Browser refresh tokens are stored only in HttpOnly, SameSite=Strict cookies.
- Refresh sessions rotate server-side and logout revokes the session.
- Production startup fails closed for unsafe JWT secrets, enabled bootstrap or disabled auth rate limiting.

## Authorization and tenancy

- Operator endpoints are workspace-scoped with deny-by-default permission checks.
- Customer portal authorization derives scope from explicit User↔Client ownership links.
- Cross-workspace and cross-customer object access is guarded against IDOR/BOLA.
- Internal notes remain separate from customer-visible messages.

## Runtime and edge

- Production API has no direct host-port exposure.
- Backend Docker networking is private and independent from unrelated projects.
- API docs/OpenAPI/ReDoc are disabled in production and explicitly blocked by nginx before SPA fallback.
- Application containers use no-new-privileges, reduced capabilities and read-only root filesystems where applicable.
- Health endpoints expose release version and build revision for deployment identity checks.
- Public edge tooling fails closed for placeholder origin, non-loopback web binding and invalid external HTTPS behavior.
- A dedicated `cloudflared-support-endpoint.service` example prevents implicit coupling to an existing host tunnel.

## AI boundary

- AI remains disabled by default and advisory-only when enabled.
- The model has no database mutation, message sending, shell, network administration or infrastructure execution authority.
- Email/phone redaction occurs before model transport.
- Rate limiting and distributed circuit state bound unhealthy model behavior.

## Storage and recovery

- Attachment uploads are capped per file and per workspace.
- Workspace quota allocation is serialized.
- PostgreSQL backups are checksummed and restored into an isolated temporary database for verification.
- Existing-database production deployment requires a fresh backup and restore verification before application replacement.
- Off-host tooling verifies the checksum before transfer and again at the independent destination.
- Dedicated backup systemd units are provided so unrelated host backup stacks are not modified or implicitly trusted.

## Findings closed before stable promotion

1. Customer portal static entrypoint omission was fixed and guarded by release checks.
2. nginx SPA fallback exposure of disabled API docs was fixed with exact 404 routes.
3. Production Compose interpolation was fixed to load the explicit environment file before manifest interpolation.
4. Production backup path parsing was fixed to consume the exact structured `backup=` output.
5. Runtime backup artifacts are ignored by git so mandatory backups cannot dirty the deployment checkout.
6. Public-edge and off-host backup gaps now have fail-closed tooling and isolated service templates rather than coupling to unrelated host infrastructure.

## Environment-specific requirements before public exposure

The stable repository does not itself prove external DNS/TLS or remote backup availability. Public-production activation requires:

- a dedicated real HTTPS hostname;
- CORS set to that exact origin;
- a dedicated tunnel/reverse-proxy path to the loopback-only web listener;
- successful external edge verification;
- an independent off-host backup destination and successful verified transfer;
- host firewall and administrative-access review.

No unresolved repository-level security blocker is known for v0.9.0. Environment-specific public-production gates remain intentionally fail-closed until real external resources are provisioned.
