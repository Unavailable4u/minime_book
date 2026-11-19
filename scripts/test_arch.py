#!/usr/bin/env python3
"""
Tests for scripts/arch.py and scripts/arch_extract.py (patch P25). Standard library only.

    python scripts/test_arch.py
    python -m unittest discover -s scripts

Most tests build a miniature census and topology in memory. The git tests make a throw-away repository in a temp folder
(skipped when git is not installed). Two tests check the repo itself: the committed registry is valid, and the committed
architecture data is exactly what `arch.py build` would write.
"""
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


arch_extract = _load("arch_extract")
arch = _load("arch")

C1, C2 = "a" * 40, "b" * 40
H = lambda c: c * 10


def sym(qual, start, end, h):
    return {"name": qual.split(".")[-1], "qual": qual, "kind": "function", "start": start, "end": end, "loc": end - start + 1,
            "hash": h, "calls": [], "test": False}


def rec(path, funcs=(), **extra):
    return {"path": path, "lang": "python", "lines": 100, "code": 80, "test": False, "binary": False,
            "functions": list(funcs), "classes": [], **extra}


def census(files, commit=C1):
    return {"meta": {"script_version": 2}, "git": {"head": commit[:7], "head_full": commit}, "files": list(files),
            "env_usage": {"DATABASE_URL": ["backend/eo/x.py"], "UPSTASH_REDIS_REST_URL": ["backend/eo/x.py", "m2c/src/m2c/y.py"]},
            "table_refs": {"chats": ["backend/api/a.py", "m2c/src/m2c/y.py"]}}


FILES = [
    rec("backend/api/a.py", [sym("post_task", 10, 30, H("1"))]),
    rec("backend/eo/x.py", [sym("run", 5, 50, H("2")), sym("step", 60, 80, H("3"))]),
    rec("backend/eo/test_x.py", [], test=True),
    rec("m2c/src/m2c/y.py", [sym("go", 1, 9, H("4"))]),
    rec("m2c/src/m2c/sandbox/z.py", [sym("jail", 1, 9, H("5"))]),
    rec("protocol/v.py", [sym("check", 1, 9, H("6"))]),
]
TOPO = {
    "view": {"w": 1000, "h": 600},
    "groups": [{"id": "server", "label": "Server", "x": 0, "y": 0, "w": 500, "h": 500},
               {"id": "devices", "label": "Devices", "x": 500, "y": 0, "w": 500, "h": 500},
               {"id": "contract", "label": "Contract", "x": 0, "y": 500, "w": 1000, "h": 100}],
    "nodes": [
        {"id": "api", "label": "API", "group": "server", "x": 10, "y": 10, "folders": ["backend/api"], "what": "HTTP"},
        {"id": "eo", "label": "Orchestrator", "group": "server", "x": 10, "y": 100, "folders": ["backend/eo"]},
        {"id": "m2c", "label": "M2C", "group": "devices", "x": 510, "y": 10, "folders": ["m2c/src/m2c"]},
        {"id": "m2c-core", "label": "M2C core", "group": "devices", "folders": ["m2c/src/m2c"]},
        {"id": "m2c-sandbox", "label": "Sandbox", "group": "devices", "parent": "m2c", "folders": ["m2c/src/m2c/sandbox"]},
        {"id": "protocol", "label": "Protocol", "group": "contract", "x": 10, "y": 510, "folders": ["protocol"]},
    ],
    "edges": [{"from": "eo", "to": "m2c", "label": "only after approval", "declared": True, "gate": True}],
}
LAYOUT = {
    "virtual": [{"id": "store:postgres", "label": "Postgres", "kind": "store", "group": "group:server", "source": "migrations",
                 "edges_from": {"tables": True, "env": ["DATABASE_URL"]}},
                {"id": "store:redis", "label": "Redis", "kind": "store", "group": "group:server", "source": "env",
                 "edges_from": {"env": ["UPSTASH_REDIS_REST_URL"]}}],
    "pins": {"backend/api": {"x": 99, "y": 98}, "nowhere": {"x": 1, "y": 1}},
}
INPUTS = {
    "imports": {"imports": {"backend/api/a.py": [["backend/eo/x.py", 3]], "backend/eo/x.py": [["protocol/v.py", 4], ["backend/eo/test_x.py", 5]]}},
    "routes": {"routes": [{"file": "backend/api/a.py", "method": "POST", "path": "/api/tasks", "handler": "post_task", "line": 10,
                           "router": "router", "include_prefix": "", "response_model": None,
                           "callers": [{"file": "m2c/src/m2c/y.py", "line": 3}]}]},
    "agents": {"modules": [], "roles": [], "providers": []},
    "folders": {"pairs": [["backend/api", "backend/eo", 7]]},
}


def make_ctx(files=FILES, commit=C1):
    ctx = arch.Ctx(commit=commit)
    ctx.files = {f["path"]: f for f in files}
    ctx.symbols = {p: arch.notes.symbol_table(f) for p, f in ctx.files.items()}
    return ctx


