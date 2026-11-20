#!/usr/bin/env python3
"""Tests for the System page (patch P09). Run: python scripts/test_system.py

Covers assets/js/system-model.js (the pure parts, run in Node with no browser, on the committed model and on the miniature flows of
scripts/arch_render_fixtures.py), content/system/views.json (every chapter section, page and view it names must exist), architecture.html
(the page contract: the palette links to architecture.html#<view id>, so a section's id is its view id) and the rules the DOM layer
(system.js, system.css) must always keep: no innerHTML, no browser storage, no network address, no colour that is not a token.
Tests that need Node are skipped, not failed, when `node` is not on PATH. Standard library only.
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

import arch_render_fixtures as FX  # noqa: E402

NODE = shutil.which("node")
JS = ROOT / "assets" / "js"


def text(p):
    return Path(p).read_text(encoding="utf-8")


def load(rel):
    return json.loads(text(ROOT / rel))


def run_node(body, data=None):
    """Run `body` (ES module code that can use S (system-model) and M (arch/model) and `data`) and return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "arch").mkdir()
        shutil.copy(JS / "system-model.js", tmp / "system-model.js")
        shutil.copy(JS / "arch" / "model.js", tmp / "arch" / "model.js")
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as S from './system-model.js'; import * as M from './arch/model.js'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def flow_of(name):
    f = FX.FLOWS[name]()
    return f


