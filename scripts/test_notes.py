#!/usr/bin/env python3
"""
Tests for scripts/notes.py (patch P11). Standard library only.

    python scripts/test_notes.py
    python -m unittest discover -s scripts

Most tests build a miniature census in memory. The git tests make a throw-away repository in a temp folder (they are
skipped when git is not installed). One test checks the repo itself: every committed note must validate.
"""
import copy
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("notes", ROOT / "scripts" / "notes.py")
notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(notes)

C1 = "a" * 40
C2 = "b" * 40
B1 = "1" * 40
B2 = "2" * 40
H = lambda c: c * 10        # a 10-hex symbol hash


def sym(qual, start, end, h, kind="function", **extra):
    d = {"name": qual.split(".")[-1], "qual": qual, "kind": kind, "start": start, "end": end, "loc": end - start + 1,
         "cc": 1, "hash": h, "visibility": "public", "decorators": [], "test": False}
    d.update(extra)
    return d


def rec(path, funcs=(), classes=(), lang="python", **extra):
    return {"path": path, "lang": lang, "lines": 100, "test": False, "binary": False, "functions": list(funcs),
            "classes": list(classes), "git": {"commits": 3}, **extra}


def census(files, commit=C1, routes=()):
    return {"meta": {"script_version": 2}, "git": {"head": commit[:7], "head_full": commit}, "files": list(files), "routes": list(routes)}


TIERS = {
    "rules": [
        {"tier": 0, "why": "binary", "binary": True},
        {"tier": 4, "why": "tests", "test": True, "globs": ["**/tests/**"]},
        {"tier": 1, "why": "hubs", "hubs": 2},
        {"tier": 1, "why": "routes", "route_files": True},
        {"tier": 1, "why": "core", "globs": ["backend/core/**"]},
        {"tier": 2, "why": "agents", "globs": ["backend/agents/**"]},
    ],
    "default": {"tier": 3, "languages": ["python", "javascript"], "other": 0},
    "symbols": {"skip_kinds": ["nested"], "1": {"min_loc": 6, "min_cc": 3, "decorated": True},
                "2": {"min_loc": 12, "min_cc": 6, "decorated": True, "public": True}, "3": {"public": True, "exported": True}},
}


def good_note(path="backend/core/a.py", commit=C1, blob=B1, tier=1, symbols=None, **extra):
    n = {"schema": 1, "path": path, "blob": blob, "commit": commit, "written": "2026-11-16", "tier": tier,
         "summary": "Does a thing.", "symbols": symbols if symbols is not None else []}
    n.update(extra)
    return n


def nsym(qual, start, end, h=None, summary="Does it.", **extra):
    return {"qual": qual, "start": start, "end": end, "hash": h, "summary": summary, **extra}


def make_ctx(files, blobs=None, commit=C1, tiers=None, degree=None):
    ctx = notes.build_ctx(ROOT, None, census(files, commit))
    ctx.cfg = tiers or TIERS
    ctx.degree = degree or {}
    ctx.tiers = notes.assign_tiers(list(ctx.files.values()), ctx.cfg, ctx.degree, ())
    ctx.blobs = blobs
    return ctx


class GlobTests(unittest.TestCase):
    def test_double_star_crosses_folders_and_matches_zero_folders(self):
        self.assertTrue(notes.glob_match("**/tests/**", "backend/tests/unit/x.py"))
        self.assertTrue(notes.glob_match("**/tests/**", "tests/x.py"))
        self.assertFalse(notes.glob_match("**/tests/**", "backend/testsuite/x.py"))

    def test_single_star_stays_inside_a_folder(self):
        self.assertTrue(notes.glob_match("backend/api/*.py", "backend/api/server.py"))
        self.assertFalse(notes.glob_match("backend/api/*.py", "backend/api/routes/x.py"))

    def test_a_pattern_without_a_slash_matches_the_file_name_at_any_depth(self):
        self.assertTrue(notes.glob_match("*.jsonl", "protocol/fixtures/a/b.jsonl"))
        self.assertFalse(notes.glob_match("*.jsonl", "a/b.jsonlx"))
        self.assertTrue(notes.glob_match("package-lock.json", "frontend/package-lock.json"))

    def test_braces_are_alternatives(self):
        g = "m2c/src/m2c/{policy,sandbox}/**"
        self.assertTrue(notes.glob_match(g, "m2c/src/m2c/sandbox/run.py"))
        self.assertFalse(notes.glob_match(g, "m2c/src/m2c/tui/run.py"))
        self.assertTrue(notes.glob_match("backend/eo/{a,b}.py", "backend/eo/b.py"))

    def test_dots_are_literal(self):
        self.assertFalse(notes.glob_match("a.py", "axpy"))


