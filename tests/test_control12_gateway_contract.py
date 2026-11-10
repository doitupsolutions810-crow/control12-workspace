"""Fail-closed edge tests for the CONTROL12 host-only gateway adapter.

These do not claim to launch agents or contact production endpoints.
"""
import hashlib
import hmac
import json

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

KEY = "disposable-test-key-longer-than-32-characters-only"


@pytest.mark.parametrize("origin", [
    "http://example.com", "http://10.0.0.1", "http://user@evil.example",
    "file:///tmp/foo", "https://user:pass@example.com",
    "https://example.com/path", "https://example.com/?token=x",
    "http://localhost:0", "http://127.0.0.1:99999",
])
def test_refuses_unsafe_origins(origin):
    with pytest.raises(ValueError):
        Control12Gateway(origin, KEY, "tenant-a", "host", ["mission:write"])


def test_hmac_exact_body_and_nonce():
    requests = []
    def handle(req):
        requests.append(req)
        return httpx.Response(201, json={"id": "receipt"})
    adapter = Control12Gateway("http://127.0.0.1:8080", KEY, "tenant-a", "host",
                               ["mission:write"], transport=httpx.MockTransport(handle))
    try:
        payload = {"name": "A", "objective": "test only", "mode": "cooperative", "budget": 5}
        assert adapter.call("create_mission", "/v1/missions", payload) == {"id": "receipt"}
        assert adapter.call("create_mission", "/v1/missions", payload) == {"id": "receipt"}
        assert len(requests) == 2
        assert requests[0].headers["x-avrone-nonce"] != requests[1].headers["x-avrone-nonce"]
        for req in requests:
            h = req.headers
            body_hash = hashlib.sha256(req.content).hexdigest()
            fields = [req.method, req.url.path, "", h["x-avrone-tenant"],
                      h["x-avrone-principal"], h["x-avrone-permissions"],
                      h["x-avrone-timestamp"], h["x-avrone-nonce"], body_hash]
            signature = hmac.new(KEY.encode(), "\n".join(fields).encode(), hashlib.sha256).hexdigest()
            assert h["x-avrone-signature"] == signature
            assert json.loads(req.content) == payload
    finally:
        adapter.close()


@pytest.mark.parametrize("operation,path", [
    ("proxy", "/v1/missions"), ("create_mission", "/v1/tasks"),
    ("create_task", "/v1/tasks"), ("create_mission", "/v1/missions?x=y"),
    ("create_task", "/v1/missions/../../secrets/tasks"),
    ("telemetry", "https://attacker.example"),
])
def test_refuses_unknown_routes(operation, path):
    client = Control12Gateway("https://runtime.example", KEY, "tenant-a", "host", ["mission:write", "telemetry:read"])
    try:
        with pytest.raises(ValueError):
            client.call(operation, path, {})
    finally:
        client.close()


def test_denies_missing_scope_before_network():
    adapter = Control12Gateway("https://runtime.example", KEY, "tenant-a", "host", ["telemetry:read"])
    try:
        with pytest.raises(PermissionError):
            adapter.call("create_mission", "/v1/missions", {"name": "no"})
    finally:
        adapter.close()


@pytest.mark.parametrize("response_code,data,ambiguous", [
    (200, b'{"x":1,"x":2}', True),
    (200, b'not-json', True),
    (307, b'{"ok":true}', True),
    (409, b'{"detail":"conflict"}', False),
])
def test_ambiguous_mutation_responses(response_code, data, ambiguous):
    adapter = Control12Gateway(
        "https://runtime.example", KEY, "tenant-a", "host", ["mission:write"],
        transport=httpx.MockTransport(lambda req: httpx.Response(response_code, content=data)),
    )
    try:
        with pytest.raises(GatewayError) as err:
            adapter.call("create_mission", "/v1/missions", {"name": "trial"})
        assert err.value.ambiguous is ambiguous
    finally:
        adapter.close()


def test_never_follows_redirect_and_never_reads_unbounded_response():
    def oversized(req):
        return httpx.Response(200, content=b'{' + b'x' * 70000 + b'}')
    adapter = Control12Gateway("https://runtime.example", KEY, "tenant-a", "host",
                               ["mission:write"], transport=httpx.MockTransport(oversized))
    try:
        with pytest.raises(GatewayError) as err:
            adapter.call("create_mission", "/v1/missions", {"name": "trial"})
        assert err.value.ambiguous is True
    finally:
        adapter.close()


def test_rejects_unserializable_payload_without_network():
    adapter = Control12Gateway("https://runtime.example", KEY, "tenant-a", "host", ["mission:write"])
    try:
        with pytest.raises(ValueError):
            adapter.call("create_mission", "/v1/missions", {"budget": float("nan")})
    finally:
        adapter.close()