@unittest.skipUnless(NODE, "node is not on PATH")
class PureHelpers(unittest.TestCase):
    def test_sections_follow_the_prose_order_and_cover_every_view(self):
        model, prose = load("data/arch/model.json"), load("content/system/views.json")
        out = run_node("console.log(JSON.stringify(S.viewSections(data.model, data.prose).map(s => s.id)))", {"model": model, "prose": prose})
        self.assertEqual(out, prose["order"])
        self.assertEqual(set(out), {v["id"] for v in model["views"]})

    def test_a_new_view_appears_without_prose_and_unknown_prose_ids_are_ignored(self):
        model = {"views": [{"id": "system", "title": "System map"}, {"id": "brand-new", "title": "Brand new", "type": "layered"}]}
        prose = {"order": ["ghost", "brand-new"], "views": {}}
        out = run_node("console.log(JSON.stringify(S.viewSections(data.model, data.prose)))", {"model": model, "prose": prose})
        self.assertEqual([s["id"] for s in out], ["brand-new", "system"])
        self.assertEqual(out[0]["what"], "")
        self.assertEqual(out[0]["chapters"], [])

    def test_no_model_and_no_prose_gives_an_empty_page_not_an_error(self):
        out = run_node("console.log(JSON.stringify([S.viewSections(null, null), S.flowSummary(null), S.stepRows(null), S.conflictRows(null), S.flowStatus(null)]))")
        self.assertEqual(out[0], [])
        self.assertEqual(out[1]["total"], 0)
        self.assertEqual(out[2:], [[], [], "missing"])

    def test_flow_summary_of_the_committed_index(self):
        idx = load("data/index/arch.json")
        out = run_node("console.log(JSON.stringify(S.flowSummary(data)))", idx)
        self.assertEqual(out["total"], len(idx["flows"]))
        self.assertEqual(out["written"] + len(out["missing"]), out["total"])
        self.assertEqual(sum(out["counts"].values()), out["total"])

    def test_flow_summary_counts_each_status(self):
        idx = {"flows": {"a": {"status": "fresh"}, "b": {"status": "stale"}, "c": {"status": "broken"}, "d": {"status": "missing", "title": "D", "kind": "pipeline"}, "e": {"status": "weird"}}}
        out = run_node("console.log(JSON.stringify(S.flowSummary(data)))", idx)
        self.assertEqual(out["counts"], {"fresh": 1, "unverified": 1, "stale": 1, "broken": 1, "missing": 1})
        self.assertEqual(out["written"], 4)
        self.assertEqual(out["missing"], [{"id": "d", "title": "D", "kind": "pipeline"}])

    def test_step_rows_come_from_the_flow_in_order(self):
        flow = flow_of("task-pipeline")
        nodes = {"backend/eo": {"label": "Orchestrator"}}
        rows = run_node("console.log(JSON.stringify(S.stepRows(data.flow, data.flow.commit, data.nodes)))", {"flow": flow, "nodes": nodes})
        self.assertEqual([r["n"] for r in rows], list(range(1, len(flow["steps"]) + 1)))
        self.assertEqual([r["id"] for r in rows], [s["id"] for s in flow["steps"]])
        stale = [r for r in rows if r["status"] == "stale"]
        self.assertEqual(len(stale), 1)
        gate = [r for r in rows if r["gate"]]
        self.assertEqual(gate[0]["gate"], {"tier": "T1", "who": "policy"})
        self.assertEqual(rows[2]["actor"], "Orchestrator")                       # a node label when the model has one
        self.assertEqual(rows[0]["actor"], "components")                         # else the last part of the path
        for r in rows:
            self.assertTrue(r["evidence"], "every step cites code")
            self.assertEqual(r["evidence"][0]["commit"], flow["commit"])

    def test_lifecycle_rows_are_transitions(self):
        flow = flow_of("taskrun-lifecycle")
        rows = run_node("console.log(JSON.stringify(S.stepRows(data, data.commit, {})))", flow)
        self.assertEqual(len(rows), len(flow["transitions"]))
        self.assertTrue(all(r["type"] == "transition" and "\u2192" in r["title"] for r in rows))

    def test_flow_status_and_confidence_use_the_worst_step(self):
        flow = flow_of("task-pipeline")
        out = run_node("console.log(JSON.stringify([S.flowStatus(data), S.flowConfidence(data), S.flowConfidence(null)]))", flow)
        self.assertEqual(out[0], flow.get("status") or "stale")
        self.assertEqual(out[1], "low")                                           # one low step is enough
        self.assertEqual(out[2], "")

    def test_anatomy_prefers_the_flow_and_falls_back_to_the_draft(self):
        draft, flow = load("content/system/request-path.json"), flow_of("task-sequence")
        a = run_node("console.log(JSON.stringify([S.anatomySteps(data.flow, data.draft, 'abc', {}), S.anatomySteps(null, data.draft, 'abc', {}), S.anatomySteps(null, null, 'abc', {})]))", {"flow": flow, "draft": draft})
        self.assertEqual(a[0]["source"], "flow")
        self.assertEqual(len(a[0]["steps"]), len(flow["steps"]))
        self.assertEqual(a[1]["source"], "draft")
        self.assertEqual([s["id"] for s in a[1]["steps"]], [s["id"] for s in draft["steps"]])
        self.assertTrue(all(s["code"] for s in a[1]["steps"]))
        self.assertEqual(a[2]["source"], "none")
        self.assertEqual(a[2]["steps"], [])

    def test_conflicts_link_to_the_chapter_section(self):
        flow = {"doc_conflicts": [{"chapter": "doc-minime-feature-guide#orchestrator", "note": "25 stages, code has 27"}, {"note": "no chapter"}, {}]}
        out = run_node("console.log(JSON.stringify(S.conflictRows(data)))", flow)
        self.assertEqual(out[0]["href"], "doc-minime-feature-guide.html#orchestrator")
        self.assertEqual(out[1]["href"], "")
        self.assertEqual(len(out), 2)

    def test_view_lookups(self):
        model = load("data/arch/model.json")
        out = run_node("console.log(JSON.stringify([S.viewForLegacy(data, 'architecture/task-sequence.html'), S.viewForLegacy(data, 'architecture/none.html'), S.viewIdForFlow(data, 'request-path'), S.viewIdForFlow(data, 'nope')]))", model)
        self.assertEqual(out, ["task-sequence", None, "task-sequence", None])


