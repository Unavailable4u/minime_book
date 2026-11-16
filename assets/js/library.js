/* MiniMe Atlas 2 - book library (P05). One ES module, no dependencies. Loaded by docs.html.

   Draws the table of contents of the book from data, so nothing on the page is typed by hand:
     data/index/book.json       chapters, parts, counts and last-built date, read by scripts/build_index.py from each chapter's banner
     content/reading-paths.json "I want to understand ..." paths: ordered chapter sections and code files
     data/index/search.json     chapter headings, for the in-book search and for naming path steps
     data/index/stats.json      the MiniMe commit, so code files link to the exact source that was indexed
     localStorage "minime_reader_pos"   written by reader.js (P04): how far the reader got in each chapter -> progress rings

   Pure helpers are exported so scripts/test_library.py can run them in Node with no browser. */

const KEY_POS = "minime_reader_pos";           // same key and shape as reader.js: { [chapter id]: { id, off, pct, t } }
const GITHUB_BLOB = "https://github.com/Unavailable4u/MiniMe/blob/";   // same repo palette.js links to
const BASE = typeof document !== "undefined" ? new URL("../../", import.meta.url) : null;
const MAX_HITS = 12;

/* ================================================================== pure helpers (no DOM) */

export const fmtN = (n) => new Intl.NumberFormat("en-US").format(n);

/* 37 -> "37 min"; 502 -> "8 h 22 min"; 120 -> "2 h". */
export function fmtMinutes(min) {
  if (!Number.isFinite(min) || min <= 0) return "";
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return m ? `${h} h ${m} min` : `${h} h`;
}

/* "2026-10-07" -> "7 Oct 2026". Anything else is shown as it is. */
export function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
  if (!m) return String(iso || "");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${Number(m[3])} ${months[Number(m[2]) - 1] || m[2]} ${m[1]}`;
}

/* The reader's saved position for one chapter, or null. */
export function readProgress(map, id) {
  const p = map && typeof map === "object" ? map[id] : null;
  if (!p || typeof p !== "object" || !Number.isFinite(p.pct)) return null;
  return { pct: Math.min(100, Math.max(0, Math.round(p.pct))), id: typeof p.id === "string" ? p.id : "", t: Number.isFinite(p.t) ? p.t : 0 };
}

/* "new" below 3 %, "done" from 96 %, otherwise "reading". Same thresholds reader.js uses for its resume toast. */
export function progressState(prog) {
  if (!prog || prog.pct < 3) return "new";
  return prog.pct >= 96 ? "done" : "reading";
}

/* Where the Continue button goes: the section the reader stopped in, else the top of the chapter. */
export function continueHref(chapter, prog) {
  return progressState(prog) === "reading" && prog.id ? `${chapter.url}#${encodeURIComponent(prog.id)}` : chapter.url;
}

/* The chapter read most recently and not finished, or null. */
export function mostRecent(chapters, map) {
  let best = null;
  for (const c of chapters) {
    const prog = readProgress(map, c.id);
    if (progressState(prog) !== "reading") continue;
    if (!best || prog.t > best.prog.t) best = { chapter: c, prog };
  }
  return best;
}

const norm = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
export const tokens = (q) => norm(q).split(/[^a-z0-9.]+/).filter(Boolean);

/* Every word of the query must appear (any order) in the chapter's label, title, blurb, description or part. */
export function filterChapters(chapters, q) {
  const t = tokens(q);
  if (!t.length) return chapters.slice();
  return chapters.filter((c) => {
    const hay = norm([c.label, c.title, c.blurb, c.desc, c.partTitle].join(" "));
    return t.every((w) => hay.includes(w));
  });
}

/* Heading matches for the in-book search: all words must appear in the heading or its chapter's title; headings that start with the
   query come first. */
export function matchHeadings(headings, q, limit = MAX_HITS) {
  const t = tokens(q);
  if (!t.length) return { rows: [], total: 0 };
  const first = t[0];
  const scored = [];
  for (const h of headings || []) {
    const title = norm(h.title), hay = `${title} ${norm(h.chapterTitle)}`;
    if (!t.every((w) => hay.includes(w))) continue;
    scored.push({ h, score: (title.startsWith(first) ? 0 : title.includes(first) ? 1 : 2) * 10 + Math.min(h.level || 3, 3) });
  }
  scored.sort((a, b) => a.score - b.score);
  return { rows: scored.slice(0, limit).map((s) => s.h), total: scored.length };
}

