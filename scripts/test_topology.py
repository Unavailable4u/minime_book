#!/usr/bin/env python3
"""Tests for the live topology diagram (patch P08). Run: python scripts/test_topology.py

Covers assets/js/topology.js (its pure helpers, run in Node with no browser), content/topology.json (the curated layout, checked against
data/census.json so every box stands for real folders), data/graph/folders.json, data/index/vitals.json census.topology, index.html and
assets/css/topology.css. The tests that need Node are skipped, not failed, when `node` is not on PATH. The code that writes the two data
files is tested in scripts/test_refresh_atlas.py and scripts/test_refresh_graph.py. Standard library only.
"""
from __future__ import annotations

import copy
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

import check_site  # noqa: E402

NODE = shutil.which("node")
JS = ROOT / "assets" / "js"
TOPOLOGY_JS = JS / "topology.js"
LIBRARY_JS = JS / "library.js"
TOPOLOGY_CSS = ROOT / "assets" / "css" / "topology.css"
INDEX_HTML = ROOT / "index.html"


def text(path):
    return Path(path).read_text(encoding="utf-8")


def load(rel):
    return json.loads(text(ROOT / rel))


def run_node(body, data=None):
    """Run `body` (ES module code that can use `M`, the exports of topology.js, and `data`) in a temp folder holding topology.js and
    library.js (which it imports); return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(TOPOLOGY_JS, tmp / "topology.js")
        shutil.copy(LIBRARY_JS, tmp / "library.js")
        shutil.copy(JS / "svgview.js", tmp / "svgview.js")
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")        # no "reparsing as ES module" warning on stderr
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text("import * as M from './topology.js'; import fs from 'node:fs';\n"
                                     "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def js(expr, data=None):
    return run_node(f"console.log(JSON.stringify({expr}))", data)


@unittest.skipUnless(NODE, "node is not installed")
class PureHelpers(unittest.TestCase):
    def test_importing_the_module_in_node_does_not_boot_the_page(self):
        self.assertEqual(True, js("typeof M.buildModel === 'function'"))

    def test_fmtK(self):
        self.assertEqual(["0", "640", "1.0k", "18.6k", "99.9k", "120k", "0"], js("[0, 640, 1000, 18638, 99940, 120400, null].map(M.fmtK)"))

    def test_box_size_grows_with_code_lines_between_the_two_limits(self):
        out = js("[M.nodeSize(0, 100), M.nodeSize(100, 100), M.nodeSize(25, 100), M.nodeSize(5, 0), M.nodeSize(undefined, 100)]")
        self.assertEqual({"w": 112, "h": 44}, out[0])
        self.assertEqual({"w": 156, "h": 60}, out[1])
        self.assertEqual({"w": 134, "h": 52}, out[2])                      # the root of 0.25 is 0.5: the area follows the lines
        self.assertEqual({"w": 112, "h": 44}, out[3])
        self.assertEqual({"w": 112, "h": 44}, out[4])

    def test_line_width_is_logarithmic_and_a_declared_line_is_thin(self):
        w = js("[0, 1, 10, 100, 500].map(n => M.edgeWidth(n, 500)).concat([M.edgeWidth(5, 0), M.edgeWidth(-3, 10)])")
        self.assertEqual(1.5, w[0])
        self.assertEqual(10.0, w[4])
        self.assertEqual(sorted(w[:5]), w[:5], "more links never draw a thinner line")
        self.assertLess(w[2] - w[1], w[4] - w[3] + 8, "sanity: no jump")
        self.assertEqual([1.5, 1.5], w[5:])

    def test_zoom_is_clamped_and_rounded(self):
        self.assertEqual([1, 4, 1.25, 1], js("[M.clampZoom(0.2), M.clampZoom(9), M.clampZoom(1.2500001), M.clampZoom('x')]"))

    def test_the_longest_folder_prefix_claims_a_folder(self):
        nodes = [{"id": "pkg", "folders": ["m2c/src/m2c"]}, {"id": "tui", "folders": ["m2c/src/m2c/tui"]}, {"id": "api", "folders": ["backend/api"]}]
        out = js("['m2c/src/m2c/tui/x.py', 'm2c/src/m2c/runner.py', 'm2c/src/m2c/tuixx/a.py', 'backend/api', 'backend/apix/a.py', 'docs'].map(f => M.nodeOf(f, data))", nodes)
        self.assertEqual(["tui", "pkg", "pkg", "api", None, None], out, "a prefix must end at a slash: backend/apix is not backend/api")

    def test_link_weights_sum_per_direction_and_drop_internal_and_unclaimed_links(self):
        nodes = [{"id": "a", "folders": ["x/a", "x/a2"]}, {"id": "b", "folders": ["x/b"]}]
        pairs = [["x/a", "x/b", 5], ["x/a2", "x/b", 2], ["x/b", "x/a", 3], ["x/a", "x/a2", 99], ["x/a", "elsewhere", 7]]
        out = js("[...M.linkWeights(data.pairs, data.nodes)]", {"pairs": pairs, "nodes": nodes})
        self.assertEqual([["a>b", 7], ["b>a", 3]], out)

    def test_edge_rows_say_which_edges_are_live(self):
        nodes = [{"id": "a", "folders": ["a"]}, {"id": "b", "folders": ["b"]}, {"id": "c", "folders": ["c"]}]
        rows = js("M.edgeRows(data.edges, data.pairs, data.nodes)", {"edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "c", "declared": True}],
                                                                       "pairs": [["a", "b", 4], ["b", "a", 1]], "nodes": nodes})
        self.assertEqual((4, 1, 5, True), (rows[0]["fwd"], rows[0]["bwd"], rows[0]["links"], rows[0]["live"]))
        self.assertEqual((0, False), (rows[1]["links"], rows[1]["live"]))

    def test_clip_to_rect_leaves_a_box_on_its_edge(self):
        out = js("[M.clipToRect({x: 0, y: 0, w: 100, h: 40}, 200, 0), M.clipToRect({x: 0, y: 0, w: 100, h: 40}, 0, -90), M.clipToRect({x: 5, y: 5, w: 10, h: 10}, 5, 5)]")
        self.assertEqual([{"x": 50, "y": 0}, {"x": 0, "y": -20}, {"x": 5, "y": 5}], out)

    def test_a_straight_edge_runs_between_the_two_box_borders_and_labels_in_the_middle(self):
        p = js("M.edgePath({x: 0, y: 0, w: 20, h: 20}, {x: 100, y: 0, w: 20, h: 20})")
        self.assertEqual({"d": "M10 0L90 0", "mid": {"x": 50, "y": 0}}, p)

    def test_the_label_position_slides_along_the_line_and_is_kept_inside_it(self):
        a, b = "{x: 0, y: 0, w: 20, h: 20}", "{x: 100, y: 0, w: 20, h: 20}"
        out = js(f"[M.edgePath({a}, {b}, 0, 0.25).mid, M.edgePath({a}, {b}, 0, 7).mid, M.edgePath({a}, {b}, 0, -1).mid, M.edgePath({a}, {b}, 0, 'x').mid]")
        self.assertEqual([{"x": 30, "y": 0}, {"x": 90, "y": 0}, {"x": 10, "y": 0}, {"x": 50, "y": 0}], out)

    def test_a_bent_edge_curves_to_one_side_and_its_label_follows_the_curve(self):
        a, b = "{x: 0, y: 0, w: 20, h: 20}", "{x: 100, y: 0, w: 20, h: 20}"
        up, down = js(f"[M.edgePath({a}, {b}, 40), M.edgePath({a}, {b}, -40)]")
        self.assertTrue(up["d"].startswith("M") and "Q" in up["d"])
        self.assertEqual(-down["mid"]["y"], up["mid"]["y"], "the opposite bend mirrors it")
        self.assertNotEqual(0, up["mid"]["y"])
        early, late = js(f"[M.edgePath({a}, {b}, 40, 0.2).mid, M.edgePath({a}, {b}, 40, 0.8).mid]")
        self.assertLess(early["x"], up["mid"]["x"])
        self.assertGreater(late["x"], up["mid"]["x"])

    def test_the_frame_around_opened_parts_has_room_for_a_title(self):
        out = js("M.frameRect([{x: 10, y: 10, w: 20, h: 20}, {x: 50, y: 40, w: 20, h: 20}], 10, 30)")
        self.assertEqual({"x": 30, "y": 10, "w": 80, "h": 100}, out)
        self.assertIsNone(js("M.frameRect([])"))

    def test_a_request_step_touches_the_nodes_that_hold_its_code(self):
        nodes = [{"id": "api", "folders": ["backend/api"]}, {"id": "eo", "folders": ["backend/eo"]}]
        steps = [{"id": "s1", "title": "One", "code": [{"path": "backend/api/a.py"}, {"path": "backend/api/b.py"}, {"path": "backend/eo/r.py"}, {"path": "docs/x.md"}]},
                 {"id": "s2", "title": "Two", "code": [{"path": "backend/eo/z.py"}]}, {"id": "s3", "title": "None"}]
        out = js("(() => { const l = M.stepNodes(data.steps, data.nodes); return [l.map(s => s.nodes), M.pathSequence(l)]; })()", {"steps": steps, "nodes": nodes})
        self.assertEqual([[["api", "eo"], ["eo"], []], ["api", "eo"]], out, "a repeat of the node just before it is dropped from the path")

    def test_arrow_keys_pick_the_nearest_box_in_that_direction(self):
        c = [{"id": "m", "x": 100, "y": 100}, {"id": "r", "x": 200, "y": 105}, {"id": "r2", "x": 400, "y": 100}, {"id": "d", "x": 105, "y": 180}, {"id": "u", "x": 100, "y": 20}]
        out = js("['left', 'right', 'up', 'down', 'sideways'].map(k => M.nearestInDirection(data, 'm', k)).concat([M.nearestInDirection(data, 'nope', 'up')])", c)
        self.assertEqual([None, "r", "u", "d", None, None], out)

    def test_docstring_label_says_why_there_is_no_figure(self):
        out = js("[M.docsLabel(41, 50), M.docsLabel(0, 0)]")
        self.assertEqual("82 % of 50 Python functions have a docstring.", out[0])
        self.assertIn("No Python functions", out[1])

    def test_links_go_where_the_page_can_open_them(self):
        out = js("[M.explorerHref('backend/eo/a b.py'), M.githubTree('m2c/src/m2c', '94af156'), M.githubTree('a b/c', null), M.chapterHref('doc-x#5-y'), M.chapterHref('doc-x')]")
        self.assertEqual(["explore.html#backend%2Feo%2Fa%20b.py", "https://github.com/Unavailable4u/MiniMe/tree/94af156/m2c/src/m2c",
                          "https://github.com/Unavailable4u/MiniMe/tree/main/a%20b/c", "doc-x.html#5-y", "doc-x.html"], out)

    def test_a_label_needs_a_box_wide_enough_for_it_and_never_a_narrower_one(self):
        out = js("[M.fitWidth(124, 131), M.fitWidth(124, 80), M.fitWidth(72, 56, M.KID_PAD), M.fitWidth(72, 70, M.KID_PAD), M.fitWidth(100, null)]")
        self.assertEqual([151, 124, 72, 82, 100], out)

    def test_null_and_false_are_dropped_before_replaceChildren(self):
        self.assertEqual([1, 2, "x", 0], js("M.liveKids([1, null, [2, [false, 'x', undefined]], 0])"))

    def test_the_source_line_names_both_commits_and_warns_about_a_seed_or_a_mismatch(self):
        census = {"commit": "94af156abc", "generated": "2026-11-15T10:00:00"}
        fresh = js("M.sourceLine(data.c, {commit: '94af156', date: '2026-11-15', source: 'graphify'})", {"c": census})
        self.assertEqual(("fresh", []), (fresh["state"], fresh["notes"]))
        self.assertIn("94af156", fresh["text"])
        seed = js("M.sourceLine(data.c, {commit: '94af156', date: '2026-11-15', source: 'seed'})", {"c": census})
        self.assertEqual("stale", seed["state"])
        self.assertIn("approximation", seed["notes"][0])
        other = js("M.sourceLine(data.c, {commit: '50e25b5', date: '2026-10-01', source: 'graphify'})", {"c": census})
        self.assertEqual("stale", other["state"])
        self.assertIn("different commits", other["notes"][0])
        none = js("M.sourceLine(null, null)")
        self.assertEqual("stale", none["state"])
        self.assertIn("could not be loaded", none["notes"][0])

    def test_dragging_changes_only_x_and_y_and_keeps_the_key_order(self):
        spec = load("content/topology.json")
        out = js("M.exportSpec(data.spec, {db: {x: 12.4, y: 99.6}, nope: {x: 1, y: 1}})", {"spec": spec})
        new = json.loads(out)
        before, after = {n["id"]: n for n in spec["nodes"]}, {n["id"]: n for n in new["nodes"]}
        self.assertEqual((12, 100), (after["db"]["x"], after["db"]["y"]))
        self.assertEqual([i for i in before if i != "db"], [i for i in before if i != "db" and before[i] == after[i]])
        self.assertEqual({k: v for k, v in before["db"].items() if k not in "xy"}, {k: v for k, v in after["db"].items() if k not in "xy"})
        self.assertEqual(list(before["db"]), list(after["db"]))
        self.assertTrue(out.endswith("}\n"))

    def test_the_model_pairs_every_edge_with_its_graph_links_and_counts_in_and_out(self):
        spec, folders = load("content/topology.json"), load("data/graph/folders.json")
        counts = load("data/index/vitals.json")["census"]["topology"]
        m = js("(() => { const m = M.buildModel(data.spec, data.counts, data.folders); return {edges: m.edges, top: m.top.length, kids: m.nodes.length - m.top.length, max: m.maxLinks, io: [...m.io]}; })()",
               {"spec": spec, "counts": counts, "folders": folders})
        self.assertEqual(len(spec["edges"]), len(m["edges"]))
        self.assertEqual(11, m["top"])
        self.assertEqual(9, m["kids"])
        for e in m["edges"]:
            self.assertEqual(e["live"], e["width"] > 1.5 or e["links"] > 0)
            if e["live"]:
                self.assertGreater(e["width"], 1.5)
        self.assertEqual(max(e["links"] for e in m["edges"]), m["max"])


@unittest.skipUnless(NODE, "node is not installed")
class Geometry(unittest.TestCase):
    """The drawing rules that were found by eye, as checks: they fail when a layout change (or a ?edit=1 drag pasted back) breaks them."""

    def lines(self):
        spec, counts, folders = load("content/topology.json"), load("data/index/vitals.json")["census"]["topology"], load("data/graph/folders.json")
        body = """
