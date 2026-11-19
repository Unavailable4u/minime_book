#!/usr/bin/env python3
"""
refresh_protocol.py -- the data behind the Protocol, M2C and Decision-records pages (P24, plan section 8).

    python scripts/refresh_protocol.py --minime ../MiniMe           # write data/code/protocol.json
    python scripts/refresh_protocol.py --minime ../MiniMe --check   # change nothing; exit 1 if the file is out of date
    python scripts/refresh_protocol.py --check                      # no MiniMe here: prove the file is well formed and at the census commit

Why: MiniMe's `protocol/` folder is the single source of truth for what the device client (`m2c/`) and the server
(`backend/codeagent/`) say to each other. The pages must show THAT, not a hand-typed copy of it, so everything here is read
FROM GIT AT THE CENSUS COMMIT (`git ls-tree` + `git cat-file`), never from the working tree. CRLF checkouts and uncommitted
edits therefore cannot change the result, and the commit shown on the page is the one the Explorer links point at.

What it reads (all at the census commit)
    protocol/v1/*.json         envelope.json (routing rules), common.json (shared enums), one payload schema per message type,
                               run_event.json ($defs: one per subtype)
    protocol/v1/tools/*.json   the tool catalogue: description, input schema, risk (and risk_max)
    protocol/fixtures/*.jsonl  golden transcripts and the invalid examples: listed, and used to pick one real example per message
    m2c/src/m2c/protocol/v1/   the client's copy of the schemas: compared blob by blob with protocol/v1 (the "client copy" chip)
    m2c/README.md              status line and the commands table
    m2c/src/m2c/**             the package map: file counts and the first paragraph of each package's own docstring
    docs/decisions/*.md        the decision records (ADRs): number, title, status

What it writes: data/code/protocol.json (sorted keys, no timestamps: `generated` is the commit's own date, so `--check`
can compare byte for byte).

Secrets: a field a schema marks `x-m2c-secret` is replaced by a placeholder in the example shown on the page, whatever the
fixture holds, so the credential-shaped strings in the fixtures never reach the site.

Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True      # no __pycache__ next to the scripts

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_index  # noqa: E402
import refresh_source  # noqa: E402  (git helpers and census_commit: one implementation for the whole repo)

ROOT = HERE.parent
SCHEMA = 1
OUT_FILE = "data/code/protocol.json"
PROTO_DIR = "protocol/v1/"
TOOLS_DIR = "protocol/v1/tools/"
FIXTURE_DIR = "protocol/fixtures/"
CLIENT_DIR = "m2c/src/m2c/protocol/v1/"
M2C_PKG = "m2c/src/m2c/"
ADR_DIR = "docs/decisions/"
REDACTED = "«redacted: x-m2c-secret»"
MAX_DEPTH = 3                       # nested fields shown (limits{...}, history items, ...)
MAX_STR = 160                       # longest string kept in an example
MAX_ITEMS = 3                       # longest list kept in an example


# ----------------------------------------------------------------------------- git (read only)
def git_text(minime: Path, args: list[str]) -> str:
    r = refresh_source.git(minime, *args)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} failed in {minime}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace").strip()


def decode(data: bytes) -> str:
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


class Repo:
    """The MiniMe tree at one commit: a path -> blob map, and the text of any blob, read once."""

    def __init__(self, minime: Path, commit: str):
        self.minime, self.commit = minime, commit
        self.tree = refresh_source.ls_tree(minime, commit)
        self._text: dict[str, str] = {}

    def paths(self, prefix: str, suffix: str = "") -> list[str]:
        return sorted(p for p in self.tree if p.startswith(prefix) and p.endswith(suffix))

    def blob(self, path: str) -> str | None:
        entry = self.tree.get(path)
        return entry[1] if entry else None

    def load(self, paths: list[str]) -> None:
        want = [self.tree[p][1] for p in paths if p in self.tree and p not in self._text]
        got = refresh_source.read_blobs(self.minime, want)
        for p in paths:
            if p in self.tree and self.tree[p][1] in got:
                self._text[p] = decode(got[self.tree[p][1]])

    def text(self, path: str) -> str | None:
        if path not in self._text:
            self.load([path])
        return self._text.get(path)

    def json(self, path: str):
        t = self.text(path)
        if t is None:
            raise SystemExit(f"{path} is not in MiniMe at {self.commit[:7]}")
        try:
            return json.loads(t)
        except ValueError as e:
            raise SystemExit(f"{path} is not valid JSON: {e}")


# ----------------------------------------------------------------------------- JSON Schema reading
def deref(schema, files: dict, here: str):
    """Follow a $ref ('common.json#/$defs/uuid' or '#/$defs/x'); local keys (a description) win over the target's."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 8:
        seen += 1
        ref = schema["$ref"]
        name, _, ptr = ref.partition("#")
        doc_name = name or here
        node = files.get(doc_name)
        for part in [x for x in ptr.split("/") if x]:
            node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return {k: v for k, v in schema.items() if k != "$ref"}
        merged = dict(node)
        merged.update({k: v for k, v in schema.items() if k != "$ref"})
        schema, here = merged, doc_name
    return schema


