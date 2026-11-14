#!/usr/bin/env python3
"""Build the Atlas search index (patch P03).

Standard library only. Output is deterministic (sorted keys, no timestamps), so
`--check` can compare it byte-for-byte (line endings are normalised on read).

Inputs
  content/nav.json         pages (wings -> items) and optional chapter order
  doc-*.html               chapter headings (h2/h3 that carry an id)
  content/glossary.json    optional; list of terms or {"terms": [...]}
  data/census.json         files, functions, classes, routes

Outputs (all under data/index/)
  search.json              {"pages": [...], "headings": [...], "terms": [...]}
  paths.json               {"paths": [...]}
  routes.json              {"routes": [{method, route, handler, file, line}]}
  symbols.json             manifest of the shards below
  symbols-<shard>.json     {"fields": [...], "rows": [[name, qual, path, line, kind]]}
                           sharded by top folder; a folder with more than
                           MAX_SHARD_ROWS rows is split by its second level

Usage
  python scripts/build_index.py            write the index
  python scripts/build_index.py --check    exit 1 if the files on disk are stale
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = "data/index"
MAX_SHARD_ROWS = 4000
SYMBOL_FIELDS = ["name", "qual", "path", "line", "kind"]
GLOSSARY_PAGE = "glossary.html"
LOCAL_URL_SKIP = ("http://", "https://", "#", "mailto:")


# --------------------------------------------------------------------------- io
def read_lf(path: Path) -> str:
    """Read UTF-8 text with LF line endings (CRLF-safe, BOM-safe)."""
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(read_lf(path))


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def slug(text, fallback: str = "root") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s or fallback


# ------------------------------------------------------------------ chapter html
class _Headings(HTMLParser):
    """Collect h2/h3 headings that carry an id, plus the first h1 and the <title>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str, str]] = []
        self.title = ""
        self.h1 = ""
        self._skip = 0
        self._cur: list | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = True
        elif tag in ("h1", "h2", "h3") and self._cur is None:
            self._cur = [tag, dict(attrs).get("id") or "", []]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav"):
            self._skip = max(0, self._skip - 1)
            return
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = " ".join("".join(self._title_parts).split())
        elif self._cur is not None and tag == self._cur[0]:
            tag_, hid, parts = self._cur
            self._cur = None
            text = " ".join("".join(parts).split())
            text = re.sub(r"\s*[#¶§]$", "", text)  # trailing permalink glyphs
            if tag_ == "h1":
                self.h1 = self.h1 or text
            elif hid and text:
                self.headings.append((int(tag_[1]), hid, text))

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self._title_parts.append(data)
        elif self._cur is not None:
            self._cur[2].append(data)


def parse_chapter(html: str) -> _Headings:
    p = _Headings()
    p.feed(html)
    p.close()
    return p


# ------------------------------------------------------------------------ nav
def _wing_list(v) -> list[dict]:
    if isinstance(v, dict):
        return [dict(w, id=w.get("id", k)) for k, w in v.items() if isinstance(w, dict)]
    return [w for w in (v or []) if isinstance(w, dict)]


def _keywords(v) -> list[str]:
    if isinstance(v, str):
        return [k for k in re.split(r"[,\s]+", v) if k]
    return [str(k) for k in (v or [])]


def collect_pages(nav: dict) -> list[dict]:
    pages: list[dict] = []
    seen: set[str] = set()

    def add(it: dict, wing: str) -> None:
        url, title = it.get("url"), it.get("title")
        if not url or not title or url.startswith(LOCAL_URL_SKIP) or url in seen:
            return
        seen.add(url)
        pages.append({
            "id": it.get("id") or slug(url),
            "title": title,
            "url": url,
            "wing": wing or it.get("wing") or "",
            "blurb": it.get("blurb") or "",
            "keywords": _keywords(it.get("keywords")),
        })

    for w in _wing_list(nav.get("wings")):
        wname = w.get("title") or w.get("id") or ""
        for it in w.get("items") or []:
            if isinstance(it, dict):
                add(it, wname)
    for it in nav.get("items") or []:
        if isinstance(it, dict):
            add(it, it.get("wing") or "")
    return pages


