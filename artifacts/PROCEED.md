# Proceed status — 2026-08-15

## Live (sandbox process mode)

- Workspace: http://127.0.0.1:8080/
- VM Browser: http://127.0.0.1:8080/vm-browser
- Gateway: http://127.0.0.1:3010/api/health

## Gates

| Check | Result |
|-------|--------|
| Child lattices | 9 |
| Forge BuildContinuity | ok |
| Horizon | definition_of_done true, score 1.0 |
| Procure T0–T2 | ok |
| Ship plan | no failed steps |
| Version | 1.0.0-ship |

## Public

- Repo: https://github.com/doitupsolutions810-crow/control12-workspace
- Portal: docs/index.html (enable GitHub Pages → Actions)
- Expected Pages URL: https://doitupsolutions810-crow.github.io/control12-workspace/

## Your machine / phone

```bash
export ALLOW_AGENT_EXECUTION=true
./run.sh   # or scripts/deploy.sh process
npx localtunnel --port 8080
```