def type_text(s: dict, files: dict, here: str) -> str:
    if "enum" in s:
        return "enum"
    if "const" in s:
        return "const"
    t = s.get("type")
    if isinstance(t, list):
        return " | ".join(str(x) for x in t)
    if t == "array":
        items = deref(s.get("items", {}), files, here) if isinstance(s.get("items"), dict) else {}
        inner = type_text(items, files, here) if items else "any"
        return f"array<{inner}>"
    if t:
        return str(t)
    for key in ("oneOf", "anyOf"):
        if key in s:
            return "one of " + str(len(s[key]))
    return "any"


def constraints(s: dict) -> str:
    out = []
    if "minLength" in s or "maxLength" in s:
        out.append(f"{s.get('minLength', 0)}\u2013{s['maxLength']} chars" if "maxLength" in s else f"\u2265 {s['minLength']} chars")
    if "minimum" in s or "maximum" in s:
        lo, hi = s.get("minimum"), s.get("maximum")
        out.append(f"{lo}\u2013{hi}" if lo is not None and hi is not None else (f"\u2265 {lo}" if lo is not None else f"\u2264 {hi}"))
    if "minItems" in s or "maxItems" in s:
        lo, hi = s.get("minItems"), s.get("maxItems")
        out.append(f"{lo}\u2013{hi} items" if lo is not None and hi is not None else (f"\u2265 {lo} items" if lo is not None else f"\u2264 {hi} items"))
    if s.get("uniqueItems"):
        out.append("unique")
    return ", ".join(out)


def fields_of(schema: dict, files: dict, here: str, depth: int = 0) -> list[dict]:
    """One row per property of an object schema (nested objects up to MAX_DEPTH), in the schema's own order."""
    schema = deref(schema, files, here)
    props = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(props, dict):
        return []
    required = set(schema.get("required") or [])
    rows = []
    for name, raw in props.items():
        s = deref(raw if isinstance(raw, dict) else {}, files, here)
        row = {"name": name, "type": type_text(s, files, here), "required": name in required}
        if "enum" in s:
            row["enum"] = list(s["enum"])
        if "const" in s:
            row["const"] = s["const"]
        if "default" in s:
            row["default"] = s["default"]
        if s.get("description"):
            row["desc"] = s["description"]
        c = constraints(s)
        if c:
            row["limits"] = c
        if isinstance(s.get("pattern"), str):
            row["pattern"] = s["pattern"]
        if s.get("x-m2c-secret"):
            row["secret"] = True
        if depth + 1 < MAX_DEPTH:
            target = s
            if s.get("type") == "array" and isinstance(s.get("items"), dict):
                target = deref(s["items"], files, here)
            kids = fields_of(target, files, here, depth + 1) if isinstance(target, dict) and isinstance(target.get("properties"), dict) else []
            if kids:
                row["fields"] = kids
        rows.append(row)
    return rows


def secret_names(rows: list[dict]) -> set[str]:
    out: set[str] = set()
    for r in rows:
        if r.get("secret"):
            out.add(r["name"])
        out |= secret_names(r.get("fields", []))
    return out


