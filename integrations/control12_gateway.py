"""Trusted service-to-CONTROL12 v0.26.6 HMAC gateway adapter.

Host-only integration. Do not expose signer keys or this class to agents.
Writes are never automatically retried; keyed mission/task creation may be replayed explicitly on v0.26.6+.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import math
import re
import secrets
import time
from urllib.parse import urlsplit

import httpx

_OPERATIONS = {
    "register_agent": ("POST", r"/v1/agents", "agents:write"),
    "set_agent_state": ("PATCH", r"/v1/agents/[0-9a-fA-F-]{36}", "agents:write"),
    "create_mission": ("POST", r"/v1/missions", "mission:write"),
    "list_missions": ("GET", r"/v1/missions", "mission:read"),
    "create_task": ("POST", r"/v1/missions/[0-9a-fA-F-]{36}/tasks", "mission:write"),
    "get_task": ("GET", r"/v1/tasks/[0-9a-fA-F-]{36}", "mission:read"),
    "get_receipts": ("GET", r"/v1/receipts/[A-Za-z0-9._-]{16,128}", "mission:read"),
    "reconcile_mission": ("GET", r"/v1/missions/[0-9a-fA-F-]{36}/reconcile", "mission:read"),
    "claim_next": ("POST", r"/v1/tasks/claim-next", "tasks:execute"),
    "submit_bid": ("POST", r"/v1/tasks/[0-9a-fA-F-]{36}/bids", "tasks:execute"),
    "award": ("POST", r"/v1/tasks/[0-9a-fA-F-]{36}/award", "mission:write"),
    "renew": ("POST", r"/v1/tasks/[0-9a-fA-F-]{36}/renew", "tasks:execute"),
    "complete": ("POST", r"/v1/tasks/[0-9a-fA-F-]{36}/complete", "tasks:execute"),
    "fail": ("POST", r"/v1/tasks/[0-9a-fA-F-]{36}/fail", "tasks:execute"),
    "telemetry": ("GET", r"/v1/telemetry", "telemetry:read"),
    "agent_telemetry": ("GET", r"/v1/telemetry/agents", "telemetry:read"),
    "audit": ("GET", r"/v1/audit", "audit:read"),
}


class GatewayError(RuntimeError):
    def __init__(self, message, *, status=None, ambiguous=False):
        super().__init__(message)
        self.status = status
        self.ambiguous = ambiguous


def _origin(value):
    if not isinstance(value, str) or any(ord(c) < 33 or ord(c) == 127 for c in value):
        raise ValueError("invalid configured origin")
    p = urlsplit(value)
    if (p.scheme not in ("https", "http") or not p.hostname or p.username or p.password
            or p.path not in ("", "/") or p.query or p.fragment):
        raise ValueError("origin must not contain credentials, paths or query")
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("invalid port") from exc
    if port == 0:
        raise ValueError("invalid port")
    if p.scheme == "http":
        try:
            local = ipaddress.ip_address(p.hostname).is_loopback
        except ValueError:
            local = p.hostname.lower() == "localhost"
        if not local:
            raise ValueError("HTTP requires loopback")
    return value.rstrip("/")


def _json(data):
    if len(data) > 65536:
        raise GatewayError("response too large")
    try:
        def object_pairs(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise ValueError("duplicate key")
                result[k] = v
            return result
        def constant(_):
            raise ValueError("nonfinite")
        obj = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=object_pairs, parse_constant=constant)
        todo = [(obj, 0)]
        while todo:
            value, depth = todo.pop()
            if depth > 64:
                raise ValueError("deep JSON")
            if isinstance(value, dict):
                todo.extend((k, depth + 1) for k in value)
                todo.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                todo.extend((v, depth + 1) for v in value)
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError("nonfinite float")
            elif isinstance(value, str):
                value.encode("utf-8", "strict")
        return obj
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise GatewayError("invalid JSON response") from exc


class Control12Gateway:
    """Use only behind a trusted authenticated gateway / service boundary."""

    def __init__(self, origin, secret, tenant, principal, scopes, *, transport=None):
        self.origin = _origin(origin)
        if not isinstance(secret, str) or len(secret.encode()) < 32:
            raise ValueError("weak signing key")
        for name, val, cap in (("tenant", tenant, 100), ("principal", principal, 120)):
            if not isinstance(val, str) or not 1 <= len(val) <= cap or any(ord(c) < 33 or ord(c) == 127 for c in val):
                raise ValueError("invalid " + name)
        if not scopes or any(not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9:*_-]{1,80}", s) for s in scopes):
            raise ValueError("invalid scopes")
        self.secret, self.tenant, self.principal, self.scopes = secret, tenant, principal, frozenset(scopes)
        self.http = httpx.Client(transport=transport, timeout=8.0, trust_env=False, follow_redirects=False)

    def close(self):
        self.http.close()

    def call(self, operation, path, payload=None, *, idempotency_key=None):
        if operation not in _OPERATIONS:
            raise ValueError("operation not permitted")
        method, allowed_path, required_scope = _OPERATIONS[operation]
        if not re.fullmatch(allowed_path, path):
            raise ValueError("path not permitted")
        if required_scope not in self.scopes and "admin:*" not in self.scopes:
            raise PermissionError("missing " + required_scope)
        if (operation == "reconcile_mission" and "audit:read" not in self.scopes
                and "admin:*" not in self.scopes):
            raise PermissionError("missing audit:read")
        if method == "GET" and payload is not None:
            raise ValueError("GET body is not permitted")
        if idempotency_key is not None:
            if (operation not in {"create_mission", "create_task"} or
                    not isinstance(idempotency_key, str) or
                    re.fullmatch(r"[A-Za-z0-9._-]{16,128}", idempotency_key) is None):
                raise ValueError("invalid idempotency key or unsupported operation")
        try:
            body = (b"" if payload is None else
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8", "strict"))
        except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
            raise ValueError("invalid JSON request") from exc
        if len(body) > 262144:
            raise ValueError("request exceeds maximum")
        nonce, timestamp = secrets.token_urlsafe(24), str(int(time.time()))
        perms = ",".join(sorted(self.scopes))
        msg = "\n".join((method, path, "", self.tenant, self.principal, perms,
                         timestamp, nonce, hashlib.sha256(body).hexdigest()))
        if idempotency_key is not None:
            msg += "\nidempotency-key:" + idempotency_key
        sig = hmac.new(self.secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        headers = {
            "x-avrone-tenant": self.tenant, "x-avrone-principal": self.principal,
            "x-avrone-permissions": perms, "x-avrone-timestamp": timestamp,
            "x-avrone-nonce": nonce, "x-avrone-signature": sig,
            "accept": "application/json", "accept-encoding": "identity",
        }
        if body:
            headers["content-type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        try:
            with self.http.stream(method, self.origin + path, content=body, headers=headers) as resp:
                if resp.is_redirect or resp.headers.get("content-encoding", "identity").lower() != "identity":
                    raise GatewayError("redirect or compressed response refused",
                                       status=resp.status_code, ambiguous=method != "GET")
                raw = bytearray()
                for chunk in resp.iter_bytes():
                    if len(raw) + len(chunk) > 65536:
                        raise GatewayError("response too large", status=resp.status_code,
                                           ambiguous=method != "GET")
                    raw.extend(chunk)
                try:
                    value = _json(bytes(raw))
                except GatewayError as exc:
                    exc.ambiguous = method != "GET"
                    raise
                if resp.status_code >= 400:
                    raise GatewayError("remote rejected operation", status=resp.status_code)
                return value
        except (httpx.HTTPError, TimeoutError) as exc:
            raise GatewayError("transport uncertainty; do not blindly retry mutations",
                               ambiguous=method != "GET") from exc
