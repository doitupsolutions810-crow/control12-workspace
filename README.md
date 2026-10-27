# CONTROL12 Workspace

**User-facing ChatBot + Agent Orchestration Coding Workspace**

Backed by Trinity Core (AttestPipe cryptographic spine, Autonomous Cycle Kernel, Host-ONLY execution, Operational Bridge) and CONTROL12 FORGE.

## Features

- **Agent ChatBot** — every gated turn can be attested and run through the Cycle Kernel
- **Coding Workspace** — in-browser file read/write for agent-orchestrated coding
- **Forge Tool Spec** — submit portable tool definitions through AttestPipe → Host-ONLY → FORGE path
- **Live Status** — gate, receipts, bridge, forge URL
- **Explicit gates** — `ALLOW_AGENT_EXECUTION=true` required for forge / cycle / pipeline actions

## Quick start

```bash
cd control12-workspace
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: enable privileged agent actions
export CONTROL12_BASIC_AUTH_USER=workspace-operator
export CONTROL12_BASIC_AUTH_PASSWORD='<set-a-strong-secret>'
export ALLOW_AGENT_EXECUTION=true
export CONTROL12_FORGE_URL=http://localhost:3001

# Run (from app/ or with PYTHONPATH)
cd app
uvicorn main:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080

## Authentication boundary

All routes except GET /api/health require HTTP Basic authentication configured with both CONTROL12_BASIC_AUTH_USER and CONTROL12_BASIC_AUTH_PASSWORD. If either value is absent, protected routes return HTTP 503 rather than silently running unauthenticated. Incorrect or missing credentials return HTTP 401.

Use this only behind HTTPS or a trusted private ingress; Basic credentials are not encrypted by the authentication scheme itself. Keep credentials in the deployment secret manager, not in source control. ALLOW_AGENT_EXECUTION=true is an additional capability gate, not a substitute for authentication.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Workspace UI |
| GET | `/api/health` | Health + gate |
| GET | `/api/status` | Full system status |
| POST | `/api/chat` | ChatBot turn |
| POST | `/api/tools/forge` | Forge tool spec (gated) |
| GET/PUT | `/api/code` | Coding workspace files |
| POST | `/api/agent` | Cycle / pipeline / status actions (gated) |
| GET | `/api/receipts` | Recent attestation receipts |

## Control12 bounds

- Production fabric apply remains disabled by default
- Host-ONLY: no implicit network from the execution boundary
- Training and model promotion stay behind human confirmation gates
- Cryptographic governance (receipts, epochs) — not promises

Control704 · Avrone Due’Krey · Control12-lattice-op