# ----------------------------------------------------------------------------- envelope rules
def envelope_rules(env: dict) -> dict[str, dict]:
    """{message type: {run_id: required|forbidden|optional, seq: required|forbidden}} read from the envelope's own if/then branches."""
    types = env.get("x-m2c-types", {})
    every = list(types.get("client_to_server", [])) + list(types.get("server_to_client", []))
    rules = {t: {"run_id": "optional", "seq": "optional"} for t in every}
    for branch in env.get("allOf", []):
        cond = (branch.get("if", {}).get("properties", {}).get("t", {}) or {}).get("enum")
        then = branch.get("then", {})
        if not cond:
            continue                          # the payload $ref branches carry a single const, not an enum list
        for field in ("run_id", "seq"):
            state = None
            if field in (then.get("required") or []):
                state = "required"
            elif field in (then.get("not", {}).get("required") or []):
                state = "forbidden"
            if state:
                for t in cond:
                    if t in rules:
                        rules[t][field] = state
    return rules


# ----------------------------------------------------------------------------- fixtures -> one real example per message
def clean_example(value, hide: set[str]):
    """A copy of a fixture value that is safe to publish: secret fields replaced, long strings and lists cut."""
    if isinstance(value, dict):
        return {k: (REDACTED if k in hide else clean_example(v, hide)) for k, v in value.items()}
    if isinstance(value, list):
        out = [clean_example(v, hide) for v in value[:MAX_ITEMS]]
        if len(value) > MAX_ITEMS:
            out.append(f"\u2026 {len(value) - MAX_ITEMS} more")
        return out
    if isinstance(value, str) and len(value) > MAX_STR:
        return value[:MAX_STR] + "\u2026"
    return value


def read_fixtures(repo: Repo) -> tuple[list[dict], list[tuple[str, int, dict]]]:
    """([fixture summary], [(fixture name, line number, message)]) for the valid transcripts, in name order."""
    paths = repo.paths(FIXTURE_DIR, ".jsonl")
    repo.load(paths)
    summary, messages = [], []
    for p in paths:
        name = p.rsplit("/", 1)[-1]
        text = repo.text(p) or ""
        lines = [ln for ln in text.split("\n") if ln.strip()]
        kind = "invalid" if name.startswith("invalid") else "transcript"
        entry = {"name": name, "path": p, "kind": kind, "messages": len(lines), "blob": repo.blob(p)}
        if kind == "transcript":
            counts: dict[str, int] = {}
            for i, ln in enumerate(lines, 1):
                try:
                    msg = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(msg, dict) and isinstance(msg.get("t"), str):
                    counts[msg["t"]] = counts.get(msg["t"], 0) + 1
                    messages.append((name, i, msg))
            entry["types"] = counts
        summary.append(entry)
    return summary, messages


def pick_example(messages, t: str, subtype: str | None, hide: set[str]) -> dict | None:
    for name, line, msg in messages:
        if msg.get("t") != t:
            continue
        payload = msg.get("payload", {})
        if subtype is not None and (not isinstance(payload, dict) or payload.get("type") != subtype):
            continue
        keep = {k: msg[k] for k in ("v", "t", "id", "run_id", "seq", "ts") if k in msg}
        keep["payload"] = clean_example(payload, hide)
        return {"fixture": name, "line": line, "message": keep}
    return None


def fixtures_with(fixtures: list[dict], t: str) -> list[dict]:
    return [{"name": f["name"], "count": f["types"][t]} for f in fixtures if f["kind"] == "transcript" and t in f.get("types", {})]


