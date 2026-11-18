#!/usr/bin/env python3
"""Tests for scripts/chapter_links.py (patch P15) and its wiring in build_index.py. Run: python scripts/test_chapter_links.py

The first half uses a small synthetic census and chapters, so every resolution rule is pinned down by an example.
The second half checks the real repository: the files under data/index/ are current, every link points at something in the census,
and every chapter section a mention names exists in that chapter."""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build_index as bi  # noqa: E402
import chapter_links as cl  # noqa: E402

PATHS = [
    "backend/api/deps.py", "backend/agents/search.py", "backend/tests/unit/test_search.py", "frontend/app/hooks/useDaemonStatus.js",
    "m2c/src/m2c/tui/app.py", "daemon/server.py", "backend/utils/log.py", "backend/eo/log.py", "README.md", "backend/.env.example", "daemon/.env.example",
]
SYMBOLS = [                                   # [qual, path, line, kind], like build_index.collect_symbols()
    ["get_current_user", "backend/api/deps.py", 10, "fn"],
    ["clean_query", "backend/agents/search.py", 5, "fn"],
    ["SearchAgent", "backend/agents/search.py", 20, "cls"],
    ["SearchAgent.run", "backend/agents/search.py", 30, "fn"],
    ["test_clean_query", "backend/tests/unit/test_search.py", 3, "fn"],
    ["clean_query", "backend/tests/unit/test_search.py", 40, "fn"],          # same name, but in a test file
    ["useDaemonStatus", "frontend/app/hooks/useDaemonStatus.js", 1, "fn"],
    ["App", "m2c/src/m2c/tui/app.py", 2, "cls"],
    ["serve_forever", "daemon/server.py", 7, "fn"],
    ["serve_forever", "backend/utils/log.py", 9, "fn"],                      # two source files share this name
    ["rotate_logs", "backend/utils/log.py", 3, "fn"],
    ["rotate_logs", "backend/eo/log.py", 4, "fn"],
    ["__init__", "backend/api/deps.py", 1, "fn"],
]


def ch(url: str, body: str, title: str = "T") -> dict:
    return {"url": url, "title": title, "html": f"<html><body><nav><code>backend/api/deps.py</code></nav><main>{body}</main></body></html>"}


def collect(chapters, aliases=None):
    return cl.collect_links(chapters, PATHS, SYMBOLS, aliases)


def resolve(text, aliases=None):
    ix = cl.Index(PATHS, SYMBOLS)
    return cl.resolve(text, ix, cl.load_aliases(aliases, ix)[0])


