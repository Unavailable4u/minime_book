// router.js and model.js: pure functions, no DOM.
import assert from "node:assert/strict";
import { parseRoute, buildRoute } from "../../assets/js/explorer/router.js";
import * as M from "../../assets/js/explorer/model.js";
let n = 0;
const t = (name, f) => { try { f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };

t("router: home", () => { assert.equal(parseRoute("").view, "home"); assert.equal(parseRoute("#/").view, "home"); assert.equal(buildRoute({ view: "home" }), "#/"); });
t("router: file + symbol + lines", () => {
  const r = parseRoute("#/f/backend/agents/academic_search.py::_clean_query@120-141");
  assert.deepEqual([r.view, r.path, r.qual, r.start, r.end], ["file", "backend/agents/academic_search.py", "_clean_query", 120, 141]);
});
t("router: round trip with spaces, tab, method qual", () => {
  const o = { view: "file", path: "a b/c d.py", qual: "A.m", start: 3, end: 9, tab: "symbols" };
  const h = buildRoute(o);
  assert.ok(!h.includes(" "));
  const r = parseRoute(h);
  assert.deepEqual([r.view, r.path, r.qual, r.start, r.end, r.tab], ["file", "a b/c d.py", "A.m", 3, 9, "symbols"]);
});
t("router: folder ignores qual and lines", () => assert.equal(buildRoute({ view: "dir", path: "backend", qual: "x", start: 1 }), "#/d/backend"));
t("router: legacy links.js form is view auto", () => { const r = parseRoute("#/backend/a.py@10-20"); assert.deepEqual([r.view, r.path, r.start, r.end], ["auto", "backend/a.py", 10, 20]); });
t("router: bad input falls back to home, never throws", () => { for (const h of ["#/f/%E0%A4%A", "#/f/", "#/f/::x", "#/f/a.py@0", "#/f/a.py@9-3"]) parseRoute(h); assert.equal(parseRoute("#/f/%E0%A4%A").view, "home"); assert.equal(parseRoute("#/f/a.py@0").start, null); assert.equal(parseRoute("#/f/a.py@9-3").end, 9); });
t("router: unknown tab is dropped", () => assert.equal(parseRoute("#/f/a.py?tab=source").tab, ""));

const raw = { file_fields: ["name", "lang", "lines", "code", "functions", "classes", "commits", "last", "flags", "shard"], shards: ["s0"], root: { files: [["R.md", "md", 5, 4, 0, 0, 1, "", "", 0]], dirs: [{ name: "b", n: { files: 3, lines: 19, code: 17, functions: 2, classes: 0 }, files: [["z.py", "py", 9, 8, 1, 0, 2, "", "t", 0], ["a.py", "py", 9, 8, 1, 0, 2, "", "", 0]], dirs: [{ name: "c", files: [["d.py", "py", 1, 1, 0, 0, 0, "", "", 0]], dirs: [] }] }] } };
const tree = M.buildTree(raw);
t("model: buildTree paths, sort, flags, totals", () => {
  assert.deepEqual([...tree.files.keys()].sort(), ["R.md", "b/a.py", "b/c/d.py", "b/z.py"]);
  assert.deepEqual(tree.dirs.get("b").files.map((f) => f.name), ["a.py", "z.py"]);
  assert.equal(tree.files.get("b/z.py").test, true);
  assert.equal(tree.root.n.files, 4);
});
t("model: ancestors", () => assert.deepEqual(M.ancestors("a/b/c.py"), ["a", "a/b"]));
t("model: flatten collapsed / expanded / filtered", () => {
  assert.deepEqual(M.flatten(tree.root, new Set()).map((r) => r.node.path), ["b", "R.md"]);
  assert.deepEqual(M.flatten(tree.root, new Set(["b"])).map((r) => r.node.path), ["b", "b/c", "b/a.py", "b/z.py", "R.md"]);
  assert.deepEqual(M.flatten(tree.root, new Set(), "d.py").map((r) => r.node.path), ["b", "b/c", "b/c/d.py"]);
  assert.deepEqual(M.flatten(tree.root, new Set(), "nothing"), []);
});
t("model: coverage dots", () => {
  const notes = { folders: { a: { files: 10, noted: 0 }, b: { files: 10, noted: 1 }, c: { files: 10, noted: 9 }, d: { files: 10, noted: 10 }, e: { files: 0, noted: 0 } } };
  assert.equal(M.coverage(notes, "a").dots, 0); assert.equal(M.coverage(notes, "b").dots, 1); assert.equal(M.coverage(notes, "c").dots, 3); assert.equal(M.coverage(notes, "d").dots, 4);
  assert.equal(M.coverage(notes, "e"), null); assert.equal(M.coverage(null, "a"), null);
});
t("model: noteStatus", () => { const nt = { files: { f: { status: "fresh" }, s: { status: "stale" }, b: { bad: ["x"] } } }; assert.deepEqual(["f", "s", "b", "q"].map((p) => M.noteStatus(nt, p)), ["fresh", "stale", "stale", "none"]); assert.equal(M.noteStatus(null, "f"), "none"); });
t("model: signature", () => {
  assert.equal(M.signature({ kind: "function", name: "f", async: true, params: [{ name: "x", annotation: "int", default: "1" }, { name: "y" }], returns: "str" }), "async f(x: int = 1, y) -> str");
  assert.equal(M.signature({ kind: "class", name: "C", bases: ["A", "B"] }), "class C(A, B)");
});
t("model: symbolRows description chain and freshness", () => {
  const rec = { path: "p.py", functions: [{ qual: "a", name: "a", start: 1, end: 2, doc1: "Doc a.", hash: "1" }, { qual: "b", name: "b", start: 3, end: 4, doc1: "", hash: "2" }, { qual: "c", name: "c", start: 5, end: 6, doc1: "Doc c.", hash: "3" }, { qual: "d", name: "d", start: 7, end: 8, hash: "4" }], classes: [] };
  const note = { symbols: [{ qual: "a", summary: "Note a.", hash: "1" }, { qual: "b", summary: "Note b.", hash: "X" }, { qual: "d", summary: "Note d." }] };
  const r = Object.fromEntries(M.symbolRows(rec, note).map((x) => [x.qual, x]));
  assert.deepEqual([r.a.from, r.a.desc, r.a.fresh], ["note", "Note a.", "fresh"]);
  assert.deepEqual([r.b.from, r.b.fresh], ["note", "stale"]);
  assert.deepEqual([r.c.from, r.c.desc, r.c.fresh], ["doc", "Doc c.", "none"]);
  assert.deepEqual([r.d.fresh], ["unverified"]);
  const bare = M.symbolRows(rec, null);
  assert.deepEqual(bare.map((x) => x.from), ["doc", "none", "doc", "none"]);
});
t("model: filterSymbols and SORTS", () => {
  const rows = [{ qual: "a", name: "a", path: "x.py", desc: "Fetch data", kind: "function", from: "note", test: false, start: 5, loc: 3, cc: 1 }, { qual: "B.t", name: "t", path: "y.py", desc: "", kind: "method", from: "none", test: true, start: 1, loc: 9, cc: null }];
  assert.equal(M.filterSymbols(rows, { q: "fetch" }).length, 1); assert.equal(M.filterSymbols(rows, { kind: "method" }).length, 1);
  assert.equal(M.filterSymbols(rows, { noteOnly: true }).length, 1); assert.equal(M.filterSymbols(rows, { hideTests: true }).length, 1);
  assert.deepEqual(rows.slice().sort(M.SORTS.size.cmp).map((r) => r.qual), ["B.t", "a"]); assert.deepEqual(rows.slice().sort(M.SORTS.line.cmp).map((r) => r.qual), ["B.t", "a"]);
  assert.deepEqual(rows.slice().sort(M.SORTS.cc.cmp).map((r) => r.qual), ["a", "B.t"]);
});
t("model: monthBuckets", () => {
  assert.deepEqual(M.monthBuckets([]).counts, []);
  const b = M.monthBuckets(["2026-01-05", "2026-01-09", "2026-03-01"]);
  assert.deepEqual([b.counts, b.first, b.last], [[2, 0, 1], "2026-01", "2026-03"]);
  assert.equal(M.monthBuckets(["2026-03-01"]).counts.length, 2);
});
t("model: indexFileLinks", () => {
  assert.equal(M.indexFileLinks(null), null); assert.equal(M.indexFileLinks({ paths: ["a"] }), null);
  const m = M.indexFileLinks({ paths: ["a", "b"], links: [[[1, 3]], []], commit: "c" });
  assert.deepEqual(m.map.get("a"), [{ path: "b", n: 3 }]); assert.deepEqual(m.map.get("b"), []);
});
t("model: noteFileName and notePrompt", () => { assert.equal(M.noteFileName("a/b.py"), "a__b.py.json"); const p = M.notePrompt("a/b.py"); assert.ok(p.includes("a__b.py.json") && p.includes("git hash-object a/b.py")); });
console.log(`${n} passed`);
