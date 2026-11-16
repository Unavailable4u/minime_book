#!/usr/bin/env python3
"""
Tests for scripts/build_code.py (patch P10). Standard library only.

    python scripts/test_build_code.py
    python -m unittest discover -s scripts

Most tests build a miniature census in memory. One checks the repo itself: the committed data/code must match the
committed data/census.json (if you replaced the census and it fails, run `python scripts/refresh_atlas.py`).
"""
import collections
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("build_code", ROOT / "scripts" / "build_code.py")
bc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bc)


def imp(mod, names=(), level=0, line=1):
    return {"mod": mod, "names": list(names), "level": level, "line": line, "lazy": False}


def pyfile(path, imports=(), functions=(), test=False, **extra):
    return {"path": path, "ext": "py", "lang": "python", "lines": 10, "code": 8, "comment": 1, "blank": 1, "size": 100,
            "test": test, "binary": False, "imports": list(imports), "functions": list(functions), "classes": [], **extra}


def jsfile(path, imports=(), functions=()):
    return {"path": path, "ext": path.rsplit(".", 1)[-1], "lang": "javascript", "lines": 5, "code": 5, "comment": 0, "blank": 0,
            "size": 50, "test": False, "binary": False, "imports": [{"mod": m, "line": i + 1} for i, m in enumerate(imports)],
            "functions": list(functions), "classes": []}


def fn(qual, start=1, end=3, calls=None, **extra):
    d = {"name": qual.split(".")[-1], "qual": qual, "kind": "function", "start": start, "end": end, "loc": end - start + 1, "cc": 1,
         "hash": "0123456789", **extra}
    if calls is not None:
        d["calls"] = calls
    return d


def census(files, **meta):
    return {"meta": {"generated": "2026-11-15T01:02:03", "script_version": 2, **meta},
            "git": {"head": "abc1234", "head_full": "a" * 40}, "totals": {}, "files": files}


def build(files, **meta):
    return bc.build(Path("/nonexistent"), census(files, **meta))


def load(out, rel):
    return json.loads(out[rel])


