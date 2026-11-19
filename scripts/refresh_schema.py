#!/usr/bin/env python3
"""
refresh_schema.py -- the data model of MiniMe, read from its SQL (P18).

    python scripts/refresh_schema.py            # write data/code/schema.json
    python scripts/refresh_schema.py --check    # change nothing; exit 1 if schema.json is out of date

data.html is a shell: assets/js/data.js draws the table list, the relationship diagram and the migration timeline from
data/code/schema.json. Nothing in that file is typed by hand.

Inputs (all inside this repo, so it also runs in CI, with no MiniMe checkout):
    data/census.json         the SQL file list, the per-table "mentioned in" lists (`table_refs`), the commit
    data/src/<file>.sql.txt  the SQL itself, as committed at the census commit (scripts/refresh_source.py copied it)

Two kinds of SQL are read, and the page shows both, because they do not agree:
    backend/migrations/*.sql   what MiniMe's own migrations build, applied in file order (create, add column, foreign keys,
                               row-level security, policies, indexes, triggers, comments)
    scripts/{public,auth,...}.sql   a Supabase "context only" dump of the live database (its own header says it may be
                               behind). Tables seen only in one of the two, and columns that differ, are reported as drift.

If the embedded source is missing or is from another commit, the file falls back to what the census recorded (table and
column names, truncated types, no foreign keys) and says so in `source`; nothing is guessed.

"Who touches this table" comes from the census `table_refs`: files whose text names the table. That is a text match, not
proof that a file queries it, and the page says so.

Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_REL = "data/code/schema.json"
DATA_SCHEMA = 1
SRC_DIR = "data/src"
CENSUS_REL = "data/census.json"
MIGRATIONS_DIR = "backend/migrations/"
SNAPSHOT_DIR = "scripts/"
DEFAULT_SCHEMA = "public"
SUMMARY_MAX = 240
COMMENT_MAX = 300
DEFAULT_MAX = 90
CHECK_MAX = 160

# ----------------------------------------------------------------------------- statements


def split_statements(text):
    """[(first line number, statement text)] with comments removed. Respects 'strings' ('' is an escaped quote),
    "identifiers", $tag$ ... $tag$ bodies, -- line comments and /* block */ comments."""
    out, buf = [], []
    i, n, line, start = 0, len(text), 1, None

    def flush():
        nonlocal buf, start
        s = "".join(buf).strip()
        if s:
            out.append((start or 1, s))
        buf, start = [], None

    while i < n:
        ch = text[i]
        two = text[i:i + 2]
        if two == "--":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += text.count("\n", i, j)
            buf.append(" ")
            i = j
            continue
        if ch == "\n":
            line += 1
        if start is None and not ch.isspace():
            start = line
        if ch == "'":
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if text[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            seg = text[i:j + 1]
            line += seg.count("\n")
            buf.append(seg)
            i = j + 1
            continue
        if ch == '"':
            j = text.find('"', i + 1)
            j = n - 1 if j < 0 else j
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        if ch == "$":
            m = re.match(r"\$([A-Za-z_]\w*)?\$", text[i:])
            if m:
                tag = m.group(0)
                j = text.find(tag, i + len(tag))
                j = n if j < 0 else j + len(tag)
                seg = text[i:j]
                line += seg.count("\n")
                buf.append(seg)
                i = j
                continue
        if ch == ";":
            flush()
            i += 1
            continue
        buf.append(ch)
        i += 1
    flush()
    return out


def split_top(s, sep=","):
    """Split on `sep` outside parentheses, quotes and dollar quotes."""
    parts, depth, cur, i, n = [], 0, [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if s[j] == "'":
                    if s[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if ch == '"':
            j = s.find('"', i + 1)
            j = n - 1 if j < 0 else j
            cur.append(s[i:j + 1])
            i = j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    last = "".join(cur).strip()
    if last or parts:
        parts.append(last)
    return [p for p in parts if p]


def balanced(s, open_at):
    """The text inside the parenthesis that opens at s[open_at], and the index after its closing one."""
    depth, i, n = 0, open_at, len(s)
    while i < n:
        ch = s[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if s[j] == "'":
                    if s[j + 1:j + 2] == "'":
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return s[open_at + 1:i], i + 1
        i += 1
    return s[open_at + 1:], n


def ident(s):
    return s.strip().strip('"').lower()


def split_name(raw, default_schema):
    """'public.Foo' / '"auth"."users"' / 'foo' -> (schema, name), lower-case."""
    parts = [ident(p) for p in re.split(r"\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", raw.strip())]
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return default_schema, parts[0] if parts else ""


def idents(s):
    return [ident(p) for p in split_top(s)]


def squash(s):
    return re.sub(r"\s+", " ", s or "").strip()


def cut(s, n):
    s = squash(s)
    if len(s) <= n:
        return s
    return s[:n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"


def literals(s):
    """Every 'quoted string' in s, with '' unescaped, joined (SQL concatenates adjacent literals)."""
    return "".join(m.replace("''", "'") for m in re.findall(r"'((?:[^']|'')*)'", s))


# ----------------------------------------------------------------------------- columns and constraints
KEYWORDS = r"(?:not\s+null|null|default|primary\s+key|references|check|unique|constraint|generated|collate)"
TYPE_SHORT = {"timestamp with time zone": "timestamptz", "timestamp without time zone": "timestamp", "character varying": "varchar",
              "double precision": "float8", "time with time zone": "timetz", "time without time zone": "time"}


def norm_type(t):
    t = squash(t).lower()
    for long_, short in TYPE_SHORT.items():
        if t.startswith(long_):
            t = short + t[len(long_):]
    return t


SERIAL = {"bigserial": "bigint", "serial": "integer", "smallserial": "smallint", "serial8": "bigint", "serial4": "integer"}


def type_key(t):
    """A type with the spelling differences between a hand-written migration and a Postgres dump removed (bigserial = bigint,
    numeric(18, 8) = numeric, text[] = ARRAY), so drift reports only real differences."""
    t = re.sub(r"\(.*?\)", "", norm_type(t)).strip()
    if t.endswith("[]") or t == "array":
        return "array"
    return SERIAL.get(t, t)


def read_default(rest):
    """The DEFAULT expression of a column definition, or None. Reads until a top-level keyword."""
    m = re.search(r"\bdefault\s+", rest, re.I)
    if not m:
        return None
    i, n, depth = m.end(), len(rest), 0
    j = i
    while j < n:
        ch = rest[j]
        if ch == "'":
            k = j + 1
            while k < n:
                if rest[k] == "'":
                    if rest[k + 1:k + 2] == "'":
                        k += 2
                        continue
                    break
                k += 1
            j = k + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch.isspace() and re.match(r"\s+" + KEYWORDS + r"\b", rest[j:], re.I):
            break
        j += 1
    return cut(rest[i:j], DEFAULT_MAX) or None


def parse_references(rest, default_schema):
    m = re.search(r"\breferences\s+([\w.\"]+)\s*(?:\(([^)]*)\))?(.*)$", rest, re.I | re.S)
    if not m:
        return None
    schema, name = split_name(m.group(1), default_schema)
    tail = m.group(3) or ""
    od = re.search(r"\bon\s+delete\s+(cascade|set\s+null|set\s+default|restrict|no\s+action)", tail, re.I)
    return {"to": f"{schema}.{name}", "to_cols": idents(m.group(2)) if m.group(2) else [], "on_delete": squash(od.group(1)).lower() if od else None}


def parse_column(defn, default_schema):
    m = re.match(r'\s*("[^"]+"|\w+)\s*(.*)$', defn, re.S)
    if not m:
        return None
    name, rest = ident(m.group(1)), m.group(2)
    parts = re.split(r"\s+(?=" + KEYWORDS + r"\b)", rest, maxsplit=1, flags=re.I)
    col = {"name": name, "type": norm_type(parts[0]), "notnull": bool(re.search(r"\bnot\s+null\b", rest, re.I)),
           "pk": bool(re.search(r"\bprimary\s+key\b", rest, re.I)), "unique": bool(re.search(r"\bunique\b", rest, re.I)),
           "default": read_default(rest)}
    if col["pk"]:
        col["notnull"] = True
    ref = parse_references(rest, default_schema)
    if ref:
        col["fk"] = {"to": ref["to"], "col": ref["to_cols"][0] if ref["to_cols"] else None, "on_delete": ref["on_delete"]}
    cm = re.search(r"\bcheck\s*\(", rest, re.I)
    if cm:
        body, _ = balanced(rest, cm.end() - 1)
        col["check"] = cut(body, CHECK_MAX)
    return col


def parse_constraint(defn, default_schema):
    """('pk'|'fk'|'unique'|'check', payload) for a table-level constraint, else None."""
    d = re.sub(r"^\s*constraint\s+(?:\"[^\"]+\"|\w+)\s+", "", defn, flags=re.I)
    m = re.match(r"primary\s+key\s*\(([^)]*)\)", d, re.I)
    if m:
        return "pk", idents(m.group(1))
    m = re.match(r"unique\s*\(([^)]*)\)", d, re.I)
    if m:
        return "unique", idents(m.group(1))
    m = re.match(r"foreign\s+key\s*\(([^)]*)\)\s*(.*)$", d, re.I | re.S)
    if m:
        ref = parse_references(m.group(2), default_schema)
        if ref:
            return "fk", {"cols": idents(m.group(1)), **ref}
    m = re.match(r"check\s*\(", d, re.I)
    if m:
        body, _ = balanced(d, m.end() - 1)
        return "check", cut(body, CHECK_MAX)
    return None


class Table:
    def __init__(self, schema, name, file, line=None):
        self.schema, self.name, self.key = schema, name, f"{schema}.{name}"
        self.created_in, self.line = file, line
        self.columns = {}
        self.pk, self.uniques, self.checks, self.fks = [], [], [], []
        self.rls = None
        self.policies, self.indexes, self.triggers, self.touched = {}, [], [], []
        self.comment = None

    def touch(self, file, op):
        if not any(t["file"] == file and t["op"] == op for t in self.touched):
            self.touched.append({"file": file, "op": op})

    def finish_pk(self):
        for c in self.columns.values():
            if c["name"] in self.pk:
                c["pk"], c["notnull"] = True, True

    def add_fk(self, fk, file):
        if any(f["cols"] == fk["cols"] and f["to"] == fk["to"] and f["to_cols"] == fk["to_cols"] for f in self.fks):
            return
        self.fks.append({**fk, "file": file})


def apply_create_table(tables, stmt, file, line, default_schema):
    m = re.match(r"create\s+(?:(?:global\s+|local\s+)?(?:temp|temporary|unlogged)\s+)?table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)\s*\(", stmt, re.I)
    if not m:
        return
    schema, name = split_name(m.group(1), default_schema)
    body, _ = balanced(stmt, m.end() - 1)
    t = tables.get(f"{schema}.{name}")
    if t is None:
        t = tables[f"{schema}.{name}"] = Table(schema, name, file, line)
    t.touch(file, "create")
    for part in split_top(body):
        first = part.split(None, 1)[0].lower() if part.split() else ""
        if first in ("constraint", "primary", "foreign", "unique", "check", "exclude", "like"):
            pc = parse_constraint(part, schema)
            if not pc:
                continue
            kind, val = pc
            if kind == "pk":
                t.pk = val
            elif kind == "unique":
                t.uniques.append(val)
            elif kind == "check":
                t.checks.append(val)
            elif kind == "fk":
                t.add_fk({"cols": val["cols"], "to": val["to"], "to_cols": val["to_cols"], "on_delete": val["on_delete"]}, file)
            continue
        col = parse_column(part, schema)
        if col and col["name"] not in t.columns:
            t.columns[col["name"]] = col
    for c in list(t.columns.values()):
        if c.get("fk"):
            t.add_fk({"cols": [c["name"]], "to": c["fk"]["to"], "to_cols": [c["fk"]["col"]] if c["fk"]["col"] else [], "on_delete": c["fk"]["on_delete"]}, file)
        if c["pk"] and c["name"] not in t.pk:
            t.pk.append(c["name"])
    t.finish_pk()


def apply_alter_table(tables, stmt, file, default_schema):
    m = re.match(r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?([\w.\"]+)\s+(.*)$", stmt, re.I | re.S)
    if not m:
        return
    schema, name = split_name(m.group(1), default_schema)
    t = tables.get(f"{schema}.{name}")
    if t is None:                       # a table made outside the recorded SQL: keep what the alter says
        t = tables[f"{schema}.{name}"] = Table(schema, name, file)
    for action in split_top(m.group(2)):
        a = action.strip()
        low = a.lower()
        am = re.match(r"add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?(.*)$", a, re.I | re.S)
        if re.match(r"add\s+constraint\b", low) or re.match(r"add\s+(?:primary|foreign|unique|check)\b", low):
            pc = parse_constraint(re.sub(r"^add\s+", "", a, flags=re.I), schema)
            if pc:
                kind, val = pc
                if kind == "pk":
                    t.pk = val
                    t.finish_pk()
                elif kind == "unique":
                    t.uniques.append(val)
                elif kind == "check":
                    t.checks.append(val)
                elif kind == "fk":
                    t.add_fk({"cols": val["cols"], "to": val["to"], "to_cols": val["to_cols"], "on_delete": val["on_delete"]}, file)
            t.touch(file, "constraint")
        elif am and re.match(r"add\b", low):
            col = parse_column(am.group(1), schema)
            if col:
                t.columns.setdefault(col["name"], col)
                if col.get("fk"):
                    t.add_fk({"cols": [col["name"]], "to": col["fk"]["to"], "to_cols": [col["fk"]["col"]] if col["fk"]["col"] else [], "on_delete": col["fk"]["on_delete"]}, file)
                t.touch(file, "add column")
                t.columns[col["name"]].setdefault("added_in", file)
        elif re.match(r"drop\s+column\b", low):
            cm = re.match(r"drop\s+column\s+(?:if\s+exists\s+)?([\w\"]+)", a, re.I)
            if cm:
                t.columns.pop(ident(cm.group(1)), None)
                t.touch(file, "drop column")
        elif re.match(r"(enable|force)\s+row\s+level\s+security", low):
            t.rls = "forced" if low.startswith("force") else (t.rls or "enabled")
            t.touch(file, "row level security")


def apply_other(tables, stmt, file, default_schema, functions):
    low = stmt.lower()
    m = re.match(r"create\s+policy\s+(\"[^\"]+\"|\w+)\s+on\s+([\w.\"]+)(.*)$", stmt, re.I | re.S)
    if m:
        schema, name = split_name(m.group(2), default_schema)
        t = tables.get(f"{schema}.{name}")
        if t is not None:
            tail = m.group(3)
            cmd = re.search(r"\bfor\s+(all|select|insert|update|delete)\b", tail, re.I)
            to = re.search(r"\bto\s+([\w\s,\"]+?)(?=\s+(?:using|with)\b|$)", tail, re.I)
            t.policies[ident(m.group(1))] = {"name": ident(m.group(1)), "cmd": cmd.group(1).lower() if cmd else "all",
                                             "roles": [ident(r) for r in to.group(1).split(",")] if to else [], "file": file}
            t.touch(file, "policy")
        return
    m = re.match(r"drop\s+policy\s+(?:if\s+exists\s+)?(\"[^\"]+\"|\w+)\s+on\s+([\w.\"]+)", stmt, re.I)
    if m:
        schema, name = split_name(m.group(2), default_schema)
        t = tables.get(f"{schema}.{name}")
        if t is not None:
            t.policies.pop(ident(m.group(1)), None)
        return
    m = re.match(r"create\s+(unique\s+)?index\s+(?:concurrently\s+)?(?:if\s+not\s+exists\s+)?(\"[^\"]+\"|\w+)\s+on\s+(?:only\s+)?([\w.\"]+)\s*(?:using\s+\w+\s*)?\(", stmt, re.I)
    if m:
        schema, name = split_name(m.group(3), default_schema)
        t = tables.get(f"{schema}.{name}")
        if t is not None:
            cols, _ = balanced(stmt, m.end() - 1)
            t.indexes.append({"name": ident(m.group(2)), "unique": bool(m.group(1)), "on": cut(cols, 100), "file": file})
            t.touch(file, "index")
        return
    m = re.match(r"create\s+(?:or\s+replace\s+)?function\s+([\w.\"]+)\s*\(", stmt, re.I)
    if m:
        functions.append({"name": split_name(m.group(1), default_schema)[1], "file": file})
        return
    m = re.match(r"create\s+(?:or\s+replace\s+)?trigger\s+(\"[^\"]+\"|\w+)\s+(before|after|instead\s+of)\s+(.+?)\s+on\s+([\w.\"]+)", stmt, re.I | re.S)
    if m:
        schema, name = split_name(m.group(4), default_schema)
        t = tables.get(f"{schema}.{name}")
        if t is not None:
            t.triggers.append({"name": ident(m.group(1)), "when": squash(m.group(2)).lower() + " " + squash(m.group(3)).lower(), "file": file})
            t.touch(file, "trigger")
        return
    m = re.match(r"comment\s+on\s+(table|column)\s+([\w.\"]+)\s+is\s+(.*)$", stmt, re.I | re.S)
    if m:
        text = cut(literals(m.group(3)), COMMENT_MAX)
        if m.group(1).lower() == "table":
            schema, name = split_name(m.group(2), default_schema)
            t = tables.get(f"{schema}.{name}")
            if t is not None and text:
                t.comment = text
        else:
            parts = [ident(p) for p in m.group(2).split(".")]
            if len(parts) >= 3:
                t = tables.get(f"{parts[-3]}.{parts[-2]}")
            elif len(parts) == 2:
                t = tables.get(f"{default_schema}.{parts[0]}")
            else:
                t = None
            if t is not None and parts and parts[-1] in t.columns and text:
                t.columns[parts[-1]]["comment"] = text
        return
    if low.startswith("drop table"):
        m = re.match(r"drop\s+table\s+(?:if\s+exists\s+)?([\w.\"]+)", stmt, re.I)
        if m:
            schema, name = split_name(m.group(1), default_schema)
            tables.pop(f"{schema}.{name}", None)


def parse_sql(text, file, tables, functions, default_schema=DEFAULT_SCHEMA):
    """Apply every statement of one SQL file to `tables` (a dict key -> Table), in order."""
    for line, stmt in split_statements(text):
        low = stmt[:40].lower()
        if low.startswith("create") and re.match(r"create\s+(?:(?:global\s+|local\s+)?(?:temp|temporary|unlogged)\s+)?table\b", low):
            apply_create_table(tables, stmt, file, line, default_schema)
        elif low.startswith("alter table"):
            apply_alter_table(tables, stmt, file, default_schema)
        else:
            apply_other(tables, stmt, file, default_schema, functions)


# ----------------------------------------------------------------------------- reading the inputs
def read_text(path):
    return Path(path).read_bytes().decode("utf-8").replace("\r\n", "\n")


def read_json(path):
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(read_text(p))
    except ValueError:
        return None


def json_text(d):
    """The same layout refresh_atlas.json_text writes: one-space indent, sorted keys, trailing newline."""
    return json.dumps(d, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def src_commit_matches(manifest, census):
    if not manifest or not manifest.get("commit"):
        return False
    head = census.get("git", {}).get("head", "")
    full = census.get("git", {}).get("head_full", "") or head
    return bool(head) and (str(manifest["commit"]).startswith(head) or str(manifest["commit"]) == full)


def source_for(root, census):
    """{sql path: text} when every SQL file the census lists is embedded at the census commit, else None."""
    manifest = read_json(Path(root) / SRC_DIR / "manifest.json")
    if not src_commit_matches(manifest, census):
        return None
    out = {}
    for rel in sorted(census.get("sql") or {}):
        p = Path(root) / SRC_DIR / (rel + ".txt")
        if not p.is_file():
            return None
        out[rel] = read_text(p)
    return out


def is_migration(rel):
    return rel.startswith(MIGRATIONS_DIR) and rel.endswith(".sql")


def migration_id(rel):
    m = re.match(r"(\d+)_", Path(rel).name)
    return m.group(1) if m else ""


def snapshot_schema(rel, text):
    """The schema a dump file is about: the one its CREATE TABLE statements name (auth.sql -> auth), else its file name."""
    m = re.search(r"create\s+table\s+(?:if\s+not\s+exists\s+)?\"?(\w+)\"?\.", text, re.I)
    return m.group(1).lower() if m else Path(rel).stem


def first_paragraph(text):
    """The first comment paragraph after the file-name line: what the migration says it is for."""
    lines = []
    for raw in text.split("\n"):
        s = raw.strip()
        if not s.startswith("--"):
            if lines or s:
                break
            continue
        body = s[2:].strip()
        if not lines and (not body or re.match(r"^\d+_\S+\.sql$", body)):
            continue
        if not body:
            if lines:
                break
            continue
        if re.match(r"^[-=]{3,}$", body):
            continue
        lines.append(body)
    return cut(" ".join(lines), SUMMARY_MAX)


def from_census(census):
    """The fallback when the SQL is not embedded: the tables and columns the census recorded (types are cut to two words)."""
    tables, functions = {}, []
    for rel, info in sorted(census.get("sql", {}).items()):
        schema = DEFAULT_SCHEMA
        for tb in info.get("tables") or []:
            s, n = split_name(tb["name"], schema)
            if f"{s}.{n}" in tables:
                continue
            t = Table(s, n, rel)
            for c in tb.get("columns") or []:
                if not re.match(r"^\w+$", c.get("name", "")):
                    continue
                t.columns[c["name"].lower()] = {"name": c["name"].lower(), "type": norm_type(c.get("type", "")), "notnull": False, "pk": False, "unique": False, "default": None}
            t.touch(rel, "create")
            tables[t.key] = t
        for fn in info.get("functions") or []:
            functions.append({"name": fn if isinstance(fn, str) else fn.get("name", ""), "file": rel})
    return tables, functions


# ----------------------------------------------------------------------------- the document
def col_out(c, snap_names=None):
    out = {"name": c["name"], "type": c["type"], "notnull": c["notnull"], "pk": c["pk"]}
    for k in ("unique", "default", "check", "comment", "added_in"):
        if c.get(k):
            out[k] = c[k]
    if c.get("fk"):
        out["fk"] = {k: v for k, v in c["fk"].items() if v}
    return out


def table_out(t, origin, refs, snap_cols=None):
    cols = [col_out(c) for c in t.columns.values()]
    rec = {"key": t.key, "schema": t.schema, "name": t.name, "origin": origin, "created_in": t.created_in, "columns": cols, "pk": t.pk}
    if t.line:
        rec["created_line"] = t.line
    if t.uniques:
        rec["unique"] = t.uniques
    if t.checks:
        rec["checks"] = t.checks
    if t.fks:
        rec["fks"] = [{"cols": f["cols"], "to": f["to"], "to_cols": f["to_cols"], **({"on_delete": f["on_delete"]} if f.get("on_delete") else {})} for f in t.fks]
    if t.rls:
        rec["rls"] = t.rls
    if t.policies:
        rec["policies"] = sorted(({k: v for k, v in p.items() if v} for p in t.policies.values()), key=lambda p: p["name"])
    if t.indexes:
        rec["indexes"] = t.indexes
    if t.triggers:
        rec["triggers"] = t.triggers
    if t.comment:
        rec["comment"] = t.comment
    rec["touched"] = t.touched
    if refs is not None:
        rec["refs"] = refs
    return rec


def ref_buckets(name, census, test_paths):
    """Files whose text names the table, split into code / tests / sql. None when the census has no entry."""
    files = (census.get("table_refs") or {}).get(name)
    if files is None:
        return None
    code, tests, sql = [], [], []
    for p in files:
        if p.endswith(".sql"):
            sql.append(p)
        elif p in test_paths or "/tests/" in p or p.startswith("tests/"):
            tests.append(p)
        else:
            code.append(p)
    return {"code": sorted(code), "tests": sorted(tests), "sql": sorted(sql)}


def drift_of(mig, snap):
    """Column-name differences between a table as the migrations build it and as the dump has it."""
    a, b = set(mig.columns), set(snap.columns)
    ta = {n: type_key(mig.columns[n]["type"]) for n in a & b}
    tb = {n: type_key(snap.columns[n]["type"]) for n in a & b}
    d = {"only_migrations": sorted(a - b), "only_dump": sorted(b - a), "type_differs": sorted(n for n in ta if ta[n] != tb[n])}
    return {k: v for k, v in d.items() if v}


def drop_split_parts(rels):
    """The Supabase dump writes one composite foreign key as several single-column ones. When a relation between the same two
    tables covers all of those columns, the single-column ones are not separate relationships."""
    keep = []
    for r in rels:
        parts = [o for o in rels if o is not r and o["from"] == r["from"] and o["to"] == r["to"] and len(o["cols"]) > len(r["cols"])
                 and set(r["cols"]) <= set(o["cols"]) and set(r["to_cols"]) <= set(o["to_cols"])]
        if not parts:
            keep.append(r)
    return keep


def relations_of(sources):
    """[(Table, origin)] -> deduped foreign keys. A key found in both the migrations and the dump says so."""
    seen = {}
    for t, origin in sources:
        for f in t.fks:
            k = (t.key, tuple(f["cols"]), f["to"], tuple(f["to_cols"]))
            r = seen.setdefault(k, {"from": t.key, "cols": f["cols"], "to": f["to"], "to_cols": f["to_cols"], "origins": []})
            if origin not in r["origins"]:
                r["origins"].append(origin)
            if f.get("on_delete"):
                r["on_delete"] = f["on_delete"]
    out = []
    for r in seen.values():
        r["origin"] = "both" if len(r["origins"]) > 1 else r["origins"][0]
        del r["origins"]
        out.append(r)
    return sorted(drop_split_parts(out), key=lambda r: (r["from"], r["cols"], r["to"]))


def build_schema(root, census):
    """The whole of data/code/schema.json."""
    root = Path(root)
    sql_files = sorted((census.get("sql") or {}))
    src = source_for(root, census)
    migs = [f for f in sql_files if is_migration(f)]
    snaps = [f for f in sql_files if f.startswith(SNAPSHOT_DIR) and f.endswith(".sql")]
    functions = []
    mig_tables, snap_tables = {}, {}
    mig_summary, snap_schema_of = {}, {}
    if src is not None:
        for f in migs:
            parse_sql(src[f], f, mig_tables, functions)
            mig_summary[f] = first_paragraph(src[f])
        for f in snaps:
            sch = snapshot_schema(f, src[f])
            snap_schema_of[f] = sch
            parse_sql(src[f], f, snap_tables, [], default_schema=sch)
    else:
        for f in migs + snaps:
            found, fn = from_census({"sql": {f: census["sql"][f]}})
            target = mig_tables if f in migs else snap_tables
            for k, v in found.items():
                target.setdefault(k, v)
            functions.extend(fn)
            if f in snaps:
                snap_schema_of[f] = next(iter(found.values())).schema if found else Path(f).stem
    test_paths = {f["path"] for f in census.get("files", []) if f.get("test")}

    out_tables = []
    for key in sorted(set(mig_tables) | set(snap_tables), key=lambda k: (k.split(".")[0] != DEFAULT_SCHEMA, k.split(".")[0], migs.index(mig_tables[k].created_in) if k in mig_tables and mig_tables[k].created_in in migs else -1, k)):
        m, s = mig_tables.get(key), snap_tables.get(key)
        t = m or s
        origin = "both" if (m and s) else ("migrations" if m else "dump")
        rec = table_out(t, origin, ref_buckets(t.name, census, test_paths) if t.schema == DEFAULT_SCHEMA else None)
        if m and s:
            d = drift_of(m, s)
            if d:
                rec["drift"] = d
            for f in s.fks:             # a foreign key only the dump records still belongs to the table
                if not any(x["to"] == f["to"] and set(f["cols"]) <= set(x["cols"]) for x in t.fks):
                    rec.setdefault("fks", []).append({"cols": f["cols"], "to": f["to"], "to_cols": f["to_cols"], **({"on_delete": f["on_delete"]} if f.get("on_delete") else {})})
        out_tables.append(rec)

    sources = [(t, "migrations") for t in mig_tables.values()] + [(t, "dump") for t in snap_tables.values()]
    rels = relations_of(sources)

    migrations = []
    for f in migs:
        creates = [t.key for t in mig_tables.values() if any(x["file"] == f and x["op"] == "create" for x in t.touched)]
        added = [{"table": t.key, "column": c["name"]} for t in mig_tables.values() for c in t.columns.values() if c.get("added_in") == f]
        touched = sorted({t.key for t in mig_tables.values() if any(x["file"] == f for x in t.touched)} - set(creates))
        policies = sum(1 for t in mig_tables.values() for p in t.policies.values() if p["file"] == f)
        indexes = sum(1 for t in mig_tables.values() for i in t.indexes if i["file"] == f)
        fns = sorted({x["name"] for x in functions if x["file"] == f})
        trig = sum(1 for t in mig_tables.values() for g in t.triggers if g["file"] == f)
        migrations.append({"file": f, "id": migration_id(f), "title": re.sub(r"^\d+_", "", Path(f).stem).replace("_", " "), "summary": mig_summary.get(f, ""),
                           "creates": sorted(creates), "adds_columns": added, "touches": touched, "policies": policies, "indexes": indexes,
                           "functions": fns, "triggers": trig})

    schemas = {}
    for f in snaps:
        sch = snap_schema_of.get(f, Path(f).stem)
        n = sum(1 for t in snap_tables.values() if t.schema == sch)
        schemas[sch] = {"name": sch, "tables": n, "file": f}
    for t in mig_tables.values():
        if t.schema not in schemas:
            schemas[t.schema] = {"name": t.schema, "tables": sum(1 for x in mig_tables.values() if x.schema == t.schema), "file": None}
    pub_m = {k for k, t in mig_tables.items() if t.schema == DEFAULT_SCHEMA}
    pub_s = {k for k, t in snap_tables.items() if t.schema == DEFAULT_SCHEMA}
    doc = {
        "schema": DATA_SCHEMA,
        "commit": census["git"]["head"],
        "generated": census["meta"]["generated"][:10],
        "source": "src" if src is not None else "census",
        "schemas": sorted(schemas.values(), key=lambda s: (s["name"] != DEFAULT_SCHEMA, s["name"])),
        "tables": out_tables,
        "relations": rels,
        "migrations": migrations,
        "drift": {"in_migrations_not_in_dump": sorted(pub_m - pub_s), "in_dump_not_in_migrations": sorted(pub_s - pub_m)},
        "dump_files": snaps,
    }
    return doc


# ----------------------------------------------------------------------------- driver
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if data/code/schema.json is out of date")
    args = ap.parse_args(argv)
    root = Path(args.root)
    census = read_json(root / CENSUS_REL)
    if not census:
        sys.exit(f"{root / CENSUS_REL} is missing or not valid JSON")
    new = json_text(build_schema(root, census))
    p = root / SCHEMA_REL
    old = read_text(p) if p.is_file() else None
    if new == old:
        print("data/code/schema.json: up to date")
        return 0
    if args.check:
        print("out of date: data/code/schema.json; run: python scripts/refresh_schema.py")
        return 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(new.encode("utf-8"))
    print("updated:", SCHEMA_REL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
