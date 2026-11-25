#!/usr/bin/env python3
"""Tests for the book library and the glossary (patch P05). Run: python scripts/test_library.py

Covers assets/js/library.js and assets/js/glossary.js (their pure helpers, run in Node with no browser), docs.html, glossary.html,
content/glossary.json, content/reading-paths.json and data/index/book.json. The tests that need Node are skipped, not failed, when `node`
is not on PATH. The tooltip half of P05 lives in scripts/test_reader.py. Standard library only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_index  # noqa: E402
import check_site  # noqa: E402

NODE = shutil.which("node")
LIB_JS = ROOT / "assets" / "js" / "library.js"
GLOSSARY_JS = ROOT / "assets" / "js" / "glossary.js"
LIB_CSS = ROOT / "assets" / "css" / "library.css"


def run_node(src: Path, body: str, data=None):
    """Run `body` (ES module code that can use `M`, the exports of `src`, and `data`) next to a copy of it; return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(src, tmp / "mod.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text("import * as M from './mod.mjs'; import fs from 'node:fs';\n"
                                     "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def nav_chapters():
    return [it for w in load_json("content/nav.json")["wings"] for it in w["items"] if it.get("chapter") is not None]


CHAPTERS = [
    {"id": "doc-a", "url": "doc-a.html", "label": "Ch. 1", "title": "Rulebook", "blurb": "Pricing and rules", "desc": "The money constitution", "partTitle": "Part I"},
    {"id": "doc-b", "url": "doc-b.html", "label": "Ch. 4", "title": "MiniMe Feature Guide", "blurb": "", "desc": "Every subsystem", "partTitle": "Part II"},
]


@unittest.skipUnless(NODE, "node is not installed")
class LibraryHelpers(unittest.TestCase):
    def test_formatting(self):
        out = run_node(LIB_JS, """console.log(JSON.stringify([M.fmtMinutes(37), M.fmtMinutes(502), M.fmtMinutes(120), M.fmtMinutes(0), M.fmtMinutes(null),
            M.fmtDate('2026-10-07'), M.fmtDate('soon'), M.fmtDate(''), M.fmtN(110083)]));""")
        self.assertEqual(out, ["37 min", "8 h 22 min", "2 h", "", "", "7 Oct 2026", "soon", "", "110,083"])

    def test_progress_states_and_continue_link(self):
        out = run_node(LIB_JS, """
            const map = { a: { id: 'sec-1', pct: 40, t: 5 }, b: { id: 'x', pct: 99, t: 9 }, c: { id: 'y', pct: 1, t: 1 }, d: 'junk', e: { pct: 'many' } };
            const ch = (id) => ({ id, url: id + '.html' });
            console.log(JSON.stringify({
              states: ['a', 'b', 'c', 'd', 'e', 'zzz'].map((k) => M.progressState(M.readProgress(map, k))),
              hrefs: ['a', 'b', 'c'].map((k) => M.continueHref(ch(k), M.readProgress(map, k))),
              clamp: M.readProgress({ q: { pct: 250 } }, 'q').pct,
            }));""")
        self.assertEqual(out["states"], ["reading", "done", "new", "new", "new", "new"])
        self.assertEqual(out["hrefs"], ["a.html#sec-1", "b.html", "c.html"])
        self.assertEqual(out["clamp"], 100)

    def test_most_recent_unfinished_chapter(self):
        out = run_node(LIB_JS, """
            const chapters = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
            const map = { a: { id: 'x', pct: 30, t: 100 }, b: { id: 'y', pct: 60, t: 200 }, c: { id: 'z', pct: 100, t: 300 } };
            console.log(JSON.stringify([M.mostRecent(chapters, map).chapter.id, M.mostRecent(chapters, {})]));""")
        self.assertEqual(out, ["b", None])                  # c is finished, so it is not offered; b is the newest of the rest

    def test_chapter_filter_needs_every_word(self):
        out = run_node(LIB_JS, "console.log(JSON.stringify([q => M.filterChapters(data, q).map((c) => c.id)].map((f) => [f(''), f('rulebook'), f('pricing rules'), f('part ii guide'), f('zebra')])[0]));", CHAPTERS)
        self.assertEqual(out, [["doc-a", "doc-b"], ["doc-a"], ["doc-a"], ["doc-b"], []])

    def test_heading_search_ranks_prefix_matches_first_and_reports_the_total(self):
        out = run_node(LIB_JS, "const r = M.matchHeadings(data, 'golden', 2); console.log(JSON.stringify({ t: r.rows.map((h) => h.title), total: r.total }));",
                       [{"title": "The 15 Golden Rules", "chapterTitle": "Rulebook", "level": 1}, {"title": "Golden rule 5", "chapterTitle": "Rulebook", "level": 2},
                        {"title": "Other", "chapterTitle": "About golden things", "level": 2}, {"title": "Unrelated", "chapterTitle": "X", "level": 2}])
        self.assertEqual(out, {"t": ["Golden rule 5", "The 15 Golden Rules"], "total": 3})

    def test_path_steps_link_to_chapters_and_to_source(self):
        out = run_node(LIB_JS, """
            const titles = { 'doc-a.html#s1': 'Section One' };
            console.log(JSON.stringify([
              M.stepInfo({ chapter: 'doc-a', heading: 's1', note: 'n' }, data, titles, 'abc1234'),
              M.stepInfo({ chapter: 'doc-a' }, data, titles, 'abc1234').text,
              M.stepInfo({ chapter: 'nope' }, data, titles, 'abc1234'),
              M.stepInfo({ file: 'backend/eo/registry.py', qual: 'resolve_role' }, data, titles, 'abc1234'),
              M.stepInfo({ file: 'a b/c#d.py' }, data, titles, ''),
            ]));""", CHAPTERS)
        self.assertEqual(out[0], {"kind": "Ch. 1", "url": "doc-a.html#s1", "text": "Section One", "note": "n", "external": False})
        self.assertEqual(out[1], "Rulebook")
        self.assertIsNone(out[2])
        self.assertEqual(out[3]["url"], "https://github.com/Unavailable4u/MiniMe/blob/abc1234/backend/eo/registry.py")
        self.assertEqual(out[3]["text"], "backend/eo/registry.py \u00b7 resolve_role")
        self.assertTrue(out[4]["url"].endswith("/main/a%20b/c%23d.py"))

    def test_ring_geometry(self):
        out = run_node(LIB_JS, "console.log(JSON.stringify([M.ringDash(0), M.ringDash(50), M.ringDash(100), M.ringDash(500).on === M.ringDash(100).on]));")
        self.assertEqual(out[0]["on"], 0)
        self.assertAlmostEqual(out[1]["on"] * 2, out[1]["c"], delta=0.02)
        self.assertEqual(out[2]["on"], out[2]["c"])
        self.assertTrue(out[3])


@unittest.skipUnless(NODE, "node is not installed")
class GlossaryHelpers(unittest.TestCase):
    TERMS = [
        {"term": "Wave", "category": "Build", "short": "A group.", "match": "off", "aliases": ["waves"]},
        {"term": "Golden Rule", "category": "Governance", "short": "A rule.", "long": "Fifteen of them.", "aliases": ["Golden Rules"], "needs_review": True},
        {"term": "golden-rule", "short": "Same anchor as the one above, so it is dropped."},
        {"term": "No short definition"},
        {"term": "Vault", "category": "Safety", "short": "Keeps secrets.", "see": ["doc-x#intro", 7]},
    ]

    def test_slug_is_the_same_recipe_as_the_python_side(self):
        samples = ["Golden Rule", "T0 to T5 approval tiers", "Work package (WP)", "REAL_ACTION_ROLES", "usage_ledger", "M2C L26", "***", "  Café  "]
        js = run_node(GLOSSARY_JS, "console.log(JSON.stringify(data.map((s) => M.slug(s))));", samples)
        self.assertEqual(js, [build_index.slug(s) for s in samples])
        self.assertEqual(js, [check_site.term_slug(s) for s in samples])

    def test_normalize_sorts_dedupes_and_drops_incomplete_entries(self):
        out = run_node(GLOSSARY_JS, "console.log(JSON.stringify(M.normalizeTerms({ terms: data }).map((t) => [t.id, t.category, t.match, t.review, t.see])));", self.TERMS)
        self.assertEqual(out, [["golden-rule", "Governance", "ci", True, []], ["vault", "Safety", "ci", False, ["doc-x#intro"]], ["wave", "Build", "off", False, []]])

    def test_filter_by_words_and_category(self):
        out = run_node(GLOSSARY_JS, """
            const t = M.normalizeTerms(data), f = (q, c) => M.filterTerms(t, q, c).map((x) => x.id);
            console.log(JSON.stringify([f('', 'all'), f('golden rules', 'all'), f('fifteen', 'all'), f('', 'Safety'), f('secrets', 'Build'), M.categoryCounts(t)]));""", self.TERMS)
        self.assertEqual(out[:5], [["golden-rule", "vault", "wave"], ["golden-rule"], ["golden-rule"], ["vault"], []])
        self.assertEqual(out[5], [{"name": "Build", "count": 1}, {"name": "Governance", "count": 1}, {"name": "Safety", "count": 1}])

    def test_see_links(self):
        out = run_node(GLOSSARY_JS, """
            const pages = { 'doc-x': { url: 'doc-x.html', title: 'X', label: 'Ch. 9' } }, titles = { 'doc-x.html#intro': 'Intro' };
            console.log(JSON.stringify([M.seeLink('doc-x', pages, titles, 'c0ffee1'), M.seeLink('doc-x#intro', pages, titles, 'c0ffee1'), M.seeLink('nope', pages, titles, 'c0ffee1'),
              M.seeLink('m2c/src/m2c/sandbox/bwrap.py', pages, titles, 'c0ffee1'), M.seeLink('backend/eo/registry.py::resolve_role', pages, titles, '')]));""")
        self.assertEqual(out[0], {"code": False, "url": "doc-x.html", "text": "Ch. 9", "external": False})
        self.assertEqual(out[1]["text"], "Ch. 9: Intro")
        self.assertIsNone(out[2])
        self.assertEqual(out[3]["url"], "https://github.com/Unavailable4u/MiniMe/blob/c0ffee1/m2c/src/m2c/sandbox/bwrap.py")
        self.assertTrue(out[3]["code"])
        self.assertEqual(out[4]["text"], "backend/eo/registry.py \u00b7 resolve_role")
        self.assertTrue(out[4]["url"].startswith("https://github.com/Unavailable4u/MiniMe/blob/main/backend/eo/registry.py"))


class Pages(unittest.TestCase):
    def html(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def ids_used_by(self, js_path):
        return set(re.findall(r'getElementById\("([^"]+)"\)', js_path.read_text(encoding="utf-8")))

    def test_both_pages_are_on_the_shell(self):
        for name, page in (("docs.html", "docs"), ("glossary.html", "glossary")):
            s = self.html(name)
            self.assertIn('data-layout="reader"', s)
            self.assertIn(f'data-page="{page}"', s)
            self.assertIn('<script type="module" src="assets/js/shell.js"></script>', s)
            self.assertIn('<link rel="stylesheet" href="assets/css/library.css">', s)
            self.assertIn('<meta name="robots" content="noindex,nofollow">', s)
            self.assertNotIn("<nav", s)                                   # the sidebar is the shell's
            self.assertNotIn("atlas-ui.js", s)

    def test_every_element_the_scripts_look_up_exists(self):
        for html, js in (("docs.html", LIB_JS), ("glossary.html", GLOSSARY_JS)):
            ids = set(re.findall(r'\bid="([^"]+)"', self.html(html)))
            self.assertEqual(self.ids_used_by(js) - ids, set(), f"{js.name} needs ids that {html} does not have")

    def test_the_library_is_not_mistaken_for_a_chapter(self):
        s = self.html("docs.html")
        self.assertNotIn("bk-banner", s)                                  # shell.js loads the chapter reader on pages that have one
        self.assertNotIn('class="doc"', s)

    def test_old_links_survive(self):
        s = self.html("docs.html")
        for href in ("journey.html", "consistency.html", "glossary.html"):
            self.assertIn(f'href="{href}', s)

    def test_without_javascript_every_chapter_is_still_listed(self):
        noscript = re.search(r"<noscript>(.*?)</noscript>", self.html("docs.html"), re.S).group(1)
        for it in nav_chapters():
            self.assertIn(f'href="{it["url"]}"', noscript, it["url"])

    def test_the_glossary_is_in_the_navigation(self):
        items = {it["id"]: it for w in load_json("content/nav.json")["wings"] for it in w["items"]}
        self.assertEqual(items["glossary"]["url"], "glossary.html")
        self.assertEqual(items["glossary"]["layout"], "reader")

    def test_stylesheet_uses_tokens_outside_the_map(self):
        css = re.sub(r"/\*.*?\*/", "", LIB_CSS.read_text(encoding="utf-8"), flags=re.S)
        css = re.sub(r"\.lib-map \.svg-wrap\s*\{[^}]*\}|\.bk-node-box[^{]*\{[^}]*\}", "", css)    # the map SVG keeps its own dark palette
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b", css), [])
        tokens = (ROOT / "assets" / "css" / "tokens.css").read_text(encoding="utf-8") + (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        undefined = {v for v in re.findall(r"var\((--[a-z0-9-]+)", css) if f"{v}:" not in tokens}
        self.assertEqual(undefined, set())

    def test_the_ecosystem_map_survived_with_all_eight_blocks(self):
        s = self.html("docs.html")
        nodes = set(re.findall(r'data-node="([a-z0-9]+)"', s))
        info = set(re.findall(r'^\s{2}"?([a-z0-9]+)"?: \{\s*$', LIB_JS.read_text(encoding="utf-8"), re.M))
        self.assertEqual(nodes, {"web", "m2c", "menux", "minicore", "brain", "server", "rulebook", "fbebc"})
        self.assertTrue(nodes <= info, nodes - info)


class Data(unittest.TestCase):
    def test_book_json_is_current_and_covers_every_nav_chapter(self):
        self.assertEqual(build_index.check_all(ROOT, lambda m: None), [])
        book = load_json("data/index/book.json")
        self.assertEqual([c["id"] for c in book["chapters"]], [it["id"] for it in nav_chapters()])
        self.assertEqual(book["totals"]["chapters"], 14)
        self.assertEqual(book["totals"]["appendices"], 3)
        for c in book["chapters"]:
            self.assertTrue(c["desc"], c["id"])
            self.assertRegex(c["built"], r"^\d{4}-\d{2}-\d{2}$", c["id"])
        spec = [c for c in book["chapters"] if c["words"] is None]
        self.assertEqual({c["id"] for c in spec}, {"doc-m2c-product", "doc-menux-product"})     # the two interactive design specs have no counts

    def test_chapter_pages_were_not_touched(self):
        if not shutil.which("git") or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        r = subprocess.run(["git", "status", "--porcelain", "--", "doc-*.html"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.stdout.strip(), "", "a chapter page has uncommitted changes")

    def test_glossary_shape_and_seed_terms(self):
        terms = load_json("content/glossary.json")["terms"]
        self.assertGreaterEqual(len(terms), 20)
        slugs = [check_site.term_slug(t["term"]) for t in terms]
        self.assertEqual(len(slugs), len(set(slugs)))
        for t in terms:
            self.assertTrue(t["category"], t["term"])
            self.assertLessEqual(len(t["short"]), 160, t["term"])
            self.assertLessEqual(len(t.get("long", "")), 600, t["term"])
            self.assertTrue(t["see"], f'{t["term"]} points nowhere')
        have = " | ".join([t["term"] for t in terms] + [a for t in terms for a in t.get("aliases", [])]).lower()
        for seed in ("golden rule", "work package", "wave", "tech-a", "tech-h", "t0\u2013t5", "daemon", "vault", "bubblewrap", "checkpoint", "minicore", "fbebc",
                     "m2c l26", "menux", "real_action_roles", "part 0", "agent module", "role", "stage", "lock", "key pool"):
            self.assertIn(seed, have, f"seed term missing: {seed}")

    def test_terms_that_are_ordinary_words_do_not_underline_the_book(self):
        by = {t["term"]: t for t in load_json("content/glossary.json")["terms"]}
        for name in ("Wave", "Stage (workspace)", "Role", "Lock", "Checkpoint"):
            self.assertEqual(by[name].get("match"), "off", name)

    def test_the_palette_finds_every_term_at_its_page_anchor(self):
        terms = load_json("data/index/search.json")["terms"]
        self.assertEqual(len(terms), len(load_json("content/glossary.json")["terms"]))
        for t in terms:
            self.assertEqual(t["url"], f'glossary.html#{check_site.term_slug(t["term"])}')

    def test_reading_paths(self):
        paths = load_json("content/reading-paths.json")["paths"]
        self.assertGreaterEqual(len(paths), 6)
        for p in paths:
            self.assertTrue(p["title"].startswith("I want to"), p["id"])
            self.assertGreaterEqual(len(p["steps"]), 3, p["id"])
        self.assertTrue(any("file" in s for p in paths for s in p["steps"]), "no path points at code")
        self.assertTrue(any("chapter" in s for p in paths for s in p["steps"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
