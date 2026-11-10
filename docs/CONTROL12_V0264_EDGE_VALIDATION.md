# CONTROL12 v0.26.4 — extended edge-test evidence (2026-11-10)

## Local executable source

The v0.26.4 standalone source release extends the locally verified v0.26.3 suite from 383 to **430/430 passing** cases. It includes a separate runtime core patch at `integrations/patches/CONTROL12_v0262_to_v0264_core.patch` on this review branch.

The patch fixes three discovered ingress defects:

1. **UTF-16/UTF-32 autodetection:** `json.loads(bytes)` previously accepted alternate encodings of correctly signed JSON. v0.26.4 first calls `body.decode("utf-8", "strict")`.
2. **Eager unbounded stream materialization:** `await request.body()` was buffering all incoming bytes before the size check; v0.26.4 bounds each `request.stream()` chunk before accumulation and preserves the cached exact bytes for downstream request parsing.
3. **HTTP message framing ambiguity:** negative/nondecimal/mismatched `Content-Length`, duplicate length fields and simultaneous `Transfer-Encoding`/`Content-Length` are now rejected without creating records or consuming a nonce.

A previous hosted regression failed because the test fixtures used *literal backslash escape characters* instead of NUL and newline. That test bug was fixed in commit `28177bbfbff7dde14c9b62b3d234cea01a92acc4`; hosted CI passed on all three Python versions afterward.

## Verification scope

- Full standalone local run: 430 passed, 0 failed, 0 errors, 0 skipped. Python 3.13, SQLite-backed FastAPI tests; JUnit produced.
- Additional runtime cases beyond v0.26.3: 47 (UTF-8/UTF-16/UTF-32, invalid octets, request HMAC tamper, nonce preservation, request streaming, TE/CL ambiguity, randomized budget settlement).
- Separate bounded coverage run: 376 tests passed; **94% runtime core** and **97% gateway adapter**. The multiprocessing/concurrency modules were excluded from this *coverage-only* run because instrumentation with the full suite stalled; both modules were included in the passing 430-test uninstrumented run.
- Host adapter tests added under `tests/test_control12_v0264_bridge_regression.py` (Unicode signature, malformed responses, exact one-attempt timeout behavior, status-code ambiguity). GitHub Actions runs them on Python 3.11, 3.12, 3.13.
- [Hosted CI for pushed PR head](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42924202220): three Python jobs succeeded.
- [Commercial CI for same SHA](https://github.com/doitupsolutions810-crow/control12-workspace/actions/runs/42924202126): succeeded.

## Unverified and not claimed

No live PostgreSQL instance, multi-replica worker service, external provider effect, or v0.25 production gateway was tested. The patch file is a reviewable *source patch*, not a deployed application or a claim that `control12-workspace` hosts the entire runtime. The independent AVRONE Runtime bearer-key bridge and CONTROL12 signed-HMAC API remain separate.

Production still requires qualified gateway framing, workload identity/mTLS, durable mission/task creation idempotency, result attestation, policy/permissions review, isolated PostgreSQL migration/concurrency testing and independent audit integrity checks.

## Source registry

GitHub authority:
- [CONTROL12 workspace PR #8](https://github.com/doitupsolutions810-crow/control12-workspace/pull/8)
- [AVRONE Swarm PR #26](https://github.com/doitupsolutions810-crow/Avrone/pull/26)
- [avrone-daemon bridge PR #24](https://github.com/doitupsolutions810-crow/avrone-daemon/pull/24)

All linked work remains subject to its own review and production deployment gates.
