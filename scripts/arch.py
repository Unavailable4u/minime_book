#!/usr/bin/env python3
"""The Atlas architecture model (patch P25): diagrams that are generated, never drawn.

Standard library only. Output is deterministic (sorted keys, no timestamps), so `--check` can compare it
byte-for-byte (line endings are normalised on read; files are always written with LF).

Three parts, three guarantees (the rule is in MINIME_BOOK_REDESIGN_PLAN.md section 6.7)

  STRUCTURE  what exists and what connects: containers, import / API-call / table / env edges, route groups, agents,
             tables, protocol messages, the stage lists read out of the code. Derived by this script from the census and
             the data/code/*.json files. No AI, so it cannot be stale. -> data/arch/derived.json
  FLOWS      the ordered steps of a pipeline, a lifecycle, an approval path. Written by Copilot (prompt C / D in
             UPDATING.md, Step 2c) into MiniMe/graphify-out/atlas-arch/<flow id>.json. Every step must cite real code;
             when the cited code changes the step turns stale. -> data/arch/flows/<flow id>.json
  LAYOUT     where things sit. Yours: content/arch-layout.json (virtual nodes such as the database, pinned positions),
             and the positions already curated in content/topology.json.

`build` merges them into data/arch/model.json plus one small shard per view (data/arch/views/<view id>.json), and the
flow status into data/index/arch.json (the Coverage page reads that).

Node ids
  A node id is a real folder of the repo (the first folder of a topology box: `backend/eo`, `m2c/src/m2c/sandbox`), or a
  virtual node declared in content/arch-layout.json (`store:postgres`), or `group:<name>` for a grouping box. The ids of
  content/topology.json (`eo`, `web-components`) are kept as "aliases": a flow that uses one is accepted (with a warning)
  and rewritten to the real id. A topology box that repeats another box's folder (m2c-core) is merged into it.

Flow files (schema 1; written out for Copilot in _SCHEMA.md by `todo`, which is generated from this file: SCHEMA_MD, LIMITS)
  Evidence is mandatory. Errors block `ingest` (malformed JSON, wrong types, a secret-looking string, an unknown actor, a step
  without evidence, a bad `next`, a renumbered or reused step id, and a flow written at the current commit that cites a
  function that does not exist: Copilot just invented it). Warnings never block (unknown keys, over-long text, an actor
  written as an alias, a citation of code that has since gone, a flow that has no step for a stage the code registers).

Freshness of one citation (from git objects and the census, never the working tree)
  fresh       its hash equals the census hash of that symbol (or the file is unchanged since the flow was written)
  stale       the hash differs: the cited code changed
  broken      the cited file or symbol is no longer in the census
  unverified  there is nothing to compare (no hash, and MiniMe's git is not here to tell whether the file changed)
  A step takes the worst of its citations, a flow the worst of its steps.

Commands
  arch.py status   [--minime M]                       one line per flow: written, fresh / stale / broken / unverified
  arch.py todo     --minime M [--limit N]             write M/graphify-out/atlas-arch/_SCHEMA.md and _todo.json for Copilot:
                                                      the flows not written yet and the steps whose evidence changed
  arch.py validate [--dir D | --minime M]             check flow files against the schema and the census
  arch.py ingest   --minime M [--check] [--skip-invalid]
                                                      validate, copy into data/arch/flows, fill evidence hashes, then build
  arch.py build    [--minime M] [--check]             rebuild derived.json, model.json, the view shards and data/index/arch.json
                                                      from the committed flows (no MiniMe needed; with it, the stage lists
                                                      are read from git and freshness of older flows can be judged)

The functions are importable on purpose; the census loading, blob lookup and secret patterns come from scripts/notes.py (P11).
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import arch_extract  # noqa: E402  (P25: stage lists read from git with ast)
import notes  # noqa: E402  (P11: census access, blob lookup, secret patterns)

ROOT = HERE.parent
SCHEMA = 1
ARCH_DIR = "data/arch"
FLOWS_DIR = f"{ARCH_DIR}/flows"
VIEWS_DIR = f"{ARCH_DIR}/views"
DERIVED_FILE = f"{ARCH_DIR}/derived.json"
MODEL_FILE = f"{ARCH_DIR}/model.json"
INDEX_FILE = "data/index/arch.json"
REGISTRY_FILE = "content/arch-flows.json"
LAYOUT_FILE = "content/arch-layout.json"
TOPOLOGY_FILE = "content/topology.json"
ARCH_SUBDIR = "graphify-out/atlas-arch"          # inside the MiniMe checkout (ignored by MiniMe's git, like atlas-notes)
INPUTS = {                                       # optional inputs: whatever exists is used, the rest is simply absent
    "imports": "data/code/imports.json",
    "routes": "data/code/routes.json",
    "agents": "data/code/agents.json",
    "protocol": "data/code/protocol.json",
    "schema": "data/code/schema.json",
    "infra": "data/code/infra.json",
    "folders": "data/graph/folders.json",
}

FLOW_KINDS = ("pipeline", "sequence", "lifecycle", "gated")
STEP_KINDS = ("control", "data", "store", "external", "gate")
GATE_WHO = ("user", "daemon", "policy")
VIEW_TYPES = ("layered", "sequence", "lifecycle", "gated", "catalog")
VIEW_SOURCES = ("derived", "flow")
VIRTUAL_KINDS = ("store", "external", "queue")
EDGE_KINDS = ("import", "api-call", "graph", "declared", "db", "env", "protocol")
STATUS_ORDER = ("fresh", "unverified", "stale", "broken")           # worst last
CONFIDENCE = notes.CONFIDENCE

LIMITS = {"steps": 40, "title": 60, "text": 240, "summary": 240, "trigger": 120, "label": 60, "list_n": 12, "list_item": 240}
TOP_KEYS = {"schema", "flow", "title", "kind", "summary", "commit", "actors", "steps", "states", "transitions", "doc_conflicts", "unknowns"}
STEP_KEYS = {"id", "title", "actor", "kind", "text", "gate", "next", "evidence", "confidence", "unknowns", "subflow"}
STATE_KEYS = {"id", "label", "terminal"}
TRANSITION_KEYS = {"id", "from", "to", "trigger", "text", "evidence", "confidence", "unknowns", "actor", "gate"}
EVIDENCE_KEYS = {"path", "qual", "lines", "hash"}
GATE_KEYS = {"tier", "who"}
CONFLICT_KEYS = {"chapter", "note"}

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
STEP_ID = re.compile(r"^s(\d{2,4})$")
TRANSITION_ID = re.compile(r"^t(\d{2,4})$")
NODE_ID_VIRTUAL = re.compile(r"^(store|ext|queue):[a-z0-9][a-z0-9-]*$")
HEX40, HEX10 = notes.HEX40, notes.HEX10

read_lf = notes.read_lf
load_json = notes.load_json
dumps = notes.dumps
Problems = notes.Problems


# ----------------------------------------------------------------------------- the registry and the layout
def load_registry(root: Path) -> dict:
    """content/arch-flows.json as {"flows": [...], "views": [...], "extractors": [...]}; an absent file is an empty registry."""
    raw = load_json(Path(root) / REGISTRY_FILE, None)
    raw = raw if isinstance(raw, dict) else {}
    return {"flows": [f for f in raw.get("flows", []) if isinstance(f, dict) and f.get("id")],
            "views": [v for v in raw.get("views", []) if isinstance(v, dict) and v.get("id")],
            "extractors": [x for x in raw.get("extractors", []) if isinstance(x, dict) and x.get("id")]}


def registry_problems(reg: dict, root: Path | None = None) -> list[str]:
    """What is wrong with content/arch-flows.json (the same rules scripts/check_site.py applies, for people who run only arch.py)."""
    out: list[str] = []
    flow_ids: set[str] = set()
    for f in reg["flows"]:
        fid = f["id"]
        if not SLUG.match(fid):
            out.append(f"flow {fid!r}: the id must be lower-case letters, digits and hyphens")
        if fid in flow_ids:
            out.append(f"flow {fid!r}: duplicate id")
        flow_ids.add(fid)
        if f.get("kind") not in FLOW_KINDS:
            out.append(f"flow {fid!r}: kind must be one of {', '.join(FLOW_KINDS)}")
        if not isinstance(f.get("seeds"), list) or not f["seeds"]:
            out.append(f"flow {fid!r}: needs a non-empty list of seeds (a file, or path::qual)")
        for x in f.get("extractors", []):
            if x.get("kind") not in arch_extract.KINDS:
                out.append(f"flow {fid!r}: extractor {x.get('id')!r} has an unknown kind")
    view_ids: set[str] = set()
    for v in reg["views"]:
        vid = v["id"]
        if vid in view_ids:
            out.append(f"view {vid!r}: duplicate id")
        view_ids.add(vid)
        if v.get("type") not in VIEW_TYPES:
            out.append(f"view {vid!r}: type must be one of {', '.join(VIEW_TYPES)}")
        if v.get("source") not in VIEW_SOURCES:
            out.append(f"view {vid!r}: source must be one of {', '.join(VIEW_SOURCES)}")
        if v.get("source") == "flow" and v.get("flow") not in flow_ids:
            out.append(f"view {vid!r}: flow {v.get('flow')!r} is not a flow of the registry")
        bad = [k for k in v.get("edge_kinds", []) if k not in EDGE_KINDS]
        if bad:
            out.append(f"view {vid!r}: unknown edge kind(s) {', '.join(map(str, bad))}")
        if root is not None and v.get("replaces") and not (Path(root) / v["replaces"]).is_file():
            out.append(f"view {vid!r}: replaces {v['replaces']}, which does not exist")
    return out


def layout_problems(layout: dict) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in layout.get("virtual", []):
        vid = v.get("id") if isinstance(v, dict) else None
        if not isinstance(vid, str) or not NODE_ID_VIRTUAL.match(vid):
            out.append(f"virtual node {vid!r}: the id must look like store:postgres, ext:name or queue:name")
            continue
        if vid in seen:
            out.append(f"virtual node {vid!r}: duplicate id")
        seen.add(vid)
        if v.get("kind") not in VIRTUAL_KINDS:
            out.append(f"virtual node {vid!r}: kind must be one of {', '.join(VIRTUAL_KINDS)}")
        for k in ("label", "source"):
            if not isinstance(v.get(k), str) or not v[k].strip():
                out.append(f"virtual node {vid!r}: needs a {k}")
    return out


# ----------------------------------------------------------------------------- context
class Ctx:
    """Everything the freshness code needs, loaded once. A plain class (see notes.Ctx for why)."""

    def __init__(self, commit: str = ""):
        self.commit = commit                # census commit (full sha)
        self.head = ""                      # MiniMe HEAD, when MiniMe is here
        self.minime: Path | None = None
        self.files: dict = {}               # path -> census file record
        self.symbols: dict = {}             # path -> {qual: (symbol, kind)}
        self.blobs: dict | None = None      # path -> blob id at the census commit; None = git unavailable
        self.warnings: list = []
        self._blobs_at: dict = {}

    def blobs_at(self, rev: str):
        """{path: blob id} at another commit (the one a flow was written at), or None when git cannot say."""
        if not self.minime or not HEX40.match(rev or ""):
            return None
        if rev not in self._blobs_at:
            self._blobs_at[rev] = notes.ls_tree_blobs(self.minime, rev)
        return self._blobs_at[rev]

    def current_commits(self) -> set[str]:
        return {c for c in (self.commit, self.head) if c}


def build_ctx(root: Path, minime=None, census: dict | None = None) -> Ctx:
    root = Path(root)
    census = census if census is not None else load_json(root / notes.CENSUS_FILE, None)
    if not census:
        sys.exit(f"{root / notes.CENSUS_FILE} not found. Run scripts/refresh_atlas.py first.")
    ctx = Ctx(commit=notes.commit_of(census))
    flist = notes.census_files(census)
    ctx.files = {f["path"]: f for f in flist}
    ctx.symbols = {p: notes.symbol_table(f) for p, f in ctx.files.items()}
    if minime and Path(minime).is_dir():
        ctx.minime = Path(minime)
        r = notes.git(minime, "rev-parse", "HEAD")
        ctx.head = r.stdout.decode().strip() if not r.returncode else ""
        blobs = notes.ls_tree_blobs(minime, ctx.commit) if len(ctx.commit) == 40 else None
        if blobs is None:
            blobs = notes.ls_tree_blobs(minime, "HEAD")
            if blobs is not None:
                ctx.warnings.append(f"census commit {ctx.commit[:7] or '(unknown)'} is not in {minime}; blobs were read from its HEAD instead")
        ctx.blobs = blobs
    return ctx


# ----------------------------------------------------------------------------- derived structure
def _folder_of(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _under(path: str, folder: str) -> bool:
    return path == folder or path.startswith(folder + "/")


def derive(ctx: Ctx, topo: dict, layout: dict, inputs: dict, extractions: list[dict]) -> tuple[dict, dict]:
    """(derived, alias): the structure of the system, from the census and the code data, and {topology id: node id}. Pure and deterministic.

    nodes   containers (one per topology box, id = its first folder), grouping boxes (`group:x`) and the virtual nodes
            of the layout file. A container carries counts of its non-test files (inclusive of boxes inside it).
    edges   {"from", "to", "kind", "weight"} with kind import | api-call | graph | declared | db | env | protocol. A file
            belongs to the node with the longest folder prefix; edges inside one node are not drawn.
    """
    notes_: list[str] = []
    nodes: dict[str, dict] = {}
    alias: dict[str, str] = {}                     # topology id -> node id
    folder_owner: dict[str, str] = {}              # folder -> node id (first claim wins)
    groups = [g for g in topo.get("groups", []) if isinstance(g, dict) and g.get("id")]
    for g in groups:
        nodes["group:" + g["id"]] = {"id": "group:" + g["id"], "kind": "group", "label": g.get("label") or g["id"]}
    tnodes = [t for t in topo.get("nodes", []) if isinstance(t, dict) and t.get("id")]
    for t in tnodes:
        folders = [f for f in t.get("folders", []) if isinstance(f, str) and f]
        if not folders:
            continue
        primary = folders[0]
        if primary in nodes:                        # another box already claimed this folder (m2c and m2c-core): one node, two names
            alias[t["id"]] = primary
            if t["id"] not in nodes[primary]["aliases"]:
                nodes[primary]["aliases"].append(t["id"])
            notes_.append(f"topology box {t['id']!r} repeats the folder {primary} of {nodes[primary]['aliases'][0]!r}; merged into it")
            continue
        alias[t["id"]] = primary
        nodes[primary] = {"id": primary, "kind": "container", "label": t.get("label") or primary, "folders": folders,
                          "aliases": [t["id"]], "what": t.get("what") or "", "chapter": t.get("chapter"), "diagram": t.get("diagram")}
        if t.get("group") and "group:" + t["group"] in nodes:
            nodes[primary]["group"] = "group:" + t["group"]
        for f in folders:
            folder_owner.setdefault(f, primary)
    for t in tnodes:                                # boxes inside boxes (the M2C client and its packages)
        nid, par = alias.get(t["id"]), alias.get(t.get("parent") or "")
        if nid and par and nid != par:
            nodes[nid]["parent"] = par
            nodes[par].setdefault("children", []).append(nid)
    for n in nodes.values():
        if n.get("children"):
            n["children"] = sorted(n["children"])
        if n.get("aliases"):
            n["aliases"] = sorted(n["aliases"])
    for v in layout.get("virtual", []):
        if isinstance(v, dict) and isinstance(v.get("id"), str) and NODE_ID_VIRTUAL.match(v["id"]) and v["id"] not in nodes:
            nodes[v["id"]] = {"id": v["id"], "kind": v.get("kind", "store"), "label": v.get("label") or v["id"], "virtual": True,
                              "source": v.get("source") or "", **({"group": v["group"]} if v.get("group") in nodes else {})}

    ordered = sorted(folder_owner.items(), key=lambda kv: (-len(kv[0]), kv[0]))

    def owner(path: str):
        for folder, nid in ordered:
            if _under(path, folder):
                return nid
        return None

    for n in nodes.values():                        # counts: every non-test source file under the node's folders
        if n["kind"] != "container":
            continue
        fl = n["folders"]
        sel = [r for p, r in ctx.files.items() if not r.get("test") and not r.get("binary") and any(_under(p, f) for f in fl)]
        n["files"] = len(sel)
        n["code"] = sum(int(r.get("code") or 0) for r in sel)
        n["functions"] = sum(len(r.get("functions") or []) for r in sel)

    acc: collections.Counter = collections.Counter()
    undirected: set[tuple] = set()
    gate: dict[tuple, bool] = {}
    labels: dict[tuple, str] = {}
    contract = {i for i, n in nodes.items() if n.get("group") == "group:contract"}

    def add(a, b, kind, w=1):
        if a and b and a != b:
            if kind in ("import", "graph") and (a in contract or b in contract):
                kind = "protocol"                   # touching the contract (protocol/) is the protocol, not a plain import
            acc[(a, b, kind)] += w

    imp = (inputs.get("imports") or {}).get("imports") or {}
    for src, targets in imp.items():
        a = owner(src)
        for t in targets:
            add(a, owner(t[0] if isinstance(t, list) else t), "import")
    for r in (inputs.get("routes") or {}).get("routes") or []:
        b = owner(r.get("file", ""))
        for c in r.get("callers") or []:
            add(owner(c.get("file", "")), b, "api-call")
    for pair in (inputs.get("folders") or {}).get("pairs") or []:
        if len(pair) == 3:
            a, b = (next((nid for f, nid in ordered if _under(x, f)), None) for x in pair[:2])
            if a and b and a != b:
                a, b = sorted((a, b))
                kind = "protocol" if (a in contract or b in contract) else "graph"
                acc[(a, b, kind)] += int(pair[2])
                undirected.add((a, b, kind))
    for e in topo.get("edges", []):
        if isinstance(e, dict) and e.get("declared"):
            a, b = alias.get(e.get("from", "")), alias.get(e.get("to", ""))
            if a and b and a != b:
                acc.setdefault((a, b, "declared"), 0)
                labels[(a, b, "declared")] = e.get("label") or ""
                gate[(a, b, "declared")] = bool(e.get("gate"))
    env_usage = (inputs.get("census_extra") or {}).get("env_usage") or {}
    table_refs = (inputs.get("census_extra") or {}).get("table_refs") or {}
    for v in layout.get("virtual", []):
        if not isinstance(v, dict) or v.get("id") not in nodes or not nodes[v["id"]].get("virtual"):
            continue
        ef = v.get("edges_from") or {}
        allowed = set(ef.get("from_groups") or ([v["group"]] if v.get("group") else []))     # default: only code in the node's own group
        add_v = lambda f, vid, kind: (lambda o: add(o, vid, kind) if o and (not allowed or nodes[o].get("group") in allowed) else None)(owner(f))
        env_names = list(ef.get("env") or [])
        if ef.get("providers"):
            for p in (inputs.get("agents") or {}).get("providers") or []:
                env_names += [s for s in p.get("slots") or []]
        for name in sorted(set(env_names)):
            for f in env_usage.get(name) or []:
                add_v(f, v["id"], "env")
        if ef.get("tables"):
            for files in table_refs.values():
                for f in files or []:
                    add_v(f, v["id"], "db")
    edges = []
    for (a, b, kind), w in sorted(acc.items()):
        e = {"from": a, "to": b, "kind": kind, "weight": w}          # a declared edge keeps weight 0: it is stated, not counted
        if (a, b, kind) in undirected:
            e["directed"] = False
        if (a, b, kind) in labels:
            e["label"] = labels[(a, b, kind)]
            if gate.get((a, b, kind)):
                e["gate"] = True
        edges.append(e)

    # ---- catalogues: the lists the System page shows next to the drawings
    rg: dict[str, dict] = {}
    for r in (inputs.get("routes") or {}).get("routes") or []:
        g = rg.setdefault(r.get("file", ""), {"file": r.get("file", ""), "node": owner(r.get("file", "")), "router": r.get("router"),
                                              "prefix": r.get("include_prefix") or "", "routes": []})
        g["routes"].append([r.get("method", ""), r.get("path", ""), r.get("handler", ""), int(r.get("line") or 0), r.get("response_model") or None])
    route_groups = [dict(g, routes=sorted(g["routes"], key=lambda x: (x[3], x[0], x[1]))) for _, g in sorted(rg.items())]
    ag = inputs.get("agents") or {}
    role_modules = next((x["items"] for x in extractions if x.get("id") == "role-modules" and x.get("found")), None)
    agents = {"modules": sorted(({"name": m.get("name"), "file": m.get("file")} for m in ag.get("modules") or []), key=lambda m: m["name"] or ""),
              "roles": sorted(r.get("key") for r in ag.get("roles") or [] if r.get("key")),
              "providers": sorted(p.get("name") for p in ag.get("providers") or [] if p.get("name")),
              "role_modules": role_modules}
    tables = [{"name": t, "nodes": sorted({owner(f) for f in files or [] if owner(f)})} for t, files in sorted(table_refs.items()) if files]
    proto = inputs.get("protocol") or {}
    protocol = {"messages": [{"type": m.get("type"), "direction": m.get("direction")} for m in proto.get("messages") or []],
                "tools": [{"name": t.get("name"), "risk": t.get("risk")} for t in proto.get("tools") or []]}
    return {
        "schema": SCHEMA, "commit": ctx.commit,
        "sources": {"topology": bool(tnodes), "layout": bool(layout.get("virtual")), **{k: bool(inputs.get(k)) for k in sorted(INPUTS)}},
        "nodes": [nodes[k] for k in sorted(nodes)], "edges": edges,
        "catalogues": {"routes": route_groups, "agents": agents, "tables": tables, "protocol": protocol},
        "extractions": extractions, "notes": sorted(notes_),
    }, alias


def build_layout(topo: dict, layout: dict, nodes: list[dict], alias: dict) -> dict:
    """Positions: the curated ones of content/topology.json, overridden by the pins of content/arch-layout.json."""
    ids = {n["id"] for n in nodes}
    pins: dict[str, dict] = {}
    for t in topo.get("nodes", []):
        nid = alias.get(t.get("id", ""))
        if nid in ids and nid not in pins and isinstance(t.get("x"), (int, float)) and isinstance(t.get("y"), (int, float)):
            pins[nid] = {"x": t["x"], "y": t["y"], "from": "topology"}
    for nid, p in (layout.get("pins") or {}).items():
        if nid in ids and isinstance(p, dict) and isinstance(p.get("x"), (int, float)) and isinstance(p.get("y"), (int, float)):
            pins[nid] = {"x": p["x"], "y": p["y"], "from": "layout"}
    grp = [{"id": "group:" + g["id"], "label": g.get("label") or g["id"], **{k: g[k] for k in ("x", "y", "w", "h", "align") if k in g}}
           for g in topo.get("groups", []) if isinstance(g, dict) and g.get("id")]
    return {"view": topo.get("view"), "groups": grp, "pins": {k: pins[k] for k in sorted(pins)},
            "unplaced": sorted(n["id"] for n in nodes if n["kind"] != "group" and n["id"] not in pins)}


class NodeIndex:
    """Resolves the actor of a flow step to a node id: exact id, a topology alias, or a folder inside a node (the last two warn)."""

    def __init__(self, nodes: list[dict]):
        self.ids = {n["id"] for n in nodes if n["kind"] != "group"}
        self.groups = {n["id"] for n in nodes if n["kind"] == "group"}
        self.alias = {a: n["id"] for n in nodes for a in n.get("aliases", [])}
        self.folders = sorted(((f, n["id"]) for n in nodes for f in n.get("folders", [])), key=lambda kv: (-len(kv[0]), kv[0]))
        self.listed = dict(self.folders)                # a folder a box lists (backend/utils in "Shared services") is a fair way to name it

    def resolve(self, actor):
        """(node id or None, how) where how is "id", "listed folder", "alias", "folder" or a reason it failed."""
        if not isinstance(actor, str):
            return None, "not text"
        if actor in self.ids:
            return actor, "id"
        if actor in self.groups:
            return None, "is a grouping box, not a place where code runs"
        if actor in self.listed:
            return self.listed[actor], "listed folder"
        if actor in self.alias:
            return self.alias[actor], "alias"
        for folder, nid in self.folders:
            if _under(actor, folder):
                return nid, "folder"
        return None, "is not a node of the model"


# ----------------------------------------------------------------------------- flows: validation
def _evidence_list(p: Problems, where: str, v, ctx: Ctx | None, flow_commit: str, current: bool) -> None:
    if not isinstance(v, list) or not v:
        p.errors.append(f"{where}.evidence: needs at least one citation of real code. If you cannot point to code, do not write the step; put it in unknowns")
        return
    for i, e in enumerate(v):
        w = f"{where}.evidence[{i}]"
        if not isinstance(e, dict):
            p.errors.append(f"{w}: must be an object {{path, qual, lines, hash}}")
            continue
        extra = sorted(set(e) - EVIDENCE_KEYS)
        if extra:
            p.warnings.append(f"{w}: unknown key(s) {', '.join(extra)} (ignored)")
        path, qual = e.get("path"), e.get("qual")
        if not isinstance(path, str) or not path:
            p.errors.append(f"{w}.path: must be a repo-relative path")
            continue
        if qual is not None and not isinstance(qual, str):
            p.errors.append(f"{w}.qual: must be a qualified name or null")
            continue
        lines = e.get("lines")
        ok_lines = False
        if lines is not None:
            if (isinstance(lines, list) and len(lines) == 2 and all(isinstance(n, int) and not isinstance(n, bool) for n in lines)
                    and 1 <= lines[0] <= lines[1]):
                ok_lines = True
            else:
                p.errors.append(f"{w}.lines: must be [first line, last line] with 1 <= first <= last")
        if qual is None and lines is None:
            p.errors.append(f"{w}: cite a function or class (qual), or give the lines when it is module-level code")
        h = e.get("hash")
        if h is not None and not (isinstance(h, str) and HEX10.match(h)):
            p.errors.append(f"{w}.hash: leave it null (ingest fills it) or a 10-character hex hash")
        if ctx is None:
            continue
        rec = ctx.files.get(path)
        missing = (rec is None) if qual is None else (qual not in ctx.symbols.get(path, {}))
        if missing:
            what = f"{path} is not in the census" if rec is None else f"{path} has no symbol {qual!r} in the census"
            if current:
                p.errors.append(f"{w}: {what}, although this flow was written at the current commit ({flow_commit[:7]}). Cite only code that exists")
            else:
                p.warnings.append(f"{w}: {what} (it may have gone since the flow was written)")
        elif qual is not None and ok_lines and current:
            s = ctx.symbols[path][qual][0]
            a, b = s.get("start"), s.get("end")
            if isinstance(a, int) and isinstance(b, int) and (lines[1] < a or lines[0] > b):
                p.warnings.append(f"{w}: lines {lines[0]}-{lines[1]} are outside {qual} (lines {a}-{b})")


def _gate(p: Problems, where: str, v, kind) -> None:
    if v is None:
        if kind == "gate":
            p.errors.append(f"{where}: a step of kind \"gate\" needs a gate object {{\"tier\": ..., \"who\": user|daemon|policy}}")
        return
    if not isinstance(v, dict):
        p.errors.append(f"{where}.gate: must be null or {{\"tier\": ..., \"who\": user|daemon|policy}}")
        return
    extra = sorted(set(v) - GATE_KEYS)
    if extra:
        p.warnings.append(f"{where}.gate: unknown key(s) {', '.join(extra)} (ignored)")
    if not isinstance(v.get("tier"), str) or not v["tier"].strip():
        p.errors.append(f"{where}.gate.tier: must be text such as \"T3\"")
    if v.get("who") not in GATE_WHO:
        p.errors.append(f"{where}.gate.who: must be one of {', '.join(GATE_WHO)}")


def validate_flow(flow, filename: str | None = None, ctx: Ctx | None = None, nodes: NodeIndex | None = None,
                  flow_ids=None, prev: dict | None = None) -> Problems:
    """Everything wrong with one flow file. `prev` is the copy already ingested (for the stable-id rules)."""
    p = Problems()
    if not isinstance(flow, dict):
        p.errors.append("the file must contain one JSON object")
        return p
    extra = sorted(set(flow) - TOP_KEYS)
    if extra:
        p.warnings.append(f"unknown top-level key(s) {', '.join(extra)} (ignored)")
    if flow.get("schema") != SCHEMA:
        p.errors.append(f"schema: must be {SCHEMA}")
    fid = flow.get("flow")
    if not isinstance(fid, str) or not SLUG.match(fid):
        p.errors.append('flow: must be the flow id (lower-case letters, digits and hyphens), the same as the file name')
        fid = None
    elif filename and filename != f"{fid}.json":
        p.errors.append(f"flow: {fid!r} does not match the file name {filename} (it must be <flow>.json)")
    elif flow_ids is not None and fid not in flow_ids:
        p.warnings.append(f"flow {fid!r} is not in {REGISTRY_FILE}; no view will draw it")
    notes._text(p, "title", flow.get("title"), LIMITS["title"], required=True)
    notes._text(p, "summary", flow.get("summary"), LIMITS["summary"], required=True)
    kind = flow.get("kind")
    if kind not in FLOW_KINDS:
        p.errors.append(f"kind: must be one of {', '.join(FLOW_KINDS)}")
    commit = flow.get("commit")
    if not isinstance(commit, str) or not HEX40.match(commit):
        p.errors.append("commit: must be the 40-character commit the flow was written against (git rev-parse HEAD)")
        commit = ""
    current = bool(ctx and commit and commit in ctx.current_commits())
    actors = flow.get("actors")
    actor_ok: set[str] = set()
    if not isinstance(actors, list) or not actors:
        p.errors.append("actors: must be a non-empty list of node ids (see _todo.json for the allowed ones)")
    else:
        for i, a in enumerate(actors):
            _check_actor(p, f"actors[{i}]", a, nodes, actor_ok)
    for k in ("unknowns",):
        if k in flow:
            notes._text_list(p, k, flow[k], LIMITS["list_n"], LIMITS["list_item"])
    for i, c in enumerate(flow.get("doc_conflicts") or []):
        if not isinstance(c, dict) or not isinstance(c.get("chapter"), str) or not isinstance(c.get("note"), str):
            p.errors.append(f"doc_conflicts[{i}]: must be {{\"chapter\": \"doc-x#heading-id\", \"note\": \"...\"}}")
        elif set(c) - CONFLICT_KEYS:
            p.warnings.append(f"doc_conflicts[{i}]: unknown key(s) {', '.join(sorted(set(c) - CONFLICT_KEYS))} (ignored)")
    if not isinstance(flow.get("doc_conflicts", []), list):
        p.errors.append("doc_conflicts: must be a list")

    steps, states, transitions = flow.get("steps"), flow.get("states"), flow.get("transitions")
    ids: dict[str, str] = {}                        # item id -> "step" | "transition"
    if kind == "lifecycle":
        if steps:
            p.warnings.append("steps: a lifecycle uses states and transitions; steps are ignored")
        _validate_lifecycle(p, states, transitions, ctx, nodes, commit, current, actor_ok, ids)
    elif kind in FLOW_KINDS:
        if states or transitions:
            p.warnings.append("states / transitions: only a lifecycle uses them (ignored)")
        _validate_steps(p, steps, ctx, nodes, commit, current, actor_ok, ids, flow_ids)
    for x in notes._walk_strings(flow):
        for rx in notes.SECRET_RES:
            if rx.search(x):
                p.errors.append("a text field looks like a secret (key, token or password); remove it")
                return p
    if prev and not p.errors:
        _stable_ids(p, flow, prev)
    return p


def _check_actor(p: Problems, where: str, a, nodes: NodeIndex | None, ok: set) -> None:
    if not isinstance(a, str) or not a:
        p.errors.append(f"{where}: must be a node id")
        return
    if nodes is None:
        ok.add(a)
        return
    nid, how = nodes.resolve(a)
    if nid is None:
        p.errors.append(f"{where}: {a!r} {how}. Use one of the ids in _todo.json (\"actors\")")
    else:
        ok.add(a)
        if how not in ("id", "listed folder"):
            p.warnings.append(f"{where}: {a!r} is written as a {how}; the real node id is {nid!r} (it is rewritten in the model)")


def _validate_steps(p, steps, ctx, nodes, commit, current, actor_ok, ids, flow_ids) -> None:
    if not isinstance(steps, list) or not steps:
        p.errors.append("steps: must be a non-empty list")
        return
    if len(steps) > LIMITS["steps"]:
        p.errors.append(f"steps: {len(steps)} steps (limit {LIMITS['steps']}); split the flow and point to the rest with \"subflow\"")
    for i, s in enumerate(steps):
        w = f"steps[{i}]"
        if not isinstance(s, dict):
            p.errors.append(f"{w}: must be an object")
            continue
        sid = s.get("id")
        w = f"steps[{i}] ({sid})" if isinstance(sid, str) else w
        extra = sorted(set(s) - STEP_KEYS)
        if extra:
            p.warnings.append(f"{w}: unknown key(s) {', '.join(extra)} (ignored)")
        if not isinstance(sid, str) or not STEP_ID.match(sid):
            p.errors.append(f"{w}.id: must look like s01, s02, ... in execution order")
        elif sid in ids:
            p.errors.append(f"{w}.id: duplicate id")
        else:
            ids[sid] = "step"
        notes._text(p, f"{w}.title", s.get("title"), LIMITS["title"], required=True)
        notes._text(p, f"{w}.text", s.get("text"), LIMITS["text"], required=True)
        if s.get("kind") not in STEP_KINDS:
            p.errors.append(f"{w}.kind: must be one of {', '.join(STEP_KINDS)}")
        a = s.get("actor")
        if not isinstance(a, str) or not a:
            p.errors.append(f"{w}.actor: must be a node id")
        elif nodes is not None:
            _check_actor(p, f"{w}.actor", a, nodes, set())
        _gate(p, w, s.get("gate"), s.get("kind"))
        if s.get("gate") and s.get("kind") != "gate":
            p.warnings.append(f"{w}: has a gate object but kind is {s.get('kind')!r}; use kind \"gate\" so it is drawn amber")
        if s.get("confidence") not in CONFIDENCE:
            p.errors.append(f"{w}.confidence: must be one of {', '.join(CONFIDENCE)}")
        if "unknowns" in s:
            notes._text_list(p, f"{w}.unknowns", s["unknowns"], LIMITS["list_n"], LIMITS["list_item"])
        if s.get("subflow") is not None:
            if not isinstance(s["subflow"], str) or not SLUG.match(s["subflow"]):
                p.errors.append(f"{w}.subflow: must be a flow id")
            elif flow_ids is not None and s["subflow"] not in flow_ids:
                p.warnings.append(f"{w}.subflow: {s['subflow']!r} is not a flow of {REGISTRY_FILE}")
        _evidence_list(p, w, s.get("evidence"), ctx, commit, current)
    for i, s in enumerate(steps):
        if isinstance(s, dict):
            nxt = s.get("next", [])
            if not isinstance(nxt, list) or not all(isinstance(x, str) for x in nxt):
                p.errors.append(f"steps[{i}].next: must be a list of step ids (empty for the last step)")
                continue
            for x in nxt:
                if x not in ids:
                    p.errors.append(f"steps[{i}].next: {x!r} is not a step of this flow")
                elif x == s.get("id"):
                    p.errors.append(f"steps[{i}].next: a step cannot lead to itself")


def _validate_lifecycle(p, states, transitions, ctx, nodes, commit, current, actor_ok, ids) -> None:
    sids: set[str] = set()
    if not isinstance(states, list) or not states:
        p.errors.append("states: a lifecycle needs a non-empty list of {id, label, terminal?}")
        states = []
    for i, s in enumerate(states):
        w = f"states[{i}]"
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not SLUG.match(s["id"]):
            p.errors.append(f"{w}: must be {{\"id\": \"slug\", \"label\": \"...\"}}")
            continue
        if set(s) - STATE_KEYS:
            p.warnings.append(f"{w}: unknown key(s) {', '.join(sorted(set(s) - STATE_KEYS))} (ignored)")
        if s["id"] in sids:
            p.errors.append(f"{w}.id: duplicate state {s['id']!r}")
        sids.add(s["id"])
        notes._text(p, f"{w}.label", s.get("label"), LIMITS["label"], required=True)
        if "terminal" in s and not isinstance(s["terminal"], bool):
            p.errors.append(f"{w}.terminal: must be true or false")
    if not isinstance(transitions, list) or not transitions:
        p.errors.append("transitions: a lifecycle needs a non-empty list of transitions")
        return
    if len(transitions) > LIMITS["steps"]:
        p.errors.append(f"transitions: {len(transitions)} (limit {LIMITS['steps']})")
    for i, t in enumerate(transitions):
        w = f"transitions[{i}]"
        if not isinstance(t, dict):
            p.errors.append(f"{w}: must be an object")
            continue
        tid = t.get("id")
        w = f"transitions[{i}] ({tid})" if isinstance(tid, str) else w
        if set(t) - TRANSITION_KEYS:
            p.warnings.append(f"{w}: unknown key(s) {', '.join(sorted(set(t) - TRANSITION_KEYS))} (ignored)")
        if not isinstance(tid, str) or not TRANSITION_ID.match(tid):
            p.errors.append(f"{w}.id: must look like t01, t02, ...")
        elif tid in ids:
            p.errors.append(f"{w}.id: duplicate id")
        else:
            ids[tid] = "transition"
        for k in ("from", "to"):
            if t.get(k) not in sids:
                p.errors.append(f"{w}.{k}: {t.get(k)!r} is not a state of this flow")
        notes._text(p, f"{w}.trigger", t.get("trigger"), LIMITS["trigger"], required=True)
        notes._text(p, f"{w}.text", t.get("text"), LIMITS["text"], required=True)
        if t.get("confidence") is not None and t["confidence"] not in CONFIDENCE:
            p.errors.append(f"{w}.confidence: must be one of {', '.join(CONFIDENCE)}")
        if t.get("actor") is not None:
            _check_actor(p, f"{w}.actor", t["actor"], nodes, set())
        if t.get("gate") is not None:
            _gate(p, w, t["gate"], None)
        if "unknowns" in t:
            notes._text_list(p, f"{w}.unknowns", t["unknowns"], LIMITS["list_n"], LIMITS["list_item"])
        _evidence_list(p, w, t.get("evidence"), ctx, commit, current)


def items_of(flow: dict) -> list[tuple[str, dict]]:
    """[(kind, item)] of everything that carries evidence: steps, or the transitions of a lifecycle."""
    if flow.get("kind") == "lifecycle":
        return [("transition", t) for t in flow.get("transitions") or [] if isinstance(t, dict)]
    return [("step", s) for s in flow.get("steps") or [] if isinstance(s, dict)]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _num(i: str) -> int:
    m = re.search(r"\d+", i or "")
    return int(m.group()) if m else 0


def _cites(item: dict) -> set[tuple]:
    return {(e.get("path"), e.get("qual")) for e in item.get("evidence") or [] if isinstance(e, dict)}


def _stable_ids(p: Problems, flow: dict, prev: dict) -> None:
    """Step ids are never renumbered or reused: compare with the copy that was ingested last time."""
    old = {i["id"]: i for _, i in items_of(prev) if isinstance(i.get("id"), str)}
    new = {i["id"]: i for _, i in items_of(flow) if isinstance(i.get("id"), str)}
    label = lambda i: i.get("title") or i.get("trigger") or ""
    for nid, item in sorted(new.items()):
        if nid in old:
            o = old[nid]
            same_title = _norm(label(o)) == _norm(label(item))
            if not same_title and not (_cites(o) & _cites(item)):
                p.errors.append(f"{nid}: the id was used for \"{label(o)}\" and now means \"{label(item)}\" (different title and different code). "
                                "Never reuse an id: give this step the next free one")
        else:
            for oid, o in old.items():
                if oid not in new and (_norm(label(o)) == _norm(label(item)) or (_cites(o) and _cites(o) == _cites(item))):
                    p.errors.append(f"{nid}: looks like {oid} (\"{label(o)}\") renumbered. Keep the old id")
                    break
            top = max((_num(i) for i in old), default=0)
            if _num(nid) < top:
                p.warnings.append(f"{nid}: new steps take the next free id (after s{top:02d}), not a gap")


# ----------------------------------------------------------------------------- flows: freshness
def _blob_unchanged(path: str, flow_commit: str, ctx: Ctx):
    """True / False / None(unknown): is the file the same at the flow's commit as at the census commit?"""
    if flow_commit and flow_commit == ctx.commit:
        return True
    if ctx.blobs is None:
        return None
    old = ctx.blobs_at(flow_commit)
    if old is None:
        return None
    a, b = old.get(path), ctx.blobs.get(path)
    if a is None or b is None:
        return None
    return a == b


