# CONTROL12 v0.26.8 — competitive swarm re-award recovery evidence

**Date:** November 10, 2026 (America/Detroit). **Status:** draft review only. No merge, deployment or production PostgreSQL validation.

## Reproduced defect

In v0.26.7, a low-price competitive award reduced `task.cap`. When that assignment expired and the worker was disabled, another valid bidder with a higher bid became permanently ineligible, even though the mission had sufficient funds. The failing before-change fixture returned `409 no eligible bid`.

## Implemented correction

- Add immutable `Task.original_cap`, initialized at creation with the approved task ceiling.
- The auction may accept a newly submitted or previously recorded replacement bid up to this **original** ceiling, not the previous award price.
- In the mission-locked transaction, select the cheapest eligible bid whose cost is also affordable from the mission's **current** available funds plus the task's existing reservation. Change `mission.reserved` by `new_cost - current_cap`, then update `task.cap`, assigned agent and audit together.
- Reject unfunded re-awards rather than overspending. Retain original cap across renew/reap/reassignment; preserve receipt and lease semantics.
- Readiness verifies the new column and CHECK constraint `ck_tasks_original_cap`.

**Migration:** [0005_v0268_original_award_ceiling.sql](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/migrations/0005_v0268_original_award_ceiling.sql) adds a non-null column, conservatively backfills existing rows from their currently stored cap and enforces `original_cap >= cap`. The higher pre-award cap for historical tasks is unknowable and must **not** be guessed. Apply only after migration 0004, with backup, write drain and staging qualification. PostgreSQL was not available to execute this migration.

## Accountable sources

| Resource | Verified claim |
|---|---|
| [Core patch from v0.26.7](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/integrations/patches/CONTROL12_v0267_to_v0268_core.patch) | Reviewable targeted source changes for original cap and mission reservation rebalancing |
| [Host re-award contract cases](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/tests/test_control12_v0268_reaward_contract.py) | 58 offline adapter/HTTP signature, authorization, transport and ACK tests |
| [Boundary test workflow](https://github.com/doitupsolutions810-crow/control12-workspace/blob/integration/control12-v0263-boundary-2026-11-10/.github/workflows/control12-boundary.yml) | Python 3.11/3.12/3.13 on relevant push/PR |
| [Draft PR #8](https://github.com/doitupsolutions810-crow/control12-workspace/pull/8) | Proposed integration branch and review boundary |

## Standalone runtime evidence (not vendored into this repository)

The local v0.26.8 release includes **1,012 test cases across 22 test files**, all passing in isolated file runs (0 failures, 0 errors, 0 skips): 818 existing v0.26.7 cases plus **194** new recovery/migration cases. The 194-case suite passed independently, including in a clean extraction. The clean extracted ZIP was integrity-verified and all **1,012** cases passed across 22 independent file runs there too.

Two combined/unified run attempts stalled in older concurrency-heavy tests; **no unified 1,012-case run is claimed**, and a combined coverage-instrumented run stalled so **no v0.26.8 coverage percentage is claimed**. A package-local fail-closed test runner retains per-file logs and JUnit evidence. The full v0.26.7-to-v0.26.8 source patch was applied independently and **11 changed/new source files** matched byte-for-byte.

**Release ZIP (chat artifact, not a GitHub release):** `AVRONE_CONTROL12_v0.26.8_COMPETITIVE_RECOVERY_1012_TESTS.zip`. SHA-256: `1b7469eca23baeb19530e0ac0d60553f3e0833d3ad09f957228fafbe147f851a`. It contains **93 entries**, including an accountable SHA-256 registry of **92 files**, aggregate JUnit and independent clean-extraction JUnit. All registered hashes and ZIP integrity were checked.

## Remaining gates

No actual PostgreSQL 0005 migration, no two-replica database race verification, no v0.25 live gateway, no worker-side attestation, mTLS/KMS or external provider effects were tested. The host CI validates the independent adapter tests and Workspace, **not** the complete 1,012-case runtime package. Keep PR draft and avoid production deployment until these are qualified.