class TierTests(unittest.TestCase):
    def files(self):
        return [rec("backend/core/a.py"), rec("backend/agents/b.py"), rec("backend/tests/t.py", test=True), rec("x/y.py"),
                rec("img.png", lang="other", binary=True), rec("notes.txt", lang="text"), rec("backend/api/r.py"), rec("backend/core/c.py")]

    def test_first_matching_rule_wins_and_default_covers_the_rest(self):
        t = notes.assign_tiers(self.files(), TIERS, {}, {"backend/api/r.py"})
        self.assertEqual(t["backend/core/a.py"][0], 1)
        self.assertEqual(t["backend/agents/b.py"][0], 2)
        self.assertEqual(t["backend/tests/t.py"][0], 4)
        self.assertEqual(t["x/y.py"], (3, "default"))
        self.assertEqual(t["img.png"][0], 0)
        self.assertEqual(t["notes.txt"][0], 0)               # not source code
        self.assertEqual(t["backend/api/r.py"][0], 1)         # route file

    def test_hubs_only_rank_files_no_earlier_rule_claimed(self):
        deg = {"backend/tests/t.py": 999, "x/y.py": 50, "backend/agents/b.py": 40, "backend/core/a.py": 10}
        t = notes.assign_tiers(self.files(), TIERS, deg, ())
        self.assertEqual(t["backend/tests/t.py"][0], 4)       # a test that is a hub stays a test
        self.assertEqual(t["x/y.py"], (1, "hubs"))
        self.assertEqual(t["backend/agents/b.py"], (1, "hubs"))   # top 2 beat the later agents rule
        self.assertEqual(t["backend/core/a.py"][1], "core")

    def test_a_language_filter_is_an_and(self):
        cfg = {"rules": [{"tier": 1, "globs": ["**"], "languages": ["python"]}], "default": {"tier": 3, "languages": ["python", "javascript"], "other": 0}}
        t = notes.assign_tiers([rec("a.py"), rec("b.js", lang="javascript")], cfg)
        self.assertEqual((t["a.py"][0], t["b.js"][0]), (1, 3))

    def test_the_shipped_config_is_sane(self):
        cfg = notes.load_tiers(ROOT)
        census_ = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        t = notes.assign_tiers(notes.census_files(census_), cfg, {}, {r["file"] for r in census_.get("routes", []) if r.get("file")})
        self.assertEqual(t["protocol/v1/hello.json"][0], 0)
        self.assertEqual(t["backend/api/routes/tasks.py"][0], 1)
        self.assertEqual(t["m2c/src/m2c/sandbox/__init__.py"][0], 1)
        self.assertEqual(t["backend/tests/unit/loop_testkit.py"][0], 4)
        self.assertEqual(t["README.md"][0], 0)
        self.assertTrue(all(0 <= v[0] <= 4 for v in t.values()))