# ----------------------------------------------------------------------------- the protocol
def build_protocol(repo: Repo) -> dict:
    v1 = repo.paths(PROTO_DIR, ".json")
    repo.load(v1)
    files = {p[len(PROTO_DIR):]: repo.json(p) for p in v1}
    for need in ("envelope.json", "common.json", "run_event.json"):
        if need not in files:
            raise SystemExit(f"protocol/v1/{need} is missing at {repo.commit[:7]}")
    env, common = files["envelope.json"], files["common.json"]
    types = env.get("x-m2c-types", {})
    rules = envelope_rules(env)
    fixtures, fixture_msgs = read_fixtures(repo)

    envelope = {"title": env.get("title", ""), "description": env.get("description", ""), "file": PROTO_DIR + "envelope.json",
                "fields": fields_of(env, files, "envelope.json"), "closed": env.get("additionalProperties") is False}

    messages = []
    for direction in ("client_to_server", "server_to_client"):
        for t in types.get(direction, []):
            name = f"{t}.json"
            schema = files.get(name)
            if schema is None:
                raise SystemExit(f"protocol/v1/{name} is listed in envelope.json but missing at {repo.commit[:7]}")
            rows = fields_of(schema, files, name)
            hide = secret_names(rows)
            msg = {"type": t, "direction": direction, "file": PROTO_DIR + name, "title": schema.get("title", t),
                   "description": schema.get("description", ""), "data_class": schema.get("x-m2c-data-class", ""),
                   "closed": schema.get("additionalProperties") is False, "fields": rows,
                   "run_id": rules[t]["run_id"], "seq": rules[t]["seq"],
                   "fixtures": fixtures_with(fixtures, t)}
            if t != "run_event":
                ex = pick_example(fixture_msgs, t, None, hide)
                if ex:
                    msg["example"] = ex
            messages.append(msg)

    run_events = []
    re_schema = files["run_event.json"]
    for sub, s in (re_schema.get("$defs") or {}).items():
        rows = fields_of(s, files, "run_event.json")
        ex = pick_example(fixture_msgs, "run_event", sub, secret_names(rows))
        item = {"type": sub, "data_class": s.get("x-m2c-data-class", ""), "description": s.get("description", ""), "fields": rows}
        if ex:
            item["example"] = ex
        run_events.append(item)

    enums = {}
    for name, s in (common.get("$defs") or {}).items():
        if isinstance(s, dict) and "enum" in s:
            enums[name] = {"values": list(s["enum"]), "description": s.get("description", "")}

    tools = []
    for p in repo.paths(TOOLS_DIR, ".json"):
        d = repo.json(p)
        item = {"name": d.get("name", p.rsplit("/", 1)[-1][:-5]), "version": d.get("version", ""), "risk": d.get("risk", ""),
                "description": d.get("description", ""), "file": p,
                "required": list((d.get("input_schema") or {}).get("required") or []),
                "fields": fields_of(d.get("input_schema") or {}, files, "tools/" + p.rsplit("/", 1)[-1])}
        if d.get("risk_max"):
            item["risk_max"] = d["risk_max"]
        tools.append(item)

    return {"envelope": envelope, "messages": messages, "run_events": run_events, "enums": enums, "tools": tools,
            "fixtures": fixtures}


def client_copy(repo: Repo) -> dict:
    """Compare protocol/v1/**/*.json with m2c/src/m2c/protocol/v1/**/*.json blob by blob (equal blob id = byte for byte)."""
    server = {p[len(PROTO_DIR):]: repo.blob(p) for p in repo.paths(PROTO_DIR, ".json")}
    client = {p[len(CLIENT_DIR):]: repo.blob(p) for p in repo.paths(CLIENT_DIR, ".json")}
    if not client:
        return {"state": "none", "dir": CLIENT_DIR.rstrip("/"), "files": 0, "differs": [], "missing": [], "extra": []}
    differs = sorted(k for k in server if k in client and server[k] != client[k])
    missing = sorted(k for k in server if k not in client)
    extra = sorted(k for k in client if k not in server)
    return {"state": "identical" if not (differs or missing or extra) else "differs", "dir": CLIENT_DIR.rstrip("/"),
            "files": len(client), "differs": differs, "missing": missing, "extra": extra}


# ----------------------------------------------------------------------------- the M2C client
def first_paragraph(text: str | None, own_path: str) -> str:
    """First paragraph of a module docstring, without the leading 'path -- ' the repo's docstrings start with."""
    if not text:
        return ""
    para = " ".join(text.strip().split("\n\n", 1)[0].split())
    para = re.sub(r"^[\w./-]+\s+--\s+", "", para)
    para = re.sub(r"^[\w./-]+\s+\u2014\s+", "", para)
    para = para.replace("``", "")                       # reStructuredText literals: the page shows plain text
    return para[:300].rstrip() + ("\u2026" if len(para) > 300 else "")


