# ADR-004: Client / ClientOrganization / ClientContact split

## Status
Accepted

## Context
The project charter (section G) lists `Client`, `ClientOrganization`,
and `ClientContact` as three distinct entities without further
elaboration on how they relate. A concrete relational design decision
was needed before implementation.

## Decision
- **`ClientOrganization`** — a company/business account (B2B entity),
  optional. Has `name`, `domain`, `notes`.
- **`Client`** — the primary CRM record that a Ticket (Phase 4) will
  attach to: one individual person or account-holder, with its own
  `primary_email`/`primary_phone`, optionally linked to one
  `ClientOrganization` via a nullable `organization_id`.
- **`ClientContact`** — zero or more *additional* labeled contact
  channels for a `Client` (e.g. "work email", "mobile", "billing
  phone"), kept as separate rows rather than extra columns on `Client`
  so a client can have an arbitrary number of contact points without
  further schema changes.

A `Client` can exist with no `ClientOrganization` (an individual
customer with no company affiliation) — `organization_id` is nullable
and validated (must belong to the same workspace) rather than required.

## Rejected alternatives
- **Treating `ClientContact` as redundant with `Client`** (i.e. only
  `Client` + `ClientOrganization`, no third table) was rejected: it
  would force choosing a single email/phone per client or awkwardly
  multiplying `Client` rows for one real person, complicating the
  future Ticket → Client relationship.
- **Making `organization_id` required** was rejected: many real
  customer-service workspaces serve individual consumers with no
  organizational affiliation at all (B2C), not only B2B accounts.

## Consequences
- Every `Client`/`ClientOrganization`/`ClientContact` row carries its
  own `workspace_id` (not just inherited via a join) so repository
  queries can filter directly on it without an extra join — this
  matters for the IDOR guard: `ClientRepository.get_in_workspace`
  filters on `(id, workspace_id)` together, so a client id belonging
  to workspace B can never resolve through workspace A's path even if
  the caller is a legitimate member of workspace A (see the regression
  test `test_client_id_from_one_workspace_not_resolvable_via_another_workspace_path`).
- Search (`GET /clients?q=...`) matches against `full_name`,
  `primary_email`, and `primary_phone` on `Client` directly; it does
  not currently search `ClientContact.value` — extending search to
  contact channels is a reasonable Phase 3 follow-up if operators need
  to find a client by a secondary phone/email, not implemented in this
  delivery.
- Deletion is soft (`is_active=False`) on `Client` and
  `ClientOrganization`; `ClientContact` rows are hard-deleted, since
  they carry no history of their own that a future Ticket could
  reference (unlike a Client, which a Ticket will reference by id).
