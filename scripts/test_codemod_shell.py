#!/usr/bin/env python3
"""
Tests for patch P02 (scripts/codemod_shell.py, content/nav.json, assets/js/shell.js, assets/css/shell.css).
Standard library only; the two tests that run JavaScript are skipped when `node` is not on PATH.

    python scripts/test_codemod_shell.py
    python -m unittest discover -s scripts

What is pinned down here:
    * content/nav.json is consistent with the site (every page listed once, ids unique, parts and counts resolve)
    * the codemod converts a page, leaves <main> byte-identical, is idempotent, keeps CRLF, and refuses odd pages
    * the pre-paint snippet in <head> and pickSidebar() in shell.js give the same answer for every input
    * every CSS variable that shell.css uses exists in the P01 tokens
"""
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("codemod_shell", ROOT / "scripts" / "codemod_shell.py")
cm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cm)

NODE = shutil.which("node")
BUILT = "Built 2026-11-15 from commit 94af156."
PAGE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
    "<title>Fixture - MiniMe Atlas</title>\n"
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&display=swap">'
    "<style>body{display:flex}nav{width:210px}</style></head><body>"
    '<nav><div class="logo">Mini<b>Me</b> Atlas</div><a href="index.html" class="on">Overview</a>'
    f"<small>Private. {BUILT}</small></nav>"
    f"<main><h1>Fixture</h1><p>{BUILT}</p><table><tr><th>a</th></tr></table></main>"
    '<script src="atlas-ui.js"></script></body></html>'
)
CHAPTER = PAGE.replace('<script src="atlas-ui.js"></script>', "")          # chapters never loaded atlas-ui.js
ITEM = {"id": "fixture", "title": "Fixture & Co", "url": "fixture.html", "layout": "workbench", "wing": "code", "hidden": False}
NAV = {
    "site": {"name": "MiniMe Atlas", "home": "index.html"},
    "parts": {},
    "wings": [{"id": "code", "title": "Code", "icon": "code", "items": [
        {"id": "fixture", "title": "Fixture & Co", "url": "fixture.html", "layout": "workbench"},
        {"id": "chapter", "title": "A chapter", "url": "chapter.html", "layout": "reader"},
        {"id": "broken", "title": "Broken", "url": "broken.html", "layout": "reader"}]}],
    "hidden": [{"id": "viewer", "title": "Viewer", "url": "viewer.html", "layout": "bare"}],
}


def main_of(html):
    return html[html.index("<main"):html.index("</main>") + 7]


class NavFile(unittest.TestCase):
    """content/nav.json is the single source for the sidebar, breadcrumbs, palette and page titles."""

    @classmethod
    def setUpClass(cls):
        cls.nav = json.loads((ROOT / "content" / "nav.json").read_bytes().decode("utf-8-sig"))
        cls.items = [it for w in cls.nav["wings"] for it in w["items"]]
        cls.everything = cls.items + cls.nav.get("hidden", [])

    def test_required_fields_and_layouts(self):
        for it in self.everything:
            for key in ("id", "title", "url", "layout"):
                self.assertTrue(it.get(key), f"{it.get('url')}: missing {key}")
            self.assertIn(it["layout"], cm.LAYOUTS, it["url"])
        for w in self.nav["wings"]:
            for key in ("id", "title", "icon"):
                self.assertTrue(w.get(key), f"wing {w.get('id')}: missing {key}")

    def test_ids_and_urls_are_unique(self):
        for key in ("id", "url"):
            vals = [it[key] for it in self.everything]
            self.assertEqual(sorted(set(vals)), sorted(vals), f"duplicate {key}")

    def test_every_root_page_is_listed_and_every_listed_page_exists(self):
        pages = {p.name for p in ROOT.glob("*.html")}
        listed = {it["url"] for it in self.everything}
        self.assertEqual(set(), pages - listed, "root pages missing from content/nav.json")
        self.assertEqual(set(), listed - pages, "nav.json lists pages that do not exist")

    def test_parts_and_chapters_resolve(self):
        for it in self.items:
            if it.get("part"):
                self.assertIn(it["part"], self.nav["parts"], it["url"])
                self.assertIn("chapter", it, f"{it['url']}: a part needs a chapter number")
        chapters = [it["chapter"] for it in self.items if "chapter" in it]
        self.assertEqual(sorted(map(str, chapters)), sorted(set(map(str, chapters))), "duplicate chapter number")

    def test_counts_come_from_stats_json(self):
        stats = json.loads((ROOT / "data" / "index" / "stats.json").read_text(encoding="utf-8"))
        for it in self.items:
            if it.get("count_from"):
                self.assertIsInstance(stats.get(it["count_from"]), int, f"{it['url']}: stats.json has no number '{it['count_from']}'")

    def test_titles_have_no_typed_counts(self):
        for it in self.everything:
            self.assertFalse(re.search(r"\d[\d,]{2,}", it["title"]), f"{it['url']}: typed number in the title; use count_from")


