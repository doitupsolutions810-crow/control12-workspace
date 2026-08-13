#!/usr/bin/env python3
"""
CONTROL12 Workspace — User-facing ChatBot + Agent Orchestration Coding Workspace
================================================================================
Real-world surface for Trinity Core / Control12 Lattice.

Features:
- ChatBot agent interface (orchestrated through Cycle Kernel + AttestPipe)
- Coding workspace panel (submit tool specs → FORGE path)
- Live status of cryptographic spine, Host-ONLY, Quarantine, Bridge
- Explicit gates: ALLOW_AGENT_EXECUTION required for privileged actions
- No implicit network from Host-ONLY boundary

Control704 VIP / Avrone Due’Krey / Control12-lattice-op authenticated path.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT.parent
TRINITY = ARTIFACTS / "trinity-core"
OPS = ARTIFACTS / "control12-ops"
sys.path.insert(0, str(TRINITY))
sys.path.insert(0, str(OPS / "pipeline"))

app = FastAPI(
    title="CONTROL12 Workspace",
    description="ChatBot + Agent Orchestration Coding Workspace under Control12 Lattice",
    version="1.0.0",
)

_sessions: Dict[str, List[Dict[str, Any]]] = {}
_receipts: List[Dict[str, Any]] = []
_workspace_files: Dict[str, str] = {
    "README.md": "# CONTROL12 Coding Workspace\n\nAgent-orchestrated coding surface under AttestPipe + Cycle Kernel.\n",
    "main.py": "# Your code starts here\nprint('Hello from CONTROL12 Workspace')\n",
}


def _gate_ok() -> bool:
    return os.getenv("ALLOW_AGENT_EXECUTION") == "true"


def _try_bridge():
    try:
        from ops.bridge import OperationalBridge
        return OperationalBridge()
    except Exception:
        return None


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: Optional[str] = None
    system_hint: Optional[str] = "You are the CONTROL12 Workspace agent under Trinity Core."


class ToolSpecRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    description: str = Field(..., min_length=10, max_length=4000)
    capabilities: List[str] = Field(..., min_items=1, max_items=32)


class CodeUpdate(BaseModel):
    path: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., max_length=200_000)


class AgentAction(BaseModel):
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = ROOT / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CONTROL12 Workspace</h1><p>templates/index.html missing</p>")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "control12-workspace",
        "version": "1.0.0",
        "gate": "ALLOW_AGENT_EXECUTION",
        "gate_satisfied": _gate_ok(),
        "time": time.time(),
    }


@app.get("/api/status")
async def status():
    bridge = _try_bridge()
    base = {
        "workspace": "CONTROL12 ChatBot + Agent Orchestration Coding Workspace",
        "gate_satisfied": _gate_ok(),
        "sessions": len(_sessions),
        "receipts": len(_receipts),
        "files": list(_workspace_files.keys()),
        "trinity_core": str(TRINITY),
        "ops": str(OPS),
        "forge_url": os.getenv("CONTROL12_FORGE_URL", "http://localhost:3001"),
    }
    if bridge:
        try:
            base["bridge"] = bridge.status()
        except Exception as e:
            base["bridge_error"] = str(e)
    else:
        base["bridge"] = "not_loaded"
    return base


@app.post("/api/chat")
async def chat(body: ChatMessage):
    sid = body.session_id or str(uuid.uuid4())
    history = _sessions.setdefault(sid, [])
    user_turn = {"role": "user", "content": body.message, "ts": time.time()}
    history.append(user_turn)

    reply_text = (
        f"[CONTROL12 Workspace] Received: {body.message[:200]}\n\n"
        "I am the agent-orchestration surface under Trinity Core.\n"
        "- Use /api/tools/forge to submit a portable tool spec (gated).\n"
        "- Use /api/code to read/write workspace files.\n"
        "- Use /api/agent to run Cycle Kernel / AttestPipe actions when ALLOW_AGENT_EXECUTION=true.\n"
        "- Status: /api/status\n"
    )

    receipt = None
    if _gate_ok():
        bridge = _try_bridge()
        if bridge:
            try:
                att = bridge.attest.attest_artifact(
                    {"session": sid, "message_digest": body.message[:64]},
                    policy="chat_turn",
                )
                receipt = {
                    "receipt_hash": att.get("receipt_hash"),
                    "epoch": att.get("zk_proof", {}).get("epoch"),
                }
                _receipts.append(receipt)
                cycle = bridge.kernel.full_cycle(
                    data={"chat": body.message[:200], "session": sid},
                    decision={"action": "respond", "channel": "workspace"},
                    attestation=receipt["receipt_hash"],
                )
                reply_text += (
                    f"\n[Attested] receipt={receipt['receipt_hash'][:16]}… "
                    f"cycle={cycle.cycle_id} phase={cycle.phase}"
                )
            except Exception as e:
                reply_text += f"\n[Bridge note] {e}"

    assistant_turn = {"role": "assistant", "content": reply_text, "ts": time.time(), "receipt": receipt}
    history.append(assistant_turn)
    return {"session_id": sid, "reply": reply_text, "receipt": receipt, "history_len": len(history)}


@app.post("/api/tools/forge")
async def forge_tool(body: ToolSpecRequest):
    if not _gate_ok():
        raise HTTPException(403, detail="ALLOW_AGENT_EXECUTION must be true to forge tools")
    bridge = _try_bridge()
    if not bridge:
        raise HTTPException(503, detail="Operational Bridge not available")
    result = bridge.forge_tool_spec(body.name, body.description, body.capabilities)
    _receipts.append({"type": "forge", "receipt": result.get("attestation", {}).get("receipt_hash")})
    return {
        "status": "forged_intent",
        "result": result,
        "next": "POST the returned spec to CONTROL12 FORGE /api/forge when the forge service is running",
    }


@app.get("/api/code")
async def list_code():
    return {"files": {k: len(v) for k, v in _workspace_files.items()}}


@app.get("/api/code/{path:path}")
async def get_code(path: str):
    if path not in _workspace_files:
        raise HTTPException(404, detail="File not found in workspace")
    return {"path": path, "content": _workspace_files[path]}


@app.put("/api/code")
async def put_code(body: CodeUpdate):
    clean = body.path.replace("..", "").lstrip("/")
    if not clean or len(clean) > 200:
        raise HTTPException(400, detail="Invalid path")
    _workspace_files[clean] = body.content
    return {"path": clean, "bytes": len(body.content), "status": "saved"}


@app.post("/api/agent")
async def agent_action(body: AgentAction):
    if not _gate_ok():
        raise HTTPException(403, detail="ALLOW_AGENT_EXECUTION required")
    bridge = _try_bridge()
    if not bridge:
        raise HTTPException(503, detail="Bridge unavailable")
    if body.action == "pipeline":
        prompt = str(body.payload.get("prompt", "workspace agent action"))
        return bridge.run_avrone_pipeline(prompt)
    if body.action == "status":
        return bridge.status()
    if body.action == "cycle":
        data = body.payload.get("data", {"source": "workspace"})
        decision = body.payload.get("decision", {"action": "observe"})
        att = bridge.attest.attest_artifact(data, policy="agent_cycle")
        cycle = bridge.kernel.full_cycle(data, decision, att["receipt_hash"])
        return {"cycle_id": cycle.cycle_id, "phase": cycle.phase, "executed": cycle.executed, "receipt": att["receipt_hash"]}
    raise HTTPException(400, detail=f"Unknown action: {body.action}")


@app.get("/api/receipts")
async def receipts():
    return {"count": len(_receipts), "recent": _receipts[-20:]}


static_dir = ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