const m = M.buildModel(data.spec, data.counts, data.folders);
const rect = (n) => ({ x: n.x, y: n.y, ...M.nodeSize(n.code, m.maxCode) });
const out = [];
for (const e of m.edges) {
  const a = m.byId.get(e.from), b = m.byId.get(e.to);
  const p = M.edgePath(rect(a), rect(b), e.bend || 0, e.label_t);
  const nums = p.d.match(/-?[\\d.]+/g).map(Number);
  const pts = [];
  for (let i = 0; i <= 100; i++) {
    const t = i / 100;
    if (nums.length === 6) { const u = 1 - t; pts.push([u*u*nums[0] + 2*u*t*nums[2] + t*t*nums[4], u*u*nums[1] + 2*u*t*nums[3] + t*t*nums[5]]); }
    else pts.push([nums[0] + (nums[2] - nums[0]) * t, nums[1] + (nums[3] - nums[1]) * t]);
  }
  const hits = [];
  for (const n of m.top) {
    if (n.id === e.from || n.id === e.to) continue;
    const r = rect(n), pad = 0;
    if (pts.some(([x, y]) => x > r.x - r.w/2 - pad && x < r.x + r.w/2 + pad && y > r.y - r.h/2 - pad && y < r.y + r.h/2 + pad)) hits.push(n.id);
  }
  out.push({ from: e.from, to: e.to, gate: !!e.gate, hits, inside: pts.every(([x, y]) => x >= 0 && x <= data.spec.view[0] && y >= 0 && y <= data.spec.view[1]), label: p.mid });
}
console.log(JSON.stringify(out));
"""
        return run_node(body, {"spec": spec, "counts": counts, "folders": folders})

    def test_no_line_runs_through_a_box_it_does_not_connect(self):
        bad = [(l["from"], l["to"], l["hits"]) for l in self.lines() if l["hits"]]
        self.assertEqual([], bad, "adjust x/y or add a bend in content/topology.json")

    def test_every_line_stays_inside_the_drawing(self):
        self.assertEqual([], [(l["from"], l["to"]) for l in self.lines() if not l["inside"]])

    def test_every_edge_label_sits_inside_the_drawing(self):
        w, h = load("content/topology.json")["view"]
        self.assertEqual([], [l["label"] for l in self.lines() if not (0 < l["label"]["x"] < w and 0 < l["label"]["y"] < h)])


class Layout(unittest.TestCase):
    """content/topology.json against the census, the graph file and the request path."""

    @classmethod
    def setUpClass(cls):
        cls.spec = load("content/topology.json")
        cls.census = load("data/census.json")
        cls.vitals = load("data/index/vitals.json")
        cls.nodes = {n["id"]: n for n in cls.spec["nodes"]}

    def test_node_ids_are_unique_and_every_node_has_what_the_card_shows(self):
        ids = [n["id"] for n in self.spec["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for n in self.spec["nodes"]:
            self.assertTrue(n.get("label") and n.get("what") and n.get("folders"), n["id"])
            self.assertIsInstance(n["x"], int, n["id"])
            self.assertIsInstance(n["y"], int, n["id"])
        self.assertEqual(20, len(ids))

    def test_parents_and_children_agree(self):
        for n in self.spec["nodes"]:
            for kid in n.get("children", []):
                self.assertEqual(n["id"], self.nodes[kid].get("parent"), f"{kid} is listed as a part of {n['id']}")
            if n.get("parent"):
                self.assertIn(n["id"], self.nodes[n["parent"]].get("children", []), n["id"])
                self.assertFalse(self.nodes[n["parent"]].get("parent"), "parts are one level deep")
        self.assertEqual(["m2c"], [n["id"] for n in self.spec["nodes"] if n.get("children")])
        self.assertEqual(9, len(self.nodes["m2c"]["children"]))

    def test_every_top_level_node_sits_inside_one_group_and_inside_the_drawing(self):
        w, h = self.spec["view"]
        groups = {g["id"]: g for g in self.spec["groups"]}
        for n in self.spec["nodes"]:
            if n.get("parent"):
                continue
            self.assertIn(n.get("group"), groups, n["id"])
            g = groups[n["group"]]
            self.assertTrue(g["x"] < n["x"] < g["x"] + g["w"] and g["y"] < n["y"] < g["y"] + g["h"], f"{n['id']} is outside its group")
        for g in self.spec["groups"]:
            self.assertTrue(0 <= g["x"] and g["x"] + g["w"] <= w and 0 <= g["y"] and g["y"] + g["h"] <= h, g["id"])

    def test_the_parts_fit_inside_the_machine_group_when_opened(self):
        g = next(g for g in self.spec["groups"] if g["id"] == "devices")
        for kid in self.nodes["m2c"]["children"]:
            k = self.nodes[kid]
            self.assertTrue(g["x"] + 12 <= k["x"] - 36 and k["x"] + 36 <= g["x"] + g["w"] - 12, f"{kid} sticks out of the group")
            self.assertTrue(g["y"] < k["y"] - 21 and k["y"] + 21 < g["y"] + g["h"], kid)

    def test_the_parts_do_not_overlap_each_other(self):
        kids = [self.nodes[k] for k in self.nodes["m2c"]["children"]]
        for i, a in enumerate(kids):
            for b in kids[i + 1:]:
                self.assertFalse(abs(a["x"] - b["x"]) < 72 and abs(a["y"] - b["y"]) < 42, f"{a['id']} overlaps {b['id']}")

    def test_edges_point_at_nodes_and_never_twice_at_the_same_pair(self):
        seen = set()
        for e in self.spec["edges"]:
            self.assertIn(e["from"], self.nodes)
            self.assertIn(e["to"], self.nodes)
            for key in ("from_child", "to_child"):
                if key in e:
                    self.assertEqual(e["from" if key == "from_child" else "to"], self.nodes[e[key]].get("parent"), key)
            pair = tuple(sorted((e["from"], e["to"])))
            self.assertNotIn(pair, seen, f"{pair} is drawn twice")
            seen.add(pair)
            self.assertTrue(isinstance(e.get("label_t", 0.5), (int, float)) and 0 <= e.get("label_t", 0.5) <= 1)
        self.assertEqual(13, len(self.spec["edges"]))

    def test_declared_edges_have_a_label_and_the_approval_gate_is_the_one_amber_line(self):
        for e in self.spec["edges"]:
            if e.get("declared"):
                self.assertTrue(e.get("label"), f"{e['from']} -> {e['to']} is declared, so it says what it is")
        gates = [e for e in self.spec["edges"] if e.get("gate")]
        self.assertEqual([("eo", "daemon")], [(e["from"], e["to"]) for e in gates])
        self.assertTrue(gates[0].get("declared"))
        self.assertIn("approval", gates[0]["label"])

    def test_chapter_and_diagram_links_exist(self):
        for n in self.spec["nodes"]:
            if n.get("chapter"):
                page, _, frag = n["chapter"].partition("#")
                f = ROOT / f"{page}.html"
                self.assertTrue(f.is_file(), f"{n['id']}: {page}.html")
                if frag:
                    self.assertIn(f'id="{frag}"', text(f), f"{n['id']}: #{frag} is not in {page}.html")
            if n.get("diagram"):
                self.assertTrue((ROOT / n["diagram"]).is_file(), f"{n['id']}: {n['diagram']}")

    def test_every_folder_of_every_node_holds_census_files_and_no_two_nodes_claim_the_same_one(self):
        paths = [f["path"] for f in self.census["files"]]
        claimed = {}
        for n in self.spec["nodes"]:
            for folder in n["folders"]:
                self.assertTrue(any(p.startswith(folder + "/") for p in paths), f"{n['id']}: {folder} holds no file of the census")
                if not n.get("children"):
                    self.assertNotIn(folder, claimed, f"{folder} is claimed by {claimed.get(folder)} and {n['id']}")
                    claimed[folder] = n["id"]

    def test_the_request_path_only_touches_nodes_that_are_drawn(self):
        steps = load("content/system/request-path.json")["steps"]
        top = [n for n in self.spec["nodes"] if not n.get("parent")]
        for s in steps:
            hits = {n["id"] for c in s.get("code", []) for n in top if any(c["path"].startswith(f + "/") or c["path"] == f for f in n["folders"])}
            self.assertTrue(hits, f"step {s['id']} would light up nothing in the diagram")

    def test_vitals_hold_numbers_for_exactly_the_nodes_drawn(self):
        t = self.vitals["census"]["topology"]
        self.assertEqual(set(self.nodes), set(t))
        for nid, row in t.items():
            self.assertGreater(row["files"], 0, nid)
            self.assertLessEqual(row["documented"], row["python_functions"], nid)
            self.assertLessEqual(row["python_functions"], row["functions"], nid)
            self.assertTrue(1 <= len(row["top"]) <= 3, nid)
            self.assertEqual(sorted((r["code"] for r in row["top"]), reverse=True), [r["code"] for r in row["top"]], nid)
        kids = self.nodes["m2c"]["children"]
        self.assertEqual(t["m2c"]["code"], sum(t[k]["code"] for k in kids), "the client is the sum of its parts")

    def test_the_numbers_in_vitals_come_from_the_committed_census(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import refresh_atlas as ra  # noqa: E402
        self.assertEqual(ra.topology_counts(self.census, self.spec), self.vitals["census"]["topology"], "run: python scripts/refresh_atlas.py")


class FoldersFile(unittest.TestCase):
    def test_shape(self):
        d = load("data/graph/folders.json")
        self.assertEqual(1, d["version"])
        self.assertIn(d["source"], ("graphify", "seed"))
        self.assertTrue(re.fullmatch(r"[0-9a-f]{7}", d["commit"]), d["commit"])
        self.assertTrue(re.fullmatch(r"\d{4}-\d\d-\d\d", d["date"]))
        self.assertIsInstance(d["nodes"], dict)
        for a, b, n in d["pairs"]:
            self.assertNotEqual(a, b)
            self.assertIsInstance(n, int)
            self.assertGreater(n, 0)
        self.assertEqual(sorted(d["pairs"], key=lambda r: (-r[2], r[0], r[1])), d["pairs"], "largest first, ties by name: a rebuilt graph gives a small diff")

    def test_a_graph_built_file_says_so_and_a_seed_is_honest_about_it(self):
        d = load("data/graph/folders.json")
        if d["source"] == "seed":
            self.assertEqual({}, d["nodes"], "a seed has no node counts of its own")
            self.assertIn("approximation", text(TOPOLOGY_JS), "the page must tell the reader a seed is approximate")

    def test_most_solid_edges_of_the_layout_have_graph_links(self):
        spec, d = load("content/topology.json"), load("data/graph/folders.json")
        if d["source"] == "seed":
            self.skipTest("data/graph/folders.json is still the seed table: run scripts/update_all.py to get the real link counts")
        top = [n for n in spec["nodes"] if not n.get("parent")]
        owner = lambda f: max(((len(x), n["id"]) for n in top for x in n["folders"] if f == x or f.startswith(x + "/")), default=(0, None))[1]
        linked = {tuple(sorted((owner(a), owner(b)))) for a, b, _ in d["pairs"] if owner(a) and owner(b) and owner(a) != owner(b)}
        undeclared = [e for e in spec["edges"] if not e.get("declared")]
        dead = [(e["from"], e["to"]) for e in undeclared if tuple(sorted((e["from"], e["to"]))) not in linked]
        self.assertLessEqual(len(dead), 1, f"edges drawn as graph links that the graph file does not have: {dead}")


class Page(unittest.TestCase):
    def test_index_loads_the_diagram_after_the_overview_and_has_one_place_for_it(self):
        html = text(INDEX_HTML)
        self.assertEqual(1, html.count("data-topology"))
        self.assertIn('<link rel="stylesheet" href="assets/css/topology.css">', html)
        self.assertIn('<script type="module" src="assets/js/topology.js"></script>', html)
        self.assertLess(html.index("overview.css"), html.index("topology.css"))
        self.assertIn('id="topology-h"', html)
        self.assertLess(len(html.encode("utf-8")), 6000, "index.html is a shell; the content lives in fragments and JSON")

    def test_replaceChildren_only_ever_gets_a_filtered_list(self):
        """replaceChildren(null) writes the text 'null' (a real bug of the first P08 cut: it showed above the card text).
        Every call goes through put(), which filters; the comments are not counted. Since P26 put() lives in svgview.js, shared by
        topology.js and the architecture views: topology.js must not call replaceChildren itself, svgview.js calls it once, in put()."""
        strip = lambda path: re.sub(r"/\*.*?\*/", "", text(path), flags=re.S)
        topo, shared = strip(TOPOLOGY_JS), strip(JS / "svgview.js")
        self.assertEqual([], [m.start() for m in re.finditer(r"\.replaceChildren\(", topo)], "call put(parent, ...kids) instead of replaceChildren")
        self.assertEqual(1, len(re.findall(r"\.replaceChildren\(", shared)))
        self.assertIn("function put(parent, ...kids) { parent.replaceChildren(...liveKids(kids)); }", shared)
        self.assertIn('from "./svgview.js"', topo)

    def test_the_card_closes_on_escape_even_though_focus_left_the_svg(self):
        src = text(TOPOLOGY_JS)
        self.assertRegex(src, r'(?s)E\.card = h\("aside".*?keydown:\s*\(ev\) => \{ if \(ev\.key === "Escape"')
        self.assertIn('ev.key === "Escape" && S.selected) select(null)', src)

    def test_the_script_has_no_browser_storage_and_no_network_beyond_the_site(self):
        src = text(TOPOLOGY_JS)
        for bad in ("localStorage", "sessionStorage", "XMLHttpRequest", "eval("):
            self.assertNotIn(bad, src)
        self.assertEqual([], re.findall(r"fetch\((?!new URL\(rel, BASE\))", src))

    def test_every_class_the_script_makes_has_a_rule_or_is_a_state_marker(self):
        js, css = text(TOPOLOGY_JS), text(TOPOLOGY_CSS)
        made = set(re.findall(r"\b(tp-[a-z0-9]+(?:__[a-z0-9]+)?(?:--[a-z0-9]+)?)\b", js))
        styled = set(re.findall(r"\.(tp-[a-z0-9]+(?:__[a-z0-9]+)?(?:--[a-z0-9]+)?)", css))
        # containers the script finds by class, and ids that look like classes: they need no rule of their own; tp-sw--live is the plain .tp-sw
        markers = {"tp-svg", "tp-edges", "tp-groups", "tp-nodes", "tp-badges", "tp-pathlayer", "tp-frame", "tp-title", "tp-keys", "tp-card-title", "tp-sw--live"}
        missing = sorted(c for c in made - styled - markers if not c.endswith("-"))
        self.assertEqual([], missing, "classes used in topology.js with no rule in topology.css")

    def test_the_css_uses_tokens_and_no_raw_colours(self):
        css = text(TOPOLOGY_CSS)
        self.assertEqual([], re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", css))
        tokens = text(ROOT / "assets" / "css" / "tokens.css")
        defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", tokens))
        used = set(re.findall(r"var\((--[a-z0-9-]+)", css))
        self.assertEqual([], sorted(u for u in used - defined if u not in {"--z-modal"}), "a token that tokens.css does not define")

    def test_the_diagram_has_its_own_font_so_it_does_not_depend_on_the_page(self):
        css = text(TOPOLOGY_CSS)
        self.assertRegex(css, r"\[data-topology\] \{[^}]*font-family: var\(--font-ui\)")

    def test_a_link_styled_as_a_button_keeps_its_own_colour_inside_the_overview(self):
        """overview.css colours every `.ov a` with the brand colour, which is also the primary button's background."""
        css = text(TOPOLOGY_CSS)
        self.assertRegex(css, r"\[data-topology\] a\.mm-btn--primary[^{]*\{\s*color: var\(--on-brand\)")


