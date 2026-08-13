# HarnessOpt under Control12

Unifying equation:

```
z_{t+1} = O(A_optimizer, z_t, Evaluate(z_t))
```

with `z = H = (P, K, T, μ, Φ, C, V, B)` mapped to the Trinity / Workspace stack.

## Module

`trinity-core/orchestration/harness_opt.py`

## Loop (real)

1. **Seed H0** — serialize prompts, skills, tools, memory, context, control flow, verification, constraints
2. **Evaluate** — LongHorizonCluster runs → evidence `D_k = {(x, τ, r)}` with real rewards
3. **Hypothesize** `q_k` — pattern analysis over traces (forge unreachable, step fails, low reward)
4. **Design** `Δh` — bounded single-component edit
5. **Apply** — in-memory H update + AttestPipe receipt + Host-ONLY gate
6. **Persist** — `storage/harness_opt/H_current.json` + history.jsonl

## API

```json
POST /api/agent
{"action": "harness_opt", "payload": {"depth": 5}}
{"action": "harness_status", "payload": {}}
```

## Verified round

See `harness-opt-round.json` — status **applied**, H0 → H-dh-*, avg_reward 0.705, production apply remains false.

Control704 · Avrone Due’Krey · Control12-lattice-op
