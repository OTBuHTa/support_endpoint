# ADR-003: Workspace multi-tenancy and deny-by-default authorization

## Status
Accepted

## Context
The platform must guarantee that a member of one workspace (tenant)
can never read or act on another workspace's data, even if they know
or guess its id — this is a mandatory security regression per the
project charter. We also need a uniform way to express "this role
lacks this permission" across every endpoint.

## Decision
- **Workspace as tenant boundary.** `WorkspaceMembership` is the only
  join between a `User` and a `Workspace`; it carries a single `Role`.
  Every tenant-scoped endpoint that takes a `workspace_id` resolves
  the caller's membership via `get_workspace_membership` before doing
  anything else.
- **Permissions are the authorization unit, not roles.** Roles
  (`Client`, `Operator`, `Supervisor`, `Administrator`) are bundles of
  permission codes (`RolePermission`). `require_permission(code)` is a
  FastAPI dependency factory checking the flattened permission set for
  the caller's role in that workspace — deny-by-default: absence of a
  grant row means denied.
- **404, not 403, on both "no membership" and "no permission".**
  `get_workspace_membership` and `require_permission` both raise the
  same `NotFoundError` (404) whether the caller has no membership in
  the workspace at all, or has membership but lacks the specific
  permission. This is deliberate: a 403 discloses that the workspace
  *exists* and that the caller is merely unauthorized for it, which is
  itself information leakage across tenants (workspace-id enumeration
  becomes possible via 403-vs-404 timing/response differences). A
  uniform 404 makes an unauthorized workspace indistinguishable from a
  nonexistent one.

## Consequences
- Frontend error handling for "workspace not found" and "you don't
  have permission" must be unified into one UX state, or the frontend
  must derive permission state from `GET /workspaces/{id}/my-permissions`
  proactively rather than relying on distinguishing 403 from 404 on
  the action endpoint itself.
- Every new tenant-scoped router in later phases (tickets, clients,
  knowledge base, etc.) must depend on `require_permission(...)` (or
  at minimum `get_workspace_membership`) — this is the primary
  mechanism enforced by the mandatory `test_workspace_a_cannot_access_workspace_b`-style
  regression tests, and new endpoints should ship an equivalent test.
