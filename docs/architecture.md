# Architecture

## Deployment topology

```text
srv-ai (192.168.5.155)
├── AI-project-SRV stack (untouched, separate repo/compose project)
├── ai-lab stack (untouched — grafana/prometheus/qdrant/ollama/open-webui/…)
└── csp stack (this project)
    ├── network: csp_default, subnet 172.31.0.0/24
    ├── postgres (db "csp", volume csp_postgres_data)
    ├── redis (volume csp_redis_data)
    ├── api  — FastAPI, host port 8100 → container 8000
    ├── web  — nginx placeholder (Phase 7: React/Vite), host port 8180 → 80
    └── optional LLM — host.docker.internal:11434/v1 via host-gateway
```

The CSP stack never shares database, cache, network, volume, secret or migration history with AI-project-SRV.

## Backend module layout

```text
apps/api/app/
├── main.py
├── core/              # config, security, exceptions
├── db/                # SQLAlchemy, Redis, declarative base
├── models/            # identity, CRM, ticketing, communications, knowledge/AI, operations
├── schemas/           # Pydantic request/response DTOs
├── repositories/      # DB access only
├── services/          # deterministic business logic + audit
├── authz/             # deny-by-default permissions/dependencies
├── api/v1/            # HTTP routers
├── middleware/        # correlation/security middleware
├── observability/     # structured logging
└── ai/                # bounded advisory LLM gateway
alembic/               # CSP-only migration history
```

## Authorization request flow

```text
Request
  → correlation/security middleware
  → router
  → authenticated user
  → workspace membership
  → require_permission(code)
  → service-layer object/workspace validation
  → repository workspace-scoped query
  → audit + commit
  → response
```

Missing membership, missing permission, wrong-workspace object IDs and wrong-ticket nested IDs are intentionally normalized to non-disclosing 404 behavior where applicable.

## Communications model (Phase 5)

```text
Ticket
  ├── Conversation [channel: web/email/chat/phone/api]
  │     └── Message [inbound|outbound, customer-visible]
  │            └── Attachment
  └── InternalNote [operator-only]
         └── Attachment
```

`InternalNote` is a separate table and API surface rather than `Message.is_internal`. Internal-note endpoints and attachments require `tickets.internal_comment`. Attachments are capped at 5 MiB in Phase 5 and carry SHA-256 integrity metadata.

## Knowledge + advisory AI model (Phase 6A)

```text
Ticket + up to 5 published KnowledgeArticles from same workspace
  → permission: ai.assist
  → deterministic context assembly
  → email/phone redaction
  → workspace rate limit
  → process-local circuit breaker
  → LLMGateway (OpenAI-compatible, text proposal only)
  → immutable AISuggestion
  → audit event
  → operator reviews proposal
```

The LLM receives no mutation or execution tools. It cannot close/reassign tickets, change permissions, edit knowledge, send messages, execute shell commands or modify infrastructure. Only a SHA-256 hash of the redacted prompt and the returned proposal are persisted. `LLM_ENABLED=false` is the default. Repeated gateway failures open a configurable process-local circuit breaker; each API worker has independent breaker state in Phase 6A. See ADR-007.

Knowledge articles are workspace-scoped. Operators receive `knowledge.read` and `ai.assist`; supervisors receive `knowledge.write` in addition; the Client system role receives none of these internal permissions. The Phase 6A migration also upgrades grants for existing system roles, not only newly bootstrapped installations.

## Deterministic Operations model (Phase 6B)

```text
Ticket
  ├── SupportTask [open → done|cancelled]
  ├── TicketSLA
  │     ├── created_at → response/resolution deadlines from SLAPolicy
  │     ├── first OUTBOUND Message → first_response_at
  │     └── first audited resolved|closed transition → resolved_at
  └── Notification [recipient scoped to workspace membership]
```

SLA clocks are replayable from deterministic business history. They use ticket creation time as the origin and can be materialized later without moving the deadline. The evaluator derives historical response/resolution timestamps before deciding whether a warning or breach is due, and persisted anti-duplicate flags prevent repeated notifications for the same SLA objective. See ADR-008.

Default elapsed-time targets are materialized per priority when needed and may be replaced by supervisors/administrators using `sla.manage`. Phase 6B intentionally uses wall-clock minutes, not business-hour calendars. Notifications are in-app records only; external delivery remains an adapter concern.

AI does not participate in task transitions, SLA mutation/evaluation or notification creation. It may only produce advisory text under the Phase 6A boundary.

## Phase roadmap

- **Phase 0 — Discovery** ✅
- **Phase 1 — Architecture** ✅
- **Phase 2 — Foundation** ✅ auth, tenancy/RBAC, health, logging, audit, tests, CI, Compose.
- **Phase 3 — CRM** ✅ organizations, clients, contacts, search, pagination, IDOR guards (ADR-004).
- **Phase 4 — Service Desk** ✅ tickets, state machine, queues/categories/tags, assignment history, RBAC, audit (ADR-005).
- **Phase 5 — Communications** ✅ conversations, channel abstraction, inbound/outbound messages, separate internal notes, attachments, audit and nested IDOR guards (ADR-006).
- **Phase 6A — Knowledge + Advisory AI** ✅ knowledge articles, AI permissions, redaction, bounded context, immutable suggestions, local OpenAI-compatible gateway, workspace rate limit and process-local circuit breaker (ADR-007).
- **Phase 6B — Deterministic Operations** ✅ tasks, per-priority SLA policies, replayable SLA clocks, warning/breach evaluation, in-app notifications and operations RBAC (ADR-008).
- **Phase 7 — Frontend**: React/Vite operator UI and client portal.
- **Phase 8 — Production hardening**: tenant/security review, performance/indexes, metrics/traces, distributed breaker evaluation, object-storage evaluation, CI supply-chain hardening, build identity and final documentation.

## Current non-goals

- No external email/chat provider delivery or polling yet.
- No business-hours/holiday SLA calendar or automated queue routing yet.
- No autonomous AI actions; all AI output is advisory.
- No distributed LLM circuit state across multiple API workers yet; evaluate in Phase 8 if operationally justified.
- No external notification delivery adapter yet; notifications are in-app only.
- No real operator/client frontend yet; nginx placeholder remains until Phase 7.
- No bulk ticket operations or multi-assignee/watchers model.
