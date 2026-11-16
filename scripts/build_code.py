#!/usr/bin/env python3
"""Build the sharded code data the Explorer reads (patch P10).

Standard library only. Output is deterministic (sorted keys, no timestamps of its own), so `--check`
can compare it byte-for-byte (line endings are normalised on read). The browser never loads
data/census.json whole: it reads these small files, one at a time.

Input
  data/census.json      v1 or v2 (MiniMe's scripts/codebase_census.py). A v1 census still builds; it just
                        has no params / doc1 / calls / hash, so those fields are absent and callers is empty.

Outputs (all under data/code/)
  tree.json             {"schema", "commit", "generated", "script_version", "file_fields", "shards", "root"}
                        root is a folder: {"name", "n": {files, lines, code, functions, classes}, "dirs": [...], "files": [...]}.
                        A file is a row laid out as "file_fields": [name, lang, lines, code, functions, classes,
                        commits, last, flags, shard]. flags: "t" test file, "b" binary. shard is an index into "shards"
                        (-1 for a binary file, which has no record). Folders and files are sorted by name.
  files/<shard>.json    {"schema", "shard", "files": [record, ...]}  every non-binary file, sorted by path.
                        A record is the census entry (path, lang, lines, code, comment, blank, size, test, module_doc,
                        exports, git, functions, classes) minus "imports" (see imports.json). Empty fields are omitted.
                        Functions and classes carry every census field, v2 ones included; the join key of a symbol is
                        "<path>::<qual>" and is unique within the census.
                        Shards follow the folder tree: a folder whose records fit in SHARD_LIMIT bytes is one shard
                        (id: path with "/" as "__"); a bigger one is split by sub-folder; a folder that cannot be split
                        further is cut into <id>~1, <id>~2 ... in path order. A single file bigger than the limit is
                        alone in its shard.
  imports.json          {"schema", "commit", "imports", "imported_by", "external", "stats"}
                          imports      {path: [[target path, line], ...]}   what a file imports from inside the repo
                          imported_by  {path: [path, ...]}                   the reverse of imports
                          external     {path: [name, ...]}                   third-party (and unresolved) top-level names;
                                                                             standard-library modules are only counted in stats
                          stats        {"python"|"javascript": {internal, external, stdlib, ambiguous}} (import statements)
                        Heuristic by design and unit-tested: relative imports are exact; an absolute Python import
                        matches the one repo file whose dotted path ends with the module, and only when no directory
                        above that suffix is a package (so "import stripe" never lands on routes/stripe.py inside a
                        package); a tie goes to the file sharing most of the importer's folder, non-test over test;
                        a tie that remains is "ambiguous" and kept as external. "from pkg import name" links the package's
                        __init__.py and, when name is a module, that module too (so __init__.py files are imported a lot).
                        Lazy (in-function) imports count. JavaScript: relative specifiers only (the repo has no path
                        aliases); extensions and /index files are tried.
  callers/<shard>.json  {"schema", "shard", "callers": {"<path>::<qual>": ["<path>::<qual>", ...]}}
                        the reverse of every resolved "calls" pair of a Python function, stored with the shard of the
                        *called* symbol's file so opening a file needs files/<shard>.json plus callers/<shard>.json.
                        A called symbol is a function or a class (a constructor call resolves to the class); a caller
                        is always a function.
                        (One callers.json would be 2.5 MB; the plan's 400 KB target is why it is sharded.)
                        JavaScript has no call data in the census, so it has no callers.

Usage
  python scripts/build_code.py            write the files
  python scripts/build_code.py --check    exit 1 if the files on disk are stale
"""
from __future__ import annotations

import argparse
import collections
import posixpath
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_index  # noqa: E402  (P03: shared reading / writing conventions)