class SymbolRuleTests(unittest.TestCase):
    def setUp(self):
        self.r = rec("a.py", funcs=[
            sym("big", 1, 20, H("1")), sym("_tiny", 30, 31, H("2"), visibility="private"),
            sym("_complex", 40, 41, H("3"), visibility="private", cc=7), sym("_deco", 50, 51, H("4"), visibility="private", decorators=["route"]),
            sym("pub", 60, 61, H("5")), sym("big.inner", 70, 90, H("6"), kind="nested"), sym("t", 95, 99, H("7"), test=True)],
            classes=[{"name": "K", "qual": "K", "start": 100, "end": 130, "loc": 31, "hash": H("8"), "bases": ["Base"]}])

    def quals(self, tier):
        return [q for q, _, _ in notes.wanted_symbols(self.r, tier, TIERS)]

    def test_tier_2_takes_big_complex_decorated_or_public(self):
        self.assertEqual(self.quals(2), ["big", "_complex", "_deco", "pub", "K"])    # not _tiny, not nested, not tests

    def test_tier_1_is_pickier_than_public(self):
        self.assertEqual(self.quals(1), ["big", "_complex", "_deco", "K"])             # `pub` is only 2 lines

    def test_tier_4_and_0_want_no_symbols(self):
        self.assertEqual(self.quals(4), [])
        self.assertEqual(self.quals(0), [])

    def test_javascript_exports_count_at_tier_3(self):
        js = rec("a.js", lang="javascript", funcs=[sym("go", 1, 3, H("1"), exported=True, visibility="private"), sym("hid", 5, 6, H("2"), exported=False, visibility="private")])
        self.assertEqual([q for q, _, _ in notes.wanted_symbols(js, 3, TIERS)], ["go"])

    def test_signature_reads_like_python(self):
        s = sym("f", 1, 2, H("1"), params=[{"name": "a", "annotation": "int"}, {"name": "b", "default": "1"}], returns="str", **{"async": True})
        self.assertEqual(notes.signature(s, "function"), "async f(a: int, b = 1) -> str")
        self.assertEqual(notes.signature({"name": "K", "bases": ["A", "B"]}, "class"), "class K(A, B)")


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.ctx = make_ctx([rec("backend/core/a.py", funcs=[sym("f", 10, 20, H("1"))])])

    def v(self, note, name=None, ctx=True):
        return notes.validate_note(note, name or notes.note_filename(note.get("path", "x")) if isinstance(note, dict) else None, self.ctx if ctx else None)

    def test_a_good_note_has_no_problems(self):
        p = self.v(good_note(symbols=[nsym("f", 10, 20, H("1"), confidence="high", evidence=["12-14", "15"], params=[{"name": "x", "desc": "y"}], returns="int", raises=["ValueError"])]))
        self.assertEqual((p.errors, p.warnings), ([], []))

    def test_required_fields(self):
        for k in ("schema", "path", "blob", "commit", "written", "tier", "summary"):
            n = good_note()
            del n[k]
            self.assertTrue(self.v(n, "x.json", ctx=False).errors, k)

    def test_types_and_formats(self):
        for patch in ({"blob": "xyz"}, {"commit": "A" * 40}, {"written": "yesterday"}, {"tier": 9}, {"tier": True}, {"tier": "1"}, {"summary": ""}, {"schema": 2},
                      {"symbols": "no"}, {"blocks": {}}, {"how_it_works": "text"}, {"how_it_works": [1]}):
            self.assertTrue(self.v({**good_note(), **patch}).errors, patch)
        self.assertTrue(notes.validate_note([], None).errors)

    def test_unknown_keys_and_long_text_only_warn(self):
        n = good_note(extra_thing=1, summary="x" * 300, symbols=[nsym("f", 10, 20, H("1"), mystery=True, summary="y" * 200)])
        p = self.v(n)
        self.assertEqual(p.errors, [])
        self.assertEqual(len(p.warnings), 4)

    def test_file_name_must_match_the_path(self):
        self.assertTrue(notes.validate_note(good_note(), "wrong.json", self.ctx).errors)
        self.assertFalse(notes.validate_note(good_note(), "backend__core__a.py.json", self.ctx).errors)

    def test_symbol_checks(self):
        bad = [nsym("f", 20, 10), nsym("f", 0, 5), nsym("f", 1, 2, "nothex"), nsym("f", 1, 2, confidence="sure"), nsym("f", 1, 2, evidence=["x"]),
               nsym("f", 1, 2, evidence=["9-3"]), nsym("f", 1, 2, params=["a"]), {"qual": "f", "start": 1, "end": 2}]
        for s in bad:
            self.assertTrue(self.v(good_note(symbols=[s])).errors, s)
        self.assertTrue(self.v(good_note(symbols=[nsym("f", 10, 20), nsym("f", 10, 20)])).errors)             # listed twice

    def test_unknown_symbol_is_an_error_at_the_census_commit_and_a_warning_later(self):
        n = good_note(symbols=[nsym("ghost", 1, 2)])
        p = self.v(n)
        self.assertTrue(any("ghost" in e for e in p.errors))                       # a hallucination
        p = self.v(good_note(commit=C2, symbols=[nsym("ghost", 1, 2)]))
        self.assertEqual(p.errors, [])
        self.assertTrue(any("ghost" in w for w in p.warnings))                     # the code moved on

    def test_unknown_file_is_an_error_at_the_census_commit_and_a_warning_later(self):
        self.assertTrue(self.v(good_note(path="nope.py")).errors)
        p = self.v(good_note(path="nope.py", commit=C2))
        self.assertEqual(p.errors, [])
        self.assertTrue(p.warnings)

    def test_blocks(self):
        ok = {"lines": "1-5", "anchor": "def f", "title": "T", "text": "x"}
        self.assertEqual(self.v(good_note(blocks=[ok])).errors, [])
        for patch in ({"lines": "5-1"}, {"lines": "7"}, {"anchor": ""}, {"title": 3}):
            self.assertTrue(self.v(good_note(blocks=[{**ok, **patch}])).errors, patch)
        self.assertTrue(any("file has" in w for w in self.v(good_note(blocks=[{**ok, "lines": "90-500"}])).warnings))

    def test_secrets_are_refused(self):
        for text in ("-----BEGIN RSA PRIVATE KEY-----", "AKIAABCDEFGHIJKLMNOP", "ghp_" + "a" * 36, "sk-" + "a" * 30,
                     'api_key = "abcdefghijklmnopqrstuvwxyz"', "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fw"):
            self.assertTrue(any("secret" in e for e in self.v(good_note(gotchas=[text])).errors), text)
        for text in ("Reads the API key from the environment", "task-based routing with risk-aware policies", "token budget per step"):
            self.assertEqual(self.v(good_note(gotchas=[text])).errors, [], text)

    def test_the_schema_example_given_to_copilot_validates(self):
        md = notes.schema_markdown()
        self.assertFalse(re.search(r"@[a-z_]+@", md))                                  # every @limit@ was replaced
        for k, v in notes.LIMITS.items():
            if k in ("summary", "purpose", "sym_summary", "block_text"):
                self.assertIn(str(v), md)
        example = re.search(r"```json\n(.*?)\n```", md, re.S).group(1).replace("<copy from the todo entry>", "e" * 40)
        n = json.loads(example)
        n["symbols"][0]["hash"] = "e" * 10
        p = notes.validate_note(n, notes.note_filename(n["path"]), None)
        self.assertEqual((p.errors, p.warnings), ([], []))


