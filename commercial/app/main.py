from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from .store import Store, utcnow

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CONTROL12_DATA_DIR", ROOT / "data"))
STORE = Store(DATA_DIR / "control12-commercial.db")
ADMIN_KEY = os.getenv("CONTROL12_ADMIN_KEY", "").strip()
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()
VERSION = "1.0.0"

PLANS = {
    "developer": {"name": "Developer", "monthly_usd": 49, "projects": 3, "verification_runs": 100},
    "team": {"name": "Team", "monthly_usd": 249, "projects": 20, "verification_runs": 1000},
    "business": {"name": "Business", "monthly_usd": 799, "projects": 100, "verification_runs": 10000},
    "enterprise": {"name": "Enterprise", "monthly_usd": None, "projects": None, "verification_runs": None},
}

app = FastAPI(
    title="CONTROL12 Commercial API",
    version=VERSION,
    description="Release assurance, evidence, policy, deployment, usage, and billing control plane.",
)


def require_write_key(x_control12_key: str | None = Header(default=None)) -> None:
    if ADMIN_KEY and not hmac.compare_digest(x_control12_key or "", ADMIN_KEY):
        raise HTTPException(status_code=401, detail="Invalid CONTROL12 write key")


def actor(request: Request) -> str:
    return request.headers.get("X-Control12-Actor", "local-operator")[:120]


def get_or_404(table: str, object_id: str) -> dict[str, Any]:
    allowed = {"organizations", "projects", "releases"}
    if table not in allowed:
        raise ValueError("invalid table")
    item = STORE.query_one(f"SELECT * FROM {table} WHERE id=?", (object_id,))
    if not item:
        raise HTTPException(404, detail=f"{table[:-1].title()} not found")
    return item


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=64)
    plan: Literal["developer", "team", "business", "enterprise"] = "developer"

    @field_validator("slug")
    @classmethod
    def valid_slug(cls, value: str) -> str:
        value = value.lower().strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}[a-z0-9]", value):
            raise ValueError("slug must use lowercase letters, numbers, and hyphens")
        return value


class ProjectCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=120)
    repository_url: str | None = Field(default=None, max_length=500)
    default_branch: str = Field(default="main", min_length=1, max_length=120)


class ReleaseCreate(BaseModel):
    organization_id: str
    project_id: str
    version: str = Field(min_length=1, max_length=120)
    commit_sha: str | None = Field(default=None, max_length=64)
    artifact_sha256: str | None = Field(default=None, max_length=64)

    @field_validator("artifact_sha256")
    @classmethod
    def valid_sha(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("artifact_sha256 must be 64 hex characters")
        return value.lower() if value else value


class EvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=80)
    source: str = Field(min_length=2, max_length=120)
    status: Literal["pass", "fail", "pending", "informational"]
    payload: dict[str, Any] = Field(default_factory=dict)


class DeploymentCreate(BaseModel):
    environment: str = Field(min_length=2, max_length=80)
    status: Literal["queued", "running", "succeeded", "failed", "rolled_back"] = "queued"
    target: str | None = Field(default=None, max_length=500)


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    index = ROOT / "templates" / "index.html"
    if not index.exists():
        return HTMLResponse("<h1>CONTROL12 Commercial</h1>")
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "control12-commercial",
        "version": VERSION,
        "persistence": "sqlite",
        "write_auth": bool(ADMIN_KEY),
        "time": utcnow(),
    }


@app.get("/api/plans")
def plans() -> dict[str, Any]:
    return {"plans": PLANS}


@app.get("/api/organizations")
def list_organizations() -> dict[str, Any]:
    return {"items": STORE.query_all("SELECT * FROM organizations ORDER BY created_at DESC")}


@app.post("/api/organizations", dependencies=[Depends(require_write_key)])
def create_organization(body: OrganizationCreate, request: Request) -> dict[str, Any]:
    org_id = STORE.new_id("org")
    try:
        STORE.execute(
            "INSERT INTO organizations(id,name,slug,plan,created_at) VALUES (?,?,?,?,?)",
            (org_id, body.name.strip(), body.slug, body.plan, utcnow()),
        )
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(409, detail="Organization slug already exists") from exc
        raise
    STORE.audit(org_id, actor(request), "organization.created", "organization", org_id, body.model_dump())
    return get_or_404("organizations", org_id)