class Resolver(unittest.TestCase):
    def setUp(self):
        self.files = [
            pyfile("backend/eo/__init__.py"),
            pyfile("backend/eo/a.py"),
            pyfile("backend/eo/b.py"),
            pyfile("backend/eo/sub/__init__.py"),
            pyfile("backend/eo/sub/leaf.py"),
            pyfile("backend/utils/logging.py"),
            pyfile("backend/api/routes/__init__.py"),
            pyfile("backend/api/routes/stripe.py"),
            pyfile("backend/tests/test_a.py", test=True),
            pyfile("m2c/src/m2c/__init__.py"),
            pyfile("m2c/src/m2c/link/__init__.py"),
            pyfile("m2c/src/m2c/link/client.py"),
            pyfile("backend/tests/conftest.py", test=True),
            pyfile("m2c/tests/conftest.py", test=True),
        ]
        self.r = bc.ImportResolver(self.files)

    def test_relative_imports_are_exact(self):
        self.assertEqual((["backend/eo/b.py"], "internal"), self.r.python("backend/eo/a.py", "b", 1, ["thing"]))
        self.assertEqual((["backend/eo/sub/leaf.py"], "internal"), self.r.python("backend/eo/a.py", "sub.leaf", 1, []))
        self.assertEqual((["backend/eo/__init__.py"], "internal"), self.r.python("backend/eo/sub/leaf.py", "", 2, []))
        self.assertEqual((["backend/eo/b.py"], "internal"), self.r.python("backend/eo/sub/leaf.py", "b", 2, []))

    def test_from_package_import_module_links_the_init_and_the_submodule(self):
        targets, status = self.r.python("backend/tests/test_a.py", "eo", 0, ["a", "not_a_module"])
        self.assertEqual("internal", status)
        self.assertEqual(["backend/eo/__init__.py", "backend/eo/a.py"], targets)
        # from . import b  ->  the package itself and the submodule
        self.assertEqual((["backend/eo/__init__.py", "backend/eo/b.py"], "internal"), self.r.python("backend/eo/a.py", "", 1, ["b"]))

    def test_unresolvable_relative_import_is_external(self):
        self.assertEqual(([], "external"), self.r.python("backend/eo/a.py", "nope", 1, []))

    def test_absolute_import_matches_by_dotted_suffix(self):
        self.assertEqual((["backend/eo/b.py"], "internal"), self.r.python("backend/eo/a.py", "eo.b", 0, []))
        self.assertEqual((["m2c/src/m2c/link/client.py"], "internal"), self.r.python("backend/eo/a.py", "m2c.link.client", 0, []))
        self.assertEqual((["backend/eo/__init__.py"], "internal"), self.r.python("backend/eo/a.py", "eo", 0, []))

    def test_stdlib_wins_over_a_repo_file_of_the_same_name(self):
        self.assertEqual(([], "stdlib"), self.r.python("backend/eo/a.py", "logging", 0, []))

    def test_a_third_party_name_never_lands_on_a_file_inside_a_package(self):
        # backend/api/routes is a package, so routes/stripe.py is only importable as routes.stripe
        self.assertEqual(([], "external"), self.r.python("backend/eo/a.py", "stripe", 0, []))
        self.assertEqual((["backend/api/routes/stripe.py"], "internal"), self.r.python("backend/eo/a.py", "routes.stripe", 0, []))
        self.assertEqual(([], "external"), self.r.python("backend/eo/a.py", "b", 0, []))     # eo/b.py sits inside the eo package

    def test_ties_prefer_the_importers_folder_then_ambiguous(self):
        self.assertEqual((["backend/tests/conftest.py"], "internal"), self.r.python("backend/tests/test_a.py", "conftest", 0, []))
        self.assertEqual((["backend/tests/conftest.py"], "internal"), self.r.python("backend/eo/a.py", "conftest", 0, []))   # shares "backend"
        self.assertEqual(([], "ambiguous"), self.r.python("tools/x.py", "conftest", 0, []))                                   # shares nothing with either

    def test_non_test_importers_prefer_non_test_files(self):
        files = [pyfile("a/helpers.py"), pyfile("t/helpers.py", test=True), pyfile("b/main.py")]
        r = bc.ImportResolver(files)
        self.assertEqual((["a/helpers.py"], "internal"), r.python("b/main.py", "helpers", 0, []))

    def test_star_and_empty_names_are_ignored(self):
        self.assertEqual((["backend/eo/b.py"], "internal"), self.r.python("backend/eo/a.py", "eo.b", 0, ["*", ""]))

    # ---- javascript
    def test_javascript_relative_resolution(self):
        files = [jsfile("web/app/page.js"), jsfile("web/lib/util.js"), jsfile("web/components/Gate.jsx"), jsfile("web/components/box/index.js"),
                 {**jsfile("web/data.json"), "ext": "json", "lang": "json"}, jsfile("web/lib/mod.mjs")]
        r = bc.ImportResolver(files)
        self.assertEqual(("web/lib/util.js", "internal"), r.javascript("web/app/page.js", "../lib/util"))
        self.assertEqual(("web/lib/util.js", "internal"), r.javascript("web/app/page.js", "../lib/util.js"))
        self.assertEqual(("web/components/Gate.jsx", "internal"), r.javascript("web/app/page.js", "../components/Gate"))
        self.assertEqual(("web/components/box/index.js", "internal"), r.javascript("web/app/page.js", "../components/box"))
        self.assertEqual(("web/data.json", "internal"), r.javascript("web/app/page.js", "../data.json"))
        self.assertEqual(("web/lib/mod.mjs", "internal"), r.javascript("web/app/page.js", "../lib/mod"))
        self.assertEqual((None, "external"), r.javascript("web/app/page.js", "./missing"))
        self.assertEqual((None, "external"), r.javascript("web/app/page.js", "../../../outside"))

    def test_javascript_bare_specifiers(self):
        r = bc.ImportResolver([jsfile("web/a.js")])
        self.assertEqual((None, "external"), r.javascript("web/a.js", "react"))
        self.assertEqual((None, "stdlib"), r.javascript("web/a.js", "fs"))
        self.assertEqual((None, "stdlib"), r.javascript("web/a.js", "node:path"))
        self.assertEqual("next", bc.external_name("js", "next/link"))
        self.assertEqual("@sentry/nextjs", bc.external_name("js", "@sentry/nextjs"))
        self.assertEqual("@sentry/nextjs", bc.external_name("mjs", "@sentry/nextjs/foo"))
        self.assertEqual("fastapi", bc.external_name("py", "fastapi.responses"))