class Content(unittest.TestCase):
    prose = load("content/system/views.json")
    model = load("data/arch/model.json")

    def test_every_view_of_the_model_has_prose_and_every_prose_id_is_a_view(self):
        ids = {v["id"] for v in self.model["views"]}
        self.assertEqual(set(self.prose["views"]), ids)
        self.assertTrue(set(self.prose["order"]) <= ids)
        self.assertEqual(len(self.prose["order"]), len(set(self.prose["order"])))

    def test_chapter_refs_point_at_real_headings(self):
        book = {c["id"] for c in load("data/index/book.json")["chapters"]}
        for vid, v in self.prose["views"].items():
            for c in v.get("chapters", []):
                cid, _, frag = c["ref"].partition("#")
                self.assertIn(cid, book, f"{vid}: unknown chapter {cid}")
                if frag:
                    html = text(ROOT / f"{cid}.html")
                    self.assertIn(f'id="{frag}"', html, f"{vid}: {cid} has no heading #{frag}")
                self.assertTrue(c.get("label"), f"{vid}: {c['ref']} needs a label")

    def test_pages_exist(self):
        for vid, v in self.prose["views"].items():
            for p in v.get("pages", []):
                self.assertTrue((ROOT / p["url"].split("#")[0]).is_file(), f"{vid}: {p['url']} is not a page")

    def test_legend_has_the_semantic_colours(self):
        self.assertTrue({"flow", "gate", "sel", "stale"} <= {l["id"] for l in self.prose["legend"]})
        for l in self.prose["legend"]:
            self.assertTrue(l["label"] and l["text"])

    def test_prose_is_short(self):
        for vid, v in self.prose["views"].items():
            self.assertLessEqual(len(v["what"]), 420, vid)
            self.assertLessEqual(len(v.get("reading", "")), 240, vid)


class Page(unittest.TestCase):
    html = text(ROOT / "architecture.html")
    js = text(JS / "system.js")
    css = text(ROOT / "assets" / "css" / "system.css")

    def test_page_contract(self):
        self.assertIn("data-system-page", self.html)
        self.assertIn('assets/js/system.js', self.html)
        self.assertIn('assets/css/arch.css', self.html)
        self.assertIn('assets/css/system.css', self.html)
        self.assertLess(self.html.index("arch.css"), self.html.index("system.css"), "system.css must load after arch.css so it can size the diagram window")
        self.assertIn('<body data-page="architecture">', self.html)
        self.assertNotIn("<style", self.html, "the old per-page CSS is gone")

    def test_layout_matches_the_nav(self):
        nav = load("content/nav.json")
        item = next(i for w in nav["wings"] for i in w["items"] if i["id"] == "architecture")
        self.assertIn(f'data-layout="{item["layout"]}"', self.html)

    def test_legacy_diagrams_are_a_collapsed_block_of_links(self):
        m = re.search(r'<details class="sy-legacy">(.*?)</details>', self.html, re.S)
        self.assertIsNotNone(m)
        self.assertIn("not updated", m.group(1))
        files = sorted(p.name for p in (ROOT / "architecture").glob("*.html"))
        linked = sorted(re.findall(r'href="architecture/([^"]+)"', m.group(1)))
        self.assertEqual(linked, files)
        self.assertNotIn("<iframe", self.html, "legacy diagrams are links, never loaded into the page")

    def test_section_ids_are_view_ids_because_the_palette_links_there(self):
        self.assertIn("id: sec.id", self.js)
        build_index = text(ROOT / "scripts" / "build_index.py")
        self.assertIn('ARCH_PAGE = "architecture.html"', build_index)
        reserved = {"anatomy", "modules", "legacy"}
        self.assertFalse(reserved & {v["id"] for v in load("data/arch/model.json")["views"]})

    def test_dom_layer_rules(self):
        for name, src in (("system.js", self.js), ("system-model.js", text(JS / "system-model.js"))):
            self.assertNotRegex(src, r"innerHTML|insertAdjacentHTML|document\.write", name)
            self.assertNotRegex(src, r"localStorage|sessionStorage|indexedDB", name)
            self.assertNotRegex(src, r"https?://", f"{name} has a network address")
        self.assertNotRegex(text(JS / "system-model.js"), r"\bdocument\b|\bwindow\b", "system-model.js must stay free of the DOM")

    def test_css_uses_tokens_only(self):
        self.assertNotRegex(self.css, r"#[0-9a-fA-F]{3,8}\b", "no hex colours")
        self.assertNotRegex(self.css, r"\brgba?\(|\bhsla?\(", "no literal colours")
        self.assertIn("@media print", self.css)

    def test_every_pure_import_is_used_and_exists(self):
        for rel in re.findall(r'from "(\./[^"]+)"', self.js):
            self.assertTrue((JS / rel).exists(), f"system.js imports {rel}")
        for name in re.findall(r"\bS\.(\w+)", self.js):
            self.assertRegex(text(JS / "system-model.js"), rf"export (?:const|function) {name}\b|export \{{[^}}]*\b{name}\b", f"system.js uses S.{name}, which system-model.js does not export")


if __name__ == "__main__":
    unittest.main(verbosity=2)
