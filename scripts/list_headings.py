#!/usr/bin/env python3
"""Print the headings of a book chapter with their ids (patch P04).

Later patches place figures, glossary links and callouts "after heading X", and they need the real heading ids.
This lists them straight from the chapter HTML, the same headings assets/js/reader.js sees at run time
(h1-h4 inside <article>, the footer cards excluded).

    python scripts/list_headings.py doc-minime-feature-guide          # a chapter id, or a file name
    python scripts/list_headings.py doc-rulebook --max-level 2        # only h1 and h2
    python scripts/list_headings.py doc-minime-feature-guide --grep sandbox
    python scripts/list_headings.py doc-fbebc-phase1 --json           # for other scripts
    python scripts/list_headings.py --all --missing                   # headings that have no id of their own

A heading without an id is shown with the id reader.js will give it (marked `*`). Existing ids are never changed.
The slug rule is the same as slugify() in reader.js. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^h[1-4]$")


def slugify(text: str, limit: int = 40) -> str:
    """Same recipe as slugify() in assets/js/reader.js."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+$", "", s[:limit]) or "section"


def unique_id(base: str, taken: set[str]) -> str:
    out, n = base, 2
    while out in taken:
        out, n = f"{base}-{n}", n + 1
    taken.add(out)
    return out


class _Scan(HTMLParser):
    """Collects every id on the page and the headings inside <article> (outside .bk-footer)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.heads: list[dict] = []
        self._article = 0
        self._footer: list[int] = []     # depth at which a .bk-footer opened
        self._depth = 0
        self._cur: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag not in ("br", "img", "hr", "input", "meta", "link"):
            self._depth += 1
        if tag == "article":
            self._article += 1
        if "bk-footer" in (a.get("class") or "").split():
            self._footer.append(self._depth)
        if self._article and not self._footer and HEADING.match(tag):
            self._cur = {"level": int(tag[1]), "id": a.get("id") or "", "text": ""}

    def handle_endtag(self, tag):
        if self._cur is not None and HEADING.match(tag):
            text = re.sub(r"\s+", " ", self._cur["text"]).strip()
            if text:
                self._cur["text"] = text
                self.heads.append(self._cur)
            self._cur = None
        if tag == "article" and self._article:
            self._article -= 1
        if self._footer and self._depth == self._footer[-1]:
            self._footer.pop()
        if tag not in ("br", "img", "hr", "input", "meta", "link"):
            self._depth -= 1

    def handle_data(self, data):
        if self._cur is not None:
            self._cur["text"] += data


def headings(path: Path) -> list[dict]:
    """[{level, id, text, own}] in document order; `own` is False when the id was made up (slug)."""
    scan = _Scan()
    scan.feed(path.read_text(encoding="utf-8"))
    taken = set(scan.ids)
    out = []
    for h in scan.heads:
        own = bool(h["id"])
        out.append({"level": h["level"], "id": h["id"] or unique_id(slugify(h["text"]), taken), "text": h["text"], "own": own})
    return out


def resolve(name: str) -> Path:
    n = name[:-5] if name.endswith(".html") else name
    p = ROOT / f"{n}.html"
    if not p.exists() and not n.startswith("doc-"):
        p = ROOT / f"doc-{n}.html"
    if not p.exists():
        sys.exit(f"No chapter page found for {name!r} (looked for {n}.html in {ROOT}).")
    return p


def chapter_files() -> list[Path]:
    nav = json.loads((ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
    files = []
    for w in nav.get("wings", []):
        for it in w.get("items", []):
            if it.get("chapter") is not None and (ROOT / it["url"]).exists():
                files.append(ROOT / it["url"])
    return files


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows pipes default to cp1252, which cannot print every heading
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("chapter", nargs="?", help="chapter id (doc-rulebook) or file name; omit with --all")
    ap.add_argument("--all", action="store_true", help="every chapter listed in content/nav.json")
    ap.add_argument("--min-level", type=int, default=1)
    ap.add_argument("--max-level", type=int, default=4)
    ap.add_argument("--grep", help="only headings whose text contains this (case-insensitive)")
    ap.add_argument("--missing", action="store_true", help="only headings that have no id in the HTML")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.all == bool(args.chapter):
        ap.error("give a chapter, or --all")
    files = chapter_files() if args.all else [resolve(args.chapter)]

    result = {}
    for f in files:
        rows = [h for h in headings(f) if args.min_level <= h["level"] <= args.max_level]
        if args.grep:
            rows = [h for h in rows if args.grep.lower() in h["text"].lower()]
        if args.missing:
            rows = [h for h in rows if not h["own"]]
        result[f.stem] = rows

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    for stem, rows in result.items():
        if args.all:
            print(f"== {stem}  ({len(rows)} headings)")
        for h in rows:
            print(f"{'  ' * (h['level'] - 1)}h{h['level']}  #{h['id']}{'' if h['own'] else ' *'}  {h['text']}")
        if args.all:
            print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:          # `... | head`: the reader went away, that is fine
        sys.stderr.close()
        raise SystemExit(0)
