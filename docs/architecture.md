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
    └── LLM access (Phase 6+): host.docker.internal:11434/v1 via host-gateway
```

The CSP stack never shares database, cache, network, volume, secret, or migration history with AI-project-SRV.

## Backend module layout

```text
apps/api/app/
├── main.py
├── core/              # config, security, exceptions
├── db/                # SQLAlchemy, Redis, declarative base
├── models/            # identity, CRM, ticketing, communications ORM
├── schemas/           # Pydantic request/response DTOs
├── repositories/      # DB access only
├── services/          # deterministic business logic + audit
├── authz/             # deny-by-default permissions/dependencies
├── api/v1/            # HTTP routers
├── middleware/        # correlation/security middleware
├── observability/     # structured logging
└── ai/                # reserved for Phase 6 LLMGateway
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

`InternalNote` is a separate table and API surface rather than `Message.is_internal`. This is a deliberate security boundary: customer-visible message queries cannot return internal notes by accidentally omitting a visibility predicate. Internal-note endpoints and their attachments require `tickets.internal_comment`.

Attachments are capped at 5 MiB in Phase 5, carry SHA-256 integrity metadata, and are stored in CSP's own PostgreSQL database. Moving blob storage to an object store is a Phase 8 optimization and must preserve the same IDs and authorization checks. See ADR-006.

Phase 5 provides deterministic storage/recording of inbound and outbound messages. It does not send email/chat traffic or poll providers; external channel adapters are future integrations.

## Ticket / SLA / AI flow (Phase 6, advisory-only)

```text
Ticket event → deterministic service layer → optional AI suggestion
  → redaction / bounded LLM gateway
  → suggestion stored as proposal
  → operator + authorization gate
  → deterministic mutation → audit event
```

LLM failure must not break CRM/ticket/communications flows. AI must never independently close tickets, change permissions, delete customers, alter SLA policy, send external messages, execute shell commands, or modify infrastructure.

## Phase roadmap

- **Phase 0 — Discovery** ✅
- **Phase 1 — Architecture** ✅
- **Phase 2 — Foundation** ✅ auth, tenancy/RBAC, health, logging, audit, tests, CI, Compose.
- **Phase 3 — CRM** ✅ organizations, clients, contacts, search, pagination, IDOR guards (ADR-004).
- **Phase 4 — Service Desk** ✅ tickets, state machine, queues/categories/tags, assignment history, RBAC, audit (ADR-005).
- **Phase 5 — Communications** ✅ conversations, channel abstraction, inbound/outbound messages, separate internal notes, attachments, audit and tenant/ticket IDOR guards (ADR-006).
- **Phase 6 — Operations + AI**: tasks, SLA engine, notifications, knowledge base, bounded/advisory local-LLM features (`LLMGateway`, redaction, circuit breaker, per-workspace rate limits).
- **Phase 7 — Frontend**: React/Vite operator UI and client portal.
- **Phase 8 — Production hardening**: tenant/security review, performance/indexes, metrics/traces, object-storage evaluation, CI supply-chain hardening, build identity and final documentation.

## Current non-goals

- No external email/chat provider delivery or polling yet.
- No SLA engine or automated queue routing yet.
- No AI wiring yet; `LLM_ENABLED=false` remains the default until Phase 6.
- No real operator/client frontend yet; nginx placeholder remains until Phase 7.
- No bulk ticket operations or multi-assignee/watchers model.
