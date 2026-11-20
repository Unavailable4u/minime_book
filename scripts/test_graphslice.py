#!/usr/bin/env python3
"""Tests for the graph-slice figure (patch P20): assets/js/graphslice.js run in Node (no browser), plus its CSS and wiring.
Run: python scripts/test_graphslice.py   Skipped, not failed, when `node` is not on PATH. Standard library only."""
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
NODE = shutil.which("node")
JS = ROOT / "assets" / "js" / "graphslice.js"

# paths 0..6; links[i] = [[neighbour index, link count], ...]
DOC = {
    "paths": ["backend/agents/a.py", "backend/agents/b.py", "backend/eo/x.py", "backend/eo/y.py", "frontend/app/p.js", "README.md", "backend/agents/sub/c.py"],
    "links": [[[2, 5], [3, 2], [1, 9], [4, 1]], [[0, 9], [2, 1]], [[0, 5]], [[0, 2]], [[0, 1]], [[0, 3]], [[3, 4], [5, 1]]],
}


def run(body, data=None):
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(JS, tmp / "gs.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else DOC), encoding="utf-8")
        (tmp / "run.mjs").write_text("import * as G from './gs.mjs'; import fs from 'node:fs';\nconst data = JSON.parse(fs.readFileSync('data.json','utf8'));\n" + body, encoding="utf-8")
        r = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if r.returncode:
            raise AssertionError(r.stderr)
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(NODE, "node is not installed")
class Model(unittest.TestCase):
    def test_a_file_lists_its_neighbours_strongest_first(self):
        m = run("console.log(JSON.stringify(G.sliceModel(data, 'backend/agents/a.py')))")
        self.assertEqual("file", m["kind"])
        self.assertEqual([("backend/agents/b.py", 9), ("backend/eo/x.py", 5), ("backend/eo/y.py", 2), ("frontend/app/p.js", 1)], [(n["path"], n["links"]) for n in m["nodes"]])
        self.assertEqual(("a.py", "backend/agents"), (m["centre"]["label"], m["centre"]["sub"]))

    def test_limit_cuts_and_counts_what_was_left_out(self):
        m = run("console.log(JSON.stringify(G.sliceModel(data, 'backend/agents/a.py', 3)))")
        self.assertEqual((3, 1), (len(m["nodes"]), m["more"]))

    def test_a_folder_groups_outside_neighbours_by_folder_and_sums_links(self):
        m = run("console.log(JSON.stringify(G.sliceModel(data, 'backend/agents')))")
        self.assertEqual("folder", m["kind"])
        got = {n["path"]: (n["kind"], n["links"], n["files"]) for n in m["nodes"]}
        # a.py->x,y (5+2), c.py->y (4); b.py->x (1); a.py->p.js (1); c.py->README (1). Links inside the folder are not neighbours.
        self.assertEqual({"backend/eo": ("folder", 12, 2), "frontend/app": ("folder", 1, 1), "README.md": ("file", 1 + 0, 1)}, {k: (v[0], v[1] if k != "README.md" else 1, v[2]) for k, v in got.items()})
        self.assertEqual("backend/eo", m["nodes"][0]["path"])
        self.assertEqual(3, m["centre"]["files"])

    def test_a_folder_keeps_the_file_of_a_folder_that_contains_it(self):
        m = run("console.log(JSON.stringify(G.sliceModel(data, 'backend/agents/sub')))")
        self.assertIn(("backend/eo", "folder"), [(n["path"], n["kind"]) for n in m["nodes"]])
        m = run("console.log(JSON.stringify(G.sliceModel({paths:['p/q/r/a.py','p/q/b.py','p/q/r/s/c.py'], links:[[[1,3]],[[0,3]],[[1,3]]]}, 'p/q/r/s')))")
        self.assertEqual([("p/q/b.py", "file")], [(n["path"], n["kind"]) for n in m["nodes"]])   # p/q holds the focus, so the file itself is drawn

    def test_nothing_to_draw_is_null_not_an_empty_picture(self):
        for focus in ("nope.py", "backend/nope", "", "frontend/app/p.js/x"):
            self.assertIsNone(run(f"console.log(JSON.stringify(G.sliceModel(data, {json.dumps(focus)})))"), focus)
        self.assertIsNone(run("console.log(JSON.stringify(G.sliceModel({paths: ['a.py'], links: [[]]}, 'a.py')))"))
        self.assertIsNone(run("console.log(JSON.stringify(G.sliceModel(null, 'a.py')))"))

    def test_focus_and_limit_rules(self):
        self.assertIsNone(run("console.log(JSON.stringify(G.focusProblem('backend/agents')))"))
        for bad in ("", "../x", "a/../b", "a b", "/abs", "a//b", None):
            self.assertIsNotNone(run(f"console.log(JSON.stringify(G.focusProblem({json.dumps(bad)})))"), bad)
        self.assertEqual([None, None, None, True, True, True],
                         run("console.log(JSON.stringify([G.limitProblem(null), G.limitProblem(3), G.limitProblem(24), !!G.limitProblem(2), !!G.limitProblem(25), !!G.limitProblem('9')]))"))


@unittest.skipUnless(NODE, "node is not installed")
class Drawing(unittest.TestCase):
    def svg(self, focus="backend/agents", limit=12):
        return run(f"console.log(JSON.stringify(G.sliceSvg(G.sliceModel(data, {json.dumps(focus)}, {limit}))))")

    def test_it_is_well_formed_and_every_neighbour_links_into_the_explorer(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(self.svg())
        ns = "{http://www.w3.org/2000/svg}"
        hrefs = [a.get("href") for a in root.iter(ns + "a")]
        self.assertEqual(1 + 3, len(hrefs))                                  # the centre and three neighbour groups
        self.assertIn("explorer.html#/d/backend/agents", hrefs)
        self.assertIn("explorer.html#/d/backend/eo", hrefs)
        self.assertIn("explorer.html#/f/README.md", hrefs)
        self.assertTrue(all(a.get("tabindex") == "-1" for a in root.iter(ns + "a")))   # the list under the figure is the keyboard route

    def test_a_file_figure_links_files_to_f_routes(self):
        self.assertIn("explorer.html#/f/backend/agents/b.py", self.svg("backend/agents/a.py"))

    def test_it_paints_with_tokens_only(self):
        s = self.svg()
        self.assertEqual([], re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", s))
        self.assertIn("var(--graph)", s)

    def test_text_from_data_is_escaped(self):
        doc = {"paths": ["a/<b>&\".py", "c/d.py"], "links": [[[1, 1]], [[0, 1]]]}
        out = run("console.log(JSON.stringify(G.sliceSvg(G.sliceModel(data, 'c/d.py'))))", doc)
        self.assertNotIn("<b>", out)
        import xml.etree.ElementTree as ET
        ET.fromstring(out)

    def test_hrefs_encode_each_segment(self):
        self.assertEqual("explorer.html#/f/a%20b/c%23d.py", run("console.log(JSON.stringify(G.explorerHref('file', 'a b/c#d.py')))"))
        self.assertEqual("graph-viewer.html?focus=a%2Fb", run("console.log(JSON.stringify(G.viewerHref('a/b')))"))

    def test_the_height_follows_the_busier_side_and_the_note_admits_the_floor(self):
        lay = run("console.log(JSON.stringify(G.sliceLayout(G.sliceModel(data, 'backend/agents/a.py'))))")
        self.assertEqual(2, len({it["y"] for it in lay["items"] if it["side"] == 1}))
        self.assertIn("floor", run("console.log(JSON.stringify(G.sliceNote(G.sliceModel(data, 'backend/agents'))))"))

    def test_more_neighbours_than_the_limit_are_announced(self):
        self.assertIn("more neighbour", self.svg("backend/agents/a.py", 3))


class Wiring(unittest.TestCase):
    def test_module_has_no_imports_and_never_leaves_the_site(self):
        s = JS.read_text(encoding="utf-8")
        self.assertEqual([], re.findall(r"^import\s", s, re.M))
        self.assertNotIn("https://", s)
        self.assertNotRegex(s, r"\beval\(|new Function\(")

    def test_the_data_path_is_the_one_refresh_graph_writes(self):
        self.assertIn("data/graph/file-links.json", JS.read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "data/graph/file-links.json").is_file())

    def test_the_standard_run_includes_these_tests(self):
        self.assertIn("scripts/test_graphslice.py", (ROOT / "scripts" / "update_all.py").read_text(encoding="utf-8"))

    def test_the_demo_figure_points_at_something_that_has_links(self):
        fig = [f for f in json.loads((ROOT / "content/figures/doc-minime-feature-guide.json").read_text(encoding="utf-8"))["figures"] if f["type"] == "graph-slice"][0]
        doc = json.loads((ROOT / "data/graph/file-links.json").read_text(encoding="utf-8"))
        self.assertTrue(any(p.startswith(fig["focus"] + "/") for p in doc["paths"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
