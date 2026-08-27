# RC1 acceptance checklist

Release: `v0.9.0-rc1`

## Repository gates

- [ ] Python 3.12 / Ruff / pytest / whitespace passes.
- [ ] Alembic upgrade/downgrade passes.
- [ ] React TypeScript typecheck + production build passes.
- [ ] Production compose manifest, shell syntax and release consistency pass.
- [ ] PostgreSQL backup / isolated restore rehearsal passes.
- [ ] Hardened production compose startup and smoke pass.
- [ ] Runtime `/health` reports `0.9.0-rc1` and the exact deployed git SHA.
- [ ] Operator `/` and customer `/portal.html` return HTTP 200.
- [ ] `/docs`, `/openapi.json` and `/redoc` are unavailable at the production edge.
- [ ] Metrics are not exposed without the configured bearer credential.

## Target-host gates before public exposure

- [ ] Real production secrets are generated outside the repository.
- [ ] External HTTPS origin and CORS value are correct.
- [ ] Reverse proxy/tunnel reaches only the loopback web listener.
- [ ] Host firewall and administrative access are reviewed.
- [ ] Redis host requirement `vm.overcommit_memory=1` is reviewed/applied as appropriate.
- [ ] A fresh database backup has passed restore verification.
- [ ] Encrypted off-host backup retention is configured.
- [ ] Deployed git SHA is recorded for rollback.

Repository CI can satisfy only the first section. The second section requires the real deployment host and external edge.
