/* MiniMe Atlas 2 - Overview (P07). One ES module, no dependencies. Loaded by index.html.

   index.html has no generated regions any more. It is a shell, and this module fills it from data:
     data/index/vitals.json       the numbers: written by scripts/refresh_atlas.py ("census") and refresh_graph.py ("graph")
     data/index/book.json         chapters, for links and the "docs built" date
     data/index/stats.json        the MiniMe commit, so code links point at the source that was indexed
     data/index/symbols*.json     the line of a function, looked up only for the step you are looking at
     content/nav.json             page titles for the directory table
     content/subsystems.json      the directory table (folders, what they do, chapter, pages, key files)
     content/system/request-path.json   "Anatomy of a request" (shared with the System page, P09)
     content/reading-paths.json   the reading paths, shared with docs.html
     content/overview/*.html      the hand-written text: hero, abstract, products, how the Atlas stays true
     content/overview/vitals.json why each vital sign matters, and where it links

   Every number on the page is drawn next to the commit and date it came from. Nothing is typed by hand here.
   Pure helpers are exported so scripts/test_overview.py can run them in Node with no browser. */

import { fmtN, fmtDate, stepInfo } from "./library.js";

const GITHUB = "https://github.com/Unavailable4u/MiniMe";
const BASE = typeof document !== "undefined" ? new URL("../../", import.meta.url) : null;

/* ================================================================== pure helpers (no DOM) */

export { fmtN, fmtDate };

/* Two commit ids are the same commit when one is a prefix of the other (7 characters against 40). */
export const sameCommit = (a, b) => !!a && !!b && (String(a).startsWith(String(b)) || String(b).startsWith(String(a)));

/* 3015, 16255 -> "18.5 %". No denominator: an en dash, not a made-up number. */
export function fmtPct(n, d) {
  if (!d) return "\u2013";
  return `${(Math.round((n / d) * 1000) / 10).toFixed(1)} %`;
}

/* "2026-10-07" of the newest chapter build, or "". */
export function docsBuilt(book) {
  let best = "";
  for (const c of (book && book.chapters) || []) if (typeof c.built === "string" && c.built > best) best = c.built;
  return best;
}

/* What the freshness chip says, and whether to colour it amber.
   Census, graph and notes describe the same commit when they are in step. They are "stale" (amber) when:
     - the census was taken with uncommitted files,
     - there is no graph, or the graph is from another commit than the census,
     - there are notes (P11 writes data/index/notes.json with {percent, commit}) from another commit.
   No notes yet is not stale: it is "none yet", so the chip does not stay amber until P11 exists. */
export function freshness({ census, graph, notes, docs }) {
  const items = [], reasons = [];
  if (!census) {
    items.push({ id: "census", tone: "stale", text: "census: not built" });
    reasons.push("data/index/vitals.json has no census yet. Run python scripts/refresh_atlas.py.");
  } else {
    const dirty = Number(census.dirty_files) > 0;
    items.push({ id: "census", tone: dirty ? "stale" : "ok", text: `MiniMe ${census.commit} \u00b7 ${fmtDate(census.generated)}` });
    if (dirty) reasons.push(`The census counted ${census.dirty_files} uncommitted file(s) in MiniMe.`);
  }
  if (!graph) {
    items.push({ id: "graph", tone: "stale", text: "graph: not built" });
    reasons.push("There is no graph in vitals.json yet. Run python scripts/refresh_graph.py.");
  } else {
    const ok = !census || sameCommit(graph.commit, census.commit);
    items.push({ id: "graph", tone: ok ? "ok" : "stale", text: `graph ${graph.commit} \u00b7 ${fmtDate(graph.date)}` });
    if (!ok) reasons.push(`The graph is from ${graph.commit} but the census is from ${census.commit}.`);
  }
  if (notes && Number.isFinite(notes.percent)) {
    const ok = !census || !notes.commit || sameCommit(notes.commit, census.commit);
    items.push({ id: "notes", tone: ok ? "ok" : "stale", text: `notes ${Math.round(notes.percent)} %` });
    if (!ok) reasons.push(`The notes were written at ${notes.commit}, the census is from ${census.commit}.`);
  } else {
    items.push({ id: "notes", tone: "none", text: "notes: none yet" });
  }
  items.push(docs ? { id: "docs", tone: "none", text: `docs built ${fmtDate(docs)}` } : { id: "docs", tone: "none", text: "docs: date unknown" });
  return { state: reasons.length ? "stale" : "ok", items, reasons };
}

