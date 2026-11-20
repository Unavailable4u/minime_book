#!/usr/bin/env python3
"""Tests for the Coverage & freshness page (patch P22). Run: python scripts/test_status.py

Covers: scripts/build_status.py (the pure pieces, and that the committed data/index/status.json is current), the pure logic in
assets/js/coverage-core.js (run with Node), content/copilot-prompts.json against the prompts printed in UPDATING.md, the page
and nav wiring, and the jsdom page test (scripts/explorer_tests/coverage.mjs).
The Node tests are skipped, not failed, when `node` is not on PATH; the jsdom test is skipped when jsdom is not installed
(npm install --prefix scripts/explorer_tests jsdom). Standard library only.
"""
from __future__ import annotations

import importlib.util
import json
import os
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


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bs = load_script("build_status")


class Pieces(unittest.TestCase):
    def test_sources_block_takes_the_latest_dates(self):
        notes = {"commit": "c" * 40, "files": {"a": {"written": "2026-11-01"}, "b": {"written": "2026-11-09"}, "c": {}}}
        book = {"chapters": [{"built": "2026-10-07"}, {"built": "2026-10-20"}, {}]}
        arch = {"commit": "d" * 40, "flows": {"x": {"commit": "e" * 40}, "y": {"commit": None}}}
        got = bs.sources_block({"commit": "abc1234", "generated": "2026-11-19"}, {"graph": {"commit": "abc1234", "date": "2026-11-17"}}, notes, arch, book)
        self.assertEqual(got["census"], {"commit": "abc1234", "date": "2026-11-19"})
        self.assertEqual(got["graph"], {"commit": "abc1234", "date": "2026-11-17"})
        self.assertEqual(got["notes"]["date"], "2026-11-09")
        self.assertEqual(got["arch"]["flow_commits"], ["e" * 40])
        self.assertEqual(got["docs"]["date"], "2026-10-20")

    def test_sources_block_survives_empty_inputs(self):
        got = bs.sources_block({}, {}, {}, {}, {})
        self.assertEqual(got["census"], {"commit": "", "date": ""})
        self.assertEqual(got["notes"]["date"], "")
        self.assertEqual(got["docs"]["date"], "")

    def test_folder_table_counts_every_ancestor_and_merges_notes(self):
        files = [{"path": "backend/agents/a.py", "functions": [1, 2], "classes": [1]}, {"path": "backend/api/b.py", "functions": [1]}, {"path": "README.md"}]
        got = bs.folder_table(files, {"backend": {"files": 3, "noted": 1, "fresh": 1, "stale": 0}, "gone": {"files": 9}})
        self.assertEqual(sorted(got), ["backend", "backend/agents", "backend/api"])        # the repo root is not a row; unknown folders are ignored
        self.assertEqual((got["backend"]["files"], got["backend"]["symbols"]), (2, 4))
        self.assertEqual((got["backend"]["elig"], got["backend"]["noted"]), (3, 1))
        self.assertEqual(got["backend/agents"]["elig"], 0)

    def test_stale_list_keeps_stale_and_bad_and_sorts_by_tier(self):
        notes = {"files": {
            "z.py": {"status": "stale", "tier": 1, "bad": ["f"]}, "a.py": {"status": "fresh", "tier": 2, "bad": []},
            "m.py": {"status": "fresh", "tier": 2, "bad": ["g"]}, "b.py": {"status": "stale", "tier": 1}}}
        self.assertEqual([r["path"] for r in bs.stale_list(notes)], ["b.py", "z.py", "m.py"])

    def test_stale_list_is_capped(self):
        notes = {"files": {f"f{i:04d}.py": {"status": "stale", "tier": 3} for i in range(bs.STALE_LIMIT + 50)}}
        self.assertEqual(len(bs.stale_list(notes)), bs.STALE_LIMIT)

    def test_file_degrees_sums_the_weights_by_position(self):
        doc = {"paths": ["a", "b", "c"], "links": [[[1, 2], [2, 3]], [[0, 2]], []]}
        self.assertEqual(bs.file_degrees(doc), {"a": 5, "b": 2, "c": 0})     # a file with no links is kept, at 0
        self.assertEqual(bs.file_degrees(None), {})

    def test_flow_order_reads_a_list_or_a_dict(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "content").mkdir()
            reg = Path(d) / "content" / "arch-flows.json"
            reg.write_text(json.dumps({"flows": [{"id": "b"}, {"id": "a"}]}), encoding="utf-8")
            self.assertEqual(bs.flow_order(Path(d)), ["b", "a"])
            reg.write_text(json.dumps({"flows": {"y": {}, "x": {}}}), encoding="utf-8")
            self.assertEqual(bs.flow_order(Path(d)), ["y", "x"])
            reg.unlink()
            self.assertEqual(bs.flow_order(Path(d)), [])

    def test_flows_block_defaults_missing(self):
        got = bs.flows_block({"flows": {"f": {"title": "F"}}})
        self.assertEqual(got["f"]["status"], "missing")
        self.assertEqual(got["f"]["items"], 0)

    def test_dumps_is_stable_lf_text(self):
        text = bs.dumps({"b": 1, "a": {"d": 2, "c": 3}})
        self.assertTrue(text.endswith("\n"))
        self.assertNotIn("\r", text)
        self.assertLess(text.index('"a"'), text.index('"b"'))


