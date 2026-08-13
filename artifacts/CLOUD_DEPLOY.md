# Cloud / VPS deploy (public URL)

The Grok sandbox cannot publish a public URL to your phone. Use a VPS or a tunnel.

## Option A — VPS (DigitalOcean, Linode, AWS, Hetzner)

```bash
sudo apt update && sudo apt install -y python3
# upload or clone c12-ship bundle
cd c12-ship
export ALLOW_AGENT_EXECUTION=true
./run.sh
sudo ufw allow 8080/tcp
```

**Public URL:** `http://YOUR_VPS_IP:8080/`

## Option B — Docker on VPS

```bash
cd c12-ship
export CONTROL12_API_TOKEN=$(openssl rand -hex 32)
docker compose up -d
```

## Option C — Tunnel from laptop

```bash
./run.sh
npx localtunnel --port 8080
# or: cloudflared tunnel --url http://localhost:8080
# or: ngrok http 8080
```

## Option D — TLS with Caddy

```text
your.domain.com {
  reverse_proxy 127.0.0.1:8080
}
```

## Security

```bash
export CONTROL12_API_TOKEN=$(openssl rand -hex 32)
export ALLOW_AGENT_EXECUTION=true
```
