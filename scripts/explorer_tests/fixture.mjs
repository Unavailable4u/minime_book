// Synthetic census (same shapes as data/code/*.json, data/index/notes.json, data/graph/file-links.json) and a jsdom page loader.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const FIELDS = ["name", "lang", "lines", "code", "functions", "classes", "commits", "last", "flags", "shard"];
const fn = (q, s, e, x = {}) => ({ qual: q, name: q.split(".").pop(), start: s, end: e, loc: e - s + 1, cc: 3, doc1: "", params: [{ name: "x", annotation: "int", default: null }], returns: "str", hash: `h_${q}`, kind: q.includes(".") ? "method" : "function", visibility: "public", ...x });

export const COMMIT = `a1389bfdeadbeef${"0".repeat(25)}`;     // 40 hex characters, starts with the census commit of the fixture
export const DOC_MD = [
  "# Title", "", "Some **bold** text and a [file](backend/agents/a.py#L3-L5), a [folder](backend/), a [dead](nope.md), an [evil](javascript:alert(1)) link, an [outside](https://example.org).", "",
  "## Section", "", "- one", "- two", "", "## Third", "", "```python", "def f():", "    return 1", "```", "", "### Fourth", "", "| a | b |", "|---|--:|", "| 1 | 2 |", "", "![pic](https://example.org/x.png)", "", "[jump](#third)", ""].join("\n");
export const BLOB = "b".repeat(40);
/* The embedded copy of backend/agents/a.py: 150 lines, line N reads "line N", with a few awkward ones. */
export const SRC_LINES = Array.from({ length: 150 }, (_, i) => `line ${i + 1}`);
SRC_LINES[9] = "def run(x):  # <b>not html</b>";
SRC_LINES[10] = "";
SRC_LINES[11] = "\treturn '&amp;'";

