#!/usr/bin/env python3
"""Tests for assets/js/links.js (patch P12). Run: python scripts/test_links.py

links.js is pure (no DOM at import time), so it is exercised in Node with no browser. The tests that need Node are
skipped, not failed, when `node` is not on PATH. Standard library only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
LINKS = ROOT / "assets" / "js" / "links.js"
C40 = "3727ae323c26919558a3b5f6db73c81a578537fb"


def run_node(body: str, data: dict | None = None):
    """Run `body` (ES module code that can use `L`, the links.js exports, and `data`) next to a copy of links.js; return its JSON stdout."""
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy(LINKS, tmp / "links.mjs")
        (tmp / "data.json").write_text(json.dumps(data if data is not None else {}), encoding="utf-8")
        (tmp / "run.mjs").write_text(
            "import * as L from './links.mjs'; import fs from 'node:fs';\n"
            "const data = JSON.parse(fs.readFileSync('data.json', 'utf8'));\n" + body, encoding="utf-8")
        res = subprocess.run([NODE, "run.mjs"], cwd=tmp, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            raise AssertionError(res.stderr)
        return json.loads(res.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(NODE, "node is not installed")
class Paths(unittest.TestCase):
    def test_clean_path(self):
        cases = ["a/b.py", "a\\b\\c.py", " ./a//b.py ", "", "   ", "/etc/passwd", "\\\\server\\x", "C:/x", "C:\\x", "a/../b", "../a", "a/b/..", None, 5]
        out = run_node("console.log(JSON.stringify(data.map((c) => L.cleanPath(c))));", cases)
        self.assertEqual(out, ["a/b.py", "a/b/c.py", "a/b.py", None, None, None, None, None, None, None, None, None, None, None])

    def test_explorer_hash_and_back(self):
        out = run_node("""
          const rows = [["backend/api/deps.py", 120, 141], ["backend/api/deps.py", 7, null], ["backend/api/deps.py", 7, 7], ["backend/api/deps.py", 9, 3],
                        ["docs/my notes/with space.md", 2, 4], ["frontend/app/lib/é.js", 1, 2], ["backend/x.py", null, null], ["backend/x.py", 0, 5], ["../x", 1, 2]];
          console.log(JSON.stringify(rows.map(([p, s, e]) => { const h = L.explorerHash(p, s, e); return [h, h && L.parseExplorerHash(h)]; })));
        """)
        self.assertEqual(out[0], ["#/backend/api/deps.py@120-141", {"path": "backend/api/deps.py", "start": 120, "end": 141}])
        self.assertEqual(out[1], ["#/backend/api/deps.py@7", {"path": "backend/api/deps.py", "start": 7, "end": 7}])
        self.assertEqual(out[2][0], "#/backend/api/deps.py@7")
        self.assertEqual(out[3][0], "#/backend/api/deps.py@9", "an end before the start is dropped")
        self.assertEqual(out[4], ["#/docs/my%20notes/with%20space.md@2-4", {"path": "docs/my notes/with space.md", "start": 2, "end": 4}])
        self.assertEqual(out[5][1]["path"], "frontend/app/lib/é.js")
        self.assertEqual(out[6], ["#/backend/x.py", {"path": "backend/x.py", "start": None, "end": None}])
        self.assertEqual(out[7][0], "#/backend/x.py", "line 0 is not a line")
        self.assertEqual(out[8], [None, None])

    def test_parse_explorer_hash_rejects_non_file_hashes(self):
        out = run_node("""console.log(JSON.stringify(["", "#", "#/", "#/f", "#/..%2Fetc", "#/a/../b", "#/%E0%A4%A", "#overview", null].map((h) => L.parseExplorerHash(h))));""")
        self.assertEqual(out, [None, None, None, {"path": "f", "start": None, "end": None}, None, None, None, None, None])


@unittest.skipUnless(NODE, "node is not installed")
class LocalFolder(unittest.TestCase):
    def test_normalize_root(self):
        cases = ["E:\\python workplace\\code\\MiniMe", "E:/python workplace/code/MiniMe/", '"E:\\python workplace\\code\\MiniMe"', "  'C:\\MiniMe\\'  ",
                 "E:/python%20workplace/code/MiniMe", "/home/me/MiniMe/", "/home/me/my repo", "c:\\\\double\\\\slash", "\\\\server\\share\\MiniMe", "//server/share",
                 "relative/MiniMe", "C:", "C:\\", "", "   ", None, 7, "/", "E:/a%zzb"]
        out = run_node("console.log(JSON.stringify(data.map((c) => L.normalizeRoot(c))));", cases)
        self.assertEqual(out[0], "E:/python%20workplace/code/MiniMe", "the example from the plan")
        self.assertEqual(out[1], "E:/python%20workplace/code/MiniMe")
        self.assertEqual(out[2], "E:/python%20workplace/code/MiniMe", "quotes from Copy as path")
        self.assertEqual(out[3], "C:/MiniMe")
        self.assertEqual(out[4], "E:/python%20workplace/code/MiniMe", "already encoded: not encoded twice")
        self.assertEqual(out[5], "/home/me/MiniMe")
        self.assertEqual(out[6], "/home/me/my%20repo")
        self.assertEqual(out[7], "c:/double/slash")
        self.assertEqual(out[8:17], [None] * 9, "UNC, relative, bare drive, empty and non-string input")
        self.assertEqual(out[17], None, "the filesystem root alone is not a MiniMe folder")
        self.assertEqual(out[18], "E:/a%25zzb", "a broken escape is kept as typed")

    def test_vscode_url(self):
        out = run_node("""
          const R = "E:\\\\python workplace\\\\code\\\\MiniMe";
          console.log(JSON.stringify([
            L.vscodeUrl(R, "backend/api/my file.py", 120),
            L.vscodeUrl(R, "README.md"),
            L.vscodeUrl("/home/me/MiniMe", "backend/app.py", 5),
            L.vscodeUrl(R, "backend/app.py", 5, "vscode-insiders"),
            L.vscodeUrl(R, "backend/app.py", 5, "file:///evil"),
            L.vscodeUrl(R, "backend/app.py", 0),
            L.vscodeUrl("", "backend/app.py", 5),
            L.vscodeUrl(R, "../outside.py", 5),
            L.vscodeUrl(R, "/abs.py", 5),
            L.vscodeUrl(R, "a#b?c.py", 3),
          ]));
        """)
        self.assertEqual(out[0], "vscode://file/E:/python%20workplace/code/MiniMe/backend/api/my%20file.py:120")
        self.assertEqual(out[1], "vscode://file/E:/python%20workplace/code/MiniMe/README.md")
        self.assertEqual(out[2], "vscode://file/home/me/MiniMe/backend/app.py:5")
        self.assertEqual(out[3], "vscode-insiders://file/E:/python%20workplace/code/MiniMe/backend/app.py:5")
        self.assertTrue(out[4].startswith("vscode://file/"), "an unknown scheme falls back to the default, it is never used")
        self.assertTrue(out[5].endswith("app.py"))
        self.assertEqual(out[6:9], [None, None, None])
        self.assertTrue(out[9].endswith("/a%23b%3Fc.py:3"), "# and ? in a file name cannot start a fragment or a query")


@unittest.skipUnless(NODE, "node is not installed")
class Links(unittest.TestCase):
    def test_github_url(self):
        out = run_node(f"""
          const C = "{C40}", repo = "Unavailable4u/MiniMe";
          console.log(JSON.stringify([
            L.githubUrl(repo, C, "backend/agents/academic_search.py", 58, 82),
            L.githubUrl(repo, C, "backend/agents/academic_search.py", 58, 58),
            L.githubUrl(repo, C, "backend/agents/academic_search.py"),
            L.githubUrl(repo, C, "docs/my notes/with space.md", 3, 4),
            L.githubUrl(repo, "3727ae3", "a.py", 1, 2),
            L.githubUrl(repo, "", "a.py", 1, 2),
            L.githubUrl("not a repo", C, "a.py", 1, 2),
            L.githubUrl("", C, "a.py", 1, 2),
            L.githubUrl(repo, C, "../a.py", 1, 2),
          ]));
        """)
        base = f"https://github.com/Unavailable4u/MiniMe/blob/{C40}"
        self.assertEqual(out[0], f"{base}/backend/agents/academic_search.py#L58-L82")
        self.assertEqual(out[1], f"{base}/backend/agents/academic_search.py#L58")
        self.assertEqual(out[2], f"{base}/backend/agents/academic_search.py")
        self.assertEqual(out[3], f"{base}/docs/my%20notes/with%20space.md#L3-L4")
        self.assertEqual(out[4:], [None] * 5, "a short commit, no commit, a bad repo and a bad path give no link: nothing is guessed")

    def test_code_links_for_a_sample_file_with_spaces(self):
        out = run_node(f"""
          const opts = {{ repo: "Unavailable4u/MiniMe", commit: "{C40}", root: "E:\\\\python workplace\\\\code\\\\MiniMe", scheme: "vscode",
                         srcFiles: {{ "docs/my notes/with space.md": "abc" }} }};
          console.log(JSON.stringify(L.codeLinks({{ path: "docs/my notes/with space.md", start: 10, end: 14 }}, opts)));
        """)
        self.assertEqual(out, {
            "explorer": "explorer.html#/docs/my%20notes/with%20space.md@10-14",
            "github": f"https://github.com/Unavailable4u/MiniMe/blob/{C40}/docs/my%20notes/with%20space.md#L10-L14",
            "vscode": "vscode://file/E:/python%20workplace/code/MiniMe/docs/my%20notes/with%20space.md:10",
            "src": "data/src/docs/my%20notes/with%20space.md.txt",
        })

    def test_a_link_without_its_ingredients_is_left_out(self):
        out = run_node(f"""
          const t = {{ path: "backend/app.py", start: 3, end: 4 }};
          console.log(JSON.stringify([
            L.codeLinks(t, {{}}),
            L.codeLinks(t, {{ commit: "{C40}" }}),
            L.codeLinks(t, {{ root: "/home/me/MiniMe" }}),
            L.codeLinks(t, {{ srcFiles: {{ "other.py": "x" }} }}),
            L.codeLinks(t, {{ srcFiles: null }}),
            L.codeLinks({{ path: "constructor" }}, {{ srcFiles: {{}} }}),
            L.codeLinks({{ path: "__proto__" }}, {{ srcFiles: {{}} }}),
            L.codeLinks({{ path: "../x" }}, {{ commit: "{C40}" }}),
            L.codeLinks(null, {{}}),
            L.codeLinks({{ path: "backend/app.py", commit: "{C40.upper()}" }}, {{}}),
            L.codeLinks({{ path: "backend/app.py", commit: "{'b' * 40}" }}, {{ commit: "{C40}" }}),
          ]));
        """)
        self.assertEqual(out[0], {"explorer": "explorer.html#/backend/app.py@3-4"}, "the Explorer link needs nothing")
        self.assertEqual(sorted(out[1]), ["explorer", "github"])
        self.assertEqual(sorted(out[2]), ["explorer", "vscode"])
        self.assertEqual(sorted(out[3]), ["explorer"], "a file the manifest does not list has no src link")
        self.assertEqual(sorted(out[4]), ["explorer"])
        self.assertNotIn("src", out[5], "Object.prototype names are not files")
        self.assertNotIn("src", out[6])
        self.assertEqual(out[7], {})
        self.assertEqual(out[8], {})
        self.assertIn(C40, out[9]["github"], "an upper-case commit is normalised")
        self.assertIn("b" * 40, out[10]["github"], "a commit on the target wins over the page default")


@unittest.skipUnless(NODE, "node is not installed")
class Settings(unittest.TestCase):
    STORE = """
      const mem = (init = {}) => { const m = { ...init }; return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: (k) => { delete m[k]; }, m }; };
    """

    def test_round_trip(self):
        out = run_node(self.STORE + """
          const s = mem();
          const r = [L.readSettings(s)];
          r.push(L.saveSettings({ root: "  E:\\\\code\\\\MiniMe  ", scheme: "vscode-insiders" }, s), L.readSettings(s));
          r.push(L.saveSettings({ root: "/x", scheme: "evil" }, s), L.readSettings(s));
          r.push(L.saveSettings({}, s), Object.keys(s.m), L.readSettings(s));
          console.log(JSON.stringify(r));
        """)
        self.assertEqual(out[0], {"root": "", "scheme": ""})
        self.assertTrue(out[1])
        self.assertEqual(out[2], {"root": "E:\\code\\MiniMe", "scheme": "vscode-insiders"})
        self.assertEqual(out[4], {"root": "/x", "scheme": ""}, "an unknown editor is not stored")
        self.assertEqual(out[6], [], "saving nothing removes the key")
        self.assertEqual(out[7], {"root": "", "scheme": ""})

    def test_broken_storage_never_throws(self):
        out = run_node(self.STORE + """
          const bad = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); }, removeItem() { throw new Error("denied"); } };
          const junk = mem({ [L.KEY_LINKS]: "{not json" }), wrongType = mem({ [L.KEY_LINKS]: JSON.stringify({ root: 5, scheme: ["vscode"] }) });
          console.log(JSON.stringify([L.readSettings(bad), L.saveSettings({ root: "/x" }, bad), L.readSettings(junk), L.readSettings(wrongType), L.readSettings(null), L.saveSettings({ root: "/x" }, null)]));
        """)
        self.assertEqual(out, [{"root": "", "scheme": ""}, False, {"root": "", "scheme": ""}, {"root": "", "scheme": ""}, {"root": "", "scheme": ""}, False])

    def test_link_options(self):
        out = run_node(f"""
          const manifest = {{ commit: "{C40}", files: {{ "a.py": "1" }} }};
          const s0 = {{ root: "", scheme: "" }};
          console.log(JSON.stringify([
            L.linkOptions({{}}, null, s0),
            L.linkOptions({{ github: {{ repo: "me/Other" }}, editor: {{ scheme: "vscode-insiders" }} }}, manifest, {{ root: "/m", scheme: "" }}),
            L.linkOptions({{ editor: {{ scheme: "vscode-insiders" }} }}, manifest, {{ root: "", scheme: "vscode" }}),
            L.linkOptions({{ embedSource: false }}, manifest, s0),
            L.linkOptions({{}}, {{ commit: "3727ae3", files: {{}} }}, s0),
            L.linkOptions({{ editor: {{ scheme: "emacs" }} }}, manifest, s0),
            L.linkOptions(undefined, undefined, undefined),
          ]));
        """)
        self.assertEqual(out[0], {"repo": "Unavailable4u/MiniMe", "commit": "", "root": "", "scheme": "vscode", "siteScheme": "vscode", "srcFiles": None})
        self.assertEqual(out[1]["repo"], "me/Other")
        self.assertEqual(out[1]["commit"], C40)
        self.assertEqual(out[1]["scheme"], "vscode-insiders", "the site default applies when the reader chose nothing")
        self.assertEqual(out[1]["root"], "/m")
        self.assertEqual(out[1]["srcFiles"], {"a.py": "1"})
        self.assertEqual(out[2]["scheme"], "vscode", "the reader's choice beats the site default")
        self.assertEqual(out[2]["siteScheme"], "vscode-insiders", "and the site default is still reported (the settings popover names it)")
        self.assertIsNone(out[3]["srcFiles"], "embedSource: false hides the source button")
        self.assertEqual(out[4]["commit"], "", "a short commit is not a permalink")
        self.assertEqual(out[5]["scheme"], "vscode", "an unknown editor in the config is ignored")
        self.assertEqual(out[6]["scheme"], "vscode")


class Wiring(unittest.TestCase):
    def test_shell_loads_links_lazily(self):
        # test_codemod_shell.py imports shell.js in Node with only palette.js next to it: a static import of links.js would break that
        js = (ROOT / "assets" / "js" / "shell.js").read_text(encoding="utf-8")
        self.assertIn('import("./links.js")', js)
        self.assertNotRegex(js, r'(?m)^import .* from "\./links\.js"')
        for needle in ("mm-top__links", "minime:links", "mm-links-pop", "openLinksPop", "closeLinksPop"):
            self.assertIn(needle, js)

    def test_the_popover_has_styles_and_a_keyboard_exit(self):
        css = (ROOT / "assets" / "css" / "shell.css").read_text(encoding="utf-8")
        for needle in (".mm-pop ", ".mm-pop__in", ".mm-pop__prev"):
            self.assertIn(needle, css)
        js = (ROOT / "assets" / "js" / "shell.js").read_text(encoding="utf-8")
        self.assertRegex(js, r"closeLinksPop\(true\)\) closed = true")           # Esc, through closeTransient()

    def test_links_js_touches_no_dom_and_no_network_at_import(self):
        js = LINKS.read_text(encoding="utf-8")
        head = js.split("/* ------------------------------------------------------------------ loading (browser only) */")[0]
        for bad in ("document.", "window.", "fetch(", "XMLHttpRequest"):
            self.assertNotIn(bad, head, bad)
        self.assertEqual(re.findall(r"(?m)^import ", js), [], "no dependencies")


if __name__ == "__main__":
    unittest.main(verbosity=2)
