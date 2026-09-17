import os
os.environ.pop("CONTROL12_ADMIN_KEY", None)
os.environ["CONTROL12_DATA_DIR"] = "/tmp/control12-commercial-tests"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_commercial_flow():
    assert client.get("/api/health").status_code == 200
    org = client.post("/api/organizations", json={"name":"Test Org","slug":"test-org","plan":"developer"})
    if org.status_code == 409:
        org = client.get("/api/organizations").json()["items"][0]
    else:
        assert org.status_code == 200
        org = org.json()

    project = client.post("/api/projects", json={"organization_id":org["id"],"name":"API","repository_url":"https://github.com/example/api"})
    if project.status_code == 409:
        projects = client.get("/api/projects", params={"organization_id":org["id"]}).json()["items"]
        project = projects[0]
    else:
        assert project.status_code == 200
        project = project.json()

    release = client.post("/api/releases", json={"organization_id":org["id"],"project_id":project["id"],"version":"1.0.0-test","commit_sha":"abc123","artifact_sha256":"a"*64})
    if release.status_code == 409:
        release = client.get("/api/releases", params={"project_id":project["id"]}).json()["items"][0]
    else:
        assert release.status_code == 200
        release = release.json()

    ev = client.post(f"/api/releases/{release['id']}/evidence", json={"evidence_type":"unit_tests","source":"pytest","status":"pass","payload":{"passed":12}})
    assert ev.status_code == 200
    verified = client.post(f"/api/releases/{release['id']}/verify")
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"
    receipt = client.get(f"/api/releases/{release['id']}/receipt")
    assert receipt.status_code == 200
    assert len(receipt.json()["receipt_sha256"]) == 64