/* Link and label for one step of a reading path. `titles` maps "doc-x.html#id" to the heading's title. */
export function stepInfo(step, chapters, titles, commit) {
  if (step && step.chapter) {
    const c = chapters.find((x) => x.id === step.chapter);
    if (!c) return null;
    const url = step.heading ? `${c.url}#${step.heading}` : c.url;
    return { kind: c.label, url, text: (titles && titles[url]) || step.heading || c.title, note: step.note || "", external: false };
  }
  if (step && step.file) {
    const enc = step.file.split("/").map(encodeURIComponent).join("/");
    return { kind: "code", url: `${GITHUB_BLOB}${commit || "main"}/${enc}`, text: step.qual ? `${step.file} \u00b7 ${step.qual}` : step.file, note: step.note || "", external: true };
  }
  return null;
}

/* Circle for the progress ring: circumference of r=14, and how much of it is filled. */
export function ringDash(pct, r = 14) {
  const c = 2 * Math.PI * r;
  return { c: Math.round(c * 100) / 100, on: Math.round(c * Math.min(100, Math.max(0, pct)) / 100 * 100) / 100 };
}

/* ================================================================== DOM layer */
const MAP_INFO = {
  "web": {
    "head": "Part II · MiniMe Web (Chapter 4):",
    "text": "Flagship browser workspace with 8 stage tabs, 25-stage orchestrator, 73 agent modules (46 router roles), 6-tier memory, and CAD. In Phase 0 (MK_B02–B06), browser Python Run/Terminal/Local-folder mode are replaced by M2C CLI handoff.",
    "href": "doc-minime-feature-guide.html",
    "btn": "Open Ch. 4: MiniMe Feature Guide →"
  },
  "m2c": {
    "head": "Part III · M2C L26 CLI (Chapters 5–7):",
    "text": "Local-first terminal & editor coding agent (m2c). Runs 14 local tools, SQLite FTS5 code index, git shadow checkpoints, and bubblewrap sandbox on device; calls /api/codeagent/* on the server.",
    "href": "doc-m2c-feature-guide.html",
    "btn": "Open Ch. 5: M2C L26 Feature Guide →"
  },
  "menux": {
    "head": "Part IV · Menux Node (Chapters 8–10):",
    "text": "Local-first personal automation daemon (menux). Runs APScheduler triggers, T0–T5 Approval Manager, Reader/Actor untrusted-input pipeline, 6 messaging channels, 9 connectors, and Argon2id vault on device.",
    "href": "doc-menux-feature-guide.html",
    "btn": "Open Ch. 8: Menux Feature Guide →"
  },
  "minicore": {
    "head": "Shared `minicore/` Library (Work Package P00):",
    "text": "Extracted in M2C Wave 1 and imported by backend/, m2c_cli/, and menux/. Owns wire protocol envelopes, secret/PII redaction, path guards, and cost calculation.",
    "href": "doc-m2c-plan.html#p00-shared-protocol-and-redaction-package-s-wave",
    "btn": "Inspect WP P00 in Ch. 6 →"
  },
  "brain": {
    "head": "Part I · Technical Roadmap (Chapter 2):",
    "text": "Sequences Tech-A (cost/latency telemetry & model roster cleanup) → Tech-B (Basic hardening & shared ledger) → Tech-C/D/E/F/G (Moderate, Brain meta-planner & Monitor v2).",
    "href": "doc-tech-roadmap.html",
    "btn": "Open Ch. 2: Technical Roadmap →"
  },
  "server": {
    "head": "Part I · Server Management Guide (Chapter 3):",
    "text": "Metric-gated splits from Stage 1 ($14/mo single VPS) to Stage 5. Because M2C and Menux execute locally, the server only holds a 2h/24h Redis buffer (<50 MB per 1,000 sessions).",
    "href": "doc-server-guide.html#9-how-m2c-menux-and-fbebc-fit-the-server",
    "btn": "Open Ch. 3: Server Guide §9 →"
  },
  "rulebook": {
    "head": "Part I · Financial & Model Rulebook (Chapter 1):",
    "text": "The constitution. Mandates one shared account, one subscription tier ($0 / $9 / $29 / $79), and one usage_ledger (0012 / S01) across Web, M2C, and Menux with COGS-at-cap ≤ 45%.",
    "href": "doc-rulebook.html",
    "btn": "Open Ch. 1: Rulebook →"
  },
  "fbebc": {
    "head": "Part V · FBEBC Research Track (Chapters 11–14):",
    "text": "Fitness-Band Elitist Bacterial Colony. Stage 1 runs at $0 in standalone fbebc-research (89 tests passing); Stage 2 ports EvolutionEngine into backend/agents/evolution/ after Basic launch.",
    "href": "doc-fbebc-program.html",
    "btn": "Open Ch. 11: FBEBC Program →"
  }
};

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

