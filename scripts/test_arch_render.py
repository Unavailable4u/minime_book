#!/usr/bin/env python3
"""Tests for the architecture renderer (patch P26). Run: python scripts/test_arch_render.py

Covers assets/js/svgview.js and assets/js/arch/{model,layout,sequence,lifecycle,catalog}.js: the pure parts, run in Node with no browser, on the
committed model (data/arch/) and on the miniature flows of scripts/arch_render_fixtures.py (no real flow is written yet). The DOM parts
(render.js, panel.js) are checked for the rules that must always hold: no innerHTML, no browser storage, no network address, no colour that is not
a token. Tests that need Node are skipped, not failed, when `node` is not on PATH. Standard library only.
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
import check_site  # noqa: E402

NODE = shutil.which("node")
JS = ROOT / "assets" / "js"
ARCH_JS = JS / "arch"
PURE = ["model.js", "layout.js", "sequence.js", "lifecycle.js", "catalog.js"]


def text(p):
    return Path(p).read_text(encoding="utf-8")


def load(rel):
    return json.loads(text(ROOT / rel))


def run_node(body, data=None):
    """Run `body` (ES module code that can use M (model), L (layout), S (sequence), C (lifecycle), K (catalog), V (svgview) and `data`) and return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "arch").mkdir()
        shutil.copy(JS / "svgview.js", tmp / "svgview.js")
        for f in PURE:
            shutil.copy(ARCH_JS / f, tmp / "arch" / f)
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as M from './arch/model.js'; import * as L from './arch/layout.js'; import * as S from './arch/sequence.js';\n"
            "import * as C from './arch/lifecycle.js'; import * as K from './arch/catalog.js'; import * as V from './svgview.js'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def rects_overlap(rects):
    bad = []
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if abs(a["x"] - b["x"]) < (a["w"] + b["w"]) / 2 and abs(a["y"] - b["y"]) < (a["h"] + b["h"]) / 2:
                bad.append((a.get("id"), b.get("id")))
    return bad


