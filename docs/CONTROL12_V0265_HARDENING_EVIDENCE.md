# CONTROL12 v0.26.5 runtime + host adapter test evidence (2026-11-10)

**State:** standalone local runtime package plus draft review patch. Not merged and not deployed.

## Reproducible local results

- v0.26.4 baseline: 430 passing tests
- v0.26.5 complete suite: **564/564 passing** (134 new collected cases, 0 failures, 0 errors, 0 skips)
- Scope: Python 3.13, SQLite / FastAPI TestClient and HTTPX MockTransport; **not live PostgreSQL**
- Additional metamorphic byte-fuzzing: **138 different body mutations inside one collected pytest case**, each rejected without consuming the original signed request's replay nonce
- Separate scoped coverage run: **510/510 passed**, 95% runtime-core and 98% adapter branch-inclusive coverage. Two multiprocessing/concurrency modules excluded from instrumentation *only*; they were included in the passing full run
- Repeated suite passed 536/536 twice before the last 28 new tests were added. One earlier run stalled near completion and was not counted as pass evidence

## Defects fixed

1. **NaN/Infinity security limit bypass:** setting max_age or max_body_bytes to NaN causes ordinary numeric comparisons to return false. The patch enforces bounded genuine integer security limits and bounded finite maintenance intervals.
2. **Misleading signed Content-Encoding:** signed JSON with gzip/deflate/br headers was previously accepted as if identity bytes; now rejects unsupported encodings before persisting nonce.
3. **Unsupported JSON Content-Type:** malformed, duplicate or contradictory content types and charsets now fail closed before nonce insertion.
4. **Transfer-Encoding confusion:** rejects repeated and non-chunked transfer encodings and TE/CL conflicts; still permits legitimate chunked ASGI flow.
5. **Adapter admin scope mismatch:** host-only adapter now supports trusted `admin:*`, consistent with runtime check().
6. **Fault-isolated recovery:** regressions verify audit-failure rollback, nonce-pruning rollback, and no duplicate lease-expiration events after reaper restarts.

## Source locations and evidence

- [Runtime v0.26.4 -> v0.26.5 source patch](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/patches/CONTROL12_v0264_to_v0265.patch)
- [Host adapter wildcard authorization fix](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/control12_gateway.py)
- [Host adapter test suite](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/tests/test_control12_v0265_adapter_contract.py)
- [Hosted boundary matrix](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42927319856) — success on Python 3.11, 3.12, 3.13
- [Commercial workflow](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42927319823) — success on patch commit e897652184f87288d48954d8affb6327cca3c165
- [Draft PR #8](https://github.com/doitupsolutions810-crow/control12-workspace/pull/8)

The full 564-test standalone runtime package, JUnit, coverage XML and SHA-256 source registry are delivered as a local ZIP in the user chat, **not uploaded to GitHub as a release asset**. GitHub CI validates the host adapter tests only, not all 564 local runtime tests.

## Production gates that remain open

- Real PostgreSQL transactional migration and multi-replica contention verification
- Signed gateway and service-to-service identity/mTLS integration
- Durable idempotency receipts for mission/task creation; no automatic retries of uncertain POST results
- External worker execution, result attestation, deduplicated third-party side effects
- Secret/KMS, ingress policies, independent immutable audit anchoring

Operator changes required for tightened v0.26.5 config: max_age 1..3600 (int), max_body_bytes 1024..16777216 (int), reaper_interval 0..86400 (finite numeric). Invalid settings now deliberately fail startup.
