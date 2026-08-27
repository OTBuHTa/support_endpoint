# ADR-002: Authentication — JWT access tokens + opaque rotating refresh sessions

## Status
Accepted

## Context
The platform needs stateless, verifiable short-lived credentials for
per-request authorization, plus a way to issue new access tokens over
a long-lived session without re-entering a password, and a way to
revoke a compromised or logged-out session immediately.

## Decision
- **Access tokens**: signed JWTs (HS256, `JWT_SECRET`), 15-minute
  default lifetime, carrying only the user id (`sub`) — no roles or
  permissions embedded, since those are looked up fresh per request
  against the database and can change between token issuance and use.
- **Refresh tokens**: opaque, high-entropy random strings
  (`secrets.token_urlsafe(48)`), never stored raw — only their
  SHA-256 hash is persisted in the `sessions` table, alongside
  `expires_at` and a nullable `revoked_at`.
- **Rotation**: every `/auth/refresh` call revokes the presented
  session and issues a brand-new access+refresh pair. A reused
  (already-rotated) refresh token is rejected — this detects token
  replay/theft after the fact.
- **Passwords**: hashed with `bcrypt` directly (not `passlib`, see
  "Rejected alternatives").
- **Bootstrap vs. registration**: `/auth/bootstrap` is a one-time,
  install-wide operation (creates the very first owner + workspace,
  gated by `BOOTSTRAP_ENABLED` and "no users exist yet"). All
  subsequent account creation goes through `/auth/register`, which has
  no such gate and simply creates a standalone user with no workspace
  membership — the caller then creates or is invited into a workspace.

## Rejected alternatives
- **`passlib[bcrypt]`** was tried first (matching AI-project-SRV's
  likely dependency shape) but `passlib` 1.7.4 (its last release, from
  2020, project unmaintained) has a known incompatibility with
  `bcrypt>=4.1`'s changed internal API, causing a hard `ValueError` on
  every hash/verify call. Rather than pin `bcrypt<4.1` indefinitely
  against project's an unmaintained dependency, we call the actively
  maintained `bcrypt` library directly.
- **Storing roles/permissions in the JWT** was rejected: it would let
  a permission *revocation* remain effectively active for up to the
  token's remaining lifetime, and it would require re-issuing tokens
  on every role change.

## Consequences
- Revoking a session (logout, admin-forced logout, detected replay) is
  immediate and reliable — it does not depend on waiting out an access
  token's lifetime for the *refresh* path, though the already-issued
  15-minute access token itself cannot be recalled early (accepted
  trade-off of stateless JWTs; kept short specifically to bound this).
- Every request re-checks current permissions from the database,
  trading a small amount of query overhead for correctness under
  concurrent permission changes.