def judge_evidence(e: dict, flow_commit: str, ctx: Ctx) -> tuple[str, str | None]:
    """(status, hash to store when the evidence had none): fresh | stale | broken | unverified."""
    path, qual = e.get("path"), e.get("qual")
    if path not in ctx.files:
        return "broken", None
    if qual is None:
        same = _blob_unchanged(path, flow_commit, ctx)
        return ("fresh" if same else "stale" if same is False else "unverified"), None
    cs = ctx.symbols.get(path, {}).get(qual)
    if cs is None:
        return "broken", None
    ch, h = cs[0].get("hash"), e.get("hash")
    if h and ch:
        return ("fresh" if h == ch else "stale"), None
    same = _blob_unchanged(path, flow_commit, ctx)
    if same:
        return "fresh", ch                          # the file is unchanged since the flow: the census hash is the hash it had
    return ("stale" if same is False else "unverified"), None


def worst(statuses) -> str:
    sts = list(statuses)
    return max(sts, key=STATUS_ORDER.index) if sts else "unverified"


def repair_flow(flow: dict, ctx: Ctx) -> dict:
    """A copy of the flow with every null evidence hash filled from the census where that is sound."""
    f = copy.deepcopy(flow)
    for _, item in items_of(f):
        for e in item.get("evidence") or []:
            if isinstance(e, dict) and not e.get("hash"):
                _, fill = judge_evidence(e, f.get("commit", ""), ctx)
                e["hash"] = fill if fill else None
    return f