const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } } };
const readPositions = () => { try { return JSON.parse(store.get(KEY_POS)) || {}; } catch { return {}; } };

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}

const S = { book: null, paths: null, stats: {}, search: null, searchP: null, cards: new Map(), parts: [], q: "", part: "all", positions: {}, anyCard: true };

function ring(prog) {
  const state = progressState(prog), pct = state === "new" ? 0 : prog.pct, d = ringDash(pct);
  const ns = "http://www.w3.org/2000/svg", s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 34 34");
  s.setAttribute("class", `lib-ring${state === "done" ? " lib-ring--done" : ""}`);
  s.setAttribute("role", "img");
  s.setAttribute("aria-label", state === "new" ? "Not started" : state === "done" ? "Finished" : `${pct}% read`);
  const mk = (tag, attrs, text) => { const e = document.createElementNS(ns, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); if (text != null) e.textContent = text; return e; };
  s.append(mk("circle", { class: "lib-ring__bg", cx: 17, cy: 17, r: 14 }),
    mk("circle", { class: "lib-ring__fg", cx: 17, cy: 17, r: 14, "stroke-dasharray": `${d.on} ${d.c}` }));
  s.append(mk("text", { class: "lib-ring__t", x: 17, y: 17 }, state === "done" ? "\u2713" : state === "new" ? "" : String(pct)));
  return s;
}

function buildCard(c) {
  const facts = [];
  if (c.words != null) {
    if (c.minutes) facts.push(h("li", {}, h("b", {}, fmtMinutes(c.minutes)), " read"));
    facts.push(h("li", {}, h("b", {}, fmtN(c.words)), " words"));
    if (c.sections != null) facts.push(h("li", {}, h("b", {}, fmtN(c.sections)), " sections"));
    if (c.tables != null) facts.push(h("li", {}, h("b", {}, fmtN(c.tables)), " tables"));
  } else if (c.meta) {
    facts.push(h("li", {}, c.meta));
  }
  const links = [];
  if (c.md) links.push(h("a", { href: c.md, download: "" }, ".md"));
  if (c.standalone) links.push(h("a", { href: c.standalone, target: "_blank", rel: "noopener" }, "standalone"));
  if (c.journey) links.push(h("a", { href: c.journey }, "journey"));
  const slot = h("span", { class: "lib-card__progress" });
  const go = h("a", { class: "lib-btn", href: c.url }, "Read");
  const card = h("article", { class: "lib-card", "data-chapter": c.id },
    h("div", { class: "lib-card__top" }, h("span", { class: "lib-card__n" }, c.label),
      c.built ? h("span", { class: "lib-card__built", title: c.commit ? `Built from commit ${c.commit}` : null }, `Built ${fmtDate(c.built)}`) : null),
    h("h3", { class: "lib-card__title" }, h("a", { href: c.url }, c.title)),
    h("p", { class: "lib-card__desc" }, c.desc || c.blurb),
    facts.length ? h("ul", { class: "lib-facts" }, facts) : null,
    h("div", { class: "lib-card__foot" }, slot, go, links.length ? h("div", { class: "lib-card__links" }, links) : null));
  S.cards.set(c.id, { card, slot, go, chapter: c });
  return card;
}