@unittest.skipUnless(NODE, "node is not installed")
class Model(unittest.TestCase):
    def test_status_helpers(self):
        out = run_node("""console.log(JSON.stringify([M.worstStatus(['fresh','stale','unverified']), M.worstStatus(['fresh','broken','stale']), M.worstStatus([]),
          M.viewStatus({source:'derived'}), M.viewStatus({source:'flow', flow_data:null}), M.viewStatus({source:'flow', flow_data:{status:'stale'}}), M.viewStatus(null)]));""")
        self.assertEqual(["stale", "broken", "unverified", "derived", "missing", "stale", "missing"], out)

    def test_flow_helpers_follow_the_steps(self):
        flow = FX.pipeline()
        out = run_node("""const f = data; console.log(JSON.stringify({ n: M.itemsOf(f).length, order: M.actorOrder(f), path: M.flowActorPath(f), edges: M.stepEdges(f).length,
          chain: M.stepEdgesOrChain({steps: [{id:'a'},{id:'b'},{id:'c'}]}), unknown: M.stepEdges({steps: [{id:'a', next:['zzz','a']}]}) }));""", flow)
        self.assertEqual(9, out["n"])
        self.assertEqual(flow["actors"], out["order"])
        self.assertEqual("frontend/app/components", out["path"][0])
        self.assertNotIn("backend/eo,backend/eo", ",".join(out["path"]))               # consecutive repeats dropped
        self.assertEqual(9, out["edges"])                                              # eight chain links plus the loop back to s04, minus none
        self.assertEqual([{"from": "a", "to": "b"}, {"from": "b", "to": "c"}], out["chain"])
        self.assertEqual([], out["unknown"])

    def test_lifecycle_items_are_transitions(self):
        out = run_node("console.log(JSON.stringify(M.itemsOf(data).map((i) => i.kind)));", FX.lifecycle())
        self.assertEqual({"transition"}, set(out))
        self.assertEqual(7, len(out))

    def test_evidence_targets_ready_for_code_links(self):
        out = run_node("console.log(JSON.stringify(M.evidenceTargets(data, 'abc')));", {"evidence": [{"path": "a/b.py", "qual": "f", "lines": [3, 9], "status": "stale"}, {"path": "c.py"}, {"nope": 1}]})
        self.assertEqual({"path": "a/b.py", "qual": "f", "start": 3, "end": 9, "status": "stale", "commit": "abc"}, out[0])
        self.assertNotIn("start", out[1])
        self.assertEqual(2, len(out))

    def test_wrap_text_never_exceeds_its_limits(self):
        samples = ["", "short", "a b c d e f g h i j k l m n o p q r s t u v w x y z " * 4, "x" * 200, "word " * 40, "path/to/a/very/long/file/name/that/never/breaks/anywhere.py is cited"]
        out = run_node("console.log(JSON.stringify(data.map((t) => M.wrapText(t, 20, 3))));", samples)
        for s, lines in zip(samples, out):
            self.assertLessEqual(len(lines), 3, s[:30])
            self.assertTrue(all(len(l) <= 20 for l in lines), (s[:30], lines))
        self.assertTrue(out[2][-1].endswith("…"))
        self.assertEqual([""], out[0])

    def test_stages_found_in_the_code_come_from_the_registry_extractors(self):
        out = run_node("""const [reg, der] = data; console.log(JSON.stringify([M.derivedStages(reg, der, 'task-pipeline'), M.derivedStages(reg, der, 'memory'), M.derivedStages(reg, der, 'nope')]));""",
                       [load("content/arch-flows.json"), load("data/arch/derived.json")])
        reg = load("content/arch-flows.json")
        wanted = [e["id"] for f in reg["flows"] if f["id"] == "task-pipeline" for e in f.get("extractors", [])]
        self.assertEqual(sorted(wanted), sorted(s["id"] for s in out[0]))
        self.assertEqual([], out[2])

    def test_protocol_messages_come_from_the_contract(self):
        der = load("data/arch/derived.json")
        model = load("data/arch/model.json")
        out = run_node("const [d, n] = data; console.log(JSON.stringify(M.protocolMessages(d, n)));", [der, model["nodes"]])
        self.assertEqual(len(der["catalogues"]["protocol"]["messages"]), len(out["messages"]))
        self.assertEqual("m2c/src/m2c/link", out["client"])
        for m, src in zip(out["messages"], der["catalogues"]["protocol"]["messages"]):
            self.assertEqual(src["type"], m["title"])
            self.assertEqual(m["actor"] == out["client"], src["direction"] != "server_to_client")

    def test_mermaid_export_for_every_kind(self):
        seq = run_node("const f = data; const p = S.prepareFlow(f, (id) => id); console.log(JSON.stringify(M.toMermaid({type:'sequence', actors: p.actors, messages: p.messages})));", FX.pipeline())
        self.assertTrue(seq.startswith("sequenceDiagram\n"))
        self.assertEqual(9, seq.count("->>"))
        self.assertIn("Note over", seq)                                                # the gate
        life = run_node("""const f = data; const p = C.prepare(f, (id) => id);
          console.log(JSON.stringify(M.toMermaid({type:'lifecycle', states: p.states, transitions: p.transitions.map((t) => ({from: t.from, to: t.to, label: t.trigger}))})));""", FX.lifecycle())
        self.assertTrue(life.startswith("stateDiagram-v2\n"))
        self.assertIn("[*] --> s0", life)
        self.assertEqual(3, life.count("--> [*]"))                                     # three end states
        flow = run_node("""console.log(JSON.stringify(M.toMermaid({type:'layered', nodes:[{id:'a', label:'He said "hi" <b>', lane:'X'},{id:'b', label:'B', lane:'Y'}], edges:[{from:'a', to:'b', label:'imports'},{from:'a', to:'zz'}]})));""")
        self.assertTrue(flow.startswith("flowchart LR\n"))
        self.assertNotIn('"hi"', flow); self.assertNotIn("<b>", flow)
        self.assertEqual(1, flow.count("-->"))                                         # an edge to an unknown node is dropped
        self.assertEqual(2, flow.count("subgraph"))

    def test_loader_remembers_and_survives_a_missing_file(self):
        out = run_node("""let n = 0; const L1 = M.makeLoader(async (rel) => { n++; if (rel.includes('derived')) throw new Error('404'); return {rel}; });
          const a = await L1.model(); const b = await L1.model(); const d = await L1.derived(); let threw = false; try { await (M.makeLoader(async () => { throw new Error('x'); })).view('v'); } catch { threw = true; }
          console.log(JSON.stringify({same: a === b, n, d, threw}));""")
        self.assertEqual({"same": True, "n": 2, "d": None, "threw": True}, out)