class Convert(unittest.TestCase):
    def test_page_is_moved_onto_the_shell(self):
        out = cm.convert(PAGE, ITEM)
        cm.verify(PAGE, out)
        self.assertIn('<html lang="en" data-layout="workbench">', out)
        self.assertIn("<title>Fixture &amp; Co · MiniMe Atlas</title>", out)
        self.assertNotIn("fonts.googleapis.com", out)
        self.assertNotIn("<nav", out)
        self.assertNotIn("atlas-ui.js", out)
        self.assertIn('<body data-page="fixture">', out)
        self.assertEqual(1, out.count(cm.SHELL_TAG))
        self.assertEqual(1, out.count(cm.THEME_TAG))
        self.assertEqual(1, out.count('data-mm="prepaint"'))
        for tag in cm.CSS_TAGS:
            self.assertEqual(1, out.count(tag), tag)
        self.assertEqual(main_of(PAGE), main_of(out), "<main> must be byte-identical")
        self.assertIn(f'</main><small class="mm-built">Private. {BUILT}</small>', out)

    def test_head_order_theme_first_then_shell_css_last(self):
        out = cm.convert(PAGE, ITEM)
        head = out[out.index("<head>"):out.index("</head>")]
        self.assertLess(head.index("</title>"), head.index("theme.js"))
        self.assertLess(head.index("theme.js"), head.index('data-mm="prepaint"'))
        self.assertLess(head.index("<style>"), head.index("tokens.css"))
        self.assertTrue(head.rstrip().endswith('shell.css">'), "shell.css must load last so it wins over the page's own CSS")

    def test_chapter_without_atlas_ui_gets_the_module_before_body_end(self):
        out = cm.convert(CHAPTER, dict(ITEM, layout="reader"))
        self.assertTrue(out.rstrip().endswith(cm.SHELL_TAG + "</body></html>"))
        cm.verify(CHAPTER, out)

    def test_idempotent(self):
        once = cm.convert(PAGE, ITEM)
        self.assertEqual(once, cm.convert(once, ITEM))
        twice = cm.convert(CHAPTER, ITEM)
        self.assertEqual(twice, cm.convert(twice, ITEM))

    def test_layout_and_title_follow_nav_json_when_it_changes(self):
        once = cm.convert(PAGE, ITEM)
        again = cm.convert(once, dict(ITEM, layout="reader", title="Renamed"))
        self.assertIn('data-layout="reader"', again)
        self.assertEqual(1, again.count("data-layout="))
        self.assertIn("<title>Renamed · MiniMe Atlas</title>", again)

    def test_unusual_pages_are_refused(self):
        two_mains = PAGE.replace("</main>", "</main><main>x</main>")
        with self.assertRaises(cm.CodemodError):
            cm.verify(two_mains, cm.convert(two_mains, ITEM))
        with self.assertRaises(cm.CodemodError):
            cm.convert(PAGE.replace("<title>Fixture - MiniMe Atlas</title>", ""), ITEM)
        with self.assertRaises(cm.CodemodError):
            cm.convert(PAGE, dict(ITEM, layout="sideways"))
        out = cm.convert(PAGE, ITEM)
        with self.assertRaises(cm.CodemodError):                      # a changed <main> is caught by verify
            cm.verify(PAGE, out.replace("<h1>Fixture</h1>", "<h1>Changed</h1>"))
        with self.assertRaises(cm.CodemodError):                      # a lost build stamp is caught by verify
            cm.verify(PAGE, out.replace(f'<small class="mm-built">Private. {BUILT}</small>', ""))


