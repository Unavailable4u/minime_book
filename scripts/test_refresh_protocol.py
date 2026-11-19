#!/usr/bin/env python3
"""
test_refresh_protocol.py -- tests for the Protocol, M2C and Decision-records pages (P24). Standard library only; the JavaScript tests
need `node`, the git tests need `git` (each is skipped without it).

What is checked
  * scripts/refresh_protocol.py, run against a throw-away git repository that stands in for MiniMe: fields ($ref, nesting, enums,
    constants, defaults, limits), the envelope's run_id / seq rules, the tool catalogue (risk and risk_max), one example per message,
    the client-copy comparison, the M2C commands table and package map, and the decision records.
  * the secret rule: a credential-shaped string in a fixture NEVER reaches the output, because its schema field is x-m2c-secret.
  * it reads git, not the working tree: an uncommitted edit and CRLF line endings change nothing.
  * --check: passes on a fresh file, fails once the file is stale or missing; the offline check needs no MiniMe.
  * assets/js/protocolpages.js (the pure helpers) runs under Node, no DOM and no network.
  * the committed data/code/protocol.json is well formed, is at the census commit, lists every type the envelope names, and, with a
    MiniMe checkout at that commit next to this repo, is exactly what the script would write now.
  * the three pages are small shells with their modules, are in the nav, and update_all.py and the CI workflow run the new step.

    python scripts/test_refresh_protocol.py
"""
import contextlib
import importlib.util
import io
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
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("refresh_protocol", ROOT / "scripts" / "refresh_protocol.py")
rp = importlib.util.module_from_spec(_spec)
sys.modules["refresh_protocol"] = rp
_spec.loader.exec_module(rp)

GIT = shutil.which("git")
NODE = shutil.which("node")
CREDENTIAL = "m2c-fixture-credential-0000000000"        # looks like the real fixtures' placeholder; must never be published