class Resolve(unittest.TestCase):
    def test_exact_path_and_lines(self):
        self.assertEqual(resolve("backend/api/deps.py"), ("link", "backend/api/deps.py"))
        self.assertEqual(resolve("backend/api/deps.py:12"), ("link", "backend/api/deps.py@12"))
        self.assertEqual(resolve("backend/api/deps.py:12-20"), ("link", "backend/api/deps.py@12-20"))
        self.assertEqual(resolve("backend/api/deps.py#L12-L20"), ("link", "backend/api/deps.py@12-20"))
        self.assertEqual(resolve("backend/api/deps.py:20-12"), ("link", "backend/api/deps.py@20"))       # a backwards range is a single line
        self.assertEqual(resolve("./README.md"), ("link", "README.md"))

    def test_folders(self):
        self.assertEqual(resolve("backend/api/"), ("link", "backend/api/"))
        self.assertEqual(resolve("backend/api"), ("link", "backend/api/"))        # a path that is not a file but is a folder
        self.assertEqual(resolve("backend"), ("none", ""))                          # a bare word is looked up as a name, never as a folder
        self.assertEqual(resolve("m2c/src/"), ("link", "m2c/src/"))

    def test_unique_suffix_and_choices(self):
        self.assertEqual(resolve("m2c/tui/app.py"), ("link", "m2c/src/m2c/tui/app.py"))     # a suffix of the path, folder names included
        self.assertEqual(resolve("src/tui/app.py")[0], "none")                              # not a suffix: the folders must be next to each other
        self.assertEqual(resolve("deps.py:12-20"), ("link", "backend/api/deps.py@12-20"))   # lines work without a folder in front, too
        self.assertEqual(resolve("tui/app.py"), ("link", "m2c/src/m2c/tui/app.py"))
        self.assertEqual(resolve("deps.py"), ("link", "backend/api/deps.py"))
        kind, val = resolve(".env.example")
        self.assertEqual((kind, val), ("choices", ["backend/.env.example", "daemon/.env.example"]))
        kind, val = resolve("log.py")
        self.assertEqual(kind, "choices")
        self.assertEqual(len(val), 2)

    def test_qualified(self):
        self.assertEqual(resolve("backend/agents/search.py::SearchAgent.run"), ("link", "backend/agents/search.py::SearchAgent.run"))
        self.assertEqual(resolve("search.py::SearchAgent"), ("link", "backend/agents/search.py::SearchAgent"))
        self.assertEqual(resolve("search.py::Nope"), ("none", ""))

    def test_names(self):
        self.assertEqual(resolve("get_current_user"), ("link", "backend/api/deps.py::get_current_user"))
        self.assertEqual(resolve("get_current_user()"), ("link", "backend/api/deps.py::get_current_user"))
        self.assertEqual(resolve("SearchAgent.run"), ("link", "backend/agents/search.py::SearchAgent.run"))
        self.assertEqual(resolve("clean_query"), ("link", "backend/agents/search.py::clean_query"))       # the test-file twin is ignored
        kind, val = resolve("serve_forever")
        self.assertEqual(kind, "name")                                                                       # two source files: the section decides
        self.assertEqual(sorted(val), [("backend/utils/log.py", "serve_forever"), ("daemon/server.py", "serve_forever")])

    def test_never_linked(self):
        for text in ("run", "main", "True", "id", "__init__", "self", "agent", "two words", "x = 1", "", "   ", "a.b.c.d.e", "$HOME", "GET /api/x"):
            self.assertIn(resolve(text)[0], ("skip", "none"), text)
        self.assertEqual(resolve("__init__")[0], "skip")
        self.assertEqual(resolve("memory")[0], "skip")

    def test_aliases(self):
        al = {"aliases": {"the stage router": "backend/agents/search.py::SearchAgent", "_note": "ignored", "Gone": "backend/nope.py", "Dir": "backend/api/"}}
        self.assertEqual(resolve("The Stage Router", al), ("link", "backend/agents/search.py::SearchAgent"))      # case-insensitive, spaces allowed
        self.assertEqual(resolve("Dir", al), ("link", "backend/api/"))
        self.assertNotEqual(resolve("Gone", al)[0], "link")
        _, problems = cl.load_aliases(al, cl.Index(PATHS, SYMBOLS))
        self.assertEqual(len(problems), 1)
        self.assertIn("backend/nope.py", problems[0])
        self.assertEqual(cl.load_aliases(None, cl.Index(PATHS, SYMBOLS)), ({}, []))
        self.assertEqual(cl.load_aliases({"x y": "README.md"}, cl.Index(PATHS, SYMBOLS))[0], {"x y": "README.md"})   # the bare map works too