def normalise_actors(flow: dict, nodes: NodeIndex) -> dict:
    """A copy with every actor rewritten to its real node id (aliases and folders resolved); an unresolvable actor is kept as it is."""
    f = copy.deepcopy(flow)
    f["actors"] = sorted({nodes.resolve(a)[0] or a for a in f.get("actors") or [] if isinstance(a, str)})
    for _, item in items_of(f):
        if isinstance(item.get("actor"), str):
            item["actor"] = nodes.resolve(item["actor"])[0] or item["actor"]
    return f


def stage_check(flow: dict, extractions: list[dict], reg_flow: dict | None) -> dict:
    """Compare the stage names the code registers with the steps of the flow. {"checked": [...], "missing": [...], "unavailable": [...]}"""
    out = {"checked": [], "missing": [], "unavailable": []}
    if not reg_flow:
        return out
    by_id = {x["id"]: x for x in extractions}
    hay = _norm(" ".join(str(x) for _, it in items_of(flow) for x in (
        it.get("id"), it.get("title"), it.get("text"), it.get("trigger"), it.get("actor"),
        *[f"{e.get('path')} {e.get('qual')}" for e in it.get("evidence") or [] if isinstance(e, dict)])))
    for spec in reg_flow.get("extractors", []):
        if not spec.get("cross_check"):
            continue
        res = by_id.get(spec["id"])
        if not res or not res.get("found"):
            out["unavailable"].append({"id": spec["id"], "reason": (res or {}).get("reason") or "not run"})
            continue
        out["checked"].append(spec["id"])
        for name in arch_extract.stage_names(res):
            if _norm(name) not in hay:
                out["missing"].append(name)
    out["missing"] = sorted(set(out["missing"]))
    return out


