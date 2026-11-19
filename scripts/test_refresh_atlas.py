#!/usr/bin/env python3
"""
Tests for scripts/refresh_atlas.py. Standard library only.

    python scripts/test_refresh_atlas.py
    python -m unittest discover -s scripts

The first test checks the repo itself: the committed pages must match the
committed data/census.json. If you replaced the census and it fails, run
`python scripts/refresh_atlas.py`. The rest work on a temporary copy of the
pages with a modified census, to pin down behaviour that must not regress:
refreshing is idempotent, --check notices stale pages, and the parts of the
Atlas that come from Graphify (not the census) are preserved.
"""
import copy
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("refresh_atlas", ROOT / "scripts" / "refresh_atlas.py")
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)

FILES = [f"{name}.html" for name in ra.PAGES] + ["data/census.json", "data/summary.md", "data/index/stats.json", "data/index/vitals.json", "data/code/routes.json", "data/code/agents.json",
                                                    "content/subsystems.json", "content/topology.json"]


def read(p):
    return Path(p).read_text(encoding="utf-8")


class RepoState(unittest.TestCase):
    def test_committed_pages_match_the_committed_census(self):
        census = json.loads(read(ROOT / "data" / "census.json"))
        stale = sorted(p.name for p in ra.refresh_all(ROOT, census))
        self.assertEqual([], stale, "pages are out of date with data/census.json; run: python scripts/refresh_atlas.py")