class ImportsFile(unittest.TestCase):
    def setUp(self):
        self.files = [
            pyfile("backend/eo/__init__.py"),
            pyfile("backend/eo/a.py", imports=[imp("os"), imp("fastapi.responses", ["JSONResponse"], line=2), imp("b", [], 1, line=3),
                                               imp("b", [], 1, line=9), imp("eo.a", line=4), imp("requests", line=5)]),
            pyfile("backend/eo/b.py"),
            jsfile("web/a.js", imports=["./b", "react", "fs"]),
            jsfile("web/b.js"),
            {"path": "web/logo.png", "ext": "png", "lang": "other", "binary": True, "lines": 0, "code": 0},
        ]
        self.out = bc.build_imports(census(self.files), bc.census_files(census(self.files)))

    def test_forward_edges_have_the_first_line_and_no_self_edge(self):
        self.assertEqual([["backend/eo/b.py", 3]], self.out["imports"]["backend/eo/a.py"])
        self.assertEqual([["web/b.js", 1]], self.out["imports"]["web/a.js"])

    def test_reverse_edges(self):
        self.assertEqual({"backend/eo/b.py": ["backend/eo/a.py"], "web/b.js": ["web/a.js"]}, self.out["imported_by"])

    def test_external_names_exclude_stdlib_and_are_sorted(self):
        self.assertEqual({"backend/eo/a.py": ["fastapi", "requests"], "web/a.js": ["react"]}, self.out["external"])

    def test_stats_count_statements(self):
        self.assertEqual({"internal": 3, "external": 2, "stdlib": 1, "ambiguous": 0}, self.out["stats"]["python"])
        self.assertEqual({"internal": 1, "external": 1, "stdlib": 1, "ambiguous": 0}, self.out["stats"]["javascript"])

    def test_commit_is_the_full_id(self):
        self.assertEqual("a" * 40, self.out["commit"])