class Spans(unittest.TestCase):
    def test_only_code_outside_pre_nav_and_script(self):
        html = ("<nav><code>nav_code</code></nav><main><h2 id='a'>A <code>head</code></h2><p>Use <code>deps.py</code> and "
                "<code><b>clean_query</b></code>.</p><pre><code>in_pre</code></pre><script>var x='<code>js</code>'</script>"
                "<h3 id='b'>B</h3><ul><li><code> spaced </code></li></ul></main>")
        p = cl.parse_spans(html)
        self.assertEqual([(s["text"], s["section"]) for s in p.spans], [("head", "a"), ("deps.py", "a"), ("clean_query", "a"), ("spaced", "b")])
        self.assertEqual(p.heading_text, {"a": "A head", "b": "B"})

    def test_snippet_is_the_block_around_the_span(self):
        p = cl.parse_spans("<main><h2 id='s'>S</h2><p>First sentence. We call <code>deps.py</code> here.</p><p>Other block.</p></main>")
        self.assertIn("We call deps.py here", p.spans[0]["snippet"])
        self.assertNotIn("Other block", p.spans[0]["snippet"])

    def test_long_blocks_are_cut_with_ellipses(self):
        p = cl.parse_spans(f"<main><p>{'word ' * 80}<code>deps.py</code>{' word' * 80}</p></main>")
        s = p.spans[0]["snippet"]
        self.assertTrue(s.startswith("…") and s.endswith("…"))
        self.assertLessEqual(len(s), cl.SNIPPET + 2)
        self.assertIn("deps.py", s)

    def test_span_before_any_heading_has_no_section(self):
        self.assertEqual(cl.parse_spans("<main><p><code>deps.py</code></p></main>").spans[0]["section"], "")

    def test_nested_and_unclosed_markup_does_not_raise(self):
        cl.parse_spans("<main><p><code>a<code>b</code>c</p><pre><code>x</main>")