export function writeFixture(dir, { big = false, drift = false, long = false, docs = false } = {}) {
  const W = (rel, o) => { const p = path.join(dir, rel); fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(o)); };
  const recs = [
    { path: "backend/agents/a.py", functions: [fn("run", 10, 20, { doc1: "Run it.", raises: ["ValueError"], decorators: ["cached"], calls: [["route", "backend/api/b.py::route"], ["Agent", "backend/agents/a.py::Agent"], ["print", null], ["os.path.join", null], ["print", null], ["gone", "gone/x.py::f"]] }), fn("Agent.step", 30, 40), fn("_clean_query", 120, 141)], classes: [{ qual: "Agent", name: "Agent", start: 25, end: 50, loc: 26, bases: ["Base"], hash: "h_Agent" }],
      module_doc: "Agents.\n\nMore.", git: { commits: 5, first: "2026-01-02", last: "2026-10-05", dates: ["2026-01-02", "2026-03-04", "2026-03-09", "2026-10-05", "2026-10-05"], added: 100, deleted: 20 }, exports: ["run"], size: 900, comment: 3, blank: 4 },
    { path: "backend/api/b.py", functions: [fn("route", 1, 5)], classes: [], git: { commits: 0 } },
    { path: "README.md", functions: [], classes: [] },
  ];
  const many = [];
  if (big) for (let i = 0; i < 500; i++) many.push(fn(`f${i}`, i * 3 + 1, i * 3 + 2));
  recs[1].functions.push(...many);
  const dirs = [{ name: "backend", n: { files: 2, lines: 100, code: 80, functions: 4, classes: 1 }, files: [], dirs: [
    { name: "agents", n: { files: 1, lines: 60, code: 50, functions: 3, classes: 1 }, files: [["a.py", "py", 60, 50, 3, 1, 5, "2026-10-05", "", 0]], dirs: [] },
    { name: "api", n: { files: 1, lines: 40, code: 30, functions: 1, classes: 0 }, files: [["b.py", "py", 40, 30, 1, 0, 0, "", "t", 0]], dirs: [] }] }];
  if (big) dirs.push({ name: "bulk", n: { files: 1200, lines: 1, code: 1, functions: 0, classes: 0 }, dirs: [], files: Array.from({ length: 1200 }, (_, i) => [`m${String(i).padStart(4, "0")}.py`, "py", 1, 1, 0, 0, 0, "", "", 0]) });
  W("data/code/tree.json", { file_fields: FIELDS, shards: ["s0"], commit: "a1389bfdeadbeef", generated: "2026-11-01", root: { files: [["README.md", "md", 10, 8, 0, 0, 1, "2026-01-01", "", 0], ...(docs ? [["conf.json", "json", 3, 3, 0, 0, 0, "", "", 0], ["m.sql", "sql", 3, 3, 0, 0, 0, "", "", 0], ["bad.json", "json", 1, 1, 0, 0, 0, "", "", 0]] : [])], dirs } });
  W("data/code/files/s0.json", { files: recs });
  W("data/code/imports.json", { imports: { "backend/api/b.py": ["backend/agents/a.py", "nowhere.py"] }, imported_by: { "backend/agents/a.py": ["backend/api/b.py"] }, external: { "backend/agents/a.py": ["httpx"] } });
  W("data/index/notes.json", { totals: { files: 3, noted: 1 }, folders: { "backend/agents": { files: 1, noted: 1, stale: 0 }, backend: { files: 2, noted: 1, stale: 0 } }, files: { "backend/agents/a.py": { status: "fresh", tier: 1 } } });
  W("data/notes/backend__agents__a.py.json", { summary: "Agent module.", purpose: "p", written: "2026-10-20", commit: "abcdef123", blob: drift ? "c".repeat(40) : BLOB, symbols: [{ qual: "run", summary: "Runs the agent.", details: "Longer text about run.", params: [{ name: "x", desc: "the input value" }, { name: "extra", desc: "only the note knows" }], returns: "the result text", raises: ["KeyError when missing"], side_effects: ["writes a log"], confidence: "medium", evidence: ["12-14", "bad", "18"], hash: "h_run" }, { qual: "Agent.step", summary: "Steps.", hash: "OLD" }], blocks: [
    { lines: "10-20", title: "Run", text: "x", anchor: "def run(x):" },                       // right place
    { lines: "30-40", title: "Step", text: "Steps once.", anchor: "line 30" },                // right place
    { lines: "120-141", title: "Cleaning", text: "Cleans the query.", anchor: "line 125" },   // moved 5 lines down: 125-146
    { lines: "145-150", title: "Tail", text: "No anchor." },                                   // not checked
    { lines: "200-210", title: "Past the end", text: "z", anchor: "line 200" },               // left out
    { lines: "abc", title: "Broken", text: "z" }] });                                          // left out
  if (long) {                                        // a note for the 2,500-line b.py, with blocks in the first chunk and in the last
    const r = (i) => `row ${i}`;
    W("data/notes/backend__api__b.py.json", { summary: "Router.", purpose: "p", written: "2026-10-20", commit: "abcdef123", blob: BLOB, symbols: [], blocks: [
      { lines: "5-8", title: "Top", text: "First.", anchor: r(5) }, { lines: "1500-1510", title: "Middle", text: "Second.", anchor: r(1500) }, { lines: "2400-2410", title: "Late", text: "Third.", anchor: r(2400) }] });
    const idx = JSON.parse(fs.readFileSync(path.join(dir, "data/index/notes.json"), "utf8"));
    idx.files["backend/api/b.py"] = { status: "fresh", tier: 2 };
    W("data/index/notes.json", idx);
  }
  W("content/config.json", { github: { repo: "Unavailable4u/MiniMe" }, editor: { scheme: "vscode" }, embedSource: true });
  W("data/src/manifest.json", { schema: 1, commit: drift ? "d".repeat(40) : COMMIT, files: { "backend/agents/a.py": BLOB, ...(big || long ? { "backend/api/b.py": BLOB } : {}) } });
  fs.mkdirSync(path.join(dir, "data/src/backend/agents"), { recursive: true });
  fs.writeFileSync(path.join(dir, "data/src/backend/agents/a.py.txt"), `${SRC_LINES.join("\n")}\n`);
  if (big || long) {                                 // a 2,500-line file: the viewer draws 1,000 lines at a time
    fs.mkdirSync(path.join(dir, "data/src/backend/api"), { recursive: true });
    fs.writeFileSync(path.join(dir, "data/src/backend/api/b.py.txt"), `${Array.from({ length: 2500 }, (_, i) => `row ${i + 1}`).join("\n")}\n`);
  }
  if (docs) {
    const man = JSON.parse(fs.readFileSync(path.join(dir, "data/src/manifest.json"), "utf8"));
    const put = (name, text) => { man.files[name] = BLOB; fs.writeFileSync(path.join(dir, "data/src", `${name}.txt`), text); };
    put("README.md", DOC_MD); put("conf.json", '{"name":"x","list":[1,2,3],"nested":{"a":null}}\n'); put("bad.json", '{"a": 1 "b": 2}\n');
    put("m.sql", "-- Migration\nCREATE TABLE t (id int primary key, n text not null);\nGRANT SELECT ON t TO anon;\n");
    W("data/src/manifest.json", man);
  }
  W("data/code/callers/s0.json", { schema: 2, shard: "s0", callers: { "backend/agents/a.py::run": ["backend/api/b.py::route", "backend/agents/a.py::Agent.step", "backend/api/b.py::f1", "backend/api/b.py::f2"], "backend/agents/a.py::Agent": ["backend/api/b.py::route"], "backend/api/b.py::route": ["backend/agents/a.py::run"] } });
  W("data/graph/file-links.json", { paths: ["backend/agents/a.py", "backend/api/b.py"], links: [[[1, 4]], [[0, 4]]], commit: "abc", date: "2026-11-01" });
}

