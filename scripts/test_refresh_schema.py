#!/usr/bin/env python3
"""
test_refresh_schema.py -- tests for the data model (P18): scripts/refresh_schema.py and data/code/schema.json. Standard library only.

What is checked
  * the SQL reader on small, hand-written statements: comments and quoted text, dollar quoting, columns, defaults, primary and
    foreign keys (inline and table-level), alter table (add column, add constraint, row-level security), policies, indexes,
    triggers, comments, drops;
  * golden: the old data.html (frozen in scripts/golden/p18_data_old.json) listed 15 tables and 119 columns. Every one of them is in
    schema.json with the same type, and the page draws at least as many relationships as the old diagram did;
  * the committed data/code/schema.json is exactly what the committed census and embedded source produce, and says what it was built from;
  * the dump and the migrations are compared, not merged: a table only one of them has is reported as drift;
  * the census fallback (no embedded source) never invents a foreign key.

    python scripts/test_refresh_schema.py
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "scripts" / "golden"

_spec = importlib.util.spec_from_file_location("refresh_schema", ROOT / "scripts" / "refresh_schema.py")
rs = importlib.util.module_from_spec(_spec)
sys.modules["refresh_schema"] = rs
_spec.loader.exec_module(rs)


def parse(sql, file="backend/migrations/0001_x.sql", tables=None, functions=None, schema="public"):
    tables = {} if tables is None else tables
    functions = [] if functions is None else functions
    rs.parse_sql(sql, file, tables, functions, default_schema=schema)
    return tables


class Statements(unittest.TestCase):
    def test_comments_and_semicolons_inside_text_do_not_split_a_statement(self):
        sql = "-- a; comment\ncreate table a (x text default 'a;b'); /* c; */ create table b (y int);"
        self.assertEqual(["create table a (x text default 'a;b')", "create table b (y int)"], [s for _, s in rs.split_statements(sql)])

    def test_a_dollar_quoted_body_is_one_statement_and_lines_are_counted(self):
        sql = "create function f() returns int as $$ begin select 1; return 2; end $$ language plpgsql;\n\ncreate table t (a int);"
        out = rs.split_statements(sql)
        self.assertEqual(2, len(out))
        self.assertEqual(3, out[1][0], "the line a statement starts on")

    def test_an_escaped_quote_does_not_end_the_string(self):
        self.assertEqual(1, len(rs.split_statements("comment on table t is 'it''s; fine';")))

    def test_split_top_ignores_commas_inside_parentheses_and_quotes(self):
        self.assertEqual(["a numeric(10, 2)", "b text default 'x,y'"], rs.split_top("a numeric(10, 2), b text default 'x,y'"))


class Tables(unittest.TestCase):
    def test_columns_types_defaults_and_flags(self):
        t = parse("""create table if not exists public.items (
            id bigserial primary key,
            name text not null default 'none',
            at timestamp with time zone not null default now(),
            qty integer check (qty >= 0),
            tags text[] default '{}'
        );""")["public.items"]
        c = t.columns
        self.assertEqual(["id"], t.pk)
        self.assertTrue(c["id"]["pk"] and c["id"]["notnull"])
        self.assertEqual("timestamptz", c["at"]["type"])
        self.assertEqual("'none'", c["name"]["default"])
        self.assertEqual("now()", c["at"]["default"])
        self.assertEqual("qty >= 0", c["qty"]["check"])
        self.assertFalse(c["qty"]["notnull"])

    def test_an_inline_references_is_a_foreign_key_with_its_delete_rule(self):
        t = parse("""create table public.chats (id text primary key, owner_id uuid references auth.users(id) on delete cascade,
                     ws text references workspaces(id) on delete set null);""")["public.chats"]
        self.assertEqual([{"cols": ["owner_id"], "to": "auth.users", "to_cols": ["id"], "on_delete": "cascade"},
                          {"cols": ["ws"], "to": "public.workspaces", "to_cols": ["id"], "on_delete": "set null"}],
                         [{k: v for k, v in f.items() if k != "file"} for f in t.fks])

    def test_table_level_constraints_primary_unique_check_and_composite_foreign_key(self):
        t = parse("""create table public.m (a text, b text, c int,
            constraint m_pk primary key (a, b), unique (a, c), check (c > 0),
            foreign key (a, b) references public.p (a, b) on delete cascade);""")["public.m"]
        self.assertEqual(["a", "b"], t.pk)
        self.assertEqual([["a", "c"]], t.uniques)
        self.assertEqual(["c > 0"], t.checks)
        self.assertEqual(["a", "b"], t.fks[0]["cols"])
        self.assertTrue(t.columns["a"]["pk"] and t.columns["a"]["notnull"])

    def test_alter_table_adds_columns_constraints_and_row_level_security(self):
        tables = parse("create table public.w (id text primary key);")
        parse("""alter table public.w add column if not exists stage text default 'x';
                 alter table public.w add constraint w_fk foreign key (id) references public.z (id);
                 alter table public.w enable row level security;
                 alter table public.w force row level security;""", file="backend/migrations/0002_y.sql", tables=tables)
        t = tables["public.w"]
        self.assertEqual("backend/migrations/0002_y.sql", t.columns["stage"]["added_in"])
        self.assertEqual("public.z", t.fks[0]["to"])
        self.assertEqual("forced", t.rls)

    def test_drop_column_and_drop_table(self):
        tables = parse("create table public.a (x int, y int); create table public.b (z int);")
        parse("alter table public.a drop column y; drop table if exists public.b;", tables=tables)
        self.assertEqual(["x"], list(tables["public.a"].columns))
        self.assertNotIn("public.b", tables)

    def test_policies_indexes_triggers_comments_and_functions(self):
        tables, fns = {}, []
        parse("""create table public.w (id text primary key, name text);
                 create policy "w_scope" on public.w for select to authenticated using (true);
                 create policy other on public.w for all using (true);
                 drop policy other on public.w;
                 create unique index if not exists w_name on public.w (name);
                 create function public.touch() returns trigger as $$ begin return new; end $$ language plpgsql;
                 create trigger w_touch before update on public.w for each row execute function public.touch();
                 comment on table public.w is 'the workspaces';
                 comment on column public.w.name is 'what it is called';""", tables=tables, functions=fns)
        t = tables["public.w"]
        self.assertEqual(["w_scope"], [p["name"] for p in t.policies.values()])
        self.assertEqual(["authenticated"], t.policies["w_scope"]["roles"])
        self.assertEqual("select", t.policies["w_scope"]["cmd"])
        self.assertEqual([("w_name", True)], [(i["name"], i["unique"]) for i in t.indexes])
        self.assertEqual("before update", t.triggers[0]["when"])
        self.assertEqual("the workspaces", t.comment)
        self.assertEqual("what it is called", t.columns["name"]["comment"])
        self.assertEqual(["touch"], [f["name"] for f in fns])

    def test_a_dump_in_another_schema_uses_that_schema_for_unqualified_names(self):
        tables = parse("create table users (id uuid primary key);", file="scripts/auth.sql", schema="auth")
        self.assertIn("auth.users", tables)


class Comparing(unittest.TestCase):
    def test_spelling_differences_between_a_migration_and_a_dump_are_not_drift(self):
        a = parse("create table public.t (id bigserial primary key, v numeric(18, 8), tags text[], at timestamp with time zone);")["public.t"]
        b = parse("create table public.t (id bigint primary key, v numeric, tags ARRAY, at timestamptz);", file="scripts/public.sql")["public.t"]
        self.assertEqual({}, rs.drift_of(a, b))

    def test_a_real_difference_is_reported_by_column_name(self):
        a = parse("create table public.t (id int, extra text, n int);")["public.t"]
        b = parse("create table public.t (id int, old text, n text);", file="scripts/public.sql")["public.t"]
        self.assertEqual({"only_migrations": ["extra"], "only_dump": ["old"], "type_differs": ["n"]}, rs.drift_of(a, b))

    def test_a_composite_key_the_dump_writes_as_single_columns_is_one_relationship(self):
        rels = [{"from": "p.c", "cols": ["a", "b"], "to": "p.t", "to_cols": ["a", "b"]}, {"from": "p.c", "cols": ["a"], "to": "p.t", "to_cols": ["a"]}]
        self.assertEqual([rels[0]], rs.drop_split_parts(rels))

    def test_the_first_comment_paragraph_is_the_summary_and_the_file_name_line_is_skipped(self):
        text = "-- 0007_grant.sql\n--\n-- Grants the code-file tables to the app role.\n-- Second line of it.\n--\n-- later paragraph\ncreate table x (a int);"
        self.assertEqual("Grants the code-file tables to the app role. Second line of it.", rs.first_paragraph(text))


class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        cls.doc = json.loads((ROOT / "data" / "code" / "schema.json").read_text(encoding="utf-8"))
        cls.old = json.loads((GOLD / "p18_data_old.json").read_text(encoding="utf-8"))

    def test_schema_json_is_what_the_committed_census_and_source_produce(self):
        self.assertEqual(rs.json_text(rs.build_schema(ROOT, self.census)), (ROOT / "data" / "code" / "schema.json").read_bytes().decode("utf-8").replace("\r\n", "\n"))

    def test_it_says_which_commit_and_whether_the_sql_was_read(self):
        self.assertEqual(self.census["git"]["head"], self.doc["commit"])
        self.assertIn(self.doc["source"], ("src", "census"))

    def test_every_table_and_column_of_the_old_page_is_present_with_the_same_type(self):
        norm = lambda t: {"timestamp": "timestamptz"}.get(rs.type_key(t), rs.type_key(t))
        tables = {t["key"]: t for t in self.doc["tables"]}
        self.assertEqual(self.old["public_tables"], len(self.old["columns"]))
        for name, cols in self.old["columns"].items():
            self.assertIn(f"public.{name}", tables)
            have = {c["name"]: c["type"] for c in tables[f"public.{name}"]["columns"]}
            for col, typ in cols:
                self.assertIn(col, have, f"{name}.{col}")
                self.assertEqual(norm(typ), norm(have[col]), f"{name}.{col}")

    def test_the_other_schemas_have_the_table_counts_the_old_page_gave(self):
        got = {s["name"]: s["tables"] for s in self.doc["schemas"] if s["name"] != "public"}
        self.assertEqual(self.old["other_schemas"], got)

    def test_at_least_as_many_relationships_as_the_old_diagram_drew(self):
        pub = [r for r in self.doc["relations"] if r["from"].startswith("public.")]
        self.assertGreaterEqual(len(pub), self.old["edges_drawn"])

    def test_every_relationship_joins_two_tables_the_document_knows_or_a_foreign_schema(self):
        keys = {t["key"] for t in self.doc["tables"]}
        for r in self.doc["relations"]:
            self.assertIn(r["from"], keys)
            self.assertTrue(r["to"] in keys or r["to"].split(".")[0] != "public", f"{r['from']} -> {r['to']}")
            for c in r["cols"]:
                self.assertIn(c, {x["name"] for x in next(t for t in self.doc["tables"] if t["key"] == r["from"])["columns"]})

    def test_tables_only_the_migrations_build_are_reported_as_missing_from_the_dump(self):
        miss = set(self.doc["drift"]["in_migrations_not_in_dump"])
        for k in miss:
            t = next(x for x in self.doc["tables"] if x["key"] == k)
            self.assertEqual("migrations", t["origin"])
        self.assertEqual(miss, {t["key"] for t in self.doc["tables"] if t["schema"] == "public" and t["origin"] == "migrations"})

    def test_every_public_table_lists_the_files_that_name_it_as_the_census_does(self):
        for t in self.doc["tables"]:
            if t["schema"] != "public":
                self.assertNotIn("refs", t, "the name of a table in another schema is not unique")
                continue
            files = self.census["table_refs"].get(t["name"])
            self.assertIsNotNone(files, t["name"])
            got = t["refs"]["code"] + t["refs"]["tests"] + t["refs"]["sql"]
            self.assertEqual(sorted(files), sorted(got))

    def test_every_file_a_migration_row_names_is_a_migration_of_the_census(self):
        for m in self.doc["migrations"]:
            self.assertIn(m["file"], self.census["sql"])
        self.assertEqual(sorted(m["file"] for m in self.doc["migrations"]), [m["file"] for m in self.doc["migrations"]], "file order is the apply order")

    def test_no_default_or_comment_holds_a_secret_looking_value(self):
        import re
        text = json.dumps(self.doc)
        self.assertFalse(re.search(r"(sk-|gsk_|AIza|hf_)[A-Za-z0-9_-]{16,}", text))


class Fallback(unittest.TestCase):
    def test_without_embedded_source_it_uses_the_census_and_invents_no_relationship(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "data").mkdir()
            census = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
            doc = rs.build_schema(tmp, census)         # no data/src here
            self.assertEqual("census", doc["source"])
            self.assertEqual([], doc["relations"])
            self.assertTrue(any(t["schema"] == "public" for t in doc["tables"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_source_from_another_commit_is_not_used(self):
        census = json.loads((ROOT / "data" / "census.json").read_text(encoding="utf-8"))
        self.assertFalse(rs.src_commit_matches({"commit": "0" * 40}, census))
        self.assertTrue(rs.src_commit_matches({"commit": census["git"]["head_full"]}, census))


if __name__ == "__main__":
    unittest.main(verbosity=2)