class Collect(unittest.TestCase):
    def setUp(self):
        self.body = ("<h2 id='one'>One</h2><p>See <code>backend/api/deps.py</code> and <code>get_current_user</code>.</p>"
                     "<h2 id='two'>Two</h2><p><code>backend/utils/log.py</code> defines <code>serve_forever</code>; "
                     "<code>get_current_user()</code> again and <code>mystery_thing</code>, <code>run</code>.</p>"
                     "<h2 id='three'>Three</h2><p>Only <code>serve_forever</code> here, and <code>.env.example</code>.</p>")
        self.out = collect([ch("doc-a.html", self.body, "Chapter A")])

    def test_links_choices_and_sections(self):
        lk = self.out["linkables"]
        self.assertEqual(lk["links"]["backend/api/deps.py"], "backend/api/deps.py")
        self.assertEqual(lk["links"]["get_current_user"], "backend/api/deps.py::get_current_user")
        self.assertEqual(lk["links"]["get_current_user()"], "backend/api/deps.py::get_current_user")
        self.assertEqual(lk["sections"], {"doc-a.html#two": {"serve_forever": "backend/utils/log.py::serve_forever"}})   # named log.py in the section
        self.assertEqual(sorted(lk["choices"]), [".env.example", "serve_forever"])                                       # section three names nothing: a choice
        self.assertNotIn("mystery_thing", lk["links"])
        self.assertNotIn("run", lk["links"])

    def test_a_text_with_two_answers_becomes_a_choice_everywhere(self):
        a = ch("doc-a.html", "<h2 id='s'>S</h2><p><code>deps.py</code></p>")
        paths = PATHS + ["other/deps.py"]
        out = cl.collect_links([a], paths, SYMBOLS)
        self.assertNotIn("deps.py", out["linkables"]["links"])
        self.assertEqual(out["linkables"]["choices"]["deps.py"], ["backend/api/deps.py", "other/deps.py"])

    def test_mentions(self):
        m = self.out["mentions"]
        self.assertEqual(m["chapters"], [{"url": "doc-a.html", "title": "Chapter A"}])
        deps = m["mentions"]["backend/api/deps.py"]
        self.assertEqual([(x["c"], x["id"], x["h"], x["n"]) for x in deps], [(0, "one", "One", 1)])
        sym = m["mentions"]["backend/api/deps.py::get_current_user"]
        self.assertEqual([(x["id"], x["n"]) for x in sym], [("one", 1), ("two", 1)])
        self.assertIn("get_current_user", sym[0]["s"])
        self.assertIn("backend/utils/log.py::serve_forever", m["mentions"])
        self.assertNotIn("backend/utils/log.py::serve_forever@", " ".join(m["mentions"]))

    def test_mentions_key_has_no_line_range_and_counts_repeats(self):
        out = collect([ch("doc-a.html", "<h2 id='s'>S</h2><p><code>deps.py:10-20</code> <code>deps.py:30</code> <code>deps.py</code></p>")])
        self.assertEqual(out["linkables"]["links"]["deps.py:10-20"], "backend/api/deps.py@10-20")
        self.assertEqual(out["mentions"]["mentions"]["backend/api/deps.py"][0]["n"], 3)

    def test_folders_are_linked_but_have_no_backlinks(self):
        out = collect([ch("doc-a.html", "<h2 id='s'>S</h2><p><code>backend/api/</code></p>")])
        self.assertEqual(out["linkables"]["links"]["backend/api/"], "backend/api/")
        self.assertEqual(out["mentions"]["mentions"], {})

    def test_report(self):
        r = self.out["report"]
        c = r["chapters"][0]
        self.assertEqual((c["chapter"], c["title"]), ("doc-a.html", "Chapter A"))
        self.assertEqual(c["spans"], 9)
        # resolved: deps.py, get_current_user, log.py, serve_forever (section two), get_current_user();  unresolved: mystery_thing;
        # skipped: run;  ambiguous: serve_forever (section three), .env.example
        self.assertEqual((c["resolved"], c["unresolved"], c["skipped"], c["ambiguous"]), (5, 1, 1, 2))
        self.assertEqual(c["spans"], c["resolved"] + c["unresolved"] + c["skipped"] + c["ambiguous"])
        self.assertEqual(c["top_unresolved"], [{"text": "mystery_thing", "n": 1}])
        self.assertEqual(r["summary"]["spans"], c["spans"])
        self.assertEqual(r["summary"]["pct"], round(100 * c["resolved"] / c["spans"], 1))
        self.assertEqual(r["aliasProblems"], [])

    def test_report_counts_add_up_over_chapters(self):
        out = collect([ch("doc-a.html", self.body), ch("doc-b.html", "<h2 id='x'>X</h2><p><code>deps.py</code> <code>nothing_here</code></p>")])
        s = out["report"]["summary"]
        self.assertEqual(s["spans"], s["resolved"] + s["ambiguous"] + s["unresolved"] + s["skipped"])
        self.assertEqual(s["spans"], sum(c["spans"] for c in out["report"]["chapters"]))

    def test_empty_inputs(self):
        out = cl.collect_links([], [], [])
        self.assertEqual(out["linkables"], {"links": {}, "choices": {}, "sections": {}})
        self.assertEqual(out["mentions"], {"chapters": [], "mentions": {}})
        self.assertEqual(out["report"]["summary"]["pct"], 0.0)
        out = cl.collect_links([ch("doc-a.html", "<p>No code at all.</p>")], PATHS, SYMBOLS)
        self.assertEqual(out["report"]["chapters"][0]["pct"], 0.0)

    def test_is_deterministic(self):
        again = collect([ch("doc-a.html", self.body, "Chapter A")])
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.out, sort_keys=True))


