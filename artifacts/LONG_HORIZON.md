# Long-Horizon Agent Clusters

Real multi-step execution engine: `trinity-core/orchestration/long_horizon.py`

## Steps (no mocks)

1. **attest_goal** — AttestPipe receipt + epoch binding
2. **brain_energy_deploy** — Neural Network Brain energy deployment
3. **brain_recursive_learn** — real shard replication + conflict learning
4. **cycle_decide** — Autonomous Cycle Kernel INGEST→…→EXECUTE
5. **host_only_gate** — explicit Host-ONLY execution gate
6. **forge_package_intent** — FORGE tool spec + real HTTP POST when FORGE is up
7. **codex_persist** — Eternal Codex governed + training records
8. **quarantine_check** — Quarantine Stack latency/SDA stress

## Run

```bash
export ALLOW_AGENT_EXECUTION=true
cd artifacts
PYTHONPATH=trinity-core python3 -m orchestration.long_horizon "your goal"
# or via Workspace API:
# POST /api/agent {"action":"long_horizon","payload":{"goal":"...","depth":8}}
```

## Verified run

See `long-horizon-summary.json` — status **completed**, depth 8, real receipts and cycle IDs.

Control704 · Avrone Due’Krey · Control12-lattice-op