class ShardPlanning(unittest.TestCase):
    def test_a_small_repo_is_one_shard_per_folder_only_when_it_has_to_split(self):
        sizes = {"README.md": 10, "backend/a.py": 10, "backend/b.py": 10, "web/x.js": 10}
        self.assertEqual({"README.md": "_root", "backend/a.py": "_root", "backend/b.py": "_root", "web/x.js": "_root"}, bc.plan_shards(sizes, 1000))

    def test_an_oversize_repo_splits_by_folder(self):
        sizes = {"README.md": 10, "backend/a.py": 40, "backend/b.py": 40, "web/x.js": 60}
        self.assertEqual({"README.md": "_root", "backend/a.py": "backend", "backend/b.py": "backend", "web/x.js": "web"},
                         bc.plan_shards(sizes, 100))

    def test_split_goes_as_deep_as_it_must(self):
        sizes = {"a/b/c/1.py": 60, "a/b/c/2.py": 60, "a/b/d/1.py": 60, "a/e.py": 30}
        got = bc.plan_shards(sizes, 100)
        self.assertEqual({"a/b/c/1.py": "a__b__c~1", "a/b/c/2.py": "a__b__c~2", "a/b/d/1.py": "a__b__d", "a/e.py": "a"}, got)

    def test_a_folder_without_subfolders_is_cut_in_path_order(self):
        sizes = {f"t/{n}.py": 40 for n in "abcdef"}
        got = bc.plan_shards(sizes, 100)
        self.assertEqual({"t/a.py": "t~1", "t/b.py": "t~1", "t/c.py": "t~2", "t/d.py": "t~2", "t/e.py": "t~3", "t/f.py": "t~3"}, got)

    def test_a_file_over_the_limit_is_alone(self):
        got = bc.plan_shards({"t/big.py": 500, "t/a.py": 10, "t/b.py": 10}, 100)
        self.assertEqual({"t/a.py": "t~1", "t/b.py": "t~1", "t/big.py": "t~2"}, got)

    def test_ids_are_filesystem_safe_and_never_clash(self):
        got = bc.plan_shards({".github/x.yml": 60, "a b/y.py": 60, "A-B/z.py": 60, "root.md": 1}, 100)
        # "a b" and "A-B" both become a-b: the second one gets a numeric suffix instead of overwriting the first
        self.assertEqual({".github/x.yml": "github", "A-B/z.py": "a-b", "a b/y.py": "a-b-2", "root.md": "_root"}, got)
        for sid in set(got.values()):
            self.assertRegex(sid, r"^[a-z0-9_.~-]+$")

    def test_deterministic(self):
        sizes = {f"x/{i}/{j}.py": 30 for i in range(6) for j in range(5)}
        self.assertEqual(bc.plan_shards(sizes, 100), bc.plan_shards(dict(reversed(list(sizes.items()))), 100))


