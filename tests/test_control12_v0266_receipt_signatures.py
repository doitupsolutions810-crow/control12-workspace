"""CONTROL12 v0.26.6 signed idempotency key protocol: host-only boundary tests.

These are mock transport tests, not production gateway or PostgreSQL tests.
"""
import hashlib
import hmac
import httpx
import pytest

from integrations.control12_gateway import Control12Gateway

SECRET = "test-only-durable-key-0123456789-0123456789"
MISSION = "00000000-0000-4000-8000-000000000001"
KEY = "durable-worker-key-0000001"


def make(transport, permissions=("mission:write", "mission:read")):
    return Control12Gateway(
        "http://127.0.0.1:8888", SECRET, "tenant-a", "owner",
        list(permissions), transport=transport,
    )


@pytest.mark.parametrize("op,path", [
    ("create_mission", "/v1/missions"),
    ("create_task", f"/v1/missions/{MISSION}/tasks"),
])
def test_key_is_covered_by_hmac_not_only_sent_as_header(op, path):
    seen = []
    client = make(httpx.MockTransport(lambda req:
                       seen.append(req) or httpx.Response(201, json={"ok": True})))
    try:
        assert client.call(op, path, {"name": "trial"}, idempotency_key=KEY) == {"ok": True}
        assert client.call(op, path, {"name": "trial"}, idempotency_key=KEY) == {"ok": True}
        assert len(seen) == 2
        assert seen[0].headers["x-avrone-nonce"] != seen[1].headers["x-avrone-nonce"]
        for req in seen:
            h = req.headers
            canonical = "\n".join((req.method, req.url.path, "",
                                   h["x-avrone-tenant"], h["x-avrone-principal"],
                                   h["x-avrone-permissions"], h["x-avrone-timestamp"],
                                   h["x-avrone-nonce"], hashlib.sha256(req.content).hexdigest()))
            canonical += "\nidempotency-key:" + KEY
            assert h["idempotency-key"] == KEY
            assert h["x-avrone-signature"] == hmac.new(
                SECRET.encode(), canonical.encode(), hashlib.sha256
            ).hexdigest()
    finally:
        client.close()


@pytest.mark.parametrize("invalid", [
    "", "short", "a"*15, "b"*129, "with spaces here", "abc/def-0123456789",
    "abc+def-0123456789", "abc=def-0123456789", "abc:def-0123456789",
    "abc#def-0123456789", "abc,def-0123456789", "abc;def-0123456789",
    "abc?def-0123456789", "abc|def-0123456789", "abc@def-0123456789",
    "abc\\def-0123456789", "abc{def}-0123456789", "abc[def]-0123456789",
    "bidi-\u202e-0123456789", None, 999, True, [],
])
def test_bad_idempotency_key_fails_locally_without_dispatch(invalid):
    sent = []
    client = make(httpx.MockTransport(
        lambda req: sent.append(req) or httpx.Response(201, json={"ok": True})))
    try:
        # None is intentionally "no idempotency" and retains old-wire compatibility.
        if invalid is None:
            client.call("create_mission", "/v1/missions", {"name": "legacy"}, idempotency_key=None)
            assert len(sent) == 1 and "idempotency-key" not in sent[0].headers
        else:
            with pytest.raises(ValueError):
                client.call("create_mission", "/v1/missions", {"name": "trial"}, idempotency_key=invalid)
            assert sent == []
    finally:
        client.close()


@pytest.mark.parametrize("operation,path", [
    ("claim_next", "/v1/tasks/claim-next"),
    ("list_missions", "/v1/missions"),
    ("telemetry", "/v1/telemetry"),
    ("register_agent", "/v1/agents"),
    ("complete", f"/v1/tasks/{MISSION}/complete"),
])
def test_key_not_accepted_for_unrelated_operations(operation, path):
    client = make(httpx.MockTransport(lambda req: httpx.Response(200, json={})),
                  permissions=("admin:*",))
    try:
        with pytest.raises(ValueError):
            client.call(operation, path, None, idempotency_key=KEY)
    finally:
        client.close()


def test_get_receipts_is_an_allowlisted_signed_read():
    seen = []
    client = make(httpx.MockTransport(lambda req:
        seen.append(req) or httpx.Response(200, json=[{"path": "/v1/missions", "response": {"id": "abc"}}])))
    try:
        got = client.call("get_receipts", "/v1/receipts/" + KEY)
        assert got[0]["response"]["id"] == "abc"
        assert len(seen) == 1 and seen[0].method == "GET"
        assert "idempotency-key" not in seen[0].headers
    finally:
        client.close()


def test_no_automatic_repeat_on_ambiguous_network_failure():
    attempts = []
    def fail(req):
        attempts.append(req)
        raise httpx.ReadTimeout("lost after durable commit")
    client = make(httpx.MockTransport(fail))
    try:
        with pytest.raises(Exception) as result:
            client.call("create_mission", "/v1/missions", {"name": "trial"}, idempotency_key=KEY)
        assert result.value.ambiguous is True
        assert len(attempts) == 1
    finally:
        client.close()


def test_different_key_changes_signature_without_changing_body():
    seen = []
    client = make(httpx.MockTransport(lambda req:
        seen.append(req) or httpx.Response(201, json={})))
    try:
        client.call("create_mission", "/v1/missions", {"name": "trial"}, idempotency_key=KEY)
        client.call("create_mission", "/v1/missions", {"name": "trial"},
                    idempotency_key="different-key-0123456789")
        assert seen[0].content == seen[1].content
        assert seen[0].headers["x-avrone-signature"] != seen[1].headers["x-avrone-signature"]
    finally:
        client.close()
