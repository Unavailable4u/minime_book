#!/usr/bin/env python3
"""
build_status.py -- data/index/status.json, the one small file the Coverage page and the top-bar status chip read (patch P22).

    python scripts/build_status.py            # rewrite data/index/status.json
    python scripts/build_status.py --check    # change nothing; exit 1 if it is out of date

It reads only what is committed in this repo (so CI and every contributor get the same bytes, with or without a MiniMe checkout):

    data/index/stats.json   census commit and date          data/index/vitals.json   graph commit and date
    data/index/notes.json   notes coverage and freshness    data/index/arch.json     architecture flow status
    data/index/book.json    when the chapters were built    data/census.json         files, symbols, churn
    data/graph/file-links.json   graph links per file (for the "annotate next" preview)
    content/notes-tiers.json     which files get a note (rules are the ones scripts/notes.py uses)

and writes (sorted keys, no timestamps; ages are worked out in the browser from the source dates below):

    sources   {census, graph, notes, arch, docs}: commit + date of everything the Atlas is built from
    notes     totals and per-tier coverage (copied from notes.json)
    folders   every folder: files, symbols (all of them: the universe audit marks are counted against) and its notes coverage
    flows     per architecture flow: status, step counts, commit (copied from arch.json)
    stale     files whose note is stale, with the symbols that changed (from notes.json)
    next      a PREVIEW of the next files to annotate. Tiers of files that already have a note are exact; for the others
              the "most-connected files" rule is judged from file-links.json (only each file's 12 strongest links), so a file
              near the cut-off can differ from what `notes.py todo` picks. `notes.py todo` writes the authoritative batch;
              the page says so.

Standard library only. notes.py is imported for its tier and symbol rules, so the preview cannot drift from them.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
OUT_REL = "data/index/status.json"
SCHEMA = 1
NEXT_LIMIT = 60          # files in the preview
STALE_LIMIT = 100        # files in the stale list


def load_notes_module():
    spec = importlib.util.spec_from_file_location("atlas_notes", Path(__file__).resolve().parent / "notes.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["atlas_notes"] = mod
    spec.loader.exec_module(mod)
    return mod


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        return default


def dumps(doc) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def read_lf(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


# ----------------------------------------------------------------------------- pieces (pure)
def sources_block(stats: dict, vitals: dict, notes: dict, arch: dict, book: dict) -> dict:
    graph = (vitals or {}).get("graph") or {}
    written = sorted({f.get("written", "") for f in (notes.get("files") or {}).values() if f.get("written")})
    flows = (arch or {}).get("flows") or {}
    flow_days = sorted({f.get("commit") for f in flows.values() if f.get("commit")})
    chapters = (book or {}).get("chapters") or []
    built = sorted(c.get("built", "") for c in chapters if c.get("built"))
    return {
        "census": {"commit": stats.get("commit") or "", "date": stats.get("generated") or ""},
        "graph": {"commit": graph.get("commit") or "", "date": graph.get("date") or ""},
        "notes": {"commit": notes.get("commit") or "", "date": written[-1] if written else ""},
        "arch": {"commit": (arch or {}).get("commit") or "", "flow_commits": flow_days},
        "docs": {"date": built[-1] if built else ""},
    }


def folder_table(census_files: list[dict], notes_folders: dict) -> dict:
    """Every folder with a file below it: files, symbols (functions + classes, all files, tests included) and notes coverage."""
    out: dict[str, dict] = {}
    for f in census_files:
        parts = f["path"].split("/")[:-1]
        n = len(f.get("functions") or []) + len(f.get("classes") or [])
        for k in range(1, len(parts) + 1):
            row = out.setdefault("/".join(parts[:k]), {"files": 0, "symbols": 0, "elig": 0, "noted": 0, "fresh": 0, "stale": 0})
            row["files"] += 1
            row["symbols"] += n
    for path, nf in (notes_folders or {}).items():
        row = out.get(path)
        if row is not None:
            row.update({"elig": nf.get("files", 0), "noted": nf.get("noted", 0), "fresh": nf.get("fresh", 0), "stale": nf.get("stale", 0)})
    return out


def flows_block(arch: dict) -> dict:
    out = {}
    for fid, f in sorted(((arch or {}).get("flows") or {}).items()):
        out[fid] = {"title": f.get("title", fid), "kind": f.get("kind", ""), "status": f.get("status", "missing"), "items": f.get("items", 0),
                    "counts": f.get("counts") or {}, "commit": f.get("commit"), "incomplete": f.get("incomplete") or [], "views": f.get("views") or []}
    return out


def flow_order(root: Path) -> list[str]:
    """The flows in the order content/arch-flows.json registers them (the order `arch.py todo` hands them to Copilot)."""
    reg = read_json(Path(root) / "content/arch-flows.json", {}) or {}
    flows = reg.get("flows")
    if isinstance(flows, dict):
        return list(flows)
    return [f["id"] for f in flows or [] if isinstance(f, dict) and f.get("id")]


def stale_list(notes: dict) -> list[dict]:
    rows = []
    for path, f in sorted((notes.get("files") or {}).items()):
        bad = f.get("bad") or []
        if f.get("status") not in (None, "fresh") or bad:
            rows.append({"path": path, "tier": f.get("tier"), "status": f.get("status"), "bad": bad[:20], "written": f.get("written", ""), "summary": f.get("summary", "")})
    rows.sort(key=lambda r: (r["tier"] or 9, r["path"]))
    return rows[:STALE_LIMIT]


def file_degrees(links_doc: dict | None) -> dict[str, int]:
    """Graph links per file from data/graph/file-links.json (each file keeps its 12 strongest neighbours: an approximation of the full degree)."""
    if not links_doc:
        return {}
    paths, rows = links_doc.get("paths") or [], links_doc.get("links") or []
    deg: collections.Counter = collections.Counter()
    for i, row in enumerate(rows):
        if i < len(paths):
            deg[paths[i]] += sum(w for _, w in row)
    return dict(deg)


def next_preview(nm, ctx, notes: dict, limit: int = NEXT_LIMIT) -> dict:
    """The next files that need a note (missing or stale), ordered like notes.py todo: tier, then graph links, then churn."""
    exact = {p: f.get("tier") for p, f in (notes.get("files") or {}).items() if f.get("tier")}
    rows, tier_counts = [], collections.Counter()
    for path, rec in ctx.files.items():
        tier = exact.get(path) or ctx.tiers.get(path, (0, ""))[0]
        if not 1 <= tier <= 3:
            continue
        info = (notes.get("files") or {}).get(path)
        if info and info.get("status") == "fresh" and not info.get("bad"):
            continue
        reason = "new" if not info else "changed"
        rows.append({
            "path": path, "tier": tier, "reason": reason, "links": ctx.degree.get(path, 0),
            "commits": (rec.get("git") or {}).get("commits", 0), "lines": rec.get("lines", 0),
            "symbols": len(nm.wanted_symbols(rec, tier, ctx.cfg)), "tier_exact": path in exact,
        })
        tier_counts[tier] += 1
    rows.sort(key=lambda r: (r["tier"], -r["links"], -r["commits"], r["path"]))
    return {
        "basis": "Preview. Tiers of files that already have a note are exact; the others are judged from the 12 strongest graph links of each file. "
                 "`python scripts/notes.py todo` writes the authoritative batch.",
        "needing": len(rows), "per_tier": {str(t): tier_counts[t] for t in (1, 2, 3)}, "files": rows[:limit],
    }


def build_status(root: Path = ROOT) -> dict:
    nm = load_notes_module()
    root = Path(root)
    stats = read_json(root / "data/index/stats.json", {}) or {}
    vitals = read_json(root / "data/index/vitals.json", {}) or {}
    notes = read_json(root / "data/index/notes.json", {}) or {}
    arch = read_json(root / "data/index/arch.json", {}) or {}
    book = read_json(root / "data/index/book.json", {}) or {}
    ctx = nm.build_ctx(root, None)
    ctx.degree = file_degrees(read_json(root / "data/graph/file-links.json"))
    ctx.hubs_source = "file-links"
    census = read_json(root / "data/census.json", {}) or {}
    routes = {r["file"] for r in census.get("routes", []) if isinstance(r, dict) and r.get("file")}
    ctx.tiers = nm.assign_tiers([ctx.files[p] for p in ctx.files], ctx.cfg, ctx.degree, routes)
    symbols = sum(len(f.get("functions") or []) + len(f.get("classes") or []) for f in ctx.files.values())
    return {
        "schema": SCHEMA,
        "sources": sources_block(stats, vitals, notes, arch, book),
        "totals": {"files": len(ctx.files), "symbols": symbols},
        "notes": {"totals": notes.get("totals") or {}, "tiers": notes.get("tiers") or {}, "blobs_known": bool(notes.get("blobs_known"))},
        "folders": folder_table(list(ctx.files.values()), notes.get("folders") or {}),
        "flows": flows_block(arch),
        "flow_order": flow_order(root),
        "flow_totals": (arch or {}).get("totals") or {},
        "stale": stale_list(notes),
        "next": next_preview(nm, ctx, notes),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if data/index/status.json is out of date")
    args = ap.parse_args(argv)
    root = Path(args.root)
    text = dumps(build_status(root))
    out = root / OUT_REL
    current = read_lf(out) if out.exists() else None
    if args.check:
        if current != text:
            print(f"{OUT_REL} is out of date. Run: python scripts/build_status.py")
            return 1
        print("status is current")
        return 0
    if current != text:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))        # always LF; git/autocrlf is free to convert
        print(f"wrote {OUT_REL}")
    else:
        print(f"{OUT_REL} already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())