#!/usr/bin/env python3
"""
test_codepages.py -- tests for the API and Agents pages (P17). Standard library only; the JavaScript tests need `node` (skipped without it).

What is checked
  * assets/js/codepages.js (the pure helpers both pages share) runs under Node, no DOM and no network, and produces exactly the KPIs,
    bars, rows and flags the old regex-built api.html and agents.html showed. That "golden" is frozen in scripts/golden/p17_*.json,
    taken from those pages at the commit before P17, together with the slice of the census they were built from.
  * data/code/routes.json and agents.json built from that census slice hold the same information as the old pages' tables.
  * with a MiniMe checkout at the golden commit next to this repo (../MiniMe, or $MINIME_REPO), the frontend scan finds exactly the
    callers the old page counted. Skipped when MiniMe is not there or is at another commit.
  * the committed data files are consistent with the census, and the two pages are shells (small, no baked-in data, modules exist).

    python scripts/test_codepages.py
"""
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
GOLD = ROOT / "scripts" / "golden"
NODE = shutil.which("node")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ra = load("refresh_atlas")
rg = load("refresh_graph")


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def fmt(n):
    return f"{n:,}"


def by_count(pairs):
    """Bars with equal counts may be listed in a different order; the information is the same."""
    return sorted(([a, b] for a, b in pairs), key=lambda p: (-p[1], p[0]))