/* "x,y x,y ..." for an SVG polyline: the values scaled into a w by h box. Fewer than two values: "". A flat series: a flat line. */
export function sparkPoints(values, w = 96, h = 24, pad = 2) {
  const v = (values || []).filter((x) => Number.isFinite(x));
  if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo;
  const r = (n) => Math.round(n * 10) / 10;
  return v.map((x, i) => `${r(pad + (i * (w - 2 * pad)) / (v.length - 1))},${r(span ? h - pad - ((x - lo) / span) * (h - 2 * pad) : h / 2)}`).join(" ");
}

/* One numeric series out of vitals.census.months: "commits" or "added". */
export function monthSeries(months, key) {
  return (months || []).map((m) => Number(m[key]) || 0);
}

/* The vital signs, in a fixed order, each with the commit and date it was measured at. A vital whose data is missing is left out
   (not shown as 0). `copy` is content/overview/vitals.json: the label, why-it-matters line and link of each. */
export function vitalCards(vitals, copy) {
  const out = [];
  const c = vitals && vitals.census, g = vitals && vitals.graph, text = (copy && copy.vitals) || {};
  const censusSrc = c ? { commit: c.commit, date: c.generated, tone: Number(c.dirty_files) > 0 ? "stale" : "ok" } : null;
  const graphSrc = g ? { commit: g.commit, date: g.date, tone: !c || sameCommit(g.commit, c.commit) ? "ok" : "stale" } : null;
  const add = (id, value, extra) => {
    const t = text[id] || {};
    out.push({ id, label: t.label || id, why: t.why || "", href: t.href || "", spark: null, context: "", ...extra, value });
  };
  if (c) {
    const k = c.kpis || {}, months = c.months || [];
    add("files", k.files, { display: fmtN(k.files), context: `${fmtN(k.source_files)} source and ${fmtN(k.test_files)} test files in Python and JavaScript`, source: censusSrc });
    add("code_lines", k.code_lines, { display: fmtN(k.code_lines), context: `of ${fmtN(k.total_lines)} lines in all`, spark: { label: "lines added per month", values: monthSeries(months, "added") }, source: censusSrc });
    add("functions", k.functions, { display: fmtN(k.functions), source: censusSrc });
    const d = c.docstrings;
    if (d) add("docstrings", d.documented, { display: fmtPct(d.documented, d.python_functions), context: `${fmtN(d.documented)} of ${fmtN(d.python_functions)} Python functions`, source: censusSrc });
    add("routes", k.routes, { display: fmtN(k.routes), source: censusSrc });
    add("commits", k.commits, { display: fmtN(k.commits), context: months.length ? `since ${months[0].month}` : "", spark: { label: "commits per month", values: monthSeries(months, "commits") }, source: censusSrc });
    add("tests_written", k.tests_written, { display: fmtN(k.tests_written), context: `in ${fmtN(k.test_files)} test files`, source: censusSrc });
  }
  if (g) {
    add("nodes", g.nodes, { display: fmtN(g.nodes), context: `in ${fmtN(g.communities)} communities`, source: graphSrc });
    add("links", g.links, { display: fmtN(g.links), source: graphSrc });
  }
  return out.filter((v) => Number.isFinite(v.value));
}

/* https://github.com/.../blob/<commit>/path#L12 (the path encoded segment by segment). */
export function githubUrl(path, commit, line) {
  const enc = String(path).split("/").map(encodeURIComponent).join("/");
  return `${GITHUB}/blob/${commit || "main"}/${enc}${line ? `#L${line}` : ""}`;
}

