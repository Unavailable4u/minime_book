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

PAGES = ["index.html", "graph.html", "explore.html", "api.html", "graph-viewer.html", "data/summary.md"]
COMMIT = "a" * 40


def read(p):
    return Path(p).read_text(encoding="utf-8")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.book, self.minime = self.tmp / "book", self.tmp / "MiniMe"
        (self.book / "data").mkdir(parents=True)
        for rel in PAGES:
            shutil.copy(ROOT / rel, self.book / rel)
        (self.minime / "graphify-out").mkdir(parents=True)
        (self.minime / "graphify-out" / "graph.html").write_text("<script>const RAW_NODES = []</script>", encoding="utf-8")
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
            p.write_bytes(data)


class Refresh(Fixture):
    def test_refresh_is_idempotent(self):
        self.apply()
        self.assertEqual({}, rg.refresh_all(self.book, self.graph(), self.minime))

    def test_index_counts_and_hubs_ignore_concept_nodes(self):
        self.apply()
        html = read(self.book / "index.html")
        self.assertIn('<div class="k">5</div><div class="l">graph nodes</div>', html)
        self.assertIn('<div class="k">5</div><div class="l">graph links</div>', html)
        hubs = ra.find_card(html, "Graph hubs")
        text = html[hubs[0]:hubs[1]]
        self.assertNotIn(">json  ", text)                        # concept nodes have no file
        self.assertRegex(text, r"ag_fn\(\)  [^<]+</span><i[^>]*></i><em>4</em>")

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

    def test_summary_line_and_viewer_copy(self):
        self.apply()
        self.assertRegex(read(self.book / "data" / "summary.md"), r"- Graph: 5 nodes, 5 links, 2 communities \(Graphify run of [\d-]+, commit `aaaaaaa`\)\.")
        self.assertEqual(read(self.minime / "graphify-out" / "graph.html"), read(self.book / "graph-viewer.html"))

    def test_a_file_that_is_not_a_graphify_viewer_is_refused(self):
        (self.minime / "graphify-out" / "graph.html").write_text("<html>nothing</html>", encoding="utf-8")
        with self.assertRaises(ValueError):
            rg.refresh_all(self.book, self.graph(), self.minime)


class ApiCallers(Fixture):
    def callers(self):
        routes = [("GET", "/api/workspaces/{ws_id}/code/files"), ("GET", "/api/workspaces/{ws_id}/code/files/{file_path:path}/history"),
                  ("POST", "/api/devices/{device_id}/revoke"), ("GET", "/api/devices"), ("GET", "/api/devices/{device_id}")]
        return rg.scan_callers(self.minime / "frontend", routes)

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


class Freshness(Fixture):
    def test_matching_commits_pass_and_mismatches_are_reported(self):
        census = {"git": {"head": "aaaaaaa"}}
        g = self.graph()
        self.assertEqual([], [p for p in rg.freshness_problems(g, census, self.tmp / "nowhere") if "census" in p])
        self.assertEqual(1, len(rg.freshness_problems(g, {"git": {"head": "bbbbbbb"}}, self.tmp / "nowhere")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
