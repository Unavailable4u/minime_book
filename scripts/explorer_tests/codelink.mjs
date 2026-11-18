// P15: assets/js/codelink.js (targets, lookup, the card's content, a chapter page in jsdom) and assets/js/explorer/backlinks.js.
//   node codelink.mjs              every scenario, each in its own process (model.js caches fetched JSON for the life of the page)
//   node codelink.mjs pure|page|nolinkables|fetchfail
// The page scenarios need jsdom (npm install --prefix scripts/explorer_tests jsdom); without it they exit 77 and the pure ones still run.
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SCENARIOS = ["pure", "page", "nolinkables", "fetchfail"];
const which = process.argv[2];
if (!which) {
  let bad = 0;
  let skipped = false;
  for (const sc of SCENARIOS) {
    const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), sc], { encoding: "utf8", env: { ...process.env, NODE_NO_WARNINGS: "1" } });
    process.stdout.write(`--- ${sc}\n${r.stdout}${r.stderr}`);
    if (r.status === 77) skipped = true;
    else if (r.status !== 0) bad++;
  }
  process.exit(bad ? 1 : skipped ? 77 : 0);
}

const { ROOT, makeOk, writeFixture, jsdomOrSkip } = await import("./fixture.mjs");
const L = await import(pathToFileURL(path.join(ROOT, "assets/js/codelink.js")).href);
const B = await import(pathToFileURL(path.join(ROOT, "assets/js/explorer/backlinks.js")).href);
const { ok, done } = makeOk();

