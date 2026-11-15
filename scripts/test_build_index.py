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


def unpack(shard):
    """On-disk shard -> [[qual, path, line, kind]] (what palette.js's symbolItems() reads)."""
    return [[q, shard["files"][fi], line, kind] for q, fi, line, kind in shard["rows"]]


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
        shard = out["data/index/symbols-backend.json"]
        rows = unpack(shard)
        self.assertEqual(rows[0], ["Agent", "backend/agents/a.py", 10, "cls"])
        self.assertIn(["Agent.run", "backend/agents/a.py", 70, "fn"], rows)
        self.assertEqual(man["shards"][0]["count"], len(rows))
        self.assertEqual(man["fields"], bi.SYMBOL_FIELDS)
        self.assertEqual(man["fields"], ["qual", "file", "line", "kind"])

    def test_shard_lists_each_path_once(self):
        shard = self.built()["data/index/symbols-backend.json"]
        self.assertEqual(shard["files"], ["backend/agents/a.py", "backend/api/routes.py"])
        self.assertEqual(len(shard["rows"]), 4)  # Agent, _clean_query, Agent.run, health: four rows, two paths
        self.assertTrue(all(isinstance(r[1], int) for r in shard["rows"]))

    def test_short_name_is_not_stored(self):
        shard = self.built()["data/index/symbols-backend.json"]
        self.assertTrue(all(len(r) == 4 for r in shard["rows"]))
        self.assertIn("Agent.run", [r[0] for r in shard["rows"]])

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
        rows = unpack(self.built(census=census)["data/index/symbols-a.json"])
        self.assertEqual([r[2] for r in rows], [1, 9])

    def test_binary_files_are_not_in_paths(self):
        census = {"files": [{"path": "docs/logo.png", "binary": True}, {"path": "docs/a.md"}]}
        self.assertEqual(self.built(census=census)["data/index/paths.json"]["paths"], ["docs/a.md"])

    def test_census_argument_overrides_the_file_on_disk(self):
        fresh = {"files": [{"path": "new/only.py", "functions": [{"name": "f", "qual": "f", "start": 1}]}]}
        out = bi.build(self.root, self.warnings.append, census=fresh)
        self.assertEqual(json.loads(out["data/index/paths.json"])["paths"], ["new/only.py"])
        bi.write_all(self.root, self.warnings.append)             # the index for the census on disk ...
        self.assertTrue(bi.check_all(self.root, self.warnings.append, census=fresh))   # ... is stale for the fresh one
        bi.write_all(self.root, self.warnings.append, census=fresh)
        self.assertEqual(bi.check_all(self.root, self.warnings.append, census=fresh), [])

    def test_chapter_pages_get_label_and_part(self):
        nav = {"parts": {"strategy": "Part I · Strategy"},
               "wings": [{"id": "book", "title": "THE BOOK", "items": [
                   {"id": "a", "title": "Rulebook", "url": "doc-a.html", "chapter": 1, "part": "strategy"},
                   {"id": "m", "title": "Migration", "url": "doc-b.html", "chapter": "A", "part": "appendix"},
                   {"id": "o", "title": "Overview", "url": "index.html"}]}]}
        pages = {p["url"]: p for p in bi.collect_pages(nav)}
        self.assertEqual(pages["doc-a.html"]["label"], "Ch. 1 · Rulebook")
        self.assertEqual(pages["doc-a.html"]["part"], "Part I · Strategy")
        self.assertEqual(pages["doc-b.html"]["label"], "App. A · Migration")
        self.assertNotIn("part", pages["doc-b.html"])  # "appendix" is not in nav.parts
        self.assertNotIn("label", pages["index.html"])

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


BANNER_DOC = (
    '<html><head><title>Ch1</title></head><body><main><div class="bk-banner"><div class="bk-top"><div>'
    '<span class="bk-part">Part I</span><span class="bk-ch">Chapter 1 of 14</span></div>'
    '<div class="bk-actions"><a href="docs.html" class="bk-pill-link">All</a>'
    '<a href="journey.html#doc-one" class="bk-pill-link">Journey</a>'
    '<a href="data/docs/one.md" download class="bk-pill-link">md</a></div></div>'
    '<p class="bk-desc">The money &amp; model <em>constitution</em>.</p>'
    '<div class="bk-meta"><span><b>27,349</b> words (~124 min read)</span><span>&middot;</span><span><b>135</b> sections</span>'
    '<span>&middot;</span><span><b>90</b> tables</span></div>'
    '<div class="bk-prevnext"><a href="doc-two.html">Next</a></div></div>'
    '<div class="doc"><article><h1 id="t">One</h1><h2 id="a">A</h2></article></div></main>'
    '<small class="mm-built">Private. Built 2026-10-07 from commit febb685.</small></body></html>'
)
SPEC_DOC = (
    '<html><body><main><div class="bk-banner"><div class="bk-top"><span class="bk-part">Part III</span><span class="bk-ch">Chapter 2 of 14</span>'
    '<div class="bk-actions"><a href="guides/Spec.html" target="_blank">Open standalone</a></div></div>'
    '<p class="bk-desc">Design note.</p><div class="bk-meta"><span><b>Interactive HTML Spec</b> &middot; Synchronized</span></div></div>'
    '<div class="doc"><article><h1>Spec</h1></article></div></main></body></html>'
)
APP_DOC = BANNER_DOC.replace("27,349", "1,000").replace("~124", "~5").replace("Built 2026-10-07 from commit febb685", "Added 2026-11-14 on commit aaca7f1")
BOOK_NAV = {
    "parts": {"strategy": "Part I", "m2c": "Part III", "appendix": "Appendix", "empty": "Unused part"},
    "wings": [{"id": "book", "title": "THE BOOK", "items": [
        {"id": "docs", "title": "Library", "url": "docs.html"},
        {"id": "doc-one", "title": "One", "url": "doc-one.html", "part": "strategy", "chapter": 1, "blurb": "Short blurb"},
        {"id": "doc-spec", "title": "Spec", "url": "doc-spec.html", "part": "m2c", "chapter": 2},
        {"id": "doc-app", "title": "Appendix thing", "url": "doc-app.html", "part": "appendix", "chapter": "A"},
        {"id": "doc-gone", "title": "Gone", "url": "doc-gone.html", "part": "m2c", "chapter": 3},
    ]}],
}


