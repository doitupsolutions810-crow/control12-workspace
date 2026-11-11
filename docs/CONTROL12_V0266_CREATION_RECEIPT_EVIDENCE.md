# CONTROL12 v0.26.6 — authenticated creation receipts / qualification evidence

**Date:** 2026-11-10 (America/Detroit). **State:** review-only; no merge, deployment, live PostgreSQL test or external-agent effects.

## Contract

The independent CONTROL12 v0.26.6 reference service adds durable idempotency receipts for exactly two creation routes: `POST /v1/missions` and `POST /v1/missions/{mission_id}/tasks`. A signed `Idempotency-Key` of 16–128 printable ASCII letters/numbers/periods/hyphens/underscores is bound as `\nidempotency-key:<key>` after the existing HMAC canonical request. Unsigned or substituted headers are rejected. Gateway nonces MUST be fresh for every retry.

The uniqueness namespace is `tenant + principal + POST + resource path + request key`. Under the deployed database's transaction guarantees, the creation resource, budget reservation, audit event and response receipt commit atomically. Replaying the same normalized validated body yields the original creation response; changed data yields 409. `GET /v1/receipts/{key}` requires `mission:read` and only exposes receipts belonging to the current signed tenant/principal.

The existing keyless API remains backward-compatible unless the operator explicitly enables `AVRONE_REQUIRE_IDEMPOTENCY_KEYS=true` (missing keys on the two creation routes then yield HTTP 428). **Only enable this after migration 0003 and caller upgrades.** The host adapter never automatically retries ambiguous mutations; privileged callers can reconcile receipts and then deliberately retry with the same stable key.

## Source registry

- [Host-only signed gateway adapter](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/control12_gateway.py) — now includes signed creation keys and receipt readback
- [Remote adapter protocol tests](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/tests/test_control12_v0266_receipt_signatures.py) — exact HMAC/key binding, invalid key fuzzing, allowlisting, lost ACK single-attempt
- [Forward PostgreSQL migration](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/migrations/0003_v0266_creation_receipts.sql) — schema source only, **not executed on a PostgreSQL server**
- [Workflow](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/.github/workflows/control12-boundary.yml) — runs remote adapter tests for Python 3.11, 3.12 and 3.13 on relevant pushes and pull requests
- [Draft PR #8](https://github.com/doitupsolutions810-crow/control12-workspace/pull/8) — changelog/review boundary

## Local runtime evidence (separate packaged release)

- **651 full local tests passed**, 0 failures/errors/skips, Python 3.13 with real temporary SQLite databases, ASGI tests and separate Python processes. **87 new collected pytest cases** since v0.26.5 (564).
- After extracting the standalone release ZIP into a fresh directory, **651/651 tests passed again**.
- A separate, scoped **594-test** coverage run passed: **94% runtime core**, **98% host adapter**, 94% combined branch-inclusive coverage. Concurrent/multiprocess test files were excluded from coverage *instrumentation only*; they were included in the full 651-test evidence.
- The release ZIP `AVRONE_CONTROL12_v0.26.6_DURABLE_RECEIPTS_651_TESTS.zip` has SHA-256 `cac6d607ec2d29dc52aaaf05dff70e40de6f47c241f86e42dfc0753780a2f276`. The ZIP is a chat artifact, **not a GitHub release attachment**.
- Its source registry inventories 46 file hashes; a v0.26.5-to-v0.26.6 patch reapplied cleanly to the prior release and nine modified source files matched byte-for-byte.

## Last observed remote CI

- [Boundary workflow](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42931133741): Python 3.11/3.12/3.13 all succeeded, on migration commit `2ab1f5e7531f0a591982d9eb4bb9287ecaa2651d`.
- [Commercial CI](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42931133945): succeeded on same commit.

Remote CI covers the independent host adapter/Workspace; it does **not** run the full 651 tests against the complete standalone runtime package. The full runtime patch and 87 new local test cases remain in the local release ZIP, not vendored into this Workspace repository.

## Open production gates

Before merge/deploy: run migration 0003 on an isolated PostgreSQL clone with multi-replica same-key collisions and crash/retry tests; qualify the real signed ingress, workload identity/mTLS, lease-result attestation, provider-side effect deduplication, secret/KMS policy and receipt retention. Creation receipts do not provide exactly-once external agent execution. Keep PR draft until these gates are reviewed.