# --------------------------------------------------------------------------------------------- the checker's topology rules
CENSUS_FILES = {"app/a.py", "app/sub/b.py", "svc/c.py", "edge/d.py", "app/sub/k.py"}


def sample_spec():
    return {
        "version": 1, "view": [600, 400],
        "groups": [{"id": "left", "label": "Left", "x": 10, "y": 10, "w": 280, "h": 380}, {"id": "right", "label": "Right", "x": 310, "y": 10, "w": 280, "h": 380}],
        "nodes": [
            {"id": "app", "label": "App", "folders": ["app"], "group": "left", "x": 150, "y": 120, "what": "The app.", "children": ["app-sub"]},
            {"id": "app-sub", "label": "sub", "folders": ["app/sub"], "parent": "app", "x": 100, "y": 250, "what": "A part."},
            {"id": "svc", "label": "Service", "folders": ["svc"], "group": "right", "x": 450, "y": 120, "what": "The service."},
            {"id": "edge", "label": "Edge", "folders": ["edge"], "group": "right", "x": 450, "y": 300, "what": "The edge."},
        ],
        "edges": [{"from": "app", "to": "svc"}, {"from": "svc", "to": "edge", "declared": True, "label": "over HTTP"}],
    }


SAMPLE_VITALS = {"census": {"topology": {k: {"files": 1, "code": c} for k, c in (("app", 500), ("app-sub", 100), ("svc", 300), ("edge", 100))}}}
SAMPLE_PAIRS = {"pairs": [["app/a.py", "svc/c.py", 12]]}


