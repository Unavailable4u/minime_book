#!/usr/bin/env python3
"""
Tests for scripts/refresh_source.py (patch P12). Standard library only.

    python scripts/test_refresh_source.py
    python -m unittest discover -s scripts

Most tests build a throw-away git repository in a temp folder that stands in for MiniMe (they are skipped when git is not
installed): a normal file, a path with spaces, a CRLF file, a real .env, a key file, a lockfile, an oversized file, a binary
file, a non-UTF-8 file, a symlink, and files that contain a PLANTED FAKE SECRET, one in a normal folder and one under tests/.
A few tests check the repo itself: the config, the deny list, the CI and update_all wiring, and, when data/src exists,
that it agrees with its own manifest.
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("refresh_source", ROOT / "scripts" / "refresh_source.py")
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)

_spec2 = importlib.util.spec_from_file_location("update_all", ROOT / "scripts" / "update_all.py")
update_all = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(update_all)

HAVE_GIT = shutil.which("git") is not None
FAKE_KEY = "sk-" + "A1b2C3d4" * 3            # planted in the throw-away repo; never a real key
FAKE_GH = "ghp_" + "x9Y8" * 9


def sh(repo, *args, input=None):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, input=input)
    if r.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout.decode("utf-8", "replace").strip()


def write(repo: Path, rel: str, data):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


def commit_all(repo: Path, msg="c") -> str:
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", msg)
    return sh(repo, "rev-parse", "HEAD")


def make_minime(tmp: Path) -> tuple[Path, str]:
    """A tiny repo with one example of everything the copier has to decide about. Returns (path, HEAD)."""
    repo = tmp / "MiniMe"
    repo.mkdir()
    sh(repo, "init", "-q")
    sh(repo, "config", "user.email", "t@example.com")
    sh(repo, "config", "user.name", "t")
    sh(repo, "config", "core.autocrlf", "false")
    write(repo, "README.md", "# MiniMe\n")
    write(repo, "backend/app.py", "def main():\n    return 1\n")
    write(repo, "docs/my notes/with space.md", "spaces in the path\n")
    write(repo, "windows.py", b"a = 1\r\nb = 2\r\n")                       # committed with CRLF on purpose
    write(repo, ".env", "SUPABASE_KEY=abc\n")                                # a real .env: refused
    write(repo, ".env.example", "SUPABASE_KEY=\n")                           # the template: copied
    write(repo, "certs/server.pem", "not really a key\n")                    # key material by name: refused
    write(repo, "frontend/package-lock.json", '{"lock": true}\n')           # deny list
    write(repo, "backend/data/chats/c.json", '{"chat": "private"}\n')       # deny list
    write(repo, "protocol/fixtures/a.jsonl", '{"a": 1}\n')                  # deny list
    write(repo, "big.txt", "x" * (rs.MAX_BYTES + 10))                        # too large
    write(repo, "logo.bin", b"\x00\x01\x02binary")                           # binary
    write(repo, "latin1.txt", "caf\xe9\n".encode("latin-1"))                 # not UTF-8
    write(repo, "src/leak.py", f'API_KEY = "{FAKE_KEY}"\n')                  # planted fake secret, normal folder: refused
    write(repo, "backend/tests/test_fake.py", f'GH = "{FAKE_GH}"\n')         # planted fake secret under tests/: warning only
    commit_all(repo, "first")
    try:                                                                     # a symlink entry (mode 120000), without needing OS support for links
        blob = sh(repo, "hash-object", "-w", "--stdin", input=b"README.md")
        sh(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},link-to-readme")
        sh(repo, "commit", "-q", "-m", "symlink")
    except AssertionError:
        pass
    return repo, sh(repo, "rev-parse", "HEAD")


def make_root(tmp: Path, commit: str, deny="package-lock.json\n*.jsonl\nbackend/data/**\n") -> Path:
    root = tmp / "book"
    (root / "data").mkdir(parents=True)
    (root / "data" / "census.json").write_text(json.dumps({"git": {"head": commit[:7], "head_full": commit}}), encoding="utf-8")
    (root / "data" / "src-denylist.txt").write_text(deny, encoding="utf-8")
    return root


def quiet(fn, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = fn(*a, **kw)
    return rc, out.getvalue()


# --------------------------------------------------------------------------- pure rules
class Rules(unittest.TestCase):
    DENY = ["package-lock.json", "*.jsonl", "backend/data/**"]

    def test_real_env_and_key_files_are_refused_but_templates_are_not(self):
        for p in (".env", "backend/.env", ".env.local", ".env.production", "a/server.pem", "k.key", "x.p12", "x.pfx", "BACKEND/.ENV"):
            self.assertEqual(rs.always_refused(p), "env", p)
        for p in (".env.example", ".env.sample", ".env.template", ".env.dist", "env.py", "environment.md", "monkey.keyboard"):
            self.assertIsNone(rs.always_refused(p), p)

    def test_names_that_sound_secret_are_still_source(self):
        # judged by content, never by name (plan 6.4): these are ordinary modules in MiniMe
        for p in ("m2c/src/m2c/auth/credentials.py", "m2c/src/m2c/secrets/store.py", "backend/utils/token_helper.py"):
            self.assertIsNone(rs.classify(p, "100644", 100, self.DENY), p)

    def test_classify(self):
        c = lambda p, mode="100644", size=10: rs.classify(p, mode, size, self.DENY)
        self.assertEqual(c("x", "160000"), "submodule")
        self.assertEqual(c("x", "120000"), "symlink")
        self.assertEqual(c("a/../b.py"), "unsafe-path")
        self.assertEqual(c("a:b.py"), "unsafe-path")
        self.assertEqual(c("a\\b.py"), "unsafe-path")
        self.assertEqual(c("frontend/package-lock.json"), "denylist")
        self.assertEqual(c("protocol/fixtures/x.jsonl"), "denylist")
        self.assertEqual(c("backend/data/chats/x.json"), "denylist")
        self.assertEqual(c("big.py", size=rs.MAX_BYTES + 1), "too-large")
        self.assertIsNone(c("big.py", size=rs.MAX_BYTES))
        self.assertEqual(c(".env"), "env")
        self.assertIsNone(c("backend/app.py"))

    def test_in_tests(self):
        for p in ("backend/tests/x.py", "m2c/tests/secret_handling/a.py", "a/fixtures/b.json", "a/test_x.py", "conftest.py", "a/b.test.mjs", "a/b.spec.js", "a/__tests__/c.js"):
            self.assertTrue(rs.in_tests(p), p)
        for p in ("backend/app.py", "backend/testing_tools.py", "contests/x.py", "m2c/src/m2c/secrets/store.py"):
            self.assertFalse(rs.in_tests(p), p)

    def test_decode_text(self):
        self.assertEqual(rs.decode_text("héllo".encode("utf-8")), "héllo")
        self.assertIsNone(rs.decode_text(b"a\x00b"))
        self.assertIsNone(rs.decode_text("caf\xe9".encode("latin-1")))

    def test_blob_id_is_gits(self):
        self.assertEqual(rs.git_blob_id(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")
        self.assertEqual(rs.git_blob_id(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_regex_scan_finds_the_planted_secrets_and_never_returns_them(self):
        samples = {
            "private key": "-----BEGIN RSA PRIVATE KEY-----\nMIIB\n",
            "AWS access key": "k = 'AKIA" + "ABCDEFGHIJKLMNOP" + "'",
            "GitHub token": f"t = '{FAKE_GH}'",
            "API secret key": f"k = '{FAKE_KEY}'",
            "Slack token": "xoxb-" + "1234567890-abcdef",
            "JWT": "eyJ" + "a" * 20 + "." + "b" * 20 + "." + "c" * 12,
            "long credential assignment": 'password = "correct-horse-battery-staple"',
        }
        for label, text in samples.items():
            hits = rs.regex_scan(text)
            self.assertTrue(any(label in h for h in hits), (label, hits))
            self.assertIn("line 1", " ".join(hits))
            for h in hits:                                   # a report line is a label and a line number, nothing else
                self.assertNotIn(text.strip()[8:30], h)
        self.assertEqual(rs.regex_scan("password = os.environ['PASSWORD']\nsecret = None\nkey = 'short'\n"), [])
        self.assertIn("line 3", rs.regex_scan("a\nb\n" + f'token = "{FAKE_KEY}"')[0])

    def test_denylist_file_parsing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "data").mkdir()
            (root / "data" / "src-denylist.txt").write_bytes(b"# comment\r\n\r\n*.lock  # trailing comment\r\nbackend/data/**\r\n   \r\n")
            self.assertEqual(rs.load_denylist(root), ["*.lock", "backend/data/**"])
            self.assertEqual(rs.load_denylist(root / "nowhere"), [])

    def test_rules_id_changes_with_every_rule(self):
        a = rs.rules_id(["a"], "regex")
        self.assertEqual(a, rs.rules_id(["a"], "regex"))
        self.assertNotEqual(a, rs.rules_id(["a", "b"], "regex"))
        self.assertNotEqual(a, rs.rules_id(["a"], "gitleaks"))


class GitleaksReport(unittest.TestCase):
    def test_parse_keeps_rule_id_and_line_only(self):
        stage = Path("/tmp/x/stage")
        report = json.dumps([
            {"RuleID": "generic-api-key", "File": "/tmp/x/stage/backend/a.py", "StartLine": 7, "Secret": "TOPSECRETVALUE", "Match": "key = TOPSECRETVALUE"},
            {"RuleID": "aws-access-token", "File": "/tmp/x/stage/backend/a.py", "StartLine": 9, "Secret": "TOPSECRETVALUE"},
            {"File": "", "RuleID": "ignored"},
            "junk",
        ])
        out = rs.parse_gitleaks_report(report, stage)
        self.assertEqual(out, {"backend/a.py": ["generic-api-key (line 7)", "aws-access-token (line 9)"]})
        self.assertNotIn("TOPSECRETVALUE", json.dumps(out))

    def test_parse_empty_and_bad(self):
        self.assertEqual(rs.parse_gitleaks_report("", Path("/s")), {})
        self.assertEqual(rs.parse_gitleaks_report("null", Path("/s")), {})
        with self.assertRaises(RuntimeError):
            rs.parse_gitleaks_report("not json", Path("/s"))


# --------------------------------------------------------------------------- against a real git repo
@unittest.skipUnless(HAVE_GIT, "git is not installed")
class Plan(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo, self.head = make_minime(self.tmp)
        self.root = make_root(self.tmp, self.head)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self, prev=None, **kw):
        kw.setdefault("scanner", "regex")
        return rs.build_plan(self.repo, self.head, self.root, prev, log=lambda *_: None, **kw)

    def test_who_gets_copied_and_why_not(self):
        p = self.plan()
        files, skipped = p["manifest"]["files"], p["manifest"]["skipped"]
        for path in ("README.md", "backend/app.py", "docs/my notes/with space.md", "windows.py", ".env.example", "backend/tests/test_fake.py"):
            self.assertIn(path, files, path)
        why = {k: v["why"] for k, v in skipped.items()}
        self.assertEqual(why[".env"], "env")
        self.assertEqual(why["certs/server.pem"], "env")
        self.assertEqual(why["frontend/package-lock.json"], "denylist")
        self.assertEqual(why["backend/data/chats/c.json"], "denylist")
        self.assertEqual(why["protocol/fixtures/a.jsonl"], "denylist")
        self.assertEqual(why["big.txt"], "too-large")
        self.assertEqual(why["logo.bin"], "binary")
        self.assertEqual(why["latin1.txt"], "not-utf8")
        self.assertEqual(why["src/leak.py"], "secret")
        if "link-to-readme" in why:                                     # only when the symlink entry could be made
            self.assertEqual(why["link-to-readme"], "symlink")
        self.assertEqual(set(files) & set(skipped), set(), "a file is either copied or skipped")
        self.assertEqual(set(p["writes"]), set(files))

    def test_planted_secret_is_refused_and_a_fake_under_tests_is_only_a_warning(self):
        p = self.plan()
        self.assertNotIn("src/leak.py", p["writes"])
        self.assertEqual([r.split(":")[0] for r in p["refused"] if "leak.py" in r], ["src/leak.py"])
        self.assertTrue(any(r.startswith(".env:") for r in p["refused"]))
        self.assertTrue(any(r.startswith("certs/server.pem:") for r in p["refused"]))
        self.assertTrue(any("backend/tests/test_fake.py" in w for w in p["warnings"]))
        self.assertIn("backend/tests/test_fake.py", p["manifest"]["warned"])
        self.assertIn("backend/tests/test_fake.py", p["writes"])

    def test_the_secret_itself_is_never_reported(self):
        p = self.plan()
        text = json.dumps(p["manifest"]) + "\n".join(p["refused"]) + "\n".join(p["warnings"])
        for secret in (FAKE_KEY, FAKE_GH, "SUPABASE_KEY=abc"):
            self.assertNotIn(secret, text)
        for path, data in p["writes"].items():                          # and nothing refused was queued for writing
            self.assertNotIn(FAKE_KEY.encode(), data, path)

    def test_copies_are_the_committed_bytes_and_their_blob_ids_are_gits(self):
        p = self.plan()
        for path, data in p["writes"].items():
            self.assertEqual(rs.git_blob_id(data), p["manifest"]["files"][path], path)
            self.assertEqual(sh(self.repo, "rev-parse", f"{self.head}:{path}"), p["manifest"]["files"][path], path)
        self.assertEqual(p["writes"]["windows.py"], b"a = 1\r\nb = 2\r\n", "CRLF in the commit stays CRLF; nothing is re-encoded")
        self.assertEqual(p["writes"]["backend/app.py"], b"def main():\n    return 1\n")

    def test_reads_git_not_the_working_tree(self):
        write(self.repo, "backend/app.py", "EDITED but not committed\n")
        write(self.repo, "untracked.py", "never committed\n")
        (self.repo / "README.md").unlink()
        p = self.plan()
        self.assertEqual(p["writes"]["backend/app.py"], b"def main():\n    return 1\n")
        self.assertIn("README.md", p["writes"])
        self.assertNotIn("untracked.py", p["manifest"]["files"])

    def test_apply_then_plan_again_changes_nothing(self):
        p = self.plan()
        rs.apply_plan(self.root, p)
        base = self.root / "data" / "src"
        self.assertEqual((base / "docs/my notes/with space.md.txt").read_bytes(), b"spaces in the path\n")
        self.assertFalse((base / "src/leak.py.txt").exists())
        self.assertFalse((base / ".env.txt").exists())
        self.assertTrue((base / "manifest.json").exists())
        again = self.plan(prev=rs.load_manifest(self.root))
        self.assertEqual(again["writes"], {}, "unchanged blobs are not rewritten")
        self.assertEqual(again["deletes"], [])
        self.assertEqual(again["manifest"], p["manifest"], "same inputs, same manifest")
        self.assertEqual(again["refused"], p["refused"], "refusals are repeated on every run")

    def test_manifest_file_is_deterministic_lf_json(self):
        rs.apply_plan(self.root, self.plan())
        raw = (self.root / "data" / "src" / "manifest.json").read_bytes()
        self.assertNotIn(b"\r", raw)
        self.assertEqual(raw.decode("utf-8"), rs.build_index.dumps(json.loads(raw)))

    def test_a_new_commit_rewrites_only_what_changed_and_removes_what_is_gone(self):
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        write(self.repo, "backend/app.py", "def main():\n    return 2\n")
        write(self.repo, "backend/new.py", "x = 1\n")
        (self.repo / "README.md").unlink()
        self.head = commit_all(self.repo, "second")
        p = self.plan(prev=prev)
        self.assertEqual(set(p["writes"]), {"backend/app.py", "backend/new.py"})
        self.assertEqual(p["deletes"], ["README.md"])
        rs.apply_plan(self.root, p)
        base = self.root / "data" / "src"
        self.assertFalse((base / "README.md.txt").exists())
        self.assertEqual((base / "backend/app.py.txt").read_bytes(), b"def main():\n    return 2\n")

    def test_a_missing_or_damaged_copy_is_made_again(self):
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        base = self.root / "data" / "src"
        (base / "backend/app.py.txt").write_bytes(b"truncated")
        (base / "README.md.txt").unlink()
        p = self.plan(prev=prev)
        self.assertEqual(set(p["writes"]), {"backend/app.py", "README.md"})

    def test_a_crlf_checkout_of_data_src_is_not_stale(self):
        # Windows git with core.autocrlf=true turns the committed LF copies into CRLF; the blob id still has to match
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        f = self.root / "data" / "src" / "backend/app.py.txt"
        f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(self.plan(prev=prev)["writes"], {})
        self.assertEqual(rs.check_offline(self.root, self.head, log=lambda *_: None), 0)

    def test_changing_the_denylist_judges_every_file_again(self):
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        (self.root / "data" / "src-denylist.txt").write_text("package-lock.json\n*.jsonl\nbackend/data/**\nbackend/app.py\n", encoding="utf-8")
        p = self.plan(prev=prev)
        self.assertEqual(p["manifest"]["skipped"]["backend/app.py"]["why"], "denylist")
        self.assertIn("backend/app.py", p["deletes"])
        self.assertNotEqual(p["manifest"]["rules"], prev["rules"])

    def test_a_remembered_secret_refusal_survives_until_the_file_changes(self):
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        self.assertEqual(prev["skipped"]["src/leak.py"]["why"], "secret")
        self.assertEqual(self.plan(prev=prev)["manifest"]["skipped"]["src/leak.py"]["why"], "secret")
        write(self.repo, "src/leak.py", 'API_KEY = os.environ["API_KEY"]\n')       # the leak is fixed in MiniMe
        self.head = commit_all(self.repo, "fix")
        p = self.plan(prev=prev)
        self.assertIn("src/leak.py", p["writes"])
        self.assertFalse(any("leak.py" in r for r in p["refused"]))

    def test_force_ignores_remembered_decisions(self):
        rs.apply_plan(self.root, self.plan())
        prev = rs.load_manifest(self.root)
        self.assertEqual(len(self.plan(prev=prev, force=True)["writes"]), len(prev["files"]))

    def test_gitleaks_findings_decide_when_gitleaks_is_the_scanner(self):
        found = {"backend/app.py": ["generic-api-key (line 2)"], "backend/tests/test_fake.py": ["generic-api-key (line 1)"]}
        with mock.patch.object(rs, "gitleaks_scan", return_value=found), mock.patch.object(rs.shutil, "which", return_value="/usr/bin/gitleaks"):
            p = self.plan(scanner="gitleaks")
        self.assertEqual(p["manifest"]["scanner"], "gitleaks")
        self.assertEqual(p["manifest"]["skipped"]["backend/app.py"]["why"], "secret")
        self.assertIn("backend/tests/test_fake.py", p["writes"])
        self.assertIn("backend/tests/test_fake.py", p["manifest"]["warned"])
        self.assertIn("src/leak.py", p["writes"], "with gitleaks the regex fallback is not consulted")

    def test_gitleaks_that_cannot_run_falls_back_to_the_regex_scan(self):
        logged = []
        with mock.patch.object(rs, "gitleaks_scan", side_effect=RuntimeError("boom")), mock.patch.object(rs.shutil, "which", return_value="/usr/bin/gitleaks"):
            p = rs.build_plan(self.repo, self.head, self.root, None, scanner="gitleaks", log=logged.append)
        self.assertEqual(p["manifest"]["scanner"], "regex")
        self.assertEqual(p["manifest"]["rules"], rs.rules_id(rs.load_denylist(self.root), "regex"))
        self.assertTrue(any("gitleaks could not be used" in m for m in logged))
        self.assertEqual(p["manifest"]["skipped"]["src/leak.py"]["why"], "secret")


# --------------------------------------------------------------------------- the command line
@unittest.skipUnless(HAVE_GIT, "git is not installed")
class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo, self.head = make_minime(self.tmp)
        self.root = make_root(self.tmp, self.head)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *extra):
        with mock.patch.object(rs.shutil, "which", return_value=None):          # always the regex scan: same result on every machine
            return quiet(rs.main, ["--minime", str(self.repo), "--root", str(self.root), *extra])

    def test_copy_then_check_then_drift(self):
        rc, out = self.run_cli("--check")
        self.assertEqual(rc, 1, "nothing copied yet")
        self.assertFalse((self.root / "data" / "src").exists(), "--check never writes")
        rc, out = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("REFUSED (not copied): src/leak.py", out)
        self.assertIn("REFUSED (not copied): .env:", out)
        self.assertIn("file(s) embedded at", out)
        self.assertNotIn(FAKE_KEY, out)
        rc, out = self.run_cli("--check")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli()
        self.assertIn("already up to date", out)
        write(self.repo, "backend/app.py", "def main():\n    return 3\n")
        self.head = commit_all(self.repo, "drift")
        (self.root / "data" / "census.json").write_text(json.dumps({"git": {"head_full": self.head}}), encoding="utf-8")
        rc, out = self.run_cli("--check")
        self.assertEqual(rc, 1)
        self.assertIn("out of date", out)
        self.assertEqual((self.root / "data/src/backend/app.py.txt").read_bytes(), b"def main():\n    return 1\n", "--check did not write")

    def test_strict_fails_when_something_was_refused(self):
        self.assertEqual(self.run_cli("--strict")[0], 1)
        self.assertEqual(self.run_cli()[0], 0)

    def test_the_census_commit_decides_not_minimes_head(self):
        old = self.head
        write(self.repo, "backend/app.py", "def main():\n    return 'newer than the census'\n")
        commit_all(self.repo, "newer")
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual((self.root / "data/src/backend/app.py.txt").read_bytes(), b"def main():\n    return 1\n")
        self.assertEqual(rs.load_manifest(self.root)["commit"], old)

    def test_a_census_commit_minime_does_not_have_is_an_error(self):
        (self.root / "data" / "census.json").write_text(json.dumps({"git": {"head_full": "f" * 40}}), encoding="utf-8")
        rc, out = self.run_cli()
        self.assertEqual(rc, 2)
        self.assertIn("has no commit", out)

    def test_a_census_without_a_full_commit_is_an_error(self):
        (self.root / "data" / "census.json").write_text(json.dumps({"git": {"head": self.head[:7]}}), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            self.run_cli()
        self.assertIn("full commit", str(cm.exception))

    def test_minime_that_is_not_a_checkout_is_an_error(self):
        rc, out = quiet(rs.main, ["--minime", str(self.tmp / "nowhere"), "--root", str(self.root)])
        self.assertEqual(rc, 2)

    def test_offline_check(self):
        log = []
        self.assertEqual(rs.check_offline(self.root, self.head, log=log.append), 1)
        self.assertTrue(any("manifest.json is missing" in m for m in log))
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(rs.check_offline(self.root, self.head, log=lambda *_: None), 0)
        base = self.root / "data" / "src"
        (base / "README.md.txt").write_bytes(b"tampered")
        write(self.root, "data/src/stray.py.txt", "not in the manifest")
        log = []
        self.assertEqual(rs.check_offline(self.root, self.head, log=log.append), 1)
        self.assertTrue(any("README.md: missing or different" in m for m in log))
        self.assertTrue(any("stray.py: not in the manifest" in m for m in log))
        log = []
        self.assertEqual(rs.check_offline(self.root, "e" * 40, log=log.append), 1)
        self.assertTrue(any("census is at eeeeeee" in m for m in log))


# --------------------------------------------------------------------------- the repo itself
class Wiring(unittest.TestCase):
    def read(self, rel):
        return (ROOT / rel).read_text(encoding="utf-8")

    def test_config_is_valid(self):
        cfg = json.loads(self.read("content/config.json"))
        self.assertIs(cfg["embedSource"], True)
        self.assertRegex(cfg["github"]["repo"], r"^[\w.-]+/[\w.-]+$")
        self.assertIn(cfg["editor"]["scheme"], ("vscode", "vscode-insiders"))

    def test_deny_list_covers_what_minime_tracks_but_is_not_source(self):
        deny = rs.load_denylist(ROOT)
        self.assertTrue(deny)
        for p in ("frontend/package-lock.json", "backend/evals/promptfoo/package-lock.json", "protocol/fixtures/01_plain_chat.jsonl",
                  "backend/data/chats/chat_cd273d6a9d81.json", "backend/data/graph/_edges.json", "backend/.coverage"):
            self.assertIsNotNone(rs.classify(p, "100644", 10, deny), p)
        for p in ("backend/agents/academic_search.py", "m2c/src/m2c/auth/credentials.py", "protocol/v1/envelope.json", ".env.example",
                  "backend/agents/data/component_dimensions_table.json"):
            self.assertIsNone(rs.classify(p, "100644", 10, deny), p)

    def test_update_all_runs_the_copier_and_its_tests(self):
        src = self.read("scripts/update_all.py")
        for needle in ("refresh_source.py", "--no-embed-source", "test_refresh_source.py", "test_links.py", "embedSource"):
            self.assertIn(needle, src)

    def test_embed_source_switch(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.assertTrue(update_all.embed_source_enabled(root), "no config: on")
            (root / "content").mkdir()
            cfg = root / "content" / "config.json"
            cfg.write_text('{"embedSource": false}', encoding="utf-8")
            self.assertFalse(update_all.embed_source_enabled(root))
            cfg.write_text('{"embedSource": true}', encoding="utf-8")
            self.assertTrue(update_all.embed_source_enabled(root))
            cfg.write_text("{broken", encoding="utf-8")
            self.assertTrue(update_all.embed_source_enabled(root), "unreadable config: on")
        self.assertTrue(update_all.embed_source_enabled(ROOT))

    def test_ci_checks_the_embedded_source(self):
        wf = self.read(".github/workflows/site-check.yml")
        for needle in ("refresh_source.py --check", "test_refresh_source.py", "test_links.py"):
            self.assertIn(needle, wf)

    def test_vercel_serves_the_source_as_plain_text(self):
        rules = {r["source"]: {h["key"]: h["value"] for h in r["headers"]} for r in json.loads(self.read("vercel.json"))["headers"]}
        h = rules["/data/src/(.*)"]
        self.assertEqual(h["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")

    def test_git_never_converts_the_copies(self):
        self.assertRegex(self.read(".gitattributes"), r"(?m)^data/src/\*\* -text")

    def test_updating_md_explains_it(self):
        md = self.read("UPDATING.md")
        for needle in ("refresh_source.py", "data/src", "src-denylist.txt", "--no-embed-source"):
            self.assertIn(needle, md)

    def test_data_src_agrees_with_its_manifest_when_it_exists(self):
        if not (ROOT / "data" / "src" / "manifest.json").exists():
            self.skipTest("data/src has not been generated yet: python scripts/refresh_source.py --minime ../MiniMe")
        census = json.loads(self.read("data/census.json"))
        commit = rs.build_code.commit_of(census)
        log = []
        self.assertEqual(rs.check_offline(ROOT, commit, log=log.append), 0, "\n".join(log))


if __name__ == "__main__":
    unittest.main(verbosity=2)
