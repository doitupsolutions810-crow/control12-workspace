# CONTROL12 Commercial v1

A deployable commercial control plane for release assurance. This package turns the existing CONTROL12 verification lineage into a customer-facing workflow: organizations, projects, releases, evidence, policy status, deployments, usage metering, audit events, and deterministic verification receipts.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080`.

For production writes, set `CONTROL12_ADMIN_KEY` and send it as `X-Control12-Key`. Configure `GITHUB_WEBHOOK_SECRET` before enabling `/api/github/webhook`.

## Docker

```bash
docker compose up --build
```

The SQLite volume is persistent. The package also ships a Supabase migration for managed Postgres/Auth/RLS state.

## Release workflow

1. Create an organization.
2. Create a project and optionally record its GitHub repository URL.
3. Create a release with commit and artifact digest references.
4. Attach evidence from CI/security systems.
5. Run policy evaluation with `POST /api/releases/{id}/verify`.
6. Export `/api/releases/{id}/receipt`.
7. Production deployment records are blocked unless policy status is `pass`.

The built-in verifier does not pretend to run external scanners. Missing external evidence remains `pending`, and failed evidence blocks the release.

## Managed production state

Apply `supabase/migrations/20260917_001_commercial.sql` to the CONTROL12 Supabase project. It creates organization membership, project, release, evidence, deployment, usage, and audit tables with row-level security.

## Packaging

```bash
python scripts/package_release.py
```

This creates a ZIP, SHA-256 file, and per-file manifest under `dist/`.
