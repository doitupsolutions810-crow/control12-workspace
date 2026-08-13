# SECURITY

- Production: set CONTROL12_API_TOKEN; Bearer or X-API-Key
- ALLOW_AGENT_EXECUTION required for agent actions
- Host-ONLY enforced; production apply defaults false
- X-Tenant-Id for storage isolation
- TLS at reverse proxy in production
