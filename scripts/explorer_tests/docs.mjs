// P14e: markdown.js, jsonview.js, sql.js and docview.js (pure parts), then every embedded .md / .json / .sql file of the repository.
//   node docs.mjs
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as MD from "../../assets/js/explorer/markdown.js";
import * as JV from "../../assets/js/explorer/jsonview.js";
import * as SQ from "../../assets/js/explorer/sql.js";
import { parseRoute, buildRoute } from "../../assets/js/explorer/router.js";
import { langFromFence, highlightWith } from "../../assets/js/explorer/highlight.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
let n = 0;
const t = async (name, f) => { try { await f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };
const kinds = (blocks) => blocks.map((b) => b.t);

await t("router: the view tab round trips", () => {
  assert.equal(parseRoute("#/f/README.md?tab=view").tab, "view");
  assert.equal(buildRoute({ view: "file", path: "README.md", tab: "view" }), "#/f/README.md?tab=view");
});

await t("highlight: langFromFence aliases and unknowns", () => {
  assert.deepEqual(["python", "py", "js title=x", "jsonc", "sh", "psql", "{.yaml}", "mermaid", "", null].map(langFromFence), ["python", "python", "javascript", "json", "bash", "sql", null, null, null, null]);
});

await t("markdown: headings, setext, ids are unique, line numbers", () => {
  const d = MD.parseMarkdown("# A\n\ntext\n\nB\n---\n\n## A\n\n### A\n");
  assert.deepEqual(d.headings.map((x) => [x.level, x.id, x.line]), [[1, "a", 1], [2, "b", 5], [2, "a-1", 8], [3, "a-2", 10]]);
});

await t("markdown: inline emphasis, code, escapes, entities", () => {
  const p = (s) => MD.parseInline(s);
  assert.deepEqual(p("a **b** *c* ~~d~~ `e`").map((x) => x.t), ["text", "strong", "text", "em", "text", "del", "text", "code"]);
  assert.equal(MD.plainText(p("snake_case_word and 2 * 3 * 4")), "snake_case_word and 2 * 3 * 4");
  assert.equal(MD.plainText(p("\\*not\\* &amp; &lt;b&gt;")), "*not* & <b>");
  assert.deepEqual(p("``a`b``"), [{ t: "code", v: "a`b" }]);
});

await t("markdown: lists nest, tasks, ordered start", () => {
  const d = MD.parseMarkdown("- a\n  - b\n- [x] c\n- [ ] d\n\n3. x\n4. y\n");
  assert.deepEqual(kinds(d.blocks), ["list", "list"]);
  assert.equal(d.blocks[0].items.length, 3);
  assert.equal(d.blocks[0].items[0].c[1].t, "list");
  assert.deepEqual(d.blocks[0].items.map((i) => i.task), [null, true, false]);
  assert.equal(d.blocks[1].start, 3);
});

await t("markdown: tables with alignment, fenced and indented code, quote, hr, front matter", () => {
  const d = MD.parseMarkdown("---\ntitle: x\n---\n| a | b |\n|:-:|--:|\n| 1 | 2 |\n\n```py title=x\nprint(1)\n```\n\n    indented\n\n> q\n> r\n\n***\n");
  assert.equal(d.front, "title: x");
  assert.deepEqual(kinds(d.blocks), ["table", "code", "code", "quote", "hr"]);
  assert.deepEqual(d.blocks[0].align, ["center", "right"]);
  assert.equal(d.blocks[1].lang, "py title=x");
  assert.equal(d.blocks[1].line, 8);
});

await t("markdown: reference links and HTML comments", () => {
  const d = MD.parseMarkdown("see [the doc][d] <!-- hidden -->\n\n[d]: ./a.md \"T\"\n");
  assert.equal(d.blocks.length, 1);
  assert.equal(d.blocks[0].c.find((x) => x.t === "link").href, "./a.md");
  assert.ok(!JSON.stringify(d.blocks).includes("hidden"));
});

await t("markdown: resolveHref never lets code out", () => {
  const ctx = { path: "docs/decisions/0001.md", hasFile: (p) => p === "src/app.py" || p === "docs/a.md", hasDir: (p) => p === "docs" };
  const k = (h) => MD.resolveHref(h, ctx);
  for (const bad of ["javascript:alert(1)", "JaVa\tScRiPt:alert(1)", "data:text/html,x", "file:///etc/passwd", "vbscript:x", "../../../../etc/passwd", ""]) assert.equal(k(bad).kind, "blocked", bad);
  assert.equal(k("https://x.org/a").kind, "external");
  assert.equal(k("mailto:a@b.c").kind, "external");
  assert.deepEqual(k("../../src/app.py#L10-L20"), { kind: "file", path: "src/app.py", start: 10, end: 20 });
  assert.deepEqual(k("../a.md"), { kind: "file", path: "docs/a.md" });
  assert.equal(k("../../docs").kind, "dir");
  assert.equal(k("nothing.md").kind, "missing");
  assert.deepEqual(k("#My%20Heading"), { kind: "anchor", id: "my heading" });
});

await t("markdown: pathological input finishes quickly", () => {
  const t0 = Date.now();
  MD.parseMarkdown("*".repeat(3000) + "\n" + "[".repeat(2000) + "\n" + "`".repeat(2000) + "\n" + "- ".repeat(500) + "\n" + "> ".repeat(300) + "x");
  MD.parseMarkdown(("a_" + "b ").repeat(5000));
  assert.ok(Date.now() - t0 < 3000, `took ${Date.now() - t0} ms`);
});

await t("json: strict, relaxed, error position", () => {
  assert.equal(JV.parseJsonText('{"a":[1,2]}').relaxed, false);
  const r = JV.parseJsonText('{\n  // c\n  "a": 1,\n}');
  assert.ok(r.ok && r.relaxed && r.value.a === 1);
  assert.equal(JV.parseJsonText('{"url":"http://x//y"}').value.url, "http://x//y");
  const bad = JV.parseJsonText('{\n "a": 1\n "b": 2\n}');
  assert.ok(!bad.ok && bad.line >= 2, JSON.stringify(bad));
  assert.ok(JV.parseJsonText("\uFEFF[1]").ok);
});

await t("json: pathString, describe, countNodes, schemaSummary", () => {
  assert.equal(JV.pathString(["a", 0, "b-c", "it's"]), "$.a[0]['b-c']['it\\'s']");
  assert.equal(JV.describe({ a: 1 }), "object, 1 key"); assert.equal(JV.describe([1, 2]), "array, 2 items");
  assert.equal(JV.countNodes({ a: [1, 2], b: { c: 3 } }), 6);
  assert.ok(JV.countNodes(Array.from({ length: 10000 }, () => 1), 100) > 100);
  assert.equal(JV.schemaSummary({ a: 1 }), null);
  const s = JV.schemaSummary({ $schema: "https://json-schema.org/draft/2020-12/schema", title: "T", required: ["x"], properties: { x: { type: "string" }, y: { $ref: "c.json#/$defs/id" }, z: { type: "array", items: { type: "number" } }, w: { enum: [1, 2] } }, $defs: { id: {} } });
  assert.deepEqual(s.props.map((p) => [p.name, p.type, p.required]), [["x", "string", true], ["y", "-> c.json#/$defs/id", false], ["z", "array of number", false], ["w", "enum (2)", false]]);
});

await t("sql: scanner keeps $$ bodies, strings and comments together", () => {
  const src = "-- Migration 7\n-- adds things\n\n-- the table\nCREATE TABLE a (id int primary key, x text default 'a;b');\n/* block ; */ CREATE FUNCTION f() RETURNS int AS $$ BEGIN; SELECT 1; END; $$ LANGUAGE plpgsql;\nINSERT INTO a VALUES (E'it\\'s;');\n\\set ON_ERROR_STOP on\n";
  const { statements, header } = SQ.scanSql(src);
  assert.equal(statements.length, 4);
  assert.equal(header, "Migration 7\nadds things");
  assert.equal(statements[0].comment, "the table");
  assert.deepEqual(statements.map((s) => s.line), [5, 6, 7, 8]);
});

await t("sql: classify the statements the repository uses", () => {
  const c = SQ.classify;
  const tb = c("CREATE TABLE IF NOT EXISTS public.users (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid NOT NULL REFERENCES public.orgs(id), email text UNIQUE, UNIQUE (org_id, email))");
  assert.deepEqual([tb.kind, tb.name, tb.columns.length, tb.constraints.length], ["table", "public.users", 3, 1]);
  assert.equal(tb.columns[1].ref, "public.orgs(id)");
  assert.deepEqual([c("CREATE UNIQUE INDEX CONCURRENTLY ix ON t (a)").kind, c("CREATE POLICY p ON t FOR SELECT TO authenticated USING (true)").detail], ["index", "on t · for select · to authenticated · using"]);
  assert.equal(c("ALTER TABLE t ENABLE ROW LEVEL SECURITY").kind, "alter");
  assert.equal(c("GRANT SELECT ON t TO anon").name, "t");
  assert.equal(c("COMMENT ON TABLE t IS 'x'").kind, "comment");
  assert.equal(c("VACUUM t").kind, "other");
});

await t("highlight: highlightWith colours a fenced block and keeps the text", async () => {
  const r = await highlightWith(["def f():", "    return 1"], "python");
  assert.ok(r && r.lines.length === 2 && r.lines[0].some((s) => s.c));
  assert.equal(await highlightWith(["x"], "nope"), null);
});

/* every real file of the repository, as the Document / Structure / Outline tabs would read it */
const walk = (d) => fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)])) : [];
const files = walk(path.join(ROOT, "data", "src"));
await t("corpus: every embedded .md parses, every heading has a Source line, no link escapes", () => {
  let c = 0;
  for (const f of files.filter((x) => /\.(md|markdown)\.txt$/.test(x))) {
    const text = fs.readFileSync(f, "utf8");
    const d = MD.parseMarkdown(text);
    const total = text.split("\n").length;
    for (const h of d.headings) assert.ok(h.line >= 1 && h.line <= total, `${f}: heading line ${h.line}/${total}`);
    const walkInline = (nodes) => nodes.forEach((x) => { if (x.t === "link") assert.notEqual(MD.resolveHref(x.href, { path: "a/b.md" }).kind === "external" && /^javascript/i.test(x.href), true); if (x.c) walkInline(x.c); });
    const walkBlocks = (bs) => bs.forEach((b) => { if (b.c && b.t !== "table") (b.t === "quote" ? walkBlocks : walkInline)(b.c); if (b.items) b.items.forEach((i) => walkBlocks(i.c)); });
    walkBlocks(d.blocks);
    c++;
  }
  console.log(`   (${c} Markdown files)`);
});
await t("corpus: every embedded .json parses (strict or relaxed)", () => {
  let c = 0, relaxed = 0;
  for (const f of files.filter((x) => /\.jsonc?\.txt$/.test(x))) { const r = JV.parseJsonText(fs.readFileSync(f, "utf8")); assert.ok(r.ok, `${f}: ${r.error}`); if (r.relaxed) relaxed++; c++; }
  console.log(`   (${c} JSON files, ${relaxed} relaxed)`);
});
await t("corpus: every embedded .sql gives statements inside the file, in order", () => {
  let c = 0, s = 0;
  for (const f of files.filter((x) => /\.sql\.txt$/.test(x))) {
    const text = fs.readFileSync(f, "utf8");
    const total = text.replace(/\r\n?/g, "\n").split("\n").length;
    const o = SQ.sqlOutline(text);
    let prev = 0;
    for (const st of o.statements) { assert.ok(st.line >= prev && st.end >= st.line && st.end <= total + 1, `${f}: ${st.line}-${st.end}/${total}`); prev = st.line; }
    s += o.statements.length; c++;
  }
  console.log(`   (${c} SQL files, ${s} statements)`);
});

console.log(`${n} passed`);
