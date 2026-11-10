# AVRONE CONTROL12 signed gateway integration (v0.26.3 candidate)

**State:** reviewable adapter committed; not deployed, and not merged to main.
The integration module is `integrations/control12_gateway.py`; the regression
suite is `tests/test_control12_gateway_contract.py`. CI runs on every push
to the integration branch and on pull requests affecting these files.

## Important API distinction

The existing `doitupsolutions810-crow/Avrone` host platform bridge
(`plugins/platform_bridge.py`) targets an **independent AVRONE Runtime**
API. Its `/v1/tasks` and `/v1/swarms` endpoints require a bearer tenant
API key and phase-specific idempotency receipts.

**CONTROL12 v0.26.2 is not that API.** It uses:
- HMAC-signed scoped tenant/principal request headers and a one-use nonce
- `POST /v1/missions` and `POST /v1/missions/{id}/tasks`
- `POST /v1/tasks/claim-next`, `renew`, `complete`, `fail`
- distinct stored mission and task records, but no `/v1/swarms` creation path

Do not direct the existing AVRONE Runtime bearer token, replay IDs, or
`/v1/swarms` calls to CONTROL12. Configure separate ingress routes,
signing material, principal permissions and target selection. A real agent
worker executes its own task; creating orchestration records is not execution.

## Trust and authorization

Only the trusted host/gateway may instantiate `Control12Gateway` with
the signing secret. No agent, untrusted tool input, browser, model output,
or external Replit App may receive the key. The adapter allows only listed
operations and path templates. It refuses redirects, bearer-in-URL,
non-loopback cleartext HTTP, unsupported compression, ambiguous response
JSON, or responses over 64 KiB; it disables environment proxy inheritance.
HMAC canonicalization matches the source of CONTROL12 v0.26.2.

The adapter never retries mutation requests, because CONTROL12 creation
endpoints **lack stable idempotency receipts**. For a timed-out write,
`GatewayError.ambiguous` is true: stop and reconcile task/mission state
using privileged read paths, or add server-side durable idempotency before
automatic retry support. External side effects require independent
worker-level idempotency and attestation.

## Verification and source registry

Sources reviewed from the connected GitHub owner:
- [Avrone PR #26](https://github.com/doitupsolutions810-crow/Avrone/pull/26):
  current draft swarm bridge hardening and independent Runtime verifier
- [avrone-daemon PR #24](https://github.com/doitupsolutions810-crow/avrone-daemon/pull/24):
  daemon bridge port and trial record idempotency
- [Avrone PR #22](https://github.com/doitupsolutions810-crow/Avrone/pull/22):
  previously merged platform integration
- [control12-workspace main](https://github.com/doitupsolutions810-crow/control12-workspace):
  existing dedicated control-plane workspace

The local source archive for CONTROL12 v0.26.2 was tested with 323
baseline cases plus 28 new boundary tests and 17 ASGI adapter tests,
total **368 passing tests**. Those results are local evidence, not
proof of GitHub CI completion. GitHub Actions must complete on this
commit before merging, and deploy only after an isolated PostgreSQL
and live authenticated gateway qualification.

## Remaining review gates

1. Verify GitHub Actions on this PR's head SHA across Python 3.11–3.13.
2. Execute the adapter behind the authenticated v0.25 gateway with
   workload identity and private network allowlists.
3. Run disposable PostgreSQL multi-process races and migration qualification.
4. Implement durable creation idempotency or explicit operator reconciliation.
5. Add task result attestation and downstream effect deduplication.
6. Confirm least-privilege secrets and audit integrity before a production rollout.

## Reproducibility

```sh
python -m pip install 'pytest>=8,<10' 'httpx>=0.27,<1'
python -m compileall -q integrations/control12_gateway.py tests/test_control12_gateway_contract.py
python -m pytest -q tests/test_control12_gateway_contract.py
```

This repo's workflow does not fetch arbitrary release archives or secrets
from other repositories, and it never deploys production workloads.
