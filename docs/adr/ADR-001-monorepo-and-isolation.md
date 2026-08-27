# ADR-001: Monorepo layout, independent from AI-project-SRV

## Status
Accepted

## Context
This project must be operationally independent from the existing
AI-project-SRV repository, while both run on the same host (`srv-ai`).
We need a repository layout that supports a FastAPI backend and a
React/Vite frontend evolving together, without any shared Git history,
Compose project, or infrastructure with AI-project-SRV.

## Decision
Use a single new repository (`apps/api`, `apps/web`, `docs/`, root
`docker-compose.yml`), structurally similar in *shape* to
AI-project-SRV (for operator familiarity) but with:
- a distinct Compose project name (`csp`),
- distinct Docker network/volume/container names,
- a distinct Postgres database/user (`csp`/`csp`, not `aisrv`),
- its own Git repository and CI pipeline.

## Consequences
- Operators familiar with AI-project-SRV's conventions (Makefile
  targets, `.env.example` shape, ADR practice) can navigate this
  project quickly.
- No mechanism exists for this project to accidentally mutate
  AI-project-SRV's database, cache, volumes, or containers — isolation
  is structural, not just a runtime convention.
- Any future integration between the two systems must go through a
  documented, versioned API or event contract (never direct DB access
  or shared Compose network membership).