@app.get("/api/projects")
def list_projects(organization_id: str | None = None) -> dict[str, Any]:
    if organization_id:
        items = STORE.query_all("SELECT * FROM projects WHERE organization_id=? ORDER BY created_at DESC", (organization_id,))
    else:
        items = STORE.query_all("SELECT * FROM projects ORDER BY created_at DESC")
    return {"items": items}


@app.post("/api/projects", dependencies=[Depends(require_write_key)])
def create_project(body: ProjectCreate, request: Request) -> dict[str, Any]:
    get_or_404("organizations", body.organization_id)
    project_id = STORE.new_id("prj")
    STORE.execute(
        "INSERT INTO projects(id,organization_id,name,repository_url,default_branch,created_at) VALUES (?,?,?,?,?,?)",
        (project_id, body.organization_id, body.name.strip(), body.repository_url, body.default_branch, utcnow()),
    )
    STORE.audit(body.organization_id, actor(request), "project.created", "project", project_id, body.model_dump())
    return get_or_404("projects", project_id)


@app.get("/api/releases")
def list_releases(organization_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    sql = "SELECT * FROM releases"
    params: list[Any] = []
    where: list[str] = []
    if organization_id:
        where.append("organization_id=?")
        params.append(organization_id)
    if project_id:
        where.append("project_id=?")
        params.append(project_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC"
    return {"items": STORE.query_all(sql, params)}


@app.post("/api/releases", dependencies=[Depends(require_write_key)])
def create_release(body: ReleaseCreate, request: Request) -> dict[str, Any]:
    project = get_or_404("projects", body.project_id)
    if project["organization_id"] != body.organization_id:
        raise HTTPException(400, detail="Project does not belong to organization")
    release_id = STORE.new_id("rel")
    STORE.execute(
        "INSERT INTO releases(id,organization_id,project_id,version,commit_sha,artifact_sha256,status,policy_status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (release_id, body.organization_id, body.project_id, body.version, body.commit_sha, body.artifact_sha256, "draft", "pending", utcnow()),
    )
    STORE.audit(body.organization_id, actor(request), "release.created", "release", release_id, body.model_dump())
    STORE.usage(body.organization_id, "release.created", 1, {"release_id": release_id})
    return get_or_404("releases", release_id)


@app.post("/api/releases/{release_id}/evidence", dependencies=[Depends(require_write_key)])
def add_evidence(release_id: str, body: EvidenceCreate, request: Request) -> dict[str, Any]:
    release = get_or_404("releases", release_id)
    evidence_id = STORE.new_id("evd")
    STORE.execute(
        "INSERT INTO evidence(id,release_id,evidence_type,source,status,payload_json,created_at) VALUES (?,?,?,?,?,?,?)",
        (evidence_id, release_id, body.evidence_type, body.source, body.status, json.dumps(body.payload, sort_keys=True), utcnow()),
    )
    STORE.audit(release["organization_id"], actor(request), "evidence.added", "release", release_id, body.model_dump())
    return {"id": evidence_id, "release_id": release_id, **body.model_dump(), "created_at": utcnow()}


@app.post("/api/releases/{release_id}/verify", dependencies=[Depends(require_write_key)])
def verify_release(release_id: str, request: Request) -> dict[str, Any]:
    release = get_or_404("releases", release_id)
    evidence = STORE.query_all("SELECT * FROM evidence WHERE release_id=? ORDER BY created_at", (release_id,))
    checks: list[dict[str, Any]] = [
        {"name": "commit_reference", "status": "pass" if release.get("commit_sha") else "pending"},
        {"name": "artifact_digest", "status": "pass" if release.get("artifact_sha256") else "pending"},
    ]
    for row in evidence:
        checks.append({"name": f"{row['source']}:{row['evidence_type']}", "status": row["status"]})
    failed = any(c["status"] == "fail" for c in checks)
    pending = any(c["status"] == "pending" for c in checks)
    if failed:
        status, policy_status = "blocked", "fail"
    elif pending:
        status, policy_status = "needs_external_checks", "pending"
    else:
        status, policy_status = "verified", "pass"
    verified_at = utcnow()
    STORE.execute(
        "UPDATE releases SET status=?,policy_status=?,verified_at=? WHERE id=?",
        (status, policy_status, verified_at, release_id),
    )
    STORE.usage(release["organization_id"], "verification.run", 1, {"release_id": release_id, "status": status})
    STORE.audit(release["organization_id"], actor(request), "release.verified", "release", release_id, {"status": status, "checks": checks})
    return {"release_id": release_id, "status": status, "policy_status": policy_status, "checks": checks, "verified_at": verified_at}


@app.get("/api/releases/{release_id}/receipt")
def release_receipt(release_id: str) -> dict[str, Any]:
    release = get_or_404("releases", release_id)
    project = get_or_404("projects", release["project_id"])
    evidence = STORE.query_all("SELECT evidence_type,source,status,payload_json,created_at FROM evidence WHERE release_id=? ORDER BY created_at", (release_id,))
    normalized_evidence = []
    for item in evidence:
        item = dict(item)
        item["payload"] = json.loads(item.pop("payload_json"))
        normalized_evidence.append(item)
    payload = {
        "schema": "control12.receipt/v1",
        "release": release,
        "project": project,
        "evidence": normalized_evidence,
        "generated_at": utcnow(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


@app.post("/api/releases/{release_id}/deployments", dependencies=[Depends(require_write_key)])
def create_deployment(release_id: str, body: DeploymentCreate, request: Request) -> dict[str, Any]:
    release = get_or_404("releases", release_id)
    if release["policy_status"] != "pass" and body.environment.lower() in {"production", "prod"}:
        raise HTTPException(409, detail="Production deployment blocked until policy passes")
    deployment_id = STORE.new_id("dep")
    created_at = utcnow()
    STORE.execute(
        "INSERT INTO deployments(id,release_id,environment,status,target,created_at) VALUES (?,?,?,?,?,?)",
        (deployment_id, release_id, body.environment, body.status, body.target, created_at),
    )
    STORE.audit(release["organization_id"], actor(request), "deployment.created", "deployment", deployment_id, {"release_id": release_id, **body.model_dump()})
    STORE.usage(release["organization_id"], "deployment.created", 1, {"release_id": release_id, "environment": body.environment})
    return {"id": deployment_id, "release_id": release_id, **body.model_dump(), "created_at": created_at}


@app.get("/api/dashboard")
def dashboard(organization_id: str | None = None) -> dict[str, Any]:
    clauses = []
    params: list[Any] = []
    if organization_id:
        clauses.append("organization_id=?")
        params.append(organization_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    releases = STORE.query_one(f"SELECT COUNT(*) AS n FROM releases{where}", params)["n"]
    verified = STORE.query_one(f"SELECT COUNT(*) AS n FROM releases{where + (' AND' if where else ' WHERE')} status='verified'", params)["n"]
    blocked = STORE.query_one(f"SELECT COUNT(*) AS n FROM releases{where + (' AND' if where else ' WHERE')} status='blocked'", params)["n"]
    if organization_id:
        usage = STORE.query_all("SELECT event_type,SUM(quantity) AS quantity FROM usage_events WHERE organization_id=? GROUP BY event_type", (organization_id,))
    else:
        usage = STORE.query_all("SELECT event_type,SUM(quantity) AS quantity FROM usage_events GROUP BY event_type")
    return {"releases": releases, "verified": verified, "blocked": blocked, "usage": usage}


@app.get("/api/audit")
def audit(organization_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(limit, 500))
    if organization_id:
        rows = STORE.query_all("SELECT * FROM audit_events WHERE organization_id=? ORDER BY created_at DESC LIMIT ?", (organization_id, limit))
    else:
        rows = STORE.query_all("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,))
    for row in rows:
        row["payload"] = json.loads(row.pop("payload_json"))
    return {"items": rows}


@app.post("/api/github/webhook")
async def github_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None), x_github_event: str | None = Header(default=None)):
    raw = await request.body()
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(503, detail="GITHUB_WEBHOOK_SECRET is not configured")
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(x_hub_signature_256 or "", expected):
        raise HTTPException(401, detail="Invalid GitHub webhook signature")
    payload = json.loads(raw or b"{}")
    return JSONResponse({"accepted": True, "event": x_github_event, "repository": payload.get("repository", {}).get("full_name")})


@app.get("/api/billing/status")
def billing_status() -> dict[str, Any]:
    return {
        "provider": "stripe",
        "configured": bool(os.getenv("STRIPE_SECRET_KEY")),
        "mode": "live" if os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_live_") else "test_or_unconfigured",
        "plans": PLANS,
    }