def collect_headings(root: Path, nav: dict) -> list[dict]:
    """Chapter headings. nav order first, then any doc-*.html not listed there."""
    order: list[tuple[str, str]] = []
    seen: set[str] = set()
    for c in nav.get("chapters") or []:
        if isinstance(c, dict) and c.get("url") and (root / c["url"]).is_file() and c["url"] not in seen:
            seen.add(c["url"])
            order.append((c["url"], c.get("title") or ""))
    for p in sorted(root.glob("doc-*.html")):
        if p.name not in seen:
            seen.add(p.name)
            order.append((p.name, ""))

    out: list[dict] = []
    for url, nav_title in order:
        parsed = parse_chapter(read_lf(root / url))
        title = nav_title or parsed.h1 or re.sub(r"\s*[·|-]\s*MiniMe Atlas\s*$", "", parsed.title) or url
        used: set[str] = set()
        for level, hid, text in parsed.headings:
            if hid in used:  # duplicate ids are a content bug; keep the first
                continue
            used.add(hid)
            out.append({
                "chapter": url,
                "chapterTitle": title,
                "level": level,
                "title": text,
                "url": f"{url}#{hid}",
            })
    return out


def collect_terms(root: Path) -> list[dict]:
    g = load_json(root / "content" / "glossary.json", None)
    if g is None:
        return []
    items = g.get("terms") if isinstance(g, dict) else g
    out, seen = [], set()
    for t in items or []:
        if not isinstance(t, dict) or not t.get("term"):
            continue
        url = f"{GLOSSARY_PAGE}#{slug(t['term'])}"
        if url in seen:
            continue
        seen.add(url)
        out.append({
            "term": t["term"],
            "aliases": [str(a) for a in (t.get("aliases") or [])],
            "category": t.get("category") or "",
            "short": t.get("short") or "",
            "url": url,
        })
    return sorted(out, key=lambda x: x["term"].lower())


# ---------------------------------------------------------------------- census
def _census_files(census: dict) -> list[dict]:
    files = census.get("files") or []
    if isinstance(files, dict):
        return [dict(v, path=k) for k, v in files.items() if isinstance(v, dict)]
    return [f for f in files if isinstance(f, dict)]


def _file_path(f: dict) -> str:
    return f.get("path") or f.get("file") or ""


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def collect_paths(census: dict) -> list[str]:
    return sorted({_file_path(f) for f in _census_files(census) if _file_path(f)})


def collect_symbols(census: dict) -> list[list]:
    rows: set[tuple] = set()

    def add(path: str, item, kind: str) -> None:
        if not path or not isinstance(item, dict):
            return
        name = item.get("name") or ""
        qual = item.get("qual") or name
        if not qual:
            return
        name = name or qual.rsplit(".", 1)[-1]
        rows.add((name, qual, path, _int(item.get("start") or item.get("line")), kind))

    for f in _census_files(census):
        p = _file_path(f)
        for fn in f.get("functions") or []:
            add(p, fn, "fn")
        for c in f.get("classes") or []:
            add(p, c, "cls")
    # alternative layout: flat top-level lists carrying their own file path
    for key, kind in (("functions", "fn"), ("classes", "cls")):
        flat = census.get(key)
        if isinstance(flat, list):
            for item in flat:
                if isinstance(item, dict):
                    add(item.get("file") or item.get("path") or "", item, kind)
    return sorted((list(r) for r in rows), key=lambda r: (r[2], r[3], r[1], r[0], r[4]))


def collect_routes(census: dict) -> list[dict]:
    out = []
    for r in census.get("routes") or []:
        if not isinstance(r, dict):
            continue
        method = r.get("method") or r.get("methods") or ""
        if isinstance(method, (list, tuple)):
            method = "|".join(str(m) for m in method)
        out.append({
            "method": str(method).upper(),
            "route": r.get("path") or r.get("route") or r.get("url") or r.get("endpoint") or "",
            "handler": r.get("handler") or r.get("func") or r.get("name") or "",
            "file": r.get("file") or "",
            "line": _int(r.get("line") or r.get("start")),
        })
    return sorted(out, key=lambda r: (r["route"], r["method"], r["file"], r["line"]))