def run_node(script):
    """Run `script` (an ES module body) next to copies of the modules it imports; return its stdout parsed as JSON."""
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "explorer").mkdir()
        shutil.copy(ROOT / "assets/js/codepages.js", tmp / "codepages.js")
        shutil.copy(ROOT / "assets/js/links.js", tmp / "links.js")
        shutil.copy(ROOT / "assets/js/explorer/router.js", tmp / "explorer" / "router.js")
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (tmp / "t.js").write_text(script, encoding="utf-8")
        r = subprocess.run([NODE, "t.js"], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError(f"node failed:\n{r.stderr}")
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class Golden(unittest.TestCase):
    """The new data files, built from the census slice the old pages were built from, say what the old pages said."""

    @classmethod
    def setUpClass(cls):
        cls.slice = jload(GOLD / "p17_census_slice.json")
        cls.api_old = jload(GOLD / "p17_api_old.json")
        cls.ag_old = jload(GOLD / "p17_agents_old.json")
        cls.routes = ra.build_routes(cls.slice)
        cls.agents = ra.build_agents(cls.slice)

    def test_every_route_row_of_the_old_page_is_in_routes_json(self):
        short = lambda p: p[len("backend/api/"):] if p.startswith("backend/api/") else p
        new = [[r["method"], r["path"], r["handler"], short(r["file"]), r["line"], ", ".join(r["deps"]) or "none", r["response_model"] or ""] for r in self.routes["routes"]]
        self.assertEqual([row[:7] for row in self.api_old["rows"]], new)

    def test_every_module_row_of_the_old_page_is_in_agents_json(self):
        new = [[m["name"], m["doc"][:52], m["code"], m["functions"], len(m["tests"]), m["commits"], m["last"]] for m in self.agents["modules"]]
        self.assertEqual([r[:7] for r in self.ag_old["rows"]], new, "the old table cut the docstring at 52 characters; the new data keeps up to 200")

    def test_roles_providers_and_slots_add_up_like_the_old_charts(self):
        slots = sum(len(p["slots"]) for p in self.agents["providers"])
        self.assertEqual(int(self.ag_old["kpis"][2][0]), slots)
        self.assertEqual(by_count([[p["name"], len(p["slots"])] for p in self.agents["providers"]]), by_count(self.ag_old["provider_bars"]))
        self.assertEqual(by_count([[r["key"], len(r["slots"])] for r in self.agents["roles"] if r["slots"]]), by_count(self.ag_old["role_bars"]))
        unserved = [r["key"] + " · no key slot" for r in self.agents["roles"] if not r["slots"]]
        self.assertEqual(sorted(p for p in self.ag_old["pills"] if p.endswith("no key slot")), sorted(unserved))
        self.assertEqual(self.ag_old["pills"], [r["key"] + (" · no key slot" if not r["slots"] else "") for r in self.agents["roles"]])

    def test_no_secret_value_is_in_agents_json_only_slot_names(self):
        text = json.dumps(self.agents)
        self.assertFalse(re.search(r"(sk-|gsk_|AIza|hf_)[A-Za-z0-9_-]{16,}", text))
        for p in self.agents["providers"]:
            for s in p["slots"]:
                self.assertRegex(s, r"^[A-Z0-9_]+$", "a slot is the name of an environment variable")

    def test_a_role_is_tied_to_a_module_only_when_they_share_a_name(self):
        names = {m["name"] for m in self.agents["modules"]}
        for r in self.agents["roles"]:
            self.assertEqual(r["key"] in names, "module" in r, r["key"])

    def test_a_router_is_linked_only_when_exactly_one_include_is_named_after_the_file(self):
        inc = [{"alias": "chats_router", "prefix": "/x"}, {"alias": "mcp_routes", "prefix": ""}, {"alias": "mcp_routes", "prefix": ""}, {"alias": "tasks", "prefix": ""}, {"alias": "tasks_router", "prefix": ""}]
        self.assertEqual("chats_router", ra.router_include("backend/api/routes/chats.py", inc)["alias"])
        self.assertIsNone(ra.router_include("backend/api/routes/mcp.py", inc), "two includes of one name: ambiguous, so none")
        self.assertIsNone(ra.router_include("backend/api/routes/tasks.py", inc), "two different candidates: ambiguous, so none")
        self.assertIsNone(ra.router_include("backend/api/routes/other.py", inc))


class CommittedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = jload(ROOT / "data" / "census.json")
        cls.routes = jload(ROOT / ra.ROUTES_REL)
        cls.agents = jload(ROOT / ra.AGENTS_REL)

    def test_the_census_half_of_routes_json_is_the_census(self):
        strip = lambda d: {**d, "routes": [{k: v for k, v in r.items() if k != "callers"} for r in d["routes"]]}
        built = ra.build_routes(self.census, self.routes)
        self.assertEqual(strip(built), strip(self.routes))
        self.assertEqual(len(self.census["routes"]), len(self.routes["routes"]))
        keys = [r["key"] for r in self.routes["routes"]]
        self.assertEqual(len(keys), len(set(keys)), "a route key (METHOD path) must be unique: the page's hash links use it")

    def test_agents_json_is_the_census(self):
        self.assertEqual(ra.build_agents(self.census), self.agents)

    def test_every_caller_is_a_frontend_file_of_the_census_with_a_known_kind_of_evidence(self):
        paths = {f["path"] for f in self.census["files"]}
        for r in self.routes["routes"]:
            files = [c["file"] for c in r["callers"]]
            self.assertEqual(files, sorted(files))
            self.assertEqual(len(files), len(set(files)))
            for c in r["callers"]:
                self.assertIn(c["file"], paths, f'{r["key"]} <- {c["file"]}')
                self.assertTrue(c["file"].startswith("frontend/"))
                self.assertTrue(c["via"] and set(c["via"]) <= set(rg.VIA_ORDER) and c["via"] == [v for v in rg.VIA_ORDER if v in c["via"]])
        scan = self.routes["callers_scan"]
        self.assertEqual(scan["pairs"], sum(len(r["callers"]) for r in self.routes["routes"]))

    def test_the_caller_scan_is_from_the_census_commit_or_the_page_would_say_so(self):
        scan = self.routes["callers_scan"]
        self.assertTrue(scan["commit"].startswith(self.routes["commit"]), "the committed scan is stale against the census: run python scripts/update_all.py")


class Pages(unittest.TestCase):
    def test_the_pages_are_small_shells_with_no_data_baked_in(self):
        for name, data in (("api", "routes"), ("agents", "agents")):
            html = (ROOT / f"{name}.html").read_text(encoding="utf-8")
            self.assertLess(len(html.encode("utf-8")), 100_000)
            self.assertNotIn("ROWS=", html)
            self.assertNotIn("<table", html)
            self.assertIn(f'data-page="{name}"', html)
            self.assertIn('id="cp-app"', html)
            self.assertIn(f"assets/js/{name}.js", html)
            self.assertIn("assets/css/codepages.css", html)
            self.assertIn(f"data/code/{data}.json", html)
            self.assertEqual(1, html.count("<title>"))

    def test_every_module_a_page_imports_exists_and_parses(self):
        if not NODE:
            self.skipTest("node is not installed")
        for name in ("api", "agents", "codeui", "codepages"):
            src = (ROOT / "assets" / "js" / f"{name}.js").read_text(encoding="utf-8")
            for rel in re.findall(r'from\s+"(\.{1,2}/[^"]+)"', src):
                self.assertTrue((ROOT / "assets" / "js" / rel).resolve().is_file(), f"{name}.js imports {rel}")
            tmp = Path(tempfile.mkdtemp())
            try:
                (tmp / f"{name}.mjs").write_text(src, encoding="utf-8")
                r = subprocess.run([NODE, "--check", str(tmp / f"{name}.mjs")], capture_output=True, text=True)
                self.assertEqual(0, r.returncode, r.stderr)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_the_pages_write_text_not_html(self):
        for name in ("api", "agents", "codeui"):
            src = (ROOT / "assets" / "js" / f"{name}.js").read_text(encoding="utf-8")
            self.assertNotRegex(src, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", name)


@unittest.skipUnless(NODE, "node is not installed")
class Helpers(unittest.TestCase):
    """codepages.js under Node, on the real committed data and on small inputs."""

    @classmethod
    def setUpClass(cls):
        cls.api_old = jload(GOLD / "p17_api_old.json")
        cls.ag_old = jload(GOLD / "p17_agents_old.json")
        cls.out = run_node(f"""
import fs from "node:fs";
import * as P from "./codepages.js";
const routes = JSON.parse(fs.readFileSync({json.dumps(str(ROOT / "data/code/routes.json"))}, "utf8"));
const agents = JSON.parse(fs.readFileSync({json.dumps(str(ROOT / "data/code/agents.json"))}, "utf8"));
const rows = P.routeRows(routes);
const emit = {{
  kpis: P.routeKpis(rows), perFile: P.routesPerFile(rows), callers: P.callerFiles(rows),
  agentKpis: P.agentKpis(agents), providers: P.providerCounts(agents), roles: P.roleCounts(agents), unserved: P.unservedRoles(agents),
  modules: P.moduleRows(agents).map((m) => [m.name, m.role ? m.role.key : null, m.testCount]),
  called: rows.map((r) => [r.method, r.path, r.called]),
  hashes: rows.slice(0, 3).concat(rows.filter((r) => r.path.includes("{{")).slice(0, 2)).map((r) => [P.routeHash(r), P.routeFromHash(rows, P.routeHash(r)) === rows.find((x) => x.key === r.key)]),
  widths: P.barWidths([{{ n: 28 }}, {{ n: 14 }}, {{ n: 1 }}, {{ n: 0 }}]),
  widthsEmpty: P.barWidths([]),
  filter: P.filterRows([{{ t: "GET /api/chats" }}, {{ t: "POST /api/chats" }}, {{ t: "GET /api/tasks" }}], "  CHATS  get ", (r) => r.t).map((r) => r.t),
  filterAll: P.filterRows([1, 2], "", (r) => String(r)),
  sortNum: P.sortRows([{{ v: 10 }}, {{ v: 9 }}, {{ v: null }}, {{ v: 100 }}], (r) => r.v, true).map((r) => r.v),
  sortNumDesc: P.sortRows([{{ v: 10 }}, {{ v: 9 }}, {{ v: null }}, {{ v: 100 }}], (r) => r.v, false).map((r) => r.v),
  sortText: P.sortRows([{{ v: "b" }}, {{ v: "" }}, {{ v: "A" }}, {{ v: "a" }}], (r) => r.v, true).map((r) => r.v),
  sortStable: P.sortRows([{{ k: 1, i: "x" }}, {{ k: 1, i: "y" }}, {{ k: 0, i: "z" }}], (r) => r.k, true).map((r) => r.i),
  via: [P.viaRank(["shape"]), P.viaRank(["score", "shape"]), P.viaRank(["method", "shape"]), P.viaRank([]), P.viaRank(undefined), P.viaText(["method", "shape", "x"])],
  chain: [P.prefixChain({{ path: "/a" }}), P.prefixChain({{ path: "/a/b", router: "r", include_prefix: "/api", prefix: "/a" }}), P.prefixChain({{ path: "/p", router: "r", include_prefix: "" }})],
  badKey: P.routeFromHash(rows, "#%E0%A4%A"), noKey: P.routeFromHash(rows, "#GET%20%2Fnope"),
  sym: [P.pickSymbol({{ symbols: [{{ qual: "f", summary: "s" }}] }}, "f"), P.pickSymbol({{ symbols: [] }}, "f"), P.pickSymbol(null, "f"), P.pickSymbol({{}}, "f")],
  noteState: [P.noteState({{ files: {{ "a.py": {{ status: "fresh" }} }} }}, "a.py"), P.noteState({{ files: {{ "a.py": {{ status: "stale" }} }} }}, "a.py"),
              P.noteState({{ files: {{ "a.py": {{ status: "fresh", bad: ["x"] }} }} }}, "a.py"), P.noteState({{ files: {{}} }}, "a.py"), P.noteState(null, "a.py")],
  noteFile: P.noteFile("backend/api/routes/chats.py"),
  scan: [P.scanInfo(routes), P.scanInfo({{}}), P.scanInfo({{ commit: "bbbbbbb", callers_scan: {{ commit: "aaaaaaa1111", frontend_files: 3, pairs: 4 }} }})],
  href: [P.explorerHref("backend/api/x.py"), P.explorerHref("backend/api/x.py", {{ qual: "h", start: 5, end: 9 }})],
  fmt: [P.fmtN(12345), P.fmtN(NaN), P.fmtN(undefined)],
  names: [P.shortFile("backend/api/routes/chats.py"), P.shortFile("daemon/x.py"), P.stem("a/b/c.test.js"), P.baseName("a/b/c.js")],
  empty: [P.routeRows(null), P.agentKpis(null), P.moduleRows(undefined), P.roleCounts({{}}), P.unservedRoles(null)],
}};
console.log(JSON.stringify(emit));
""")

    def test_route_kpis_and_bars_equal_the_old_page(self):
        o = self.out
        self.assertEqual([[fmt(k["value"]), k["label"]] for k in o["kpis"]], self.api_old["kpis"])
        self.assertEqual(by_count([[b["name"], b["n"]] for b in o["perFile"]]), by_count(self.api_old["routes_per_file"]))
        self.assertEqual([[b["name"], b["n"]] for b in o["callers"]], self.api_old["caller_files"])

    def test_every_routes_caller_count_equals_the_old_column(self):
        old = {(r[0], r[1]): r[7] for r in self.api_old["rows"]}
        new = {(m, p): n for m, p, n in self.out["called"]}
        self.assertEqual(set(old), set(new))
        self.assertEqual([], [(k, old[k], new[k]) for k in old if (old[k] or 0) != new[k]])

    def test_agent_kpis_and_charts_equal_the_old_page(self):
        o = self.out
        self.assertEqual([[fmt(k["value"]), k["label"]] for k in o["agentKpis"]], self.ag_old["kpis"])
        self.assertEqual(by_count([[b["name"], b["n"]] for b in o["providers"]]), by_count(self.ag_old["provider_bars"]))
        self.assertEqual(by_count([[b["name"], b["n"]] for b in o["roles"]]), by_count(self.ag_old["role_bars"]))
        self.assertEqual(sorted(o["unserved"]), sorted(p[:-len(" · no key slot")] for p in self.ag_old["pills"] if p.endswith("no key slot")))
        self.assertEqual([[m[0], m[2]] for m in o["modules"]], [[r[0], r[4]] for r in self.ag_old["rows"]])

    def test_provider_bars_are_biggest_first_and_ties_go_by_name(self):
        ps = self.out["providers"]
        self.assertEqual(ps, sorted(ps, key=lambda b: (-b["n"], b["name"])))

    def test_bar_widths_scale_to_the_biggest_with_a_visible_minimum(self):
        self.assertEqual([55, 27.5, 2, 1.1], self.out["widths"])
        self.assertEqual([], self.out["widthsEmpty"])

    def test_filtering_matches_every_word_in_any_order_and_ignores_case(self):
        self.assertEqual(["GET /api/chats"], self.out["filter"])
        self.assertEqual([1, 2], self.out["filterAll"])

    def test_sorting_is_stable_and_puts_empty_values_last_both_ways(self):
        self.assertEqual([9, 10, 100, None], self.out["sortNum"])
        self.assertEqual([100, 10, 9, None], self.out["sortNumDesc"])
        self.assertEqual(["A", "a", "b", ""], self.out["sortText"])
        self.assertEqual(["z", "x", "y"], self.out["sortStable"])

    def test_how_well_a_caller_is_backed_ranks_method_over_score_over_shape(self):
        self.assertEqual([2, 1, 0, 3, 3], self.out["via"][:5])
        self.assertEqual("best path match, and the code names this HTTP method; same path shape (HTTP method ignored); x", self.out["via"][5])

    def test_the_prefix_chain_holds_only_what_is_known(self):
        a, b, c = self.out["chain"]
        self.assertEqual([{"label": "decorator path", "prefix": "/a"}], a)
        self.assertEqual(["include_router(r)", "APIRouter(prefix=...)", "decorator path"], [x["label"] for x in b])
        self.assertEqual("", c[0]["prefix"], "an include with an empty prefix is a known fact, and is shown")

    def test_route_hashes_round_trip_and_a_bad_hash_finds_nothing_instead_of_throwing(self):
        for h, ok in self.out["hashes"]:
            self.assertTrue(ok, h)
            self.assertTrue(h.startswith("#") and " " not in h and "/" not in h[1:] and "{" not in h)
        self.assertIsNone(self.out["badKey"])
        self.assertIsNone(self.out["noKey"])

    def test_notes_are_found_and_judged_fresh_or_stale_by_the_explorers_rule(self):
        self.assertEqual({"qual": "f", "summary": "s"}, self.out["sym"][0])
        self.assertEqual([None, None, None], self.out["sym"][1:])
        self.assertEqual(["fresh", "stale", "stale", "none", "none"], self.out["noteState"])
        self.assertEqual("data/notes/backend__api__routes__chats.py.json", self.out["noteFile"])
        self.assertTrue((ROOT / self.out["noteFile"]).is_file(), "the file name rule must match the notes the pipeline writes")

    def test_the_scan_age_line_flags_a_scan_from_another_commit_or_none_at_all(self):
        real, none, other = self.out["scan"]
        self.assertFalse(real["stale"])
        self.assertIn("191 frontend files", real["text"])
        self.assertTrue(none["stale"])
        self.assertIn("refresh_graph.py", none["text"])
        self.assertTrue(other["stale"])
        self.assertIn("aaaaaaa", other["text"])

    def test_explorer_links_use_the_explorers_own_route_format(self):
        self.assertEqual("explorer.html#/f/backend/api/x.py", self.out["href"][0])
        self.assertTrue(self.out["href"][1].startswith("explorer.html#/f/backend/api/x.py::h@5-9"), self.out["href"][1])

    def test_missing_input_gives_empty_results_not_a_crash(self):
        self.assertEqual([[], 6, [], [], []], [self.out["empty"][0], len(self.out["empty"][1]), self.out["empty"][2], self.out["empty"][3], self.out["empty"][4]])
        self.assertEqual(["12,345", "–", "–"], self.out["fmt"])
        self.assertEqual(["routes/chats.py", "daemon/x.py", "c.test", "c.js"], self.out["names"])


class RealFrontend(unittest.TestCase):
    """The scan finds, on the real MiniMe frontend, exactly the callers the old api.html counted."""

    def minime(self):
        for c in (os.environ.get("MINIME_REPO"), str(ROOT.parent / "MiniMe")):
            if c and (Path(c) / "frontend").is_dir():
                return Path(c)
        return None

    def test_counts_equal_the_old_page_on_the_commit_it_was_built_from(self):
        mm = self.minime()
        if not mm:
            self.skipTest("no MiniMe checkout next to this repo (set MINIME_REPO)")
        head = rg.git_head(mm)
        gold = jload(GOLD / "p17_census_slice.json")["git"]["head_full"]
        if head != gold:
            self.skipTest(f"MiniMe is at {str(head)[:7]}, the golden numbers are for {gold[:7]}")
        routes = [{"method": r["method"], "path": r["path"]} for r in jload(GOLD / "p17_census_slice.json")["routes"]]
        callers, scan = rg.api_callers(mm / "frontend", head, routes)
        old = {(r[0], r[1]): r[7] for r in jload(GOLD / "p17_api_old.json")["rows"]}
        new = {(r["method"], r["path"]): len(callers.get(f'{r["method"]} {r["path"]}', [])) for r in routes}
        self.assertEqual([], [(k, old[k], new[k]) for k in old if (old[k] or 0) != new[k]])
        self.assertEqual(215, scan["pairs"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
