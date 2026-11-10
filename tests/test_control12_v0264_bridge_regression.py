"""Additional adversarial regressions for the host-only CONTROL12 adapter.

The full runtime's UTF-8 and streaming fixes are tracked separately in the
v0.26.4 runtime patch; these tests cover the independently packaged adapter.
"""
import hashlib
import hmac
import json

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

KEY = "disposable-v0264-hmac-key-at-least-32-bytes"


def make(transport, *, scopes=("mission:write", "telemetry:read")):
    return Control12Gateway(
        "http://127.0.0.1:8765", KEY, "fixture-tenant", "fixture-principal",
        list(scopes), transport=transport,
    )


def test_unicode_payload_hmac_binds_actual_utf8_bytes():
    messages = []
    def serve(req):
        messages.append(req)
        return httpx.Response(201, json={"id": "fixed"})
    client = make(httpx.MockTransport(serve))
    try:
        result = client.call("create_mission", "/v1/missions", {
            "name": "雪の mission 🌙", "mode": "cooperative", "budget": 9
        })
        assert result["id"] == "fixed"
        req = messages[0]
        assert json.loads(req.content)["name"] == "雪の mission 🌙"
        header = req.headers
        canonical = "\n".join((
            req.method, req.url.path, "", header["x-avrone-tenant"],
            header["x-avrone-principal"], header["x-avrone-permissions"],
            header["x-avrone-timestamp"], header["x-avrone-nonce"],
            hashlib.sha256(req.content).hexdigest(),
        ))
        assert header["x-avrone-signature"] == hmac.new(
            KEY.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()
    finally:
        client.close()


@pytest.mark.parametrize("reply", [
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
    b'{"x":"\\ud800"}', b'{"x":1,"x":2}',
    b'{"x":' + b'[' * 70 + b'0' + b']' * 70 + b'}',
])
def test_bad_remote_json_never_acknowledges_a_write(reply):
    client = make(httpx.MockTransport(lambda _: httpx.Response(200, content=reply)))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("create_mission", "/v1/missions", {"name": "trial"})
        assert caught.value.ambiguous
    finally:
        client.close()


def test_write_transport_uncertainty_does_not_retry_or_leak_secret():
    attempts = []
    def fail(req):
        attempts.append(req)
        raise httpx.ReadTimeout("injected timeout")
    client = make(httpx.MockTransport(fail))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("create_mission", "/v1/missions", {"name": "trial"})
        assert caught.value.ambiguous
        assert len(attempts) == 1
        assert KEY not in str(caught.value)
    finally:
        client.close()


def test_read_transport_failure_is_not_ambiguous_write():
    client = make(httpx.MockTransport(lambda _: (_ for _ in ()).throw(
        httpx.ConnectError("connection unavailable")
    )))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("telemetry", "/v1/telemetry")
        assert not caught.value.ambiguous
    finally:
        client.close()


@pytest.mark.parametrize("status", [400, 401, 403, 409, 422, 500, 503])
def test_explicit_http_failure_is_not_transport_uncertainty(status):
    client = make(httpx.MockTransport(lambda _: httpx.Response(
        status, json={"detail": "rejected"}
    )))
    try:
        with pytest.raises(GatewayError) as caught:
            client.call("create_mission", "/v1/missions", {"name": "trial"})
        assert caught.value.status == status
        assert not caught.value.ambiguous
    finally:
        client.close()