class OnACopy(unittest.TestCase):
    """The driver: which pages are converted, which are skipped, line endings, --check."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "content").mkdir()
        (self.tmp / "content" / "nav.json").write_text(json.dumps(NAV), encoding="utf-8")
        (self.tmp / "fixture.html").write_bytes(PAGE.replace("\n", "\r\n").encode("utf-8"))      # a Windows checkout
        (self.tmp / "chapter.html").write_bytes(CHAPTER.encode("utf-8"))
        (self.tmp / "broken.html").write_bytes(PAGE.replace("</main>", "</main><main></main>").encode("utf-8"))
        (self.tmp / "viewer.html").write_bytes(b"<html><title>v</title></html>")                # hidden
        (self.tmp / "stray.html").write_bytes(b"<html><title>s</title></html>")                  # not in nav.json

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def apply(self, changes):
        for p, text in changes.items():
            p.write_bytes(text.encode("utf-8"))

    def test_plan_converts_skips_and_reports(self):
        changes, skipped, errors = cm.plan(self.tmp)
        self.assertEqual({"fixture.html", "chapter.html"}, {p.name for p in changes})
        self.assertEqual({"viewer.html", "stray.html"}, {n for n, _ in skipped})
        self.assertEqual(["broken.html"], [n for n, _ in errors])

    def test_crlf_is_preserved_and_second_run_changes_nothing(self):
        changes, _, _ = cm.plan(self.tmp)
        raw = changes[self.tmp / "fixture.html"].encode("utf-8")
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), "a bare LF was introduced")
        raw_lf = changes[self.tmp / "chapter.html"].encode("utf-8")
        self.assertNotIn(b"\r", raw_lf, "an LF page must stay LF")
        self.apply(changes)
        self.assertEqual(({}, ), cm.plan(self.tmp)[:1], "running the codemod twice must change nothing")

    def test_only_selects_by_file_name_or_nav_id(self):
        self.assertEqual({"fixture.html"}, {p.name for p in cm.plan(self.tmp, ["fixture.html"])[0]})
        self.assertEqual({"chapter.html"}, {p.name for p in cm.plan(self.tmp, ["chapter"])[0]})
        with self.assertRaises(SystemExit):
            cm.plan(self.tmp, ["nope.html"])

    def test_main_exit_codes(self):
        (self.tmp / "broken.html").unlink()
        self.assertEqual(1, cm.main(["--root", str(self.tmp), "--check"]))
        self.assertEqual(1, cm.main(["--root", str(self.tmp), "--check"]), "--check never writes")
        self.assertEqual(0, cm.main(["--root", str(self.tmp), "--dry-run"]))
        self.assertEqual(0, cm.main(["--root", str(self.tmp)]))
        self.assertEqual(0, cm.main(["--root", str(self.tmp), "--check"]))


class PrePaintMatchesShell(unittest.TestCase):
    """The inline snippet in <head> and pickSidebar() in shell.js are one rule written twice. They must never disagree,
    or the sidebar jumps when shell.js loads."""

    @unittest.skipUnless(NODE, "node is not installed")
    def test_every_input_gives_the_same_state(self):
        snippet = re.search(r'<script data-mm="prepaint">(.*)</script>', cm.PREPAINT, re.S).group(1)
        cases = [{"w": w, "saved": s, "layout": lay}
                 for w in (320, 760, 761, 900, 1099, 1100, 1440)
                 for s in (None, "open", "collapsed", "garbage")
                 for lay in ("reader", "workbench", "bare")]
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "assets" / "js" / "shell.js", tmp / "shell.mjs")
            (tmp / "run.mjs").write_text(
                "import vm from 'node:vm'; import fs from 'node:fs'; import { pickSidebar } from './shell.mjs';\n"
                "const snippet = fs.readFileSync('snippet.js', 'utf8'); const cases = JSON.parse(fs.readFileSync('cases.json', 'utf8'));\n"
                "const run = (c, search) => { const dataset = { layout: c.layout };\n"
                "  vm.runInNewContext(snippet, { document: { documentElement: { dataset } }, window: { innerWidth: c.w, location: { search } },\n"
                "    localStorage: { getItem: () => c.saved } }); return dataset.sidebar ?? null; };\n"
                "console.log(JSON.stringify(cases.map((c) => ({ ...c, pre: run(c, ''), fn: pickSidebar(c.w, c.saved, c.layout),\n"
                "  legacy: run(c, '?x=1&legacy=1') }))));\n", encoding="utf-8")
            (tmp / "snippet.js").write_text(snippet, encoding="utf-8")
            (tmp / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
            res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, timeout=60)
            self.assertEqual(0, res.returncode, res.stderr)
            rows = json.loads(res.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(len(cases), len(rows))
        for r in rows:
            self.assertEqual(r["fn"], r["pre"], f"pre-paint and shell.js disagree for {r}")
            self.assertIsNone(r["legacy"], "?legacy=1 must leave html[data-sidebar] unset (shell off)")
        self.assertEqual({"open", "collapsed", "drawer"}, {r["pre"] for r in rows})

    @unittest.skipUnless(NODE, "node is not installed")
    def test_palette_scoring(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "assets" / "js" / "shell.js", tmp / "shell.mjs")
            (tmp / "run.mjs").write_text(
                "import { scorePage } from './shell.mjs';\n"
                "const it = { title: 'API', wingTitle: 'Code library', keywords: 'routes fastapi', blurb: 'HTTP routes', part: null };\n"
                "console.log(JSON.stringify([scorePage(it, {}, 'api'), scorePage(it, {}, 'fastapi'), scorePage(it, {}, 'api routes'), scorePage(it, {}, 'zebra')]));\n",
                encoding="utf-8")
            res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, timeout=60)
            self.assertEqual(0, res.returncode, res.stderr)
            title, keyword, both, none = json.loads(res.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertGreater(title, keyword)
        self.assertGreater(both, keyword)
        self.assertEqual(-1, none)


class ShellCss(unittest.TestCase):
    def test_every_variable_it_uses_is_defined(self):
        css = (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        defined = set()
        for name in ("tokens", "base", "components", "shell"):
            defined |= set(re.findall(r"(--[\w-]+)\s*:", (ROOT / "assets" / "css" / f"{name}.css").read_text(encoding="utf-8")))
        used = set(re.findall(r"var\((--[\w-]+)", css))
        self.assertEqual([], sorted(used - defined), "shell.css uses tokens that tokens.css (P01) does not define")


if __name__ == "__main__":
    unittest.main(verbosity=2)
