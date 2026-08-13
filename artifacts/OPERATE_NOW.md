# Operate CONTROL12 now

## Live URLs (this machine)

| What | URL |
|------|-----|
| **ChatBot + coding** | http://127.0.0.1:8080/ |
| **VM Browser dashboards** | http://127.0.0.1:8080/vm-browser |
| **Gateway health** | http://127.0.0.1:3010/api/health |

Use **http** (not https) unless you add a TLS proxy.

## Start / stop

```bash
export ALLOW_AGENT_EXECUTION=true
export PYTHONPATH=/path/to/trinity-core
export CONTROL12_FORGE_URL=http://127.0.0.1:3010

./control12-workspace/scripts/deploy.sh process

c12ctl gateway start
c12ctl workspace start
c12ctl workspace stop
c12ctl gateway stop
```

## ChatBot commands

```
/help /status /reach /cycle /forge MyTool /spawn MyLattice /dashboard /evaluate <goal>
```

## CLI

```bash
c12ctl status
c12ctl reach
c12ctl forge --name Demo --desc "..."
c12ctl evaluate --goal "..." --depth 5
c12ctl children list
c12ctl procure
c12ctl ship
```

## Docker

See artifacts/DOCKER_COMPOSE.md

## Published repo

https://github.com/doitupsolutions810-crow/control12-workspace
