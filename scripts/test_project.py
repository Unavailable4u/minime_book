#!/usr/bin/env python3
"""Tests for the Project wing alignment (patch P21). Run: python scripts/test_project.py

Covers: the ten Project pages and assets/css/project.css, the stable Golden Rule ids on decisions.html (G-01 ... G-15),
the Explorer links on progress.html and health.html (every one must resolve against data/census.json), and the
rule-callout deep link in reader.js (calloutRef) with its entry in content/reader.json.
The Node tests are skipped, not failed, when `node` is not on PATH; the jsdom page test (scripts/explorer_tests/project.mjs)
is skipped when jsdom is not installed. Standard library only.
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
from urllib.parse import unquote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
WING = ["roadmap", "todo", "build", "progress", "decisions", "consistency", "journey", "tests", "health", "finance"]


def page(name: str) -> str:
    return (ROOT / f"{name}.html").read_text(encoding="utf-8")


def census_files() -> dict:
    return {f["path"]: f for f in json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))["files"]}


class WingWiring(unittest.TestCase):
    def test_every_page_is_in_the_wing_and_loads_project_css_last(self):
        for name in WING:
            s = page(name)
            self.assertIn(f'<body data-page="{name}" data-wing="project">', s, name)
            shell, proj = s.find("assets/css/shell.css"), s.find("assets/css/project.css")
            self.assertGreater(shell, 0, name)
            self.assertGreater(proj, shell, f"{name}: project.css must load after shell.css")
            self.assertEqual(s.count("assets/css/project.css"), 1, name)

    def test_sync_js_is_untouched_in_behaviour(self):
        # P21 is styles only for the to-do and finance pages: the same scripts, in the same order, as before
        for name in ("todo", "roadmap"):
            self.assertIn('src="sync.js"', page(name), name)

    def test_css_is_scoped_to_the_wing_and_uses_tokens(self):
        css = (ROOT / "assets" / "css" / "project.css").read_text(encoding="utf-8")
        body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        def top_level_parts(sel):
            parts, depth, cur = [], 0, ""
            for ch in sel:
                depth += ch in "([" and 1 or ch in ")]" and -1 or 0
                if ch == "," and depth == 0:
                    parts.append(cur)
                    cur = ""
                else:
                    cur += ch
            return parts + [cur]

        for sel in re.findall(r"([^{}]+)\{", body):
            for part in top_level_parts(sel):
                part = part.strip()
                if part.startswith("@media") or not part:
                    continue
                self.assertTrue(part.startswith('body[data-wing="project"]'), f"unscoped selector: {part}")
        self.assertNotRegex(body, r"#[0-9a-fA-F]{3,8}\b", "project.css must use tokens, not hard-coded colours")
        defined = set(re.findall(r"--[a-z0-9-]+(?=\s*:)", (ROOT / "assets" / "css" / "tokens.css").read_text(encoding="utf-8")))
        used = set(re.findall(r"var\((--[a-z0-9-]+)", body))
        self.assertFalse(used - defined, f"tokens that do not exist: {sorted(used - defined)}")


class Decisions(unittest.TestCase):
    def setUp(self):
        self.s = page("decisions")
        self.ids = re.findall(r'<div class="card dec" id="([^"]+)"', self.s)

    def test_golden_rules_have_stable_ids(self):
        rules = [i for i in self.ids if i.startswith("G-")]
        self.assertEqual(rules, [f"G-{n:02d}" for n in range(1, 16)])
        self.assertFalse([i for i in self.ids if re.fullmatch(r"G\d+", i)], "an old-style id is still used")

    def test_all_86_decisions_are_static_unique_and_anchored(self):
        self.assertEqual(len(self.ids), 86)
        self.assertEqual(len(set(self.ids)), 86)
        all_ids = re.findall(r'\bid="([^"]+)"', self.s)
        self.assertEqual(len(all_ids), len(set(all_ids)), "duplicate element ids on the page")
        for i in self.ids:
            self.assertIn(f'<a class="dec-id" href="#{i}">', self.s)
            self.assertIn(f'<label for="c-{i}">', self.s)

    def test_golden_rules_link_to_the_rulebook_section_that_exists(self):
        self.assertIn('href="doc-rulebook.html#1-the-15-golden-rules"', self.s)
        self.assertIn('id="1-the-15-golden-rules"', page("doc-rulebook"))

    def test_old_keys_are_migrated_and_listed(self):
        m = re.search(r"var LEGACY=(\{.*?\});", self.s)
        self.assertTrue(m)
        legacy = json.loads(m.group(1))
        self.assertEqual(legacy, {f"G{n}": f"G-{n:02d}" for n in range(1, 16)})

    def test_roadmap_still_counts_locks_by_prefix(self):
        # roadmap.html counts every localStorage key that starts with atlas:dec: and is "1"; the new keys keep that prefix
        self.assertIn("startsWith('atlas:dec:')", page("roadmap"))
        self.assertIn("var K='atlas:dec:'", self.s)

    @unittest.skipUnless(NODE, "node is not installed")
    def test_page_behaviour_in_jsdom(self):
        r = subprocess.run([NODE, str(ROOT / "scripts" / "explorer_tests" / "project.mjs")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120, env={"NODE_NO_WARNINGS": "1", "PATH": __import__("os").environ.get("PATH", "")})
        if r.returncode == 77:
            self.skipTest("jsdom is not installed (npm install --prefix scripts/explorer_tests jsdom)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class ExplorerLinks(unittest.TestCase):
    def test_progress_file_names_are_links_that_resolve(self):
        files, s = census_files(), page("progress")
        links = re.findall(r'<span><a href="explorer\.html#/f/([^"]+)" title="([^"]+)">', s)
        self.assertGreaterEqual(len(links), 30)
        for href, title in links:
            self.assertEqual(unquote(href), title)
            self.assertIn(title, files, f"progress links to a file that is not in the census: {title}")
        self.assertNotRegex(s, r'<span title="[^"]+">[^<]*</span><i ', "a progress bar still has a plain file name")

    def test_health_largest_functions_open_the_symbol(self):
        files, s = census_files(), page("health")
        seg = s[s.index("<h2>Largest functions</h2>"): s.index("<h2>Biggest files</h2>")]
        rows = re.findall(r'<tr><td><a href="explorer\.html#/f/([^":]+)::([^"?]+)\?tab=symbols">([^<]+)</a></td>', seg)
        self.assertEqual(len(rows), 15)
        for path, qual, name in rows:
            quals = {f["qual"] for f in files[unquote(path)].get("functions", [])}
            self.assertIn(unquote(qual), quals, f"{path}::{qual} is not a symbol in the census")
            self.assertEqual(unquote(qual).split(".")[-1], name)

    def test_health_risk_board_links_to_symbols_too(self):
        files, s = census_files(), page("health")
        seg = s[s.index("<h2>Risk board"): s.index("<h2>Largest functions</h2>")]
        paths = re.findall(r'<a class="l" href="explorer\.html#/f/([^"?]+)\?tab=symbols">symbols</a>', seg)
        self.assertGreaterEqual(len(paths), 10)
        for p in paths:
            self.assertIn(unquote(p), files)


@unittest.skipUnless(NODE, "node is not installed")
class RuleCallouts(unittest.TestCase):
    def run_node(self, body, data=None):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "assets" / "js" / "reader.js", tmp / "reader.mjs")
            (tmp / "data.json").write_text(json.dumps(data or {}), encoding="utf-8")
            (tmp / "run.mjs").write_text("import * as R from './reader.mjs'; import fs from 'node:fs';\n"
                                         "const data = JSON.parse(fs.readFileSync('data.json','utf8'));\n" + body, encoding="utf-8")
            res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            self.assertEqual(res.returncode, 0, res.stderr)
            return json.loads(res.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def cfg(self):
        return json.loads((ROOT / "content" / "reader.json").read_text(encoding="utf-8"))

    def test_rule_n_links_to_g_nn(self):
        out = self.run_node(
            "const rules = R.compileCallouts(data.callouts);"
            "const t = (s) => { const r = R.classifyCallout(s, rules); return r && R.calloutRef(r, s); };"
            "console.log(JSON.stringify([t('Golden Rule 7: never one vendor'), t('Rule 15: last'), t('Rule 16: past the list'), t('Rule: no number'), t('Rule 0: zero'), t('Purpose: x')]));",
            self.cfg())
        self.assertEqual(out[0], {"href": "decisions.html#G-07", "label": "G-07"})
        self.assertEqual(out[1], {"href": "decisions.html#G-15", "label": "G-15"})
        self.assertEqual(out[2], {"href": "decisions.html", "label": "Decisions"}, "above hrefMax falls back")
        self.assertEqual(out[3], {"href": "decisions.html", "label": "Decisions"})
        self.assertEqual(out[4], {"href": "decisions.html", "label": "Decisions"})
        self.assertIsNone(out[5], "a callout without a reference has none")

    def test_plain_href_rules_are_unchanged(self):
        out = self.run_node("console.log(JSON.stringify([R.calloutRef({href:'a.html',hrefLabel:'A'}, 'x'), R.calloutRef({href:'a.html'}, 'x'), R.calloutRef({}, 'x'), R.calloutRef(null, 'x')]));")
        self.assertEqual(out, [{"href": "a.html", "label": "A"}, {"href": "a.html", "label": "a.html"}, None, None])

    def test_every_target_the_config_can_make_exists_on_decisions_page(self):
        rule = next(r for r in self.cfg()["callouts"] if "hrefTemplate" in r)
        s = page("decisions")
        for n in range(1, rule["hrefMax"] + 1):
            href = rule["hrefTemplate"].replace("{nn}", f"{n:02d}")
            self.assertIn(f'id="{href.split("#")[1]}"', s, href)
        self.assertEqual(rule["hrefMax"], 15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
