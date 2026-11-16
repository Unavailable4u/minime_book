#!/usr/bin/env python3
"""Tests for the Overview (patch P07). Run: python scripts/test_overview.py

Covers assets/js/overview.js (its pure helpers, run in Node with no browser), index.html (now a shell), assets/css/overview.css,
content/subsystems.json, content/system/request-path.json, content/overview/*, and data/index/vitals.json against data/census.json.
The tests that need Node are skipped, not failed, when `node` is not on PATH. The generators that write vitals.json are tested in
scripts/test_refresh_atlas.py (census half) and scripts/test_refresh_graph.py (graph half). Standard library only.
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

import check_site  # noqa: E402

NODE = shutil.which("node")
JS = ROOT / "assets" / "js"
OVERVIEW_JS = JS / "overview.js"
LIBRARY_JS = JS / "library.js"
OVERVIEW_CSS = ROOT / "assets" / "css" / "overview.css"
COMPONENTS_CSS = ROOT / "assets" / "css" / "components.css"
INDEX_HTML = ROOT / "index.html"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def text(path):
    return Path(path).read_text(encoding="utf-8")


def run_node(body, data=None):
    """Run `body` (ES module code that can use `M`, the exports of overview.js, and `data`) in a temp folder holding overview.js and
    library.js (which it imports); return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(OVERVIEW_JS, tmp / "overview.js")
        shutil.copy(LIBRARY_JS, tmp / "library.js")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text("import * as M from './overview.js'; import fs from 'node:fs';\n"
                                     "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


CENSUS = {"commit": "94af156", "generated": "2026-11-15", "dirty_files": 0}
GRAPH = {"commit": "94af156", "date": "2026-11-15", "nodes": 5, "links": 7, "communities": 2, "hubs": []}


@unittest.skipUnless(NODE, "node is not installed")
class PureHelpers(unittest.TestCase):
    def test_importing_the_module_in_node_does_not_boot_the_page_or_the_library(self):
        self.assertEqual(True, run_node("console.log(JSON.stringify(typeof M.freshness === 'function'))"))

    def test_same_commit_accepts_a_prefix_either_way_round(self):
        out = run_node("console.log(JSON.stringify([M.sameCommit('94af156','94af1566ab'), M.sameCommit('94af1566ab','94af156'),"
                       " M.sameCommit('94af156','50e25b5'), M.sameCommit('', '94af156'), M.sameCommit(null, null)]))")
        self.assertEqual([True, True, False, False, False], out)

    def test_percent_has_one_decimal_and_a_dash_without_a_denominator(self):
        out = run_node("console.log(JSON.stringify([M.fmtPct(3015, 16255), M.fmtPct(1, 3), M.fmtPct(0, 10), M.fmtPct(5, 0)]))")
        self.assertEqual(["18.5 %", "33.3 %", "0.0 %", "–"], out)

    def test_docs_built_is_the_newest_chapter_build(self):
        out = run_node("console.log(JSON.stringify([M.docsBuilt({chapters:[{built:'2026-10-07'},{built:'2026-10-12'},{}]}), M.docsBuilt({}), M.docsBuilt(null)]))")
        self.assertEqual(["2026-10-12", "", ""], out)

    def freshness(self, **kw):
        return run_node("console.log(JSON.stringify(M.freshness(data)))", kw)

    def test_everything_from_one_commit_is_in_step(self):
        f = self.freshness(census=CENSUS, graph=GRAPH, notes=None, docs="2026-10-12")
        self.assertEqual("ok", f["state"])
        self.assertEqual([], f["reasons"])
        self.assertEqual(["census", "graph", "notes", "docs"], [i["id"] for i in f["items"]])
        self.assertEqual("none", next(i for i in f["items"] if i["id"] == "notes")["tone"], "no notes yet is not a reason to be amber")

    def test_a_graph_from_another_commit_makes_the_chip_amber_and_says_why(self):
        f = self.freshness(census=CENSUS, graph=dict(GRAPH, commit="50e25b5"), notes=None, docs="")
        self.assertEqual("stale", f["state"])
        self.assertEqual("stale", next(i for i in f["items"] if i["id"] == "graph")["tone"])
        self.assertIn("50e25b5", f["reasons"][0])
        self.assertIn("94af156", f["reasons"][0])

    def test_a_missing_graph_a_missing_census_and_a_dirty_census_are_each_reported(self):
        self.assertEqual("stale", self.freshness(census=CENSUS, graph=None, notes=None, docs="")["state"])
        f = self.freshness(census=None, graph=None, notes=None, docs="")
        self.assertEqual("stale", f["state"])
        self.assertEqual(2, len(f["reasons"]))
        dirty = self.freshness(census=dict(CENSUS, dirty_files=3), graph=GRAPH, notes=None, docs="")
        self.assertEqual("stale", dirty["state"])
        self.assertIn("3 uncommitted", dirty["reasons"][0])

    def test_notes_from_another_commit_are_stale_and_notes_from_this_one_are_not(self):
        self.assertEqual("stale", self.freshness(census=CENSUS, graph=GRAPH, notes={"percent": 14.2, "commit": "50e25b5"}, docs="")["state"])
        ok = self.freshness(census=CENSUS, graph=GRAPH, notes={"percent": 14.2, "commit": "94af1566ab"}, docs="")
        self.assertEqual("ok", ok["state"])
        self.assertEqual("notes 14 %", next(i for i in ok["items"] if i["id"] == "notes")["text"])

    def test_spark_points_scale_into_the_box_and_a_flat_series_is_a_flat_line(self):
        out = run_node("console.log(JSON.stringify([M.sparkPoints([0, 10], 100, 20, 0), M.sparkPoints([5, 5, 5], 100, 20, 0), M.sparkPoints([1]), M.sparkPoints([]), M.sparkPoints([1, NaN, 3], 10, 10, 0)]))")
        self.assertEqual("0,20 100,0", out[0])
        self.assertEqual("0,10 50,10 100,10", out[1])
        self.assertEqual("", out[2])
        self.assertEqual("", out[3])
        self.assertEqual("0,10 10,0", out[4], "a value that is not a number is dropped, not drawn as 0")

    def test_github_links_point_at_the_indexed_commit_and_encode_each_segment(self):
        out = run_node("console.log(JSON.stringify([M.githubUrl('backend/eo/registry.py', '94af156', 1991), M.githubUrl('a b/c#d.py', null, 0)]))")
        self.assertEqual("https://github.com/Unavailable4u/MiniMe/blob/94af156/backend/eo/registry.py#L1991", out[0])
        self.assertEqual("https://github.com/Unavailable4u/MiniMe/blob/main/a%20b/c%23d.py", out[1])

    def test_a_vital_with_no_data_is_left_out_not_shown_as_zero(self):
        census = {"commit": "94af156", "generated": "2026-11-15", "dirty_files": 0, "kpis": {"files": 10, "functions": 4}, "months": []}
        out = run_node("console.log(JSON.stringify(M.vitalCards(data.v, data.copy).map(c => c.id)))", {"v": {"census": census}, "copy": {"vitals": {}}})
        self.assertEqual(["files", "functions"], out)

    def test_vital_cards_carry_the_commit_and_day_they_were_measured_at(self):
        v = load("data/index/vitals.json")
        cards = run_node("console.log(JSON.stringify(M.vitalCards(data.v, data.copy)))", {"v": v, "copy": load("content/overview/vitals.json")})
        self.assertEqual(["files", "code_lines", "functions", "docstrings", "routes", "commits", "tests_written", "nodes", "links"], [c["id"] for c in cards])
        for c in cards:
            self.assertTrue(c["source"]["commit"] and c["source"]["date"], c["id"])
            self.assertTrue(c["why"], f'{c["id"]} needs a "why this matters" line in content/overview/vitals.json')
            self.assertTrue(c["label"] and c["label"] != c["id"], c["id"])
        by = {c["id"]: c for c in cards}
        self.assertEqual(v["census"]["commit"], by["files"]["source"]["commit"])
        self.assertEqual(v["graph"]["commit"], by["nodes"]["source"]["commit"])
        self.assertIn(" %", by["docstrings"]["display"])
        self.assertEqual(len(v["census"]["months"]), len(by["commits"]["spark"]["values"]))

    def test_the_graph_vitals_turn_amber_when_the_graph_is_from_another_commit(self):
        v = load("data/index/vitals.json")
        v["graph"]["commit"] = "50e25b5"
        cards = run_node("console.log(JSON.stringify(M.vitalCards(data.v, data.copy)))", {"v": v, "copy": {}})
        self.assertEqual({"stale"}, {c["source"]["tone"] for c in cards if c["id"] in ("nodes", "links")})
        self.assertEqual({"ok"}, {c["source"]["tone"] for c in cards if c["id"] not in ("nodes", "links")})

    def test_directory_rows_add_up_and_files_nobody_claims_come_last(self):
        v = load("data/index/vitals.json")["census"]
        out = run_node("console.log(JSON.stringify(M.directoryRows(data.spec, data.counts, data.nav, data.book, data.commit)))",
                       {"spec": load("content/subsystems.json"), "counts": v["subsystems"], "nav": load("content/nav.json"),
                        "book": load("data/index/book.json"), "commit": v["commit"]})
        rows, totals = out["rows"], out["totals"]
        self.assertEqual("other", rows[-1]["id"])
        self.assertEqual(v["kpis"]["files"], totals["files"])
        self.assertEqual(v["kpis"]["code_lines"], totals["code"])
        self.assertEqual(v["kpis"]["functions"], totals["functions"])
        eo = next(r for r in rows if r["id"] == "eo")
        self.assertEqual("Ch. 4", eo["chapter"]["label"])
        self.assertTrue(eo["chapter"]["url"].startswith("doc-minime-feature-guide.html#"))
        self.assertTrue(all(k["url"].startswith(f"https://github.com/Unavailable4u/MiniMe/blob/{v['commit']}/") for k in eo["keyFiles"]))
        self.assertEqual(["System map", "Agents & roles"], [p["title"] for p in eo["pages"]][:2])

    def test_a_subsystem_with_no_counts_is_a_row_of_zeros_not_a_crash(self):
        spec = {"subsystems": [{"id": "x", "name": "X", "folder": "x", "what": "w", "chapter": "nope#h", "pages": ["ghost"], "key_files": []}]}
        out = run_node("console.log(JSON.stringify(M.directoryRows(data.spec, {}, {wings: []}, {chapters: []}, 'abc')))", {"spec": spec})
        self.assertEqual([{"files": 0, "code": 0, "functions": 0}], [{k: out["rows"][0][k] for k in ("files", "code", "functions")}])
        self.assertIsNone(out["rows"][0]["chapter"])
        self.assertEqual([], out["rows"][0]["pages"])

    def test_the_shard_of_a_file_follows_the_rule_build_index_uses(self):
        ids = ["backend__eo", "backend__files", "frontend", "daemon", "_root"]
        out = run_node("console.log(JSON.stringify(data.paths.map(p => M.shardIdFor(p, data.ids))))",
                       {"ids": ids, "paths": ["backend/eo/registry.py", "backend/x.py", "frontend/app/a.jsx", "daemon/tools.py", "README.md", "m2c/src/a.py"]})
        self.assertEqual(["backend__eo", "backend__files", "frontend", "daemon", "_root", None], out)

    def test_line_of_finds_a_function_in_a_shard_and_is_zero_when_unknown(self):
        shard = {"files": ["a.py", "b.py"], "rows": [["f", 0, 10, "function"], ["f", 1, 20, "function"], ["C.m", 1, 30, "method"]]}
        out = run_node("console.log(JSON.stringify([M.lineOf(data, 'a.py', 'f'), M.lineOf(data, 'b.py', 'f'), M.lineOf(data, 'b.py', 'C.m'), M.lineOf(data, 'b.py', 'nope'), M.lineOf(data, 'c.py', 'f'), M.lineOf(null, 'a.py', 'f')]))", shard)
        self.assertEqual([10, 20, 30, 0, 0, 0], out)


@unittest.skipUnless(NODE, "node is not installed")
class RealData(unittest.TestCase):
    """The content files against the real symbol index: every code reference of the Overview must resolve to a line."""

    def test_every_code_reference_resolves_to_a_line_through_the_same_lookup_the_page_uses(self):
        refs = [k for s in load("content/subsystems.json")["subsystems"] for k in s["key_files"]]
        refs += [c for st in load("content/system/request-path.json")["steps"] for c in st["code"]]
        refs = [r for r in refs if r.get("qual")]
        self.assertGreaterEqual(len(refs), 10)
        manifest = load("data/index/symbols.json")
        shards = {s["id"]: load(f"data/index/{s['file']}") for s in manifest["shards"]}
        out = run_node("console.log(JSON.stringify(data.refs.map(r => { const id = M.shardIdFor(r.path, data.ids);"
                       " return [r.path, r.qual, id, id ? M.lineOf(data.shards[id], r.path, r.qual) : -1]; })))",
                       {"refs": refs, "ids": list(shards), "shards": shards})
        self.assertEqual([], [r for r in out if r[3] <= 0], "these references do not resolve to a line, so the link would point at the top of the file")


class Data(unittest.TestCase):
    def test_vitals_has_every_field_overview_js_reads(self):
        v = load("data/index/vitals.json")
        c = v["census"]
        for key in ("commit", "generated", "dirty_files", "kpis", "docstrings", "languages", "months", "areas", "largest", "changed", "complex", "subsystems"):
            self.assertIn(key, c, f"vitals.census.{key}")
        for key in ("files", "total_lines", "code_lines", "functions", "routes", "commits", "tests_written", "source_files", "test_files"):
            self.assertIsInstance(c["kpis"][key], int, key)
        self.assertEqual({"documented", "python_functions"}, set(c["docstrings"]))
        self.assertTrue(all({"lang", "code"} == set(r) for r in c["languages"]))
        self.assertTrue(all({"month", "commits", "added"} == set(r) for r in c["months"]))
        self.assertTrue(all({"area", "code"} == set(r) for r in c["areas"]))
        self.assertTrue(all({"path", "code"} == set(r) for r in c["largest"]))
        self.assertTrue(all({"path", "commits"} == set(r) for r in c["changed"]))
        self.assertTrue(all({"name", "path", "cc"} == set(r) for r in c["complex"]))
        g = v["graph"]
        for key in ("commit", "date", "nodes", "links", "communities", "hubs"):
            self.assertIn(key, g, f"vitals.graph.{key}")
        self.assertTrue(all({"label", "path", "links"} == set(h) for h in g["hubs"]))

    def test_the_census_half_matches_the_census(self):
        c = load("data/census.json")
        v = load("data/index/vitals.json")["census"]
        self.assertEqual(c["git"]["head"], v["commit"])
        self.assertEqual(c["meta"]["generated"][:10], v["generated"])
        self.assertEqual(c["totals"]["code"], v["kpis"]["code_lines"])
        self.assertEqual(c["totals"]["functions"], v["kpis"]["functions"])
        self.assertEqual(len(c["routes"]), v["kpis"]["routes"])
        self.assertEqual(len(c["git"]["commits"]), v["kpis"]["commits"])
        self.assertEqual(v["kpis"]["commits"], sum(m["commits"] for m in v["months"]))

    def test_every_file_is_counted_in_exactly_one_subsystem(self):
        v = load("data/index/vitals.json")["census"]
        total = {"files": 0, "code": 0, "functions": 0}
        for row in v["subsystems"].values():
            for k in total:
                total[k] += row[k]
        self.assertEqual({"files": v["kpis"]["files"], "code": v["kpis"]["code_lines"], "functions": v["kpis"]["functions"]}, total)
        ids = [s["id"] for s in load("content/subsystems.json")["subsystems"]]
        self.assertEqual(sorted(ids + ["other"]), sorted(v["subsystems"]))

    def test_the_overview_content_passes_the_site_checker(self):
        report = check_site.run_checks(ROOT, allow=[])
        found = [f"{f.code} {f.file} {f.message}" for f in report.errors if f.code.startswith(("overview-", "glossary-", "path-"))]
        self.assertEqual([], found)

    def test_the_request_path_has_steps_and_marks_the_approval_gate_amber(self):
        doc = load("content/system/request-path.json")
        self.assertGreaterEqual(len(doc["steps"]), 4)
        self.assertLessEqual(len(doc["steps"]), 7)
        self.assertEqual(["gatekeeper"], [s["id"] for s in doc["steps"] if s.get("gate")])
        self.assertTrue(doc["needs_review"], "an AI-drafted path must say so until a person has read it")


class Page(unittest.TestCase):
    def test_index_is_a_shell_with_no_generated_regions_left(self):
        html = text(INDEX_HTML)
        self.assertNotIn('<div class="card"><h3>', html)
        self.assertNotIn('<div class="k">', html)
        self.assertNotIn("Snapshot of your working copy", html)
        self.assertLess(len(html.encode("utf-8")), 6000)
        self.assertIn('<script type="module" src="assets/js/overview.js"></script>', html)
        self.assertIn('<link rel="stylesheet" href="assets/css/overview.css">', html)
        self.assertIn("<title>Overview · MiniMe Atlas</title>", html)
        self.assertNotIn("<h1", html, "the h1 lives in the hero fragment")
        self.assertEqual(1, text(ROOT / "content" / "overview" / "hero.html").count("<h1"))

    def test_every_element_overview_js_looks_up_is_on_the_page(self):
        js, html = text(OVERVIEW_JS), text(INDEX_HTML)
        wanted = set(re.findall(r"\$\(\"([a-z-]+)\"\)", js))
        self.assertTrue({"ov-fresh", "ov-steps", "ov-paths", "ov-vitals", "ov-dir", "ov-details-body"} <= wanted)
        for el in sorted(wanted):
            self.assertIn(f'id="{el}"', html, f"index.html has no #{el}")

    def test_every_fragment_the_page_loads_exists_and_nothing_else_is_left_unused(self):
        names = set(re.findall(r'data-fragment="([a-z-]+)"', text(INDEX_HTML)))
        self.assertEqual({"hero", "abstract", "products", "stays-true"}, names)
        for n in names:
            self.assertTrue((ROOT / "content" / "overview" / f"{n}.html").is_file(), n)
        on_disk = {p.stem for p in (ROOT / "content" / "overview").glob("*.html")}
        self.assertEqual(names, on_disk)

    def test_fragments_link_only_to_things_that_exist(self):
        files, _ = check_site.walk_site(ROOT)
        headings = {h["url"] for h in load("data/index/search.json")["headings"]}
        for frag in sorted((ROOT / "content" / "overview").glob("*.html")):
            for href in re.findall(r'href="([^"]+)"', text(frag)):
                if re.match(r"^(https?:|#|mailto:)", href):
                    continue
                self.assertIn(href.split("#")[0], files, f"{frag.name}: {href}")
                if "#" in href:
                    self.assertIn(href, headings, f"{frag.name}: {href} is not a heading id of the chapter")

    def test_the_directory_table_asks_for_a_chapter_that_exists(self):
        chapters = {c["id"] for c in load("data/index/book.json")["chapters"]}
        for s in load("content/subsystems.json")["subsystems"]:
            if s.get("chapter"):
                self.assertIn(s["chapter"].split("#")[0], chapters, s["id"])

    def test_library_js_boots_only_on_the_library_page(self):
        js = text(LIBRARY_JS)
        self.assertRegex(js, r'if \(typeof document !== "undefined" && document\.getElementById\("lib-parts"\)\) \{')
        self.assertEqual(1, js.count('document.addEventListener("DOMContentLoaded", boot'))


class DomPitfalls(unittest.TestCase):
    def test_no_replace_children_call_can_pass_null_which_the_dom_prints_as_the_word_null(self):
        """Only a null that is itself an argument is a problem: h() drops null children, so a null inside h(...) or [...] is fine."""
        js = text(OVERVIEW_JS)
        bad = []
        for m in re.finditer(r"\.replaceChildren\(", js):
            depth, i, top = 1, m.end(), ""
            while depth and i < len(js):
                ch = js[i]
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif depth == 1:
                    top += ch
                i += 1
            if re.search(r":\s*null\b|,\s*null\s*$", top):
                bad.append(js[:m.start()].count("\n") + 1)
        self.assertEqual([], bad, "line(s) where a null can reach replaceChildren as an argument; wrap the list in [...].filter(Boolean)")


class Css(unittest.TestCase):
    def test_every_ov_class_the_page_uses_is_styled(self):
        css = text(OVERVIEW_CSS)
        used = set()
        for src in [OVERVIEW_JS, INDEX_HTML] + sorted((ROOT / "content" / "overview").glob("*.html")):
            body = re.sub(r'\$\("[a-z-]+"\)|\bid="[^"]*"|\bid: `[^`]*`|"aria-controls": "[^"]*"', "", text(src))   # ids are not classes
            used |= set(re.findall(r"\bov-[a-z0-9]+(?:__[a-z0-9]+)?(?:--[a-z0-9]+)?", body))
        used = {u for u in used if not u.endswith(("-", "_"))}
        missing = sorted(u for u in used if f".{u}" not in css)
        self.assertEqual([], missing, "classes used by the page but not styled in overview.css")

    def test_the_tone_variants_of_the_freshness_chip_are_styled(self):
        css = text(OVERVIEW_CSS)
        for tone in ("ok", "stale", "none"):
            self.assertIn(f".ov-fresh__i--{tone}", css) if tone != "none" else None
        self.assertIn('.ov-fresh[data-state="stale"]', css)

    def test_every_mm_class_the_page_uses_exists_in_the_components(self):
        comp = text(COMPONENTS_CSS)
        used = set(re.findall(r"\bmm-[a-z0-9]+(?:__[a-z0-9]+)?(?:--[a-z0-9]+)?", text(OVERVIEW_JS) + text(INDEX_HTML)
                              + "".join(text(p) for p in (ROOT / "content" / "overview").glob("*.html"))))
        used = {u for u in used if not u.endswith(("-", "_"))}
        self.assertEqual([], sorted(u for u in used if f".{u}" not in comp))
        for variant in ("ok", "stale"):                 # built in a template string, so the scan above cannot see them
            self.assertIn(f".mm-badge--{variant}", comp)

    def test_overview_css_uses_tokens_only(self):
        css = text(OVERVIEW_CSS)
        self.assertEqual([], re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", css), "raw colours break the Paper theme")
        self.assertNotRegex(css, r"z-index\s*:\s*\d")


if __name__ == "__main__":
    unittest.main(verbosity=2)
