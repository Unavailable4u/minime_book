// highlight.js of the Explorer (P14b): language choice, HTML -> segments, the real vendored engine, and a round trip over the embedded source.
//   node highlight.mjs            all tests
//   node highlight.mjs --corpus   also every embedded file (slow, ~1 min); the default run uses a sample
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as HL from "../../assets/js/explorer/highlight.js";
import { splitLines } from "../../assets/js/explorer/model.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
let n = 0;
const t = async (name, f) => { try { await f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };
const plain = (lines) => lines.map((l) => l.map((s) => s.t).join(""));

await t("langFor: extensions, names, shebang, unknown", () => {
  const f = (p, first) => HL.langFor(p, first);
  assert.deepEqual(["a.py", "x/b.JS", "c.jsx", "d.mjs", "e.ts", "f.json", "g.sql", "h.yaml", "i.yml", "j.sh", "k.ps1", "l.css", "m.svg", "n.ini", "o.toml", "p.md"].map((p) => f(p)),
    ["python", "javascript", "javascript", "javascript", "typescript", "json", "sql", "yaml", "yaml", "bash", "powershell", "css", "xml", "ini", "ini", "markdown"]);
  assert.equal(f("backend.Dockerfile"), "dockerfile"); assert.equal(f("Dockerfile"), "dockerfile"); assert.equal(f("a/b/Dockerfile.dev"), "dockerfile");
  assert.equal(f(".env.example"), "ini");
  assert.equal(f(".githooks/pre-commit", "#!/usr/bin/env bash"), "bash"); assert.equal(f("bin/tool", "#!/usr/bin/python3"), "python"); assert.equal(f("bin/tool", "#!/usr/bin/env node"), "javascript");
  assert.equal(f("bin/tool", "not a shebang"), null);
  for (const p of [".gitignore", ".dockerignore", ".gitattributes", "notes.txt", "x.patch", "LICENSE", "", null]) assert.equal(f(p), null, String(p));
});

await t("parseHighlighted: plain text, spans, nesting, entities", () => {
  assert.deepEqual(HL.parseHighlighted("a &lt; b &amp;&amp; c"), [[{ t: "a < b && c", c: "" }]]);
  assert.deepEqual(HL.parseHighlighted('x <span class="hljs-keyword">def</span> y'), [[{ t: "x ", c: "" }, { t: "def", c: "hljs-keyword" }, { t: " y", c: "" }]]);
  assert.deepEqual(HL.parseHighlighted('<span class="hljs-string">"a <span class="hljs-subst">{b}</span> c"</span>'.replace('"a', "&quot;a").replace('c"<', "c&quot;<")),
    [[{ t: '"a ', c: "hljs-string" }, { t: "{b}", c: "hljs-subst" }, { t: ' c"', c: "hljs-string" }]]);
  assert.deepEqual(HL.parseHighlighted("it&#x27;s &#39;ok&#39;"), [[{ t: "it's 'ok'", c: "" }]]);
  assert.deepEqual(HL.parseHighlighted(""), [[]]);
  assert.deepEqual(HL.parseHighlighted(null), [[]]);
});

await t("parseHighlighted: a token that spans lines is carried onto each line; empty lines stay empty", () => {
  const out = HL.parseHighlighted('a\n<span class="hljs-string">"""one\n\ntwo"""</span>\nb');
  assert.equal(out.length, 5);
  assert.deepEqual(out[1], [{ t: '"""one', c: "hljs-string" }]);
  assert.deepEqual(out[2], []);
  assert.deepEqual(out[3], [{ t: 'two"""', c: "hljs-string" }]);
  assert.deepEqual(plain(out), ["a", '"""one', "", 'two"""', "b"]);
});

await t("parseHighlighted: nested span closes back to the outer class on the same line", () => {
  const out = HL.parseHighlighted('<span class="hljs-meta">#<span class="hljs-keyword">include</span> &lt;x&gt;</span>');
  assert.deepEqual(out[0], [{ t: "#", c: "hljs-meta" }, { t: "include", c: "hljs-keyword" }, { t: " <x>", c: "hljs-meta" }]);
});

const run = (src, p) => HL.highlightLines(splitLines(src), p);
const has = (res, cls, text) => res.lines.some((l) => l.some((s) => s.c.split(" ").includes(cls) && s.t === text));

await t("highlightLines: python keywords, comment, multi-line docstring, one entry per line", async () => {
  const src = 'import os\n\ndef f(x):\n    """Docs\n    more <b>\n    """\n    return x  # done\n';
  const r = await run(src, "a.py");
  assert.equal(r.lang, "python"); assert.equal(r.lines.length, 7);
  assert.deepEqual(plain(r.lines), splitLines(src));
  assert.ok(has(r, "hljs-keyword", "import") && has(r, "hljs-keyword", "def") && has(r, "hljs-keyword", "return"));
  assert.ok(r.lines[4].some((s) => s.c === "hljs-string" || s.c.includes("hljs-string") || s.c.includes("hljs-doctag")), "docstring body keeps a string class on the middle line");
  assert.ok(r.lines[6].some((s) => s.c === "hljs-comment" && s.t === "# done"));
});

await t("highlightLines: JSX (needs xml), TypeScript, JSON, SQL, YAML, bash, Dockerfile, CSS, ini, powershell, markdown", async () => {
  const cases = [
    ["a.jsx", "export default function A({ x }) {\n  return <div className=\"a\">{x}</div>;\n}\n", "hljs-keyword"],
    ["a.ts", "interface A { x: number }\nconst a: A = { x: 1 };\n", "hljs-keyword"],
    ["a.json", '{\n  "a": [1, true, null]\n}\n', "hljs-attr"],
    ["a.sql", "SELECT id, name FROM users WHERE id = 1;\n", "hljs-keyword"],
    ["a.yaml", "name: ci\non:\n  push: {}\n", "hljs-attr"],
    ["a.sh", "#!/bin/bash\nset -e\nif [ -f x ]; then echo hi; fi\n", "hljs-keyword"],
    ["a.Dockerfile", "FROM python:3.12\nRUN echo hi\n", "hljs-keyword"],
    ["a.css", ".a { color: red; }\n", "hljs-selector-class"],
    ["a.ini", "[core]\nname = x\n", "hljs-section"],
    ["a.ps1", "function Get-X { param($a) return $a }\n", "hljs-keyword"],
    ["a.md", "# Title\n\nSome *text* and `code`.\n", "hljs-section"],
  ];
  for (const [p, src, cls] of cases) {
    const r = await run(src, p);
    assert.ok(r, `${p}: no result`);
    assert.deepEqual(plain(r.lines), splitLines(src), `${p}: text changed`);
    assert.ok(r.lines.some((l) => l.some((s) => s.c.split(" ").includes(cls))), `${p}: no ${cls}`);
  }
  const jsx = await run(cases[0][1], "a.jsx");
  assert.ok(has(jsx, "hljs-name", "div") || jsx.lines[1].some((s) => /hljs-(name|tag|attr)/.test(s.c)), "JSX tag is coloured");
});

await t("highlightLines: markup in the source stays text", async () => {
  const r = await run("x = '<img src=x onerror=alert(1)>'  # <b>hi</b> &amp; &lt;\n", "a.py");
  assert.deepEqual(plain(r.lines), ["x = '<img src=x onerror=alert(1)>'  # <b>hi</b> &amp; &lt;"]);
});

await t("highlightLines: nothing to colour -> null (plain file, too big, empty list)", async () => {
  assert.equal(await run("hello\n", "notes.txt"), null);
  assert.equal(await run("hello\n", ".gitignore"), null);
  assert.equal(await HL.highlightLines(["x".repeat(HL.MAX_CHARS + 1)], "a.py"), null);
  assert.equal(await HL.highlightLines([], "a.py"), null);
});

await t("highlightLines: engine missing -> null, never throws; and it recovers when the folder is back", async () => {
  HL.setVendorBase("../../vendor/does-not-exist/");
  assert.equal(await run("def f(): pass\n", "a.py"), null);
  HL.setVendorBase("../../vendor/highlight/");
  assert.ok(await run("def f(): pass\n", "a.py"));
});

/* Round trip: for real MiniMe files, the coloured lines must read exactly like the plain ones (same count, same text). */
await t("round trip over the embedded source", async () => {
  const dir = path.join(ROOT, "data", "src");
  const files = [];
  (function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (e.name.endsWith(".txt")) files.push(p); } })(dir);
  const by = new Map();
  for (const f of files) {
    const rel = path.relative(dir, f).replace(/\\/g, "/").slice(0, -4);
    const text = fs.readFileSync(f, "utf8");
    const lang = HL.langFor(rel, text.split("\n", 1)[0]);
    if (!lang) continue;
    if (!by.has(lang)) by.set(lang, []);
    by.get(lang).push({ rel, text });
  }
  const all = process.argv.includes("--corpus");
  let checked = 0, coloured = 0;
  for (const [lang, list] of by) {
    list.sort((a, b) => a.text.length - b.text.length);
    const pick = all ? list : list.filter((_, i) => i % Math.max(1, Math.ceil(list.length / 12)) === 0).concat(list.slice(-1));
    for (const { rel, text } of pick) {
      if (text.length > HL.MAX_CHARS) continue;
      const lines = splitLines(text);
      const r = await HL.highlightLines(lines, rel);
      checked++;
      assert.ok(r, `${rel} (${lang}) was not highlighted`);
      assert.equal(r.lines.length, lines.length, `${rel}: line count`);
      assert.deepEqual(plain(r.lines), lines, `${rel}: text differs`);
      if (r.lines.some((l) => l.some((s) => s.c))) coloured++;
    }
  }
  console.log(`   ${checked} files in ${by.size} languages checked, ${coloured} with colours`);
  assert.ok(checked >= 10 || by.size === 0, "the sample is not empty");
  assert.ok(coloured >= checked * 0.9, "almost every checked file has at least one coloured token");
});

console.log(`${n} passed`);