def evaluate_flow(flow: dict, ctx: Ctx, extractions: list[dict] | None = None, reg_flow: dict | None = None) -> dict:
    """The flow plus its freshness: every item and citation gets a status; the flow gets the worst, a count per status, and its stage check."""
    f = copy.deepcopy(flow)
    counts = collections.Counter()
    for _, item in items_of(f):
        sts = []
        for e in item.get("evidence") or []:
            if isinstance(e, dict):
                e["status"], _ = judge_evidence(e, f.get("commit", ""), ctx)
                sts.append(e["status"])
        item["status"] = worst(sts)
        counts[item["status"]] += 1
    f["status"] = worst(i["status"] for _, i in items_of(f))
    f["counts"] = {k: counts[k] for k in STATUS_ORDER if counts[k]}
    f["stage_check"] = stage_check(f, extractions or [], reg_flow)
    return f


# ----------------------------------------------------------------------------- collecting flows
def collect_flows(root: Path, minime, ctx: Ctx, nodes: NodeIndex, flow_ids):
    """Merge data/arch/flows with MiniMe's atlas-arch folder (MiniMe wins). Returns (flows {id: flow}, previous {id: committed copy}, problems {label: Problems})."""
    root = Path(root)
    committed, bad = notes.read_notes_dir(root / FLOWS_DIR)
    problems: dict[str, Problems] = {f"{FLOWS_DIR}/{n}": pr for n, pr in bad.items()}
    previous: dict[str, dict] = {}
    for name, flow in committed.items():
        pr = validate_flow(flow, name, ctx, nodes, flow_ids)
        if pr.errors or pr.warnings:
            problems[f"{FLOWS_DIR}/{name}"] = pr
        if not pr.errors:
            previous[flow["flow"]] = flow
    merged = dict(previous)
    src, src_bad = notes.read_notes_dir(Path(minime) / ARCH_SUBDIR) if minime else ({}, {})
    problems.update(src_bad)
    for name, flow in src.items():
        prev = previous.get(flow.get("flow")) if isinstance(flow, dict) else None
        pr = validate_flow(flow, name, ctx, nodes, flow_ids, prev)
        if pr.errors or pr.warnings:
            problems[name] = pr
        if not pr.errors:
            merged[flow["flow"]] = flow
    return merged, previous, problems


