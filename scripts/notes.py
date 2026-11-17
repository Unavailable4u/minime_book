#!/usr/bin/env python3
"""The Atlas notes pipeline (patch P11): AI-written explanations of the code, kept honest and incremental.

Standard library only. Output is deterministic (sorted keys, no timestamps), so `ingest --check` can compare
it byte-for-byte (line endings are normalised on read; files are always written with LF).

What a note is
  One JSON file per source file, written by Copilot (agent mode, inside the MiniMe checkout) into
  MiniMe/graphify-out/atlas-notes/<path with "/" replaced by "__">.json   (graphify-out/ is ignored by MiniMe's git,
  so this never dirties the checkout). `ingest` validates them and copies the good ones into data/notes/, which is
  what the site reads. The schema is written out for Copilot in _SCHEMA.md by `todo`; it comes from this file
  (SCHEMA_MD, LIMITS), so the validator and the instructions cannot disagree.

Freshness (two levels, both from git objects, never from the working tree)
  file    the note's "blob" against `git ls-tree -r <census commit>` in MiniMe:  fresh | stale | missing
  symbol  the note's symbol "hash" against the census v2 "hash" of the same "qual":  fresh | stale | broken
          (broken = the symbol no longer exists). A file is fresh only when its blob matches and none of its
          symbols is stale or broken.

Commands
  notes.py status   [--minime M] [--folders]         coverage by tier (and folder): files, notes, fresh / stale / missing
  notes.py tiers    [PATH ...] [--minime M]          which tier each file gets, and which rule decided it
  notes.py todo     [--tier N] [--limit N] [--max-symbols N] --minime M
                                                     write M/graphify-out/atlas-notes/_SCHEMA.md and _todo.json: the next
                                                     batch of files for Copilot (tiers 1..N, most connected first)
  notes.py validate [--dir D | --minime M]           check notes against the schema and the census (default: data/notes)
  notes.py ingest   --minime M [--check] [--skip-invalid] [--prune-orphans]
                                                     validate, copy into data/notes/, fill symbol hashes, write
                                                     data/index/notes.json (coverage and freshness, for the Explorer and Coverage page)

Rules that keep the notes cheap and trustworthy
  * Errors block `ingest` (malformed JSON, wrong types, a secret-looking string, a symbol that does not exist in the
    census although the note was written at the census commit). Warnings never block (unknown keys, over-long text,
    a symbol that vanished from newer code, a note for a deleted file).
  * `hash` may be null when Copilot writes a note. `ingest` fills it from the census when the file is unchanged since
    the note (same blob), or carries it over from the copy already in data/notes/. After that, a symbol whose hash equals the census hash is
    known to be unchanged, so its start/end are corrected to the census lines (and its evidence ranges moved with it).
    A symbol whose code changed keeps its old hash and shows as stale until it is re-annotated.
  * The census is the only source of facts (lines, signatures, hashes). Copilot adds meaning, never numbers it could get wrong.
  * `ingest` never deletes a note by itself: without MiniMe's atlas-notes folder (another machine) it just rebuilds the index
    from data/notes. A note in MiniMe that is older (`written`) than the committed copy is skipped.

The functions below are importable on purpose: scripts/arch.py (P25) reuses the census loading, blob lookup,
hash filling and freshness helpers.
"""
from __future__ import annotations

import argparse
import collections
import copy
import datetime as dt
import functools
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_code  # noqa: E402  (P10: census access, shared conventions)
import build_index  # noqa: E402

ROOT = HERE.parent
SCHEMA = 1
NOTES_SUBDIR = "graphify-out/atlas-notes"          # inside the MiniMe checkout
DATA_NOTES = "data/notes"
INDEX_FILE = "data/index/notes.json"
TIERS_FILE = "content/notes-tiers.json"
CENSUS_FILE = "data/census.json"
CONFIDENCE = ("high", "medium", "low")
COVERAGE_TIERS = (1, 2, 3)                          # tier 4 is optional one-liners: listed, but not part of the coverage totals

# Text limits keep the UI tidy. Going over one is a warning (the UI truncates), never an error.
LIMITS = {
    "summary": 240, "purpose": 800, "role": 40, "layer": 40,
    "list_n": 12, "list_item": 200,
    "blocks_n": 14, "block_title": 80, "block_text": 500, "block_anchor": 200,
    "sym_summary": 160, "sym_details": 600, "sym_param_desc": 200, "sym_returns": 200, "sym_item": 160, "sym_list_n": 12,
}
TOP_KEYS = {"schema", "path", "blob", "commit", "written", "tier", "summary", "purpose", "role", "layer", "how_it_works",
            "inputs", "outputs", "side_effects", "concepts", "gotchas", "unknowns", "blocks", "symbols"}
LIST_KEYS = ("how_it_works", "inputs", "outputs", "side_effects", "concepts", "gotchas", "unknowns")
BLOCK_KEYS = {"lines", "anchor", "title", "text"}
SYMBOL_KEYS = {"qual", "start", "end", "hash", "summary", "details", "params", "returns", "raises", "side_effects", "confidence", "evidence"}

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX10 = re.compile(r"^[0-9a-f]{10}$")
RANGE = re.compile(r"^(\d+)(?:-(\d+))?$")
SECRET_RES = [re.compile(p) for p in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"\bsk-[A-Za-z0-9_-]{20,}",
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}",
    r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']",
)]

read_lf = build_index.read_lf
load_json = build_index.load_json
dumps = build_index.dumps
census_files = build_code.census_files
commit_of = build_code.commit_of


def note_filename(path: str) -> str:
    return path.replace("/", "__") + ".json"