def shard_symbols(rows: list[list]) -> dict[str, list[list]]:
    """Group by top folder; split oversized folders by their second level."""
    by_top: dict[str, list[list]] = defaultdict(list)
    for r in rows:
        parts = r[2].split("/")
        by_top[parts[0] if len(parts) > 1 else "_root"].append(r)

    shards: dict[str, list[list]] = {}
    for top, rs in by_top.items():
        if len(rs) <= MAX_SHARD_ROWS:
            shards.setdefault(slug(top), []).extend(rs)
            continue
        for r in rs:
            parts = r[2].split("/")
            second = parts[1] if len(parts) > 2 else "_files"
            shards.setdefault(f"{slug(top)}__{slug(second)}", []).append(r)
    for rs in shards.values():
        rs.sort(key=lambda r: (r[2], r[3], r[1], r[0], r[4]))
    return shards


# ----------------------------------------------------------------------- build
def build(root: Path, warn=None) -> dict[str, str]:
    """Return {repo-relative output path: file text}. Pure: writes nothing."""
    root = Path(root)
    warn = warn or (lambda m: print(f"warning: {m}", file=sys.stderr))

    nav = load_json(root / "content" / "nav.json", None)
    if nav is None:
        warn("content/nav.json not found: the pages list will be empty (run P02 first)")
        nav = {}
    census = load_json(root / "data" / "census.json", None)
    if census is None:
        warn("data/census.json not found: files, symbols and routes will be empty")
        census = {}

    out: dict[str, str] = {}
    out[f"{INDEX_DIR}/search.json"] = dumps({
        "pages": collect_pages(nav),
        "headings": collect_headings(root, nav),
        "terms": collect_terms(root),
    })
    out[f"{INDEX_DIR}/paths.json"] = dumps({"paths": collect_paths(census)})
    out[f"{INDEX_DIR}/routes.json"] = dumps({"routes": collect_routes(census)})

    shards = shard_symbols(collect_symbols(census))
    manifest = []
    for sid in sorted(shards):
        fname = f"symbols-{sid}.json"
        out[f"{INDEX_DIR}/{fname}"] = dumps({"fields": SYMBOL_FIELDS, "rows": shards[sid]})
        manifest.append({"id": sid, "file": fname, "count": len(shards[sid])})
    out[f"{INDEX_DIR}/symbols.json"] = dumps({"fields": SYMBOL_FIELDS, "shards": manifest})
    return out


def _stale_shards(root: Path, outputs: dict[str, str]) -> list[Path]:
    d = root / INDEX_DIR
    if not d.is_dir():
        return []
    return [p for p in sorted(d.glob("symbols-*.json")) if f"{INDEX_DIR}/{p.name}" not in outputs]


def write_all(root: Path = ROOT, warn=None) -> list[str]:
    """Write the index (only files whose content changed). Returns changed paths."""
    root = Path(root)
    outputs = build(root, warn)
    changed: list[str] = []
    for rel, text in sorted(outputs.items()):
        p = root / rel
        if p.exists() and read_lf(p) == text:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))  # always LF; git/autocrlf is free to convert
        changed.append(rel)
    for p in _stale_shards(root, outputs):
        p.unlink()
        changed.append(f"{INDEX_DIR}/{p.name} (removed)")
    return changed


def check_all(root: Path = ROOT, warn=None) -> list[str]:
    """Return a list of problems; empty means the index on disk is current."""
    root = Path(root)
    outputs = build(root, warn)
    problems: list[str] = []
    for rel, text in sorted(outputs.items()):
        p = root / rel
        if not p.exists():
            problems.append(f"missing: {rel}")
        elif read_lf(p) != text:
            problems.append(f"stale: {rel}")
    for p in _stale_shards(root, outputs):
        problems.append(f"unexpected: {INDEX_DIR}/{p.name}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="site root (default: repo root)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the index on disk is stale")
    args = ap.parse_args(argv)
    root = Path(args.root)

    if args.check:
        problems = check_all(root)
        if problems:
            print("search index is out of date:", file=sys.stderr)
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            print("run: python scripts/build_index.py", file=sys.stderr)
            return 1
        print("search index is current")
        return 0

    changed = write_all(root)
    print(f"search index: {len(changed)} file(s) updated" if changed else "search index: already current")
    for c in changed:
        print(f"  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
