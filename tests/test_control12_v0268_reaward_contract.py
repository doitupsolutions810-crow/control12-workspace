"""v0.26.8 host-side re-award signature/transport tests.

Mocks verify the trusted adapter, NOT server-side budget accounting.
The actual runtime budget tests are distributed in the standalone release.
"""
import hashlib
import hmac

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

SECRET = "offline-only-reaward-hmac-credential-0123456789"
TASK = "00000000-0000-4000-8000-000000000001"


def host(transport, scopes=("mission:read", "mission:write")):
    return Control12Gateway("http://127.0.0.1:8082", SECRET,
                            "tenant-a", "admin", list(scopes), transport=transport)


@pytest.mark.parametrize("previous", [1,2,3,5,7,9,13,17])
@pytest.mark.parametrize("replacement", [19,20,25,30,35,39])
def test_allowed_award_readback_retains_original_approved_ceiling(previous,replacement):
    received = []
    def respond(request):
        received.append(request)
        return httpx.Response(200, json={
            "status": "assigned", "cap": replacement, "original_cap": 40,
            "assigned_agent_id": "agent-2",
        })
    client = host(httpx.MockTransport(respond))
    try:
        result = client.call("award", f"/v1/tasks/{TASK}/award")
        assert result["original_cap"] == 40
        assert previous < result["cap"] <= result["original_cap"]
        assert len(received) == 1
        req = received[0]
        assert req.method == "POST" and req.url.path.endswith("/award")
        hdr=req.headers
        canonical="\n".join((req.method, req.url.path, "",
                             hdr["x-avrone-tenant"], hdr["x-avrone-principal"],
                             hdr["x-avrone-permissions"], hdr["x-avrone-timestamp"],
                             hdr["x-avrone-nonce"], hashlib.sha256(req.content).hexdigest()))
        assert hdr["x-avrone-signature"] == hmac.new(
            SECRET.encode(),canonical.encode(),hashlib.sha256).hexdigest()
    finally:
        client.close()


@pytest.mark.parametrize("status", [401,403,404,409,422,503])
def test_host_does_not_retry_or_misreport_explicit_auction_failure(status):
    calls=[]
    def reject(req):
        calls.append(req)
        return httpx.Response(status, json={"detail":"auction rejected"})
    client=host(httpx.MockTransport(reject))
    try:
        with pytest.raises(GatewayError) as exc:
            client.call("award",f"/v1/tasks/{TASK}/award")
        assert exc.value.status == status and not exc.value.ambiguous
        assert len(calls)==1
    finally:
        client.close()


@pytest.mark.parametrize("operation,path", [
    ("award",f"/v1/tasks/{TASK}/award"),
    ("get_task",f"/v1/tasks/{TASK}"),
])
def test_host_fails_closed_before_network_when_scope_missing(operation,path):
    seen=[]
    client=host(httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(200,json={})),
                scopes=("telemetry:read",))
    try:
        with pytest.raises(PermissionError):
            client.call(operation,path)
        assert not seen
    finally:
        client.close()


def test_no_creation_key_is_misapplied_to_reaward():
    seen=[]
    client=host(httpx.MockTransport(lambda req: seen.append(req) or httpx.Response(200,json={})))
    try:
        with pytest.raises(ValueError):
            client.call("award",f"/v1/tasks/{TASK}/award",
                        idempotency_key="do-not-apply-create-key-0001")
        assert not seen
    finally:
        client.close()


def test_reaward_lost_ack_is_never_retried_automatically():
    calls=[]
    def lost(req):
        calls.append(req)
        raise httpx.ReadTimeout("simulated response lost after commit")
    client=host(httpx.MockTransport(lost))
    try:
        with pytest.raises(GatewayError) as exc:
            client.call("award",f"/v1/tasks/{TASK}/award")
        assert exc.value.ambiguous and len(calls)==1
    finally:
        client.close()