# ----------------------------------------------------------------------------- model, views, index
def load_inputs(root: Path, census: dict | None = None) -> dict:
    root = Path(root)
    out = {k: load_json(root / rel, None) for k, rel in INPUTS.items()}
    census = census if census is not None else load_json(root / notes.CENSUS_FILE, {}) or {}
    out["census_extra"] = {"env_usage": census.get("env_usage") or {}, "table_refs": census.get("table_refs") or {}}
    return out


def gather_extractions(ctx: Ctx, reg: dict, previous: list[dict] | None) -> list[dict]:
    """Run the extractors of the registry against MiniMe's git. Without MiniMe, keep what the last build recorded."""
    specs = list(reg["extractors"]) + [dict(x, flow=f["id"]) for f in reg["flows"] for x in f.get("extractors", [])]
    if not ctx.minime:
        return previous or []
    rev = ctx.commit if ctx.commit and not notes.git(ctx.minime, "cat-file", "-e", f"{ctx.commit}^{{commit}}").returncode else "HEAD"
    return sorted(arch_extract.extract_all(ctx.minime, rev, specs), key=lambda r: r["id"])


def view_shard(view: dict, derived: dict, model: dict, flows: dict, status: str) -> dict:
    """One small file per view: what a section of the System page needs to draw it."""
    pins = model["layout"]["pins"]
    out = {"schema": SCHEMA, "commit": derived["commit"], "id": view["id"], "title": view.get("title", view["id"]), "type": view["type"],
           "source": view["source"], "flow": view.get("flow"), "replaces": view.get("replaces"), "status": status}
    node_by = {n["id"]: n for n in derived["nodes"]}
    if view["type"] == "catalog":
        out["catalogue"] = derived["catalogues"]["routes"]
        out["nodes"] = sorted({g["node"] for g in out["catalogue"] if g.get("node")})
        return out
    kinds = view.get("edge_kinds")
    if view["source"] == "flow" and view.get("flow") in flows:
        fl = flows[view["flow"]]
        ids = sorted(set(fl.get("actors") or []) | {i.get("actor") for _, i in items_of(fl) if i.get("actor")})
        out["flow_data"] = fl
    else:
        ids = sorted(node_by)                                       # a derived view, or a flow not written yet: the whole structure
        out["flow_data"] = None
    ids = [i for i in ids if i in node_by]
    out["nodes"] = [node_by[i] for i in ids]
    idset = set(ids)
    out["edges"] = [e for e in derived["edges"] if e["from"] in idset and e["to"] in idset and (not kinds or e["kind"] in kinds)]
    out["pins"] = {i: pins[i] for i in ids if i in pins}
    return out