/* The rows of the directory table. `spec` is content/subsystems.json, `counts` is vitals.census.subsystems, `nav` is content/nav.json,
   `book` is data/index/book.json. Files no subsystem claims come last as "Everything else"; `totals` adds every row. */
export function directoryRows(spec, counts, nav, book, commit) {
  const pages = new Map();
  for (const w of (nav && nav.wings) || []) for (const it of w.items || []) if (it.chapter == null) pages.set(it.id, { title: it.title, url: it.url });
  const chapters = new Map(((book && book.chapters) || []).map((c) => [c.id, c]));
  const none = { files: 0, code: 0, functions: 0 };
  const rows = ((spec && spec.subsystems) || []).map((s) => {
    const [cid, heading] = String(s.chapter || "").split("#");
    const ch = chapters.get(cid);
    return {
      id: s.id, name: s.name, folder: s.folder, what: s.what, product: s.product,
      ...((counts && counts[s.id]) || none),
      chapter: ch ? { label: ch.label, title: ch.title, url: heading ? `${ch.url}#${heading}` : ch.url } : null,
      pages: (s.pages || []).map((id) => pages.get(id)).filter(Boolean),
      keyFiles: (s.key_files || []).map((f) => ({ text: f.qual ? `${f.path.split("/").pop()} \u00b7 ${f.qual}` : f.path.split("/").pop(), title: f.qual ? `${f.path} :: ${f.qual}` : f.path, url: githubUrl(f.path, commit) })),
    };
  });
  const other = counts && counts.other;
  if (other && other.files > 0) rows.push({ id: "other", name: "Everything else", folder: "", what: "Files no subsystem above claims: root files, configuration, data folders.", product: "", ...other, chapter: null, pages: [], keyFiles: [] });
  const totals = rows.reduce((t, r) => ({ files: t.files + r.files, code: t.code + r.code, functions: t.functions + r.functions }), { ...none });
  return { rows, totals };
}

/* ---- finding a function's line without loading every symbol shard */

const slug = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

/* Which data/index/symbols-<id>.json holds a file's symbols. Mirrors scripts/build_index.py shard_symbols: the top folder,
   or top__second for a folder that was too big, or top__files for a loose file in such a folder. `ids` are the shard ids of symbols.json. */
export function shardIdFor(path, ids) {
  const set = new Set(ids), parts = String(path).split("/");
  if (parts.length < 2) return set.has("_root") ? "_root" : null;
  const top = slug(parts[0]), second = parts.length > 2 ? slug(parts[1]) : "files";
  const id = [`${top}__${second}`, top].find((x) => set.has(x));
  return id || null;
}

/* The line of `qual` in `path` inside one parsed shard ({files, rows:[qual, file index, line, kind]}), or 0. */
export function lineOf(shard, path, qual) {
  const i = ((shard && shard.files) || []).indexOf(path);
  if (i < 0) return 0;
  const row = (shard.rows || []).find((r) => r[1] === i && r[0] === qual);
  return row ? Number(row[2]) || 0 : 0;
}

/* ================================================================== DOM layer */

function h(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  for (const c of kids) if (c != null) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}

async function getText(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.text();
}

/* A failed file leaves its section saying so; the rest of the page still draws. */
const soft = (rel) => getJSON(rel).catch((err) => { console.warn("[atlas overview]", err); return null; });
const $ = (id) => document.getElementById(id);
const note = (msg) => h("p", { class: "ov-empty" }, msg);
const LOCAL_HINT = "If you opened this file directly, start the local server: python scripts/serve.py";

const D = { vitals: null, stats: {}, book: null, nav: null, subsystems: null, steps: null, paths: null, copy: null, symbols: null, shards: new Map() };