class Committed(unittest.TestCase):
    def test_status_json_is_current(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_status.py"), "--check"], capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_status_json_shape(self):
        s = json.loads((ROOT / "data" / "index" / "status.json").read_text(encoding="utf-8"))
        for key in ("schema", "sources", "totals", "notes", "folders", "flows", "flow_order", "flow_totals", "stale", "next"):
            self.assertIn(key, s)
        self.assertLessEqual(len(s["next"]["files"]), bs.NEXT_LIMIT)
        for f in s["next"]["files"]:
            self.assertIn(f["tier"], (1, 2, 3))
            self.assertIn(f["reason"], ("new", "changed"))
        self.assertEqual(set(s["flow_order"]), set(s["flows"]))
        self.assertLess((ROOT / "data" / "index" / "status.json").stat().st_size, 200_000, "status.json is read on every page: keep it small")
        # the census totals match what the Explorer's tree says
        census = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        self.assertEqual(s["totals"]["files"], len(census["files"]))

    def test_next_preview_agrees_with_the_notes_index_when_the_graph_is_unchanged(self):
        s = json.loads((ROOT / "data" / "index" / "status.json").read_text(encoding="utf-8"))
        notes = json.loads((ROOT / "data" / "index" / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(s["next"]["needing"], notes["totals"]["missing"] + notes["totals"]["stale"])


class Prompts(unittest.TestCase):
    def test_prompts_equal_the_ones_in_updating_md(self):
        prompts = json.loads((ROOT / "content" / "copilot-prompts.json").read_text(encoding="utf-8"))
        text = (ROOT / "UPDATING.md").read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(sorted(prompts), ["A", "B", "C", "D"])
        for key, body in prompts.items():
            m = re.search(r"\*\*Prompt " + key + r"[^\n]*\*\*\n\n```\n(.*?)\n```", text, re.S)
            self.assertIsNotNone(m, f"UPDATING.md has no prompt {key}")
            self.assertEqual(body, m.group(1), f"content/copilot-prompts.json prompt {key} differs from UPDATING.md")


class Wiring(unittest.TestCase):
    def test_page_is_a_project_page_with_its_own_css_last(self):
        s = (ROOT / "coverage.html").read_text(encoding="utf-8")
        self.assertIn('<body data-page="coverage" data-wing="project">', s)
        self.assertLess(s.index("assets/css/shell.css"), s.index("assets/css/coverage.css"))
        self.assertIn('id="cv-app"', s)
        self.assertIn("assets/js/coverage.js", s)
        self.assertIn("assets/js/shell.js", s)

    def test_nav_lists_it_once_in_the_project_wing(self):
        nav = json.loads((ROOT / "content" / "nav.json").read_text(encoding="utf-8"))
        project = next(w for w in nav["wings"] if w["id"] == "project")
        hits = [i for w in nav["wings"] for i in w["items"] if i["id"] == "coverage"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["url"], "coverage.html")
        self.assertIn(hits[0], project["items"])

    def test_config_has_thresholds_and_they_are_positive(self):
        cfg = json.loads((ROOT / "content" / "config.json").read_text(encoding="utf-8"))
        warn = cfg["freshness"]["warnDays"]
        self.assertEqual(sorted(warn), ["census", "docs", "graph", "notes"])
        self.assertTrue(all(isinstance(v, int) and v > 0 for v in warn.values()))

    def test_css_has_no_raw_colours(self):
        css = re.sub(r"/\*.*?\*/", "", (ROOT / "assets" / "css" / "coverage.css").read_text(encoding="utf-8"), flags=re.S)
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b")
        self.assertNotRegex(css, r"\b(?:rgb|hsl)a?\(")

    def test_every_class_the_page_draws_is_styled(self):
        js = (ROOT / "assets" / "js" / "coverage.js").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "css" / "coverage.css").read_text(encoding="utf-8")
        used = set(re.findall(r"\bcv-[a-z][a-z0-9_-]*", js))
        used -= {"cv-app", "cv-heat--", "cv-tile--", "cv-heat", "cv-tile"}      # the id, and the prefixes of computed names
        for cls in sorted(used):
            self.assertIn(cls, css, f"coverage.js uses .{cls} but coverage.css does not style it")


@unittest.skipUnless(NODE, "node is not installed")
class CorePure(unittest.TestCase):
    def run_node(self, body: str):
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(ROOT / "assets" / "js" / "coverage-core.js", tmp / "core.mjs")
            (tmp / "run.mjs").write_text('import * as C from "./core.mjs";\nconst out = (v) => console.log(JSON.stringify(v));\n' + body, encoding="utf-8")
            r = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return json.loads(r.stdout.strip().splitlines()[-1])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_age_and_pct(self):
        got = self.run_node('const now = Date.UTC(2026, 10, 21, 12);\nout([C.ageDays("2026-11-21", now), C.ageDays("2026-11-19", now), C.ageDays("2027-01-01", now), C.ageDays("", now), C.ageDays(null, now), C.ageDays("nope", now), C.pct(1, 3), C.pct(1, 0), C.pct(NaN, 4)]);')
        self.assertEqual(got, [0, 2, 0, None, None, None, 33, None, None])

    def test_warn_days_falls_back_per_source(self):
        got = self.run_node('out([C.warnDays({}), C.warnDays({ freshness: { warnDays: 7 } }), C.warnDays({ freshness: { warnDays: { census: 3, graph: -1, notes: "x" } } })]);')
        self.assertEqual(got[0], {"census": 14, "graph": 14, "notes": 30, "docs": 60})
        self.assertEqual(got[1], {"census": 7, "graph": 7, "notes": 7, "docs": 7})
        self.assertEqual(got[2], {"census": 3, "graph": 14, "notes": 30, "docs": 60})

    def test_same_commit_compares_prefixes(self):
        got = self.run_node('out([C.sameCommit("3727ae3", "3727ae323c26"), C.sameCommit("3727ae3", "50e25b5"), C.sameCommit("", "abc"), C.sameCommit("ABC1234", "abc1234ffff")]);')
        self.assertEqual(got, [True, False, False, True])

    def test_chip_is_ok_amber_or_unknown(self):
        body = '''
const now = Date.UTC(2026, 10, 21);
const st = (o = {}) => ({ sources: { census: { commit: "3727ae3", date: o.census || "2026-11-19" }, graph: { commit: o.graph || "3727ae3", date: "2026-11-17" },
  notes: { commit: o.notes || "3727ae323c26", date: "2026-11-18" }, docs: { date: "2026-11-14" } }, notes: { totals: { files: 596, noted: 108 } } });
const a = C.chipModel(st(), {}, now), b = C.chipModel(st({ census: "2026-10-01" }), {}, now), c = C.chipModel(st({ graph: "50e25b5" }), {}, now),
  d = C.chipModel(st({ notes: "deadbee" }), {}, now), e = C.chipModel({}, {}, now), f = C.chipModel(null, {}, now);
out([a.state, a.text, b.state, b.reasons.length, c.state, c.reasons[0], d.state, e.state, f.state]);
'''
        got = self.run_node(body)
        self.assertEqual(got[0], "ok")
        self.assertEqual(got[1], "census 2 days · graph 4 days · notes 18%")
        self.assertEqual(got[2], "stale")
        self.assertEqual(got[3], 1)
        self.assertEqual(got[4], "stale")
        self.assertIn("50e25b5", got[5])
        self.assertEqual(got[6], "stale")
        self.assertEqual(got[7:], ["unknown", "unknown"])

    def test_folder_rows_show_only_open_branches_in_tree_order(self):
        body = '''
const f = { "a": { files: 2, symbols: 5, elig: 2, noted: 1 }, "a/b": { files: 1 }, "a/b/c": { files: 1 }, "a/d": { files: 1 }, "z": { files: 1 } };
out([C.folderRows(f).map((r) => r.path), C.folderRows(f, new Set(["a"])).map((r) => r.path), C.folderRows(f, new Set(["a", "a/b"])).map((r) => [r.path, r.depth, r.hasKids]), C.folderRows(f)[0].notesRatio, C.folderRows(f)[1].notesRatio]);
'''
        got = self.run_node(body)
        self.assertEqual(got[0], ["a", "z"])
        self.assertEqual(got[1], ["a", "a/b", "a/d", "z"])
        self.assertEqual(got[2], [["a", 0, True], ["a/b", 1, True], ["a/b/c", 2, False], ["a/d", 1, False], ["z", 0, False]])
        self.assertEqual((got[3], got[4]), (0.5, None))

    def test_heat_level_never_hides_a_little_or_a_lot(self):
        got = self.run_node("out([C.heatLevel(null), C.heatLevel(NaN), C.heatLevel(0), C.heatLevel(0.01), C.heatLevel(0.5), C.heatLevel(0.99), C.heatLevel(1)]);")
        self.assertEqual(got, [-1, -1, 0, 1, 2, 3, 4])

    def test_audit_rollup_counts_every_ancestor_and_not_gone_marks_as_reviews(self):
        body = '''
const e = (path, status, extra = {}) => ({ mark: { path, qual: "q" }, status, ...extra });
const r = C.auditRollup([e("a/b/x.py", "reviewed"), e("a/b/y.py", "reviewed", { unverified: true }), e("a/z.py", "gone"), e("a/b/x.py", "concern"), e("a/b/x.py", "rereview"), { mark: null }, null]);
out([r[""], r["a"], r["a/b"], Object.keys(r).sort()]);
'''
        got = self.run_node(body)
        self.assertEqual(got[0]["reviewed"], 2)
        self.assertEqual(got[0]["gone"], 1)
        self.assertEqual(got[0]["unchecked"], 1)
        self.assertEqual(got[0]["marked"], 5)
        self.assertEqual(got[2]["concern"], 1)
        self.assertEqual(got[2]["rereview"], 1)
        self.assertEqual(got[2]["gone"], 0)
        self.assertEqual(got[3], ["", "a", "a/b"])

    def test_notes_batch_picks_the_lowest_tier_and_the_right_prompt(self):
        body = '''
const f = (path, tier, reason) => ({ path, tier, reason, symbols: 2 });
const prompts = { A: "PROMPT-A", B: "PROMPT-B" };
const fresh = C.notesBatch({ files: [f("a", 2, "new"), f("b", 1, "new"), f("c", 1, "new"), f("d", 1, "new")] }, prompts, { limit: 2 });
const changed = C.notesBatch({ files: [f("a", 1, "changed"), f("b", 1, "changed"), f("c", 1, "new")] }, prompts);
out([fresh.tier, fresh.files.map((x) => x.path), fresh.kind, fresh.command, fresh.prompt.endsWith("PROMPT-A"), changed.kind, C.notesBatch({ files: [] }, prompts), C.notesBatch(null, prompts)]);
'''
        got = self.run_node(body)
        self.assertEqual(got[0], 1)
        self.assertEqual(got[1], ["b", "c"])        # input order is the order of status.json, and only the lowest tier is batched
        self.assertEqual(got[2], "A")
        self.assertEqual(got[3], "python scripts/notes.py todo --tier 1 --limit 2 --minime ../MiniMe")
        self.assertTrue(got[4])
        self.assertEqual(got[5], "B")
        self.assertEqual(got[6:], [None, None])

    def test_flow_batch_prefers_refresh_over_new_and_takes_two_at_a_time(self):
        body = '''
const fl = (s, extra = {}) => ({ status: s, incomplete: [], ...extra });
const flows = { a: fl("missing"), b: fl("missing"), c: fl("missing"), d: fl("fresh"), e: fl("stale"), f: fl("fresh", { incomplete: ["s1"] }) };
const prompts = { C: "PROMPT-C", D: "PROMPT-D" };
const one = C.flowBatch({ a: fl("missing"), b: fl("missing"), c: fl("missing") }, ["a", "b", "c"], prompts);
const two = C.flowBatch(flows, ["a", "b", "c", "d", "e", "f"], prompts);
out([one.kind, one.flows, two.kind, two.flows, two.missing, C.flowBatch({ a: fl("fresh") }, ["a"], prompts), C.flowBatch({}, [], prompts)]);
'''
        got = self.run_node(body)
        self.assertEqual(got[:2], ["C", ["a", "b"]])
        self.assertEqual(got[2:5], ["D", ["e", "f"], ["a", "b", "c"]])
        self.assertEqual(got[5:], [None, None])


@unittest.skipUnless(NODE, "node is not installed")
class PageInJsdom(unittest.TestCase):
    def test_page_and_chip_behaviour(self):
        r = subprocess.run([NODE, str(ROOT / "scripts" / "explorer_tests" / "coverage.mjs")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=240, env={"NODE_NO_WARNINGS": "1", "PATH": os.environ.get("PATH", "")})
        if r.returncode == 77:
            self.skipTest("jsdom is not installed (npm install --prefix scripts/explorer_tests jsdom)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