@unittest.skipUnless(NODE, "node is not installed")
class Layout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load("data/arch/model.json")
        cls.nodes = [n for n in cls.model["nodes"] if n["kind"] != "group"]

    def test_every_node_gets_a_place_and_boxes_do_not_overlap(self):
        out = run_node("""const [nodes, layout] = data; const R = L.structureLayout(nodes, layout);
          console.log(JSON.stringify({pos: [...R.pos], box: [...R.box], auto: [...R.auto], size: R.size}));""", [self.nodes, self.model["layout"]])
        pos, box = dict(out["pos"]), dict(out["box"])
        self.assertEqual({n["id"] for n in self.nodes}, set(pos))
        rects = [{"id": i, **pos[i], **box[i]} for i in pos if "/" not in i or not i.startswith("m2c/src/m2c") or True]
        parents = {n["id"] for n in self.nodes if n.get("children")}
        bad = [p for p in rects_overlap([r for r in rects if r["id"] not in parents]) ]
        self.assertEqual([], bad, "boxes overlap")
        for i, p in pos.items():
            self.assertTrue(all(isinstance(v, (int, float)) for v in p.values()))
        pinned = self.model["layout"]["pins"]
        for i in out["auto"]:
            self.assertNotIn(i, pinned)

    def test_an_unpinned_node_is_placed_inside_its_group(self):
        groups = {g["id"]: g for g in self.model["layout"]["groups"]}
        out = run_node("""const [nodes, layout] = data; const R = L.structureLayout(nodes, layout); console.log(JSON.stringify({pos: [...R.pos], box: [...R.box], auto: [...R.auto]}));""", [self.nodes, self.model["layout"]])
        pos, box = dict(out["pos"]), dict(out["box"])
        self.assertTrue(out["auto"], "the model has unplaced nodes (stores, outside services): auto placement is what draws them")
        by = {n["id"]: n for n in self.nodes}
        for i in out["auto"]:
            g = groups.get(by[i].get("group"))
            if g:
                self.assertTrue(g["x"] <= pos[i]["x"] - box[i]["w"] / 2 and pos[i]["x"] + box[i]["w"] / 2 <= g["x"] + g["w"], i)
                self.assertTrue(g["y"] <= pos[i]["y"] - box[i]["h"] / 2 and pos[i]["y"] + box[i]["h"] / 2 <= g["y"] + g["h"], i)

    def test_auto_placement_is_deterministic_and_survives_no_pins_at_all(self):
        a = run_node("const [n, l] = data; console.log(JSON.stringify([...L.structureLayout(n, l).pos]));", [self.nodes, self.model["layout"]])
        b = run_node("const [n, l] = data; console.log(JSON.stringify([...L.structureLayout(n, l).pos]));", [self.nodes, self.model["layout"]])
        self.assertEqual(a, b)
        bare = dict(self.model["layout"], pins={})
        out = run_node("const [n, l] = data; const R = L.structureLayout(n, l); console.log(JSON.stringify({n: R.pos.size, auto: R.auto.size, size: R.size, box: [...R.box]}));", [self.nodes, bare])
        self.assertEqual(len(self.nodes), out["n"])                                    # a fresh census with no layout still draws every node
        self.assertEqual(len(self.nodes), out["auto"])

    def test_zoom_levels(self):
        edges, groups = self.model["edges"], self.model["layout"]["groups"]
        out = run_node("""const [nodes, groups, edges] = data; const r = (lv) => { const g = L.levelGraph(nodes, groups, edges, lv, (e) => e.kind !== 'graph'); return {n: g.nodes.length, e: g.edges.length, ids: g.nodes.map((x) => x.id), opened: g.frameOf, self: g.edges.filter((x) => x.a === x.b).length, groupBoxes: g.groupBoxes}; };
          console.log(JSON.stringify([r(0), r(1), r(2)]));""", [self.nodes, groups, edges])
        l0, l1, l2 = out
        used = {n["group"] for n in self.nodes if n.get("group")}
        self.assertEqual(len(used), l0["n"]); self.assertTrue(l0["groupBoxes"])
        self.assertEqual(len([n for n in self.nodes if not n.get("parent")]), l1["n"])
        self.assertTrue(all(not i.startswith("m2c/src/m2c/") for i in l1["ids"]))
        self.assertEqual(["m2c/src/m2c"], l2["opened"])
        self.assertGreater(l2["n"], l1["n"])
        for r in out:
            self.assertEqual(0, r["self"])
        self.assertLessEqual(l0["e"], l1["e"])

    def test_rollup_merges_parallel_edges_and_keeps_direction(self):
        out = run_node("""const e = [{from:'a',to:'b',kind:'import',weight:3},{from:'b',to:'a',kind:'api-call',weight:2},{from:'a',to:'b',kind:'graph',weight:9},{from:'a',to:'a',kind:'import',weight:1},{from:'a',to:'c',kind:'declared',weight:0,gate:true,label:'ok'}];
          console.log(JSON.stringify([L.rollupEdges(e, (x) => x), L.rollupEdges(e, (x) => x, (x) => x.kind !== 'graph')]));""")
        both, nograph = out
        ab = next(x for x in both if x["id"] == "a|b")
        self.assertEqual(14, ab["weight"]); self.assertTrue(ab["arrowAB"] and ab["arrowBA"]); self.assertTrue(ab["flow"])
        ac = next(x for x in both if x["id"] == "a|c")
        self.assertTrue(ac["gate"]); self.assertEqual(["ok"], ac["labels"])
        self.assertEqual(5, next(x for x in nograph if x["id"] == "a|b")["weight"])
        self.assertEqual(2, len(both))                                                 # the self loop is dropped

    def test_edge_width_is_monotonic_and_bounded(self):
        out = run_node("console.log(JSON.stringify([0, 1, 5, 50, 500].map((w) => L.edgeWidth(w, 500))));")
        self.assertEqual(sorted(out[1:]), out[1:])
        self.assertEqual(1.5, out[0]); self.assertLessEqual(max(out), 6)

    def test_layered_layout_of_a_flow(self):
        flow = FX.pipeline()
        out = run_node("""const f = data; const steps = f.steps; const items = steps.map((s) => ({id: s.id, lane: s.actor, ...L.stepBox(s)})); const edges = M.stepEdgesOrChain(f);
          const R = L.layeredLayout(items, edges, {axis: 'down', laneOrder: M.actorOrder(f)}); const R2 = L.layeredLayout(items, edges, {axis: 'down', laneOrder: M.actorOrder(f)});
          console.log(JSON.stringify({pos: [...R.pos], layer: [...R.layer], back: [...R.back], size: R.size, lanes: R.lanes.map((l) => l.id), same: JSON.stringify([...R.pos]) === JSON.stringify([...R2.pos]), edges}));""", flow)
        pos = {k: {"id": k, **v} for k, v in out["pos"]}
        self.assertEqual([], rects_overlap(list(pos.values())))
        self.assertTrue(out["same"])
        self.assertEqual(flow["actors"], out["lanes"])
        layer = dict(out["layer"])
        for i, e in enumerate(out["edges"]):
            if i in out["back"]:
                continue
            self.assertGreater(layer[e["to"]], layer[e["from"]], f"{e}: a step comes after the one it follows")
        self.assertEqual(1, len(out["back"]))                                          # the retry loop s05 -> s04, and only that
        self.assertEqual("s04", out["edges"][out["back"][0]]["to"])
        for p in pos.values():
            self.assertTrue(0 < p["x"] < out["size"][0] and 0 < p["y"] < out["size"][1])

    def test_layered_layout_handles_cycles_empty_input_and_unknown_ids(self):
        out = run_node("""const it = (id, lane) => ({id, lane, w: 100, h: 40});
          const a = L.layeredLayout([it('a','x'), it('b','x'), it('c','y')], [{from:'a',to:'b'},{from:'b',to:'c'},{from:'c',to:'a'},{from:'a',to:'zz'},{from:'a',to:'a'}]);
          const e = L.layeredLayout([], []); const r = L.layeredLayout([it('a','x'), it('b','y')], [{from:'a',to:'b'}], {axis:'right'});
          console.log(JSON.stringify({back: [...a.back], n: a.pos.size, e: e.size, rx: [r.pos.get('a').x, r.pos.get('b').x]}));""")
        self.assertEqual([2], out["back"]); self.assertEqual(3, out["n"]); self.assertEqual(2, len(out["e"]))
        self.assertLess(out["rx"][0], out["rx"][1])                                    # axis "right": layers go left to right

    def test_route_edge_stays_finite(self):
        out = run_node("""const a = {x: 100, y: 50, w: 100, h: 40}, b = {x: 300, y: 200, w: 100, h: 40}, c = {x: 300, y: 55, w: 100, h: 40};
          console.log(JSON.stringify([L.routeEdge(a, b, {}), L.routeEdge(b, a, {back: true}), L.routeEdge(a, c, {}), L.routeEdge(a, b, {axis: 'right'}), L.routeEdge(b, a, {axis: 'right', back: true})]));""")
        for r in out:
            self.assertTrue(r["d"].startswith("M"), r)
            self.assertNotIn("NaN", r["d"])
            self.assertTrue(all(isinstance(v, (int, float)) for v in r["mid"].values()))

    def test_lifecycle_main_chain_on_row_zero_and_end_states_below(self):
        flow = FX.lifecycle()
        out = run_node("const p = C.prepare(data, (x) => x); console.log(JSON.stringify([...L.lifecycleLanes(p.states, p.transitions)]));", flow)
        lanes = dict(out)
        self.assertEqual(0, lanes["queued"]); self.assertEqual(0, lanes["running"]); self.assertEqual(0, lanes["awaiting"])
        for s in flow["states"]:
            if s.get("terminal"):
                self.assertEqual(1, lanes[s["id"]], s["id"])

    def test_sequence_layout_and_preparation(self):
        flow = FX.pipeline("sequence")
        out = run_node("""const p = S.prepareFlow(data, (id) => id); const R = L.sequenceLayout(p.actors, p.messages);
          console.log(JSON.stringify({actors: p.actors.map((a) => a.id), msgs: p.messages.length, ys: R.rows.map((r) => r.y), selfs: R.rows.filter((r) => r.self).length, size: R.size, first: p.messages[0], second: p.messages[1]}));""", flow)
        self.assertEqual(9, out["msgs"]); self.assertEqual(9, len(out["ys"]))
        self.assertEqual(sorted(out["ys"]), out["ys"]); self.assertEqual(len(set(out["ys"])), len(out["ys"]))
        self.assertEqual(out["actors"][0], out["first"]["from"])                      # the first message is a loop on its own actor
        self.assertEqual(out["first"]["to"], out["second"]["from"])                   # step n starts where step n-1 happened
        self.assertEqual(flow["steps"][0]["actor"], out["actors"][0])
        two = run_node("const R = L.sequenceLayout([{id:'a',label:'A'},{id:'b',label:'B'}], []); console.log(JSON.stringify(R.size));")
        self.assertGreaterEqual(two[0], 760)                                           # few lifelines are not scaled up to a poster

    def test_protocol_sequence_has_two_lifelines(self):
        der, model = load("data/arch/derived.json"), load("data/arch/model.json")
        out = run_node("const [d, n] = data; const p = S.prepareProtocol(d, n, (x) => x); console.log(JSON.stringify({actors: p.actors, n: p.messages.length, derived: p.derived, st: [...new Set(p.messages.map((m) => m.status))]}));", [der, model["nodes"]])
        self.assertEqual(2, len(out["actors"])); self.assertTrue(out["derived"]); self.assertEqual(["derived"], out["st"])
        self.assertEqual(len(der["catalogues"]["protocol"]["messages"]), out["n"])

    def test_catalog_layout_and_filter(self):
        der = load("data/arch/derived.json")
        routes = der["catalogues"]["routes"]
        out = run_node("""const r = data; const all = K.groupsOf(r, ''); const L1 = L.catalogLayout(all.map((g) => ({id: g.id, rows: g.rows.length})), 1240);
          const f = K.groupsOf(r, 'POST'); console.log(JSON.stringify({total: K.totalRoutes(r), rows: all.reduce((n, g) => n + g.rows.length, 0), cards: L1.cards, size: L1.size, filtered: f.reduce((n, g) => n + g.rows.length, 0), none: K.groupsOf(r, 'zzzzqq').length, clip: K.clip('x'.repeat(60), 10)}));""", routes)
        self.assertEqual(out["total"], out["rows"])
        self.assertGreater(out["total"], 100)
        self.assertEqual([], rects_overlap([{"id": c["id"], "x": c["x"] + c["w"] / 2, "y": c["y"] + c["h"] / 2, "w": c["w"], "h": c["h"]} for c in out["cards"]]))
        self.assertTrue(0 < out["filtered"] < out["total"]); self.assertEqual(0, out["none"]); self.assertEqual(10, len(out["clip"]))

    def test_the_box_sizes_are_the_ones_of_the_topology_and_check_site(self):
        out = run_node("console.log(JSON.stringify({box: L.BOX, kid: L.KID}));")
        self.assertEqual(check_site.TOPOLOGY_BOX, out["box"])
        self.assertEqual(72, out["kid"]["w"])                                          # content/topology.json pins its parts 77 apart