ROOT = HERE.parent
CODE_DIR = "data/code"
FILES_DIR = f"{CODE_DIR}/files"
CALLERS_DIR = f"{CODE_DIR}/callers"
SCHEMA = 1
SHARD_LIMIT = 400_000            # bytes of JSON per shard (the plan's target; check_site warns at 600 KB)
TREE_FIELDS = ["name", "lang", "lines", "code", "functions", "classes", "commits", "last", "flags", "shard"]
JS_EXTS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
JS_LANG_EXTS = {e.lstrip(".") for e in JS_EXTS}
JS_BUILTINS = {"fs", "path", "os", "util", "crypto", "http", "https", "http2", "child_process", "url", "stream", "events",
               "assert", "zlib", "net", "tls", "readline", "buffer", "querystring", "timers", "worker_threads", "perf_hooks",
               "dns", "cluster", "vm", "v8", "module", "process", "string_decoder", "tty", "dgram", "inspector"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}      # sys.stdlib_module_names needs Python 3.10+

read_lf = build_index.read_lf
load_json = build_index.load_json
dumps = build_index.dumps


# ---------------------------------------------------------------------- census access
def census_files(census: dict) -> list[dict]:
    files = census.get("files") or []
    if isinstance(files, dict):
        files = [dict(v, path=k) for k, v in files.items() if isinstance(v, dict)]
    return sorted((f for f in files if isinstance(f, dict) and f.get("path")), key=lambda f: f["path"])


def commit_of(census: dict) -> str:
    g = census.get("git") or {}
    return g.get("head_full") or g.get("head") or ""


def _empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def file_record(f: dict) -> dict:
    """The census entry of a file, without its raw imports and without empty fields."""
    return {k: v for k, v in f.items() if k != "imports" and not _empty(v)}


# ---------------------------------------------------------------------- shards
def _shard_name(prefix: str) -> str:
    if not prefix:
        return "_root"
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", prefix.replace("/", "__")).strip(".-").lower()
    return s or "_root"


def plan_shards(sizes: dict[str, int], limit: int = SHARD_LIMIT) -> dict[str, str]:
    """{path: shard id}. `sizes` maps each path to the byte size of its record."""
    out: dict[str, str] = {}
    owner: dict[str, str] = {}          # shard id -> folder that claimed it (a clash gets a numeric suffix)

    def claim(prefix: str, suffix: str = "") -> str:
        base = _shard_name(prefix) + suffix
        sid, n = base, 1
        while owner.get(sid, prefix + suffix) != prefix + suffix:
            n += 1
            sid = f"{base}-{n}"
        owner[sid] = prefix + suffix
        return sid

    def chunk(prefix: str, paths: list[str]) -> None:
        part, used, n = [], 0, 1
        groups = []
        for p in sorted(paths):
            if part and used + sizes[p] > limit:
                groups.append(part)
                part, used = [], 0
            part.append(p)
            used += sizes[p]
        if part:
            groups.append(part)
        if len(groups) == 1:
            sid = claim(prefix)
            for p in groups[0]:
                out[p] = sid
            return
        for g in groups:
            sid = claim(prefix, f"~{n}")
            n += 1
            for p in g:
                out[p] = sid

    def split(prefix: str, paths: list[str]) -> None:
        if sum(sizes[p] for p in paths) <= limit:
            sid = claim(prefix)
            for p in paths:
                out[p] = sid
            return
        depth = len(prefix.split("/")) if prefix else 0
        direct, kids = [], collections.defaultdict(list)
        for p in paths:
            parts = p.split("/")
            if len(parts) - 1 == depth:
                direct.append(p)
            else:
                kids[parts[depth]].append(p)
        for name in sorted(kids):
            split(f"{prefix}/{name}" if prefix else name, kids[name])
        if direct:
            chunk(prefix, direct)

    split("", sorted(sizes))
    return out