/* Progress rings, Continue buttons and the resume strip: called again whenever another tab or the back button changes the saved positions. */
function paintProgress() {
  S.positions = readPositions();
  for (const { slot, go, chapter } of S.cards.values()) {
    const prog = readProgress(S.positions, chapter.id), state = progressState(prog);
    slot.replaceChildren(ring(prog));
    go.textContent = state === "reading" ? "Continue" : state === "done" ? "Read again" : "Read";
    go.className = `lib-btn${state === "reading" ? " lib-btn--primary" : ""}`;
    go.href = continueHref(chapter, prog);
  }
  const box = document.getElementById("lib-resume");
  if (!box) return;
  const last = mostRecent(S.book.chapters, S.positions);
  box.hidden = !last;
  if (!last) return;
  box.replaceChildren(
    h("div", { class: "lib-resume__t" }, h("b", {}, `${last.chapter.label} \u00b7 ${last.chapter.title}`), `You were ${last.prog.pct}% through this chapter.`),
    h("a", { class: "lib-btn lib-btn--primary", href: continueHref(last.chapter, last.prog) }, "Continue reading"));
}

function renderTotals() {
  const t = S.book.totals, box = document.getElementById("lib-totals");
  const item = (n, l) => h("div", { class: "lib-totals__i" }, h("span", { class: "lib-totals__n" }, n), h("span", { class: "lib-totals__l" }, l));
  const parts = [item(String(t.chapters), "chapters"), t.appendices ? item(String(t.appendices), t.appendices === 1 ? "appendix" : "appendices") : null,
    item(fmtN(t.words), "words"), t.minutes ? item(fmtMinutes(t.minutes), "to read it all") : null, item(fmtN(t.sections), "sections"), item(fmtN(t.tables), "tables")];
  box.replaceChildren(...parts.filter(Boolean), h("p", { class: "lib-totals__src" },
    `Counted from the chapter banners${t.withCounts < t.chapters + t.appendices ? "; the interactive design specs have no counts" : ""}.`));
}

function renderParts() {
  const root = document.getElementById("lib-parts"), chips = document.getElementById("lib-chips");
  const byId = new Map(S.book.chapters.map((c) => [c.id, c]));
  root.replaceChildren();
  S.parts = [];
  for (const p of S.book.parts) {
    const grid = h("div", { class: "lib-grid" }, p.chapters.map((id) => buildCard(byId.get(id))));
    const sec = h("section", { class: "lib-part", "data-part": p.id },
      h("div", { class: "lib-part__h" }, h("h2", {}, p.title), h("span", {}, `${p.chapters.length} ${p.chapters.length === 1 ? "chapter" : "chapters"}`)), grid);
    S.parts.push({ id: p.id, sec, ids: p.chapters });
    root.append(sec);
  }
  const mk = (id, text) => h("button", { class: "lib-chip", type: "button", "aria-pressed": String(id === S.part), "data-part": id, onclick: () => { S.part = id; apply(); } }, text);
  chips.replaceChildren(mk("all", "All"), ...S.book.parts.map((p) => mk(p.id, p.title)));
}

