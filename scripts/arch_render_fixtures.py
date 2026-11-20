"""Miniature flows for testing the architecture renderer (P26). Used by scripts/test_arch_render.py and for looking at the views before Copilot
has written the real flows. Standard library only. The actors are real node ids of data/arch/model.json; nothing here is written into the repo's data."""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

COMMIT = "3727ae323c26919558a3b5f6db73c81a578537fb"


def ev(path, qual, a, b, status="fresh"):
    return [{"path": path, "qual": qual, "lines": [a, b], "hash": None, "status": status}]


def step(i, title, actor, kind="control", nxt=None, status="fresh", gate=None, conf="high", unknowns=None):
    return {"id": f"s{i:02d}", "title": title, "actor": actor, "kind": kind, "text": f"{title}. Plain-English detail for step {i}.", "gate": gate,
            "next": nxt if nxt is not None else [f"s{i + 1:02d}"], "confidence": conf, "unknowns": unknowns or [], "status": status,
            "evidence": ev("backend/api/task_runner.py", f"fn_{i}", 10 * i, 10 * i + 8, status)}


def pipeline(kind="pipeline", fid="task-pipeline"):
    steps = [
        step(1, "Chat panel posts the task", "frontend/app/components"),
        step(2, "Validate and enqueue the task", "backend/api"),
        step(3, "Classify the tier and try the cache", "backend/eo"),
        step(4, "Route to an agent graph", "backend/eo", status="stale"),
        step(5, "Gatekeeper decides whether to loop again", "backend/eo", "gate", ["s06", "s04"], gate={"tier": "T1", "who": "policy"}),
        step(6, "Worker prepares the model request", "backend/agents", "data", conf="low", unknowns=["Why the retry limit is 3 is not stated in the code"]),
        step(7, "Call the model provider", "ext:llm-providers", "external", status="unverified"),
        step(8, "Persist the result", "store:postgres", "store"),
        step(9, "Push the reply over WebSocket", "backend/api", nxt=[], status="broken"),
    ]
    return {"schema": 1, "flow": fid, "title": "Task pipeline", "kind": kind, "summary": "From a posted task to a delivered reply.", "commit": COMMIT,
            "actors": ["frontend/app/components", "backend/api", "backend/eo", "backend/agents", "ext:llm-providers", "store:postgres"], "steps": steps,
            "doc_conflicts": [{"chapter": "doc-minime-feature-guide#1-what-minime-is", "note": "The book says 25 stages, the code registers 27"}],
            "unknowns": ["Whether the cache is consulted for tier 0"], "status": "broken", "counts": {"fresh": 5, "stale": 1, "broken": 1, "unverified": 1},
            "stage_check": {"checked": ["router-tiers"], "missing": ["responder"], "unavailable": []}}


def sequence():
    f = pipeline("sequence", "request-path")
    f["title"] = "Request path"
    return f


def lifecycle():
    states = [{"id": "queued", "label": "Queued"}, {"id": "running", "label": "Running"}, {"id": "awaiting", "label": "Awaiting confirmation"},
              {"id": "delivered", "label": "Delivered", "terminal": True}, {"id": "failed", "label": "Failed", "terminal": True}, {"id": "denied", "label": "Denied", "terminal": True}]

    def t(i, a, b, trig, status="fresh", gate=None):
        return {"id": f"t{i:02d}", "from": a, "to": b, "trigger": trig, "text": trig, "gate": gate, "confidence": "high", "unknowns": [], "status": status,
                "evidence": ev("backend/eo/executor.py", f"on_{i}", 20 * i, 20 * i + 9, status)}
    tr = [t(1, "queued", "running", "worker picks it up"), t(2, "running", "awaiting", "a tool needs approval", "stale", {"tier": "T3", "who": "user"}), t(3, "awaiting", "running", "user approves"),
          t(4, "awaiting", "denied", "user denies or 15 minutes pass"), t(5, "running", "delivered", "reply sent"), t(6, "running", "failed", "an error is raised", "broken"), t(7, "failed", "queued", "fixer pool retries", "unverified")]
    return {"schema": 1, "flow": "taskrun-lifecycle", "title": "Task run lifecycle", "kind": "lifecycle", "summary": "The states one task moves through.", "commit": COMMIT,
            "actors": ["backend/eo"], "states": states, "transitions": tr, "status": "broken", "counts": {"fresh": 4, "stale": 1, "broken": 1, "unverified": 1}, "stage_check": {"checked": [], "missing": [], "unavailable": []}}


def gated():
    f = pipeline("gated", "daemon-approval")
    f["title"] = "Daemon approval"
    return f


FLOWS = {"task-pipeline": pipeline, "task-sequence": sequence, "taskrun-lifecycle": lifecycle, "daemon-approval": gated}
FLOW_OF_VIEW = {"task-pipeline": "task-pipeline", "task-sequence": "request-path", "taskrun-lifecycle": "taskrun-lifecycle", "daemon-approval": "daemon-approval"}


def with_flows(site: Path) -> dict:
    """Write the fixture flows into the view shards and the index of a COPY of the site at `site`. Returns {view id: flow}."""
    model = json.loads((site / "data/arch/model.json").read_text(encoding="utf-8"))
    by = {n["id"]: n for n in model["nodes"]}
    idx_path = site / "data/index/arch.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    out = {}
    for vid, make in FLOWS.items():
        flow = make()
        p = site / f"data/arch/views/{vid}.json"
        shard = json.loads(p.read_text(encoding="utf-8"))
        ids = sorted(set(flow["actors"]) | {i.get("actor") for i in flow.get("steps", []) if i.get("actor")})
        shard["flow_data"] = flow
        shard["status"] = flow["status"]
        shard["nodes"] = [by[i] for i in ids if i in by]
        shard["edges"] = []
        p.write_text(json.dumps(shard, indent=1, sort_keys=True), encoding="utf-8")
        fid = FLOW_OF_VIEW[vid]
        if fid in idx["flows"]:
            idx["flows"][fid]["status"] = flow["status"]
        out[vid] = flow
    idx_path.write_text(json.dumps(idx, indent=1, sort_keys=True), encoding="utf-8")
    return out


def copy_site(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "node_modules", "src", "__pycache__"), dirs_exist_ok=True)
    return dst
