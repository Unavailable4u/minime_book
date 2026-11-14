#!/usr/bin/env python3
"""Unit tests for scripts/build_index.py (patch P03). Run: python scripts/test_build_index.py"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_index as bi  # noqa: E402

NAV = {
    "wings": [
        {"id": "start", "title": "START HERE", "items": [
            {"id": "overview", "title": "Overview", "url": "index.html",
             "blurb": "The tour", "keywords": ["home", "readme"]},
            {"id": "ext", "title": "External", "url": "https://example.com"},
        ]},
        {"id": "book", "title": "THE BOOK", "items": [
            {"id": "docs", "title": "Book library", "url": "docs.html", "keywords": "chapters, read"},
        ]},
    ],
    "chapters": [
        {"id": "ch-a", "title": "Chapter A: Strategy", "url": "doc-a.html"},
        {"id": "ch-gone", "title": "Missing file", "url": "doc-gone.html"},
    ],
}

DOC_A = (
    "<html><head><title>Doc A · MiniMe Atlas</title></head><body>"
    "<nav><h2 id='nav-h'>Sidebar</h2></nav>"
    "<main><h1 id='t'>Title</h1>"
    "<h2 id='intro'>Intro <a href='#intro'>#</a></h2>"
    "<h2>No id here</h2>"
    "<h3 id='deep'>Deep <code>dive</code></h3>"
    "<h4 id='h4'>Ignored level</h4>"
    "<script>var s = '<h2 id=\"x\">fake</h2>';</script>"
    "<h2 id='intro'>Duplicate id</h2>"
    "</main></body></html>"
)
DOC_B = "<html><head><title>Rulebook · MiniMe Atlas</title></head><body><h1>The Rulebook</h1><h2 id='r1'>Rule one</h2></body></html>"

CENSUS = {
    "files": [
        {"path": "backend/agents/a.py", "functions": [
            {"name": "_clean_query", "qual": "_clean_query", "start": 58},
            {"name": "run", "qual": "Agent.run", "start": 70}], "classes": [{"name": "Agent", "qual": "Agent", "start": 10}]},
        {"path": "backend/api/routes.py", "functions": [{"name": "health", "qual": "health", "start": 5}]},
        {"path": "frontend/app/Foo.jsx", "functions": [{"name": "Foo", "qual": "Foo", "start": 1}]},
        {"path": "setup.py", "functions": []},
    ],
    "routes": [
        {"method": "GET", "path": "/health", "handler": "health", "file": "backend/api/routes.py", "line": 5},
        {"methods": ["POST", "PUT"], "path": "/a", "handler": "run", "file": "backend/agents/a.py", "line": 70},
    ],
}


def make_site(root: Path, nav=NAV, census=CENSUS, glossary=None) -> None:
    (root / "content").mkdir(parents=True, exist_ok=True)
    (root / "data").mkdir(parents=True, exist_ok=True)
    if nav is not None:
        (root / "content" / "nav.json").write_text(json.dumps(nav), encoding="utf-8")
    if census is not None:
        (root / "data" / "census.json").write_text(json.dumps(census), encoding="utf-8")
    (root / "doc-a.html").write_bytes(DOC_A.replace("><", ">\r\n<").encode("utf-8"))  # CRLF on purpose
    (root / "doc-b.html").write_text(DOC_B, encoding="utf-8")
    if glossary is not None:
        (root / "content" / "glossary.json").write_text(json.dumps(glossary), encoding="utf-8")


class BuildIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.warnings: list[str] = []

    def tearDown(self):
        self._tmp.cleanup()

    def built(self, **kw):
        make_site(self.root, **kw)
        out = bi.build(self.root, self.warnings.append)
        return {k: json.loads(v) for k, v in out.items()}

    def test_pages_from_nav(self):
        pages = self.built()["data/index/search.json"]["pages"]
        self.assertEqual([p["url"] for p in pages], ["index.html", "docs.html"])  # external skipped, order kept
        self.assertEqual(pages[0]["wing"], "START HERE")
        self.assertEqual(pages[0]["keywords"], ["home", "readme"])
        self.assertEqual(pages[1]["keywords"], ["chapters", "read"])

    def test_wings_as_dict_and_flat_items(self):
        nav = {"wings": {"w1": {"title": "W1", "items": [{"id": "a", "title": "A", "url": "a.html"}]}},
               "items": [{"id": "b", "title": "B", "url": "b.html", "wing": "W2"}]}
        pages = self.built(nav=nav)["data/index/search.json"]["pages"]
        self.assertEqual([(p["url"], p["wing"]) for p in pages], [("a.html", "W1"), ("b.html", "W2")])

    def test_headings(self):
        heads = self.built()["data/index/search.json"]["headings"]
        a = [h for h in heads if h["chapter"] == "doc-a.html"]
        self.assertEqual([(h["level"], h["title"], h["url"]) for h in a],
                         [(2, "Intro", "doc-a.html#intro"), (3, "Deep dive", "doc-a.html#deep")])
        self.assertTrue(all(h["chapterTitle"] == "Chapter A: Strategy" for h in a))

    def test_unlisted_chapter_is_picked_up_with_h1_title(self):
        heads = self.built()["data/index/search.json"]["headings"]
        b = [h for h in heads if h["chapter"] == "doc-b.html"]
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["chapterTitle"], "The Rulebook")
        self.assertEqual([h["chapter"] for h in heads][-1], "doc-b.html")  # nav chapters first

    def test_terms(self):
        gl = {"terms": [{"term": "Golden Rule", "aliases": ["GR"], "short": "s", "category": "c"},
                        {"term": "agent module", "short": "x"}, {"nope": 1}]}
        terms = self.built(glossary=gl)["data/index/search.json"]["terms"]
        self.assertEqual([t["term"] for t in terms], ["agent module", "Golden Rule"])
        self.assertEqual(terms[1]["url"], "glossary.html#golden-rule")

    def test_no_glossary_gives_empty_terms(self):
        self.assertEqual(self.built()["data/index/search.json"]["terms"], [])

    def test_paths_and_routes(self):
        out = self.built()
        self.assertEqual(out["data/index/paths.json"]["paths"],
                         ["backend/agents/a.py", "backend/api/routes.py", "frontend/app/Foo.jsx", "setup.py"])
        routes = out["data/index/routes.json"]["routes"]
        self.assertEqual([(r["method"], r["route"]) for r in routes], [("POST|PUT", "/a"), ("GET", "/health")])
        self.assertEqual(routes[1]["line"], 5)

    def test_symbols_sharded_by_top_folder(self):
        out = self.built()
        man = out["data/index/symbols.json"]
        self.assertEqual([s["id"] for s in man["shards"]], ["backend", "frontend"])
        rows = out["data/index/symbols-backend.json"]["rows"]
        self.assertEqual(rows[0], ["Agent", "Agent", "backend/agents/a.py", 10, "cls"])
        self.assertIn(["run", "Agent.run", "backend/agents/a.py", 70, "fn"], rows)
        self.assertEqual(man["shards"][0]["count"], len(rows))
        self.assertEqual(man["fields"], bi.SYMBOL_FIELDS)

    def test_root_level_files_go_to_root_shard(self):
        census = {"files": [{"path": "setup.py", "functions": [{"name": "main", "qual": "main", "start": 3}]}]}
        out = self.built(census=census)
        self.assertEqual([s["id"] for s in out["data/index/symbols.json"]["shards"]], ["root"])

    def test_oversized_folder_is_split_by_second_level(self):
        old = bi.MAX_SHARD_ROWS
        bi.MAX_SHARD_ROWS = 2
        try:
            out = self.built()
        finally:
            bi.MAX_SHARD_ROWS = old
        ids = [s["id"] for s in out["data/index/symbols.json"]["shards"]]
        self.assertEqual(ids, ["backend__agents", "backend__api", "frontend"])

    def test_duplicate_quals_are_kept(self):
        census = {"files": [{"path": "a/b.py", "functions": [
            {"name": "x", "qual": "C.x", "start": 1}, {"name": "x", "qual": "C.x", "start": 9}]}]}
        rows = self.built(census=census)["data/index/symbols-a.json"]["rows"]
        self.assertEqual([r[3] for r in rows], [1, 9])

    def test_deterministic_and_no_timestamps(self):
        make_site(self.root)
        a = bi.build(self.root, self.warnings.append)
        b = bi.build(self.root, self.warnings.append)
        self.assertEqual(a, b)
        self.assertNotRegex("".join(a.values()), r"20\d\d-\d\d-\d\d")

    def test_missing_inputs_warn_instead_of_crash(self):
        make_site(self.root, nav=None, census=None)
        out = bi.build(self.root, self.warnings.append)
        self.assertEqual(len(self.warnings), 2)
        self.assertEqual(json.loads(out["data/index/paths.json"])["paths"], [])
        self.assertEqual(json.loads(out["data/index/symbols.json"])["shards"], [])

    def test_write_then_check_then_stale(self):
        make_site(self.root)
        self.assertTrue(bi.check_all(self.root, self.warnings.append))  # nothing written yet
        changed = bi.write_all(self.root, self.warnings.append)
        self.assertTrue(changed)
        self.assertEqual(bi.check_all(self.root, self.warnings.append), [])
        self.assertEqual(bi.write_all(self.root, self.warnings.append), [])  # idempotent
        # a chapter gains a heading -> stale
        doc = self.root / "doc-b.html"
        doc.write_text(doc.read_text(encoding="utf-8").replace("</body>", "<h2 id='r2'>Two</h2></body>"), encoding="utf-8")
        problems = bi.check_all(self.root, self.warnings.append)
        self.assertEqual(problems, ["stale: data/index/search.json"])

    def test_check_tolerates_crlf_on_disk(self):
        make_site(self.root)
        bi.write_all(self.root, self.warnings.append)
        for p in (self.root / "data" / "index").glob("*.json"):
            p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(bi.check_all(self.root, self.warnings.append), [])

    def test_orphan_shard_is_removed_and_reported(self):
        make_site(self.root)
        bi.write_all(self.root, self.warnings.append)
        orphan = self.root / "data" / "index" / "symbols-gone.json"
        orphan.write_text("{}", encoding="utf-8")
        self.assertEqual(bi.check_all(self.root, self.warnings.append), ["unexpected: data/index/symbols-gone.json"])
        bi.write_all(self.root, self.warnings.append)
        self.assertFalse(orphan.exists())

    def test_main_exit_codes(self):
        make_site(self.root)
        self.assertEqual(bi.main(["--root", str(self.root), "--check"]), 1)
        self.assertEqual(bi.main(["--root", str(self.root)]), 0)
        self.assertEqual(bi.main(["--root", str(self.root), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
