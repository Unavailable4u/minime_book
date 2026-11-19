#!/usr/bin/env python3
"""
Tests for scripts/refresh_graph.py. Standard library only.

    python scripts/test_refresh_graph.py

Everything runs on a temporary copy of the pages with a small invented graph and an
invented frontend, so no MiniMe checkout or graphify run is needed.
"""
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("refresh_graph", ROOT / "scripts" / "refresh_graph.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)
ra = rg.ra

PAGES = ["graph.html", "explore.html", "graph-viewer.html", "data/summary.md", "data/index/vitals.json"]
COMMIT = "a" * 40


def read(p):
    return Path(p).read_text(encoding="utf-8")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book, self.minime = self.tmp / "book", self.tmp / "MiniMe"
        (self.book / "data" / "index").mkdir(parents=True)
        (self.book / "data" / "code").mkdir(parents=True)
        for rel in PAGES:
            shutil.copy(ROOT / rel, self.book / rel)
        (self.minime / "graphify-out").mkdir(parents=True)
        files = [r[0] for r in ra.read_literal(read(self.book / "explore.html"), "const F=")]
        self.eo = next(f for f in files if f.startswith("backend/eo/"))
        self.ag = next(f for f in files if f.startswith("backend/agents/") and not f.startswith("backend/agents/test_"))
        self.write_graph()
        self.write_frontend()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_graph(self):
        node = lambda i, label, f, c: {"id": i, "label": label, "source_file": f, "community": c, "file_type": "code" if f else "concept"}
        nodes = [node("e1", "eo_fn()", self.eo, 0), node("e2", "eo_other()", self.eo, 0), node("a1", "ag_fn()", self.ag, 0),
                 node("j", "json", "", 1), node("t1", "test_it()", "backend/tests/test_x.py", 1)]
        links = [("a1", "e1"), ("a1", "e2"), ("a1", "j"), ("t1", "a1"), ("e1", "j")]
        d = {"directed": False, "nodes": nodes, "links": [{"source": s, "target": t} for s, t in links], "built_at_commit": COMMIT}
        (self.minime / "graphify-out" / "graph.json").write_text(json.dumps(d), encoding="utf-8")

    def write_frontend(self):
        fe = self.minime / "frontend" / "app"
        (fe / "lib").mkdir(parents=True)
        (fe / "lib" / "files.js").write_text(
            "const base = `${apiUrl}/api/workspaces/${workspaceId}/code`;\n"
            "fetch(`${base}/files`); fetch(`${base}/files/${path}/history`);\n"
            "fetch(`/api/devices/${encodeURIComponent(target.id)}/revoke`);\n", encoding="utf-8")
        (fe / "lib" / "files.test.js").write_text("fetch('/api/devices')", encoding="utf-8")

    def graph(self):
        return rg.Graph(self.minime / "graphify-out" / "graph.json", repo_prefix=str(self.minime))

    def apply(self):
        for p, data in rg.refresh_all(self.book, self.graph(), self.minime).items():
            p.parent.mkdir(parents=True, exist_ok=True)         # like main(): data/graph/ does not exist before the first run
            p.write_bytes(data)


class FoldersJson(Fixture):
    """data/graph/folders.json (P08): folder-to-folder link counts at the finer level the topology diagram needs."""
    REL = "data/graph/folders.json"

    def test_the_diagram_folder_is_one_level_finer_where_the_diagram_needs_it(self):
        cases = {
            "m2c/src/m2c/tui/app.py": "m2c/src/m2c/tui", "m2c/src/m2c/policy/sub/deep.py": "m2c/src/m2c/policy",
            "m2c/src/m2c/cli.py": "m2c/src/m2c", "m2c/tests/test_cli.py": "m2c/tests",
            "frontend/app/components/Chat.jsx": "frontend/app/components", "frontend/app/lib/preview/x.js": "frontend/app/lib",
            "frontend/app/page.js": "frontend/app", "frontend/package.json": "frontend",
            "protocol/v1/hello.json": "protocol/v1", "protocol/validate.py": "protocol",
            "daemon/tools.py": "daemon", "backend/eo/a.py": "backend/eo", "backend/api/routes/x.py": "backend/api",
            "README.md": "",
        }
        self.assertEqual(cases, {p: rg.topo_folder(p) for p in cases})

    def test_refresh_writes_the_pairs_and_node_counts_of_the_graph_with_tests_and_concepts_left_out(self):
        self.apply()
        doc = json.loads(read(self.book / self.REL))
        self.assertEqual(["version", "source", "commit", "date", "nodes", "pairs"], list(doc))
        self.assertEqual((1, "graphify", COMMIT[:7]), (doc["version"], doc["source"], doc["commit"]))
        self.assertEqual([["backend/agents", "backend/eo", 2]], doc["pairs"], "a1 to e1 and e2 count; the concept node and the test file do not")
        self.assertEqual({"backend/agents": 1, "backend/eo": 2}, doc["nodes"])

    def test_the_file_has_one_pair_per_line_busiest_first_and_ends_with_a_newline(self):
        self.apply()
        raw = read(self.book / self.REL)
        self.assertTrue(raw.endswith("}\n"))
        self.assertNotIn("\r", raw)
        self.assertEqual(1, len([ln for ln in raw.splitlines() if ln.startswith('    ["')]))
        self.assertEqual(raw, rg.folders_json(self.graph()))

    def test_pairs_are_sorted_by_count_then_name_and_survive_an_empty_graph(self):
        pairs = json.loads(rg.folders_json(self.finer_graph()))["pairs"]
        self.assertEqual(sorted(pairs, key=lambda r: (-r[2], r[0], r[1])), pairs)
        self.assertEqual([["m2c/src/m2c/tui", "m2c/src/m2c/link", 2], ["frontend/app/components", "frontend/app/lib", 1], ["m2c/src/m2c/link", "protocol/v1", 1]], pairs)
        empty = self.finer_graph(links=[])
        self.assertEqual([], json.loads(rg.folders_json(empty))["pairs"])
        self.assertIn('"pairs": []', rg.folders_json(empty))

    def test_the_parts_of_m2c_and_the_frontend_are_told_apart_not_lumped_into_their_top_folder(self):
        pairs = {(a, b) for a, b, _ in json.loads(rg.folders_json(self.finer_graph()))["pairs"]}
        self.assertIn(("m2c/src/m2c/tui", "m2c/src/m2c/link"), pairs)
        self.assertIn(("frontend/app/components", "frontend/app/lib"), pairs)
        self.assertNotIn(("m2c/src", "m2c/src"), pairs)

    def test_a_link_inside_one_folder_is_not_a_pair(self):
        doc = json.loads(rg.folders_json(self.finer_graph(links=[("t1", "t2")])))
        self.assertEqual([], doc["pairs"], "t1 and t2 are both in m2c/src/m2c/tui")

    def test_the_seed_file_is_replaced_by_the_real_numbers_and_a_second_run_changes_nothing(self):
        # The seed is built here, not copied from the repo: after the first update_all.py run the repo's own file is the real
        # graph (source "graphify"), and this test must not depend on which of the two the checkout happens to hold.
        (self.book / "data" / "graph").mkdir(parents=True)
        seed = {"version": 1, "source": "seed", "commit": "94af156", "date": "2026-11-15", "nodes": {}, "pairs": [["backend/api", "backend/eo", 526]]}
        (self.book / self.REL).write_text(json.dumps(seed, indent=2) + "\n", encoding="utf-8")
        self.assertEqual("seed", json.loads(read(self.book / self.REL))["source"])
        self.apply()
        self.assertEqual("graphify", json.loads(read(self.book / self.REL))["source"])
        first = (self.book / self.REL).read_bytes()
        self.apply()
        self.assertEqual(first, (self.book / self.REL).read_bytes())

    def test_a_refresh_does_not_touch_the_layout_or_the_numbers_of_the_census(self):
        (self.book / "content").mkdir(parents=True)
        shutil.copy(ROOT / "content" / "topology.json", self.book / "content" / "topology.json")
        before = (self.book / "content" / "topology.json").read_bytes()
        vit = json.loads(read(self.book / "data" / "index" / "vitals.json"))["census"]
        self.apply()
        self.assertEqual(before, (self.book / "content" / "topology.json").read_bytes(), "the layout is curated by hand")
        self.assertEqual(vit, json.loads(read(self.book / "data" / "index" / "vitals.json"))["census"], "census.topology belongs to refresh_atlas.py")

    def finer_graph(self, links=None):
        node = lambda i, f: {"id": i, "label": i + "()", "source_file": f, "community": 0, "file_type": "code"}
        nodes = [node("t1", "m2c/src/m2c/tui/a.py"), node("t2", "m2c/src/m2c/tui/b.py"), node("l1", "m2c/src/m2c/link/c.py"),
                 node("c1", "frontend/app/components/X.jsx"), node("b1", "frontend/app/lib/y.js"), node("p1", "protocol/v1/hello.json")]
        links = [("t1", "l1"), ("t2", "l1"), ("c1", "b1"), ("l1", "p1")] if links is None else links
        path = self.tmp / "finer.json"
        path.write_text(json.dumps({"directed": False, "nodes": nodes, "links": [{"source": s, "target": t} for s, t in links], "built_at_commit": COMMIT}), encoding="utf-8")
        return rg.Graph(path, repo_prefix=str(self.minime))


class FileLinksJson(Fixture):
    """data/graph/file-links.json (P13): the strongest file-to-file graph links of each file, for the Explorer."""
    REL = "data/graph/file-links.json"

    def doc(self, g=None):
        return json.loads(rg.file_links_json(g or self.graph()))

    def pairs(self, doc):
        """{(path, other path): count} read back from the compact index form."""
        return {(doc["paths"][i], doc["paths"][j]): n for i, row in enumerate(doc["links"]) for j, n in row}

    def test_links_are_file_pairs_counted_in_both_directions_with_concepts_and_self_links_left_out(self):
        doc = self.doc()
        test = "backend/tests/test_x.py"
        self.assertEqual(["version", "source", "commit", "date", "top", "paths", "links"], list(doc))
        self.assertEqual((1, "graphify", COMMIT[:7], rg.FILELINKS_TOP), (doc["version"], doc["source"], doc["commit"], doc["top"]))
        self.assertEqual(sorted([self.ag, self.eo, test]), doc["paths"])
        want = {(self.ag, self.eo): 2, (self.eo, self.ag): 2, (self.ag, test): 1, (test, self.ag): 1}
        self.assertEqual(want, self.pairs(doc), "a1-e1 and a1-e2 make 2; the concept node 'json' and the two links inside one file make none; tests stay in")

    def test_every_path_has_one_line_of_links_and_the_strongest_neighbour_comes_first(self):
        doc = self.doc()
        self.assertEqual(len(doc["paths"]), len(doc["links"]))
        row = doc["links"][doc["paths"].index(self.ag)]
        self.assertEqual([[doc["paths"].index(self.eo), 2], [doc["paths"].index("backend/tests/test_x.py"), 1]], row)

    def test_only_the_strongest_neighbours_are_kept_and_ties_are_broken_by_path(self):
        node = lambda i, f: {"id": i, "label": i + "()", "source_file": f, "community": 0, "file_type": "code"}
        hub = "backend/eo/hub.py"
        names = [f"backend/eo/f{i:02d}.py" for i in range(rg.FILELINKS_TOP + 3)]
        nodes = [node("h", hub)] + [node(f"n{i}", n) for i, n in enumerate(names)]
        links = [("h", f"n{i}") for i in range(len(names))] + [("h", "n0")]            # n0 has two links to the hub: it wins, the rest tie
        path = self.tmp / "wide.json"
        path.write_text(json.dumps({"directed": False, "nodes": nodes, "links": [{"source": s, "target": t} for s, t in links], "built_at_commit": COMMIT}), encoding="utf-8")
        doc = self.doc(rg.Graph(path, repo_prefix=str(self.minime)))
        row = doc["links"][doc["paths"].index(hub)]
        got = [doc["paths"][j] for j, _ in row]
        self.assertEqual(rg.FILELINKS_TOP, len(row))
        self.assertEqual(names[0], got[0])
        self.assertEqual(names[1:rg.FILELINKS_TOP], got[1:], "equal counts are ordered by path")
        self.assertEqual(2, row[0][1])

    def test_the_file_has_one_path_and_one_row_per_line_and_ends_with_a_newline(self):
        self.apply()
        raw = read(self.book / self.REL)
        self.assertTrue(raw.endswith("}\n"))
        self.assertNotIn("\r", raw)
        self.assertEqual(3, len([ln for ln in raw.splitlines() if ln.startswith('    "')]))
        self.assertEqual(3, len([ln for ln in raw.splitlines() if ln.startswith("    [[")]))
        self.assertEqual(raw, rg.file_links_json(self.graph()))

    def test_a_graph_without_file_links_gives_empty_lists_and_a_second_run_changes_nothing(self):
        node = {"id": "a", "label": "a()", "source_file": self.eo, "community": 0, "file_type": "code"}
        path = self.tmp / "one.json"
        path.write_text(json.dumps({"directed": False, "nodes": [node], "links": [], "built_at_commit": COMMIT}), encoding="utf-8")
        doc = self.doc(rg.Graph(path, repo_prefix=str(self.minime)))
        self.assertEqual(([], []), (doc["paths"], doc["links"]))
        self.apply()
        first = (self.book / self.REL).read_bytes()
        self.apply()
        self.assertEqual(first, (self.book / self.REL).read_bytes())


class Refresh(Fixture):
    def test_refresh_is_idempotent(self):
        self.apply()
        self.assertEqual({}, rg.refresh_all(self.book, self.graph(), self.minime))

    def test_vitals_graph_half_counts_and_hubs_ignore_concept_nodes(self):
        self.apply()
        g = json.loads(read(self.book / "data" / "index" / "vitals.json"))["graph"]
        self.assertEqual({"commit": "aaaaaaa", "date": self.graph().date, "nodes": 5, "links": 5, "communities": 2}, {k: g[k] for k in g if k != "hubs"})
        self.assertNotIn("json", [h["label"] for h in g["hubs"]])          # concept nodes have no file
        top = g["hubs"][0]
        self.assertEqual({"label": "ag_fn()", "path": self.ag, "links": 4}, top)
        self.assertTrue(all({"label", "path", "links"} == set(h) for h in g["hubs"]))
        self.assertEqual(sorted((h["links"] for h in g["hubs"]), reverse=True), [h["links"] for h in g["hubs"]])

    def test_the_census_half_of_vitals_is_carried_over_untouched(self):
        vp = self.book / "data" / "index" / "vitals.json"
        before = json.loads(read(vp))["census"]
        self.apply()
        self.assertEqual(before, json.loads(read(vp))["census"])

    def test_vitals_are_created_when_missing_and_hold_only_the_graph_then(self):
        vp = self.book / "data" / "index" / "vitals.json"
        vp.unlink()
        self.apply()
        self.assertEqual({"graph"}, set(json.loads(read(vp))))

    def test_index_html_is_not_touched_by_the_graph_refresh(self):
        self.assertNotIn(self.book / "index.html", rg.refresh_all(self.book, self.graph(), self.minime))

    def test_graph_page_matrix_pairs_and_communities(self):
        self.apply()
        html = read(self.book / "graph.html")
        self.assertIn("5 nodes and 5 links from Graphify", html)
        self.assertIn("backend/agents -&gt; backend/eo: 2 links", html)       # a1 -> e1, a1 -> e2
        self.assertRegex(html, r'title="backend/agents → backend/eo">backend/agents → backend/eo</span><i style="width:55.0%"></i><em>2</em>')
        self.assertIn("Largest 2 of 2.", html)
        self.assertIn(f"Built {self.graph().date} from commit aaaaaaa.", html)

    def test_explore_edges_are_file_to_file_link_counts(self):
        self.apply()
        html = read(self.book / "explore.html")
        paths = [r[0] for r in ra.read_literal(html, "const F=")]
        eg = ra.read_literal(html, ",EG=")
        ag, eo = paths.index(self.ag), paths.index(self.eo)
        self.assertEqual([[eo, 2]], eg[str(ag)]["o"])
        self.assertEqual([[ag, 2]], eg[str(eo)]["i"])

    def test_summary_line(self):
        self.apply()
        self.assertRegex(read(self.book / "data" / "summary.md"), r"- Graph: 5 nodes, 5 links, 2 communities \(Graphify run of [\d-]+, commit `aaaaaaa`\)\.")


class Viewer(Fixture):
    def data(self):
        self.apply()
        html = read(self.book / "graph-viewer.html")
        return html, ra.read_literal(html, "const D = ")

    def test_viewer_is_a_complete_page_with_the_graph_embedded(self):
        html, d = self.data()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("__DATA__", html)
        self.assertNotIn("RAW_NODES", html)                      # no longer Graphify's viewer
        self.assertEqual({"date": self.graph().date, "commit": "aaaaaaa"}, d["meta"])
        explore = read(self.book / "explore.html")
        self.assertEqual(len(ra.read_literal(explore, "const F=")), len(d["files"]))
        self.assertEqual(len(ra.read_literal(explore, ",FN=")), len(d["fns"]))

    def test_links_are_counted_from_the_graph_without_the_explore_cap(self):
        _, d = self.data()
        paths = [f[0] for f in d["files"]]
        ag, eo = paths.index(self.ag), paths.index(self.eo)
        self.assertIn([ag, eo, 2], d["edges"])                  # a1 -> e1 and a1 -> e2
        self.assertTrue(all(a != b for a, b, _ in d["edges"]))  # nothing links a file to itself
        self.assertEqual(1, sum(1 for a, b, _ in d["edges"] if (a, b) == (ag, eo)))

    def test_every_file_belongs_to_a_named_folder(self):
        _, d = self.data()
        self.assertTrue(all(0 <= f[7] < len(d["groups"]) for f in d["files"]))
        self.assertEqual("backend/tests", d["groups"][0])      # biggest folder first
        self.assertEqual("root", rg.viewer_group(".gitignore"))
        self.assertEqual("root", rg.viewer_group("README.md"))
        self.assertEqual("daemon", rg.viewer_group("daemon/main.py"))
        self.assertEqual("frontend/app", rg.viewer_group("frontend/app/x/y.jsx"))

    def test_graph_page_describes_the_new_viewer_once(self):
        self.apply()
        html = read(self.book / "graph.html")
        self.assertIn("as a constellation", html)
        self.assertNotIn("Your Graphify view, as generated.", html)
        self.assertEqual(1, html.count('<iframe src="graph-viewer.html"'))

    def test_a_template_without_the_data_placeholder_is_refused(self):
        bad = self.tmp / "bad.html"
        bad.write_text("<html></html>", encoding="utf-8")
        with self.assertRaises(ValueError):
            rg.viewer_html({}, template=bad)

    def test_text_that_could_close_the_script_tag_is_escaped(self):
        tpl = self.tmp / "t.html"
        tpl.write_text("<script>const D = __DATA__;</script>", encoding="utf-8")
        out = rg.viewer_html({"x": "</script><b>"}, template=tpl)
        self.assertEqual(1, out.count("</script>"))
        self.assertEqual({"x": "</script><b>"}, ra.read_literal(out, "const D = "))


class ApiCallers(Fixture):
    def callers(self):
        routes = [("GET", "/api/workspaces/{ws_id}/code/files"), ("GET", "/api/workspaces/{ws_id}/code/files/{file_path:path}/history"),
                  ("POST", "/api/devices/{device_id}/revoke"), ("GET", "/api/devices"), ("GET", "/api/devices/{device_id}")]
        return rg.scan_callers(self.minime / "frontend", routes)

    def calls(self, routes):
        return rg.scan_api_calls(self.minime / "frontend", routes)[0]

    def test_alias_path_param_and_nested_parentheses_are_matched(self):
        counts, per_file = self.callers()
        self.assertEqual(1, counts[("GET", "/api/workspaces/{ws_id}/code/files")])
        self.assertEqual(1, counts[("GET", "/api/workspaces/{ws_id}/code/files/{file_path:path}/history")])
        self.assertEqual(1, counts[("POST", "/api/devices/{device_id}/revoke")])
        self.assertEqual({"app/lib/files.js": 3}, per_file)

    def test_test_files_do_not_count_as_callers(self):
        counts, _ = self.callers()
        self.assertEqual(0, counts[("GET", "/api/devices")])

    def test_exact_path_beats_a_param_route_of_the_same_shape(self):
        (self.minime / "frontend" / "app" / "lib" / "x.js").write_text("fetch('/api/devices')", encoding="utf-8")
        counts, _ = self.callers()
        self.assertEqual(1, counts[("GET", "/api/devices")])


    # ------------------------------------------------------------- P17: how well each link is backed (`via`) and routes.json
    def test_via_says_method_when_the_code_names_the_route_method_and_shape_when_only_the_path_fits(self):
        (self.minime / "frontend" / "app" / "lib" / "dev.js").write_text(
            "export const revoke = (id) => fetch(`/api/devices/${id}/revoke`, {\n  method: \"POST\",\n});\n", encoding="utf-8")
        post, get = ("POST", "/api/devices/{device_id}/revoke"), ("GET", "/api/devices/{device_id}/revoke")
        calls = self.calls([post, get])
        self.assertEqual(["method"], calls[post]["app/lib/dev.js"])
        self.assertEqual(["shape"], calls[get]["app/lib/dev.js"], "same path shape, but the code says POST: a weaker link, kept and labelled, not dropped")

    def test_via_says_score_when_the_best_path_matches_and_no_method_is_named(self):
        (self.minime / "frontend" / "app" / "lib" / "dev.js").write_text("export const list = () => fetch('/api/devices');\n", encoding="utf-8")
        route = ("GET", "/api/devices")
        self.assertEqual(["score"], self.calls([route, ("GET", "/api/devices/{device_id}")])[route]["app/lib/dev.js"])

    def test_a_helper_named_apiPost_names_the_method(self):
        (self.minime / "frontend" / "app" / "lib" / "h.js").write_text("apiPost('/api/devices/revoke-all', {});\n", encoding="utf-8")
        post = ("POST", "/api/devices/revoke-all")
        self.assertEqual(["method"], self.calls([post, ("GET", "/api/devices/revoke-all")])[post]["app/lib/h.js"])

    def test_a_comment_line_is_not_evidence_for_a_method_but_the_link_itself_is_still_found(self):
        (self.minime / "frontend" / "app" / "lib" / "c.js").write_text("// POST /api/devices/revoke-all is used below\nconst u = '/api/devices/revoke-all';\n", encoding="utf-8")
        post = ("POST", "/api/devices/revoke-all")
        self.assertEqual(["score"], self.calls([post])[post]["app/lib/c.js"])

    def test_the_pair_set_is_the_same_with_or_without_the_second_opinion(self):
        routes = [("GET", "/api/workspaces/{ws_id}/code/files"), ("GET", "/api/workspaces/{ws_id}/code/files/{file_path:path}/history"),
                  ("POST", "/api/devices/{device_id}/revoke"), ("GET", "/api/devices"), ("GET", "/api/devices/{device_id}")]
        calls = self.calls(routes)
        counts, per_file = self.callers()
        self.assertEqual({r: len(calls[r]) for r in routes}, {r: counts[r] for r in routes})
        self.assertEqual(sum(per_file.values()), sum(len(v) for v in calls.values()))

    def test_refresh_writes_the_callers_half_of_routes_json_and_keeps_the_census_half(self):
        census = {"meta": {"generated": "2026-11-19T00:00:00"}, "git": {"head": "aaaaaaa"},
                  "routes": [{"method": "POST", "path": "/api/devices/{device_id}/revoke", "handler": "revoke", "file": "backend/api/routes/devices.py", "line": 10,
                              "end": 20, "async": True, "deps": ["get_user"], "response_model": None, "router_prefix": ""},
                             {"method": "GET", "path": "/api/nobody-calls-this", "handler": "n", "file": "backend/api/routes/n.py", "line": 1, "end": 2, "deps": []}]}
        (self.book / "data" / "census.json").write_text(json.dumps(census), encoding="utf-8")
        (self.minime / "frontend" / "app" / "lib" / "dev.js").write_text("fetch(`/api/devices/${id}/revoke`, { method: 'POST' });\n", encoding="utf-8")
        self.apply()
        doc = json.loads(read(self.book / ra.ROUTES_REL))
        by = {r["path"]: r for r in doc["routes"]}
        self.assertEqual([{"file": "frontend/app/lib/dev.js", "via": ["method"]}, {"file": "frontend/app/lib/files.js", "via": ["score"]}],
                         by["/api/devices/{device_id}/revoke"]["callers"], "one file names POST, the other names no method")
        self.assertEqual([], by["/api/nobody-calls-this"]["callers"])
        self.assertEqual("revoke", by["/api/devices/{device_id}/revoke"]["handler"], "the census half is built from the census")
        self.assertEqual(rg.git_head(self.minime) or self.graph().commit, doc["callers_scan"]["commit"])
        self.assertEqual(2, doc["callers_scan"]["frontend_files"], "files.js and dev.js; files.test.js is not scanned")
        self.assertEqual(2, doc["callers_scan"]["pairs"])
        self.assertEqual({}, rg.refresh_all(self.book, self.graph(), self.minime), "a second run changes nothing")


class Freshness(Fixture):
    def test_matching_commits_pass_and_mismatches_are_reported(self):
        census = {"git": {"head": "aaaaaaa"}}
        g = self.graph()
        self.assertEqual([], [p for p in rg.freshness_problems(g, census, self.tmp / "nowhere") if "census" in p])
        self.assertEqual(1, len(rg.freshness_problems(g, {"git": {"head": "bbbbbbb"}}, self.tmp / "nowhere")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