class FreshnessTests(unittest.TestCase):
    def ctx(self, blob=B1, f_hash=H("1")):
        return make_ctx([rec("backend/core/a.py", funcs=[sym("f", 10, 20, f_hash), sym("g", 30, 40, H("2"))])], blobs={"backend/core/a.py": blob})

    def test_fresh_when_blob_and_hashes_match(self):
        n = good_note(symbols=[nsym("f", 10, 20, H("1")), nsym("g", 30, 40, H("2"))])
        ev = notes.evaluate_note(n, self.ctx())
        self.assertEqual((ev["file"], ev["symbols"]), ("fresh", {"f": "fresh", "g": "fresh"}))

    def test_a_changed_symbol_is_stale_and_so_is_its_file(self):
        n = good_note(symbols=[nsym("f", 10, 20, H("1")), nsym("g", 30, 40, H("2"))])
        ev = notes.evaluate_note(n, self.ctx(f_hash=H("9")))
        self.assertEqual((ev["file"], ev["symbols"]["f"], ev["symbols"]["g"]), ("stale", "stale", "fresh"))

    def test_a_changed_blob_makes_the_file_stale_even_if_every_symbol_is_fresh(self):
        n = good_note(symbols=[nsym("f", 10, 20, H("1"))])
        ev = notes.evaluate_note(n, self.ctx(blob=B2))
        self.assertEqual((ev["file"], ev["blob"], ev["symbols"]["f"]), ("stale", "changed", "fresh"))

    def test_a_missing_symbol_is_broken(self):
        ev = notes.evaluate_note(good_note(symbols=[nsym("gone", 1, 2, H("1"))]), self.ctx())
        self.assertEqual(ev["symbols"]["gone"], "broken")
        self.assertEqual(ev["file"], "stale")

    def test_a_null_hash_is_stale_not_fresh(self):
        ev = notes.evaluate_note(good_note(symbols=[nsym("f", 10, 20, None)]), self.ctx())
        self.assertEqual(ev["symbols"]["f"], "stale")

    def test_a_file_that_is_not_in_the_census_is_an_orphan(self):
        self.assertTrue(notes.evaluate_note(good_note(path="old.py"), self.ctx()).get("orphan"))

    def test_without_git_freshness_follows_the_commit(self):
        ctx = self.ctx()
        ctx.blobs = None
        n = good_note(symbols=[nsym("f", 10, 20, H("1"))])
        self.assertEqual(notes.evaluate_note(n, ctx)["blob"], "same")
        self.assertEqual(notes.evaluate_note({**n, "commit": C2}, ctx)["blob"], "changed")


class RepairTests(unittest.TestCase):
    def ctx(self, blob=B1, f=(10, 20, H("1"))):
        return make_ctx([rec("backend/core/a.py", funcs=[sym("f", f[0], f[1], f[2])])], blobs={"backend/core/a.py": blob})

    def test_null_hash_is_filled_from_the_census_when_the_file_is_unchanged(self):
        n = notes.repair_note(good_note(symbols=[nsym("f", 10, 20)]), self.ctx())
        self.assertEqual(n["symbols"][0]["hash"], H("1"))

    def test_null_hash_stays_null_when_the_file_changed_and_there_is_no_earlier_copy(self):
        n = notes.repair_note(good_note(symbols=[nsym("f", 10, 20)]), self.ctx(blob=B2))
        self.assertIsNone(n["symbols"][0]["hash"])

    def test_the_earlier_copy_supplies_the_hash_when_it_has_the_same_blob_and_lines(self):
        prev = good_note(symbols=[nsym("f", 10, 20, H("7"))])
        n = notes.repair_note(good_note(symbols=[nsym("f", 10, 20)]), self.ctx(blob=B2, f=(10, 20, H("9"))), prev)
        self.assertEqual(n["symbols"][0]["hash"], H("7"))          # the code changed since: 7 != 9, so it will show as stale
        self.assertEqual(notes.evaluate_note(n, self.ctx(blob=B2, f=(10, 20, H("9"))))["symbols"]["f"], "stale")
        other = notes.repair_note(good_note(symbols=[nsym("f", 11, 20)]), self.ctx(blob=B2), prev)     # different lines: not the same symbol version
        self.assertIsNone(other["symbols"][0]["hash"])
        newer = notes.repair_note(good_note(blob=B2, symbols=[nsym("f", 10, 20)]), self.ctx(blob=B1), prev)   # different blob: no carry-over
        self.assertEqual(newer["symbols"][0]["hash"], None)

    def test_an_unchanged_symbol_is_moved_to_its_census_lines_and_its_evidence_moves_with_it(self):
        n = notes.repair_note(good_note(blob=B2, symbols=[nsym("f", 10, 20, H("1"), evidence=["12-14", "20", "50"])]), self.ctx(blob=B2, f=(15, 25, H("1"))))
        s = n["symbols"][0]
        self.assertEqual((s["start"], s["end"], s["evidence"]), (15, 25, ["17-19", "25", "50"]))     # 50 is outside the symbol: left alone

    def test_a_changed_symbol_keeps_its_old_lines_and_hash(self):
        n = notes.repair_note(good_note(symbols=[nsym("f", 10, 20, H("1"))]), self.ctx(f=(15, 30, H("9"))))
        s = n["symbols"][0]
        self.assertEqual((s["start"], s["end"], s["hash"]), (10, 20, H("1")))

    def test_the_input_is_not_modified(self):
        n = good_note(symbols=[nsym("f", 10, 20)])
        before = copy.deepcopy(n)
        notes.repair_note(n, self.ctx())
        self.assertEqual(n, before)


