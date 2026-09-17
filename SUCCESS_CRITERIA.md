# CONTROL12 success criteria

Hosted GitHub Actions is **not** a required gate.

## Required

1. Repo has a dispatchable Commercial CI workflow.
2. Lab/commercial mode is explicit (`workflow_dispatch.inputs.mode`).
3. Commercial mode fail-closed without `CONTAINER_KEY_BASE64`.
4. Self-hosted target exists: `[self-hosted, linux, control12]`.
5. Swarm VM stack exists (doitupsolutions810-crow/swarm-vm-runner).

## Degraded (allowed)

- Hosted job `conclusion=failure` with `runner_id: 0` / empty `runner_name` / no logs.
- `ubuntu-slim` / `ubuntu-24.04` / `ubuntu-latest` assignment miss.
- GitHub App PEM not yet installed (lab only; production still fail-closed).

## Optional

- Idle self-hosted runner on a VM.
- Content host `:8088`.
- Second runner replica for concurrency.

Prove locally: clone swarm-vm-runner and run `./scripts/prove-success.sh`.
