# Architecture

## Deployment topology

```
srv-ai (192.168.5.155)
├── AI-project-SRV stack (untouched, separate repo/compose project)
├── ai-lab stack (untouched — grafana/prometheus/qdrant/ollama/open-webui/…)
└── csp stack (this project)
    ├── network: csp_default, subnet 172.31.0.0/24
    ├── postgres (db "csp", volume csp_postgres_data)
    ├── redis (volume csp_redis_data)
    ├── api  — FastAPI, host port 8100 → container 8000
    ├── web  — nginx placeholder (Phase 7: React/Vite), host port 8180 → 80
    └── LLM access (Phase 6+): host.docker.internal:11434/v1 via
        extra_hosts: host-gateway — same pattern as AI-project-SRV,
        no LAN/WAN Ollama exposure required
```

## Backend module layout

```
apps/api/app/
├── main.py           # app factory, middleware, exception handlers
├── core/              # config (env-driven settings), security (JWT/bcrypt), exceptions
├── db/                # SQLAlchemy session, Redis client, declarative base
├── models/            # ORM: User, Workspace, WorkspaceMembership, Role,
│                       #      Permission, RolePermission, RefreshSession, AuditEvent
├── schemas/            # Pydantic request/response DTOs
├── repositories/       # DB access only — no business logic
├── services/           # business logic (auth, workspace, rate limiting)
├── authz/              # permission constants, deny-by-default dependencies
├── api/v1/             # thin HTTP routers, call services
├── middleware/          # correlation-id middleware
├── observability/       # structured JSON logging
└── ai/                  # reserved for Phase 6 LLMGateway — empty in Foundation
alembic/                 # this project's own migration history
```

## Request flow (representative — auth + authorization)

```
Request
  → CorrelationIdMiddleware (assigns/propagates X-Correlation-ID)
  → CORS
  → router (api/v1/*)
  → Depends(get_current_user)          # validates JWT, loads active User
  → Depends(get_workspace_membership)   # 404 if caller has no membership here
  → Depends(require_permission(code))   # 404 if membership lacks the permission
  → service layer                       # business logic, commits, audit record
  → repository layer                    # SQLAlchemy queries, workspace-scoped
  → response
```

## Ticket / SLA / AI flow (Phase 4/6, advisory-only)

```
Ticket event → service layer → (optional) AI suggestion via LLMGateway
   → suggestion stored as a proposal (never auto-applied)
   → operator/authorization gate
   → deterministic service-layer mutation → audit event
```
If the LLM call times out, errors, or the circuit breaker is open, the
ticket/CRM flow continues unaffected — only the AI-assist panel
reports "unavailable." The LLM must never independently close tickets,
change permissions, delete customers, alter SLA policies, perform
administrative actions, send external messages, execute shell
commands, or modify infrastructure (see ADR-002 for token design and
`docs/security.md` for the full authorization model).

## Phase roadmap

- **Phase 0 — Discovery** ✅ done: host/repo inventory, collision report.
- **Phase 1 — Architecture** ✅ done: this document, ADR-001..003.
- **Phase 2 — Foundation** ✅ done: auth, workspace/RBAC,
  health, logging, audit, tests, CI, Compose.
- **Phase 3 — CRM** ✅ done: ClientOrganization, Client,
  ClientContact — workspace-scoped CRUD, case-insensitive search,
  pagination, soft-delete, RBAC (`clients.read`/`clients.write`),
  audit events, object-level IDOR guard (see ADR-004).
- **Phase 4 — Service Desk** ✅ done (this delivery): Ticket with a
  server-controlled state machine (ADR-005), Queue/TicketCategory/Tag
  workspace-customizable lookups, assignment with membership
  validation and append-only history, filtered search/pagination,
  RBAC (`tickets.*`, with `tickets.close` distinct from
  `tickets.update`), audit events, object-level IDOR guard.
- **Phase 5 — Communications**: conversations, messages, internal
  notes (never visible to clients), attachments, channel abstraction.
- **Phase 6 — Operations + AI**: tasks, SLA engine, notifications,
  knowledge base, bounded/advisory LLM features via a new `ai/` module
  (LLMGateway, redaction, circuit breaker, per-workspace rate limits).
- **Phase 7 — Frontend**: real React/Vite operator UI and client
  portal, replacing the current nginx placeholder.
- **Phase 8 — Production hardening**: security/tenant-isolation
  review, performance/indexes, observability (metrics/traces), CI
  supply-chain hardening (pinned action SHAs, dependency constraints,
  image build-identity verification — deferred from Phase 2, see
  `.github/workflows/ci.yml`), documentation review.

## Explicit non-goals of Foundation (Phase 2)

- No ticket/CRM domain entities yet — only the identity/tenancy/RBAC
  substrate they will sit on. (CRM itself landed in Phase 3, see below.)
- No LLM wiring — `LLM_ENABLED=false` by default; `app/ai/` is an
  empty placeholder package.
- No real frontend — `apps/web` is a static nginx placeholder proving
  the Compose/network/port layout end-to-end.
- No user-invitation endpoint — the only ways into a workspace are
  bootstrap (first-ever owner) or self-registration + self-creation of
  a workspace (immediate Administrator). Inviting an existing user
  into someone else's workspace is Phase 3+ scope.

## Explicit non-goals of Phase 3 (CRM)

- No Ticket entity yet — `Client` exists as the record a Ticket will
  reference in Phase 4, but nothing references it yet.
- Search does not cover `ClientContact.value` (secondary emails/phones)
  — only `Client.full_name`/`primary_email`/`primary_phone`. See
  ADR-004's consequences section.
- No bulk import/export, no deduplication/merge workflow for clients.
- `ClientOrganization`/`Client` are soft-deleted (`is_active=False`);
  `ClientContact` is hard-deleted (see ADR-004).

## Explicit non-goals of Phase 4 (Service Desk)

- No Conversation/Message/InternalNote yet — a ticket has `subject`
  and `description` but no threaded discussion (Phase 5).
- No SLA engine yet — `Ticket` has no due-date/breach tracking (Phase 6).
- No bulk ticket operations (bulk assign, bulk close, bulk tag).
- Assignment is single-assignee only; no multi-assignee/watchers model.
- `TicketStatus`/`TicketPriority` are fixed system enums, not
  workspace-customizable (see ADR-005) — revisit only on genuine need.
- No SLA/queue-based auto-routing — queue assignment on ticket creation
  is caller-specified, not automatic.