class IndexAndTodoTests(unittest.TestCase):
    def setUp(self):
        self.files = [rec("backend/core/a.py", funcs=[sym("f", 10, 30, H("1")), sym("g", 40, 60, H("2"))], git={"commits": 9}),
                      rec("backend/core/b.py", funcs=[sym("h", 1, 20, H("3"))], git={"commits": 2}),
                      rec("backend/agents/c.py", funcs=[sym("k", 1, 20, H("4"))]),
                      rec("backend/tests/t.py", test=True, funcs=[sym("t", 1, 20, H("5"))]),
                      rec("old/z.py")]
        self.blobs = {"backend/core/a.py": B1, "backend/core/b.py": B1, "backend/agents/c.py": B1, "backend/tests/t.py": B1}
        self.ctx = make_ctx(self.files[:4], self.blobs, degree={"backend/core/b.py": 7})

    def repaired(self, *ns):
        return {n["path"]: notes.repair_note(n, self.ctx) for n in ns}

    def test_index_counts_tiers_folders_and_symbols(self):
        ns = self.repaired(good_note("backend/core/a.py", symbols=[nsym("f", 10, 30)]), good_note("backend/agents/c.py", tier=2), good_note("old/z.py"))
        idx = notes.build_notes_index(self.ctx, ns)
        self.assertEqual({t: (r["files"], r["noted"], r["fresh"], r["missing"]) for t, r in idx["tiers"].items()},
                         {"1": (2, 1, 1, 1), "2": (1, 1, 1, 0), "3": (0, 0, 0, 0), "4": (1, 0, 0, 1)})
        self.assertEqual(idx["totals"]["files"], 3)                                    # tier 4 is not part of the totals
        self.assertEqual(idx["tiers"]["1"]["symbols_wanted"], 3)                       # f, g, h
        self.assertEqual(idx["tiers"]["1"]["symbols_covered"], 1)                      # only f is documented
        self.assertEqual(idx["folders"]["backend/core"], {"files": 2, "noted": 1, "fresh": 1, "stale": 0})
        self.assertEqual(idx["folders"]["backend"]["files"], 3)
        self.assertEqual(idx["orphans"], ["old/z.py"])
        self.assertEqual(idx["files"]["backend/core/a.py"]["status"], "fresh")
        self.assertNotIn("old/z.py", idx["files"])

    def test_index_is_json_serialisable_and_deterministic(self):
        ns = self.repaired(good_note("backend/core/a.py", symbols=[nsym("f", 10, 30)]))
        self.assertEqual(notes.dumps(notes.build_notes_index(self.ctx, ns)), notes.dumps(notes.build_notes_index(self.ctx, copy.deepcopy(ns))))

    def test_todo_orders_by_tier_then_links_then_churn(self):
        t = notes.build_todo(self.ctx, {}, tier_max=2, limit=10)
        self.assertEqual([f["path"] for f in t["files"]], ["backend/core/b.py", "backend/core/a.py", "backend/agents/c.py"])
        self.assertEqual(t["files_needing_work"], 3)
        self.assertEqual([f["reason"] for f in t["files"]], ["new"] * 3)

    def test_todo_respects_the_tier_and_never_lists_tier_4_unless_asked(self):
        self.assertEqual({f["tier"] for f in notes.build_todo(self.ctx, {}, 1, 10)["files"]}, {1})
        self.assertIn("backend/tests/t.py", [f["path"] for f in notes.build_todo(self.ctx, {}, 4, 10)["files"]])
        t4 = [f for f in notes.build_todo(self.ctx, {}, 4, 10)["files"] if f["tier"] == 4][0]
        self.assertEqual(t4["symbols"], [])

    def test_todo_gives_copilot_the_blob_commit_and_the_symbol_facts(self):
        f = notes.build_todo(self.ctx, {}, 1, 1)["files"][0]
        self.assertEqual((f["blob"], f["commit"], f["write_blocks"], f["note_file"]), (B1, C1, True, "backend__core__b.py.json"))
        self.assertEqual({k: f["symbols"][0][k] for k in ("qual", "start", "end", "hash", "why")}, {"qual": "h", "start": 1, "end": 20, "hash": H("3"), "why": "new"})

    def test_todo_skips_fresh_files_and_lists_only_what_changed(self):
        ns = self.repaired(good_note("backend/core/a.py", symbols=[nsym("f", 10, 30), nsym("g", 40, 60)]))
        self.assertNotIn("backend/core/a.py", [f["path"] for f in notes.build_todo(self.ctx, ns, 1, 10)["files"]])
        # the code of g changes and a blob moves on
        files = copy.deepcopy(self.files[:4])
        files[0]["functions"][1]["hash"] = H("9")
        files[0]["functions"].append(sym("newfn", 70, 90, H("8")))
        ctx = make_ctx(files, {**self.blobs, "backend/core/a.py": B2}, degree={"backend/core/b.py": 7})
        t = notes.build_todo(ctx, ns, 1, 10)
        a = [f for f in t["files"] if f["path"] == "backend/core/a.py"][0]
        self.assertEqual(a["reason"], "changed")
        self.assertEqual([(s["qual"], s["why"]) for s in a["symbols"]], [("g", "changed"), ("newfn", "new")])
        self.assertEqual(a["fresh_symbols_kept"], 1)

    def test_todo_lists_removed_symbols_and_stale_symbols_that_are_not_wanted(self):
        ns = self.repaired(good_note("backend/core/b.py", symbols=[nsym("h", 1, 20), nsym("vanished", 30, 40, H("6"))]))
        b = [f for f in notes.build_todo(self.ctx, ns, 1, 10)["files"] if f["path"] == "backend/core/b.py"][0]
        self.assertEqual(b["removed"], ["vanished"])
        self.assertEqual(b["reason"], "fix")
        files = copy.deepcopy(self.files[:4])
        files[1]["functions"].append(sym("_small", 50, 51, H("7"), visibility="private"))        # documented although tier 1 does not want it
        ctx = make_ctx(files, self.blobs, degree={"backend/core/b.py": 7})
        ns = {"backend/core/b.py": good_note("backend/core/b.py", symbols=[nsym("h", 1, 20, H("3")), nsym("_small", 50, 51, H("0"))])}
        b = [f for f in notes.build_todo(ctx, ns, 1, 10)["files"] if f["path"] == "backend/core/b.py"][0]
        self.assertEqual([(s["qual"], s["why"]) for s in b["symbols"]], [("_small", "changed")])

    def test_a_batch_stops_at_the_symbol_budget_but_always_takes_the_first_file(self):
        t = notes.build_todo(self.ctx, {}, 2, limit=10, max_symbols=1)
        self.assertEqual([f["path"] for f in t["files"]], ["backend/core/b.py"])
        self.assertEqual(t["files_needing_work"], 3)
        self.assertEqual(len(notes.build_todo(self.ctx, {}, 2, limit=2)["files"]), 2)