def build_outputs(root: Path, ctx: Ctx, flows: dict[str, dict], previous_derived: dict | None = None, topo=None, layout=None,
                  reg=None, inputs=None, extractions=None) -> dict[str, str]:
    """{repo-relative path: text} for derived.json, model.json, the view shards and data/index/arch.json. `flows` are the (repaired) flows to publish. Pure."""
    root = Path(root)
    topo = topo if topo is not None else (load_json(root / TOPOLOGY_FILE, {}) or {})
    layout = layout if layout is not None else (load_json(root / LAYOUT_FILE, {}) or {})
    reg = reg if reg is not None else load_registry(root)
    inputs = inputs if inputs is not None else load_inputs(root)
    if extractions is None:
        extractions = gather_extractions(ctx, reg, (previous_derived or {}).get("extractions"))
    derived, alias = derive(ctx, topo, layout, inputs, extractions)
    nodes = NodeIndex(derived["nodes"])
    reg_by = {f["id"]: f for f in reg["flows"]}
    evaluated = {fid: evaluate_flow(normalise_actors(f, nodes), ctx, extractions, reg_by.get(fid)) for fid, f in sorted(flows.items())}
    model_layout = build_layout(topo, layout, derived["nodes"], alias)
    views = []
    for v in reg["views"]:
        fid = v.get("flow") if v["source"] == "flow" else None
        status = (evaluated[fid]["status"] if fid in evaluated else "missing") if fid else "derived"
        views.append({k: v[k] for k in ("id", "title", "type", "source", "flow", "replaces", "edge_kinds") if k in v} | {"status": status})
    model = {"schema": SCHEMA, "commit": ctx.commit, "nodes": derived["nodes"], "edges": derived["edges"], "layout": model_layout,
             "flows": evaluated, "views": views}
    out: dict[str, str] = {DERIVED_FILE: dumps(derived), MODEL_FILE: dumps(model)}
    for v, meta in zip(reg["views"], views):
        out[f"{VIEWS_DIR}/{v['id']}.json"] = dumps(view_shard(v, derived, model, evaluated, meta["status"]))
    out[INDEX_FILE] = dumps(build_index(ctx, reg, evaluated, views, extractions, derived))
    return out


def build_index(ctx: Ctx, reg: dict, evaluated: dict, views: list[dict], extractions: list[dict], derived: dict) -> dict:
    flows = {}
    for f in reg["flows"]:
        ev = evaluated.get(f["id"])
        flows[f["id"]] = {"title": f.get("title") or f["id"], "kind": f.get("kind"), "views": f.get("views", []), "registered": True,
                          "status": ev["status"] if ev else "missing", "counts": ev["counts"] if ev else {},
                          "items": len(items_of(ev)) if ev else 0, "commit": ev["commit"] if ev else None,
                          "incomplete": ev["stage_check"]["missing"] if ev else [],
                          "stage_unavailable": [u["id"] for u in ev["stage_check"]["unavailable"]] if ev else []}
    for fid, ev in evaluated.items():
        if fid not in flows:
            flows[fid] = {"title": ev.get("title") or fid, "kind": ev.get("kind"), "views": [], "registered": False, "status": ev["status"],
                          "counts": ev["counts"], "items": len(items_of(ev)), "commit": ev["commit"], "incomplete": [], "stage_unavailable": []}
    tot = collections.Counter(v["status"] for v in flows.values())
    return {"schema": SCHEMA, "commit": ctx.commit,
            "totals": {"flows": len(flows), "written": len(flows) - tot["missing"], **{k: tot[k] for k in (*STATUS_ORDER, "missing")}},
            "flows": {k: flows[k] for k in sorted(flows)},
            "views": {v["id"]: {"title": v.get("title"), "type": v["type"], "flow": v.get("flow"), "status": v["status"]} for v in views},
            "extractors": {x["id"]: {"found": bool(x["found"]), "count": len(arch_extract.stage_names(x)), "reason": x["reason"]} for x in extractions},
            "nodes": len(derived["nodes"]), "edges": len(derived["edges"])}


# ----------------------------------------------------------------------------- writing and checking
def _write_or_check(root: Path, wanted: dict[str, str], check: bool, log, prune_dirs=(), keep=()) -> int:
    root = Path(root)
    changed = [rel for rel, text in wanted.items() if not (root / rel).exists() or read_lf(root / rel) != text]
    stale = []
    for d in prune_dirs:
        folder = root / d
        if folder.is_dir():
            stale += [f for f in sorted(folder.glob("*.json")) if f"{d}/{f.name}" not in wanted and f.name not in keep]
    if check:
        for rel in changed:
            log(f"architecture data is out of date: {rel}")
        for f in stale:
            log(f"architecture data is out of date: {f.relative_to(root).as_posix()} should be removed")
        if changed or stale:
            log("run: python scripts/arch.py ingest --minime <MiniMe>   (or: python scripts/arch.py build)")
            return 1
        log("architecture data is current")
        return 0
    for rel in changed:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(wanted[rel].encode("utf-8"))             # always LF; git/autocrlf is free to convert
    for f in stale:
        f.unlink()
    log(f"architecture: {len(changed)} file(s) updated" + (f", {len(stale)} removed" if stale else ""))
    return 0


def prepare(root: Path, minime, with_minime_flows: bool, log=print):
    """Load everything `ingest`, `build`, `status` and `todo` share. Returns a dict of the loaded pieces."""
    root = Path(root)
    ctx = build_ctx(root, minime)
    for w in ctx.warnings:
        log(f"warning: {w}")
    reg = load_registry(root)
    topo = load_json(root / TOPOLOGY_FILE, {}) or {}
    layout = load_json(root / LAYOUT_FILE, {}) or {}
    for prob in registry_problems(reg, root) + layout_problems(layout):
        log(f"warning: {prob}")
    previous_derived = load_json(root / DERIVED_FILE, None)
    inputs = load_inputs(root)
    extractions = gather_extractions(ctx, reg, (previous_derived or {}).get("extractions"))
    derived, _ = derive(ctx, topo, layout, inputs, extractions)
    nodes = NodeIndex(derived["nodes"])
    flow_ids = {f["id"] for f in reg["flows"]}
    flows, previous, problems = collect_flows(root, minime if with_minime_flows else None, ctx, nodes, flow_ids)
    return {"extractions": extractions, "root": root, "ctx": ctx, "reg": reg, "topo": topo, "layout": layout, "inputs": inputs, "derived": derived, "nodes": nodes,
            "flows": flows, "previous": previous, "problems": problems, "previous_derived": previous_derived}


