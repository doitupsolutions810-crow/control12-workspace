# First published tool — Workspace Attestor v1

**Status:** attested intent, ready for CONTROL12 FORGE packaging

| Field | Value |
|-------|--------|
| Receipt (prefix) | `4b3004ca6283cf2cd37abe73ed35e037` |
| Cycle ID | `cycle-0-7832724a` |
| Host gate | allowed (host_only, network denied_implicit) |
| Forge endpoint | `http://localhost:3001/api/forge` |

## Capabilities
attest, package, verify, export_receipt, workspace_bind

## Path closed
**Chat / intent → AttestPipe receipt → Cycle Kernel (INGEST→…→EXECUTE) → Host-ONLY gate → FORGE-ready portable tool spec**

## Next
1. Start FORGE: `cd control12-ops/forge && cp .env.example .env && ./validate.sh && docker compose up --build`
2. POST the tool object in `workspace-attestor-v1.json` to `POST /api/forge`
3. Store returned encrypted portable artifact under the next AttestPipe epoch

Control704 · Avrone Due’Krey · Control12-lattice-op