/* ---- freshness chip */
async function renderFreshness() {
  const box = $("ov-fresh");
  let notes = null;
  try { notes = await getJSON("data/index/notes.json"); } catch { /* P11 has not landed: no notes yet */ }
  const f = freshness({ census: D.vitals && D.vitals.census, graph: D.vitals && D.vitals.graph, notes, docs: docsBuilt(D.book) });
  box.dataset.state = f.state;
  box.replaceChildren(...[   // replaceChildren turns a null argument into the text "null", so empty slots are filtered out
    h("span", { class: `mm-badge mm-badge--${f.state === "ok" ? "ok" : "stale"}` }, f.state === "ok" ? "In step" : "Out of step"),
    h("ul", { class: "ov-fresh__list" }, f.items.map((i) => h("li", { class: `ov-fresh__i ov-fresh__i--${i.tone}`, "data-id": i.id }, i.text))),
    f.reasons.length ? h("p", { class: "ov-fresh__why" }, f.reasons.join(" ")) : null].filter(Boolean));
}

/* ---- anatomy of a request */
async function shardFor(path) {
  if (!D.symbols) D.symbols = await getJSON("data/index/symbols.json");
  const id = shardIdFor(path, D.symbols.shards.map((s) => s.id));
  if (!id) return null;
  if (!D.shards.has(id)) {
    const file = D.symbols.shards.find((s) => s.id === id).file;
    D.shards.set(id, getJSON(`data/index/${file}`).catch(() => null));
  }
  return D.shards.get(id);
}

async function codeLink(ref) {
  const commit = D.stats.commit;
  const label = ref.qual ? `${ref.path.split("/").pop()} \u00b7 ${ref.qual}` : ref.path.split("/").pop();
  let line = 0;
  if (ref.qual) { try { line = lineOf(await shardFor(ref.path), ref.path, ref.qual); } catch { line = 0; } }
  return h("a", { href: githubUrl(ref.path, commit, line), target: "_blank", rel: "noopener", title: `${ref.path}${ref.qual ? " :: " + ref.qual : ""}${line ? ` (line ${line})` : ""}` }, h("code", {}, label));
}