def report_problems(problems: dict, log=print) -> dict:
    errors = {n: pr for n, pr in problems.items() if pr.errors}
    for name, pr in sorted(problems.items()):
        for w in pr.warnings:
            log(f"warning: {name}: {w}")
    for name, pr in sorted(errors.items()):
        for e in pr.errors:
            log(f"error: {name}: {e}")
    return errors


def ingest(root: Path, minime=None, check: bool = False, skip_invalid: bool = False, log=print) -> int:
    """Validate, copy the flows into data/arch/flows with their evidence hashes filled, then rebuild everything. Returns an exit code."""
    P = prepare(root, minime, True, log)
    root, ctx = P["root"], P["ctx"]
    if minime and not (Path(minime) / ARCH_SUBDIR).is_dir():
        log(f"no {ARCH_SUBDIR} folder in {minime} (no flow written there yet, or another machine): using data/arch/flows as it is")
    errors = report_problems(P["problems"], log)
    if errors:
        if not skip_invalid:
            log(f"\n{len(errors)} flow file(s) are malformed, nothing was ingested. Fix or delete them (they are in "
                f"{Path(minime) / ARCH_SUBDIR if minime else root / FLOWS_DIR}), or use --skip-invalid to ingest the rest.")
            return 1
        log(f"{len(errors)} malformed flow file(s) skipped (--skip-invalid)")
    repaired = {fid: repair_flow(f, ctx) for fid, f in sorted(P["flows"].items())}
    wanted = build_outputs(root, ctx, repaired, P["previous_derived"], P["topo"], P["layout"], P["reg"], P["inputs"], P["extractions"])
    for fid, f in repaired.items():
        wanted[f"{FLOWS_DIR}/{fid}.json"] = dumps(f)
    for fid, ev in sorted(json.loads(wanted[MODEL_FILE])["flows"].items()):
        sc = ev["stage_check"]
        if sc["missing"]:
            log(f"warning: {fid}: no step for {len(sc['missing'])} stage(s) the code registers: {', '.join(sc['missing'][:8])}{' ...' if len(sc['missing']) > 8 else ''}")
        for u in sc["unavailable"]:
            log(f"note: {fid}: stage list {u['id']} not found in the code ({u['reason']}); the flow stands on Copilot's trace alone")
    rc = _write_or_check(root, wanted, check, log, prune_dirs=(VIEWS_DIR,))
    if not check:
        log(f"architecture: {len(repaired)} flow(s) ingested")
    return rc


def build(root: Path, minime=None, check: bool = False, log=print) -> int:
    """Rebuild derived.json, model.json, the view shards and data/index/arch.json from the committed flows."""
    P = prepare(root, minime, False, log)
    errors = report_problems({k: v for k, v in P["problems"].items() if v.errors}, log)
    if errors:
        log("the committed flows are malformed; nothing was built")
        return 1
    flows = {fid: f for fid, f in sorted(P["flows"].items())}
    wanted = build_outputs(P["root"], P["ctx"], flows, P["previous_derived"], P["topo"], P["layout"], P["reg"], P["inputs"], P["extractions"])
    return _write_or_check(P["root"], wanted, check, log, prune_dirs=(VIEWS_DIR,))


# ----------------------------------------------------------------------------- todo and the instructions for Copilot
SCHEMA_MD = """# Atlas architecture flows: what to write

You write one JSON file per flow into this folder (`graphify-out/atlas-arch/`). The flows to write or refresh are in
`_todo.json` (same folder). The Atlas draws them as diagrams (a pipeline, a sequence, a lifecycle, an approval path) and
links every step to the real code, so they must be **true**. A step is only worth writing if you can point to code that does it.

## File name
`<flow id>.json`, for example `task-pipeline.json`. The id is in `_todo.json`.

## The file (schema version 1)
```json
{
  "schema": 1,
  "flow": "task-pipeline",
  "title": "Task pipeline",
  "kind": "pipeline",
  "summary": "<= %(summary)d characters: what this flow is",
  "commit": "<40-character sha from `git rev-parse HEAD`>",
  "actors": ["backend/api", "backend/eo"],
  "steps": [
    {
      "id": "s01",
      "title": "<= %(title)d characters",
      "actor": "backend/api",
      "kind": "control",
      "text": "<= %(text)d characters, plain English: what happens here",
      "gate": null,
      "next": ["s02"],
      "evidence": [{"path": "backend/api/tasks.py", "qual": "create_task", "lines": [40, 88], "hash": null}],
      "confidence": "high",
      "unknowns": []
    }
  ],
  "doc_conflicts": [{"chapter": "doc-minime-feature-guide#orchestrator", "note": "Book says 25 stages, the code registers 27"}],
  "unknowns": []
}
```

## Rules
* **Evidence is mandatory.** Every step (or transition) has at least one `evidence` entry: a real `path` and the `qual` of a
  function or class that does what the step says, plus `lines` as `[first, last]` (use `lines` with `qual: null` only for
  module-level code). Leave `hash` null; ingest fills it. If you cannot point to code, do **not** write the step: put the
  question in `unknowns`.
* **Follow the code, not the documents.** Order the steps by real execution order. If a chapter of the book disagrees with the
  code, follow the code and add an entry to `doc_conflicts` naming the chapter (and heading id if you know it).
* `actors` and every step's `actor` must be one of the ids listed under `actors` in `_todo.json` (real folders, or virtual
  nodes such as `store:postgres`). Never write free text.
* `kind` of a flow: `pipeline`, `sequence`, `lifecycle` or `gated`. `kind` of a step: `control` (ordinary logic), `data`
  (data is handed over or transformed), `store` (database, cache or file write), `external` (network or model-provider call),
  `gate` (an approval: also set `"gate": {"tier": "T3", "who": "user"}`, who is `user`, `daemon` or `policy`).
* `next` lists the ids of the steps that can follow (empty for the last one; two entries for a branch).
* **Stable ids.** Steps are `s01`, `s02`, ... in execution order. Once an id exists it is never renumbered or reused. A new step
  takes the next free id. When you refresh a flow, keep the order unless the code order really changed.
* **A lifecycle** has no `steps`. It has `"states": [{"id": "queued", "label": "Queued", "terminal": false}]` and
  `"transitions": [{"id": "t01", "from": "queued", "to": "running", "trigger": "<= %(trigger)d characters", "text": "...",
  "evidence": [...], "confidence": "high"}]`. Transition ids are `t01`, `t02`, ...
* At most %(steps)d steps per flow; split a bigger flow and point to the rest with `"subflow": "<flow id>"` on a step.
* `confidence` is `high`, `medium` or `low`; use `low` when unsure. Put anything you could not confirm in `unknowns`.
* Never include secrets, tokens, passwords or values from .env files.
* Do not modify any source file and do not commit.
"""


def schema_markdown() -> str:
    return SCHEMA_MD % LIMITS


def _seed_rows(ctx: Ctx, seeds: list) -> tuple[list[dict], list[str]]:
    rows, missing = [], []
    for s in seeds:
        path, _, qual = str(s).partition("::")
        rec = ctx.files.get(path)
        if rec is None:
            missing.append(str(s))
            continue
        tbl = ctx.symbols.get(path, {})
        picked = [(qual, tbl[qual])] if qual and qual in tbl else ([] if qual else sorted(tbl.items(), key=lambda kv: kv[1][0].get("start", 0))[:30])
        if qual and qual not in tbl:
            missing.append(str(s))
            continue
        syms = []
        for q, (sym, kind) in picked:
            calls = [c[1] for c in sym.get("calls") or [] if isinstance(c, list) and len(c) == 2 and c[1]][:12]
            syms.append({"qual": q, "kind": kind, "start": sym.get("start"), "end": sym.get("end"), "hash": sym.get("hash"),
                         "signature": notes.signature(sym, kind), "doc1": sym.get("doc1"), "calls": calls})
        rows.append({"path": path, "lines": rec.get("lines"), "module_doc": (rec.get("module_doc") or "")[:300] or None, "symbols": syms})
    return rows, missing