/* ------------------------------------------------------------------ pure */
if (which === "pure") {
  const P = (t) => JSON.stringify(L.parseTarget(t));
  ok(P("backend/api/deps.py") === '{"kind":"file","path":"backend/api/deps.py","qual":"","start":null,"end":null}', "parseTarget: a file");
  ok(P("a/b.py::Cls.m@10-20") === '{"kind":"file","path":"a/b.py","qual":"Cls.m","start":10,"end":20}', "parseTarget: symbol and lines");
  ok(P("a/b.py@7") === '{"kind":"file","path":"a/b.py","qual":"","start":7,"end":null}', "parseTarget: one line");
  ok(P("a/b.py@9-3") === '{"kind":"file","path":"a/b.py","qual":"","start":9,"end":null}', "parseTarget: a backwards range is one line");
  ok(P("frontend/@types/x.d.ts") === '{"kind":"file","path":"frontend/@types/x.d.ts","qual":"","start":null,"end":null}', "parseTarget: an @ inside a folder name is part of the path");
  ok(P("m2c/src/") === '{"kind":"dir","path":"m2c/src"}', "parseTarget: a folder");
  ok(["", "  ", null, undefined, 5, "../etc/passwd", "a/../b.py", "/"].every((x) => L.parseTarget(x) === null), "parseTarget: empty, wrong type and climbing paths are null");

  ok(L.explorerHref(L.parseTarget("a/b.py")) === "explorer.html#/f/a/b.py", "explorerHref: file");
  ok(L.explorerHref(L.parseTarget("a/b.py::A.m")) === "explorer.html#/f/a/b.py::A.m?tab=symbols", "explorerHref: a symbol opens the Symbols tab");
  ok(L.explorerHref(L.parseTarget("a/b.py@3-9")) === "explorer.html#/f/a/b.py@3-9?tab=source", "explorerHref: lines open the Source tab");
  ok(L.explorerHref(L.parseTarget("a b/c.py")) === "explorer.html#/f/a%20b/c.py", "explorerHref: spaces are encoded");
  ok(L.explorerHref(L.parseTarget("a/b/")) === "explorer.html#/d/a/b", "explorerHref: folder");
  ok(L.explorerHref(null) === null, "explorerHref: null");

  const data = { links: { x_name: "a/x.py::x_name", "constructor": "never" }, choices: { twin: ["a/b.py::t", "c/d.py::t"], solo: [] }, sections: { "doc.html#s": { twin: "c/d.py::t" } } };
  ok(L.lookup(data, "x_name", "doc.html#s").target === "a/x.py::x_name", "lookup: a link");
  ok(L.lookup(data, "twin", "doc.html#s").kind === "link" && L.lookup(data, "twin", "doc.html#s").target === "c/d.py::t", "lookup: the section's own answer wins");
  ok(L.lookup(data, "twin", "doc.html#other").kind === "choices" && L.lookup(data, "twin").targets.length === 2, "lookup: elsewhere it is a choice");
  ok(L.lookup(data, "solo") === null && L.lookup(data, "missing") === null, "lookup: an empty choice and an unknown text are null");
  ok(L.lookup(data, "toString") === null && L.lookup(data, "__proto__") === null && L.lookup(data, "hasOwnProperty") === null, "lookup: object prototype names are not texts");
  ok(L.lookup(null, "x") === null && L.lookup({}, "x") === null && L.lookup(data, 5) === null, "lookup: bad input is null");

  ok(L.pageName("/doc-x.html") === "doc-x.html" && L.pageName("/guides/doc-x.html") === "doc-x.html" && L.pageName("/doc-x") === "doc-x.html" && L.pageName("/") === "" && L.pageName("") === "", "pageName: file, folder, clean URL, nothing");

  // describeTarget with a fake environment
  const M = await import(pathToFileURL(path.join(ROOT, "assets/js/explorer/model.js")).href);
  const file = { path: "a/x.py", name: "x.py", lines: 120, functions: 2, classes: 1, binary: false };
  const rec = { path: "a/x.py", module_doc: "Does the x thing.\n\nMore.", functions: [{ qual: "f", name: "f", start: 3, end: 9, loc: 7, cc: 2, doc1: "Runs f.", hash: "h1", params: [{ name: "n", annotation: "int" }], returns: "str" }], classes: [] };
  const note = { summary: "File note.", symbols: [{ qual: "f", summary: "AI summary of f.", hash: "h1" }] };
  const tree = { files: new Map([["a/x.py", file], ["a/bin.png", { path: "a/bin.png", name: "bin.png", binary: true, lines: 0 }]]), dirs: new Map([["a", { n: { files: 2, lines: 120, functions: 2 } }]]) };
  const env = (over = {}) => ({ tree, notes: { files: { "a/x.py": { status: "fresh" } } }, linkOpts: { commit: "a".repeat(40) }, loadRecord: async () => rec, loadNote: async () => note, ...over });
  const D = (t, e) => L.describeTarget(t, e || env());

  let d = await D("a/x.py::f");
  ok(d.kind === "function" && d.title === "f" && d.where === "a/x.py" && d.sig === "f(n: int) -> str", `describe symbol: kind, title, signature (${d.sig})`);
  ok(d.summary === "AI summary of f." && d.from === "note" && d.fresh === "fresh" && d.stats === "lines 3–9 · 7 loc · cc 2", `describe symbol: note summary, freshness, numbers (${d.stats})`);
  ok(d.buttons.explorer === "explorer.html#/f/a/x.py::f?tab=symbols" && d.buttons.source === "explorer.html#/f/a/x.py::f@3-9?tab=source", "describe symbol: Explorer and Source links carry the symbol's lines");
  ok(d.buttons.github === `https://github.com/Unavailable4u/MiniMe/blob/${"a".repeat(40)}/a/x.py#L3-L9` && d.buttons.vscode === undefined, "describe symbol: GitHub at the census commit, no VS Code without a folder");
  d = await D("a/x.py::f", env({ loadNote: async () => ({ symbols: [{ qual: "f", summary: "S", hash: "different" }] }) }));
  ok(d.fresh === "stale", "describe symbol: a changed hash is stale");
  d = await D("a/x.py::f", env({ notes: { files: {} }, loadNote: async () => { throw new Error("must not be asked"); } }));
  ok(d.summary === "Runs f." && d.from === "doc" && d.fresh === "none", "describe symbol: no note means the docstring, and the note is not even fetched");
  d = await D("a/x.py::gone");
  ok(d.summary.includes("not in the census") && d.buttons.explorer.includes("::gone"), "describe symbol: a symbol that moved says so and still links");
  d = await D("a/x.py");
  ok(d.kind === "file" && d.title === "x.py" && d.summary === "File note." && d.stats === "120 lines · 2 functions · 1 classes", `describe file (${d.stats})`);
  d = await D("a/x.py@5-8");
  ok(d.buttons.github.endsWith("#L5-L8") && d.buttons.source === "explorer.html#/f/a/x.py@5-8?tab=source", "describe file with lines: the lines win");
  d = await D("a/x.py", env({ notes: { files: {} } }));
  ok(d.summary === "Does the x thing." && d.from === "doc", "describe file: no note, the first paragraph of the module docstring");
  d = await D("a/bin.png");
  ok(d.buttons.source === undefined && d.buttons.explorer === "explorer.html#/f/a/bin.png", "describe binary: no Source button");
  d = await D("a/");
  ok(d.kind === "folder" && d.stats === "2 files · 120 lines · 2 functions" && d.buttons.explorer === "explorer.html#/d/a" && !d.buttons.source, "describe folder");
  d = await D("nowhere/y.py::g");
  ok(d.missing === true && d.buttons.explorer.includes("nowhere/y.py") && !d.buttons.source, "describe a file the census lacks: marked missing, still links");
  d = await D("a/x.py::f", env({ loadRecord: async () => { throw new Error("shard 404"); } }));
  ok(d.kind === "symbol" && d.where === "a/x.py" && d.buttons.explorer, "describe: a failed record load still gives a card with links");
  ok((await D("")) === null && (await D(null)) === null, "describe: not a target is null");

  // backlinks
  const doc = { chapters: [{ url: "doc-a.html", title: "A" }, { url: "doc-b.html", title: "B" }], mentions: {
    "p/x.py": [{ c: 1, id: "s2", h: "Two", s: "snip", n: 1 }, { c: 0, id: "s1", h: "One", s: "", n: 3 }],
    "p/x.py::f": [{ c: 0, id: "s1", h: "One", s: "sf", n: 1 }], "p/x.py::g": [{ c: 1, id: "", h: "", s: "", n: 1 }], "p/xy.py": [{ c: 0, id: "z", h: "Z", s: "", n: 1 }],
    "q/orphan.py": [{ c: 9, id: "a", h: "", s: "", n: 1 }] } };
  let m = B.bookMentions(doc, "p/x.py");
  ok(m.length === 4 && m.map((x) => x.url).join() === "doc-a.html#s1,doc-a.html#s1,doc-b.html,doc-b.html#s2", `bookMentions: a file takes its own and its symbols' mentions, in chapter order (${m.map((x) => x.url)})`);
  ok(m[0].sym === "" && m[1].sym === "f" && m[0].n === 3 && m[2].sym === "g", "bookMentions: file mentions first within a section, then symbols");
  ok(!m.some((x) => x.url.endsWith("#z")), "bookMentions: p/xy.py is not p/x.py");
  m = B.bookMentions(doc, "p/x.py", "f");
  ok(m.length === 1 && m[0].sym === "f" && m[0].snippet === "sf", "bookMentions: one symbol");
  ok(B.bookMentions(doc, "q/orphan.py").length === 0, "bookMentions: a mention of a chapter that is gone is dropped");
  ok(B.bookMentions(null, "p/x.py").length === 0 && B.bookMentions({}, "p/x.py").length === 0 && B.bookMentions(doc, "").length === 0 && B.bookMentions(doc, "none.py").length === 0, "bookMentions: no data, no path, no mentions");
  done();
}