def write(base: Path, rel: str, text: str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def jd(obj) -> str:
    return json.dumps(obj, indent=1) + "\n"


COMMON = {"$id": "common.json", "$defs": {
    "uuid": {"type": "string", "pattern": "^[0-9a-f-]{36}$", "description": "A UUID."},
    "run_id": {"type": "string", "description": "Opaque run id."},
    "risk": {"enum": ["R0", "R1", "R2", "R3", "R4"], "description": "R0 read-only, R1 write inside project, R2 run command, R3 network or outside project, R4 irreversible or external effect."},
    "mode": {"enum": ["plan", "ask"], "description": "Permission mode."},
    "text": {"type": "string", "maxLength": 100000}}}
TYPES = {"client_to_server": ["hello", "run.start", "ping"], "server_to_client": ["run_event", "pong"]}
ENVELOPE = {"$id": "envelope.json", "title": "envelope", "description": "Every message.", "x-m2c-types": TYPES, "type": "object",
            "required": ["v", "t", "id"], "additionalProperties": False,
            "properties": {"v": {"const": 1}, "t": {"enum": TYPES["client_to_server"] + TYPES["server_to_client"]},
                           "id": {"$ref": "common.json#/$defs/uuid"}, "run_id": {"$ref": "common.json#/$defs/run_id"}, "seq": {"type": "integer", "minimum": 1}},
            "allOf": [
                {"if": {"properties": {"t": {"const": "hello"}}, "required": ["t"]}, "then": {"properties": {"payload": {"$ref": "hello.json"}}}},
                {"if": {"properties": {"t": {"enum": ["run.start"]}}, "required": ["t"]}, "then": {"required": ["run_id"]}},
                {"if": {"properties": {"t": {"enum": ["hello", "ping", "pong"]}}, "required": ["t"]}, "then": {"not": {"required": ["run_id"]}}},
                {"if": {"properties": {"t": {"enum": ["run_event"]}}, "required": ["t"]}, "then": {"required": ["seq"]}},
                {"if": {"properties": {"t": {"enum": ["hello", "run.start", "ping", "pong"]}}, "required": ["t"]}, "then": {"not": {"required": ["seq"]}}}]}
HELLO = {"title": "hello (client -> server)", "description": "First message.", "x-m2c-data-class": "metadata", "type": "object",
         "required": ["device_credential", "capabilities"], "additionalProperties": False,
         "properties": {"device_credential": {"type": "string", "x-m2c-secret": True},
                        "capabilities": {"type": "array", "maxItems": 32, "items": {"type": "string"}, "description": "Optional features."}}}
RUN_START = {"title": "run.start", "description": "Begin a run.", "type": "object", "required": ["mode", "limits"], "additionalProperties": False,
             "properties": {"mode": {"$ref": "common.json#/$defs/mode", "default": "ask"},
                            "limits": {"type": "object", "required": ["parallel"], "properties": {"parallel": {"type": "integer", "minimum": 1, "maximum": 8}}}}}
SIMPLE = {"title": "empty", "description": "No fields.", "type": "object", "additionalProperties": False, "properties": {}}
RUN_EVENT = {"title": "run_event", "description": "Events.", "type": "object", "required": ["type"], "$defs": {
    "text_delta": {"x-m2c-data-class": "content", "description": "A piece of text.", "type": "object", "required": ["type", "text"], "additionalProperties": False,
                   "properties": {"type": {"const": "text_delta"}, "text": {"$ref": "common.json#/$defs/text"}}}}}
BASH = {"name": "bash", "version": "v0", "risk": "R2", "description": "Run a command.", "input_schema": {"type": "object", "required": ["command"], "properties": {"command": {"type": "string"}}}}
DELETE = {"name": "delete_path", "version": "v0", "risk": "R1", "risk_max": "R4", "description": "Delete.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}


def msg(t, payload, **env):
    base = {"v": 1, "t": t, "id": "00000000-0000-0000-0000-000000000001", "ts": "2026-11-02T09:00:00Z", "payload": payload}
    base.update(env)
    return json.dumps(base)


FIXTURE = "\n".join([
    msg("hello", {"device_credential": CREDENTIAL, "capabilities": ["sandbox"]}),
    msg("run.start", {"mode": "ask", "limits": {"parallel": 2}}, run_id="run_fixture_1"),
    msg("run_event", {"type": "text_delta", "text": "x" * 400}, run_id="run_fixture_1", seq=1),
    msg("ping", {}),
]) + "\n"
README = """# m2c

**Status: early.** It can do two things.

## Commands

| Command | What it does |
|---|---|
| `m2c --version` | Print the version. |
| `m2c login [--name N]` | Sign in with a `code`. |

## Next
"""
ADR1 = "# 0001 \u2014 Scope\n\n**Status:** accepted\n**Context:** a thing.\n\n## Decision\n"
ADR2 = "# 0002 \u2014 Old way\n\n**Status:** superseded \u2014 the `cli/` was removed.\nLeft as history.\n\n**Status (as decided):** accepted\n"


def make_repo(base: Path, *, client_copy: bool = True, crlf: bool = False) -> str:
    """A tiny MiniMe: a protocol folder, its client copy, an m2c package and two decision records. Returns the commit."""
    nl = (lambda s: s.replace("\n", "\r\n")) if crlf else (lambda s: s)
    files = {"protocol/v1/envelope.json": jd(ENVELOPE), "protocol/v1/common.json": jd(COMMON), "protocol/v1/hello.json": jd(HELLO),
             "protocol/v1/run.start.json": jd(RUN_START), "protocol/v1/ping.json": jd(SIMPLE), "protocol/v1/pong.json": jd(SIMPLE),
             "protocol/v1/run_event.json": jd(RUN_EVENT), "protocol/v1/tools/bash.json": jd(BASH), "protocol/v1/tools/delete_path.json": jd(DELETE),
             "protocol/fixtures/01_chat.jsonl": FIXTURE, "protocol/fixtures/invalid_examples.jsonl": "{}\n{}\n",
             "m2c/README.md": README, "m2c/src/m2c/__init__.py": '"""m2c/src/m2c/__init__.py -- Patch C01: the client package.\n\nMore."""\n',
             "m2c/src/m2c/auth/__init__.py": '"""m2c/src/m2c/auth/__init__.py -- Patch C03: signing in, and ``the credential``.\n\nLong."""\n',
             "m2c/src/m2c/auth/login.py": "x = 1\n", "m2c/src/m2c/cli.py": '"""cli.py -- the command."""\n',
             "docs/decisions/0001-scope.md": ADR1, "docs/decisions/0002-old.md": ADR2}
    if client_copy:
        for rel in [k for k in files if k.startswith("protocol/v1/")]:
            files["m2c/src/m2c/protocol/v1/" + rel[len("protocol/v1/"):]] = files[rel]
    for rel, text in files.items():
        write(base, rel, nl(text))
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "PATH": __import__("os").environ["PATH"],
           "HOME": str(base)}
    def run(*a):
        return subprocess.run(["git", "-C", str(base), "-c", "core.autocrlf=false", *a], capture_output=True, text=True, env=env, check=True).stdout.strip()
    run("init", "-q"); run("add", "-A"); run("commit", "-q", "-m", "m")
    return run("rev-parse", "HEAD")


def make_root(base: Path, commit: str) -> Path:
    """A throw-away minime_book root: just a census that names the commit."""
    root = base / "book"
    write(root, "data/census.json", json.dumps({"git": {"head_full": commit, "head": commit[:7]}}))
    return root


@unittest.skipUnless(GIT, "git is not installed")
class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.repo = cls.tmp / "MiniMe"
        cls.repo.mkdir()
        cls.commit = make_repo(cls.repo)
        cls.doc = rp.build(cls.repo, cls.commit)
        cls.msg = {m["type"]: m for m in cls.doc["messages"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_totals_and_directions(self):
        t = self.doc["totals"]
        self.assertEqual((t["messages"], t["client_to_server"], t["server_to_client"], t["run_events"], t["tools"]), (5, 3, 2, 1, 2))
        self.assertEqual([m["type"] for m in self.doc["messages"]], ["hello", "run.start", "ping", "run_event", "pong"])   # the envelope's own order
        self.assertEqual(self.msg["hello"]["direction"], "client_to_server")
        self.assertEqual(self.msg["pong"]["direction"], "server_to_client")
        self.assertEqual(self.doc["versions"], [1])
        self.assertEqual(self.doc["commit"], self.commit)

    def test_fields_resolve_refs_and_nest(self):
        rs = {f["name"]: f for f in self.msg["run.start"]["fields"]}
        self.assertEqual(rs["mode"]["type"], "enum")
        self.assertEqual(rs["mode"]["enum"], ["plan", "ask"])
        self.assertEqual(rs["mode"]["default"], "ask")
        self.assertEqual(rs["mode"]["desc"], "Permission mode.")                        # the target's description, through the $ref
        self.assertTrue(rs["mode"]["required"])
        inner = rs["limits"]["fields"][0]
        self.assertEqual((inner["name"], inner["type"], inner["limits"], inner["required"]), ("parallel", "integer", "1\u20138", True))
        caps = {f["name"]: f for f in self.msg["hello"]["fields"]}["capabilities"]
        self.assertEqual((caps["type"], caps["limits"], caps["required"]), ("array<string>", "\u2264 32 items", True))

    def test_envelope_fields_and_description(self):
        names = [f["name"] for f in self.doc["envelope"]["fields"]]
        self.assertEqual(names, ["v", "t", "id", "run_id", "seq"])
        env = {f["name"]: f for f in self.doc["envelope"]["fields"]}
        self.assertEqual(env["v"]["const"], 1)
        self.assertEqual(env["id"]["desc"], "A UUID.")

    def test_routing_rules_come_from_the_envelope(self):
        got = {t: (m["run_id"], m["seq"]) for t, m in self.msg.items()}
        self.assertEqual(got["hello"], ("forbidden", "forbidden"))
        self.assertEqual(got["run.start"], ("required", "forbidden"))
        self.assertEqual(got["run_event"], ("optional", "required"))       # no branch names run_event for run_id: left optional, not guessed
        self.assertEqual(got["pong"], ("forbidden", "forbidden"))

    def test_tools_and_risk(self):
        tools = {t["name"]: t for t in self.doc["tools"]}
        self.assertEqual((tools["bash"]["risk"], tools["bash"].get("risk_max"), tools["bash"]["required"]), ("R2", None, ["command"]))
        self.assertEqual((tools["delete_path"]["risk"], tools["delete_path"]["risk_max"]), ("R1", "R4"))
        self.assertEqual(tools["bash"]["fields"][0]["name"], "command")
        self.assertIn("R0 read-only", self.doc["enums"]["risk"]["description"])
        self.assertEqual(self.doc["enums"]["risk"]["values"], ["R0", "R1", "R2", "R3", "R4"])
        self.assertNotIn("uuid", self.doc["enums"])                                   # only $defs that are enums

    def test_run_event_subtypes(self):
        ev = self.doc["run_events"][0]
        self.assertEqual((ev["type"], ev["data_class"]), ("text_delta", "content"))
        self.assertEqual([f["name"] for f in ev["fields"]], ["type", "text"])
        self.assertEqual(ev["example"]["message"]["payload"]["type"], "text_delta")
        self.assertNotIn("example", self.msg["run_event"])                            # run_event's examples live on its subtypes

    def test_example_cuts_long_values(self):
        text = self.doc["run_events"][0]["example"]["message"]["payload"]["text"]
        self.assertLess(len(text), 200)
        self.assertTrue(text.endswith("\u2026"))
        ex = self.msg["run.start"]["example"]
        self.assertEqual((ex["fixture"], ex["line"]), ("01_chat.jsonl", 2))

    def test_secret_fields_never_reach_the_output(self):
        ex = self.msg["hello"]["example"]["message"]["payload"]
        self.assertEqual(ex["device_credential"], rp.REDACTED)
        self.assertEqual(ex["capabilities"], ["sandbox"])
        self.assertTrue({f["name"]: f for f in self.msg["hello"]["fields"]}["device_credential"]["secret"])
        self.assertNotIn(CREDENTIAL, json.dumps(self.doc))
        self.assertNotIn(CREDENTIAL, (rp.build_index.dumps(self.doc)))

    def test_fixtures_listed_with_message_counts(self):
        fx = {f["name"]: f for f in self.doc["fixtures"]}
        self.assertEqual(fx["01_chat.jsonl"]["kind"], "transcript")
        self.assertEqual(fx["01_chat.jsonl"]["types"], {"hello": 1, "ping": 1, "run.start": 1, "run_event": 1})
        self.assertEqual((fx["invalid_examples.jsonl"]["kind"], fx["invalid_examples.jsonl"]["messages"]), ("invalid", 2))
        self.assertEqual(self.msg["hello"]["fixtures"], [{"name": "01_chat.jsonl", "count": 1}])
        self.assertEqual(self.msg["pong"]["fixtures"], [])
        self.assertEqual(self.doc["totals"]["fixtures"], 1)                           # the invalid file is not a transcript

    def test_client_copy_identical(self):
        c = self.doc["client_copy"]
        self.assertEqual((c["state"], c["differs"], c["missing"], c["extra"]), ("identical", [], [], []))
        self.assertEqual(c["files"], 9)

    def test_m2c_section(self):
        m = self.doc["m2c"]
        self.assertEqual(m["status"], "early")
        self.assertEqual(m["doc"], "Patch C01: the client package.")                  # the 'path -- ' lead-in is dropped
        self.assertEqual(m["commands"], [{"command": "m2c --version", "what": "Print the version."}, {"command": "m2c login [--name N]", "what": "Sign in with a code."}])
        pk = {p["name"]: p for p in m["packages"]}
        self.assertEqual((pk["auth"]["kind"], pk["auth"]["files"]), ("package", 2))
        self.assertEqual(pk["auth"]["doc"], "Patch C03: signing in, and the credential.")   # reStructuredText literals are plain text
        self.assertEqual((pk["cli.py"]["kind"], pk["cli.py"]["doc"]), ("module", "the command."))
        self.assertTrue(pk["protocol"]["client_copy"])
        self.assertNotIn("__init__.py", pk)                                           # the root marker is not a "module"
        self.assertEqual([p["name"] for p in m["packages"]][:2], ["auth", "protocol"])   # packages first, then modules

    def test_adrs(self):
        a = self.doc["adrs"]
        self.assertEqual([(x["number"], x["title"], x["status"]) for x in a], [("0001", "Scope", "accepted"), ("0002", "Old way", "superseded")])
        self.assertEqual(a[1]["status_text"], "superseded \u2014 the cli/ was removed. Left as history.")   # first Status line only, backticks gone
        self.assertEqual(a[0]["status_text"], "accepted")

    def test_deterministic(self):
        self.assertEqual(rp.build_index.dumps(self.doc), rp.build_index.dumps(rp.build(self.repo, self.commit)))
        self.assertRegex(self.doc["generated"], r"^\d{4}-\d{2}-\d{2}$")


@unittest.skipUnless(GIT, "git is not installed")
class FromGit(unittest.TestCase):
    def test_client_copy_differs_and_missing(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "m"; repo.mkdir()
            commit = make_repo(repo)
            write(repo, "m2c/src/m2c/protocol/v1/hello.json", jd({**HELLO, "description": "changed"}))
            (repo / "m2c/src/m2c/protocol/v1/ping.json").unlink()
            write(repo, "m2c/src/m2c/protocol/v1/extra.json", "{}")
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"], check=True)
            head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            c = rp.build(repo, head)["client_copy"]
            self.assertEqual((c["state"], c["differs"], c["missing"], c["extra"]), ("differs", ["hello.json"], ["ping.json"], ["extra.json"]))
            self.assertNotEqual(commit, head)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_client_copy(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "m"; repo.mkdir()
            commit = make_repo(repo, client_copy=False)
            self.assertEqual(rp.build(repo, commit)["client_copy"]["state"], "none")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_reads_git_not_the_working_tree(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "m"; repo.mkdir()
            commit = make_repo(repo)
            before = rp.build_index.dumps(rp.build(repo, commit))
            write(repo, "protocol/v1/hello.json", jd({**HELLO, "description": "EDITED, NOT COMMITTED"}))      # an uncommitted edit
            write(repo, "docs/decisions/0009-new.md", "# 0009 \u2014 New\n\n**Status:** accepted\n")           # an untracked file
            self.assertEqual(rp.build_index.dumps(rp.build(repo, commit)), before)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_crlf_checkout_gives_the_same_data(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            a, b = tmp / "a", tmp / "b"; a.mkdir(); b.mkdir()
            ca, cb = make_repo(a), make_repo(b, crlf=True)
            da, db = rp.build(a, ca), rp.build(b, cb)
            for d in (da, db):
                d.pop("commit"); d.pop("short"); d.pop("generated")
                for f in d["fixtures"]:
                    f.pop("blob"); f.pop("path", None)
                for x in d["adrs"]:
                    x.pop("blob")
                for p in d["m2c"]["packages"]:
                    p.pop("bytes")
            self.assertEqual(da["messages"], db["messages"])
            self.assertEqual(da["m2c"]["commands"], db["m2c"]["commands"])
            self.assertEqual(da["adrs"], db["adrs"])
            self.assertEqual(da["fixtures"], db["fixtures"])
            self.assertEqual(da["m2c"]["packages"], db["m2c"]["packages"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_repo_without_protocol_is_refused(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "m"; repo.mkdir()
            write(repo, "README.md", "x")
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"], check=True)
            head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            with self.assertRaises(SystemExit):
                rp.build(repo, head)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_listed_type_without_a_schema_is_an_error(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            repo = tmp / "m"; repo.mkdir()
            make_repo(repo)
            subprocess.run(["git", "-C", str(repo), "rm", "-q", "protocol/v1/pong.json"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"], check=True)
            head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            with self.assertRaises(SystemExit) as cm:
                rp.build(repo, head)
            self.assertIn("pong.json", str(cm.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(GIT, "git is not installed")
class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "MiniMe"; self.repo.mkdir()
        self.commit = make_repo(self.repo)
        self.root = make_root(self.tmp, self.commit)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rp.main(["--root", str(self.root), *args])
        return code, out.getvalue() + err.getvalue()

    def test_write_then_check(self):
        code, out = self.run_main("--minime", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertIn("5 message type(s)", out)
        dest = self.root / rp.OUT_FILE
        self.assertTrue(dest.exists())
        self.assertNotIn(b"\r\n", dest.read_bytes())                               # always LF
        self.assertEqual(self.run_main("--minime", str(self.repo), "--check")[0], 0)
        self.assertEqual(self.run_main("--check")[0] if False else rp.problems_offline(rp.load_current(self.root), self.commit), [])

    def test_check_fails_when_stale_or_missing(self):
        code, out = self.run_main("--minime", str(self.repo), "--check")
        self.assertEqual(code, 1)
        self.assertIn("out of date", out)
        self.run_main("--minime", str(self.repo))
        dest = self.root / rp.OUT_FILE
        dest.write_text(dest.read_text(encoding="utf-8").replace('"messages":5', '"messages":6'), encoding="utf-8")
        self.assertEqual(self.run_main("--minime", str(self.repo), "--check")[0], 1)

    def test_check_does_not_write(self):
        self.run_main("--minime", str(self.repo), "--check")
        self.assertFalse((self.root / rp.OUT_FILE).exists())

    def test_unknown_minime_is_an_error(self):
        code, out = self.run_main("--minime", str(self.tmp / "nowhere"))
        self.assertEqual(code, 2)
        self.assertIn("not a git checkout", out)

    def test_census_commit_missing_in_minime(self):
        write(self.root, "data/census.json", json.dumps({"git": {"head_full": "0" * 40}}))
        code, out = self.run_main("--minime", str(self.repo))
        self.assertEqual(code, 2)
        self.assertIn("no commit 0000000", out)


class Offline(unittest.TestCase):
    def doc(self):
        return {"schema": 1, "commit": "a" * 40, "envelope": {"fields": []}, "messages": [{"type": "x"}], "run_events": [], "enums": {}, "tools": [],
                "fixtures": [], "client_copy": {}, "m2c": {}, "adrs": [], "totals": {"messages": 1, "tools": 0}}

    def test_good(self):
        self.assertEqual(rp.problems_offline(self.doc(), "a" * 40), [])

    def test_wrong_commit_and_missing_parts(self):
        d = self.doc()
        self.assertIn("is for aaaaaaa, the census is at bbbbbbb", rp.problems_offline(d, "b" * 40)[0])
        d.pop("tools")
        d["totals"]["messages"] = 3
        out = " ".join(rp.problems_offline(d, "a" * 40))
        self.assertIn('no "tools"', out)
        self.assertIn("totals.messages", out)
        self.assertEqual(len(rp.problems_offline(None, "a" * 40)), 1)

    def test_helpers(self):
        self.assertEqual(rp.first_paragraph("a/b.py -- Patch X: does it.\n\nMore.", "a/b.py"), "Patch X: does it.")
        self.assertEqual(rp.first_paragraph(None, "a"), "")
        long = rp.first_paragraph("w " * 400, "a")
        self.assertTrue(long.endswith("\u2026") and len(long) <= 301)
        self.assertEqual(rp.constraints({"minLength": 1, "maxLength": 64}), "1\u201364 chars")
        self.assertEqual(rp.constraints({"minimum": 0}), "\u2265 0")
        self.assertEqual(rp.clean_example({"a": ["x"] * 5, "k": "v"}, {"k"}), {"a": ["x", "x", "x", "\u2026 2 more"], "k": rp.REDACTED})
        self.assertEqual(rp.parse_commands("no table here"), [])


# ---------------------------------------------------------------------------------------------------- the committed data
DATA = ROOT / "data" / "code" / "protocol.json"


@unittest.skipUnless(DATA.exists(), "data/code/protocol.json has not been generated yet")
class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(DATA.read_text(encoding="utf-8"))

    def test_is_at_the_census_commit_and_well_formed(self):
        census = rp.refresh_source.census_commit(ROOT)
        self.assertEqual(rp.problems_offline(self.doc, census), [])

    def test_lists_every_type_the_envelope_names(self):
        named = [f for f in self.doc["envelope"]["fields"] if f["name"] == "t"][0]["enum"]
        self.assertEqual([m["type"] for m in self.doc["messages"]], named)
        self.assertEqual(self.doc["totals"]["messages"], len(named))
        for m in self.doc["messages"]:
            self.assertIn(m["direction"], ("client_to_server", "server_to_client"))
            self.assertIn(m["run_id"], ("required", "forbidden", "optional"))
            self.assertIn(m["seq"], ("required", "forbidden"))

    def test_every_run_event_subtype_the_schema_enumerates_is_present(self):
        ev = [m for m in self.doc["messages"] if m["type"] == "run_event"][0]
        self.assertTrue(ev["fields"][0]["enum"])
        self.assertEqual([e["type"] for e in self.doc["run_events"]], ev["fields"][0]["enum"])

    def test_every_tool_has_a_valid_risk(self):
        levels = set(self.doc["enums"]["risk"]["values"])
        self.assertTrue(self.doc["tools"])
        for t in self.doc["tools"]:
            self.assertIn(t["risk"], levels)
            self.assertIn(t.get("risk_max", t["risk"]), levels)

    def test_no_secret_reaches_the_published_file(self):
        text = DATA.read_text(encoding="utf-8")
        for m in self.doc["messages"]:
            for f in m["fields"]:
                if f.get("secret") and m.get("example"):
                    self.assertEqual(m["example"]["message"]["payload"][f["name"]], rp.REDACTED)
        self.assertNotRegex(text, r"m2c-fixture-credential")
        self.assertNotRegex(text, rp.refresh_source.SECRET_PATTERNS[0][1])      # no private key block either

    def test_matches_what_the_script_writes_now(self):
        minime = ROOT.parent / "MiniMe"
        census = rp.refresh_source.census_commit(ROOT)
        if not GIT or not minime.exists() or not rp.refresh_source.commit_exists(minime, census):
            self.skipTest("no MiniMe checkout with the census commit next to this repo")
        self.assertEqual(rp.build_index.dumps(rp.build(minime, census)), DATA.read_bytes().decode("utf-8"))


# ---------------------------------------------------------------------------------------------------- the JavaScript helpers
def run_node(script: str):
    tmp = Path(tempfile.mkdtemp())
    try:
        (tmp / "explorer").mkdir()
        for name in ("protocolpages.js", "codepages.js", "links.js"):
            shutil.copy(ROOT / "assets/js" / name, tmp / name)
        shutil.copy(ROOT / "assets/js/explorer/router.js", tmp / "explorer" / "router.js")
        (tmp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (tmp / "t.js").write_text(script, encoding="utf-8")
        r = subprocess.run([NODE, "t.js"], cwd=tmp, capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise AssertionError(f"node failed:\n{r.stderr}")
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(NODE and DATA.exists(), "node is not installed, or protocol.json is missing")
class Helpers(unittest.TestCase):
    def test_pure_helpers(self):
        doc = json.loads(DATA.read_text(encoding="utf-8"))
        out = run_node("""
import fs from "node:fs";
import * as P from "./protocolpages.js";
const doc = JSON.parse(fs.readFileSync("__DATA__", "utf8"));
const msgs = P.messageRows(doc), evs = P.eventRows(doc), tools = P.toolRows(doc), all = [...msgs, ...evs, ...tools];
const rt = all.every((r) => P.rowFromHash(all, P.rowHash(r)) === r);
const del = tools.find((t) => t.name === "delete_path");
console.log(JSON.stringify({
  roundTrip: rt, dotted: P.rowHash(msgs.find((m) => m.type === "run.start")), badHash: P.rowFromHash(all, "#m/nope"), junk: P.rowFromHash(all, "#m/%"), none: P.rowFromHash(all, ""),
  risk: P.riskMap(doc), pips: [P.riskPips("R0"), P.riskPips("R4"), P.riskPips("zz")], level: [P.riskLevel("R3"), P.riskLevel("x")],
  deleteText: del ? P.toolRiskText(del) : null, deleteLevel: del ? del.level : null,
  kpis: P.protocolKpis(doc).map((k) => k.value), copy: P.clientCopyInfo(doc).kind,
  copyBad: P.clientCopyInfo({ client_copy: { state: "differs", files: 3, dir: "d", differs: ["a.json"], missing: [], extra: ["b.json"] } }),
  copyNone: P.clientCopyInfo({ client_copy: { state: "none" } }).text,
  flat: P.flattenFields([{ name: "a", fields: [{ name: "b", fields: [{ name: "c" }] }] }, { name: "d" }]).map((f) => f.name + f.depth),
  facts: P.fieldFacts({ enum: ["x", "y"], default: 5, limits: "1-2", const: "k" }), noFacts: P.fieldFacts({}),
  routing: P.routingText({ run_id: "required", seq: "forbidden" }), dir: P.directionLabel("client_to_server"),
  dirHref: P.dirHref("m2c/src/m2c/tui"), fileHref: P.fileHref("protocol/v1/hello.json"),
  adr: P.adrRows(doc).map((a) => [a.number, P.adrBadge(a)[1]]), adrOther: P.adrBadge({ status: "weird" }),
}));
""".replace("__DATA__", DATA.as_posix()))
        self.assertTrue(out["roundTrip"])
        self.assertEqual(out["dotted"], "#m/run.start")
        self.assertIsNone(out["badHash"]); self.assertIsNone(out["junk"]); self.assertIsNone(out["none"])
        self.assertEqual(out["risk"]["R0"], "read-only")
        self.assertEqual(out["risk"]["R4"], "irreversible or external effect")
        self.assertEqual(out["pips"], ["\u25cf\u25cb\u25cb\u25cb\u25cb", "\u25cf\u25cf\u25cf\u25cf\u25cf", ""])
        self.assertEqual(out["level"], [3, -1])
        self.assertEqual(out["kpis"], [doc["totals"]["messages"], doc["totals"]["run_events"], doc["totals"]["tools"], doc["totals"]["fixtures"]])
        self.assertEqual(out["copy"], "ok" if doc["client_copy"]["state"] == "identical" else "stale")
        self.assertEqual(out["copyBad"]["kind"], "stale")
        self.assertIn("1 differ", out["copyBad"]["text"]); self.assertIn("1 extra on the client", out["copyBad"]["text"])
        self.assertEqual(out["copyNone"], "no client copy found")
        self.assertEqual(out["flat"], ["a0", "b1", "c2", "d0"])
        self.assertEqual(out["facts"], ['one of: x, y', 'always "k"', "default 5", "1-2"])
        self.assertEqual(out["noFacts"], [])
        self.assertEqual(out["routing"], "run_id required \u00b7 seq forbidden")
        self.assertEqual(out["dir"], "client \u2192 server")
        self.assertEqual(out["dirHref"], "explorer.html#/d/m2c/src/m2c/tui")
        self.assertEqual(out["fileHref"], "explorer.html#/f/protocol/v1/hello.json")
        self.assertEqual(out["adrOther"], ["here", "see the record"])
        if any(t["name"] == "delete_path" for t in doc["tools"]):
            self.assertEqual(out["deleteText"], "R1 up to R4")
            self.assertEqual(out["deleteLevel"], 4)                              # sorted by the worst call can be, not the usual level

    def test_package_notes(self):
        out = run_node("""
import * as P from "./protocolpages.js";
const index = { files: {
  "m2c/src/m2c/sandbox/run.py": { summary: "Runs a command.", tier: 1, status: "fresh" },
  "m2c/src/m2c/sandbox/__init__.py": { summary: "The sandbox package.", tier: 2, status: "stale" },
  "m2c/src/m2c/sandbox/zz.py": { tier: 1, status: "fresh" },
  "m2c/src/m2c/tui/a.py": { summary: "B tier 2.", tier: 2, status: "fresh" },
  "m2c/src/m2c/tui/b.py": { summary: "A tier 1.", tier: 1, status: "fresh" },
  "m2c/src/m2c/cli.py": { summary: "The command.", tier: 1, status: "fresh" },
  "m2c/src/m2c/cli_extra.py": { summary: "Not cli.py.", tier: 1, status: "fresh" } } };
const pkg = (name, kind = "package") => ({ name, kind, path: "m2c/src/m2c/" + name + (kind === "module" ? "" : "") });
const doc = { m2c: { packages: [{ name: "sandbox", kind: "package", path: "m2c/src/m2c/sandbox", files: 7 }, { name: "cli.py", kind: "module", path: "m2c/src/m2c/cli.py", files: 1 }, { name: "auth", kind: "package", path: "m2c/src/m2c/auth", files: 3 }] } };
const rows = P.packageRows(doc, index);
console.log(JSON.stringify({
  sandbox: rows[0].note, cli: rows[1].note, auth: rows[2].note, none: P.noteForPackage(null, doc.m2c.packages[0]),
  tui: P.noteForPackage(index, { kind: "package", path: "m2c/src/m2c/tui" }).path, hrefs: rows.map((r) => r.href),
  kpis: P.m2cKpis(doc).map((k) => k.value),
}));
""")
        self.assertEqual(out["sandbox"]["path"], "m2c/src/m2c/sandbox/__init__.py")          # __init__ first, whatever its tier
        self.assertEqual(out["sandbox"]["state"], "stale")
        self.assertEqual(out["sandbox"]["count"], 2)                                         # a file without a summary does not count
        self.assertEqual(out["cli"]["path"], "m2c/src/m2c/cli.py")                           # a module matches its own file only
        self.assertIsNone(out["auth"]); self.assertIsNone(out["none"])
        self.assertEqual(out["tui"], "m2c/src/m2c/tui/b.py")                                 # then the lowest tier
        self.assertEqual(out["hrefs"], ["explorer.html#/d/m2c/src/m2c/sandbox", "explorer.html#/f/m2c/src/m2c/cli.py", "explorer.html#/d/m2c/src/m2c/auth"])
        self.assertEqual(out["kpis"], [2, 1, 11, 0])


# ---------------------------------------------------------------------------------------------------- the pages and the wiring
class Pages(unittest.TestCase):
    PAGES = {"protocol.html": ("protocol", "pr-app"), "m2c.html": ("m2c", "m2c-app"), "adrs.html": ("adrs", "adr-app")}

    def test_pages_are_small_shells(self):
        for name, (nav_id, app) in self.PAGES.items():
            html = (ROOT / name).read_text(encoding="utf-8")
            self.assertLess(len(html), 4000, name)
            self.assertIn(f'<body data-page="{nav_id}">', html, name)
            self.assertIn(f'id="{app}"', html, name)
            self.assertIn("noindex", html, name)
            self.assertIn('src="assets/js/protocol.js"', html, name)
            self.assertIn('src="assets/js/shell.js"', html, name)
            self.assertIn("assets/css/protocol.css", html, name)
            self.assertNotIn("<table", html, f"{name} must not carry baked-in data")
            self.assertRegex(html, r"<title>[^<]+ \u00b7 MiniMe Atlas</title>", name)

    def test_modules_and_styles_exist_and_are_wired(self):
        for rel in ("assets/js/protocol.js", "assets/js/protocolpages.js", "assets/css/protocol.css", "content/system/m2c.json"):
            self.assertTrue((ROOT / rel).exists(), rel)
        js = (ROOT / "assets/js/protocol.js").read_text(encoding="utf-8")
        self.assertIn('from "./protocolpages.js"', js)
        self.assertNotIn("innerHTML", js)                                           # text goes in through h(), never as HTML
        self.assertNotIn("localStorage", js)

    def test_stylesheet_uses_tokens_only(self):
        css = (ROOT / "assets/css/protocol.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b", "raw hex colour")
        self.assertNotRegex(css, r"\brgba?\(", "raw rgb colour")
        self.assertIn("var(--gate)", css)                                           # risk is the gate colour
        self.assertIn("prefers-reduced-motion", (ROOT / "assets/css/codepages.css").read_text(encoding="utf-8"))

    def test_nav_has_the_pages_in_the_right_wings(self):
        nav = json.loads((ROOT / "content/nav.json").read_text(encoding="utf-8"))
        where = {i["id"]: (w["id"], i) for w in nav["wings"] for i in w["items"]}
        self.assertEqual(where["protocol"][0], "code")
        self.assertEqual(where["m2c"][0], "code")
        self.assertEqual(where["adrs"][0], "project")
        for nid, (wing, item) in where.items():
            if nid in ("protocol", "m2c", "adrs"):
                self.assertTrue((ROOT / item["url"]).exists(), item["url"])
                self.assertTrue(item["blurb"] and item["keywords"], nid)
        self.assertEqual(where["protocol"][1]["layout"], "workbench")
        ids = [i["id"] for w in nav["wings"] for i in w["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_m2c_text_points_at_real_pages(self):
        text = json.loads((ROOT / "content/system/m2c.json").read_text(encoding="utf-8"))
        self.assertTrue(text["intro"])
        for b in text["book"]:
            self.assertTrue((ROOT / b["url"].split("#")[0]).exists(), b["url"])

    def test_update_all_and_ci_run_the_new_step(self):
        ua = (ROOT / "scripts/update_all.py").read_text(encoding="utf-8")
        self.assertIn("scripts/refresh_protocol.py", ua)
        self.assertIn("protocol + [\"--check\"]", ua)
        self.assertIn("scripts/test_refresh_protocol.py", ua)
        self.assertLess(ua.index("scripts/refresh_protocol.py"), ua.index("Verifying nothing is stale"))
        wf = (ROOT / ".github/workflows/site-check.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/refresh_protocol.py --check", wf)
        self.assertIn("python3 scripts/test_refresh_protocol.py", wf)

    def test_search_index_lists_the_new_pages(self):
        idx = json.loads((ROOT / "data/index/search.json").read_text(encoding="utf-8"))
        urls = {p["url"] for p in idx["pages"]}
        self.assertTrue({"protocol.html", "m2c.html", "adrs.html"} <= urls)


if __name__ == "__main__":
    unittest.main(verbosity=1)