class Outputs(unittest.TestCase):
    def setUp(self):
        self.files = [
            pyfile("backend/eo/__init__.py", module_doc="The eo package."),
            pyfile("backend/eo/a.py", imports=[imp("eo.b")],
                   functions=[fn("top", 1, 5, calls=[["helper", "backend/eo/b.py::helper"], ["os.path.join", None]]),
                              fn("Cls.method", 6, 9, calls=[["top", "backend/eo/a.py::top"]])],
                   exports=["top"], git={"commits": 3, "added": 10, "deleted": 1, "first": "2026-01-01", "last": "2026-05-05", "dates": ["2026-01-01", "2026-05-05"]}),
            pyfile("backend/eo/b.py", functions=[fn("helper", 1, 2, calls=[["helper", "backend/eo/b.py::helper"]])]),
            pyfile("backend/tests/test_a.py", test=True, functions=[fn("test_top", 1, 3, calls=[["a.top", "backend/eo/a.py::top"]])]),
            jsfile("web/app.jsx", imports=["./util"], functions=[fn("App", 1, 4, kind="component")]),
            jsfile("web/util.js"),
            {"path": "web/logo.png", "ext": "png", "lang": "other", "binary": True, "lines": 0, "code": 0, "size": 9000},
            {"path": "README.md", "ext": "md", "lang": "markdown", "lines": 3, "code": 3, "size": 40, "test": False, "binary": False},
        ]
        self.out = build(self.files)

    def test_the_set_of_outputs(self):
        self.assertEqual({"data/code/tree.json", "data/code/imports.json", "data/code/files/_root.json", "data/code/callers/_root.json"}, set(self.out))

    def test_tree_totals_rows_and_flags(self):
        t = load(self.out, "data/code/tree.json")
        self.assertEqual(bc.TREE_FIELDS, t["file_fields"])
        self.assertEqual(["_root"], t["shards"])
        self.assertEqual((2, "2026-11-15", "a" * 40), (t["script_version"], t["generated"], t["commit"]))
        root = t["root"]
        self.assertEqual({"files": 8, "lines": 10 * 4 + 5 * 2 + 0 + 3, "code": 8 * 4 + 5 * 2 + 0 + 3, "functions": 5, "classes": 0}, root["n"])
        self.assertEqual(["README.md"], [r[0] for r in root["files"]])
        self.assertEqual(["backend", "web"], [d["name"] for d in root["dirs"]])
        web = next(d for d in root["dirs"] if d["name"] == "web")
        rows = {r[0]: dict(zip(t["file_fields"], r)) for r in web["files"]}
        self.assertEqual(-1, rows["logo.png"]["shard"])
        self.assertEqual("b", rows["logo.png"]["flags"])
        self.assertEqual(0, rows["app.jsx"]["shard"])
        self.assertEqual(1, rows["app.jsx"]["functions"])
        backend = next(d for d in root["dirs"] if d["name"] == "backend")
        eo = next(d for d in backend["dirs"] if d["name"] == "eo")
        a = dict(zip(t["file_fields"], next(r for r in eo["files"] if r[0] == "a.py")))
        self.assertEqual((3, "2026-05-05", 2), (a["commits"], a["last"], a["functions"]))
        tests = next(d for d in backend["dirs"] if d["name"] == "tests")
        self.assertEqual("t", tests["files"][0][8])

    def test_a_shard_holds_every_non_binary_file_without_raw_imports(self):
        d = load(self.out, "data/code/files/_root.json")
        self.assertEqual(1, d["schema"])
        self.assertEqual("_root", d["shard"])
        self.assertEqual(["README.md", "backend/eo/__init__.py", "backend/eo/a.py", "backend/eo/b.py", "backend/tests/test_a.py", "web/app.jsx", "web/util.js"],
                         [f["path"] for f in d["files"]])
        a = next(f for f in d["files"] if f["path"] == "backend/eo/a.py")
        self.assertNotIn("imports", a)
        self.assertEqual(["top"], a["exports"])
        self.assertEqual(["helper", "backend/eo/b.py::helper"], a["functions"][0]["calls"][0])
        self.assertEqual("0123456789", a["functions"][0]["hash"])
        readme = next(f for f in d["files"] if f["path"] == "README.md")
        self.assertNotIn("functions", readme)           # empty fields are left out
        self.assertNotIn("module_doc", readme)

    def test_callers_are_the_reverse_of_calls_without_self_calls_or_unresolved_names(self):
        c = load(self.out, "data/code/callers/_root.json")["callers"]
        self.assertEqual({"backend/eo/a.py::top": ["backend/eo/a.py::Cls.method", "backend/tests/test_a.py::test_top"],
                          "backend/eo/b.py::helper": ["backend/eo/a.py::top"]}, c)
        # helper calling itself is not an entry for helper, and os.path.join (unresolved, no target) is not in it at all

    def test_callers_are_stored_with_the_called_files_shard(self):
        many = [pyfile(f"pkg{i}/m.py", functions=[fn(f"f{j}", j + 1, j + 1) for j in range(30)]) for i in range(6)]
        many[0]["functions"][0]["calls"] = [["x", "pkg5/m.py::f3"]]
        many[5]["functions"][3]["calls"] = [["y", "pkg0/m.py::f0"]]
        old = bc.SHARD_LIMIT
        try:
            bc.SHARD_LIMIT = 100
            out = bc.build(Path("/nonexistent"), census(many))
        finally:
            bc.SHARD_LIMIT = old
        self.assertEqual({"data/code/callers/pkg0.json", "data/code/callers/pkg5.json"}, {k for k in out if k.startswith("data/code/callers/")})
        self.assertEqual({"pkg5/m.py::f3": ["pkg0/m.py::f0"]}, json.loads(out["data/code/callers/pkg5.json"])["callers"])
        self.assertEqual({"pkg0/m.py::f0": ["pkg5/m.py::f3"]}, json.loads(out["data/code/callers/pkg0.json"])["callers"])
        for rel in (k for k in out if k.startswith("data/code/callers/")):
            d = json.loads(out[rel])
            paths = {f["path"] for f in json.loads(out[f"data/code/files/{d['shard']}.json"])["files"]}
            for target in d["callers"]:
                self.assertIn(target.split("::")[0], paths, "a callers shard is named after the shard of the called symbol's file")

    def test_a_v1_census_builds_with_no_callers(self):
        files = [pyfile("a/x.py", functions=[{"name": "f", "qual": "f", "start": 1, "end": 2, "loc": 2, "cc": 1}])]
        out = bc.build(Path("/nonexistent"), {"meta": {"generated": "2026-10-26T00:00:00"}, "git": {"head": "50e25b5"}, "files": files})
        t = load(out, "data/code/tree.json")
        self.assertEqual((1, "50e25b5"), (t["script_version"], t["commit"]))
        self.assertFalse([k for k in out if "/callers/" in k])
        self.assertEqual(1, t["root"]["n"]["functions"])

    def test_deterministic_and_no_timestamp_of_its_own(self):
        again = build(list(reversed(self.files)))
        self.assertEqual(self.out, again)
        self.assertNotIn("seconds", self.out["data/code/tree.json"])

    def test_empty_census_gives_a_valid_empty_tree(self):
        out = bc.build(Path("/nonexistent"), {})
        t = load(out, "data/code/tree.json")
        self.assertEqual({"files": 0, "lines": 0, "code": 0, "functions": 0, "classes": 0}, t["root"]["n"])
        self.assertEqual([], t["shards"])


class WriteAndCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.census = census([pyfile("backend/a.py", functions=[fn("f", calls=[["g", "backend/b.py::g"]])]), pyfile("backend/b.py", functions=[fn("g")])])
        (self.tmp / "data").mkdir()
        (self.tmp / "data" / "census.json").write_text(json.dumps(self.census), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_then_check_then_stale(self):
        self.assertEqual(["missing: data/code/callers/_root.json", "missing: data/code/files/_root.json", "missing: data/code/imports.json", "missing: data/code/tree.json"],
                         bc.check_all(self.tmp))
        changed = bc.write_all(self.tmp)
        self.assertEqual(4, len(changed))
        self.assertEqual([], bc.check_all(self.tmp))
        self.assertEqual([], bc.write_all(self.tmp), "a second write changes nothing")
        (self.tmp / "data" / "code" / "tree.json").write_text("{}", encoding="utf-8")
        self.assertEqual(["stale: data/code/tree.json"], bc.check_all(self.tmp))

    def test_check_tolerates_crlf_on_disk(self):
        bc.write_all(self.tmp)
        for p in (self.tmp / "data" / "code").rglob("*.json"):
            p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual([], bc.check_all(self.tmp))

    def test_an_orphan_shard_is_reported_and_removed(self):
        bc.write_all(self.tmp)
        for d in ("files", "callers"):
            (self.tmp / "data" / "code" / d / "gone.json").write_text("{}", encoding="utf-8")
        self.assertEqual(["unexpected: data/code/files/gone.json", "unexpected: data/code/callers/gone.json"], bc.check_all(self.tmp))
        self.assertEqual(["data/code/files/gone.json (removed)", "data/code/callers/gone.json (removed)"], bc.write_all(self.tmp))
        self.assertEqual([], bc.check_all(self.tmp))

    def test_main_exit_codes(self):
        self.assertEqual(1, bc.main(["--root", str(self.tmp), "--check"]))
        self.assertEqual(0, bc.main(["--root", str(self.tmp)]))
        self.assertEqual(0, bc.main(["--root", str(self.tmp), "--check"]))

    def test_the_census_argument_overrides_the_file_on_disk(self):
        other = census([pyfile("only/c.py")])
        self.assertIn("data/code/files/_root.json", bc.build(self.tmp, other))
        self.assertIn("only/c.py", bc.build(self.tmp, other)["data/code/files/_root.json"])


class RepoState(unittest.TestCase):
    """The committed data/code against the committed census: the invariants the Explorer relies on."""

    @classmethod
    def setUpClass(cls):
        cls.census = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        cls.out = bc.build(ROOT, cls.census)

    def test_committed_data_code_matches_the_committed_census(self):
        self.assertEqual([], bc.check_all(ROOT, self.census),
                         "data/code is out of date with data/census.json; run: python scripts/refresh_atlas.py")

    def test_every_non_binary_file_is_in_exactly_one_shard_and_the_tree_agrees(self):
        where = collections.Counter()
        shard_of = {}
        for rel, text in self.out.items():
            if rel.startswith(bc.FILES_DIR + "/"):
                d = json.loads(text)
                for f in d["files"]:
                    where[f["path"]] += 1
                    shard_of[f["path"]] = d["shard"]
        expected = {f["path"] for f in self.census["files"] if not f.get("binary")}
        self.assertEqual(expected, set(where))
        self.assertEqual({1}, set(where.values()))
        t = json.loads(self.out["data/code/tree.json"])

        def walk(node, prefix=""):
            for r in node.get("files", []):
                yield prefix + r[0], r
            for d in node.get("dirs", []):
                yield from walk(d, prefix + d["name"] + "/")
        rows = dict(walk(t["root"]))
        self.assertEqual({f["path"] for f in self.census["files"]}, set(rows))
        for path, r in rows.items():
            sid = r[t["file_fields"].index("shard")]
            if path in expected:
                self.assertEqual(shard_of[path], t["shards"][sid], path)
            else:
                self.assertEqual(-1, sid, path)

    def test_totals_match_the_census(self):
        n = json.loads(self.out["data/code/tree.json"])["root"]["n"]
        self.assertEqual(self.census["totals"]["functions"], n["functions"])
        self.assertEqual(self.census["totals"]["lines"], n["lines"])
        self.assertEqual(len(self.census["files"]), n["files"])

    def test_no_shard_is_over_the_limit_unless_it_is_one_file(self):
        for rel, text in self.out.items():
            if rel.startswith((bc.FILES_DIR + "/", bc.CALLERS_DIR + "/")) or rel.endswith("imports.json"):
                size = len(text.encode("utf-8"))
                if size > bc.SHARD_LIMIT and rel.startswith(bc.FILES_DIR + "/"):
                    self.assertEqual(1, len(json.loads(text)["files"]), rel)
                else:
                    self.assertLessEqual(size, bc.SHARD_LIMIT * 1.05, rel)

    def test_symbol_keys_are_unique_when_the_census_is_v2(self):
        if (self.census["meta"].get("script_version") or 1) < 2:
            self.skipTest("v1 census: keys are not unique")
        for rel, text in self.out.items():
            if rel.startswith(bc.FILES_DIR + "/"):
                for f in json.loads(text)["files"]:
                    quals = [x["qual"] for x in f.get("functions", []) + f.get("classes", [])]
                    self.assertEqual(len(quals), len(set(quals)), f["path"])

    def test_every_caller_edge_points_at_a_real_symbol(self):
        # a call can resolve to a class (a constructor call), so a target is any function or class;
        # a caller is always a function. assertTrue with a message: assertIn would print the whole set on failure.
        funcs, classes = set(), set()
        for f in self.census["files"]:
            for x in f.get("functions", []):
                funcs.add(f"{f['path']}::{x['qual']}")
            for x in f.get("classes", []):
                classes.add(f"{f['path']}::{x.get('qual') or x['name']}")
        for rel, text in self.out.items():
            if rel.startswith(bc.CALLERS_DIR + "/"):
                for target, who in json.loads(text)["callers"].items():
                    self.assertTrue(target in funcs or target in classes, f"{rel}: unknown call target {target}")
                    for w in who:
                        self.assertTrue(w in funcs, f"{rel}: unknown caller {w}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