def docstring_of(source: str | None) -> str | None:
    if source is None:
        return None
    try:
        return ast.get_docstring(ast.parse(source), clean=True)
    except (SyntaxError, ValueError):
        return None


def parse_commands(readme: str) -> list[dict]:
    rows, started = [], False
    for ln in readme.split("\n"):
        if not started:
            started = bool(re.match(r"\|\s*Command\s*\|", ln))
            continue
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 2 and not set(cells[0]) <= set("-: "):
            rows.append({"command": cells[0].replace("`", ""), "what": cells[1].replace("`", "")})
    return rows


def build_m2c(repo: Repo) -> dict:
    readme = repo.text("m2c/README.md") or ""
    m = re.search(r"\*\*Status:\s*([^.*\n]+)", readme)
    status = m.group(1).strip().lower() if m else ""
    groups: dict[str, dict] = {}
    for p, (_mode, _blob, size) in repo.tree.items():
        if not p.startswith(M2C_PKG):
            continue
        rel = p[len(M2C_PKG):]
        top, _, rest = rel.partition("/")
        g = groups.setdefault(top, {"name": top, "kind": "package" if rest else "module", "path": M2C_PKG + top, "files": 0, "bytes": 0})
        g["files"] += 1
        g["bytes"] += size
    py = [g["path"] + "/__init__.py" if g["kind"] == "package" else g["path"] for g in groups.values()]
    repo.load([p for p in py if p.endswith(".py")])
    packages = []
    for g in sorted(groups.values(), key=lambda x: (x["kind"] != "package", x["name"])):
        src = g["path"] + "/__init__.py" if g["kind"] == "package" else g["path"]
        g["doc"] = first_paragraph(docstring_of(repo.text(src)), src)
        if g["name"] == "protocol":
            g["client_copy"] = True
        packages.append(g)
    root_doc = first_paragraph(docstring_of(repo.text(M2C_PKG + "__init__.py")), M2C_PKG + "__init__.py")
    return {"status": status, "doc": root_doc, "readme": "m2c/README.md", "commands": parse_commands(readme),
            "packages": [p for p in packages if p["name"] not in ("__pycache__", "__init__.py")]}


# ----------------------------------------------------------------------------- decision records
def build_adrs(repo: Repo) -> list[dict]:
    paths = repo.paths(ADR_DIR, ".md")
    repo.load(paths)
    out = []
    for p in paths:
        text = repo.text(p) or ""
        name = p.rsplit("/", 1)[-1]
        num = re.match(r"(\d+)", name)
        h1 = re.search(r"^#\s+(.+)$", text, re.M)
        title = re.sub(r"^\d+\s*[\u2014\u2013-]\s*", "", h1.group(1).strip()) if h1 else name
        st = re.search(r"^\*\*Status:\*\*\s*(.+?)(?:\n\s*\n|\n\*\*|\Z)", text, re.M | re.S)
        raw = " ".join(st.group(1).split()).replace("`", "") if st else ""
        low = raw.lower()
        kind = "superseded" if low.startswith("superseded") else "accepted" if low.startswith("accepted") else "other"
        out.append({"path": p, "number": num.group(1) if num else "", "title": title, "status": kind,
                    "status_text": raw[:240] + ("\u2026" if len(raw) > 240 else ""), "blob": repo.blob(p)})
    return out


