# SHIP — CONTROL12 1.0.0-ship

## Quick start
```bash
export ALLOW_AGENT_EXECUTION=true
export CONTROL12_API_TOKEN=$(openssl rand -hex 32)
./scripts/deploy.sh process
c12ctl procure
c12ctl ship
```

## Acceptance
`c12ctl procure` and `c12ctl ship` exit 0 (T0–T2). T3 container/k8s optional.

## Docs
See `artifacts/ship/` for SECURITY, PRODUCTION, LICENSE, PATENT_TECHNICAL_DISCLOSURE.