# ----------------------------------------------------------------------------- git
def git(repo, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def ls_tree_blobs(repo, rev: str = "HEAD") -> dict[str, str] | None:
    """{path: blob id} of every file in `rev`, from ONE `git ls-tree -r`. None when git cannot answer.

    Blob ids come from git objects, never from the working tree, so Windows CRLF checkouts cannot cause false 'stale'."""
    r = git(repo, "ls-tree", "-r", "-z", rev)
    if r.returncode:
        return None
    out: dict[str, str] = {}
    for rec in r.stdout.split(b"\0"):
        if not rec:
            continue
        meta, _, path = rec.partition(b"\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == b"blob":
            out[path.decode("utf-8", "replace")] = parts[2].decode("ascii")
    return out


# ----------------------------------------------------------------------------- globs and tiers
def _glob_body(g: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(g):
        c = g[i]
        if c == "*":
            if g.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if g.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "{" and "}" in g[i:]:
            j = g.index("}", i)
            out.append("(?:" + "|".join(_glob_body(a) for a in g[i + 1:j].split(",")) + ")")
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    return "".join(out)


@functools.lru_cache(maxsize=None)
def _glob_re(g: str) -> re.Pattern:
    return re.compile("^" + _glob_body(g) + "$")


def glob_match(pattern: str, path: str) -> bool:
    """`**` crosses folders, `*` and `?` do not, `{a,b}` is alternatives. A pattern without "/" matches the file name at any depth."""
    target = path if "/" in pattern else path.rsplit("/", 1)[-1]
    return bool(_glob_re(pattern).match(target))


def load_tiers(root: Path) -> dict:
    cfg = load_json(Path(root) / TIERS_FILE, None)
    return cfg if isinstance(cfg, dict) else {"rules": [], "default": {"tier": 3, "languages": ["python", "javascript"], "other": 0}, "symbols": {}}


def _rule_matches(rule: dict, f: dict, route_files: set[str]) -> bool:
    langs = rule.get("languages")
    if langs and f.get("lang") not in langs:
        return False
    path = f["path"]
    return bool((rule.get("binary") and f.get("binary"))
                or (rule.get("test") and f.get("test"))
                or (rule.get("route_files") and path in route_files)
                or any(glob_match(g, path) for g in rule.get("globs", [])))


def assign_tiers(files: list[dict], cfg: dict, degree: dict[str, int] | None = None, route_files=()) -> dict[str, tuple[int, str]]:
    """{path: (tier, why)}. Rules are tried in order; the first that matches a file wins, so a `hubs` rule only ranks
    the files that no earlier rule has claimed (a test file that is a graph hub stays a test)."""
    degree = degree or {}
    route_files = set(route_files)
    pending = {f["path"]: f for f in files}
    out: dict[str, tuple[int, str]] = {}
    for i, rule in enumerate(cfg.get("rules", [])):
        tier, why = int(rule.get("tier", 0)), rule.get("why") or f"rule {i + 1}"
        if rule.get("hubs"):
            langs = rule.get("languages")
            cands = sorted((p for p, f in pending.items() if degree.get(p, 0) > 0 and (not langs or f.get("lang") in langs)),
                           key=lambda p: (-degree[p], p))[:int(rule["hubs"])]
            hit = set(cands)
        else:
            hit = {p for p, f in pending.items() if _rule_matches(rule, f, route_files)}
        for p in sorted(hit):
            out[p] = (tier, why)
            del pending[p]
    d = cfg.get("default", {})
    for p, f in sorted(pending.items()):
        if f.get("lang") in d.get("languages", ["python", "javascript"]):
            out[p] = (int(d.get("tier", 3)), "default")
        else:
            out[p] = (int(d.get("other", 0)), "default (not source code)")
    return out


def graph_degrees(minime, paths: set[str]) -> tuple[dict[str, int], str]:
    """Cross-file links per file from graphify-out/graph.json: ({path: links}, 'graph'). ({}, 'none') when there is no graph.

    Node source files are matched to census paths by progressively dropping leading folders, so a graph built with a
    repo prefix still resolves."""
    gp = Path(minime) / "graphify-out" / "graph.json" if minime else None
    if not gp or not gp.exists():
        return {}, "none"
    try:
        g = json.loads(read_lf(gp))
    except (OSError, ValueError):
        return {}, "none"
    cache: dict[str, str] = {}

    def resolve(p) -> str:
        if isinstance(p, list):
            p = p[0] if p else ""
        p = re.sub(r"^\./", "", str(p or "").replace("\\", "/"))
        if p in cache:
            return cache[p]
        parts, found = p.split("/"), ""
        for k in range(len(parts)):
            cand = "/".join(parts[k:])
            if cand in paths:
                found = cand
                break
        cache[p] = found
        return found

    file_of = {n.get("id"): resolve(n.get("source_file")) for n in g.get("nodes", [])}
    links = g.get("links") if g.get("links") is not None else g.get("edges") or []
    deg: collections.Counter = collections.Counter()
    for l in links:
        a, b = file_of.get(l.get("source")), file_of.get(l.get("target"))
        if a and b and a != b:
            deg[a] += 1
            deg[b] += 1
    return dict(deg), "graph"


# ----------------------------------------------------------------------------- symbols
def _visibility(sym: dict) -> str:
    v = sym.get("visibility")
    if v:
        return v
    name = sym.get("name") or ""
    if name.startswith("__") and name.endswith("__"):
        return "dunder"
    return "private" if name.startswith("_") else "public"


def symbol_table(rec: dict) -> dict[str, tuple[dict, str]]:
    """{qual: (census symbol, kind)} for the functions and classes of a census file. Census v2 keys are unique."""
    out: dict[str, tuple[dict, str]] = {}
    for x in rec.get("functions") or []:
        if x.get("qual"):
            out[x["qual"]] = (x, x.get("kind") or "function")
    for x in rec.get("classes") or []:
        q = x.get("qual") or x.get("name")
        if q:
            out[q] = (x, "class")
    return out


def wanted_symbols(rec: dict, tier: int, cfg: dict) -> list[tuple[str, dict, str]]:
    """The symbols of a file that should have their own note entry at this tier: [(qual, census symbol, kind)], in source order."""
    sr = cfg.get("symbols", {})
    rule = sr.get(str(tier))
    if not rule or tier not in (1, 2, 3):
        return []
    skip = set(sr.get("skip_kinds", ["nested"]))
    out = []
    for qual, (s, kind) in symbol_table(rec).items():
        if kind in skip or s.get("test"):
            continue
        loc = s.get("loc") or (int(s.get("end", 0)) - int(s.get("start", 0)) + 1)
        ok = ((rule.get("min_loc") is not None and loc >= rule["min_loc"])
              or (rule.get("min_cc") is not None and (s.get("cc") or 0) >= rule["min_cc"])
              or (rule.get("decorated") and s.get("decorators"))
              or (rule.get("public") and _visibility(s) == "public")
              or (rule.get("exported") and s.get("exported") is True))
        if ok:
            out.append((qual, s, kind))
    return sorted(out, key=lambda t: (t[1].get("start", 0), t[0]))


def signature(sym: dict, kind: str) -> str:
    if kind == "class":
        b = ", ".join(sym.get("bases") or [])
        return f"class {sym.get('name', '')}({b})" if b else f"class {sym.get('name', '')}"
    ps = []
    for p in sym.get("params") or []:
        s = str(p.get("name", ""))
        if p.get("annotation"):
            s += f": {p['annotation']}"
        if "default" in p:
            s += f" = {p['default']}"
        ps.append(s)
    sig = f"{'async ' if sym.get('async') else ''}{sym.get('name', '')}({', '.join(ps)})"
    if sym.get("returns"):
        sig += f" -> {sym['returns']}"
    return sig if len(sig) <= 160 else sig[:157] + "..."


# ----------------------------------------------------------------------------- context
class Ctx:
    """Everything the freshness and tiering code needs, loaded once. (A plain class: scripts here are loaded with
    importlib by the tests, and dataclasses cannot be created in a module that is not in sys.modules.)"""

    def __init__(self, commit: str = ""):
        self.commit = commit                # census commit (full sha)
        self.files: dict = {}               # path -> census file record
        self.symbols: dict = {}             # path -> {qual: (symbol, kind)}
        self.blobs: dict | None = None      # path -> blob id at `commit`; None = git unavailable
        self.tiers: dict = {}               # path -> (tier, why)
        self.cfg: dict = {}
        self.degree: dict = {}              # path -> cross-file graph links
        self.hubs_source = "none"           # "graph" when graph.json was read
        self.warnings: list = []


def build_ctx(root: Path, minime=None, census: dict | None = None) -> Ctx:
    root = Path(root)
    census = census if census is not None else load_json(root / CENSUS_FILE, None)
    if not census:
        sys.exit(f"{root / CENSUS_FILE} not found. Run scripts/refresh_atlas.py first.")
    ctx = Ctx(commit=commit_of(census))
    flist = census_files(census)
    ctx.files = {f["path"]: f for f in flist}
    ctx.symbols = {p: symbol_table(f) for p, f in ctx.files.items()}
    ctx.cfg = load_tiers(root)
    if minime and Path(minime).is_dir():
        blobs = ls_tree_blobs(minime, ctx.commit) if len(ctx.commit) == 40 else None
        if blobs is None:
            blobs = ls_tree_blobs(minime, "HEAD")
            if blobs is not None:
                ctx.warnings.append(f"census commit {ctx.commit[:7] or '(unknown)'} is not in {minime}; blobs were read from its HEAD instead")
        ctx.blobs = blobs
        ctx.degree, ctx.hubs_source = graph_degrees(minime, set(ctx.files))
    routes = {r["file"] for r in census.get("routes", []) if isinstance(r, dict) and r.get("file")}
    ctx.tiers = assign_tiers(flist, ctx.cfg, ctx.degree, routes)
    return ctx


# ----------------------------------------------------------------------------- validation
class Problems:
    def __init__(self, errors=None, warnings=None):
        self.errors: list = errors if errors is not None else []
        self.warnings: list = warnings if warnings is not None else []


def _walk_strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _walk_strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk_strings(x)


def _text(p: Problems, where: str, v, limit: int | None = None, required: bool = False, nullable: bool = False) -> None:
    if v is None and nullable:
        return
    if not isinstance(v, str) or (required and not v.strip()):
        p.errors.append(f"{where}: must be a {'non-empty ' if required else ''}string")
    elif limit and len(v) > limit:
        p.warnings.append(f"{where}: {len(v)} characters (limit {limit}); the site will cut it")


def _text_list(p: Problems, where: str, v, n: int, limit: int) -> None:
    if not isinstance(v, list):
        p.errors.append(f"{where}: must be a list of strings")
        return
    if len(v) > n:
        p.warnings.append(f"{where}: {len(v)} items (limit {n})")
    for i, x in enumerate(v):
        _text(p, f"{where}[{i}]", x, limit)


def _ranges(p: Problems, where: str, v) -> None:
    if not isinstance(v, list):
        p.errors.append(f"{where}: must be a list of line ranges like \"80-82\"")
        return
    for i, x in enumerate(v):
        m = RANGE.match(x) if isinstance(x, str) else None
        if not m or (m.group(2) and int(m.group(2)) < int(m.group(1))):
            p.errors.append(f"{where}[{i}]: {x!r} is not a line range like \"80-82\" or \"80\"")


def validate_note(note, filename: str | None = None, ctx: Ctx | None = None) -> Problems:
    """Check one note against the schema (and the census, when `ctx` is given). Pure."""
    p = Problems()
    if not isinstance(note, dict):
        p.errors.append("the file must contain one JSON object")
        return p
    for k in sorted(set(note) - TOP_KEYS):
        p.warnings.append(f"unknown key {k!r} (ignored)")
    if note.get("schema") != SCHEMA:
        p.errors.append(f"schema must be {SCHEMA}")
    path = note.get("path")
    _text(p, "path", path, required=True)
    if isinstance(path, str) and filename and note_filename(path) != filename:
        p.errors.append(f"file name should be {note_filename(path)} for path {path}")
    for k in ("blob", "commit"):
        if not isinstance(note.get(k), str) or not HEX40.match(note[k]):
            p.errors.append(f"{k}: must be a 40-character lowercase hex id")
    try:
        dt.date.fromisoformat(note["written"])
    except (KeyError, TypeError, ValueError):
        p.errors.append("written: must be a date like 2026-11-16")
    if not isinstance(note.get("tier"), int) or isinstance(note.get("tier"), bool) or not 1 <= note["tier"] <= 4:
        p.errors.append("tier: must be 1, 2, 3 or 4")
    _text(p, "summary", note.get("summary"), LIMITS["summary"], required=True)
    for k in ("purpose", "role", "layer"):
        if k in note:
            _text(p, k, note[k], LIMITS.get(k))
    for k in LIST_KEYS:
        if k in note:
            _text_list(p, k, note[k], LIMITS["list_n"], LIMITS["list_item"])

    flines = (ctx.files.get(path) or {}).get("lines") if ctx and isinstance(path, str) else None
    blocks = note.get("blocks", [])
    if not isinstance(blocks, list):
        p.errors.append("blocks: must be a list")
        blocks = []
    elif len(blocks) > LIMITS["blocks_n"]:
        p.warnings.append(f"blocks: {len(blocks)} items (limit {LIMITS['blocks_n']})")
    for i, b in enumerate(blocks):
        w = f"blocks[{i}]"
        if not isinstance(b, dict):
            p.errors.append(f"{w}: must be an object")
            continue
        for k in sorted(set(b) - BLOCK_KEYS):
            p.warnings.append(f"{w}: unknown key {k!r}")
        m = re.match(r"^(\d+)-(\d+)$", b["lines"]) if isinstance(b.get("lines"), str) else None
        if not m or int(m.group(2)) < int(m.group(1)) or int(m.group(1)) < 1:
            p.errors.append(f"{w}.lines: must look like \"58-82\"")
        elif flines and int(m.group(2)) > flines:
            p.warnings.append(f"{w}.lines: ends at line {m.group(2)} but the file has {flines} lines")
        _text(p, f"{w}.anchor", b.get("anchor"), LIMITS["block_anchor"], required=True)
        _text(p, f"{w}.title", b.get("title"), LIMITS["block_title"], required=True)
        _text(p, f"{w}.text", b.get("text"), LIMITS["block_text"], required=True)

    symbols = note.get("symbols", [])
    if not isinstance(symbols, list):
        p.errors.append("symbols: must be a list")
        symbols = []
    seen: set[str] = set()
    at_census = bool(ctx and note.get("commit") == ctx.commit)      # written against this very commit: a missing symbol is a mistake
    known_file = bool(ctx and isinstance(path, str) and path in ctx.files)
    table = ctx.symbols.get(path, {}) if known_file else {}
    for i, s in enumerate(symbols):
        w = f"symbols[{i}]"
        if not isinstance(s, dict):
            p.errors.append(f"{w}: must be an object")
            continue
        for k in sorted(set(s) - SYMBOL_KEYS):
            p.warnings.append(f"{w}: unknown key {k!r}")
        q = s.get("qual")
        _text(p, f"{w}.qual", q, required=True)
        if isinstance(q, str):
            w = f"symbol {q}"
            if q in seen:
                p.errors.append(f"{w}: listed twice")
            seen.add(q)
            if known_file and q not in table:
                (p.errors if at_census else p.warnings).append(
                    f"{w}: not in the census for {path}" + ("" if at_census else " (the code changed since the note; it will show as broken)"))
        st, en = s.get("start"), s.get("end")
        if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 1 for x in (st, en)) or en < st:
            p.errors.append(f"{w}: start and end must be line numbers with start <= end")
        if s.get("hash") is not None and not (isinstance(s.get("hash"), str) and HEX10.match(s["hash"])):
            p.errors.append(f"{w}.hash: must be null or 10 hex characters")
        _text(p, f"{w}.summary", s.get("summary"), LIMITS["sym_summary"], required=True)
        for k, lim in (("details", LIMITS["sym_details"]), ("returns", LIMITS["sym_returns"])):
            if k in s:
                _text(p, f"{w}.{k}", s[k], lim, nullable=True)
        for k in ("raises", "side_effects"):
            if k in s:
                _text_list(p, f"{w}.{k}", s[k], LIMITS["sym_list_n"], LIMITS["sym_item"])
        if "params" in s:
            if not isinstance(s["params"], list):
                p.errors.append(f"{w}.params: must be a list of {{name, desc}}")
            else:
                for j, pr in enumerate(s["params"]):
                    if not isinstance(pr, dict) or not isinstance(pr.get("name"), str):
                        p.errors.append(f"{w}.params[{j}]: must be {{name, desc}}")
                    else:
                        _text(p, f"{w}.params[{j}].desc", pr.get("desc", ""), LIMITS["sym_param_desc"])
        if "confidence" in s and s["confidence"] not in CONFIDENCE:
            p.errors.append(f"{w}.confidence: must be one of {', '.join(CONFIDENCE)}")
        if "evidence" in s:
            _ranges(p, f"{w}.evidence", s["evidence"])

    if ctx and isinstance(path, str) and not known_file:
        (p.errors if at_census else p.warnings).append(
            f"{path} is not in the census" + ("" if at_census else " (the file was deleted or moved; the note is orphaned)"))
    if any(rx.search(s) for s in _walk_strings(note) for rx in SECRET_RES):
        p.errors.append("contains text that looks like a secret (key, token or password). Remove it; notes are published")
    return p


def load_note_file(path: Path):
    """(note or None, error message or None)."""
    try:
        return json.loads(read_lf(path)), None
    except (OSError, UnicodeDecodeError) as e:
        return None, f"cannot read: {e}"
    except ValueError as e:
        return None, f"invalid JSON: {e}"


def read_notes_dir(d: Path) -> tuple[dict[str, dict], dict[str, Problems]]:
    """({file name: note}, {file name: problems for unreadable files}) for every note in a folder (names starting with _ are skipped)."""
    notes, bad = {}, {}
    if d.is_dir():
        for f in sorted(d.glob("*.json")):
            if f.name.startswith("_"):
                continue
            note, err = load_note_file(f)
            if err:
                bad[f.name] = Problems(errors=[err])
            else:
                notes[f.name] = note
    return notes, bad


# ----------------------------------------------------------------------------- freshness
def blob_state(note: dict, ctx: Ctx) -> str:
    """'same' (file unchanged since the note), 'changed', or 'gone' (not in the tree). Without git: same iff written at the census commit."""
    if ctx.blobs is None:
        return "same" if note.get("commit") == ctx.commit else "changed"
    cur = ctx.blobs.get(note.get("path"))
    if cur is None:
        return "gone"
    return "same" if cur == note.get("blob") else "changed"


def symbol_status(s: dict, cs: tuple | None, state: str) -> str:
    """fresh | stale | broken for one note symbol against its census symbol (`cs` is (symbol, kind) or None)."""
    if cs is None:
        return "broken"
    h, ch = s.get("hash"), cs[0].get("hash")
    if h and ch:
        return "fresh" if h == ch else "stale"
    return "fresh" if state == "same" and not ch else "stale"       # no hash to compare: trust only an unchanged file and a hash-less (v1) census


def evaluate_note(note: dict, ctx: Ctx) -> dict:
    """{"orphan": True} or {"file": fresh|stale, "blob": same|changed, "symbols": {qual: status}}."""
    path = note["path"]
    if path not in ctx.files:
        return {"orphan": True}
    state = blob_state(note, ctx)
    if state == "gone":
        return {"orphan": True}
    table = ctx.symbols.get(path, {})
    sts = {s["qual"]: symbol_status(s, table.get(s["qual"]), state) for s in note.get("symbols", [])}
    ok = state == "same" and all(v == "fresh" for v in sts.values())
    return {"file": "fresh" if ok else "stale", "blob": state, "symbols": sts}


def _shift(ranges: list, lo: int, hi: int, delta: int) -> list:
    out = []
    for r in ranges:
        m = RANGE.match(r)
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if lo <= a and b <= hi:
            a, b = a + delta, b + delta
            r = str(a) if m.group(2) is None else f"{a}-{b}"
        out.append(r)
    return out


def repair_note(note: dict, ctx: Ctx, prev: dict | None = None) -> dict:
    """A copy of the note with symbol hashes filled and the lines of unchanged symbols corrected from the census.

    A null hash is filled from the census when the file is unchanged since the note, or copied from `prev` (the copy
    already in data/notes) when that has the same blob and the same lines for the symbol. A symbol whose hash equals
    the census hash is unchanged by definition, so its start/end become the census lines and its evidence moves with it."""
    n = copy.deepcopy(note)
    table = ctx.symbols.get(n["path"], {})
    same = blob_state(n, ctx) == "same"
    prev_syms = {}
    if prev and prev.get("blob") == n.get("blob"):
        prev_syms = {s["qual"]: s for s in prev.get("symbols", []) if isinstance(s, dict) and "qual" in s}
    for s in n.get("symbols", []):
        cs = table.get(s["qual"])
        ch = cs[0].get("hash") if cs else None
        if not s.get("hash"):
            old = prev_syms.get(s["qual"])
            if same and ch:
                s["hash"] = ch
            elif old and old.get("hash") and (old.get("start"), old.get("end")) == (s["start"], s["end"]):
                s["hash"] = old["hash"]
        if cs and ch and s.get("hash") == ch and (s["start"], s["end"]) != (cs[0].get("start"), cs[0].get("end")):
            if s.get("evidence"):
                s["evidence"] = _shift(s["evidence"], s["start"], s["end"], cs[0]["start"] - s["start"])
            s["start"], s["end"] = cs[0]["start"], cs[0]["end"]
    return n


# ----------------------------------------------------------------------------- collecting notes
def collect_notes(root: Path, minime=None, ctx: Ctx | None = None):
    """Merge data/notes with MiniMe's atlas-notes folder (MiniMe wins unless its note is older).

    Returns (notes {path: note}, previous {path: valid data/notes copy}, problems {label: Problems}, skipped [messages]).
    A label is the file name for a note in MiniMe and data/notes/<file name> for a committed one. A note with errors is
    left out of `notes` (the committed copy, if it is valid, stays)."""
    root = Path(root)
    data, bad = read_notes_dir(root / DATA_NOTES)
    problems: dict[str, Problems] = {f"{DATA_NOTES}/{n}": pr for n, pr in bad.items()}
    skipped: list[str] = []
    previous: dict[str, dict] = {}
    for name, note in data.items():                      # the committed notes are validated too, so a hand edit cannot slip in
        pr = validate_note(note, name, ctx)
        if pr.errors or pr.warnings:
            problems[f"{DATA_NOTES}/{name}"] = pr
        if not pr.errors:
            previous[note["path"]] = note
    merged = dict(previous)
    src, src_bad = read_notes_dir(Path(minime) / NOTES_SUBDIR) if minime else ({}, {})
    problems.update(src_bad)
    for name, note in src.items():
        pr = validate_note(note, name, ctx)
        if pr.errors or pr.warnings:
            problems[name] = pr
        if pr.errors:
            continue
        old = previous.get(note["path"])
        if old and str(old.get("written", "")) > str(note.get("written", "")):
            skipped.append(f"{name}: written {note['written']}, older than the committed copy ({old['written']}); skipped")
            continue
        merged[note["path"]] = note
    return merged, previous, problems, skipped


# ----------------------------------------------------------------------------- the index (data/index/notes.json)
def _tier_row() -> dict:
    return {"files": 0, "noted": 0, "fresh": 0, "stale": 0, "missing": 0, "symbols_wanted": 0, "symbols_covered": 0}


def build_notes_index(ctx: Ctx, notes: dict[str, dict]) -> dict:
    """Coverage and freshness of every eligible file. `notes` is {path: (repaired) note}. Pure."""
    tiers = {str(t): _tier_row() for t in (1, 2, 3, 4)}
    folders: dict[str, dict] = {}
    files: dict[str, dict] = {}
    orphans = sorted(p for p, n in notes.items() if evaluate_note(n, ctx).get("orphan"))
    for path in sorted(ctx.files):
        tier = ctx.tiers.get(path, (0, ""))[0]
        if tier < 1:
            continue
        note = notes.get(path)
        ev = evaluate_note(note, ctx) if note else None
        status = "missing" if not ev or ev.get("orphan") else ev["file"]
        wanted = {q for q, _, _ in wanted_symbols(ctx.files[path], tier, ctx.cfg)}
        fresh_q = {q for q, st in (ev or {}).get("symbols", {}).items() if st == "fresh"}
        row = tiers[str(tier)]
        row["files"] += 1
        row[status] += 1
        if status != "missing":
            row["noted"] += 1
        row["symbols_wanted"] += len(wanted)
        row["symbols_covered"] += len(wanted & fresh_q)
        if tier in COVERAGE_TIERS:
            parts = path.split("/")[:-1]
            for k in range(1, len(parts) + 1):
                fr = folders.setdefault("/".join(parts[:k]), {"files": 0, "noted": 0, "fresh": 0, "stale": 0})
                fr["files"] += 1
                if status != "missing":
                    fr["noted"] += 1
                    fr[status] += 1
        if status != "missing":
            counts = collections.Counter(ev["symbols"].values())
            files[path] = {
                "tier": tier, "status": status, "written": note.get("written", ""), "summary": note.get("summary", "")[:160],
                "symbols": {k: counts[k] for k in ("fresh", "stale", "broken") if counts[k]},
                "bad": sorted(q for q, st in ev["symbols"].items() if st != "fresh")[:20],
            }
    totals = _tier_row()
    for t in COVERAGE_TIERS:
        for k, v in tiers[str(t)].items():
            totals[k] += v
    return {"schema": SCHEMA, "commit": ctx.commit, "blobs_known": ctx.blobs is not None, "hubs_source": ctx.hubs_source,
            "totals": totals, "tiers": tiers, "folders": folders, "files": files, "orphans": orphans}


# ----------------------------------------------------------------------------- ingest
def ingest(root: Path, minime=None, check: bool = False, skip_invalid: bool = False, prune: bool = False, log=print) -> int:
    """Validate, copy into data/notes, rebuild data/index/notes.json. Returns an exit code."""
    root = Path(root)
    ctx = build_ctx(root, minime)
    for w in ctx.warnings:
        log(f"warning: {w}")
    src_dir = Path(minime) / NOTES_SUBDIR if minime else None
    if src_dir and not src_dir.is_dir():
        log(f"no {NOTES_SUBDIR} folder in {minime} (nothing written there yet, or another machine): using data/notes as it is")
    notes, previous, problems, skipped = collect_notes(root, minime, ctx)
    for s in skipped:
        log(f"warning: {s}")
    errors = {n: pr for n, pr in problems.items() if pr.errors}
    for name, pr in sorted(problems.items()):
        for w in pr.warnings:
            log(f"warning: {name}: {w}")
    if errors:
        for name, pr in sorted(errors.items()):
            for e in pr.errors:
                log(f"error: {name}: {e}")
        if not skip_invalid:
            log(f"\n{len(errors)} note file(s) are malformed, nothing was ingested. Fix or delete them (they are in "
                f"{src_dir if src_dir else root / DATA_NOTES}), or use --skip-invalid to ingest the rest.")
            return 1
        log(f"{len(errors)} malformed note file(s) skipped (--skip-invalid)")
    if prune:
        for p in [p for p, n in notes.items() if evaluate_note(n, ctx).get("orphan")]:
            del notes[p]
            log(f"pruned the note of {p} (not in the census)")
    repaired = {p: repair_note(n, ctx, previous.get(p)) for p, n in notes.items()}
    wanted: dict[str, str] = {f"{DATA_NOTES}/{note_filename(p)}": dumps(n) for p, n in sorted(repaired.items())}
    wanted[INDEX_FILE] = dumps(build_notes_index(ctx, repaired))

    changed, stale_files = [], []
    for rel, text in wanted.items():
        f = root / rel
        if not f.exists() or read_lf(f) != text:
            changed.append(rel)
    d = root / DATA_NOTES
    if prune and d.is_dir():
        stale_files = [f for f in sorted(d.glob("*.json")) if f"{DATA_NOTES}/{f.name}" not in wanted]
    if check:
        for rel in changed:
            log(f"notes are out of date: {rel}")
        for f in stale_files:
            log(f"notes are out of date: {DATA_NOTES}/{f.name} should be removed")
        if changed or stale_files:
            log("run: python scripts/notes.py ingest --minime <MiniMe>")
            return 1
        log("notes are current")
        return 0
    for rel in changed:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(wanted[rel].encode("utf-8"))                  # always LF; git/autocrlf is free to convert
    for f in stale_files:
        f.unlink()
    n_notes = len(repaired)
    log(f"notes: {n_notes} note(s) in data/notes, {len(changed)} file(s) updated" + (f", {len(stale_files)} removed" if stale_files else ""))
    return 0


# ----------------------------------------------------------------------------- todo and the instructions for Copilot
SCHEMA_MD = """# Atlas notes: what to write

You write one JSON file per source file into this folder (`graphify-out/atlas-notes/`). The next batch of files is in
`_todo.json` (same folder). The Atlas site shows your notes next to the real code, so they must be **true**.

## File name
`<path with "/" replaced by "__">.json`, for example `backend/agents/academic_search.py` becomes
`backend__agents__academic_search.py.json`.

## Shape (schema version 1)
```json
{
  "schema": 1,
  "path": "backend/agents/academic_search.py",
  "blob": "<copy from the todo entry>",
  "commit": "<copy from the todo entry>",
  "written": "2026-11-16",
  "tier": 1,
  "summary": "One sentence: what this file is.",
  "purpose": "2-4 sentences: what it is and why the system needs it.",
  "role": "agent",
  "layer": "agents",
  "how_it_works": ["Receives a query and chosen sources", "Calls four scholarly APIs", "Writes each paper as a graph node"],
  "inputs": ["query", "sources[]"],
  "outputs": ["knowledge-graph nodes and edges"],
  "side_effects": ["outbound HTTP to 4 APIs", "writes graph rows"],
  "concepts": ["role registry", "knowledge graph"],
  "gotchas": ["Makes zero LLM calls"],
  "unknowns": ["Why DOI is preferred over title for de-duplication is not stated in the code"],
  "blocks": [
    {"lines": "58-82", "anchor": "def _workspace_id", "title": "Workspace and query hygiene", "text": "1-3 sentences."}
  ],
  "symbols": [
    {
      "qual": "_clean_query",
      "start": 80, "end": 82,
      "hash": "<copy from the todo entry>",
      "summary": "Normalises a user query before it is sent to the APIs.",
      "details": "Optional, 1-3 sentences.",
      "params": [{"name": "task_text", "desc": "raw user text"}],
      "returns": "cleaned string",
      "raises": [],
      "side_effects": [],
      "confidence": "high",
      "evidence": ["80-82"]
    }
  ]
}
```

## Rules
* `path`, `blob`, `commit`, `tier`: copy them from the todo entry. Never compute or guess them.
* `written`: today's date, `YYYY-MM-DD`.
* `symbols`: write an entry for every symbol listed in the todo entry, using exactly its `qual`, `start`, `end` and `hash`.
  Never invent a `qual` that is not listed there. Only the symbols listed need an entry; leave the others out.
* `blocks` (tier 1 only): 4-10 contiguous line ranges that walk a newcomer through the file in reading order.
  `anchor` is the exact first line of the block (leading spaces removed).
* **Be truthful.** Describe only what the code does. If a reason, a behaviour or a caller is not visible in the code,
  put it in `unknowns` instead of guessing. Use `"confidence": "low"` when you are unsure. Every symbol needs
  `evidence`: the line ranges you relied on.
* `side_effects`: I/O, database writes, network calls, LLM calls, file system, subprocesses.
* **Never include secrets**, tokens, passwords or values from `.env` files. Notes are published.
* Plain English, no marketing words. Do not copy long passages of code or comments.
* For a symbol that is gone (listed under `removed` in the todo entry): delete its entry.

## Limits (longer text still works but is cut on the site)
summary @summary@ chars, purpose @purpose@, a symbol's summary @sym_summary@, details @sym_details@, returns @sym_returns@,
a block's text @block_text@, each list item @list_item@, at most @list_n@ items per list and @blocks_n@ blocks.
Optional fields may be left out. Unknown keys are ignored with a warning.

## Tiers (how deep to go)
1: full note with `blocks` and every listed symbol. 2: file note and the listed symbols. 3: file note and the listed
public symbols. 4: only `summary` (and `purpose` if it is obvious); no symbols.
"""


def schema_markdown() -> str:
    text = SCHEMA_MD
    for k, v in LIMITS.items():
        text = text.replace(f"@{k}@", str(v))
    return text


def build_todo(ctx: Ctx, notes: dict[str, dict], tier_max: int = 1, limit: int = 20, head: str = "", max_symbols: int = 200) -> dict:
    """The next batch of files that need a note (missing, or stale), tiers 1..tier_max, most connected first.

    A batch stops at `limit` files or when adding the next file would pass `max_symbols` symbols (a file is never split, and
    the first file is always taken), so a few huge files do not make one Copilot session too big."""
    rows = []
    for path, rec in ctx.files.items():
        tier = ctx.tiers.get(path, (0, ""))[0]
        if not 1 <= tier <= tier_max:
            continue
        note = notes.get(path)
        ev = evaluate_note(note, ctx) if note else None
        if ev and ev.get("orphan"):
            ev = note = None
        if ev and ev["file"] == "fresh":
            continue
        want = wanted_symbols(rec, tier, ctx.cfg)
        syms, removed, kept = [], [], 0
        if tier <= 3:
            table = ctx.symbols.get(path, {})
            sts = (ev or {}).get("symbols", {})
            quals = [q for q, _, _ in want] + sorted(q for q, st in sts.items() if st == "stale" and q in table and q not in {w[0] for w in want})
            for qual in quals:
                s, kind = table[qual]
                st = sts.get(qual)
                if st == "fresh":
                    kept += 1
                    continue
                syms.append({
                    "qual": qual, "kind": kind, "start": s.get("start"), "end": s.get("end"), "hash": s.get("hash"),
                    "loc": s.get("loc"), "cc": s.get("cc"), "signature": signature(s, kind), "doc1": s.get("doc1"),
                    "why": "new" if st is None else ("changed" if st == "stale" else "fix"),
                })
            syms.sort(key=lambda x: (x["start"] or 0, x["qual"]))
        if ev:
            removed = sorted(q for q, st in ev["symbols"].items() if st == "broken")
        reason = "new" if not note else ("changed" if ev["blob"] == "changed" else "fix")
        rows.append({
            "path": path, "tier": tier, "reason": reason, "note_file": note_filename(path),
            "blob": (ctx.blobs or {}).get(path), "commit": ctx.commit,
            "lines": rec.get("lines"), "links": ctx.degree.get(path, 0), "commits": (rec.get("git") or {}).get("commits", 0),
            "module_doc": (rec.get("module_doc") or "")[:500] or None,
            "write_blocks": tier == 1, "symbols": syms, "removed": removed, "fresh_symbols_kept": kept,
        })
    rows.sort(key=lambda r: (r["tier"], -r["links"], -r["commits"], r["path"]))
    batch, used = [], 0
    for r in rows:
        if len(batch) >= limit or (batch and used + len(r["symbols"]) > max_symbols):
            break
        batch.append(r)
        used += len(r["symbols"])
    return {"schema": SCHEMA, "commit": ctx.commit, "head": head, "tier_max": tier_max, "limit": limit, "max_symbols": max_symbols,
            "files_needing_work": len(rows), "files": batch}


# ----------------------------------------------------------------------------- reports
def format_status(idx: dict, folders: bool = False, top: int = 25) -> str:
    out = [f"Notes coverage at census {idx.get('commit', '')[:7] or '?'}"
           + ("" if idx.get("blobs_known") else "   (no MiniMe checkout: freshness judged by commit only)")
           + ("" if idx.get("hubs_source") == "graph" else "   (no graph: the most-connected-files rule found nothing)"),
           "", "tier  what         files  noted  fresh  stale  missing  coverage   symbols covered/wanted"]
    names = {"1": "full", "2": "standard", "3": "light", "4": "one line"}
    for t in ("1", "2", "3", "4"):
        r = idx["tiers"][t]
        pct = f"{100 * r['noted'] // r['files']}%" if r["files"] else "-"
        out.append(f"T{t}    {names[t]:<10} {r['files']:>6} {r['noted']:>6} {r['fresh']:>6} {r['stale']:>6} {r['missing']:>8} {pct:>9}   "
                   f"{r['symbols_covered']}/{r['symbols_wanted']}")
    r = idx["totals"]
    out.append(f"T1-3  {'total':<10} {r['files']:>6} {r['noted']:>6} {r['fresh']:>6} {r['stale']:>6} {r['missing']:>8} "
               f"{(str(100 * r['noted'] // r['files']) + '%') if r['files'] else '-':>9}   {r['symbols_covered']}/{r['symbols_wanted']}")
    if idx.get("orphans"):
        out.append(f"\n{len(idx['orphans'])} note(s) belong to files that no longer exist (use ingest --prune-orphans).")
    if folders:
        out += ["", "folder                                   files  noted  fresh  stale"]
        rows = sorted(idx["folders"].items(), key=lambda kv: (-kv[1]["files"], kv[0]))[:top]
        out += [f"{k:<40} {v['files']:>5} {v['noted']:>6} {v['fresh']:>6} {v['stale']:>6}" for k, v in rows]
    return "\n".join(out)


def default_minime(arg: str | None) -> Path | None:
    p = Path(arg) if arg else ROOT.parent / "MiniMe"
    return p if p.is_dir() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_minime(sp, required=False):
        sp.add_argument("--minime", default=None, required=required, help="the MiniMe checkout (default: ../MiniMe when it exists)")

    sp = sub.add_parser("status", help="coverage by tier")
    add_minime(sp)
    sp.add_argument("--folders", action="store_true", help="also list the busiest folders")
    sp = sub.add_parser("tiers", help="show the tier of files and the rule that decided it")
    add_minime(sp)
    sp.add_argument("paths", nargs="*", help="files to explain (default: a count per tier)")
    sp = sub.add_parser("todo", help="write _SCHEMA.md and _todo.json for Copilot into MiniMe's atlas-notes folder")
    add_minime(sp)
    sp.add_argument("--tier", type=int, default=1, help="include tiers 1..N (default 1)")
    sp.add_argument("--limit", type=int, default=20, help="files per batch (default 20)")
    sp.add_argument("--max-symbols", type=int, default=200, help="stop the batch before it passes this many symbols (default 200)")
    sp = sub.add_parser("validate", help="check notes against the schema and the census")
    add_minime(sp)
    sp.add_argument("--dir", default=None, help="a folder of notes (default: data/notes, or MiniMe's atlas-notes with --minime)")
    sp = sub.add_parser("ingest", help="validate and copy notes into data/notes, rebuild data/index/notes.json")
    add_minime(sp)
    sp.add_argument("--check", action="store_true", help="change nothing; exit 1 if data/notes or data/index/notes.json is out of date")
    sp.add_argument("--skip-invalid", action="store_true", help="ingest the valid notes even if some are malformed")
    sp.add_argument("--prune-orphans", action="store_true", help="delete the notes of files that are no longer in the census")
    args = ap.parse_args(argv)
    root = Path(args.root)
    minime = default_minime(args.minime)
    if args.minime and not minime:
        sys.exit(f"{args.minime} is not a folder. Use --minime PATH to the MiniMe checkout.")

    if args.cmd == "ingest":
        if not minime:
            print(f"warning: no MiniMe checkout at {args.minime or ROOT.parent / 'MiniMe'}; freshness is judged by commit only", file=sys.stderr)
        return ingest(root, minime, args.check, args.skip_invalid, args.prune_orphans)

    ctx = build_ctx(root, minime)
    for w in ctx.warnings:
        print(f"warning: {w}", file=sys.stderr)

    if args.cmd == "tiers":
        if args.paths:
            for p in args.paths:
                t = ctx.tiers.get(p)
                print(f"{p}: " + (f"T{t[0]}  ({t[1]})" if t else "not in the census"))
            return 0
        c = collections.Counter(t for t, _ in ctx.tiers.values())
        print("files per tier: " + ", ".join(f"T{t}: {c[t]}" for t in range(5)) + f"   (hubs from {ctx.hubs_source})")
        return 0

    if args.cmd == "validate":
        d = Path(args.dir) if args.dir else (minime / NOTES_SUBDIR if args.minime else root / DATA_NOTES)
        notes, bad = read_notes_dir(d)
        n_err = n_warn = 0
        results = {**bad, **{name: validate_note(n, name, ctx) for name, n in notes.items()}}
        for name, pr in sorted(results.items()):
            for e in pr.errors:
                print(f"error: {name}: {e}")
            for w in pr.warnings:
                print(f"warning: {name}: {w}")
            n_err += len(pr.errors)
            n_warn += len(pr.warnings)
        print(f"{len(results)} note file(s) in {d}: {n_err} error(s), {n_warn} warning(s)")
        return 1 if n_err else 0

    use_source = args.cmd == "todo" or bool(args.minime)          # status reads data/notes unless a MiniMe folder was asked for
    notes, previous, problems, skipped = collect_notes(root, minime if use_source else None, ctx)
    notes = {p: repair_note(n, ctx, previous.get(p)) for p, n in notes.items()}

    if args.cmd == "status":
        print(format_status(build_notes_index(ctx, notes), args.folders))
        return 0

    if args.cmd == "todo":
        if not minime:
            sys.exit("todo needs the MiniMe checkout: --minime PATH")
        if ctx.blobs is None:
            sys.exit(f"{minime} is not a git checkout (needed to read file blob ids).")
        head = git(minime, "rev-parse", "HEAD").stdout.decode().strip()
        todo = build_todo(ctx, notes, args.tier, args.limit, head, args.max_symbols)
        out = minime / NOTES_SUBDIR
        out.mkdir(parents=True, exist_ok=True)
        (out / "_SCHEMA.md").write_bytes(schema_markdown().encode("utf-8"))
        (out / "_todo.json").write_bytes((json.dumps(todo, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        for f in todo["files"]:                                      # Copilot refreshes a note in place, so it must be in MiniMe's folder
            dest = out / f["note_file"]
            if f["reason"] != "new" and not dest.exists() and f["path"] in notes:
                dest.write_bytes((json.dumps(notes[f["path"]], indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        if head and head != ctx.commit:
            print(f"warning: MiniMe is at {head[:7]} but the census is from {ctx.commit[:7]}. Run scripts/update_all.py first so lines and hashes match.", file=sys.stderr)
        for pr_name, pr in sorted(problems.items()):
            for e in pr.errors:
                print(f"warning: {pr_name} is malformed ({e}); its file is listed as new", file=sys.stderr)
        n_sym = sum(len(f["symbols"]) for f in todo["files"])
        print(f"batch of {len(todo['files'])} file(s), {n_sym} symbol(s); {todo['files_needing_work']} file(s) in tiers 1-{args.tier} still need a note. Written to {out / '_todo.json'}")
        for f in todo["files"]:
            print(f"  T{f['tier']} {f['reason']:<8} {f['path']}  ({len(f['symbols'])} symbols)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