# ---------------------------------------------------------------------- tree
def build_tree(files: list[dict], shard_of: dict[str, str], shards: list[str]) -> dict:
    index = {s: i for i, s in enumerate(shards)}

    def new():
        return {"dirs": {}, "files": []}

    top = new()
    for f in files:
        parts = f["path"].split("/")
        node = top
        for d in parts[:-1]:
            node = node["dirs"].setdefault(d, new())
        g = f.get("git") or {}
        flags = ("t" if f.get("test") else "") + ("b" if f.get("binary") else "")
        node["files"].append([
            parts[-1], f.get("lang") or "", int(f.get("lines") or 0), int(f.get("code") or 0),
            len(f.get("functions") or []), len(f.get("classes") or []),
            int(g.get("commits") or 0), g.get("last") or "", flags,
            -1 if f.get("binary") else index[shard_of[f["path"]]],
        ])

    def finish(name: str, node: dict) -> dict:
        n = {"files": len(node["files"]), "lines": 0, "code": 0, "functions": 0, "classes": 0}
        for r in node["files"]:
            n["lines"] += r[2]
            n["code"] += r[3]
            n["functions"] += r[4]
            n["classes"] += r[5]
        dirs = []
        for dname in sorted(node["dirs"]):
            d = finish(dname, node["dirs"][dname])
            dirs.append(d)
            for k in n:
                n[k] += d["n"][k]
        out = {"name": name, "n": n}
        if dirs:
            out["dirs"] = dirs
        if node["files"]:
            out["files"] = sorted(node["files"], key=lambda r: r[0])
        return out

    return finish("", top)


# ---------------------------------------------------------------------- imports
class ImportResolver:
    """Resolves the import statements the census recorded to repo paths. See the module docstring for the rules."""

    def __init__(self, files: list[dict]):
        self.all = {f["path"] for f in files if not f.get("binary")}
        self.tests = {f["path"] for f in files if f.get("test")}
        py = sorted(p for p in self.all if p.endswith(".py"))
        self.py = set(py)
        self.packages = {posixpath.dirname(p) for p in py if posixpath.basename(p) == "__init__.py"}
        self.suffix: dict[str, list[tuple[str, list[str]]]] = collections.defaultdict(list)
        for p in py:
            mod = p[:-3]
            if mod.endswith("/__init__"):
                mod = mod[:-9]
            parts = mod.split("/")
            for i in range(len(parts)):
                self.suffix[".".join(parts[i:])].append((p, parts[:i]))

    # ---- python
    def _prefix_ok(self, prefix_parts: list[str]) -> bool:
        d = ""
        for seg in prefix_parts:
            d = f"{d}/{seg}" if d else seg
            if d in self.packages:
                return False
        return True

    @staticmethod
    def _shared(a: str, b: str) -> int:
        n = 0
        for x, y in zip(a.split("/")[:-1], b.split("/")[:-1]):
            if x != y:
                break
            n += 1
        return n

    def lookup(self, importer: str, dotted: str) -> tuple[str | None, bool]:
        """(path, False) for one match, (None, True) for an ambiguous one, (None, False) for none."""
        cands = [p for p, prefix in self.suffix.get(dotted, ()) if self._prefix_ok(prefix)]
        if len(cands) <= 1:
            return (cands[0] if cands else None), False
        if importer not in self.tests:
            cands = [p for p in cands if p not in self.tests] or cands
        if len(cands) == 1:
            return cands[0], False
        ranked = sorted(cands, key=lambda p: (-self._shared(importer, p), p))
        if self._shared(importer, ranked[0]) == self._shared(importer, ranked[1]):
            return None, True
        return ranked[0], False

    def _module_file(self, base: str) -> str | None:
        for cand in (base + ".py", base + "/__init__.py"):
            if cand in self.py:
                return cand
        return None

    def python(self, importer: str, mod: str, level: int, names) -> tuple[list[str], str]:
        """(targets, status) with status internal | stdlib | external | ambiguous."""
        names = [n for n in (names or []) if n and n != "*"]
        targets: list[str] = []
        if level:
            pkg = posixpath.dirname(importer)
            for _ in range(level - 1):
                pkg = posixpath.dirname(pkg)
            base = posixpath.join(pkg, mod.replace(".", "/")) if mod else pkg
            hit = self._module_file(base) if mod else (base + "/__init__.py" if base + "/__init__.py" in self.py else None)
            if hit:
                targets.append(hit)
            for n in names:
                sub = self._module_file(posixpath.join(base, n))
                if sub and sub not in targets:
                    targets.append(sub)
            return targets, ("internal" if targets else "external")
        if not mod:
            return [], "external"
        if mod.split(".")[0] in STDLIB:
            return [], "stdlib"
        hit, ambiguous = self.lookup(importer, mod)
        if hit:
            targets.append(hit)
        for n in names:
            sub, _ = self.lookup(importer, f"{mod}.{n}")
            if sub and sub not in targets:
                targets.append(sub)
        if targets:
            return targets, "internal"
        return [], ("ambiguous" if ambiguous else "external")

    # ---- javascript
    def javascript(self, importer: str, spec: str) -> tuple[str | None, str]:
        """(target, status). Only relative specifiers are resolved; the repo uses no path aliases."""
        if not spec.startswith("."):
            if spec.startswith("node:") or spec.split("/")[0] in JS_BUILTINS:
                return None, "stdlib"
            return None, "external"
        base = posixpath.normpath(posixpath.join(posixpath.dirname(importer), spec))
        if base.startswith("..") or base == ".":
            return None, "external"
        if base in self.all:
            return base, "internal"
        for ext in JS_EXTS:
            if base + ext in self.all:
                return base + ext, "internal"
        for ext in JS_EXTS:
            if f"{base}/index{ext}" in self.all:
                return f"{base}/index{ext}", "internal"
        return None, "external"


