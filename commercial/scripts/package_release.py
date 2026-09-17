from __future__ import annotations
import hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)
VERSION = "1.0.0"
ZIP = DIST / f"control12-commercial-v{VERSION}.zip"
EXCLUDE = {"dist", ".pytest_cache", "__pycache__", "data", ".git"}
files = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file() or any(part in EXCLUDE for part in p.relative_to(ROOT).parts):
        continue
    rel = p.relative_to(ROOT).as_posix()
    raw = p.read_bytes()
    files.append({"path": rel, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for item in files:
        z.write(ROOT / item["path"], item["path"])
zip_sha = hashlib.sha256(ZIP.read_bytes()).hexdigest()
manifest = {"schema":"control12.commercial-package/v1","version":VERSION,"created_at":datetime.now(timezone.utc).isoformat(),"file_count":len(files),"archive":{"name":ZIP.name,"bytes":ZIP.stat().st_size,"sha256":zip_sha},"files":files}
(DIST / f"control12-commercial-v{VERSION}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(DIST / f"control12-commercial-v{VERSION}.sha256").write_text(f"{zip_sha}  {ZIP.name}\n")
print(json.dumps(manifest["archive"], indent=2))
