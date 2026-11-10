"""Additional v0.26.5 host-side security-contract regressions.

Tests are offline with MockTransport; no production signer or agent invoked.
"""
import hashlib
import hmac
import secrets

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

KEY = "test-only-not-a-real-signing-key-0123456789"
TASK = "00000000-0000-4000-8000-000000000001"
MISSION = "00000000-0000-4000-8000-000000000002"

VALID_OPS = [
    ("register_agent", "/v1/agents"),
    ("set_agent_state", f"/v1/agents/{TASK}"),
    ("create_mission", "/v1/missions"),
    ("list_missions", "/v1/missions"),
    ("create_task", f"/v1/missions/{MISSION}/tasks"),
    ("get_task", f"/v1/tasks/{TASK}"),
    ("claim_next", "/v1/tasks/claim-next"),
    ("submit_bid", f"/v1/tasks/{TASK}/bids"),
    ("award", f"/v1/tasks/{TASK}/award"),
    ("renew", f"/v1/tasks/{TASK}/renew"),
    ("complete", f"/v1/tasks/{TASK}/complete"),
    ("fail", f"/v1/tasks/{TASK}/fail"),
    ("telemetry", "/v1/telemetry"),
    ("agent_telemetry", "/v1/telemetry/agents"),
    ("audit", "/v1/audit"),
]


@pytest.mark.parametrize("operation,path", VALID_OPS)
def test_admin_wildcard_matches_server_superuser_contract(operation, path):
    seen = []
    def reply(req):
        seen.append(req)
        return httpx.Response(200, json={"ok": True})
    client = Control12Gateway("http://127.0.0.1:8822", KEY, "tenant", "administrator",
                              ["admin:*"], transport=httpx.MockTransport(reply))
    try:
        # Empty data is a valid signed JSON body for the adapter contract;
        # the mock verifies authorization, not Pydantic endpoint payloads.
        body = None if operation in {"list_missions","get_task","telemetry","agent_telemetry","audit"} else {}
        assert client.call(operation, path, body) == {"ok": True}
        assert len(seen) == 1
        req = seen[0]
        assert req.headers["x-avrone-permissions"] == "admin:*"
        canonical = "\n".join((
            req.method, req.url.path, "", "tenant", "administrator",
            "admin:*", req.headers["x-avrone-timestamp"],
            req.headers["x-avrone-nonce"], hashlib.sha256(req.content).hexdigest(),
        ))
        assert req.headers["x-avrone-signature"] == hmac.new(
            KEY.encode(), canonical.encode(), hashlib.sha256,
        ).hexdigest()
    finally:
        client.close()


@pytest.mark.parametrize("value", [
    "", "admin:* ", "admin:*\n", "mission:write,admin:*", "x"*81, 0, None,
])
def test_admin_wildcard_does_not_allow_malformed_scopes(value):
    with pytest.raises(ValueError):
        Control12Gateway("http://127.0.0.1:8822", KEY, "tenant",
                         "administrator", [value])


@pytest.mark.parametrize("operation,path", [
    ("create_mission", "/v1/missions"),
    ("register_agent", "/v1/agents"),
    ("complete", f"/v1/tasks/{TASK}/complete"),
])
def test_denied_permission_never_dispatches_a_network_request(operation, path):
    dispatched = []
    client = Control12Gateway(
        "http://127.0.0.1:8822", KEY, "tenant", "worker", ["telemetry:read"],
        transport=httpx.MockTransport(lambda req: dispatched.append(req) or httpx.Response(200, json={})),
    )
    try:
        with pytest.raises(PermissionError):
            client.call(operation, path, {})
        assert dispatched == []
    finally:
        client.close()