/* ------------------------------------------------------------------ a chapter page in jsdom */
const CHAPTER = `<html><head><title>X</title></head><body><main><div class="bk-banner"><p class="bk-desc">d</p></div><article>
<nav class="toc"><a href="#intro"><code>backend/agents/a.py</code></a></nav>
<h2 id="intro">Intro</h2>
<p>See <code>backend/agents/a.py</code> and <code>Agent.step</code>, <code>_clean_query</code>, <code>unknown_thing</code>, <code>twin</code>.</p>
<pre><code>backend/agents/a.py</code></pre>
<p><a href="elsewhere.html"><code>backend/agents/a.py</code></a> <code><b>Agent.step</b></code></p>
<h2 id="two">Two</h2>
<p><code>twin</code> <code>backend/</code> <code>backend/agents/a.py:12-14</code> <code>gone/x.py</code></p>
</article></main></body></html>`;

async function chapter({ omit = [] } = {}) {
  const JSDOM = await jsdomOrSkip();
  const data = fs.mkdtempSync(path.join(os.tmpdir(), "codelink-"));
  writeFixture(data, {});
  const dom = new JSDOM(CHAPTER, { url: "http://localhost:8000/doc-x.html", pretendToBeVisual: true });
  const w = dom.window;
  const set = (k, v) => Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  for (const k of ["document", "location", "history", "localStorage", "Node", "HTMLElement"]) set(k, w[k]);
  set("window", w); set("navigator", w.navigator);
  const errors = [];
  w.addEventListener("error", (e) => errors.push(e.message));
  process.on("unhandledRejection", (e) => errors.push(`rejection: ${e}`));
  const rootPath = pathToFileURL(ROOT).pathname.replace(/\/?$/, "/");
  globalThis.fetch = async (u) => {
    const rel = decodeURIComponent(new URL(String(u)).pathname).slice(rootPath.length);
    const f = path.join(data, rel);
    if (omit.includes(rel) || !fs.existsSync(f)) return { ok: false, status: 404, json: async () => ({}), text: async () => "" };
    if (omit.includes(`!${rel}`)) throw new TypeError("network down");
    return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(f, "utf8")), text: async () => fs.readFileSync(f, "utf8") };
  };
  const wait = (ms = 80) => new Promise((r) => setTimeout(r, ms));
  const n = await L.initCodeLinks({ doc: w.document, win: w });
  return { w, doc: w.document, errors, wait, n, data };
}