class BuildWiring(unittest.TestCase):
    def test_build_writes_the_three_files_and_uses_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "content").mkdir()
            (root / "content" / "nav.json").write_text(json.dumps({"chapters": [{"id": "a", "title": "Chapter A", "url": "doc-a.html"}]}), encoding="utf-8")
            (root / "content" / "link-aliases.json").write_text(json.dumps({"aliases": {"the dependency module": "backend/api/deps.py", "bad": "x/y.py"}}), encoding="utf-8")
            (root / "doc-a.html").write_text("<html><head><title>A · MiniMe Atlas</title></head><body><main><h2 id='s'>S</h2>"
                                             "<p><code>the dependency module</code> <code>get_current_user</code></p></main></body></html>", encoding="utf-8")
            census = {"files": [{"path": "backend/api/deps.py", "functions": [{"qual": "get_current_user", "start": 10}]}]}
            warnings: list[str] = []
            out = bi.build(root, warnings.append, census)
            for name in ("linkables", "mentions", "link-report"):
                self.assertIn(f"data/index/{name}.json", out)
            lk = json.loads(out["data/index/linkables.json"])
            self.assertEqual(lk["links"]["the dependency module"], "backend/api/deps.py")
            self.assertEqual(lk["links"]["get_current_user"], "backend/api/deps.py::get_current_user")
            self.assertTrue(any("x/y.py" in w for w in warnings), warnings)
            m = json.loads(out["data/index/mentions.json"])
            self.assertEqual(m["chapters"], [{"url": "doc-a.html", "title": "Chapter A"}])
            self.assertTrue(bi.write_all(root, lambda m: None, census))
            self.assertEqual(bi.check_all(root, lambda m: None, census), [])                   # and the check agrees afterwards
            (root / "doc-a.html").write_text((root / "doc-a.html").read_text(encoding="utf-8").replace("S</h2>", "S</h2><p><code>deps.py</code></p>"), encoding="utf-8")
            self.assertIn("stale: data/index/mentions.json", bi.check_all(root, lambda m: None, census))   # editing a chapter makes the check fail


class RealRepository(unittest.TestCase):
    """The committed data/index files against the committed census and chapters."""

    @classmethod
    def setUpClass(cls):
        cls.have = (ROOT / "data" / "index" / "linkables.json").exists() and (ROOT / "data" / "census.json").exists()

    def setUp(self):
        if not self.have:
            self.skipTest("data/index/linkables.json is missing: run python scripts/build_index.py")

    def load(self, name):
        return json.loads(bi.read_lf(ROOT / "data" / "index" / name))

    def test_index_is_current(self):
        self.assertEqual(bi.check_all(ROOT, lambda m: None), [])

    def test_every_link_points_at_the_census(self):
        paths = set(self.load("paths.json")["paths"])
        dirs = {"/".join(p.split("/")[:i]) for p in paths for i in range(1, len(p.split("/")))}
        symbols = set()
        for shard in self.load("symbols.json")["shards"]:
            doc = self.load(shard["file"])
            symbols |= {(doc["files"][r[1]], r[0]) for r in doc["rows"]}
        lk = self.load("linkables.json")
        targets = list(lk["links"].values()) + [t for v in lk["choices"].values() for t in v] + [t for s in lk["sections"].values() for t in s.values()]
        self.assertTrue(targets)
        for t in targets:
            if t.endswith("/"):
                self.assertIn(t.rstrip("/"), dirs, t)
                continue
            base = re.sub(r"@\d+(?:-\d+)?$", "", t)
            path, _, qual = base.partition("::")
            self.assertIn(path, paths, t)
            if qual:
                self.assertIn((path, qual), symbols, t)

    def test_choices_have_at_least_two_candidates_and_never_overlap_links(self):
        lk = self.load("linkables.json")
        for text, cands in lk["choices"].items():
            self.assertGreaterEqual(len(cands), 2, text)
            self.assertNotIn(text, lk["links"])

    def test_every_mention_names_a_real_section_of_a_real_chapter(self):
        m = self.load("mentions.json")
        paths = set(self.load("paths.json")["paths"])
        cache: dict[str, set[str]] = {}
        for key, rows in m["mentions"].items():
            self.assertIn(key.split("::")[0], paths, key)
            for r in rows:
                url = m["chapters"][r["c"]]["url"]
                if url not in cache:
                    cache[url] = {hid for _, hid, _ in bi.parse_chapter(bi.read_lf(ROOT / url)).headings}
                if r["id"]:
                    self.assertIn(r["id"], cache[url], f"{key} -> {url}#{r['id']}")

    def test_report_matches_the_chapters(self):
        rep = self.load("link-report.json")
        self.assertEqual(rep["aliasProblems"], [])
        self.assertEqual(len(rep["chapters"]), len(self.load("mentions.json")["chapters"]))
        for c in rep["chapters"]:
            self.assertEqual(c["spans"], c["resolved"] + c["ambiguous"] + c["unresolved"] + c["skipped"], c["chapter"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