def external_name(lang_ext: str, mod: str) -> str:
    """Top-level package a third-party import belongs to."""
    if lang_ext == "py":
        return mod.split(".")[0]
    parts = mod.split("/")
    return "/".join(parts[:2]) if mod.startswith("@") and len(parts) > 1 else parts[0]


def build_imports(census: dict, files: list[dict]) -> dict:
    res = ImportResolver(files)
    imports: dict[str, dict[str, int]] = {}
    external: dict[str, set[str]] = collections.defaultdict(set)
    stats = {"python": collections.Counter(), "javascript": collections.Counter()}
    for f in files:
        if f.get("binary"):
            continue
        ext = (f.get("ext") or f["path"].rsplit(".", 1)[-1]).lower()
        if ext == "py":
            lang = "python"
        elif ext in JS_LANG_EXTS:
            lang = "javascript"
        else:
            continue
        path = f["path"]
        edges = imports.setdefault(path, {})
        for imp in f.get("imports") or []:
            mod = imp.get("mod") or ""
            line = int(imp.get("line") or 0)
            if lang == "python":
                targets, status = res.python(path, mod, int(imp.get("level") or 0), imp.get("names"))
            else:
                t, status = res.javascript(path, mod)
                targets = [t] if t else []
            stats[lang][status] += 1
            for t in targets:
                if t != path and (t not in edges or line < edges[t]):
                    edges[t] = line
            if status in ("external", "ambiguous") and mod and not mod.startswith("."):
                external[path].add(external_name(ext, mod))
    forward = {p: sorted(([t, ln] for t, ln in e.items()), key=lambda r: (r[1], r[0])) for p, e in sorted(imports.items()) if e}
    reverse: dict[str, set[str]] = collections.defaultdict(set)
    for p, rows in forward.items():
        for t, _ in rows:
            reverse[t].add(p)
    return {
        "schema": SCHEMA,
        "commit": commit_of(census),
        "imports": forward,
        "imported_by": {t: sorted(v) for t, v in sorted(reverse.items())},
        "external": {p: sorted(v) for p, v in sorted(external.items()) if v},
        "stats": {lang: {k: c.get(k, 0) for k in ("internal", "external", "stdlib", "ambiguous")} for lang, c in stats.items()},
    }


# ---------------------------------------------------------------------- callers
def collect_callers(files: list[dict]) -> dict[str, list[str]]:
    """{called "path::qual": [calling "path::qual", ...]} from the resolved pairs of every function."""
    rev: dict[str, set[str]] = collections.defaultdict(set)
    for f in files:
        for fn in f.get("functions") or []:
            me = f"{f['path']}::{fn.get('qual') or fn.get('name')}"
            for pair in fn.get("calls") or []:
                target = pair[1] if isinstance(pair, (list, tuple)) and len(pair) > 1 else None
                if target and target != me:
                    rev[target].add(me)
    return {t: sorted(v) for t, v in sorted(rev.items())}