def derive(extractions=()):
    ctx = make_ctx()
    return arch.derive(ctx, TOPO, LAYOUT, copy.deepcopy(INPUTS) | {"census_extra": {k: census(FILES)[k] for k in ("env_usage", "table_refs")}}, list(extractions))


def ev(path, qual="post_task", lines=(10, 30), h=None):
    return {"path": path, "qual": qual, "lines": list(lines), "hash": h}


def step(i, title="Do it", actor="backend/api", nxt=(), evidence=None, **extra):
    return {"id": i, "title": title, "actor": actor, "kind": "control", "text": "It does a thing.", "gate": None, "next": list(nxt),
            "evidence": evidence if evidence is not None else [ev("backend/api/a.py")], "confidence": "high", **extra}


def flow(**over):
    f = {"schema": 1, "flow": "task-pipeline", "title": "Task pipeline", "kind": "pipeline", "summary": "How a task runs.", "commit": C1,
         "actors": ["backend/api", "backend/eo"],
         "steps": [step("s01", nxt=["s02"]), step("s02", "Run", "backend/eo", evidence=[ev("backend/eo/x.py", "run", (5, 50))])]}
    f.update(over)
    return f


class ExtractTests(unittest.TestCase):
    def run_one(self, kind, src, name="X", **extra):
        return arch_extract.extract_one(dict({"id": "t", "file": "f.py", "kind": kind, "name": name}, **extra), src)

    def test_dict_keys_in_source_order(self):
        r = self.run_one("dict-keys", 'X = {"b": 1, "a": 2}\n')
        self.assertTrue(r["found"])
        self.assertEqual(r["items"], ["b", "a"])

    def test_dict_map(self):
        self.assertEqual(self.run_one("dict-map", 'X = {"a": "x", "b": "y"}\n')["items"], [["a", "x"], ["b", "y"]])

    def test_list_and_tuple(self):
        self.assertEqual(self.run_one("list", 'X = ["a", "b"]\n')["items"], ["a", "b"])
        self.assertEqual(self.run_one("list", 'X = ("a",)\n')["items"], ["a"])

    def test_annotated_assignment(self):
        self.assertEqual(self.run_one("list", 'X: list[str] = ["a"]\n')["items"], ["a"])

    def test_nested_with_integer_keys_skips_keys_without_the_field(self):
        r = self.run_one("nested", 'X = {0: {"agents": ["a", "b"]}, 1: {"other": 1}, 2: {"agents": ["c"]}}\n', field="agents")
        self.assertEqual(r["items"], [{"key": "0", "items": ["a", "b"]}, {"key": "2", "items": ["c"]}])
        self.assertEqual(arch_extract.stage_names(r), ["a", "b", "c"])

    def test_not_found_says_why_and_never_guesses(self):
        cases = [
            ("dict-keys", "Y = {}\n", "not assigned"),
            ("dict-keys", "X = {}\nX = {}\n", "assigned 2 times"),
            ("dict-keys", "X = [1]\n", "not a dict literal"),
            ("dict-keys", "X = {**other}\n", "**"),
            ("dict-keys", "k = 'a'\nX = {k: 1}\n", "not a literal"),
            ("dict-map", 'X = {"a": 1}\n', "not a string literal"),
            ("list", "X = ['a', b]\n", "not a string literal"),
            ("list", "X = {'a'}\n", "not a list or tuple"),
            ("nested", 'X = {"a": {"f": ["x"]}}\n', 'needs "field"'),
            ("dict-keys", "X = (\n", "does not parse"),
        ]
        for kind, src, why in cases:
            with self.subTest(src=src):
                r = self.run_one(kind, src)
                self.assertFalse(r["found"])
                self.assertEqual(r["items"], [])
                self.assertIn(why, r["reason"])

    def test_missing_file_and_unknown_kind(self):
        self.assertIn("not in git", self.run_one("list", None)["reason"])
        self.assertIn("unknown kind", self.run_one("bogus", "X = []\n")["reason"])

    def test_extract_all_reads_each_file_once(self):
        calls = []

        def reader(repo, rev, path):
            calls.append(path)
            return 'A = ["x"]\nB = {"k": 1}\n'

        out = arch_extract.extract_all("r", "HEAD", [{"id": "a", "file": "f.py", "kind": "list", "name": "A"},
                                                      {"id": "b", "file": "f.py", "kind": "dict-keys", "name": "B"}], reader)
        self.assertEqual(calls, ["f.py"])
        self.assertEqual([o["items"] for o in out], [["x"], ["k"]])

    def test_the_source_is_never_executed(self):
        r = self.run_one("list", 'import os\nos.system("exit 1")\nX = ["a"]\n')
        self.assertTrue(r["found"])