def build_todo(ctx: Ctx, reg: dict, flows: dict[str, dict], derived: dict, nodes_ix: NodeIndex, head: str = "", limit: int = 0) -> dict:
    """The flows that need Copilot: not written yet, or with steps whose evidence is stale or broken, or with a stage the code registers and no step."""
    extractions = derived["extractions"]
    by_ex = {x["id"]: x for x in extractions}
    actors = [{"id": n["id"], "label": n["label"], "kind": n["kind"], **({"folders": n["folders"]} if n.get("folders") else {}),
               **({"what": n["what"]} if n.get("what") else {})} for n in derived["nodes"] if n["kind"] != "group"]
    rows = []
    for f in reg["flows"]:
        raw = flows.get(f["id"])
        ev = evaluate_flow(normalise_actors(raw, nodes_ix), ctx, extractions, f) if raw else None
        work = [] if not ev else [(k, i) for k, i in items_of(ev) if i.get("status") in ("stale", "broken")]
        missing = ev["stage_check"]["missing"] if ev else []
        if ev and not work and not missing:
            continue
        seeds, gone = _seed_rows(ctx, f.get("seeds", []))
        rows.append({
            "id": f["id"], "title": f.get("title") or f["id"], "kind": f.get("kind"), "flow_file": f"{f['id']}.json",
            "reason": "new" if not ev else ("changed" if work else "incomplete"), "views": f.get("views", []), "commit": ctx.commit,
            "seeds": seeds, "seeds_not_in_census": gone,
            "stages_in_code": {x["id"]: arch_extract.stage_names(by_ex[x["id"]]) for x in f.get("extractors", []) if x["id"] in by_ex and by_ex[x["id"]].get("found")},
            "steps_needing_work": [{"id": i["id"], "why": i["status"], "title": i.get("title") or i.get("trigger"),
                                    "evidence": [{k: e.get(k) for k in ("path", "qual", "lines", "status")} for e in i.get("evidence") or []]} for _, i in work],
            "stages_without_a_step": missing,
        })
    order = {"new": 0, "changed": 1, "incomplete": 2}
    pos = {f["id"]: n for n, f in enumerate(reg["flows"])}
    rows.sort(key=lambda r: (order[r["reason"]], -len(r["steps_needing_work"]), pos[r["id"]]))
    if limit:
        rows = rows[:limit]
    return {"schema": SCHEMA, "commit": ctx.commit, "head": head, "actors": actors, "flows": rows}


def format_status(index: dict, blobs_known: bool = True) -> str:
    t = index["totals"]
    out = [f"Architecture flows at census {index.get('commit', '')[:7] or '?'}   ({index['nodes']} nodes, {index['edges']} edges)"
           + ("" if blobs_known else "   (no MiniMe checkout: flows older than the census cannot be compared, so they show as unverified)"),
           f"{t['written']} of {t['flows']} flow(s) written: {t['fresh']} fresh, {t['stale']} stale, {t['broken']} broken, "
           f"{t['unverified']} unverified, {t['missing']} missing", "",
           "flow                  kind       status      items  fresh/stale/broken/unverified   commit   stages without a step"]
    for fid, f in index["flows"].items():
        c = f["counts"]
        mix = f"{c.get('fresh', 0)}/{c.get('stale', 0)}/{c.get('broken', 0)}/{c.get('unverified', 0)}"
        out.append(f"{fid:<21} {f['kind'] or '-':<10} {f['status']:<11} {f['items']:>5}  {mix:<30}  {(f['commit'] or '-')[:7]:<8} {', '.join(f['incomplete'][:5]) or '-'}")
    out += ["", "stage lists read from the code: " + (", ".join(f"{k} ({'%d names' % v['count'] if v['found'] else 'not found: ' + str(v['reason'])})"
                                                                  for k, v in index["extractors"].items()) or "none (not read without a MiniMe checkout, or none configured)")]
    return "\n".join(out)


def default_minime(arg: str | None) -> Path | None:
    p = Path(arg) if arg else ROOT.parent / "MiniMe"
    return p if p.is_dir() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_minime(sp):
        sp.add_argument("--minime", default=None, help="the MiniMe checkout (default: ../MiniMe when it exists)")

    sp = sub.add_parser("status", help="one line per flow")
    add_minime(sp)
    sp = sub.add_parser("todo", help="write _SCHEMA.md and _todo.json for Copilot into MiniMe's atlas-arch folder")
    add_minime(sp)
    sp.add_argument("--limit", type=int, default=0, help="list at most this many flows (default: all; the prompt takes two at a time)")
    sp = sub.add_parser("validate", help="check flow files against the schema and the census")
    add_minime(sp)
    sp.add_argument("--dir", default=None, help="a folder of flows (default: data/arch/flows, or MiniMe's atlas-arch with --minime)")
    sp = sub.add_parser("ingest", help="validate, copy into data/arch/flows, fill evidence hashes, then build")
    add_minime(sp)
    sp.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything under data/arch or data/index/arch.json is out of date")
    sp.add_argument("--skip-invalid", action="store_true", help="ingest the valid flows even if some are malformed")
    sp = sub.add_parser("build", help="rebuild derived.json, model.json, the view shards and data/index/arch.json from the committed flows")
    add_minime(sp)
    sp.add_argument("--check", action="store_true", help="change nothing; exit 1 if the files are out of date")
    args = ap.parse_args(argv)
    root = Path(args.root)
    minime = default_minime(args.minime)
    if args.minime and not minime:
        sys.exit(f"{args.minime} is not a folder. Use --minime PATH to the MiniMe checkout.")

    if args.cmd == "ingest":
        if not minime:
            print(f"warning: no MiniMe checkout at {args.minime or ROOT.parent / 'MiniMe'}; freshness of older flows is not judged and stage lists are kept as last built", file=sys.stderr)
        return ingest(root, minime, args.check, args.skip_invalid)
    if args.cmd == "build":
        return build(root, minime, args.check)

    if args.cmd == "validate":
        ctx = build_ctx(root, minime)
        reg = load_registry(root)
        derived, _ = derive(ctx, load_json(root / TOPOLOGY_FILE, {}) or {}, load_json(root / LAYOUT_FILE, {}) or {}, load_inputs(root), [])
        nodes = NodeIndex(derived["nodes"])
        d = Path(args.dir) if args.dir else (minime / ARCH_SUBDIR if args.minime else root / FLOWS_DIR)
        flows, bad = notes.read_notes_dir(d)
        ids = {f["id"] for f in reg["flows"]}
        results = {**bad, **{name: validate_flow(f, name, ctx, nodes, ids) for name, f in flows.items()}}
        n_err = n_warn = 0
        for name, pr in sorted(results.items()):
            for e in pr.errors:
                print(f"error: {name}: {e}")
            for w in pr.warnings:
                print(f"warning: {name}: {w}")
            n_err += len(pr.errors)
            n_warn += len(pr.warnings)
        for prob in registry_problems(reg, root) + layout_problems(load_json(root / LAYOUT_FILE, {}) or {}):
            print(f"error: {prob}")
            n_err += 1
        print(f"{len(results)} flow file(s) in {d}: {n_err} error(s), {n_warn} warning(s)")
        return 1 if n_err else 0

    use_source = args.cmd == "todo" or bool(args.minime)
    P = prepare(root, minime, use_source, lambda m: print(m, file=sys.stderr))
    for name, pr in sorted(P["problems"].items()):
        for e in pr.errors:
            print(f"warning: {name} is malformed ({e}); it is ignored", file=sys.stderr)
    if args.cmd == "status":
        flows = {fid: repair_flow(f, P["ctx"]) for fid, f in P["flows"].items()}
        wanted = build_outputs(root, P["ctx"], flows, P["previous_derived"], P["topo"], P["layout"], P["reg"], P["inputs"], P["extractions"])
        print(format_status(json.loads(wanted[INDEX_FILE]), P["ctx"].blobs is not None))
        return 0
    if args.cmd == "todo":
        if not minime:
            sys.exit("todo needs the MiniMe checkout: --minime PATH")
        if P["ctx"].blobs is None:
            sys.exit(f"{minime} is not a git checkout.")
        merged = {fid: repair_flow(f, P["ctx"]) for fid, f in P["flows"].items()}
        todo = build_todo(P["ctx"], P["reg"], merged, P["derived"], P["nodes"], P["ctx"].head, args.limit)
        out = minime / ARCH_SUBDIR
        out.mkdir(parents=True, exist_ok=True)
        (out / "_SCHEMA.md").write_bytes(schema_markdown().encode("utf-8"))
        (out / "_todo.json").write_bytes((json.dumps(todo, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        for f in todo["flows"]:                                       # Copilot refreshes a flow in place, so it must be in MiniMe's folder
            dest = out / f["flow_file"]
            if f["reason"] != "new" and not dest.exists() and f["id"] in merged:
                dest.write_bytes((json.dumps(merged[f["id"]], indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        if P["ctx"].head and P["ctx"].head != P["ctx"].commit:
            print(f"warning: MiniMe is at {P['ctx'].head[:7]} but the census is from {P['ctx'].commit[:7]}. Run scripts/update_all.py first so hashes match.", file=sys.stderr)
        print(f"{len(todo['flows'])} flow(s) need Copilot. Written to {out / '_todo.json'}")
        for f in todo["flows"]:
            extra = f" ({len(f['steps_needing_work'])} step(s) stale or broken)" if f["steps_needing_work"] else (
                f" ({len(f['stages_without_a_step'])} stage(s) without a step)" if f["stages_without_a_step"] else "")
            print(f"  {f['reason']:<10} {f['id']}{extra}")
        for f in todo["flows"]:
            for s in f["seeds_not_in_census"]:
                print(f"warning: {f['id']}: seed {s} is not in the census (fix content/arch-flows.json)", file=sys.stderr)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