function renderAnatomy() {
  const box = $("ov-steps"), doc = D.steps;
  if (!doc || !(doc.steps || []).length) { box.replaceChildren(note("The request path could not be loaded. " + LOCAL_HINT)); return; }
  const steps = doc.steps, chapters = new Map(((D.book && D.book.chapters) || []).map((c) => [c.id, c]));
  const strip = h("ol", { class: "mm-stepper ov-strip", "aria-label": "Steps of a request" });
  const panel = h("div", { class: "mm-card ov-step", role: "group", "aria-live": "polite" });
  const buttons = steps.map((s, i) => h("button", { type: "button", class: "ov-strip__b", id: `ov-step-${s.id}`, "aria-controls": "ov-step-panel", onclick: () => pick(i) }, s.title));
  buttons.forEach((b, i) => strip.append(h("li", {}, b)));
  panel.id = "ov-step-panel";
  let cur = -1;
  async function pick(i, focus) {
    if (i < 0 || i >= steps.length) return;
    cur = i;
    const s = steps[i];
    [...strip.children].forEach((li, j) => { li.classList.toggle("is-done", j < i); if (j === i) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");  buttons[j].tabIndex = j === i ? 0 : -1; });
    if (focus) buttons[i].focus();
    panel.setAttribute("aria-labelledby", buttons[i].id);
    panel.classList.toggle("ov-step--gate", !!s.gate);
    const [cid, heading] = String(s.chapter || "").split("#"), ch = chapters.get(cid);
    const links = h("ul", { class: "ov-step__code" });
    panel.replaceChildren(
      h("h3", { class: "ov-step__t" }, h("span", { class: "ov-step__n" }, `${i + 1} / ${steps.length}`), s.title, s.gate ? h("span", { class: "mm-badge mm-badge--stale" }, "approval gate") : null),
      h("p", { class: "ov-step__what" }, s.what),
      links,
      h("p", { class: "ov-step__more" },
        ch ? h("a", { href: heading ? `${ch.url}#${heading}` : ch.url }, `Read it in ${ch.label}`) : null,
        s.diagram ? h("a", { href: s.diagram }, "See the diagram") : null),
      h("div", { class: "ov-step__nav" },
        h("button", { type: "button", class: "mm-btn", disabled: i === 0, onclick: () => pick(i - 1, true) }, "Back"),
        h("button", { type: "button", class: "mm-btn mm-btn--primary", disabled: i === steps.length - 1, onclick: () => pick(i + 1, true) }, "Next step")));
    const items = await Promise.all((s.code || []).map(codeLink));
    if (cur === i) links.replaceChildren(...items.map((a) => h("li", {}, a)));
  }
  strip.addEventListener("keydown", (e) => {
    const d = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    pick(Math.min(steps.length - 1, Math.max(0, cur + d)), true);
  });
  box.replaceChildren(...[doc.intro ? h("p", { class: "ov-sub" }, doc.intro) : null,
    doc.needs_review ? h("p", { class: "ov-draft" }, h("span", { class: "mm-badge mm-badge--ai" }, "AI-drafted"), " ", doc.review_note || "Needs your review.") : null,
    strip, panel].filter(Boolean));
  pick(0);
}

/* ---- reading paths */
function renderPaths() {
  const box = $("ov-paths");
  const doc = D.paths, chapters = (D.book && D.book.chapters) || [];
  if (!doc || !(doc.paths || []).length) { box.replaceChildren(note("Reading paths could not be loaded. " + LOCAL_HINT)); return; }
  box.replaceChildren(...doc.paths.map((p) => h("article", { class: "mm-card ov-path" },
    h("h3", { class: "mm-card__title" }, p.title), p.blurb ? h("p", { class: "ov-path__b" }, p.blurb) : null,
    h("ol", { class: "ov-path__steps" }, (p.steps || []).map((st) => {
      const i = stepInfo(st, chapters, {}, D.stats.commit);
      if (!i) return null;
      return h("li", {}, h("span", { class: `ov-path__k${i.kind === "code" ? " ov-path__k--code" : ""}` }, i.kind === "code" ? "</>" : i.kind),
        h("a", i.external ? { href: i.url, target: "_blank", rel: "noopener" } : { href: i.url }, i.note || i.text));
    })))));
}

/* ---- vital signs */
function sparkline(s) {
  const pts = sparkPoints(s.values);
  if (!pts) return null;
  return svg("svg", { class: "ov-spark", viewBox: "0 0 96 24", role: "img", "aria-label": `${s.label}: ${s.values.length} months` }, svg("title", {}, s.label), svg("polyline", { points: pts, fill: "none" }));
}

function renderVitals() {
  const box = $("ov-vitals");
  const cards = vitalCards(D.vitals, D.copy);
  if (!cards.length) { box.replaceChildren(note("No numbers yet. Run python scripts/update_all.py, or python scripts/refresh_atlas.py.")); return; }
  box.replaceChildren(...cards.map((v) => {
    const src = v.source;
    const body = [
      h("div", { class: "mm-kpi" },
        h("span", { class: "mm-kpi__label" }, v.label),
        h("span", { class: "mm-kpi__value" }, v.display),
        v.context ? h("span", { class: "mm-kpi__context" }, v.context) : null),
      v.why ? h("p", { class: "ov-vital__why" }, v.why) : null,
      v.spark ? sparkline(v.spark) : null,
      h("p", { class: "mm-kpi__source" },
        h("span", { class: `mm-badge mm-badge--${src.tone === "ok" ? "ok" : "stale"}`, title: src.tone === "ok" ? "Measured at the same commit as the census." : "Not from the same commit as the census, or measured with uncommitted files." }, src.tone === "ok" ? "fresh" : "check"),
        `${src.commit} \u00b7 ${fmtDate(src.date)}`)];
    return v.href ? h("a", { class: "mm-card ov-vital ov-vital--link", href: v.href }, body) : h("div", { class: "mm-card ov-vital" }, body);
  }));
}

/* ---- directory table */
function renderDirectory() {
  const box = $("ov-dir");
  const c = D.vitals && D.vitals.census;
  if (!D.subsystems || !c || !c.subsystems || !Object.keys(c.subsystems).length) { box.replaceChildren(note("The directory could not be built. " + LOCAL_HINT)); return; }
  const { rows, totals } = directoryRows(D.subsystems, c.subsystems, D.nav, D.book, D.stats.commit || c.commit);
  const num = (n) => h("td", { class: "is-num" }, fmtN(n));
  const head = h("tr", {}, ["Subsystem", "What it does", "Files", "Code lines", "Functions", "Book", "Atlas pages", "Key files"].map((t, i) => h("th", { class: i >= 2 && i <= 4 ? "is-num" : "", scope: "col" }, t)));
  const body = rows.map((r) => h("tr", { id: `dir-${r.id}` },
    h("th", { scope: "row" }, h("b", {}, r.name), r.folder ? h("span", { class: "ov-dir__f" }, h("code", {}, r.folder)) : null),
    h("td", { class: "ov-dir__what" }, r.what), num(r.files), num(r.code), num(r.functions),
    h("td", {}, r.chapter ? h("a", { href: r.chapter.url, title: r.chapter.title }, r.chapter.label) : "\u2013"),
    h("td", { class: "ov-dir__pages" }, r.pages.length ? r.pages.map((p) => h("a", { href: p.url }, p.title)) : "\u2013"),
    h("td", { class: "ov-dir__keys" }, r.keyFiles.length ? r.keyFiles.map((k) => h("a", { href: k.url, target: "_blank", rel: "noopener", title: k.title }, h("code", {}, k.text))) : "\u2013")));
  const foot = h("tr", { class: "ov-dir__total" }, h("th", { scope: "row", colspan: 2 }, "All of the repository"), num(totals.files), num(totals.code), num(totals.functions), h("td", { colspan: 3 }));
  box.replaceChildren(
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table ov-dir__t" }, h("caption", { class: "ov-dir__cap" }, `Counted from MiniMe ${c.commit}, ${fmtDate(c.generated)}. Files that are not binary; code lines exclude comments and blanks.`), h("thead", {}, head), h("tbody", {}, body), h("tfoot", {}, foot))));
}

/* ---- details: the cards the old Overview had, so no information is lost */
function barCard(title, items, source) {
  const mx = Math.max(1, ...items.map((i) => i.value));
  return h("div", { class: "mm-card ov-card" }, h("h3", { class: "mm-card__title" }, title),
    items.map((i) => h("div", { class: "ov-bar" },
      i.href ? h("a", { class: "ov-bar__l", href: i.href, title: i.title || i.text }, i.text) : h("span", { class: "ov-bar__l", title: i.title || i.text }, i.text),
      h("i", { class: "ov-bar__i", style: `width:${Math.max(1.5, (i.value / mx) * 100).toFixed(1)}%` }), h("em", { class: "ov-bar__v" }, fmtN(i.value)))),
    h("p", { class: "mm-kpi__source" }, source));
}

const LANG_VARS = ["--brand", "--graph", "--gate", "--ok", "--pink"];

function langCard(c, source) {
  const total = c.languages.reduce((t, l) => t + l.code, 0) || 1;
  let acc = 0;
  const stops = c.languages.map((l, i) => { const a = (acc / total) * 100; acc += l.code; return `var(${LANG_VARS[i % LANG_VARS.length]}) ${a.toFixed(1)}% ${((acc / total) * 100).toFixed(1)}%`; });
  return h("div", { class: "mm-card ov-card" }, h("h3", { class: "mm-card__title" }, "Code by language"),
    h("div", { class: "ov-lang" }, h("div", { class: "ov-pie", role: "img", "aria-label": c.languages.map((l) => `${l.lang} ${fmtN(l.code)}`).join(", "), style: `background:conic-gradient(${stops.join(",")})` }),
      h("ul", { class: "ov-legend" }, c.languages.map((l, i) => h("li", {}, h("i", { style: `background:var(${LANG_VARS[i % LANG_VARS.length]})` }), `${l.lang} `, h("b", {}, fmtN(l.code)))))),
    h("p", { class: "mm-kpi__source" }, "Generated HTML, JSON, Markdown and config are left out. ", source));
}

function monthsCard(c, source) {
  const m = c.months, mx = Math.max(1, ...m.map((x) => x.commits)), W = 68;
  const chart = svg("svg", { class: "ov-months", viewBox: `0 0 ${W * m.length} 104`, role: "img", "aria-label": m.map((x) => `${x.month}: ${x.commits} commits`).join(", ") },
    ...m.flatMap((x, i) => {
      const hh = Math.max(4, Math.round((x.commits / mx) * 58)), X = 8 + W * i, Y = 86 - hh;
      return [svg("rect", { class: "ov-months__bar", x: X, y: Y, width: 52, height: hh, rx: 4 }, svg("title", {}, `${x.month}: ${x.commits} commits`)),
        svg("text", { class: "ov-months__m", x: X + 26, y: 101, "text-anchor": "middle" }, x.month.slice(2)),
        svg("text", { class: "ov-months__v", x: X + 26, y: Y - 5, "text-anchor": "middle" }, String(x.commits))];
    }));
  return h("div", { class: "mm-card ov-card" }, h("h3", { class: "mm-card__title" }, "Commits per month"), chart, h("p", { class: "mm-kpi__source" }, source));
}

function renderDetails() {
  const box = $("ov-details-body"), c = D.vitals && D.vitals.census, g = D.vitals && D.vitals.graph;
  if (!c) { box.replaceChildren(note("No census yet.")); return; }
  const src = `MiniMe ${c.commit} \u00b7 ${fmtDate(c.generated)}`, file = (p) => ({ text: p.split("/").pop(), title: p, href: `explorer.html#/f/${p.split("/").map(encodeURIComponent).join("/")}` });
  const cards = [
    langCard(c, src), monthsCard(c, src),
    barCard("Code lines by area", c.areas.map((a) => ({ text: a.area, value: a.code })), src),
    barCard("Largest files (code lines)", c.largest.map((f) => ({ ...file(f.path), value: f.code })), src),
    barCard("Most-changed files (commits)", c.changed.map((f) => ({ ...file(f.path), value: f.commits })), src),
    barCard("Most complex functions", c.complex.map((f) => ({ text: `${f.name}  ${f.path.split("/").pop()}`, title: `${f.name} in ${f.path}`, href: `explorer.html#/f/${f.path.split("/").map(encodeURIComponent).join("/")}`, value: f.cc })), src + ". Cyclomatic complexity, nested functions included."),
  ];
  if (g) cards.push(barCard("Graph hubs (most connections)", g.hubs.map((x) => ({ text: `${x.label}  ${x.path ? x.path.split("/").pop() : ""}`.trim(), title: x.path || x.label, href: x.path ? `explorer.html#/f/${x.path.split("/").map(encodeURIComponent).join("/")}` : "", value: x.links })), `graph ${g.commit} \u00b7 ${fmtDate(g.date)}`));
  box.replaceChildren(...cards);
}

/* ---- hand-written fragments */
async function loadFragments() {
  await Promise.all([...document.querySelectorAll("[data-fragment]")].map(async (el) => {
    try { el.innerHTML = await getText(`content/overview/${el.dataset.fragment}.html`); }
    catch (err) { console.warn("[atlas overview]", err); el.replaceChildren(note(`${el.dataset.fragment} could not be loaded. ${LOCAL_HINT}`)); }
  }));
}

async function boot() {
  [D.vitals, D.book, D.nav, D.subsystems, D.steps, D.paths, D.copy] = await Promise.all([
    soft("data/index/vitals.json"), soft("data/index/book.json"), soft("content/nav.json"), soft("content/subsystems.json"),
    soft("content/system/request-path.json"), soft("content/reading-paths.json"), soft("content/overview/vitals.json")]);
  D.stats = (await soft("data/index/stats.json")) || {};
  loadFragments();
  for (const draw of [renderFreshness, renderAnatomy, renderPaths, renderVitals, renderDirectory, renderDetails]) {
    try { await draw(); } catch (err) { console.warn("[atlas overview]", draw.name, err); }
  }
}

if (typeof document !== "undefined" && $("ov-vitals")) {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
}