export async function jsdomOrSkip() {
  try { return (await import("jsdom")).JSDOM; } catch { console.log("SKIP: jsdom is not installed (npm install --prefix scripts/explorer_tests jsdom)"); process.exit(77); }
}

/* Load explorer.html (scripts stripped) in jsdom, serve data/ from a temp fixture, and import the real main.js. `omit` = data paths that answer 404. */
export async function boot({ hash = "", omit = [], big = false, drift = false, long = false, docs = false } = {}) {
  const JSDOM = await jsdomOrSkip();
  const data = fs.mkdtempSync(path.join(os.tmpdir(), "explorer-"));
  writeFixture(data, { big, drift, long, docs });
  const html = fs.readFileSync(path.join(ROOT, "explorer.html"), "utf8").replace(/<script[\s\S]*?<\/script>/g, "");
  const dom = new JSDOM(html, { url: `http://localhost:8000/explorer.html${hash}`, pretendToBeVisual: true });
  const w = dom.window;
  const set = (k, v) => Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  for (const k of ["document", "location", "history", "localStorage", "Node", "HTMLElement", "requestAnimationFrame", "cancelAnimationFrame"]) set(k, w[k]);
  set("window", w); set("navigator", w.navigator);
  w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
  const errors = [];
  w.addEventListener("error", (e) => errors.push(e.message));
  process.on("unhandledRejection", (e) => errors.push(`rejection: ${e}`));
  const rootPath = pathToFileURL(ROOT).pathname.replace(/\/?$/, "/");
  globalThis.fetch = async (u) => {
    const rel = decodeURIComponent(new URL(String(u)).pathname).slice(rootPath.length);
    const f = path.join(data, rel);
    return !omit.includes(rel) && fs.existsSync(f) ? { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(f, "utf8")), text: async () => fs.readFileSync(f, "utf8") } : { ok: false, status: 404, json: async () => ({}), text: async () => "" };
  };
  await import(`${pathToFileURL(path.join(ROOT, "assets/js/explorer/main.js")).href}?${Math.random()}`);
  const wait = (ms = 80) => new Promise((r) => setTimeout(r, ms));
  await wait(200);
  const doc = w.document;
  return {
    w, doc, errors, wait,
    nav: async (h) => { w.location.hash = h; await wait(150); },
    key: (el, k, o = {}) => el.dispatchEvent(new w.KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true, ...o })),
    text: (id) => doc.getElementById(id).textContent.replace(/\s+/g, " "),
    rows: () => [...doc.querySelectorAll(".ex-row")].map((r) => r.textContent.replace(/[▾▸]/g, "").trim()),
  };
}

export function makeOk() {
  const S = { fails: 0, n: 0 };
  const ok = (c, m) => { S.n++; if (!c) { S.fails++; console.log(`FAIL: ${m}`); } else console.log(`ok: ${m}`); };
  return { ok, done: (errors = []) => { if (errors.length) { S.fails++; console.log("page errors:", errors); } console.log(`${S.n - S.fails}/${S.n} passed`); process.exit(S.fails ? 1 : 0); } };
}