class IngestTests(unittest.TestCase):
    """The folder-level behaviour: a site root and a MiniMe folder (no git) in a temp dir."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root, self.mm = self.tmp / "book", self.tmp / "MiniMe"
        (self.root / "data").mkdir(parents=True)
        (self.root / "content").mkdir()
        (self.root / "data" / "index").mkdir()
        self.files = [rec("backend/core/a.py", funcs=[sym("f", 10, 30, H("1"))]), rec("backend/core/b.py", funcs=[sym("h", 1, 20, H("3"))])]
        self.write_census(self.files)
        (self.root / "content" / "notes-tiers.json").write_text(json.dumps(TIERS), encoding="utf-8")
        self.src = self.mm / notes.NOTES_SUBDIR
        self.src.mkdir(parents=True)
        self.logs = []

    def write_census(self, files, commit=C1):
        (self.root / "data" / "census.json").write_text(json.dumps(census(files, commit)), encoding="utf-8")

    def put(self, note, where=None, name=None, crlf=False):
        d = where or self.src
        text = json.dumps(note, indent=1)
        (d / (name or notes.note_filename(note["path"]))).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))

    def run_ingest(self, **kw):
        self.logs = []
        return notes.ingest(self.root, kw.pop("minime", self.mm), log=self.logs.append, **kw)

    def data(self, name="backend__core__a.py.json"):
        return json.loads((self.root / "data" / "notes" / name).read_text(encoding="utf-8"))

    def test_ingest_copies_valid_notes_fills_hashes_and_writes_the_index(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.assertEqual(self.run_ingest(), 0)
        self.assertEqual(self.data()["symbols"][0]["hash"], H("1"))
        idx = json.loads((self.root / "data" / "index" / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual((idx["commit"], idx["totals"]["noted"], idx["files"]["backend/core/a.py"]["status"]), (C1, 1, "fresh"))
        self.assertFalse((self.root / "data" / "notes" / "_todo.json").exists())

    def test_ingest_is_idempotent_and_check_agrees(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.run_ingest()
        before = {p.name: p.read_bytes() for p in (self.root / "data").rglob("*") if p.is_file()}
        self.assertEqual(self.run_ingest(), 0)
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / "data").rglob("*") if p.is_file()}, before)
        self.assertEqual(self.run_ingest(check=True), 0)
        self.assertIn("notes are current", self.logs)

    def test_check_fails_when_something_is_out_of_date_and_changes_nothing(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.assertEqual(self.run_ingest(check=True), 1)
        self.assertFalse((self.root / "data" / "notes").exists())

    def test_a_malformed_note_blocks_everything_unless_skipped(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        (self.src / "backend__core__b.py.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(self.run_ingest(), 1)
        self.assertFalse((self.root / "data" / "notes").exists())
        self.assertTrue(any("invalid JSON" in l for l in self.logs))
        self.assertEqual(self.run_ingest(skip_invalid=True), 0)
        self.assertTrue((self.root / "data" / "notes" / "backend__core__a.py.json").exists())

    def test_warnings_never_block(self):
        self.put(good_note(summary="x" * 500, odd=1, symbols=[nsym("f", 10, 30)]))
        self.assertEqual(self.run_ingest(), 0)
        self.assertTrue(any(l.startswith("warning:") for l in self.logs))

    def test_a_note_for_a_symbol_that_does_not_exist_is_malformed(self):
        self.put(good_note(symbols=[nsym("ghost", 1, 2)]))
        self.assertEqual(self.run_ingest(), 1)

    def test_an_older_note_does_not_overwrite_a_newer_committed_one(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)], written="2026-11-20", summary="Newer."), where=self._data_dir())
        self.put(good_note(symbols=[nsym("f", 10, 30)], written="2026-11-10", summary="Older."))
        self.assertEqual(self.run_ingest(), 0)
        self.assertEqual(self.data()["summary"], "Newer.")
        self.assertTrue(any("older than the committed copy" in l for l in self.logs))

    def _data_dir(self):
        d = self.root / "data" / "notes"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_without_a_notes_folder_the_committed_notes_are_kept(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.run_ingest()
        shutil.rmtree(self.src)
        self.assertEqual(self.run_ingest(), 0)
        self.assertTrue((self.root / "data" / "notes" / "backend__core__a.py.json").exists())
        self.assertEqual(self.run_ingest(minime=None, check=True), 0)

    def test_orphans_are_kept_unless_pruned(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.put(good_note("old/gone.py", commit=C2, tier=3))
        self.assertEqual(self.run_ingest(), 0)
        self.assertTrue((self.root / "data" / "notes" / "old__gone.py.json").exists())
        idx = json.loads((self.root / "data" / "index" / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["orphans"], ["old/gone.py"])
        shutil.rmtree(self.src)
        self.assertEqual(self.run_ingest(prune=True), 0)
        self.assertFalse((self.root / "data" / "notes" / "old__gone.py.json").exists())
        self.assertTrue((self.root / "data" / "notes" / "backend__core__a.py.json").exists())

    def test_crlf_notes_and_underscore_files_are_handled(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]), crlf=True)
        (self.src / "_todo.json").write_text("{ whatever", encoding="utf-8")
        (self.src / "_SCHEMA.md").write_text("# x", encoding="utf-8")
        self.assertEqual(self.run_ingest(), 0)

    def test_notes_are_written_with_lf_only(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]), crlf=True)
        self.run_ingest()
        for p in (self.root / "data").rglob("*.json"):
            if p.name != "census.json":
                self.assertNotIn(b"\r", p.read_bytes(), p.name)

    def test_a_hand_edited_bad_committed_note_blocks_ingest(self):
        self.put(good_note(symbols=[nsym("f", 10, 30)]))
        self.run_ingest()
        p = self.root / "data" / "notes" / "backend__core__a.py.json"
        n = json.loads(p.read_text(encoding="utf-8"))
        n["blob"] = "oops"
        p.write_text(json.dumps(n), encoding="utf-8")
        self.assertEqual(self.run_ingest(), 1)
        self.assertTrue(any("data/notes/" in l for l in self.logs))


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitTests(unittest.TestCase):
    """A real throw-away repository: blob ids come from git objects, and an edited file flips its note to stale."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.mm = self.tmp / "MiniMe"
        (self.mm / "backend" / "core").mkdir(parents=True)
        self.git("init", "-q")

    def git(self, *a):
        r = subprocess.run(["git", "-C", str(self.mm), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *a],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def commit(self, text):
        (self.mm / "backend" / "core" / "a.py").write_bytes(text.encode("utf-8"))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")
        return self.git("rev-parse", "HEAD"), self.git("rev-parse", "HEAD:backend/core/a.py")

    def test_ls_tree_blobs_matches_git_and_ignores_the_working_tree(self):
        commit, blob = self.commit("def f():\n    return 1\n")
        self.assertEqual(notes.ls_tree_blobs(self.mm, commit), {"backend/core/a.py": blob})
        (self.mm / "backend" / "core" / "a.py").write_bytes(b"def f():\r\n    return 1\r\n")          # a Windows checkout: CRLF in the working tree
        self.assertEqual(notes.ls_tree_blobs(self.mm, "HEAD"), {"backend/core/a.py": blob})
        self.assertEqual(self.git("hash-object", "--no-filters", "backend/core/a.py") != blob, True)    # the working file is NOT the committed blob
        self.assertIsNone(notes.ls_tree_blobs(self.mm, "f" * 40))
        self.assertIsNone(notes.ls_tree_blobs(self.tmp / "nope", "HEAD"))

    def test_an_edit_in_minime_flips_exactly_that_note_to_stale(self):
        commit1, blob1 = self.commit("def f():\n    return 1\n\n\ndef g():\n    return 2\n")
        files1 = [rec("backend/core/a.py", funcs=[sym("f", 1, 2, H("1")), sym("g", 5, 6, H("2"))])]
        ctx = notes.build_ctx(ROOT, self.mm, census(files1, commit1))
        self.assertEqual(ctx.blobs, {"backend/core/a.py": blob1})
        note = notes.repair_note(good_note(commit=commit1, blob=blob1, symbols=[nsym("f", 1, 2), nsym("g", 5, 6)]), ctx)
        ev = notes.evaluate_note(note, ctx)
        self.assertEqual((ev["file"], ev["symbols"]), ("fresh", {"f": "fresh", "g": "fresh"}))
        self.assertEqual([s["hash"] for s in note["symbols"]], [H("1"), H("2")])

        # f is edited, g is unchanged but moves down by two lines
        commit2, blob2 = self.commit("def f():\n    x = 1\n    y = 2\n    return x + y\n\n\ndef g():\n    return 2\n")
        files2 = [rec("backend/core/a.py", funcs=[sym("f", 1, 4, H("9")), sym("g", 7, 8, H("2"))])]
        ctx2 = notes.build_ctx(ROOT, self.mm, census(files2, commit2))
        self.assertEqual(ctx2.blobs, {"backend/core/a.py": blob2})
        n2 = notes.repair_note(note, ctx2, note)
        ev2 = notes.evaluate_note(n2, ctx2)
        self.assertEqual((ev2["file"], ev2["blob"], ev2["symbols"]), ("stale", "changed", {"f": "stale", "g": "fresh"}))
        g = n2["symbols"][1]
        self.assertEqual((g["start"], g["end"]), (7, 8))                    # g moved with the code
        todo = notes.build_todo(ctx2, {"backend/core/a.py": n2}, 3, 5)      # the real tier config puts this path at tier 3
        entry = todo["files"][0]
        self.assertEqual((entry["reason"], entry["blob"], entry["commit"]), ("changed", blob2, commit2))
        self.assertEqual([(s["qual"], s["why"]) for s in entry["symbols"]], [("f", "changed")])

    def test_the_census_commit_missing_from_minime_falls_back_to_head_with_a_warning(self):
        self.commit("x = 1\n")
        ctx = notes.build_ctx(ROOT, self.mm, census([rec("backend/core/a.py")], "c" * 40))
        self.assertIsNotNone(ctx.blobs)
        self.assertTrue(ctx.warnings)


class TodoCommandTests(unittest.TestCase):
    """`notes.py todo` end to end on a throw-away MiniMe repo: it writes the schema and the batch, and puts a stale note where Copilot can edit it."""

    def test_todo_writes_schema_batch_and_the_existing_note_of_a_stale_file(self):
        if not shutil.which("git"):
            self.skipTest("git is not installed")
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        mm, root = tmp / "MiniMe", tmp / "book"

        def git(*a):
            r = subprocess.run(["git", "-C", str(mm), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout.strip()

        (mm / "backend" / "core").mkdir(parents=True)
        git("init", "-q")
        (mm / "backend" / "core" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (mm / "backend" / "core" / "b.py").write_text("def h():\n    return 3\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", "c")
        commit, blob_a = git("rev-parse", "HEAD"), git("rev-parse", "HEAD:backend/core/a.py")
        (root / "data").mkdir(parents=True)
        (root / "content").mkdir()
        files = [rec("backend/core/a.py", funcs=[sym("f", 1, 2, H("1"))]), rec("backend/core/b.py", funcs=[sym("h", 1, 2, H("3"))])]
        (root / "data" / "census.json").write_text(json.dumps(census(files, commit)), encoding="utf-8")
        (root / "content" / "notes-tiers.json").write_text(json.dumps(TIERS), encoding="utf-8")
        # a committed note for a.py written against an OLDER blob: stale, and it lives only in data/notes
        (root / "data" / "notes").mkdir()
        old = good_note("backend/core/a.py", commit=C2, blob=B2, symbols=[nsym("f", 1, 2, H("0"))])
        (root / "data" / "notes" / "backend__core__a.py.json").write_text(json.dumps(old), encoding="utf-8")

        self.assertEqual(notes.main(["--root", str(root), "todo", "--minime", str(mm), "--tier", "1", "--limit", "5"]), 0)
        out = mm / notes.NOTES_SUBDIR
        todo = json.loads((out / "_todo.json").read_text(encoding="utf-8"))
        self.assertEqual({f["path"]: f["reason"] for f in todo["files"]}, {"backend/core/a.py": "changed", "backend/core/b.py": "new"})
        a = [f for f in todo["files"] if f["path"] == "backend/core/a.py"][0]
        self.assertEqual((a["blob"], a["commit"]), (blob_a, commit))
        self.assertEqual([(s["qual"], s["hash"], s["why"]) for s in a["symbols"]], [("f", H("1"), "changed")])
        self.assertIn("# Atlas notes", (out / "_SCHEMA.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((out / "backend__core__a.py.json").read_text(encoding="utf-8"))["summary"], "Does a thing.")   # the stale note was put there
        self.assertFalse((out / "backend__core__b.py.json").exists())                                                     # a new file gets no placeholder


class WiringTests(unittest.TestCase):
    """P11 is part of the update routine, the docs and CI, and the committed notes are valid."""

    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_update_all_ingests_and_checks_the_notes(self):
        src = self.read("scripts/update_all.py")
        for needle in ('"scripts/notes.py", "ingest"', '"--check"', "test_notes.py"):
            self.assertIn(needle, src)

    def test_updating_md_carries_the_copilot_prompts(self):
        md = self.read("UPDATING.md")
        for needle in ("Step 2b", "notes.py todo", "_todo.json", "notes.py ingest"):
            self.assertIn(needle, md)

    def test_ci_runs_the_notes_tests_and_validation(self):
        wf = self.read(".github/workflows/site-check.yml")
        self.assertIn("test_notes.py", wf)
        self.assertIn("notes.py validate", wf)

    def test_every_committed_note_validates(self):
        census_ = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        ctx = notes.build_ctx(ROOT, None, census_)
        found, bad = notes.read_notes_dir(ROOT / "data" / "notes")
        self.assertEqual(bad, {})
        for name, n in found.items():
            p = notes.validate_note(n, name, ctx)
            self.assertEqual(p.errors, [], name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