if (which === "page") {
  const { w, doc, errors, wait, n, data } = await chapter();
  const links = [...doc.querySelectorAll("a.mm-codelink")];
  const href = (text) => links.find((a) => a.textContent === text && !a.closest(".toc"))?.getAttribute("href");
  ok(n === 9 && links.length === 9, `nine <code> spans became links (${n} / ${links.length})`);
  ok(href("backend/agents/a.py") === "explorer.html#/f/backend/agents/a.py", "a file links to its Explorer page");
  ok(href("Agent.step") === "explorer.html#/f/backend/agents/a.py::Agent.step?tab=symbols", "a symbol links to its Symbols tab (also when the <code> holds a <b>)");
  ok(href("backend/") === "explorer.html#/d/backend", "a folder links to the folder page");
  ok(href("backend/agents/a.py:12-14") === "explorer.html#/f/backend/agents/a.py@12-14?tab=source", "a line range links to the Source tab");
  ok(links.every((a) => a.firstElementChild && a.firstElementChild.tagName === "CODE"), "the <code> element stays inside the link");
  const twin = links.filter((a) => a.textContent === "twin");
  ok(twin.length === 2 && twin[0].classList.contains("mm-codelink--choice") && twin[0].getAttribute("aria-haspopup") === "dialog", "in the section with no answer, twin is a chooser");
  ok(!twin[1].classList.contains("mm-codelink--choice") && twin[1].getAttribute("href") === "explorer.html#/f/backend/api/b.py::route?tab=symbols", "in section two the section's own answer is a plain link");
  const text = (s) => [...doc.querySelectorAll(s)].map((x) => x.textContent);
  ok(!doc.querySelector("pre a") && !doc.querySelector(".toc a.mm-codelink") && !doc.querySelector("a a"), "nothing inside <pre>, the contents list or another link is linked");
  ok(!links.some((a) => a.textContent === "unknown_thing"), "a text that is not in linkables stays plain");
  ok(doc.querySelector('a[href="elsewhere.html"]').firstElementChild.tagName === "CODE" && !doc.querySelector('a[href="elsewhere.html"] a'), "an existing link is left alone");
  const linkables = JSON.parse(fs.readFileSync(path.join(data, "data/index/linkables.json"), "utf8"));
  ok(L.linkChapter(doc.querySelector("main"), linkables, "doc-x.html", doc).linked === 0 && doc.querySelectorAll("a.mm-codelink").length === 9, "running it again adds nothing");
  ok(!!doc.head.querySelector('link[href$="assets/css/codelink.css"]'), "the stylesheet is requested");

  const over = (el, type = "mouseover") => el.dispatchEvent(new w.MouseEvent(type, { bubbles: true }));
  const card = () => doc.querySelector(".mm-cc");
  const step = links.find((a) => a.textContent === "Agent.step");
  over(step);
  await wait(500);
  ok(card() && !card().hidden && card().textContent.includes("Steps.") && card().textContent.includes("AI note"), `hovering opens the card with the note's summary (${card()?.textContent.slice(0, 80)})`);
  ok(card().textContent.includes("code changed since the note") && !!card().querySelector(".mm-badge--stale"), "the card says the note is stale (the census hash differs)");
  const btns = [...card().querySelectorAll(".mm-cc__go a")].map((a) => [a.textContent, a.getAttribute("href")]);
  ok(btns.map((b) => b[0]).join() === "Open in Explorer,Source,GitHub" && btns[0][1] === "explorer.html#/f/backend/agents/a.py::Agent.step?tab=symbols", `buttons: Explorer, Source, GitHub (${btns.map((b) => b[0])})`);
  ok(step.getAttribute("aria-expanded") === "true", "the link says its card is open");
  w.document.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  ok(card().hidden && !step.hasAttribute("aria-expanded"), "Escape closes the card");
  over(step); over(step, "mouseout");
  await wait(500);
  ok(card().hidden, "moving away before the delay shows nothing (or closes it again)");

  const file = links.find((a) => a.textContent === "backend/agents/a.py");
  file.dispatchEvent(new w.FocusEvent("focusin", { bubbles: true }));
  await wait(150);
  ok(!card().hidden && card().textContent.includes("Agent module.") && card().textContent.includes("60 lines"), "focusing a file link shows the file's note and size (keyboard users get the card too)");
  const folder = links.find((a) => a.textContent === "backend/");
  folder.dispatchEvent(new w.FocusEvent("focusin", { bubbles: true }));
  await wait(150);
  ok(card().textContent.includes("2 files") && card().textContent.includes("backend/"), "a folder card shows its numbers");
  const lines = links.find((a) => a.textContent === "backend/agents/a.py:12-14");
  lines.dispatchEvent(new w.FocusEvent("focusin", { bubbles: true }));
  await wait(150);
  ok([...card().querySelectorAll(".mm-cc__go a")].some((a) => a.getAttribute("href") === "explorer.html#/f/backend/agents/a.py@12-14?tab=source"), "a line-range card opens the same lines");
  const gone = links.find((a) => a.textContent === "gone/x.py");
  gone.dispatchEvent(new w.FocusEvent("focusin", { bubbles: true }));
  await wait(150);
  ok(card().textContent.includes("Not in the census"), "a link to something the census no longer has says so on its card");

  const choice = twin[0];
  const click = new w.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
  choice.dispatchEvent(click);
  await wait(60);
  ok(click.defaultPrevented && !card().hidden, "clicking a chooser opens it instead of following the first candidate");
  const items = [...card().querySelectorAll(".mm-cc__list a")].map((a) => [a.textContent, a.getAttribute("href")]);
  ok(items.length === 2 && items[0][0] === "backend/agents/a.py::run" && items[1][1] === "explorer.html#/f/backend/api/b.py::route?tab=symbols", `the chooser lists every candidate (${JSON.stringify(items)})`);
  w.document.body.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  ok(card().hidden, "clicking elsewhere closes a pinned chooser");
  const mod = new w.MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ctrlKey: true });
  choice.dispatchEvent(mod);
  ok(!mod.defaultPrevented, "ctrl-click on a chooser keeps the browser's own behaviour (new tab)");
  done(errors);
}

if (which === "nolinkables") {
  const { doc, errors, n } = await chapter({ omit: ["data/index/linkables.json"] });
  ok(n === 0 && !doc.querySelector(".mm-codelink") && !doc.querySelector(".mm-cc") && !doc.head.querySelector("link"), "without linkables.json the chapter is untouched");
  done(errors);
}

if (which === "fetchfail") {
  const { doc, errors, n } = await chapter({ omit: ["!data/index/linkables.json"] });
  ok(n === 0 && !doc.querySelector(".mm-codelink"), "a network error leaves the chapter untouched and throws nothing");
  done(errors);
}