class DeriveTests(unittest.TestCase):
    def setUp(self):
        self.d, self.alias = derive()
        self.nodes = {n["id"]: n for n in self.d["nodes"]}

    def test_nodes_are_real_folders_virtuals_and_groups(self):
        self.assertEqual(sorted(self.nodes), ["backend/api", "backend/eo", "group:contract", "group:devices", "group:server",
                                              "m2c/src/m2c", "m2c/src/m2c/sandbox", "protocol", "store:postgres", "store:redis"])

    def test_a_box_that_repeats_a_folder_is_merged_and_remembered_as_an_alias(self):
        self.assertEqual(self.nodes["m2c/src/m2c"]["aliases"], ["m2c", "m2c-core"])
        self.assertEqual(self.alias["m2c-core"], "m2c/src/m2c")
        self.assertTrue(any("m2c-core" in n for n in self.d["notes"]))

    def test_parent_children_and_groups(self):
        self.assertEqual(self.nodes["m2c/src/m2c/sandbox"]["parent"], "m2c/src/m2c")
        self.assertEqual(self.nodes["m2c/src/m2c"]["children"], ["m2c/src/m2c/sandbox"])
        self.assertEqual(self.nodes["backend/eo"]["group"], "group:server")

    def test_counts_skip_tests_and_include_nested_boxes(self):
        self.assertEqual(self.nodes["backend/eo"]["files"], 1)          # test_x.py is not counted
        self.assertEqual(self.nodes["backend/eo"]["functions"], 2)
        self.assertEqual(self.nodes["m2c/src/m2c"]["files"], 2)         # y.py and sandbox/z.py

    def edge(self, a, b, kind):
        return next((e for e in self.d["edges"] if (e["from"], e["to"], e["kind"]) == (a, b, kind)), None)

    def test_import_edge_goes_to_the_longest_matching_folder_and_ignores_same_node(self):
        self.assertEqual(self.edge("backend/api", "backend/eo", "import")["weight"], 1)
        self.assertIsNone(self.edge("backend/eo", "backend/eo", "import"))

    def test_touching_the_contract_is_a_protocol_edge_not_an_import(self):
        self.assertIsNotNone(self.edge("backend/eo", "protocol", "protocol"))
        self.assertIsNone(self.edge("backend/eo", "protocol", "import"))

    def test_api_call_edge_runs_from_the_caller_to_the_route_file(self):
        self.assertEqual(self.edge("m2c/src/m2c", "backend/api", "api-call")["weight"], 1)

    def test_graph_pairs_are_undirected_and_sorted(self):
        e = self.edge("backend/api", "backend/eo", "graph")
        self.assertEqual(e["weight"], 7)
        self.assertIs(e["directed"], False)

    def test_declared_edge_keeps_its_label_gate_and_zero_weight(self):
        e = self.edge("backend/eo", "m2c/src/m2c", "declared")
        self.assertEqual((e["label"], e["gate"], e["weight"]), ("only after approval", True, 0))

    def test_virtual_nodes_connect_only_to_code_in_their_own_group(self):
        # DATABASE_URL and the table "chats" are used by m2c/y.py too, but m2c is in group:devices, Postgres in group:server
        pg = [(e["from"], e["kind"]) for e in self.d["edges"] if e["to"] == "store:postgres"]
        self.assertEqual(sorted(pg), [("backend/api", "db"), ("backend/eo", "env")])
        rd = [e["from"] for e in self.d["edges"] if e["to"] == "store:redis"]
        self.assertEqual(rd, ["backend/eo"])

    def test_route_catalogue(self):
        g = self.d["catalogues"]["routes"][0]
        self.assertEqual((g["file"], g["node"]), ("backend/api/a.py", "backend/api"))
        self.assertEqual(g["routes"][0][:3], ["POST", "/api/tasks", "post_task"])

    def test_derive_is_deterministic(self):
        again, _ = derive()
        self.assertEqual(arch.dumps(again), arch.dumps(self.d))

    def test_absent_inputs_give_a_smaller_model_not_a_crash(self):
        d, _ = arch.derive(make_ctx(), TOPO, {}, {"census_extra": {}}, [])
        self.assertFalse(d["sources"]["imports"])
        self.assertEqual(d["edges"].__len__(), sum(1 for e in d["edges"] if e["kind"] == "declared"))

    def test_layout_pins_override_topology_and_unknown_pins_are_dropped(self):
        lay = arch.build_layout(TOPO, LAYOUT, self.d["nodes"], self.alias)
        self.assertEqual(lay["pins"]["backend/api"], {"x": 99, "y": 98, "from": "layout"})
        self.assertEqual(lay["pins"]["backend/eo"]["from"], "topology")
        self.assertNotIn("nowhere", lay["pins"])
        self.assertIn("store:postgres", lay["unplaced"])
        self.assertNotIn("group:server", lay["unplaced"])