@unittest.skipUnless(NODE, "node is not installed")
class SvgView(unittest.TestCase):
    def test_pure_helpers(self):
        out = run_node("""console.log(JSON.stringify({z: [V.clampZoom(0.2), V.clampZoom(9), V.clampZoom('x'), V.clampZoom(1.234)], clip: V.clipToRect({x:0,y:0,w:100,h:50}, 200, 0), same: V.clipToRect({x:3,y:4,w:10,h:10}, 3, 4),
          near: V.nearestInDirection([{id:'a',x:0,y:0},{id:'b',x:100,y:5},{id:'c',x:50,y:200}], 'a', 'right'), none: V.nearestInDirection([{id:'a',x:0,y:0}], 'a', 'up'), bad: V.nearestInDirection([], 'a', 'up'),
          path: V.edgePath({x:0,y:0,w:20,h:20},{x:100,y:0,w:20,h:20}), bent: V.edgePath({x:0,y:0,w:20,h:20},{x:100,y:0,w:20,h:20}, 30), kids: V.liveKids([1, null, [2, false, [3]], undefined, 0])}));""")
        self.assertEqual([1, 4, 1, 1.23], out["z"])
        self.assertEqual({"x": 50, "y": 0}, out["clip"]); self.assertEqual({"x": 3, "y": 4}, out["same"])
        self.assertEqual("b", out["near"]); self.assertIsNone(out["none"]); self.assertIsNone(out["bad"])
        self.assertEqual("M10 0L90 0", out["path"]["d"]); self.assertTrue(out["bent"]["d"].startswith("M") and "Q" in out["bent"]["d"])
        self.assertEqual([1, 2, 3, 0], out["kids"])

    def test_h_flattens_nested_children_so_no_array_is_written_as_text(self):
        """A bug of the first P26 cut: [", ", code] pairs inside a list of children were written as '[object HTMLElement]'."""
        src = text(JS / "svgview.js")
        self.assertIn("kids.flat(Infinity)", src)
        self.assertNotIn("kids.flat()", src)

    def test_export_pins_changes_only_x_and_y_of_moved_nodes(self):
        layout = load("content/arch-layout.json")
        out = run_node("""const [l, moved] = data; console.log(JSON.stringify(V.exportPins(l, moved)));""", [layout, {"backend/eo": {"x": 501.6, "y": 300}, "new/node": {"x": 1, "y": 2}, "bad": {"x": "a", "y": 1}}])
        new = json.loads(out)
        self.assertEqual({"x": 502, "y": 300}, new["pins"]["backend/eo"])
        self.assertEqual({"x": 1, "y": 2}, new["pins"]["new/node"]); self.assertNotIn("bad", new["pins"])
        self.assertEqual(sorted(new["pins"]), list(new["pins"]))
        for k in layout:
            if k != "pins":
                self.assertEqual(layout[k], new[k], k)
        for k, v in layout.get("pins", {}).items():
            if k != "backend/eo":
                self.assertEqual(v, new["pins"][k], k)