/* Search box and part chips decide which cards are visible. */
function apply() {
  const show = new Set(filterChapters(S.book.chapters, S.q).map((c) => c.id));
  let any = false;
  for (const p of S.parts) {
    let n = 0;
    for (const id of p.ids) {
      const on = show.has(id) && (S.part === "all" || S.part === p.id);
      S.cards.get(id).card.hidden = !on;
      if (on) n++;
    }
    p.sec.hidden = n === 0;
    any = any || n > 0;
  }
  document.querySelectorAll("#lib-chips .lib-chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.part === S.part)));
  S.anyCard = any;
  document.getElementById("lib-none").hidden = any;
  showHits();
}

function loadSearch() {
  if (!S.searchP) S.searchP = getJSON("data/index/search.json").then((d) => (S.search = d)).catch((err) => { console.warn("[atlas library]", err); S.search = { headings: [] }; return S.search; });
  return S.searchP;
}

async function showHits() {
  const box = document.getElementById("lib-hits");
  if (tokens(S.q).join("").length < 2) { box.hidden = true; box.replaceChildren(); return; }
  const wanted = S.q;
  const data = await loadSearch();
  if (wanted !== S.q) return;                                           // typed on meanwhile
  const { rows, total } = matchHeadings(data.headings, S.q);
  box.hidden = false;
  if (rows.length) document.getElementById("lib-none").hidden = true;      // no chapter title matches, but sections do: say nothing is missing
  if (!rows.length) { box.replaceChildren(h("li", { class: "lib-hits__more" }, "No section headings match.")); return; }
  const label = new Map(S.book.chapters.map((c) => [c.url, c.label]));
  box.replaceChildren(...rows.map((r) => h("li", {}, h("a", { href: r.url },
    h("span", { class: "lib-hits__ch" }, label.get(r.chapter) || ""), h("span", { class: "lib-hits__t" }, r.title), h("span", { class: "lib-hits__in" }, r.chapterTitle)))),
    total > rows.length ? h("li", { class: "lib-hits__more" }, `${total - rows.length} more. Narrow the search, or press Ctrl+K and type # to search every heading.`) : null);
}

async function renderPaths() {
  const root = document.getElementById("lib-paths");
  let doc;
  try { doc = await getJSON("content/reading-paths.json"); } catch (err) { root.replaceChildren(h("p", { class: "lib__empty" }, "Reading paths could not be loaded.")); console.warn("[atlas library]", err); return; }
  const search = await loadSearch();
  const titles = {};
  for (const x of search.headings || []) titles[x.url] = x.title;
  root.replaceChildren(...(doc.paths || []).map((p) => {
    const items = (p.steps || []).map((st) => {
      const i = stepInfo(st, S.book.chapters, titles, S.stats.commit);
      if (!i) return null;
      return h("li", {}, h("span", { class: `lib-path__k${i.kind === "code" ? " lib-path__k--code" : ""}` }, i.kind === "code" ? "</>" : i.kind),
        h("a", i.external ? { href: i.url, target: "_blank", rel: "noopener" } : { href: i.url }, i.text), i.note ? h("span", { class: "lib-path__note" }, i.note) : null);
    });
    return h("article", { class: "lib-path" }, h("h3", {}, p.title), p.blurb ? h("p", {}, p.blurb) : null, h("ol", {}, items));
  }));
}

function initMap() {
  const txt = document.getElementById("sync-txt"), btn = document.getElementById("sync-btn");
  if (!txt || !btn) return;
  document.querySelectorAll(".bk-node-box").forEach((g) => {
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    const pick = () => {
      const d = MAP_INFO[g.dataset.node];
      if (!d) return;
      txt.replaceChildren(h("b", {}, d.head), " ", d.text);
      btn.href = d.href;
      btn.textContent = d.btn;
    };
    g.addEventListener("click", pick);
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  });
}

async function boot() {
  const err = (msg) => { document.getElementById("lib-parts").replaceChildren(h("p", { class: "lib__empty lib__err" }, msg)); };
  try {
    [S.book, S.stats] = await Promise.all([getJSON("data/index/book.json"), getJSON("data/index/stats.json").catch(() => ({}))]);
  } catch (e) {
    err("The library could not be loaded. If you opened this file directly, start the local server: python scripts/serve.py");
    console.warn("[atlas library]", e);
    return;
  }
  renderTotals();
  renderParts();
  paintProgress();
  initMap();
  const q = document.getElementById("lib-q");
  let timer = 0;
  q.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { S.q = q.value.trim(); apply(); }, 120); });
  q.addEventListener("keydown", (e) => { if (e.key === "Escape" && q.value) { q.value = ""; S.q = ""; apply(); } });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || e.defaultPrevented) return;
    const t = e.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    e.preventDefault();
    q.focus();
  });
  window.addEventListener("pageshow", paintProgress);                   // back button: the reader may have moved on
  window.addEventListener("storage", (e) => { if (e.key === KEY_POS) paintProgress(); });
  renderPaths();
}

if (typeof document !== "undefined" && document.getElementById("lib-parts")) {   // overview.js (P07) imports this file for its helpers: only the library page boots it
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
}
