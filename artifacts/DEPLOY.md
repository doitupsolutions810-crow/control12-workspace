# CONTROL12 Deploy

## Process mode (sandbox / host)

```bash
export ALLOW_AGENT_EXECUTION=true
./scripts/deploy.sh process
```

Surfaces:
- http://127.0.0.1:8080/ — ChatBot + coding workspace
- http://127.0.0.1:8080/vm-browser — Life-stack dashboards
- http://127.0.0.1:3010/api/health — Tool network gateway

## Docker mode

```bash
./scripts/deploy.sh docker
# or: docker compose up -d --build
```

## Gates

- `ALLOW_AGENT_EXECUTION=true` required for agent actions
- Host-ONLY remains enforced
- Production apply stays false
