# ADR-007: Advisory AI boundary

## Status

Accepted for Phase 6A (`v0.4.0-alpha`).

## Context

CSP needs local-LLM assistance for support operators without allowing probabilistic output to bypass deterministic authorization, ticket lifecycle, audit, communications, or infrastructure controls.

## Decision

1. `LLM_ENABLED=false` remains the default. AI failure or disablement never blocks CRM, ticketing, communications, or knowledge-base operations.
2. The LLM is reached only by the backend through `LLMGateway`; browsers and clients never call the model directly.
3. The gateway exposes no mutation or execution tools. It can return proposal text only.
4. Prompt content is redacted for email addresses and phone-like values before transmission to the LLM endpoint. Only a SHA-256 hash of the redacted prompt is persisted with the suggestion; raw prompt context is not stored in `ai_suggestions`.
5. AI output is persisted as an immutable `AISuggestion` proposal. Creating a suggestion does not change ticket status, assignment, priority, permissions, knowledge articles, communications, or infrastructure.
6. `ai.assist` is a separate deny-by-default permission. Client-role memberships receive no internal AI permission.
7. A per-workspace completed-suggestion rate limit bounds model usage. The default is 12 suggestions per minute and is environment-configurable.
8. `LLMGateway` includes a process-local circuit breaker. After a configurable number of consecutive gateway failures it rejects further LLM calls during a cooldown period, while deterministic application flows remain available. Breaker state is intentionally not shared across API workers in Phase 6A; distributed coordination can be evaluated during Phase 8 hardening.
9. AI context is bounded to the target workspace/ticket and up to five published knowledge articles from the same workspace.
10. External message sending, shell execution, infrastructure changes, account/role changes, ticket closure and other mutations remain exclusively deterministic application actions behind their existing permissions.

## Consequences

- Operators can request summaries, reply drafts and next-step proposals without giving the model agency over the system.
- Repeated model-endpoint failures are bounded by the circuit breaker instead of generating an unbounded stream of outbound calls.
- CSP can use the host-local OpenAI-compatible LLM endpoint without sharing any database, Redis namespace, Docker network, volume or secret with AI-project-SRV.
- Phase 6B may add SLA/tasks/notifications, but those systems must remain deterministic; AI may propose, never apply, their state changes.