def findings(spec, vitals=SAMPLE_VITALS, pairs=SAMPLE_PAIRS, census=CENSUS_FILES, files=("a.html",), problem=lambda *a, **k: None):
    tmp = Path(tempfile.mkdtemp())
    try:
        if vitals is not None:
            (tmp / "data" / "index").mkdir(parents=True)
            (tmp / "data" / "index" / "vitals.json").write_text(json.dumps(vitals), encoding="utf-8")
        if pairs is not None:
            (tmp / "data" / "graph").mkdir(parents=True)
            (tmp / "data" / "graph" / "folders.json").write_text(json.dumps(pairs), encoding="utf-8")
        got = []
        check_site.check_topology(tmp, spec, set(files), lambda level, code, file, detail, msg, line=None: got.append((level, code, detail)), problem, census)
        return got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class CheckerRules(unittest.TestCase):
    def mutate(self, fn, **kw):
        spec = sample_spec()
        fn(spec)
        return findings(spec, **kw)

    def test_the_valid_sample_has_no_findings(self):
        self.assertEqual([], findings(sample_spec()))

    def test_a_missing_file_means_nothing_to_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_site.run_checks(Path(tmp), allow=[])
        self.assertEqual([], [f for f in report.findings if f.code.startswith("topology-")])

    def test_the_real_layout_passes_the_site_checker_without_findings(self):
        report = check_site.run_checks(ROOT, allow=[])
        # While folders.json is still the seed table (before the first update_all run) its link counts are
        # only a rough copy of the Graph page, so a quiet line is not a finding yet.
        seed = load("data/graph/folders.json").get("source") == "seed"
        got = [str(f) for f in report.findings if f.code.startswith("topology-") and not (seed and f.code == "topology-edge-quiet")]
        self.assertEqual([], got)

    def test_the_sizes_the_checker_assumes_are_the_sizes_the_page_draws(self):
        js = text(TOPOLOGY_JS)
        box = dict(re.findall(r"(w0|w1|h0|h1):\s*(\d+)", re.search(r"export const BOX = \{[^}]*\}", js).group(0)))
        child = dict(re.findall(r"(w|h):\s*(\d+)", re.search(r"export const CHILD = \{[^}]*\}", js).group(0)))
        self.assertEqual({k: int(v) for k, v in box.items()}, check_site.TOPOLOGY_BOX)
        self.assertEqual({k: int(v) for k, v in child.items()}, check_site.TOPOLOGY_CHILD)

    def test_version_view_and_lists_must_have_the_right_shape(self):
        self.assertIn(("ERROR", "topology-bad-entry", "version"), self.mutate(lambda s: s.update(version=2)))
        self.assertIn(("ERROR", "topology-bad-entry", "view"), self.mutate(lambda s: s.update(view=[600])))
        self.assertIn(("ERROR", "topology-bad-entry", "view"), self.mutate(lambda s: s.update(view=[600, -4])))
        self.assertIn(("ERROR", "topology-bad-entry", "nodes"), self.mutate(lambda s: s.update(nodes={})))
        self.assertIn(("ERROR", "topology-bad-entry", "-"), findings([]))

    def test_ids_must_be_slugs_and_unique(self):
        def dup(s): s["nodes"][2]["id"] = "app"
        self.assertIn(("ERROR", "topology-bad-entry", "app"), self.mutate(dup))

        def bad(s): s["nodes"][2]["id"] = "Not A Slug"
        self.assertIn(("ERROR", "topology-bad-entry", "node#2"), self.mutate(bad))

        def gdup(s): s["groups"][1]["id"] = "left"
        self.assertIn(("ERROR", "topology-bad-entry", "left"), self.mutate(gdup))

    def test_a_node_needs_a_label_a_text_numbers_and_folders(self):
        def nolabel(s): del s["nodes"][2]["label"]
        self.assertIn(("ERROR", "topology-bad-entry", "svc|label"), self.mutate(nolabel))

        def notext(s): s["nodes"][2]["what"] = "  "
        self.assertIn(("ERROR", "topology-bad-entry", "svc|what"), self.mutate(notext))

        def noxy(s): s["nodes"][2]["x"] = "450"
        self.assertIn(("ERROR", "topology-bad-entry", "svc|xy"), self.mutate(noxy))

        def nofolders(s): s["nodes"][2]["folders"] = []
        self.assertIn(("ERROR", "topology-bad-entry", "svc|folders"), self.mutate(nofolders))

        def absolute(s): s["nodes"][2]["folders"] = ["/svc"]
        self.assertIn(("ERROR", "topology-bad-entry", "svc|folders"), self.mutate(absolute))

    def test_groups_parents_and_children_must_point_at_each_other(self):
        def nogroup(s): s["nodes"][2]["group"] = "nowhere"
        self.assertIn(("ERROR", "topology-bad-entry", "svc|group"), self.mutate(nogroup))

        def orphan(s): s["nodes"][0]["children"] = ["svc"]
        got = self.mutate(orphan)
        self.assertIn(("ERROR", "topology-bad-entry", "app|svc"), got)
        self.assertIn(("ERROR", "topology-bad-entry", "app-sub|parent"), got)

        def nested(s):
            s["nodes"][1]["children"] = ["svc"]
            s["nodes"][2]["parent"] = "app-sub"
        self.assertIn(("ERROR", "topology-bad-entry", "svc|nest"), self.mutate(nested))

    def test_an_edge_must_join_two_nodes_once_and_a_declared_one_needs_words(self):
        def unknown(s): s["edges"][0]["to"] = "ghost"
        self.assertIn(("ERROR", "topology-bad-entry", "edge#0"), self.mutate(unknown))

        def selfie(s): s["edges"][0]["to"] = "app"
        self.assertIn(("ERROR", "topology-bad-entry", "app->app"), self.mutate(selfie))

        def twice(s): s["edges"].append({"from": "svc", "to": "app"})
        self.assertIn(("ERROR", "topology-bad-entry", "svc->app"), self.mutate(twice), "the same pair the other way round is the same line")

        def nolabel(s): del s["edges"][1]["label"]
        self.assertIn(("ERROR", "topology-bad-entry", "svc->edge|label"), self.mutate(nolabel))

        def flag(s): s["edges"][1]["gate"] = "yes"
        self.assertIn(("ERROR", "topology-bad-entry", "svc->edge|gate"), self.mutate(flag))

        def bend(s): s["edges"][1]["bend"] = "70"
        self.assertIn(("ERROR", "topology-bad-entry", "svc->edge|bend"), self.mutate(bend))

        def label_t(s): s["edges"][1]["label_t"] = 1.5
        self.assertIn(("ERROR", "topology-bad-entry", "svc->edge|label_t"), self.mutate(label_t))

        def fc(s): s["edges"][0]["from_child"] = "svc"
        self.assertIn(("ERROR", "topology-bad-entry", "app->svc|from_child"), self.mutate(fc))

        def good_fc(s): s["edges"][0]["from_child"] = "app-sub"
        self.assertEqual([], self.mutate(good_fc))

    def test_a_folder_is_claimed_by_one_box_unless_it_is_a_part_of_it(self):
        def twice(s): s["nodes"][3]["folders"] = ["svc"]
        self.assertTrue(any(c == "topology-bad-entry" and d.endswith("|svc") for _, c, d in self.mutate(twice)))

        def part_same_folder(s): s["nodes"][1]["folders"] = ["app"]
        self.assertEqual([], self.mutate(part_same_folder), "the last part of M2C draws the folder of M2C itself")

    def test_folders_chapters_and_diagrams_must_exist(self):
        def nofolder(s): s["nodes"][3]["folders"] = ["edge/missing"]
        self.assertIn(("ERROR", "topology-bad-target", "edge|edge/missing"), self.mutate(nofolder))
        self.assertEqual([], self.mutate(nofolder, census=None), "no census, nothing to check against")

        def chapter(s): s["nodes"][2]["chapter"] = "doc-x#nope"
        got = self.mutate(chapter, problem=lambda t, is_file=False: "does not exist")
        self.assertIn(("ERROR", "topology-bad-target", "svc|doc-x#nope"), got)

        def diagram(s): s["nodes"][2]["diagram"] = "architecture/none.html"
        self.assertIn(("ERROR", "topology-bad-target", "svc|architecture/none.html"), self.mutate(diagram))
        self.assertEqual([], self.mutate(diagram, files=("a.html", "architecture/none.html")))

    def test_a_box_must_be_inside_the_diagram_and_its_group(self):
        def out_of_view(s): s["nodes"][2]["x"] = 590
        self.assertIn(("ERROR", "topology-bad-layout", "svc|view"), self.mutate(out_of_view))

        def wrong_group(s): s["nodes"][2]["x"] = 150
        self.assertIn(("ERROR", "topology-bad-layout", "svc|group"), self.mutate(wrong_group))

        def part(s): s["nodes"][1]["x"] = 400
        self.assertIn(("ERROR", "topology-bad-layout", "app-sub|group"), self.mutate(part), "a part must stay inside the group of the box it opens from")

        def big_group(s): s["groups"][1]["w"] = 400
        self.assertIn(("ERROR", "topology-bad-layout", "right|view"), self.mutate(big_group))

    def test_the_layout_rule_uses_the_size_the_box_is_really_drawn_at(self):
        """A small box may sit closer to its frame than the biggest box could; the page sizes a box by its code lines."""
        def near_edge(s): s["nodes"][3]["x"], s["nodes"][3]["y"] = 310 + 60, 300      # 60 from the frame: fits the smallest box (56), not the biggest (78)
        small = {"census": {"topology": {"edge": {"files": 1, "code": 1}, "app": {"files": 1, "code": 100000}, "svc": {"files": 1, "code": 10}, "app-sub": {"files": 1, "code": 1}}}}
        self.assertEqual([], self.mutate(near_edge, vitals=small))
        big = {"census": {"topology": {"edge": {"files": 1, "code": 100000}, "app": {"files": 1, "code": 10}, "svc": {"files": 1, "code": 10}, "app-sub": {"files": 1, "code": 1}}}}
        self.assertIn(("ERROR", "topology-bad-layout", "edge|group"), self.mutate(near_edge, vitals=big))

    def test_a_malformed_folder_table_is_an_error(self):
        for bad in ({"pairs": [["a", "b"]]}, {"pairs": [["a", "b", 0]]}, {"pairs": [["a", "b", "3"]]}, {"pairs": "x"}, [], {"pairs": [["a", "b", True]]}):
            self.assertIn(("ERROR", "topology-bad-data", "pairs"), findings(sample_spec(), pairs=bad), bad)

    def test_a_line_without_links_that_is_not_declared_is_a_warning(self):
        got = findings(sample_spec(), pairs={"pairs": [["svc/c.py", "edge/d.py", 3]]})
        self.assertEqual([("WARN", "topology-edge-quiet", "app->svc")], got)
        self.assertEqual([], findings(sample_spec(), pairs=None), "no folders.json yet: nothing to compare against")

    def test_links_between_parts_count_for_the_line_of_their_parent(self):
        self.assertEqual([], findings(sample_spec(), pairs={"pairs": [["app/sub/k.py", "svc/c.py", 2]]}))

    def test_a_box_with_no_numbers_is_a_stale_warning(self):
        vitals = copy.deepcopy(SAMPLE_VITALS)
        del vitals["census"]["topology"]["edge"]
        self.assertEqual([("WARN", "topology-stale", "edge")], findings(sample_spec(), vitals=vitals))
        vitals["census"]["topology"]["edge"] = {"files": 0, "code": 0}
        self.assertEqual([("WARN", "topology-stale", "edge")], findings(sample_spec(), vitals=vitals), "a folder with no files is just as unmeasured")
        self.assertEqual([("WARN", "topology-stale", "-")], findings(sample_spec(), vitals={"census": {}}))
        self.assertEqual([], findings(sample_spec(), vitals=None), "no vitals file: nothing to compare against")


class RealDataLinks(unittest.TestCase):
    def test_a_line_that_is_not_declared_has_graph_links_and_a_declared_one_has_none(self):
        spec, folders = load("content/topology.json"), load("data/graph/folders.json")
        if folders.get("source") == "seed":
            self.skipTest("data/graph/folders.json is still the seed table: run scripts/update_all.py to get the real link counts")
        by = {n["id"]: n for n in spec["nodes"]}
        wrong = []
        for e in spec["edges"]:
            links = check_site._topology_links(by, e["from"], e["to"], folders["pairs"])
            name = f'{e["from"]}->{e["to"]}'
            if e.get("declared") and links:
                wrong.append(f'{name} is declared but the graph has {links} links across it: drop "declared" (keep the label) so it gets a width')
            elif not e.get("declared") and not links:
                wrong.append(f'{name} is not declared but the graph has no links across it: add "declared": true and a "label"')
        self.assertEqual([], wrong, "content/topology.json no longer matches data/graph/folders.json (source: %s)" % folders.get("source"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