class NodeIndexTests(unittest.TestCase):
    def setUp(self):
        d, _ = derive()
        self.ix = arch.NodeIndex(d["nodes"])

    def test_resolution_order(self):
        self.assertEqual(self.ix.resolve("backend/eo"), ("backend/eo", "id"))
        self.assertEqual(self.ix.resolve("eo"), ("backend/eo", "alias"))
        self.assertEqual(self.ix.resolve("m2c-core"), ("m2c/src/m2c", "alias"))
        self.assertEqual(self.ix.resolve("backend/eo/sub/dir"), ("backend/eo", "folder"))
        self.assertEqual(self.ix.resolve("store:postgres"), ("store:postgres", "id"))

    def test_groups_and_unknowns_do_not_resolve(self):
        self.assertIsNone(self.ix.resolve("group:server")[0])
        self.assertIsNone(self.ix.resolve("nonsense")[0])
        self.assertIsNone(self.ix.resolve(5)[0])


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.ctx = make_ctx()
        d, _ = derive()
        self.ix = arch.NodeIndex(d["nodes"])

    def check(self, f, **kw):
        return arch.validate_flow(f, kw.pop("filename", "task-pipeline.json"), self.ctx, self.ix, {"task-pipeline"}, **kw)

    def test_a_good_flow_is_clean(self):
        p = self.check(flow())
        self.assertEqual((p.errors, p.warnings), ([], []))

    def test_not_an_object(self):
        self.assertTrue(self.check([]).errors)

    def test_file_name_must_match_the_flow_id(self):
        self.assertTrue(any("file name" in e for e in self.check(flow(), filename="other.json").errors))

    def test_evidence_is_mandatory(self):
        f = flow()
        f["steps"][0]["evidence"] = []
        self.assertTrue(any("evidence" in e for e in self.check(f).errors))
        del f["steps"][0]["evidence"]
        self.assertTrue(any("evidence" in e for e in self.check(f).errors))

    def test_evidence_needs_a_qual_or_lines(self):
        f = flow()
        f["steps"][0]["evidence"] = [{"path": "backend/api/a.py", "qual": None, "lines": None, "hash": None}]
        self.assertTrue(any("qual" in e for e in self.check(f).errors))

    def test_bad_lines_and_hash(self):
        for bad in ([5, 2], [0, 4], ["a", "b"], [1]):
            with self.subTest(lines=bad):
                f = flow()
                f["steps"][0]["evidence"] = [ev("backend/api/a.py", lines=bad)]
                self.assertTrue(any("lines" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][0]["evidence"] = [ev("backend/api/a.py", h="xyz")]
        self.assertTrue(any("hash" in e for e in self.check(f).errors))

    def test_invented_code_is_an_error_at_the_current_commit_and_a_warning_otherwise(self):
        f = flow()
        f["steps"][0]["evidence"] = [ev("backend/api/a.py", "does_not_exist")]
        self.assertTrue(any("does_not_exist" in e for e in self.check(f).errors))
        f["commit"] = C2
        p = self.check(f)
        self.assertEqual(p.errors, [])
        self.assertTrue(any("does_not_exist" in w for w in p.warnings))

    def test_unknown_file_at_the_current_commit_is_an_error(self):
        f = flow()
        f["steps"][0]["evidence"] = [ev("nope.py", None, (1, 2))]
        self.assertTrue(any("nope.py" in e for e in self.check(f).errors))

    def test_unknown_actor_is_an_error_but_alias_is_only_a_warning(self):
        f = flow()
        f["steps"][1]["actor"] = "invented/place"
        self.assertTrue(any("invented/place" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][1]["actor"] = "eo"
        p = self.check(f)
        self.assertEqual(p.errors, [])
        self.assertTrue(any("backend/eo" in w for w in p.warnings))

    def test_gate_rules(self):
        f = flow()
        f["steps"][0]["kind"] = "gate"
        self.assertTrue(any("gate object" in e for e in self.check(f).errors))
        f["steps"][0]["gate"] = {"tier": "T3", "who": "nobody"}
        self.assertTrue(any("who" in e for e in self.check(f).errors))
        f["steps"][0]["gate"] = {"tier": "T3", "who": "user"}
        self.assertEqual(self.check(f).errors, [])

    def test_step_ids_next_and_cycles_to_self(self):
        f = flow()
        f["steps"][1]["id"] = "s01"
        self.assertTrue(any("duplicate" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][0]["next"] = ["s09"]
        self.assertTrue(any("s09" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][0]["next"] = ["s01"]
        self.assertTrue(any("itself" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][0]["id"] = "step1"
        self.assertTrue(any("s01" in e for e in self.check(f).errors))

    def test_too_many_steps_is_an_error_but_long_text_only_a_warning(self):
        f = flow()
        f["steps"] = [step(f"s{i:02d}") for i in range(1, 42)]
        self.assertTrue(any("limit" in e for e in self.check(f).errors))
        f = flow()
        f["steps"][0]["text"] = "x" * 400
        p = self.check(f)
        self.assertEqual(p.errors, [])
        self.assertTrue(any("limit" in w for w in p.warnings))

    def test_secrets_are_refused(self):
        f = flow(summary="the key is sk-" + "a" * 40)
        self.assertTrue(any("secret" in e for e in self.check(f).errors))

    def test_unknown_keys_warn(self):
        f = flow(extra=1)
        f["steps"][0]["mood"] = "x"
        w = self.check(f).warnings
        self.assertTrue(any("extra" in x for x in w) and any("mood" in x for x in w))

    def test_commit_must_be_a_full_sha(self):
        self.assertTrue(any("commit" in e for e in self.check(flow(commit="abc123")).errors))

    def test_lifecycle(self):
        lc = {"schema": 1, "flow": "task-pipeline", "title": "L", "kind": "lifecycle", "summary": "s", "commit": C1, "actors": ["backend/eo"],
              "states": [{"id": "queued", "label": "Queued"}, {"id": "done", "label": "Done", "terminal": True}],
              "transitions": [{"id": "t01", "from": "queued", "to": "done", "trigger": "finished", "text": "It finishes.",
                               "evidence": [ev("backend/eo/x.py", "run", (5, 50))], "confidence": "high"}]}
        self.assertEqual(self.check(lc).errors, [])
        bad = copy.deepcopy(lc)
        bad["transitions"][0]["to"] = "gone"
        self.assertTrue(any("gone" in e for e in self.check(bad).errors))
        bad = copy.deepcopy(lc)
        bad["transitions"][0]["evidence"] = []
        self.assertTrue(any("evidence" in e for e in self.check(bad).errors))
        bad = copy.deepcopy(lc)
        bad["states"].append({"id": "done", "label": "Again"})
        self.assertTrue(any("duplicate" in e for e in self.check(bad).errors))

    def test_stable_ids_refuse_reuse_and_renumbering(self):
        prev = flow()
        reused = flow()
        reused["steps"][1] = step("s02", "Totally different", "backend/eo", evidence=[ev("backend/eo/x.py", "step", (60, 80))])
        self.assertTrue(any("reuse" in e for e in self.check(reused, prev=prev).errors))
        renumbered = flow()
        renumbered["steps"][1]["id"] = "s03"
        renumbered["steps"][0]["next"] = ["s03"]
        self.assertTrue(any("renumbered" in e for e in self.check(renumbered, prev=prev).errors))
        reworded = flow()
        reworded["steps"][1]["title"] = "Run it properly"       # same code: the id may stay
        self.assertEqual(self.check(reworded, prev=prev).errors, [])
        grown = flow()
        grown["steps"].append(step("s03", "New", evidence=[ev("backend/eo/x.py", "step", (60, 80))]))
        grown["steps"][1]["next"] = ["s03"]
        self.assertEqual(self.check(grown, prev=prev).errors, [])


class FreshnessTests(unittest.TestCase):
    def test_same_hash_is_fresh_and_different_is_stale(self):
        ctx = make_ctx()
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py", h=H("1")), C1, ctx)[0], "fresh")
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py", h=H("9")), C1, ctx)[0], "stale")

    def test_missing_file_or_symbol_is_broken(self):
        ctx = make_ctx()
        self.assertEqual(arch.judge_evidence(ev("gone.py"), C1, ctx)[0], "broken")
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py", "gone"), C1, ctx)[0], "broken")

    def test_no_hash_at_the_census_commit_fills_the_hash_and_is_fresh(self):
        status, fill = arch.judge_evidence(ev("backend/api/a.py"), C1, make_ctx())
        self.assertEqual((status, fill), ("fresh", H("1")))

    def test_no_hash_and_no_git_for_an_older_flow_is_unverified(self):
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py"), C2, make_ctx())[0], "unverified")

    def test_blob_comparison_decides_when_there_is_no_hash(self):
        ctx = make_ctx()
        ctx.blobs = {"backend/api/a.py": "1" * 40}
        ctx._blobs_at = {C2: {"backend/api/a.py": "1" * 40}}
        ctx.minime = Path(".")
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py"), C2, ctx), ("fresh", H("1")))
        ctx._blobs_at = {C2: {"backend/api/a.py": "2" * 40}}
        self.assertEqual(arch.judge_evidence(ev("backend/api/a.py"), C2, ctx)[0], "stale")

    def test_worst_status_wins(self):
        self.assertEqual(arch.worst(["fresh", "stale", "unverified"]), "stale")
        self.assertEqual(arch.worst(["fresh", "broken", "stale"]), "broken")
        self.assertEqual(arch.worst([]), "unverified")

    def test_evaluate_flow_counts_and_takes_the_worst(self):
        f = arch.repair_flow(flow(), make_ctx())
        f["steps"][1]["evidence"][0]["hash"] = H("9")            # the code of step 2 has changed since
        e = arch.evaluate_flow(f, make_ctx())
        self.assertEqual((e["status"], e["counts"]), ("stale", {"fresh": 1, "stale": 1}))
        self.assertEqual([s["status"] for s in e["steps"]], ["fresh", "stale"])

    def test_repair_does_not_overwrite_and_does_not_mutate(self):
        f = flow()
        f["steps"][0]["evidence"][0]["hash"] = H("7")
        before = copy.deepcopy(f)
        r = arch.repair_flow(f, make_ctx())
        self.assertEqual(f, before)
        self.assertEqual(r["steps"][0]["evidence"][0]["hash"], H("7"))
        self.assertEqual(r["steps"][1]["evidence"][0]["hash"], H("2"))

    def test_normalise_actors_rewrites_aliases(self):
        d, _ = derive()
        f = arch.normalise_actors(flow(actors=["eo", "backend/api"]), arch.NodeIndex(d["nodes"]))
        f["steps"][1]["actor"] = "eo"
        f = arch.normalise_actors(f, arch.NodeIndex(d["nodes"]))
        self.assertEqual(f["actors"], ["backend/api", "backend/eo"])
        self.assertEqual(f["steps"][1]["actor"], "backend/eo")


class StageCheckTests(unittest.TestCase):
    REG = {"id": "task-pipeline", "extractors": [{"id": "tiers", "cross_check": True}]}

    def found(self, names):
        return {"id": "tiers", "found": True, "items": names}

    def test_a_stage_with_no_step_is_reported(self):
        f = flow()
        out = arch.stage_check(f, [self.found(["run", "ghost_stage"])], self.REG)
        self.assertEqual(out["checked"], ["tiers"])
        self.assertEqual(out["missing"], ["ghost_stage"])          # "run" appears in step 2's title

    def test_names_match_loosely(self):
        f = flow()
        f["steps"][0]["title"] = "Gate Keeper"
        self.assertEqual(arch.stage_check(f, [self.found(["gate_keeper"])], self.REG)["missing"], [])

    def test_unavailable_when_the_name_was_not_found(self):
        out = arch.stage_check(flow(), [{"id": "tiers", "found": False, "items": [], "reason": "not assigned"}], self.REG)
        self.assertEqual(out["unavailable"], [{"id": "tiers", "reason": "not assigned"}])
        self.assertEqual(out["missing"], [])

    def test_no_cross_check_means_no_comparison(self):
        reg = {"id": "x", "extractors": [{"id": "tiers"}]}
        self.assertEqual(arch.stage_check(flow(), [self.found(["zzz"])], reg), {"checked": [], "missing": [], "unavailable": []})


class RegistryTests(unittest.TestCase):
    def test_the_committed_registry_is_valid(self):
        reg = arch.load_registry(ROOT)
        self.assertEqual(arch.registry_problems(reg, ROOT), [])
        self.assertEqual(arch.layout_problems(json.loads((ROOT / arch.LAYOUT_FILE).read_text(encoding="utf-8"))), [])

    def test_problems_are_found(self):
        reg = {"flows": [{"id": "Bad Id", "kind": "nope", "seeds": []}, {"id": "ok", "kind": "pipeline", "seeds": ["a.py"]},
                         {"id": "ok", "kind": "pipeline", "seeds": ["a.py"]}],
               "views": [{"id": "v", "type": "wrong", "source": "flow", "flow": "missing"}], "extractors": []}
        text = "\n".join(arch.registry_problems(reg))
        for needle in ("lower-case", "kind must be", "non-empty list of seeds", "duplicate id", "type must be", "not a flow of the registry"):
            self.assertIn(needle, text)

    def test_layout_problems(self):
        text = "\n".join(arch.layout_problems({"virtual": [{"id": "postgres", "kind": "store"},
                                                           {"id": "store:a", "kind": "box", "label": "A", "source": "s"}]}))
        self.assertIn("must look like", text)
        self.assertIn("kind must be", text)

    def test_the_committed_seeds_exist_in_the_committed_census(self):
        reg = arch.load_registry(ROOT)
        ctx = arch.build_ctx(ROOT)
        rows = {}
        for f in reg["flows"]:
            _, missing = arch._seed_rows(ctx, f["seeds"])
            if missing:
                rows[f["id"]] = missing
        self.assertEqual(rows, {}, "a seed is not in the census: fix content/arch-flows.json")


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "content").mkdir()
        (self.tmp / "data" / "code").mkdir(parents=True)
        (self.tmp / "data").joinpath("census.json").write_text(json.dumps(census(FILES)), encoding="utf-8")
        (self.tmp / "content" / "topology.json").write_text(json.dumps(TOPO), encoding="utf-8")
        (self.tmp / "content" / "arch-layout.json").write_text(json.dumps(LAYOUT), encoding="utf-8")
        reg = {"flows": [{"id": "task-pipeline", "title": "Task pipeline", "kind": "pipeline", "seeds": ["backend/api/a.py::post_task"],
                          "views": ["task-pipeline"], "extractors": [{"id": "tiers", "file": "backend/eo/router.py", "kind": "list", "name": "T", "cross_check": True}]},
                         {"id": "memory", "title": "Memory", "kind": "pipeline", "seeds": ["backend/eo/x.py"], "views": ["memory"]}],
               "views": [{"id": "system", "title": "System", "type": "layered", "source": "derived"},
                         {"id": "task-pipeline", "title": "Task pipeline", "type": "layered", "source": "flow", "flow": "task-pipeline"},
                         {"id": "memory", "title": "Memory", "type": "layered", "source": "flow", "flow": "memory"},
                         {"id": "api-surface", "title": "API", "type": "catalog", "source": "derived"}]}
        (self.tmp / "content" / "arch-flows.json").write_text(json.dumps(reg), encoding="utf-8")
        for name in ("imports", "routes", "agents", "folders"):
            key = "folders" if name == "folders" else name
            path = self.tmp / ("data/graph/folders.json" if name == "folders" else f"data/code/{name}.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(INPUTS[key]), encoding="utf-8")
        self.log = []

    def build(self, **kw):
        return arch.build(self.tmp, None, log=self.log.append, **kw)

    def put_flow(self, f):
        d = self.tmp / arch.FLOWS_DIR
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{f['flow']}.json").write_text(arch.dumps(f), encoding="utf-8")

    def read(self, rel):
        return json.loads((self.tmp / rel).read_text(encoding="utf-8"))

    def test_build_with_no_flows_marks_them_missing_and_still_draws_the_structure(self):
        self.assertEqual(self.build(), 0)
        idx = self.read(arch.INDEX_FILE)
        self.assertEqual(idx["totals"]["flows"], 2)
        self.assertEqual(idx["totals"]["missing"], 2)
        self.assertEqual(idx["views"]["system"]["status"], "derived")
        self.assertEqual(idx["views"]["task-pipeline"]["status"], "missing")
        shard = self.read(f"{arch.VIEWS_DIR}/task-pipeline.json")
        self.assertIsNone(shard["flow_data"])
        self.assertTrue(shard["nodes"])                       # the structure is there while the flow is not
        self.assertEqual(self.read(f"{arch.VIEWS_DIR}/api-surface.json")["type"], "catalog")

    def test_build_is_idempotent_and_check_agrees(self):
        self.build()
        first = {p.relative_to(self.tmp).as_posix(): p.read_bytes() for p in (self.tmp / "data").rglob("*.json") if "arch" in p.as_posix() or "index" in p.as_posix()}
        self.assertEqual(self.build(check=True), 0)
        self.build()
        again = {p.relative_to(self.tmp).as_posix(): p.read_bytes() for p in (self.tmp / "data").rglob("*.json") if "arch" in p.as_posix() or "index" in p.as_posix()}
        self.assertEqual(first, again)

    def test_check_fails_when_a_file_is_edited_or_removed(self):
        self.build()
        (self.tmp / arch.MODEL_FILE).write_text("{}", encoding="utf-8")
        self.assertEqual(self.build(check=True), 1)
        self.build()
        (self.tmp / f"{arch.VIEWS_DIR}/memory.json").unlink()
        self.assertEqual(self.build(check=True), 1)

    def test_check_tolerates_crlf_on_disk(self):
        self.build()
        for p in (self.tmp / "data" / "arch").rglob("*.json"):
            p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(self.build(check=True), 0)

    def test_check_fails_for_a_view_shard_that_no_view_owns(self):
        self.build()
        (self.tmp / arch.VIEWS_DIR / "old.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.build(check=True), 1)
        self.assertEqual(self.build(), 0)
        self.assertFalse((self.tmp / arch.VIEWS_DIR / "old.json").exists())

    def test_a_committed_flow_is_evaluated_and_drawn(self):
        self.put_flow(arch.repair_flow(flow(), make_ctx()))
        self.assertEqual(self.build(), 0)
        model = self.read(arch.MODEL_FILE)
        self.assertEqual(model["flows"]["task-pipeline"]["status"], "fresh")
        shard = self.read(f"{arch.VIEWS_DIR}/task-pipeline.json")
        self.assertEqual({n["id"] for n in shard["nodes"]}, {"backend/api", "backend/eo"})
        self.assertEqual(shard["status"], "fresh")
        self.assertEqual(self.read(arch.INDEX_FILE)["totals"]["fresh"], 1)

    def test_a_changed_symbol_turns_the_flow_stale(self):
        f = arch.repair_flow(flow(), make_ctx())
        f["steps"][0]["evidence"][0]["hash"] = H("9")
        self.put_flow(f)
        self.build()
        idx = self.read(arch.INDEX_FILE)
        self.assertEqual(idx["flows"]["task-pipeline"]["status"], "stale")
        self.assertEqual(idx["flows"]["task-pipeline"]["counts"], {"fresh": 1, "stale": 1})

    def test_a_malformed_committed_flow_stops_the_build(self):
        bad = flow()
        bad["steps"][0]["evidence"] = []
        self.put_flow(bad)
        self.assertEqual(self.build(), 1)
        self.assertFalse((self.tmp / arch.MODEL_FILE).exists())

    def test_an_unregistered_flow_is_still_listed(self):
        self.put_flow(arch.repair_flow(flow(flow="extra"), make_ctx()))
        self.build()
        self.assertFalse(self.read(arch.INDEX_FILE)["flows"]["extra"]["registered"])

    def test_todo_lists_new_changed_and_incomplete_flows(self):
        ctx = make_ctx()
        reg = arch.load_registry(self.tmp)
        d, _ = derive()
        ix = arch.NodeIndex(d["nodes"])
        todo = arch.build_todo(ctx, reg, {}, d, ix)
        self.assertEqual([(f["id"], f["reason"]) for f in todo["flows"]], [("task-pipeline", "new"), ("memory", "new")])
        self.assertIn("backend/eo", [a["id"] for a in todo["actors"]])
        self.assertNotIn("group:server", [a["id"] for a in todo["actors"]])
        seed = todo["flows"][0]["seeds"][0]
        self.assertEqual((seed["path"], seed["symbols"][0]["qual"]), ("backend/api/a.py", "post_task"))
        stale = arch.repair_flow(flow(), ctx)
        stale["steps"][1]["evidence"][0]["hash"] = H("9")
        todo = arch.build_todo(ctx, reg, {"task-pipeline": stale}, d, ix)
        row = next(f for f in todo["flows"] if f["id"] == "task-pipeline")
        self.assertEqual((row["reason"], [s["id"] for s in row["steps_needing_work"]]), ("changed", ["s02"]))
        fresh = arch.repair_flow(flow(), ctx)
        self.assertNotIn("task-pipeline", [f["id"] for f in arch.build_todo(ctx, reg, {"task-pipeline": fresh}, d, ix)["flows"]])

    def test_todo_reports_seeds_that_are_not_in_the_census(self):
        reg = arch.load_registry(self.tmp)
        reg["flows"][0]["seeds"] = ["backend/api/a.py::nope", "ghost.py"]
        d, _ = derive()
        todo = arch.build_todo(make_ctx(), reg, {}, d, arch.NodeIndex(d["nodes"]))
        self.assertEqual(todo["flows"][0]["seeds_not_in_census"], ["backend/api/a.py::nope", "ghost.py"])

    def test_schema_markdown_is_generated_from_the_limits(self):
        md = arch.schema_markdown()
        self.assertIn(str(arch.LIMITS["steps"]), md)
        self.assertIn("Evidence is mandatory", md)
        self.assertNotIn("%(", md)


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.tmp), *a], capture_output=True, text=True, check=True).stdout.strip()

    def test_read_git_text_reads_the_commit_not_the_working_tree_and_normalises_endings(self):
        f = self.tmp / "m.py"
        f.write_bytes(b'X = ["a"]\r\n')
        self.git("add", "-A")
        self.git("commit", "-qm", "one")
        f.write_bytes(b'X = ["changed"]\n')                   # uncommitted edit
        text = arch_extract.read_git_text(self.tmp, "HEAD", "m.py")
        self.assertEqual(text, 'X = ["a"]\n')
        self.assertIsNone(arch_extract.read_git_text(self.tmp, "HEAD", "missing.py"))
        res = arch_extract.extract_all(self.tmp, "HEAD", [{"id": "x", "file": "m.py", "kind": "list", "name": "X"}])
        self.assertEqual(res[0]["items"], ["a"])

    def test_a_flow_older_than_the_census_is_judged_by_blob_ids(self):
        (self.tmp / "a.py").write_text("one\n")
        (self.tmp / "b.py").write_text("one\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "one")
        old = self.git("rev-parse", "HEAD")
        (self.tmp / "b.py").write_text("two\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "two")
        new = self.git("rev-parse", "HEAD")
        files = [rec("a.py", [sym("fa", 1, 2, H("1"))]), rec("b.py", [sym("fb", 1, 2, H("2"))])]
        ctx = arch.build_ctx(self.tmp, self.tmp, census(files, new))
        self.assertEqual(arch.judge_evidence({"path": "a.py", "qual": "fa", "lines": [1, 2], "hash": None}, old, ctx), ("fresh", H("1")))
        self.assertEqual(arch.judge_evidence({"path": "b.py", "qual": "fb", "lines": [1, 2], "hash": None}, old, ctx)[0], "stale")


class RepoTests(unittest.TestCase):
    def test_the_committed_architecture_data_is_exactly_what_build_would_write(self):
        out = []
        self.assertEqual(arch.build(ROOT, None, check=True, log=out.append), 0, "\n".join(out))

    def test_every_committed_flow_validates(self):
        ctx = arch.build_ctx(ROOT)
        d, _ = arch.derive(ctx, json.loads((ROOT / arch.TOPOLOGY_FILE).read_text(encoding="utf-8")),
                           json.loads((ROOT / arch.LAYOUT_FILE).read_text(encoding="utf-8")), arch.load_inputs(ROOT), [])
        ix = arch.NodeIndex(d["nodes"])
        flows, bad = arch.notes.read_notes_dir(ROOT / arch.FLOWS_DIR)
        self.assertEqual(list(bad), [])
        ids = {f["id"] for f in arch.load_registry(ROOT)["flows"]}
        for name, f in flows.items():
            with self.subTest(flow=name):
                self.assertEqual(arch.validate_flow(f, name, ctx, ix, ids).errors, [])


if __name__ == "__main__":
    unittest.main()
