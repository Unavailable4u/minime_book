#!/usr/bin/env python3
"""
test_dataviews.py -- tests for the Infra, Data model and Tables pages (P18). Standard library only; the JavaScript tests need `node`
(skipped without it).

What is checked
  * data/code/infra.json built from the census slice the old infra.html was built from holds the same information as that page:
    every service, Dockerfile, CI job and step, the dependency counts, and all 123 environment variable rows (name, number of files,
    first file, in .env.example). The old page is frozen in scripts/golden/p18_infra_old.json, taken from infra.html at the commit before P18.
  * infra.json adds what the old page could not show: every file that reads a variable (and which are tests), where it is documented,
    the comment next to it, and names in an .env.example that no code reads. It holds names only, never a value.
  * assets/js/dataviews.js (the pure helpers the pages share) runs under Node with no DOM and no network: KPIs, variable families,
    table rows, hashes, relationships, column flags, drift sentences, the ER layout (deterministic, boxes never overlap, an edge only
    where a foreign key is declared), and the filter / sort / count helpers tables.html uses.
  * the committed infra.json is consistent with the committed census.
  * the pages are small shells (no data baked in), every module they import exists and parses, text goes in as text (no innerHTML),
    and tables.html no longer carries an inline script.

    python scripts/test_dataviews.py
"""
import importlib.util
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
GOLD = ROOT / "scripts" / "golden"
JS = ROOT / "assets" / "js"
NODE = shutil.which("node")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ra = load("refresh_atlas")


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def run_node(script):
    """Run `script` (an ES module body) next to copies of the modules dataviews.js imports; return its stdout parsed as JSON."""
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "explorer").mkdir()
        for f in ("dataviews.js", "codepages.js", "links.js"):
            shutil.copy(JS / f, tmp / f)
        shutil.copy(JS / "explorer" / "router.js", tmp / "explorer" / "router.js")
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (tmp / "t.js").write_text(script, encoding="utf-8")
        r = subprocess.run([NODE, "t.js"], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError(f"node failed:\n{r.stderr}")
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class GoldenInfra(unittest.TestCase):
    """infra.json, built from the census slice the old page was built from, says what the old page said."""

    @classmethod
    def setUpClass(cls):
        cls.slice = jload(GOLD / "p18_census_slice.json")
        cls.old = jload(GOLD / "p18_infra_old.json")
        cls.doc = ra.build_infra(cls.slice)

    def test_every_service_card_of_the_old_page_is_there(self):
        new = []
        for s in self.doc["services"]:
            new.append([s["name"], [f"port {p}" for p in s["ports"]] + [f"needs {d}" for d in s["depends_on"]] + s["env_names"],
                        "Built from its Dockerfile" if s["build"] else (f"Image {s['image']}" if s["image"] else "")])
        old = [[c["name"], c["pills"], c["text"]] for c in self.old["services"][:len(new)]]
        self.assertEqual(old, new)

    def test_every_dockerfile_card_of_the_old_page_is_there(self):
        old = self.old["services"][len(self.doc["services"]):]
        self.assertEqual(len(old), len(self.doc["dockerfiles"]))
        for o, d in zip(old, self.doc["dockerfiles"]):
            self.assertEqual(o["name"], d["name"])
            self.assertEqual(o["pills"], d["stages"], "one pill per FROM line, in order")
            self.assertIn(f"Port {d['expose'][0]}", o["text"])
            self.assertIn(d["cmd"], o["text"])

    def test_every_ci_job_and_step_of_the_old_page_is_there(self):
        new = [[j["name"], [st["text"][:70] for st in j["steps"]]] for wf in self.doc["ci"] for j in wf["jobs"]]
        self.assertEqual([[j["name"], j["steps"]] for j in self.old["ci_jobs"]], new)

    def test_a_pinned_step_keeps_its_short_commit_apart_from_the_text(self):
        pinned = [st for wf in self.doc["ci"] for j in wf["jobs"] for st in j["steps"] if "pin" in st]
        self.assertTrue(pinned)
        for st in pinned:
            self.assertRegex(st["pin"], r"^[0-9a-f]{7}$")
            self.assertNotIn("@", st["text"])

    def test_dependency_counts_equal_the_old_headings(self):
        by = {m["file"]: m for m in self.doc["dependencies"]}
        count = lambda f, g=None: sum(len(x["items"]) for x in by[f]["groups"] if g is None or x["title"] == g)
        heads = {h["title"]: h["n_pills"] for h in self.old["dep_headings"]}
        self.assertEqual(heads["Backend (136)"], count("backend/requirements.txt"))
        self.assertEqual(heads["Frontend"], count("frontend/package.json", "dependencies"))
        self.assertEqual(heads["Dev tools"], count("frontend/package.json", "devDependencies"))
        self.assertEqual(heads["Daemon (3)"], count("daemon/requirements.txt"))

    def test_a_manifest_the_census_kept_only_the_head_of_is_listed_as_not_read(self):
        for m in self.doc["dependencies"]:
            if m["file"].endswith(".toml"):
                self.assertFalse(m["parsed"])
                self.assertEqual([], m["groups"])

    def test_every_environment_variable_row_of_the_old_page_is_there_in_the_same_order(self):
        new = [[e["name"], len(e["files"]), ra_short(e["files"][0]), "yes" if e["documented_in"] else "no"] for e in self.doc["env"]]
        self.assertEqual([list(r) for r in self.old["env_rows"]], new)
        self.assertEqual(int(self.old["env_title_count"]), len(self.doc["env"]))

    def test_the_new_page_adds_every_reading_file_and_marks_the_tests(self):
        for e in self.doc["env"]:
            self.assertEqual(self.slice["env_usage"][e["name"]], e["files"])
            self.assertTrue(set(e["test_files"]) <= set(e["files"]))
        self.assertTrue(any(e["test_files"] for e in self.doc["env"]))

    def test_documented_variables_name_the_example_file_and_keep_its_comment(self):
        names = {v["name"]: p for p, vs in self.slice["env_examples"].items() for v in vs}
        for e in self.doc["env"]:
            self.assertEqual(e["name"] in names, bool(e["documented_in"]))
            for f in e["documented_in"]:
                self.assertIn(f, self.slice["env_examples"])

    def test_names_in_an_example_that_no_code_reads_are_listed_apart(self):
        used = set(self.slice["env_usage"])
        listed = {u["name"] for u in self.doc["env_unused_examples"]}
        self.assertTrue(listed.isdisjoint(used))
        every = {v["name"] for vs in self.slice["env_examples"].values() for v in vs}
        self.assertEqual(every - used, listed)

    def test_no_value_is_in_infra_json_only_names(self):
        text = json.dumps(self.doc)
        self.assertFalse(re.search(r"(sk-|gsk_|AIza|hf_)[A-Za-z0-9_-]{16,}", text))
        for e in self.doc["env"]:
            self.assertRegex(e["name"], r"^[A-Za-z0-9_]+$")


def ra_short(p):
    return p.replace("backend/", "", 1) if p.startswith("backend/") else p


class CommittedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = jload(ROOT / "data" / "census.json")

    def test_infra_json_is_what_the_committed_census_produces(self):
        text = (ROOT / "data" / "code" / "infra.json").read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(ra.json_text(ra.build_infra(self.census)), text)

    def test_every_file_it_links_to_is_a_file_of_the_census(self):
        have = {f["path"] for f in self.census["files"]}
        doc = jload(ROOT / "data" / "code" / "infra.json")
        for e in doc["env"]:
            for f in e["files"] + e["documented_in"]:
                self.assertIn(f, have, f"{e['name']}: {f}")
        for wf in doc["ci"]:
            self.assertIn(wf["file"], have)
        for d in doc["dockerfiles"]:
            if d["file"]:
                self.assertIn(d["file"], have)


@unittest.skipUnless(NODE, "node is not installed")
class Helpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = run_node('''
import fs from "fs";
import * as D from "./dataviews.js";
const root = %s;
const infra = JSON.parse(fs.readFileSync(root + "/data/code/infra.json", "utf8"));
const schema = JSON.parse(fs.readFileSync(root + "/data/code/schema.json", "utf8"));
const L = D.erLayout(schema);
const L2 = D.erLayout(schema);
const tr = D.tableRows(schema);
const wk = tr.find((r) => r.key === "public.workspaces");
const cyc = { tables: [{ key: "public.a", schema: "public", name: "a", columns: [{ name: "id", pk: true }, { name: "b_id", fk: { to: "public.b" } }] },
                       { key: "public.b", schema: "public", name: "b", columns: [{ name: "id", pk: true }, { name: "a_id", fk: { to: "public.a" } }] },
                       { key: "public.c", schema: "public", name: "c", columns: [{ name: "id", pk: true }] }],
              relations: [{ from: "public.a", to: "public.b", cols: ["b_id"], to_cols: ["id"] }, { from: "public.b", to: "public.a", cols: ["a_id"], to_cols: ["id"] },
                          { from: "public.a", to: "public.a", cols: ["x"], to_cols: ["id"] }] };
const C = D.erLayout(cyc);
console.log(JSON.stringify({
  infraKpis: D.infraKpis(infra), families: D.envFamilies(infra), schemaKpis: D.schemaKpis(schema), nEnv: D.envRows(infra).length,
  envFirst: D.envRows(infra)[0], layout: { w: L.width, h: L.height, nodes: L.nodes.length, edges: L.edges.length, overlaps: D.overlaps(L.nodes), same: JSON.stringify(L) === JSON.stringify(L2),
    ghost: L.ghost && L.ghost.label, inBounds: L.nodes.every((n) => n.x >= 0 && n.y >= 0 && n.x + n.w <= L.width && n.y + n.h <= L.height), isolated: L.isolated.length },
  cycle: { overlaps: D.overlaps(C.nodes), nodes: C.nodes.length, edges: C.edges.length },
  wkHash: D.tableHash(wk), byHash: D.tableFromHash(tr, "#public.workspaces") && D.tableFromHash(tr, "#public.workspaces").key, byBare: D.tableFromHash(tr, "#workspaces") && D.tableFromHash(tr, "#workspaces").key,
  bad: D.tableFromHash(tr, "#%%E0%%A4%%A") === null, none: D.tableFromHash(tr, "") === null, unknown: D.tableFromHash(tr, "#public.nope") === null,
  rel: D.relationsOf(schema, "public.chats"), flags: [D.columnFlags({ pk: true, notnull: true }), D.columnFlags({ fk: {}, notnull: true, unique: true }), D.columnFlags({})],
  refs: D.refGroups(wk).map((g) => [g.id, g.files.length]), refsOther: D.refGroups(tr.find((r) => r.schema === "auth")),
  drift: [D.driftText({ drift: { only_migrations: ["a", "b"], only_dump: ["c"], type_differs: ["d"] } }), D.driftText({})],
  stages: D.stageSummary(["node:20-slim", "node:20-slim", "x", "node:20-slim"]), label: [D.manifestLabel({ file: "backend/requirements.txt", kind: "requirements" }), D.manifestLabel({ file: "frontend/package.json", kind: "package.json", name: "minime-frontend" }), D.manifestLabel({ file: "package.json", kind: "package.json" })],
  short: [D.shortPath("backend/a/b.py"), D.shortPath("m2c/x.py")], isTest: ["a/tests/x.py", "backend/tests/unit/test_x.py", "frontend/__tests__/a.js", "conftest.py", "app/main.py", "contest.py"].map(D.isTestPath),
  mig: D.migrationRows(schema)[3], migNumber: [D.migNumber("backend/migrations/0012_x.sql"), D.migNumber("scripts/public.sql")],
  words: [D.matchWords("Claude Sonnet price", "price claude"), D.matchWords("Claude", "claude gpt"), D.matchWords("x", ""), D.matchWords(null, "a")],
  cells: [D.cellNumber("$1,200"), D.cellNumber("45%%"), D.cellNumber("3.5x"), D.cellNumber("abc"), D.cellNumber("")],
  cmp: [D.compareCells("10", "9"), D.compareCells("apple", "Banana"), D.compareCells("", "a"), D.compareCells("", "a", false), D.compareCells("2", "10", false), D.compareCells("", "")],
  cats: D.categoryCounts(["a", "b", "a", "c", "a"]), none: D.categoryCounts([]),
  empty: [D.infraKpis(null).length, D.schemaKpis(undefined).length, D.envRows(null), D.erLayout(null).nodes.length],
}));
''' % json.dumps(str(ROOT)))
        cls.r = out
        cls.infra = jload(ROOT / "data" / "code" / "infra.json")
        cls.schema = jload(ROOT / "data" / "code" / "schema.json")

    def test_infra_kpis_count_what_the_json_holds(self):
        k = {x["label"]: x["value"] for x in self.r["infraKpis"]}
        env = self.infra["env"]
        self.assertEqual(len(self.infra["services"]), k["compose services"])
        self.assertEqual(sum(len(j["steps"]) and 1 for wf in self.infra["ci"] for j in wf["jobs"]), k["CI jobs"])
        self.assertEqual(sum(len(g["items"]) for m in self.infra["dependencies"] for g in m["groups"]), k["dependencies listed"])
        self.assertEqual(len(env), k["environment variables read"])
        self.assertEqual(sum(1 for e in env if e["documented_in"]), k["documented in an .env.example"])
        self.assertEqual(sum(1 for e in env if e["files"] and len(e["test_files"]) == len(e["files"])), k["read only by tests"])

    def test_variable_rows_keep_the_whole_path_and_offer_a_short_one(self):
        self.assertEqual(len(self.infra["env"]), self.r["nEnv"])
        row = self.r["envFirst"]
        self.assertEqual(self.infra["env"][0]["files"][0], row["first"])
        self.assertFalse(row["short"].startswith("backend/"))

    def test_families_need_three_members_and_are_biggest_first(self):
        fam = self.r["families"]
        self.assertTrue(all(f["n"] >= 3 for f in fam))
        self.assertEqual(sorted((f["n"] for f in fam), reverse=True), [f["n"] for f in fam])
        self.assertEqual("NEXT_PUBLIC_", next(f["name"] for f in fam if f["name"].startswith("NEXT")))

    def test_schema_kpis_count_the_public_schema(self):
        k = {x["label"]: x["value"] for x in self.r["schemaKpis"]}
        pub = [t for t in self.schema["tables"] if t["schema"] == "public"]
        self.assertEqual(len(pub), k["tables in public"])
        self.assertEqual(sum(len(t["columns"]) for t in pub), k["columns"])
        self.assertEqual(sum(1 for r in self.schema["relations"] if r["from"].startswith("public.")), k["foreign keys"])
        self.assertEqual(len(self.schema["migrations"]), k["migrations"])
        self.assertEqual(sum(len(t.get("policies", [])) for t in pub), k["policies"])
        self.assertEqual(len(self.schema["drift"]["in_migrations_not_in_dump"]), k["tables the dump is missing"])

    def test_the_er_layout_is_deterministic_has_no_overlapping_boxes_and_one_edge_per_foreign_key(self):
        L = self.r["layout"]
        pub = [t["key"] for t in self.schema["tables"] if t["schema"] == "public"]
        self.assertTrue(L["same"])
        self.assertEqual([], L["overlaps"])
        self.assertTrue(L["inBounds"])
        self.assertEqual(len(pub), L["nodes"])
        self.assertEqual(sum(1 for r in self.schema["relations"] if r["from"] in pub), L["edges"], "an edge only where the SQL declares a foreign key")
        self.assertEqual("auth.users", L["ghost"], "foreign keys to another schema go to one shared box")
        linked = {r["from"] for r in self.schema["relations"]} | {r["to"] for r in self.schema["relations"]}
        self.assertEqual(sum(1 for k in pub if k not in linked), L["isolated"])

    def test_a_reference_cycle_and_a_self_reference_do_not_hang_or_overlap(self):
        c = self.r["cycle"]
        self.assertEqual([], c["overlaps"])
        self.assertEqual(3, c["nodes"])

    def test_hashes_round_trip_and_a_bad_one_finds_nothing_instead_of_throwing(self):
        r = self.r
        self.assertEqual("#public.workspaces", r["wkHash"])
        self.assertEqual("public.workspaces", r["byHash"])
        self.assertEqual("public.workspaces", r["byBare"])
        self.assertTrue(r["bad"] and r["none"] and r["unknown"])

    def test_relationships_go_both_ways(self):
        rel = self.r["rel"]
        self.assertTrue(any(x["table"] == "public.workspaces" for x in rel["references"]))
        self.assertTrue(any(x["table"] == "public.chat_messages" for x in rel["referencedBy"]))

    def test_column_flags_come_in_a_fixed_order(self):
        self.assertEqual([["PK"], ["FK", "NOT NULL", "UNIQUE"], []], self.r["flags"])

    def test_only_public_tables_have_a_who_touches_list(self):
        self.assertEqual(["code", "tests", "sql"], [g[0] for g in self.r["refs"]])
        self.assertIsNone(self.r["refsOther"])

    def test_drift_is_one_sentence_per_kind_and_empty_when_there_is_none(self):
        text, none = self.r["drift"]
        self.assertIn("the migrations add a, b", text)
        self.assertIn("the dump has c", text)
        self.assertIn("d has a different type", text)
        self.assertEqual("", none)

    def test_small_text_helpers(self):
        r = self.r
        self.assertEqual([{"image": "node:20-slim", "n": 3}, {"image": "x", "n": 1}], r["stages"])
        self.assertEqual(["backend", "frontend (minime-frontend)", "(root)"], r["label"])
        self.assertEqual(["a/b.py", "m2c/x.py"], r["short"])
        self.assertEqual([True, True, True, True, False, False], r["isTest"])
        self.assertEqual(["0012", ""], r["migNumber"])
        self.assertEqual(self.schema["migrations"][3]["id"], r["mig"]["key"])

    def test_the_tables_page_filter_matches_every_word_in_any_order(self):
        self.assertEqual([True, False, True, False], self.r["words"])

    def test_cells_compare_as_numbers_when_both_are_numbers_and_empty_cells_go_last(self):
        self.assertEqual([1200, 45, 3.5, None, None], self.r["cells"])
        self.assertEqual([1, -1, 1, 1, 1, 0], self.r["cmp"])

    def test_category_counts_are_counted_from_the_cards(self):
        self.assertEqual([{"id": "all", "n": 5}, {"id": "a", "n": 3}, {"id": "b", "n": 1}, {"id": "c", "n": 1}], self.r["cats"])
        self.assertEqual([{"id": "all", "n": 0}], self.r["none"])

    def test_missing_input_gives_empty_results_not_a_crash(self):
        self.assertEqual([7, 8, [], 0], self.r["empty"])


PAGES = {"infra.html": ("infra.js", "infra.json"), "data.html": ("data.js", "schema.json")}


class Pages(unittest.TestCase):
    def test_the_pages_are_small_shells_with_no_data_baked_in(self):
        for page, (mod, data) in PAGES.items():
            text = (ROOT / page).read_text(encoding="utf-8")
            self.assertLess(len(text), 20_000, f"{page} must stay a shell")
            self.assertIn(f"assets/js/{mod}", text)
            self.assertIn(f"data/code/{data}", text, "the page names its data in the no-script message")
            self.assertNotRegex(text, r"ROWS=|<table|<svg", f"{page}: no data or markup typed in")

    def test_tables_html_has_no_inline_script_and_loads_its_module(self):
        text = (ROOT / "tables.html").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"<script>")
        self.assertIn("assets/js/tables.js", text)
        self.assertIn('id="sq"', text)
        self.assertIn('id="tb-cat-bar"', text)
        self.assertIn('id="tb-exp"', text)

    def test_every_module_a_page_imports_exists_and_parses(self):
        for name in ("infra.js", "data.js", "tables.js", "dataviews.js"):
            src = (JS / name).read_text(encoding="utf-8")
            for rel in re.findall(r"from \"(\.[^\"]+)\"", src):
                self.assertTrue((JS / rel).is_file(), f"{name} imports {rel}")
            if NODE:
                r = subprocess.run([NODE, "--check", str(JS / name)], capture_output=True, text=True)
                self.assertEqual(0, r.returncode, f"{name}: {r.stderr}")

    def test_the_modules_write_text_not_html(self):
        for name in ("infra.js", "data.js", "tables.js"):
            src = (JS / name).read_text(encoding="utf-8")
            self.assertNotRegex(src, r"innerHTML|insertAdjacentHTML|document\.write", name)

    def test_the_old_regex_renderers_for_infra_are_gone(self):
        for name in ("refresh_infra", "infra_services", "env_rows", "_between"):
            self.assertFalse(hasattr(ra, name), name)
        self.assertNotIn("infra", ra.PAGES)

    def test_the_two_data_files_are_written_by_the_scripts_that_own_them(self):
        self.assertTrue(hasattr(ra, "build_infra") and ra.INFRA_REL == "data/code/infra.json")
        self.assertTrue((ROOT / "data" / "code" / "schema.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