class OnACopy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("data/index", "data/code", "content"):
            (self.tmp / d).mkdir(parents=True)
        for rel in FILES:
            shutil.copy(ROOT / rel, self.tmp / rel)
        self.census = json.loads(read(self.tmp / "data" / "census.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def save_census(self):
        (self.tmp / "data" / "census.json").write_text(json.dumps(self.census, separators=(",", ":")), encoding="utf-8")

    def refresh(self):
        changes = ra.refresh_all(self.tmp, self.census)
        for p, text in changes.items():
            p.write_bytes(text.encode("utf-8"))
        return changes

    def newer_census(self):
        """A census that differs from the committed one: a later snapshot with one more commit."""
        self.census["meta"]["generated"] = "2099-01-02T03:04:05"
        self.census["git"]["head"] = "abc1234"
        self.census["git"]["commits"].insert(0, {"hash": "abc12345", "author": "x", "date": "2099-01-02", "subject": "later commit",
                                                 "files": 1, "added": 5, "deleted": 2})
        self.save_census()

    # ----------------------------------------------------------------- behaviour
    def test_refresh_is_idempotent(self):
        self.newer_census()
        first = self.refresh()
        self.assertTrue(first, "a newer census should change the pages")
        self.assertEqual({}, self.refresh(), "a second refresh must change nothing")

    def test_check_mode_notices_stale_pages_and_passes_once_refreshed(self):
        self.newer_census()
        self.assertEqual(1, ra.main(["--root", str(self.tmp), "--check"]))
        self.assertEqual(0, ra.main(["--root", str(self.tmp)]))
        self.assertEqual(0, ra.main(["--root", str(self.tmp), "--check"]))

    def test_vitals_census_half_follows_the_census(self):
        """index.html is a shell since P07: the numbers it shows are data/index/vitals.json "census"."""
        self.newer_census()
        self.assertIn(self.tmp / "data" / "index" / "vitals.json", self.refresh())
        c = json.loads(read(self.tmp / "data" / "index" / "vitals.json"))["census"]
        self.assertEqual("abc1234", c["commit"])
        self.assertEqual("2099-01-02", c["generated"])
        self.assertEqual(len(self.census["git"]["commits"]), c["kpis"]["commits"])
        self.assertEqual({"commits": 1, "added": 5, "month": "2099-01"}, next(m for m in c["months"] if m["month"] == "2099-01"))
        self.assertEqual(self.census["totals"]["code"], c["kpis"]["code_lines"])
        self.assertIn("2099-01-02", read(self.tmp / "history.html"))

    def test_index_html_is_not_a_generated_page_any_more(self):
        self.assertNotIn("index", ra.PAGES)
        self.assertFalse(hasattr(ra, "refresh_index"))
        before = read(ROOT / "index.html")
        self.newer_census()
        self.refresh()
        self.assertEqual(before, read(ROOT / "index.html"))

    def test_every_file_lands_in_one_subsystem_and_the_rest_in_other(self):
        c = ra.census_vitals(self.census, ra.load_subsystems(self.tmp))
        total = {k: sum(r[k] for r in c["subsystems"].values()) for k in ("files", "code", "functions")}
        self.assertEqual({"files": c["kpis"]["files"], "code": c["kpis"]["code_lines"], "functions": c["kpis"]["functions"]}, total)
        # the longest match wins: a more specific prefix takes its files away from a shorter one
        spec = {"subsystems": [{"id": "all", "match": ["backend/"]}, {"id": "tests", "match": ["backend/tests/"]}]}
        counts = ra.subsystem_counts(self.census, spec)
        n_tests = sum(1 for f in self.census["files"] if not f.get("binary") and f["path"].startswith("backend/tests/"))
        n_back = sum(1 for f in self.census["files"] if not f.get("binary") and f["path"].startswith("backend/"))
        self.assertEqual(n_tests, counts["tests"]["files"])
        self.assertEqual(n_back - n_tests, counts["all"]["files"])
        self.assertEqual({}, ra.subsystem_counts(self.census, None), "no spec: nothing to count, not a crash")

    def test_an_exact_file_match_beats_its_folder(self):
        spec = {"subsystems": [{"id": "dir", "match": ["scripts/"]}, {"id": "one", "match": ["scripts/refresh_atlas.py"]}]}
        counts = ra.subsystem_counts({"files": [{"path": "scripts/refresh_atlas.py", "code": 7, "functions": []},
                                                {"path": "scripts/other.py", "code": 3, "functions": []},
                                                {"path": "README.md", "code": 1, "functions": []}]}, spec)
        self.assertEqual({"files": 1, "code": 7, "functions": 0}, counts["one"])
        self.assertEqual({"files": 1, "code": 3, "functions": 0}, counts["dir"])
        self.assertEqual({"files": 1, "code": 1, "functions": 0}, counts["other"])

    def test_topology_counts_follow_the_layout_and_children_sum_into_their_parent(self):
        """P08: census.topology holds, per node of content/topology.json, the numbers the diagram draws its boxes from."""
        spec = {"nodes": [{"id": "pkg", "folders": ["m2c/src/m2c"], "children": ["tui", "rest"]},
                          {"id": "tui", "folders": ["m2c/src/m2c/tui"], "parent": "pkg"},
                          {"id": "rest", "folders": ["m2c/src/m2c"], "parent": "pkg"},
                          {"id": "empty", "folders": ["nowhere"]}]}
        fn = lambda doc: {"name": "f", "doc": doc}
        files = [{"path": "m2c/src/m2c/tui/a.py", "lang": "python", "code": 10, "functions": [fn(True), fn(False)]},
                 {"path": "m2c/src/m2c/tui/big.py", "lang": "python", "code": 30, "functions": []},
                 {"path": "m2c/src/m2c/run.py", "lang": "python", "code": 5, "functions": [fn(True)]},
                 {"path": "m2c/src/m2c/tui/test_a.py", "lang": "python", "code": 99, "test": True, "functions": [fn(True)]},
                 {"path": "m2c/src/m2c/blob.bin", "lang": "binary", "code": 77, "binary": True, "functions": []}]
        out = ra.topology_counts({"files": files}, spec)
        self.assertEqual({"files": 2, "code": 40, "functions": 2, "documented": 1, "python_functions": 2}, {k: out["tui"][k] for k in out["tui"] if k != "top"})
        self.assertEqual({"files": 1, "code": 5, "functions": 1, "documented": 1, "python_functions": 1}, {k: out["rest"][k] for k in out["rest"] if k != "top"})
        self.assertEqual(3, out["pkg"]["files"], "a node with children is the sum of its children (tests and binaries left out)")
        self.assertEqual(45, out["pkg"]["code"])
        self.assertEqual(["m2c/src/m2c/tui/big.py", "m2c/src/m2c/tui/a.py", "m2c/src/m2c/run.py"], [t["path"] for t in out["pkg"]["top"]])
        self.assertEqual({"files": 0, "code": 0, "functions": 0, "documented": 0, "python_functions": 0, "top": []}, out["empty"])
        self.assertEqual({}, ra.topology_counts({"files": files}, None), "no layout: nothing to count, not a crash")

    def test_every_node_of_the_real_layout_resolves_to_real_files(self):
        spec = json.loads(read(self.tmp / "content" / "topology.json"))
        counts = ra.topology_counts(self.census, spec)
        self.assertEqual({n["id"] for n in spec["nodes"]}, set(counts))
        empty = [i for i, r in counts.items() if not r["files"]]
        self.assertEqual([], empty, "a node that matches no census file would be drawn as a size-less box")
        self.assertEqual(counts, ra.census_vitals(self.census, ra.load_subsystems(self.tmp), spec)["topology"])

    def test_graph_half_of_vitals_is_carried_over_untouched(self):
        graph = json.loads(read(self.tmp / "data" / "index" / "vitals.json"))["graph"]
        self.newer_census()
        self.refresh()
        self.assertEqual(graph, json.loads(read(self.tmp / "data" / "index" / "vitals.json"))["graph"])

    def test_vitals_are_rebuilt_when_missing_or_not_json_and_a_graph_half_is_not_invented(self):
        vp = self.tmp / "data" / "index" / "vitals.json"
        vp.write_text("{not json", encoding="utf-8")
        self.assertEqual(0, ra.main(["--root", str(self.tmp)]))
        d = json.loads(read(vp))
        self.assertEqual({"census"}, set(d), "a refresh of the census must never make up a graph")
        vp.unlink()
        self.assertEqual(0, ra.main(["--root", str(self.tmp)]))
        self.assertEqual({"census"}, set(json.loads(read(vp))))

    def test_graphify_derived_content_is_preserved(self):
        before = read(self.tmp / "explore.html")
        self.newer_census()
        self.refresh()
        self.assertEqual(ra.read_literal(before, ",DC="), ra.read_literal(read(self.tmp / "explore.html"), ",DC="), "doc sections must be untouched")

    def test_api_and_agents_are_shells_not_generated_pages_any_more(self):
        """P17: api.html and agents.html are drawn by assets/js/api.js and agents.js from data/code/routes.json and agents.json."""
        for name in ("api", "agents"):
            self.assertNotIn(name, ra.PAGES)
        for gone in ("refresh_api", "refresh_agents", "agent_rows", "_role_serve", "_short_api"):
            self.assertFalse(hasattr(ra, gone), gone)
        before = {n: read(ROOT / f"{n}.html") for n in ("api", "agents")}
        self.newer_census()
        self.refresh()
        for n in before:
            self.assertEqual(before[n], read(ROOT / f"{n}.html"))
        self.assertEqual("2099-01-02", json.loads(read(self.tmp / ra.ROUTES_REL))["generated"])
        self.assertEqual("abc1234", json.loads(read(self.tmp / ra.AGENTS_REL))["commit"])

    def test_new_route_has_no_callers_and_existing_callers_are_kept(self):
        old = json.loads(read(self.tmp / ra.ROUTES_REL))
        old_callers = {r["key"]: r["callers"] for r in old["routes"]}
        self.assertTrue(any(old_callers.values()), "the committed routes.json should carry callers from the last frontend scan")
        r0 = copy.deepcopy(self.census["routes"][0])
        r0.update(path="/api/brand-new-route", handler="brand_new")
        self.census["routes"].append(r0)
        self.save_census()
        self.refresh()
        doc = json.loads(read(self.tmp / ra.ROUTES_REL))
        new = [r for r in doc["routes"] if r["path"] == "/api/brand-new-route"]
        self.assertEqual(1, len(new))
        self.assertEqual([], new[0]["callers"], "no frontend scan has seen a new route: no callers, not a made-up one")
        for r in doc["routes"]:
            if r["key"] in old_callers:
                self.assertEqual(old_callers[r["key"]], r["callers"])
        self.assertEqual(old["callers_scan"], doc["callers_scan"], "the scan description belongs to refresh_graph.py and is kept")

    def test_a_removed_route_takes_its_callers_with_it_and_a_renamed_one_starts_empty(self):
        self.census["routes"][0]["path"] = "/api/renamed"
        self.save_census()
        self.refresh()
        doc = json.loads(read(self.tmp / ra.ROUTES_REL))
        self.assertEqual(len(self.census["routes"]), len(doc["routes"]))
        self.assertEqual([], next(r for r in doc["routes"] if r["path"] == "/api/renamed")["callers"])

    def test_routes_json_is_rebuilt_when_missing_or_not_json_and_no_callers_are_invented(self):
        rp = self.tmp / ra.ROUTES_REL
        for damage in (lambda: rp.write_text("{not json", encoding="utf-8"), rp.unlink):
            damage()
            self.assertEqual(0, ra.main(["--root", str(self.tmp)]))
            d = json.loads(read(rp))
            self.assertEqual(len(self.census["routes"]), len(d["routes"]))
            self.assertEqual([], [r for r in d["routes"] if r["callers"]])
            self.assertNotIn("callers_scan", d, "a census refresh must never claim a frontend scan happened")

    def test_explore_edges_follow_their_files_when_indexes_shift(self):
        def path_edges(html):
            F, EG = ra.read_literal(html, "const F="), ra.read_literal(html, ",EG=")
            return {(F[int(k)][0], F[t][0], w) for k, v in EG.items() for t, w in v["o"]}
        before = path_edges(read(self.tmp / "explore.html"))
        template = next(f for f in self.census["files"] if f["path"].endswith(".py") and not f.get("binary"))
        new_file = copy.deepcopy(template)
        new_file["path"] = ".0000_brand_new_file.py"   # sorts before ".dockerignore", so every other file's index shifts by one
        self.census["files"].append(new_file)
        self.save_census()
        self.refresh()
        html = read(self.tmp / "explore.html")
        F = ra.read_literal(html, "const F=")
        self.assertEqual(".0000_brand_new_file.py", F[0][0])
        self.assertEqual(before, path_edges(html), "every edge must still connect the same two files")

    def test_crlf_pages_are_not_seen_as_stale_and_stay_crlf(self):
        """A Windows checkout (core.autocrlf) has CRLF files. In-sync pages must not look changed, and
        pages that do change must keep CRLF rather than silently becoming LF."""
        for rel in ("code.html", "infra.html", "data/index/vitals.json"):
            p = self.tmp / rel
            p.write_bytes(read(p).replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual({}, ra.refresh_all(self.tmp, self.census), "CRLF alone must not count as out of date")
        self.newer_census()
        changes = ra.refresh_all(self.tmp, self.census)
        for rel in ("code.html", "infra.html", "data/index/vitals.json"):
            raw = changes[self.tmp / rel].encode("utf-8")
            self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), f"{rel}: a bare LF was introduced")

    def test_stats_json_follows_the_census(self):
        """data/index/stats.json feeds the shell's sidebar counts and snapshot chip (content/nav.json count_from)."""
        self.newer_census()
        self.assertIn(self.tmp / "data" / "index" / "stats.json", self.refresh())
        stats = json.loads(read(self.tmp / "data" / "index" / "stats.json"))
        self.assertEqual({"commit", "files", "functions", "generated", "routes"}, set(stats))
        self.assertEqual("abc1234", stats["commit"])
        self.assertEqual("2099-01-02", stats["generated"])
        self.assertEqual(len(self.census["routes"]), stats["routes"])
        self.assertEqual(self.census["totals"]["functions"], stats["functions"])
        self.assertEqual(sum(1 for f in self.census["files"] if not f.get("binary")), stats["files"])

    def test_stats_json_is_created_when_missing_and_keeps_crlf(self):
        (self.tmp / "data" / "index" / "stats.json").unlink()
        self.assertEqual(0, ra.main(["--root", str(self.tmp)]))       # main() must create data/index itself
        sp = self.tmp / "data" / "index" / "stats.json"
        self.assertTrue(sp.exists())
        sp.write_bytes(read(sp).replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual({}, ra.refresh_all(self.tmp, self.census), "CRLF alone must not count as out of date")

    def test_summary_keeps_windows_line_endings(self):
        sp = self.tmp / "data" / "summary.md"
        sp.write_bytes(read(sp).replace("\n", "\r\n").encode("utf-8"))
        self.newer_census()
        self.refresh()
        raw = sp.read_bytes()
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"), "no bare LF may be introduced")
        self.assertIn(b"commit abc1234.", raw)


class CensusValidation(unittest.TestCase):
    def test_the_repo_census_is_trustworthy(self):
        c = json.loads(read(ROOT / "data" / "census.json"))
        self.assertEqual([], [p for p in ra.census_problems(c) if "uncommitted" not in p])

    def test_a_degraded_census_is_flagged(self):
        bad = {"meta": {"js_parser": "heuristic-fallback"}, "docker_compose": [{"name": "backend_data"}],
               "ci": {"x.yml": {"jobs": [{"id": "test"}]}}, "git": {"dirty_files": 3}}
        problems = ra.census_problems(bad)
        self.assertEqual(3, len(problems))
        self.assertTrue(any("tree-sitter" in p for p in problems))
        self.assertTrue(any("pyyaml" in p for p in problems))
        self.assertTrue(any("uncommitted" in p for p in problems))

    # ---- P10: census script_version 1 and 2
    def good_v2(self):
        c = json.loads(read(ROOT / "data" / "census.json"))
        c["meta"]["script_version"] = 2
        c["git"]["head_full"] = "a" * 40
        for f in c["files"]:
            seen = {}
            # the v2 key rule: later definitions of the same qual become qual~2, qual~3 ... in source order
            for x in sorted(ra.G(f, "functions") + ra.G(f, "classes"), key=lambda s: s.get("start", 0)):
                q = x.get("qual") or x["name"]
                seen[q] = seen.get(q, 0) + 1
                x["qual"] = q if seen[q] == 1 else f"{q}~{seen[q]}"
                x["hash"] = "0123456789"
        return c

    def test_a_v1_census_is_accepted(self):
        c = json.loads(read(ROOT / "data" / "census.json"))
        c["meta"]["script_version"] = 1
        self.assertEqual([], [p for p in ra.census_problems(c) if "uncommitted" not in p])
        del c["meta"]["script_version"]                      # the oldest censuses did not say
        self.assertEqual([], [p for p in ra.census_problems(c) if "uncommitted" not in p])

    def test_a_good_v2_census_is_accepted(self):
        self.assertEqual([], [p for p in ra.census_problems(self.good_v2()) if "uncommitted" not in p])

    def test_a_v2_census_needs_the_full_commit_id(self):
        c = self.good_v2()
        c["git"]["head_full"] = c["git"]["head"]
        self.assertTrue(any("head_full" in p for p in ra.census_problems(c)))
        del c["git"]["head_full"]
        self.assertTrue(any("head_full" in p for p in ra.census_problems(c)))

    def test_a_v2_census_needs_unique_keys_and_a_hash_on_every_symbol(self):
        c = self.good_v2()
        f = next(f for f in c["files"] if len(ra.G(f, "functions")) >= 2)
        f["functions"][1]["qual"] = f["functions"][0]["qual"]
        f["functions"][0].pop("hash")
        problems = ra.census_problems(c)
        self.assertTrue(any("not unique" in p and f["path"] in p for p in problems), problems)
        self.assertTrue(any("no hash" in p for p in problems), problems)

    def test_an_unknown_script_version_is_refused(self):
        c = self.good_v2()
        c["meta"]["script_version"] = 3
        problems = ra.census_problems(c)
        self.assertEqual(1, len([p for p in problems if "script_version 3" in p]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