# ---------------------------------------------------------------------- build
def build(root: Path, census: dict | None = None) -> dict[str, str]:
    """Return {repo-relative output path: file text}. Pure: writes nothing."""
    root = Path(root)
    if census is None:
        census = load_json(root / "data" / "census.json", None)
    if census is None:
        print("warning: data/census.json not found: data/code will be empty", file=sys.stderr)
        census = {}
    files = census_files(census)
    code_files = [f for f in files if not f.get("binary")]
    records = {f["path"]: file_record(f) for f in code_files}
    sizes = {p: len(dumps(r).encode("utf-8")) for p, r in records.items()}
    shard_of = plan_shards(sizes, SHARD_LIMIT)       # read at call time so a test can lower it
    shards = sorted(set(shard_of.values()))
    meta = census.get("meta") or {}

    out: dict[str, str] = {}
    out[f"{CODE_DIR}/tree.json"] = dumps({
        "schema": SCHEMA,
        "commit": commit_of(census),
        "generated": str(meta.get("generated") or "")[:10],
        "script_version": int(meta.get("script_version") or 1),
        "file_fields": TREE_FIELDS,
        "shards": shards,
        "root": build_tree(files, shard_of, shards),
    })
    by_shard: dict[str, list[dict]] = collections.defaultdict(list)
    for p in sorted(records):
        by_shard[shard_of[p]].append(records[p])
    for sid in shards:
        out[f"{FILES_DIR}/{sid}.json"] = dumps({"schema": SCHEMA, "shard": sid, "files": by_shard[sid]})

    out[f"{CODE_DIR}/imports.json"] = dumps(build_imports(census, files))

    callers: dict[str, dict[str, list[str]]] = collections.defaultdict(dict)
    for target, who in collect_callers(code_files).items():
        sid = shard_of.get(target.split("::", 1)[0])
        if sid:
            callers[sid][target] = who
    for sid in sorted(callers):
        out[f"{CALLERS_DIR}/{sid}.json"] = dumps({"schema": SCHEMA, "shard": sid, "callers": callers[sid]})
    return out


def _orphans(root: Path, outputs: dict[str, str]) -> list[Path]:
    found: list[Path] = []
    for d in (FILES_DIR, CALLERS_DIR):
        folder = root / d
        if folder.is_dir():
            found += [p for p in sorted(folder.glob("*.json")) if f"{d}/{p.name}" not in outputs]
    return found


def write_all(root: Path = ROOT, census: dict | None = None) -> list[str]:
    """Write the files whose content changed and remove shards that no longer exist. Returns the changed paths."""
    root = Path(root)
    outputs = build(root, census)
    changed: list[str] = []
    for rel, text in sorted(outputs.items()):
        p = root / rel
        if p.exists() and read_lf(p) == text:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))      # always LF; git/autocrlf is free to convert
        changed.append(rel)
    for p in _orphans(root, outputs):
        p.unlink()
        changed.append(f"{p.relative_to(root).as_posix()} (removed)")
    return changed


def check_all(root: Path = ROOT, census: dict | None = None) -> list[str]:
    """Return a list of problems; empty means data/code on disk is current."""
    root = Path(root)
    outputs = build(root, census)
    problems: list[str] = []
    for rel, text in sorted(outputs.items()):
        p = root / rel
        if not p.exists():
            problems.append(f"missing: {rel}")
        elif read_lf(p) != text:
            problems.append(f"stale: {rel}")
    for p in _orphans(root, outputs):
        problems.append(f"unexpected: {p.relative_to(root).as_posix()}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="site root (default: repo root)")
    ap.add_argument("--check", action="store_true", help="exit 1 if data/code on disk is stale")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if args.check:
        problems = check_all(root)
        if problems:
            print("data/code is out of date:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            print("run: python scripts/build_code.py", file=sys.stderr)
            return 1
        print("data/code is current")
        return 0
    changed = write_all(root)
    print(f"data/code: {len(changed)} file(s) updated" if changed else "data/code: already current")
    for c in changed:
        print(f"  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
