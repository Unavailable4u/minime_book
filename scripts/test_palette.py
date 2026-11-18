#!/usr/bin/env python3
"""Tests for assets/js/palette.js (patch P03). Run: python scripts/test_palette.py

The palette's logic (query parsing, fuzzy matching, shard loading) is pure, so it is exercised in Node with
no browser. The tests that need Node are skipped, not failed, when `node` is not on PATH.
Standard library only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
PALETTE = ROOT / "assets" / "js" / "palette.js"
INDEX = ROOT / "data" / "index"


def run_node(body: str, data: dict | None = None):
    """Run `body` (ES module code that can `import * as P` and read `data`) next to a copy of palette.js; return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(PALETTE, tmp / "palette.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as P from './palette.mjs'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(NODE, "node is not installed")
class Matching(unittest.TestCase):
    def test_parse_query_operators(self):
        qs = ["", "  budget  ", ">api", "# target venues", "/backend\\api\\deps.py", "@Foo.bar", ":audit", "?", "a>b"]
        got = run_node("console.log(JSON.stringify(data.map(P.parseQuery)));", qs)
        self.assertEqual(got, [
            {"op": "", "q": ""}, {"op": "", "q": "budget"}, {"op": ">", "q": "api"}, {"op": "#", "q": "target venues"},
            {"op": "/", "q": "backend/api/deps.py"},     # Windows separators are normalised
            {"op": "@", "q": "Foo.bar"}, {"op": ":", "q": "audit"}, {"op": "?", "q": ""},
            {"op": "", "q": "a>b"},                      # only the FIRST character is an operator
        ])

    def test_parse_query_ignores_object_prototype_names(self):
        # "constructor" and friends must not be mistaken for operators (OPS is a plain object)
        got = run_node("console.log(JSON.stringify(P.parseQuery('toString')));")
        self.assertEqual(got, {"op": "", "q": "toString"})

    def test_substring_beats_subsequence_and_prefix_beats_middle(self):
        got = run_node(
            "const f = (q, t) => { const m = P.fuzzy(q, t); return m && m.score; };\n"
            "console.log(JSON.stringify({ prefix: f('rule', 'Rulebook'), middle: f('rule', 'The Rulebook'),\n"
            "  sub: f('rlbk', 'Rulebook'), none: f('zzz', 'Rulebook'), empty: f('', 'x') }));")
        self.assertGreater(got["prefix"], got["middle"])
        self.assertGreater(got["middle"], got["sub"])
        self.assertIsNone(got["none"])
        self.assertEqual(got["empty"], 0)

    def test_scattered_letters_are_not_a_match(self):
        """"api" must not find "Technical Implementation", and "budget" must not find "Building the scorer on top"."""
        got = run_node(
            "console.log(JSON.stringify([P.fuzzy('api', 'technical implementation'), P.fuzzy('budget', '4.4 building the delta-scorer on top of what already exists'),\n"
            "  P.fuzzy('rb', 'Rulebook') !== null, P.fuzzy('deps', 'backend/api/deps.py') !== null,\n"
            "  P.fuzzy('gtjwt', '_get_token_jwt') !== null, P.fuzzy('cfg', 'config.py') !== null]));")
        self.assertEqual(got, [None, None, True, True, True, True], "scattered letters are noise; real abbreviations still match")

    def test_max_span_is_tight_for_short_queries(self):
        got = run_node("console.log(JSON.stringify([2, 4, 5, 10].map(P.maxSpan)));")
        self.assertEqual(got, [6, 10, 14, 24])

    def test_every_token_must_match(self):
        got = run_node(
            "const t = (q, s) => P.match(q.split(' '), s);\n"
            "console.log(JSON.stringify([t('target venues', 'Target venues and budget') !== null, t('target zebra', 'Target venues') === null,\n"
            "  P.match([], 'x').score, P.match(['a'], 'abc').idx]));")
        self.assertEqual(got, [True, True, 0, [0]])

    def test_highlight_indexes_are_sorted_and_unique(self):
        got = run_node("console.log(JSON.stringify(P.match(['ab', 'bc'], 'abc').idx));")
        self.assertEqual(got, [0, 1, 2])


@unittest.skipUnless(NODE, "node is not installed")
class Symbols(unittest.TestCase):
    SHARD = {"fields": ["qual", "file", "line", "kind"],
             "files": ["backend/api/deps.py", "backend/tests/test_deps.py"],
             "rows": [["Agent.run", 0, 70, "fn"], ["Agent", 0, 10, "cls"], ["test_run", 1, 3, "fn"], ["bad", 9, 1, "fn"], ["", 0, 1, "fn"]]}

    def test_rows_unpack_through_the_files_table(self):
        got = run_node("console.log(JSON.stringify(P.symbolItems(data).map(i => [i.title, i.path, i.line, i.badge, i.sub, i.rank])));", self.SHARD)
        self.assertEqual(got, [
            ["Agent.run", "backend/api/deps.py", 70, "FUNC", "backend/api/deps.py:70", 0],
            ["Agent", "backend/api/deps.py", 10, "CLASS", "backend/api/deps.py:10", 0],
            ["test_run", "backend/tests/test_deps.py", 3, "FUNC", "backend/tests/test_deps.py:3", -250],   # tests rank lower, not absent
        ], "rows with an unknown file index or no name are skipped, not crashed on")

    def test_empty_or_missing_shard_gives_no_items(self):
        got = run_node("console.log(JSON.stringify([P.symbolItems(null).length, P.symbolItems({}).length, P.symbolItems({rows: [['a', 0, 1, 'fn']]}).length]));")
        self.assertEqual(got, [0, 0, 0])

    def test_test_shards_load_last(self):
        shards = [{"id": "backend__tests"}, {"id": "backend__api"}, {"id": "m2c__tests"}, {"id": "frontend"}, {"id": "contests"}]
        got = run_node("console.log(JSON.stringify(P.shardOrder(data).map(s => s.id)));", shards)
        self.assertEqual(got, ["backend__api", "frontend", "contests", "backend__tests", "m2c__tests"])

    def test_every_generated_shard_loads_and_points_at_a_real_file(self):
        man = json.loads((INDEX / "symbols.json").read_text(encoding="utf-8"))
        paths = set(json.loads((INDEX / "paths.json").read_text(encoding="utf-8"))["paths"])
        shards = {s["id"]: json.loads((INDEX / s["file"]).read_text(encoding="utf-8")) for s in man["shards"]}
        got = run_node("console.log(JSON.stringify(Object.entries(data).map(([id, sh]) => [id, P.symbolItems(sh).length, sh.rows.length])));", shards)
        for sid, items, rows in got:
            self.assertEqual(items, rows, f"{sid}: every row must become one palette item")
        for sid, sh in shards.items():
            self.assertEqual(sh["fields"], man["fields"])
            self.assertEqual(len(sh["rows"]), next(s["count"] for s in man["shards"] if s["id"] == sid))
            for q, fi, line, kind in sh["rows"][:500]:
                self.assertTrue(q and isinstance(fi, int) and 0 <= fi < len(sh["files"]) and line >= 0 and kind in ("fn", "cls"), (sid, q, fi, line, kind))
            for f in sh["files"]:
                self.assertIn(f, paths, f"{sid}: {f} is a symbol's file but not in paths.json")


class Wiring(unittest.TestCase):
    """Cheap static checks that catch the mistakes a unit test of the logic cannot."""

    js = PALETTE.read_text(encoding="utf-8")
    css = (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8")

    def test_every_palette_class_is_styled(self):
        css = self.css + (ROOT / "assets" / "css" / "components.css").read_text(encoding="utf-8")   # .mm-toast / .mm-toasts live there
        names = set(re.findall(r"""['`\s](mm[ps]?-[a-z]+)\b""", self.js))
        names -= {"mmp-o", "mms-title"}             # element ids ("mmp-o-<n>", "mms-title"), not classes
        names |= {"mm-toast", "mm-toasts"}
        self.assertGreater(len(names), 15, "the scrape found too little to be trusted")
        missing = sorted(n for n in names if not re.search(rf"\.{re.escape(n)}\b", css))
        self.assertEqual([], missing, "used by palette.js but styled nowhere")

    def test_no_style_is_injected_by_script(self):
        # P03's first draft injected a <style> block; the styles belong in shell.css so both themes and print rules apply
        self.assertNotRegex(self.js, r"createElement\(['\"]style|<style|\.insertRule|adoptedStyleSheets")
        self.assertNotIn("mm-pal-css", self.js)

    def test_one_owner_for_each_key(self):
        shell = (ROOT / "assets" / "js" / "shell.js").read_text(encoding="utf-8")
        for key in ("'t'", '"t"', "'?'", '"?"', "'g'", '"g"'):
            self.assertNotIn(f"e.key === {key}", shell, f"shell.js must not handle {key}: palette.js does")
        self.assertEqual(self.js.count("window.addEventListener('keydown'"), 1, "palette.js installs exactly one global key handler")

    def test_pages_that_own_their_keyboard_are_left_alone(self):
        self.assertIn("dataset.layout === 'bare'", self.js)
        # graph-viewer.html has its own Ctrl+K, "/", "f", "1", "2". It is a hidden, generated page (embedded by graph.html)
        # that is kept off the shell; if it is ever put on the shell it must be layout "bare" or those keys fire twice.
        gv = (ROOT / "graph-viewer.html").read_text(encoding="utf-8")
        if "shell.js" in gv:
            self.assertRegex(gv, r'<html[^>]*data-layout="bare"')
        nav = json.loads((ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
        hidden = {h["url"]: h for h in nav.get("hidden", [])}
        self.assertEqual("bare", hidden["graph-viewer.html"]["layout"])

    def test_theme_has_one_writer(self):
        theme = (ROOT / "assets" / "js" / "theme.js").read_text(encoding="utf-8")
        self.assertIn("minime:theme", theme)
        self.assertIn("window.minimeTheme", self.js)       # palette.js delegates to it ...
        self.assertEqual(self.js.count("CustomEvent('minime:theme'"), 1)   # ... and only fires the event itself if theme.js is missing

    def test_retired_ctrl_k_handlers_are_gone_from_loaded_scripts(self):
        # a page that still loaded atlas-ui.js would open a second palette on Ctrl+K
        for page in ROOT.glob("*.html"):
            self.assertNotIn("atlas-ui.js", page.read_text(encoding="utf-8"), f"{page.name} still loads atlas-ui.js")


if __name__ == "__main__":
    unittest.main(verbosity=1)
