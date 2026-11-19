#!/usr/bin/env python3
"""Tests for the Explorer page (P13, P14b, P14d, P14e, P15, P16): router.js, model.js, highlight.js, blocks.js, markdown.js, jsonview.js and sql.js (pure), and explorer.html in jsdom.

    python scripts/test_explorer.py

Needs Node 18+. The page tests also need jsdom, installed once and kept out of git:
    npm install --prefix scripts/explorer_tests jsdom
Without jsdom those tests are skipped, the pure tests still run."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent / "explorer_tests"
NODE = shutil.which("node")


def run(script: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    return subprocess.run([NODE, str(HERE / script)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, env=env)


@unittest.skipUnless(NODE, "node is not on PATH")
class ExplorerTests(unittest.TestCase):
    def test_router_and_model(self):
        r = run("pure.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_highlight(self):
        """P14b: language choice, HTML -> segments, the vendored engine, and a round trip over the embedded source."""
        r = run("highlight.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_blocks(self):
        """P14d: line ranges, anchor search, block alignment, block / function at a line, card stacking, and every real note against its embedded source."""
        r = run("blocks.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_docs(self):
        """P14e: Markdown, JSON and SQL views: parsers, link safety, and every embedded .md / .json / .sql file of the repository."""
        r = run("docs.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_codelink(self):
        """P15: chapter code links (targets, lookup, card content, a chapter page in jsdom) and the Explorer's backlinks helper."""
        r = run("codelink.mjs")
        if r.returncode == 77:
            self.skipTest("jsdom is not installed: npm install --prefix scripts/explorer_tests jsdom")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_audit(self):
        """P16: the audit rules and store (hash reset, toggling, import / export, shared mode with a fake Sync)."""
        r = run("audit.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_compat_redirects(self):
        """P19: where explore.html#<path>, explore.html#<words>, code.html and functions.html go, and that the Explorer reads it back."""
        r = run("compat.mjs")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("FAIL", r.stdout)

    def test_page(self):
        r = run("page.mjs")
        if r.returncode == 77:
            self.skipTest("jsdom is not installed: npm install --prefix scripts/explorer_tests jsdom")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class CompatPages(unittest.TestCase):
    """P19: explore.html, code.html and functions.html are thin pages that forward to the Explorer (assets/js/compat.js)."""
    ROOT = Path(__file__).resolve().parent.parent

    def test_each_old_page_forwards_and_has_a_way_out_without_javascript(self):
        for name in ("explore", "code", "functions"):
            html = (self.ROOT / f"{name}.html").read_text(encoding="utf-8")
            self.assertIn(f'<body data-compat="{name}">', html)
            self.assertIn('<script type="module" src="assets/js/compat.js"></script>', html)
            self.assertIn('<noscript><meta http-equiv="refresh" content="0;url=explorer.html"></noscript>', html)
            self.assertIn('id="compat-link" href="explorer.html#/"', html)
            self.assertIn('content="noindex,nofollow"', html)
            self.assertLess(len(html), 4000, name)

    def test_the_titles_stay_distinct_so_search_results_and_tabs_still_tell_them_apart(self):
        titles = {n: next(l for l in (self.ROOT / f"{n}.html").read_text(encoding="utf-8").splitlines() if l.startswith("<title>")) for n in ("explore", "code", "functions")}
        self.assertEqual(3, len(set(titles.values())), titles)

    def test_they_are_hidden_from_the_sidebar_but_still_listed_so_check_site_knows_them(self):
        import json
        nav = json.loads((self.ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
        shown = {it["url"] for w in nav["wings"] for it in w["items"]}
        hidden = {it["url"]: it for it in nav["hidden"]}
        for name in ("explore.html", "code.html", "functions.html"):
            self.assertNotIn(name, shown)
            self.assertEqual("bare", hidden[name]["layout"])
        self.assertIn("explorer.html", shown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