class BookTests(unittest.TestCase):
    """data/index/book.json (P05): one row per chapter, read from the chapter's own banner."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "content").mkdir()
        (self.root / "content" / "nav.json").write_text(json.dumps(BOOK_NAV), encoding="utf-8")
        (self.root / "doc-one.html").write_bytes(BANNER_DOC.replace("><", ">\r\n<").encode("utf-8"))   # CRLF on purpose
        (self.root / "doc-spec.html").write_text(SPEC_DOC, encoding="utf-8")
        (self.root / "doc-app.html").write_text(APP_DOC, encoding="utf-8")
        self.warnings: list[str] = []
        self.book = json.loads(bi.build(self.root, self.warnings.append, census={})["data/index/book.json"])

    def tearDown(self):
        self._tmp.cleanup()

    def row(self, cid):
        return next(c for c in self.book["chapters"] if c["id"] == cid)

    def test_counts_and_text_come_from_the_banner(self):
        c = self.row("doc-one")
        self.assertEqual((c["words"], c["minutes"], c["sections"], c["tables"]), (27349, 124, 135, 90))
        self.assertEqual(c["desc"], "The money & model constitution.")
        self.assertEqual((c["label"], c["partTitle"], c["blurb"]), ("Ch. 1", "Part I", "Short blurb"))

    def test_built_stamp_download_and_journey_links(self):
        c = self.row("doc-one")
        self.assertEqual((c["built"], c["commit"]), ("2026-10-07", "febb685"))
        self.assertEqual((c["md"], c["journey"]), ("data/docs/one.md", "journey.html#doc-one"))
        a = self.row("doc-app")
        self.assertEqual((a["built"], a["commit"], a["label"]), ("2026-11-14", "aaca7f1", "App. A"))   # "Added ... on commit ..." is read too

    def test_a_chapter_without_counts_has_none_not_zero(self):
        c = self.row("doc-spec")
        self.assertEqual((c["words"], c["minutes"], c["sections"], c["tables"]), (None, None, None, None))
        self.assertIn("Interactive HTML Spec", c["meta"])
        self.assertEqual(c["standalone"], "guides/Spec.html")
        self.assertEqual(c["built"], "")

    def test_only_chapter_items_in_nav_order_and_a_missing_file_warns(self):
        self.assertEqual([c["id"] for c in self.book["chapters"]], ["doc-one", "doc-spec", "doc-app"])   # docs.html is not a chapter
        self.assertTrue(any("doc-gone.html" in w for w in self.warnings))

    def test_parts_follow_nav_and_empty_parts_are_dropped(self):
        self.assertEqual([(p["id"], p["chapters"]) for p in self.book["parts"]],
                         [("strategy", ["doc-one"]), ("m2c", ["doc-spec"]), ("appendix", ["doc-app"])])

    def test_totals_skip_chapters_without_counts(self):
        t = self.book["totals"]
        self.assertEqual((t["chapters"], t["appendices"], t["withCounts"]), (2, 1, 2))
        self.assertEqual((t["words"], t["minutes"], t["sections"], t["tables"]), (28349, 129, 270, 180))

    def test_banner_in_the_page_body_is_not_confused_by_later_markup(self):
        facts = bi.parse_banner('<div class="bk-banner"><p class="bk-desc">First</p></div><p class="bk-desc">Second</p>')
        self.assertEqual(facts["desc"], "First")
        self.assertEqual(bi.parse_banner("<p>no banner</p>")["desc"], "")

    def test_book_json_is_part_of_check(self):
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / "census.json").write_text("{}", encoding="utf-8")
        bi.write_all(self.root, lambda m: None)
        self.assertTrue((self.root / "data" / "index" / "book.json").is_file())
        self.assertEqual(bi.check_all(self.root, lambda m: None), [])
        (self.root / "doc-one.html").write_text(BANNER_DOC.replace("27,349", "30,000"), encoding="utf-8")
        self.assertIn("stale: data/index/book.json", bi.check_all(self.root, lambda m: None))


if __name__ == "__main__":
    unittest.main()
