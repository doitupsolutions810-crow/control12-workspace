"""Offline HMAC contract for protected v0.26.9 mission ledger reconciliation.

This is a host adapter/MockTransport test only; real ledger queries are tested
against the standalone FastAPI + SQLite runtime and are not run by this CI.
"""
import hashlib
import hmac

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

SECRET = "offline-v0269-gateway-key-0123456789abcdef"
MISSION = "00000000-0000-4000-8000-000000000001"
ROUTE = f"/v1/missions/{MISSION}/reconcile"


def make(scopes, transport):
    return Control12Gateway(
        "http://127.0.0.1:8869", SECRET, "fixture-tenant", "fixture-operator",
        scopes, transport=transport,
    )


@pytest.mark.parametrize("scopes", [
    ["mission:read", "audit:read"],
    ["mission:read", "audit:read", "telemetry:read"],
    ["admin:*"],
    ["mission:read", "audit:read", "mission:write"],
])
def test_authorized_reconciliation_is_signed_and_returns_data(scopes):
    sent = []
    payload = {
        "mission_id": MISSION, "tenant": "fixture-tenant", "ledger_ok": True,
        "recorded_reserved": 23, "expected_reserved": 23,
        "recorded_spent": 4, "expected_spent": 4,
    }
    client = make(scopes, httpx.MockTransport(
        lambda req: sent.append(req) or httpx.Response(200, json=payload)))
    try:
        assert client.call("reconcile_mission", ROUTE) == payload
        assert len(sent) == 1
        req = sent[0]
        h = req.headers
        assert req.method == "GET" and not req.content
        assert "idempotency-key" not in h
        canonical = "\n".join((
            req.method, req.url.path, "", h["x-avrone-tenant"],
            h["x-avrone-principal"], h["x-avrone-permissions"],
            h["x-avrone-timestamp"], h["x-avrone-nonce"],
            hashlib.sha256(req.content).hexdigest(),
        ))
        assert h["x-avrone-signature"] == hmac.new(
            SECRET.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()
    finally:
        client.close()


@pytest.mark.parametrize("scopes", [
    ["mission:read"], ["audit:read"], ["telemetry:read"],
    ["mission:write", "audit:read"], ["agents:write"],
    ["mission:read", "mission:write"],
])
def test_missing_either_scope_refuses_before_network(scopes):
    sent = []
    client = make(scopes, httpx.MockTransport(
        lambda req: sent.append(req) or httpx.Response(200, json={})))
    try:
        with pytest.raises(PermissionError):
            client.call("reconcile_mission", ROUTE)
        assert not sent
    finally:
        client.close()


@pytest.mark.parametrize("bad_path", [
    "/v1/missions/reconcile",
    "/v1/missions/../../secrets/reconcile",
    "/v1/missions/00000000-0000-4000-8000-000000000001/reconcile?tenant=b",
    "/v1/missions/%2e%2e/reconcile",
    "https://attacker.invalid/v1/missions/00000000-0000-4000-8000-000000000001/reconcile",
    "/v1/missions/00000000-0000-4000-8000-000000000001/other",
])
def test_reconciliation_path_must_be_allowlisted(bad_path):
    client = make(["admin:*"], httpx.MockTransport(lambda req: httpx.Response(200, json={})))
    try:
        with pytest.raises(ValueError):
            client.call("reconcile_mission", bad_path)
    finally:
        client.close()


@pytest.mark.parametrize("status", [400,401,403,404,409,422,500,503])
def test_server_rejections_are_explicit_no_automatic_replay(status):
    sent=[]
    client=make(["admin:*"],httpx.MockTransport(
        lambda req: sent.append(req) or httpx.Response(status,json={"detail":"failure"})))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("reconcile_mission",ROUTE)
        assert caught.value.status==status
        assert not caught.value.ambiguous
        assert len(sent)==1
    finally:
        client.close()


def test_transport_failure_does_not_turn_read_into_mutation():
    sent=[]
    def broken(req):
        sent.append(req)
        raise httpx.ReadTimeout("injected read timeout")
    client=make(["admin:*"],httpx.MockTransport(broken))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("reconcile_mission",ROUTE)
        assert not caught.value.ambiguous
        assert len(sent)==1
    finally:
        client.close()
