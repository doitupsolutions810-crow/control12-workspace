# CONTROL12 v0.26.7 — lease-bound settlement acknowledgements and hostile replay tests

**Date:** 2026-11-10 (America/Detroit). **State:** additive review patch and forward schema migration; no merge or deployment.

## What changed

v0.26.6 handled durable mission and task *creation* receipts, but an external worker losing its HTTP acknowledgement for `POST /v1/tasks/{id}/complete` or `/fail` could not recover that exact result. v0.26.7 adds an immutable settlement receipt committed in the **same transaction** as mission budget accounting, terminal task state and audit events.

The receipt records tenant, task, authenticated worker principal, **SHA-256 of lease token** (never plaintext), outcome, normalized payload hash and frozen original response. The `(tenant, task_id)` uniqueness constraint prevents more than one terminal result. Identical signed retries with a fresh gateway nonce return HTTP 200 and `Idempotent-Replayed: true`. Changed cost, result, outcome, lease, principal or tenant fails closed (typically 409 or 404).

**Compatibility change:** an identical repeat settlement previously returned 409. With a persisted receipt it now returns 200 and the original response, not an additional charge. Legacy terminal tasks without historical receipts continue to return 409.

## Accountable source and evidence registry

| Resource | Origin and purpose |
| --- | --- |
| [CONTROL12 v0.26.6 to v0.26.7 core patch](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/patches/CONTROL12_v0266_to_v0267_core.patch) | Runtime implementation review (other changed source files and full tests live in standalone release ZIP) |
| [Forward migration 0004](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/migrations/0004_v0267_settlement_receipts.sql) | Tenant-bound FK, unique settled task, digest and outcome constraints; not run against live PostgreSQL |
| [Host settlement contract regression](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/tests/test_control12_v0267_settlement_contract.py) | Host caller signatures, fresh nonce, no automatic write retry on uncertain network failures, explicit HTTP 409 |
| [PR #8](https://github.com/doitupsolutions810-crow/control12-workspace/pull/8) | Review and governance boundary |

Standalone package `AVRONE_CONTROL12_v0.26.7_SETTLEMENT_RECEIPTS_818_TESTS.zip`, SHA-256 `a4acbad7d4a62466c78f463d20f6b9571b5df6665919ee2cb8ca89f85f0261c6`, contains **818/818 passing tests** (baseline 651; +167 collected cases) and per-file SHA-256 registry. It also contains a complete source patch including altered compatibility tests and new local tests; the patch was applied to v0.26.6 and **12 changed/new files matched byte-for-byte**. The ZIP is a *chat artifact*, not a GitHub release attachment.

Additional verification: 816 pre-final collected cases passed in independent file partitions; two new spawn-process settlement cases passed separately; all 818 then passed in one 56.95-second unified run. A first unified attempt stalled and was not counted as passing. Scoped, branch-inclusive coverage run: **759 passed, 94% runtime-core, 98% host-adapter**, with four concurrency/process test modules excluded from instrumentation only. It reported two SQLite resource warnings; overall measured coverage is 86% because the unexecuted PostgreSQL qualification harness contributes 0%.

## Latest tested GitHub adapter CI

[Boundary Python matrix](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42934159172) and [Commercial CI](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42934159101) both passed on bridge-workflow commit `26bfe4828543ca8da858ec75d9c898d99b4a352d`. The hosted workflow runs **adapter and Workspace tests**, not the entire standalone 818-case suite. The complete release is not vendored into the Workspace repository.

## Qualification gates before production

Apply the mandatory `0004` migration after `0003` on an isolated, backed-up PostgreSQL deployment. Then test two or more independent API replicas settling the same lease with identical and conflicting outcomes under the actual transaction isolation level, database failover, partial connection loss and repeated recovery. Validate real gateway HMAC and service identity/mTLS, worker result attestation and downstream provider-side effect deduplication. Design retention and restricted read access for indefinitely stored settlement results. No live PostgreSQL, external workers or third-party provider effects were tested in this release.

**Keep this PR draft.** Source-integrity hashes and local SQLite concurrency cannot certify production PostgreSQL behavior.