class Fixtures(unittest.TestCase):
    def test_fixture_flows_pass_the_real_validator(self):
        import arch
        reg = arch.load_registry(ROOT)
        self.assertTrue(reg["flows"])
        for f in (FX.pipeline(), FX.lifecycle()):
            self.assertTrue(f["title"] and f["commit"])
        self.assertEqual({"fresh", "stale", "broken", "unverified"}, {s["status"] for s in FX.pipeline()["steps"]})
        self.assertEqual(3, sum(1 for s in FX.lifecycle()["states"] if s.get("terminal")))

    def test_with_flows_writes_only_into_the_copy(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            site = FX.copy_site(ROOT, tmp / "site")
            before = text(ROOT / "data/arch/views/task-pipeline.json")
            out = FX.with_flows(site)
            self.assertEqual(set(FX.FLOWS), set(out))
            self.assertEqual(before, text(ROOT / "data/arch/views/task-pipeline.json"))
            shard = json.loads(text(site / "data/arch/views/task-pipeline.json"))
            self.assertEqual("broken", shard["status"]); self.assertEqual(9, len(shard["flow_data"]["steps"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Files(unittest.TestCase):
    """Rules for the DOM files that are not run here."""
    FILES = [JS / "svgview.js"] + sorted(ARCH_JS.glob("*.js"))

    def test_no_innerhtml_eval_storage_or_network(self):
        for p in self.FILES:
            code = re.sub(r"/\*.*?\*/", "", text(p), flags=re.S)
            code = re.sub(r"(^|\s)//.*$", "", code, flags=re.M)
            for bad in (r"\.innerHTML", r"\.outerHTML", r"insertAdjacentHTML", r"\beval\(", r"new Function", r"localStorage", r"sessionStorage", r"document\.write", r"XMLHttpRequest"):
                self.assertIsNone(re.search(bad, code), f"{p.name}: {bad}")
            for url in re.findall(r"https?://[^\s\"'`)]+", code):
                self.assertTrue(url.startswith(("http://www.w3.org/2000/svg", "https://github.com/Unavailable4u/MiniMe")), f"{p.name}: {url}")

    def test_the_css_uses_only_tokens_for_colour(self):
        css = text(ROOT / "assets/css/arch.css")
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", css), "a hard-coded colour in arch.css")
        self.assertIsNone(re.search(r"\b(rgb|rgba|hsl)\(", css))
        for token in set(re.findall(r"var\((--[a-z0-9-]+)", css)):
            if token in ("--z-modal", "--shadow-3"):
                continue
            self.assertIn(f"{token}:", text(ROOT / "assets/css/tokens.css"), f"{token} is not a token")

    def test_every_diagram_has_a_text_alternative_and_keyboard_access(self):
        code = text(ARCH_JS / "render.js")
        for needle in ('role: "group"', '"aria-label"', 'tabindex", "0"', '"aria-pressed"', "prefers-reduced-motion" if False else "reduced()", "listFor", "ArrowLeft"):
            self.assertIn(needle, code, needle)
        self.assertIn("prefers-reduced-motion", text(ROOT / "assets/css/arch.css"))

    def test_the_host_page_is_in_the_nav_and_loads_the_module(self):
        html = text(ROOT / "arch-view.html")
        self.assertIn("data-arch-page", html); self.assertIn('assets/js/arch/render.js', html); self.assertIn("assets/css/arch.css", html)
        urls = [i["url"] for w in load("content/nav.json")["wings"] for i in w["items"]]
        self.assertIn("arch-view.html", urls)

    def test_committed_arch_figures_name_registered_views(self):
        reg = load("content/arch-flows.json")
        views = {v["id"] for v in reg["views"]}
        flows = {f["id"] for f in reg["flows"]}
        n = 0
        for p in (ROOT / "content/figures").glob("*.json"):
            for f in load(f"content/figures/{p.name}")["figures"]:
                if f["type"] == "arch":
                    n += 1
                    self.assertIn(f["view"], views); self.assertTrue(f.get("flow") is None or f["flow"] in flows)
                    self.assertNotIn("src", f); self.assertNotIn("size", f)
        self.assertGreaterEqual(n, 2)

    def test_topology_and_arch_share_the_zoom_code(self):
        topo = text(JS / "topology.js")
        self.assertIn('from "./svgview.js"', topo)
        self.assertIn("createZoom", topo); self.assertIn("createZoom", text(ARCH_JS / "render.js"))
        self.assertNotIn("function clipToRect", topo)


if __name__ == "__main__":
    unittest.main(verbosity=1)
