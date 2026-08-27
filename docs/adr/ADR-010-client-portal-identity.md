# ADR-010: Client portal identity and ownership boundary

## Status

Accepted for Phase 7B (`v0.7.0-alpha`).

## Context

The product has global authenticated `User` identities, workspace memberships for operators, and workspace-scoped CRM `Client` records. Reusing operator workspace roles for customer access would either over-grant customers or require fragile client-side filtering. Email equality is also not an authoritative identity binding.

## Decision

1. Customer access uses an explicit `ClientUserLink` between one User and one Client within a workspace.
2. The link is created only through an operator endpoint protected by `clients.write`; the customer cannot self-select a Client ID.
3. A customer User does not need a `WorkspaceMembership`. Portal authorization is ownership-based and independent of operator RBAC.
4. The link table enforces at most one linked User per Client and one linked Client per User within a workspace. A User may have links in multiple workspaces.
5. `/portal/accounts` derives available customer accounts from the authenticated User only.
6. Portal ticket endpoints derive `workspace_id` and `client_id` from the authenticated link. Requests never accept an arbitrary client identifier from the browser.
7. Cross-user or cross-client portal object lookups normalize to 404.
8. Portal message reads return only rows from the customer-visible `Message` table. `InternalNote` is never joined or serialized by portal routes.
9. Customer replies are always stored as `INBOUND` messages. Operator outbound semantics remain under the existing Communications API.
10. Customer portal UI is a separate Vite entrypoint at `/portal.html`; the operator console remains at `/`. This is presentation separation, not the authorization boundary—the backend ownership checks remain authoritative.

## Consequences

- Customer identities cannot acquire operator permissions merely by using the portal.
- A compromised portal link is scoped to exactly one CRM Client in that workspace.
- Account linking is an explicit administrative action and should later gain invitation/verification UX if self-service onboarding is required.
- Phase 8 should evaluate browser token storage hardening and revocation UX without changing the ownership model.
