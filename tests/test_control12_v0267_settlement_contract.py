"""v0.26.7 operator-signed settlement transport contract tests.

These verify host caller behavior with mock HTTP, not agent execution or
the independent PostgreSQL runtime transaction guarantees.
"""
import hashlib
import hmac
import json

import httpx
import pytest

from integrations.control12_gateway import Control12Gateway, GatewayError

KEY = "test-only-settlement-hmac-key-0123456789abcdef"
TASK = "00000000-0000-4000-8000-000000000001"
TOKEN = "lease-fixture-token-longer-than-thirty-two-bytes"


def gateway(transport):
    return Control12Gateway(
        "http://127.0.0.1:9876", KEY, "testing", "worker",
        ["tasks:execute"], transport=transport,
    )


@pytest.mark.parametrize("outcome", ["complete", "fail"])
@pytest.mark.parametrize("cost", [0, 1, 2, 5, 7, 11, 24, 99, 100, 101, 102, 103])
def test_explicit_settlement_retry_signs_new_nonce_each_time(outcome, cost):
    sent = []
    def respond(req):
        sent.append(req)
        return httpx.Response(200, json={"status": "succeeded" if outcome == "complete" else "failed", "actual": cost})
    client = gateway(httpx.MockTransport(respond))
    path = "/v1/tasks/" + TASK + "/" + outcome
    body = {"lease_token": TOKEN, "actual": cost}
    if outcome == "fail":
        body["error_code"] = "fixture-error"
    else:
        body["result"] = {"source": "fixture"}
    try:
        first = client.call(outcome, path, body)
        second = client.call(outcome, path, body)
        assert first == second
        assert len(sent) == 2
        assert sent[0].headers["x-avrone-nonce"] != sent[1].headers["x-avrone-nonce"]
        for req in sent:
            assert json.loads(req.content) == body
            h = req.headers
            canonical = "\n".join((
                req.method, req.url.path, "", h["x-avrone-tenant"],
                h["x-avrone-principal"], h["x-avrone-permissions"],
                h["x-avrone-timestamp"], h["x-avrone-nonce"],
                hashlib.sha256(req.content).hexdigest()
            ))
            assert h["x-avrone-signature"] == hmac.new(
                KEY.encode(), canonical.encode(), hashlib.sha256
            ).hexdigest()
            assert "idempotency-key" not in h
    finally:
        client.close()


@pytest.mark.parametrize("outcome", ["complete", "fail"])
def test_write_uncertainty_does_not_trigger_automatic_retry(outcome):
    attempts = []
    def disconnect(req):
        attempts.append(req)
        raise httpx.ReadTimeout("simulated response loss after settlement")
    client = gateway(httpx.MockTransport(disconnect))
    try:
        with pytest.raises(GatewayError) as error:
            client.call(outcome, "/v1/tasks/" + TASK + "/" + outcome, {
                "lease_token": TOKEN, "actual": 5,
                **({"result": {}} if outcome == "complete" else {"error_code": "E"})
            })
        assert error.value.ambiguous is True
        assert len(attempts) == 1
    finally:
        client.close()


@pytest.mark.parametrize("outcome", ["complete", "fail"])
def test_server_settlement_conflict_is_explicit_not_ambiguous(outcome):
    client = gateway(httpx.MockTransport(lambda _: httpx.Response(409, json={"detail": "settlement conflict"})))
    try:
        with pytest.raises(GatewayError) as error:
            client.call(outcome, "/v1/tasks/" + TASK + "/" + outcome, {
                "lease_token": TOKEN, "actual": 5,
                **({"result": {}} if outcome == "complete" else {"error_code": "E"})
            })
        assert error.value.status == 409
        assert error.value.ambiguous is False
    finally:
        client.close()


@pytest.mark.parametrize("operation", ["complete", "fail"])
def test_creation_idempotency_key_refused_for_lease_settlement(operation):
    client = gateway(httpx.MockTransport(lambda _: httpx.Response(200, json={})))
    try:
        with pytest.raises(ValueError):
            client.call(operation, "/v1/tasks/" + TASK + "/" + operation,
                        {"lease_token": TOKEN, "actual": 0},
                        idempotency_key="wrong-scope-idempotency-00001")
    finally:
        client.close()