# ----------------------------------------------------------------------------- the file
def build(minime: Path, commit: str) -> dict:
    repo = Repo(minime, commit)
    if not repo.paths(PROTO_DIR, ".json"):
        raise SystemExit(f"MiniMe has no protocol/v1 at {commit[:7]}.")
    proto = build_protocol(repo)
    v = next((f for f in proto["envelope"]["fields"] if f["name"] == "v"), {})
    versions = [v["const"]] if isinstance(v.get("const"), int) else []
    msgs = proto["messages"]
    doc = {
        "schema": SCHEMA, "commit": commit, "short": commit[:7], "generated": git_text(minime, ["show", "-s", "--format=%cs", commit]),
        "versions": versions, "client_copy": client_copy(repo), "m2c": build_m2c(repo), "adrs": build_adrs(repo),
        "totals": {"messages": len(msgs), "client_to_server": sum(1 for m in msgs if m["direction"] == "client_to_server"),
                   "server_to_client": sum(1 for m in msgs if m["direction"] == "server_to_client"),
                   "run_events": len(proto["run_events"]), "tools": len(proto["tools"]),
                   "fixtures": sum(1 for f in proto["fixtures"] if f["kind"] == "transcript"), "enums": len(proto["enums"])},
    }
    for k in ("envelope", "messages", "run_events", "enums", "tools", "fixtures"):
        doc[k] = proto[k]
    return doc


def load_current(root: Path) -> dict | None:
    d = build_index.load_json(root / OUT_FILE, None)
    return d if isinstance(d, dict) and d.get("schema") == SCHEMA else None


def problems_offline(doc: dict | None, census: str) -> list[str]:
    """No MiniMe here: is the committed file well formed, and is it for the census commit?"""
    if not doc:
        return [f"{OUT_FILE} is missing or not schema {SCHEMA}"]
    out = []
    if doc.get("commit") != census:
        out.append(f"{OUT_FILE} is for {str(doc.get('commit'))[:7]}, the census is at {census[:7]}")
    for key in ("envelope", "messages", "run_events", "enums", "tools", "fixtures", "client_copy", "m2c", "adrs", "totals"):
        if key not in doc:
            out.append(f"{OUT_FILE} has no \"{key}\"")
    if isinstance(doc.get("messages"), list):
        listed = (doc.get("envelope") or {}).get("fields")
        if not doc["messages"]:
            out.append("no message types")
        if not isinstance(listed, list):
            out.append("the envelope has no field table")
        t = doc.get("totals") or {}
        if t.get("messages") != len(doc["messages"]):
            out.append("totals.messages does not match the message list")
        if t.get("tools") != len(doc.get("tools", [])):
            out.append("totals.tools does not match the tool list")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Write data/code/protocol.json from MiniMe's protocol/ folder, read from git.")
    ap.add_argument("--minime", default=None, help="the MiniMe checkout (default: ../MiniMe when it exists)")
    ap.add_argument("--root", default=str(ROOT), help="the minime_book checkout (default: this repo)")
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if data/code/protocol.json is out of date")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    commit = refresh_source.census_commit(root)
    minime = Path(args.minime).resolve() if args.minime else (ROOT.parent / "MiniMe")
    have = minime.exists() and refresh_source.git(minime, "rev-parse", "--git-dir").returncode == 0

    if args.check and not have and not args.minime:
        bad = problems_offline(load_current(root), commit)
        for b in bad:
            print(f"protocol: {b}")
        if bad:
            print("protocol: out of date. Run: python scripts/refresh_protocol.py --minime ../MiniMe")
        return 1 if bad else 0
    if not have:
        print(f"{minime} is not a git checkout. Use --minime PATH.", file=sys.stderr)
        return 2
    if not refresh_source.commit_exists(minime, commit):
        print(f"MiniMe has no commit {commit[:7]} (the census commit). Fetch it, or refresh the census from this checkout.", file=sys.stderr)
        return 2

    doc = build(minime, commit)
    text = build_index.dumps(doc)
    dest = root / OUT_FILE
    if args.check:
        have_text = dest.read_bytes().decode("utf-8").replace("\r\n", "\n") if dest.exists() else None
        if have_text != text:
            print(f"protocol: {OUT_FILE} is out of date. Run: python scripts/refresh_protocol.py --minime ../MiniMe")
            return 1
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")
    t = doc["totals"]
    print(f"protocol: {t['messages']} message type(s), {t['run_events']} run_event subtype(s), {t['tools']} tool(s), "
          f"{t['fixtures']} transcript(s), {len(doc['adrs'])} decision record(s) at {commit[:7]}; "
          f"client copy: {doc['client_copy']['state']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
