/* MiniMe Atlas 2 - chapter reader layer (P04). One ES module, no dependencies.

   Turns the 15 untouched chapter pages (doc-*.html) into a typeset monograph AT RUN TIME. The chapter bodies are
   produced by an external builder and would be overwritten, so nothing here is written back to the HTML files:
   this module only adds classes, attributes and a few helper elements to the live DOM.

   Loaded on demand by shell.js on every page that has a chapter banner or a `.doc article` (see loadReader() there).
   It fetches assets/css/reader.css itself, then switches on `html[data-reader]`; every rule in that stylesheet is
   scoped under that attribute, so nothing changes until this module has run.

   What it does (switches live in content/reader.json; reader choices are saved in localStorage):
     typography   serif / sans and 5 text sizes (the "Aa" popover), justified + hyphenated paragraphs on desktop
     On this page the existing `.toc` element is rebuilt from the article's h1-h3: collapsible groups, scroll-spy,
                  `]` toggles it (side rail >= 1200px, bottom sheet below that, opened by the top bar's Contents button)
     chapter bar  a slim sticky bar once the banner has scrolled away: chapter, current section, % read, prev / next, Aa
     progress     a 3px bar on the top edge; the reading position of each chapter is remembered (offer to resume)
     callouts     "Purpose:", "Status basis:", "Rule:" ... paragraphs become typed callouts (patterns in reader.json)
     numbering    opt-in per chapter; refused when the headings already start with numbers (the rulebook's do)
     tables       horizontal scroll + sticky header in a capped box, a filter box above tables with > 25 rows
     glossary     (P05) the first use of each glossary term in a section gets a dotted underline and a tooltip
                  (content/glossary.json; hover, focus or tap; Esc closes; never inside headings, code or links)
     small things stable ids for headings that have none (existing ids are never changed), copy-link on headings,
                  copy button on <pre>, print rules (in reader.css)

   Events it listens to:   minime:toc-toggle  (fired by shell.js on "]")
   Pure helpers are exported so scripts/test_reader.py can run them in Node with no browser. */

const KEY_PREFS = "minime_reader";       // { font: "serif" | "sans", size: 0..4 }
const KEY_POS = "minime_reader_pos";     // { [chapter id]: { id, off, pct, t } }, newest 40 kept
const KEY_TOC = "minime_toc";            // "open" | "closed": the desktop side rail
const MAX_POSITIONS = 40;
const GLOSSARY_PAGE = "glossary.html";
const WIDE = "(min-width: 1200px)";      // same breakpoint as reader.css: side rail at or above, bottom sheet below
const BASE = new URL("../../", import.meta.url);

/* ================================================================== pure helpers (no DOM) */

export const FALLBACK_CONFIG = {
  version: 1,
  defaults: { numbered: false, tableFilterMinRows: 25, tableMaxHeightVh: 75, glossary: true },
  typography: { sizes: [0.96, 1.02, 1.08, 1.16, 1.26], defaultSize: 2, defaultFont: "serif" },
  callouts: [],
  chapters: {},
};

/* Fills whatever reader.json leaves out, so a half-written file never breaks the page. */
export function mergeConfig(raw) {
  const r = raw && typeof raw === "object" ? raw : {};
  const t = { ...FALLBACK_CONFIG.typography, ...(r.typography || {}) };
  if (!Array.isArray(t.sizes) || !t.sizes.length || !t.sizes.every((n) => Number.isFinite(n) && n > 0.5 && n < 3)) t.sizes = FALLBACK_CONFIG.typography.sizes;
  t.defaultSize = Math.min(Math.max(Number.isInteger(t.defaultSize) ? t.defaultSize : 2, 0), t.sizes.length - 1);
  if (t.defaultFont !== "serif" && t.defaultFont !== "sans") t.defaultFont = "serif";
  return {
    version: 1,
    defaults: { ...FALLBACK_CONFIG.defaults, ...(r.defaults || {}) },
    typography: t,
    callouts: Array.isArray(r.callouts) ? r.callouts : [],
    chapters: r.chapters && typeof r.chapters === "object" ? r.chapters : {},
  };
}

/* The settings that apply to one chapter: defaults, then that chapter's overrides. */
export function chapterConfig(cfg, id) {
  const own = cfg.chapters && Object.prototype.hasOwnProperty.call(cfg.chapters, id) ? cfg.chapters[id] : {};
  return { ...cfg.defaults, ...(own && typeof own === "object" ? own : {}) };
}

/* Stable heading id. Same recipe as the chapter builder (lower case, runs of other characters -> one hyphen,
   cut at 40), so an id made here for a future chapter looks like the ones already in the others. */
export function slugify(text, max = 40) {
  const s = String(text).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return s.slice(0, max).replace(/-+$/g, "") || "section";
}

/* `taken` is a Set of every id already on the page; the chosen id is added to it. */
export function uniqueId(base, taken) {
  let id = base;
  for (let n = 2; taken.has(id); n++) id = `${base}-${n}`;
  taken.add(id);
  return id;
}

/* True when a heading already carries its own number: "4. Chat", "2.1 Sign in", "0.5 Situation index", "A.1 Scope". */
export function startsNumbered(text) {
  return /^\s*(?:[A-Z]\.?)?\d+(?:\.\d+)*[.):]?(?:\s|$)/.test(String(text));
}

/* heads: [{ id, text, level }] in document order, levels 1..3.
   Returns { items, tree }: items is the flat list with an effective `depth` (0, 1, 2), tree nests depth >= 1 under the
   nearest depth-0 heading. Rules:
     - a lone h1 that comes first is the document title and is left out (the rulebook has 29 h1s: those stay);
     - the shallowest level present is depth 0, the next one depth 1, the next depth 2;
     - a deeper heading with no depth-0 heading before it becomes top level itself (the feature guide opens with an h3). */
export function planToc(heads) {
  let list = heads.filter((h) => h.level >= 1 && h.level <= 3 && h.text);
  if (list.filter((h) => h.level === 1).length === 1 && list.length && list[0].level === 1) list = list.slice(1);
  const levels = [...new Set(list.map((h) => h.level))].sort((a, b) => a - b);
  const items = [], tree = [];
  let group = null;
  for (const h of list) {
    let depth = levels.indexOf(h.level);
    const orphan = depth > 0 && !group;
    if (orphan) depth = 0;
    const node = { id: h.id, text: h.text, level: h.level, depth, children: [] };
    items.push(node);
    if (depth === 0) { tree.push(node); group = orphan ? null : node; }
    else group.children.push(node);
  }
  return { items, tree };
}

/* Section labels "§ 3", "§ 3.2" for the items of planToc(); a Map id -> label. */
export function planNumbers(items) {
  const c = [0, 0, 0], out = new Map();
  for (const it of items) {
    const d = Math.min(it.depth, 2);
    c[d] += 1;
    for (let i = d + 1; i < 3; i++) c[i] = 0;
    out.set(it.id, `\u00a7\u00a0${c.slice(0, d + 1).join(".")}`);
  }
  return out;
}

/* Numbering is refused (never forced) when any heading already starts with a number. */
export function canNumber(items) {
  return items.length > 0 && !items.some((it) => startsNumbered(it.text));
}

/* Compiles the callout rules once. A rule whose pattern is not a valid regular expression is skipped, not fatal. */
export function compileCallouts(rules) {
  const out = [];
  for (const r of Array.isArray(rules) ? rules : []) {
    if (!r || typeof r.pattern !== "string" || typeof r.type !== "string") continue;
    try { out.push({ ...r, re: new RegExp(r.pattern, "i") }); } catch { /* skip the bad rule */ }
  }
  return out;
}

/* The first rule that matches the start of a paragraph's text, or null. Only the first 120 characters are looked at. */
export function classifyCallout(text, compiled) {
  const t = String(text).replace(/\s+/g, " ").trim().slice(0, 120);
  if (!t) return null;
  for (const r of compiled) if (r.re.test(t)) return r;
  return null;
}

/* Does a table row's text contain every word of the query? (case-insensitive, any order) */
export function matchesAll(rowText, query) {
  const q = String(query).toLowerCase().split(/\s+/).filter(Boolean);
  if (!q.length) return true;
  const t = String(rowText).toLowerCase();
  return q.every((w) => t.includes(w));
}

/* Previous / next chapter in nav.json order (items that carry a `chapter`), or null for a page that is not one. */
export function neighbours(nav, id) {
  const items = [];
  for (const w of (nav && nav.wings) || []) for (const it of w.items || []) if (it.chapter != null) items.push(it);
  const i = items.findIndex((x) => x.id === id);
  if (i < 0) return null;
  return { prev: items[i - 1] || null, next: items[i + 1] || null, item: items[i] };
}

/* "Chapter 4 of 14" -> "Ch. 4 of 14"; "Appendix A" -> "App. A". */
export function chipText(raw) {
  return String(raw || "").replace(/\s+/g, " ").trim().replace(/^Chapter\b/i, "Ch.").replace(/^Appendix\b/i, "App.");
}

/* "8,064 words (~37 min read)" -> 37, or null. */
export function readMinutes(text) {
  const m = /(\d[\d,]*)\s*min(?:ute)?s?\s+read/i.exec(String(text || ""));
  return m ? Number(m[1].replace(/,/g, "")) : null;
}

/* Saved reading preferences, clamped to what the config allows. */
export function normalizePrefs(raw, cfg) {
  const t = cfg.typography, r = raw && typeof raw === "object" ? raw : {};
  const font = r.font === "serif" || r.font === "sans" ? r.font : t.defaultFont;
  const size = Number.isInteger(r.size) ? Math.min(Math.max(r.size, 0), t.sizes.length - 1) : t.defaultSize;
  return { font, size };
}

/* Offer to resume only for a chapter the reader was really part-way through, and never over a link with a #hash. */
export function shouldOfferResume(saved, hasHash) {
  return !!saved && !hasHash && typeof saved.id === "string" && Number.isFinite(saved.pct) && saved.pct >= 3 && saved.pct <= 96;
}

/* Keeps only the newest `max` chapters. */
export function prunePositions(map, max = MAX_POSITIONS) {
  const keep = Object.entries(map || {}).filter(([, v]) => v && typeof v === "object").sort((a, b) => (b[1].t || 0) - (a[1].t || 0)).slice(0, max);
  return Object.fromEntries(keep);
}


/* ------------------------------------------------------------------ glossary (P05) */

const escapeRe = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+");

/* content/glossary.json -> the terms that may get a tooltip. A term with match "off" is for the glossary page only (common words such as
   "stage" or "wave" would underline half the book). Same shape check as glossary.js. */
export function normalizeGlossary(raw) {
  const list = Array.isArray(raw) ? raw : raw && Array.isArray(raw.terms) ? raw.terms : [];
  const out = [];
  for (const t of list) {
    if (!t || typeof t.term !== "string" || !t.term.trim() || typeof t.short !== "string" || !t.short.trim()) continue;
    const match = t.match === "cs" || t.match === "off" ? t.match : "ci";
    if (match === "off") continue;
    out.push({
      id: t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "root",
      term: t.term.trim(), category: t.category || "", short: t.short.trim(), match,
      labels: [t.term, ...(Array.isArray(t.aliases) ? t.aliases : [])].filter((a) => typeof a === "string" && a.trim()).map((a) => a.trim()),
    });
  }
  return out;
}

/* One regex per match mode (any case / exact case). A label matches as a whole word (letters, digits, "_" and "-" around it do not
   count as a boundary) and may carry a plural "s". Longest label first, so "Golden Rules" wins over "Rules". */
export function compileTerms(terms) {
  const groups = { ci: [], cs: [] };
  for (const t of terms) for (const label of t.labels) groups[t.match === "cs" ? "cs" : "ci"].push({ label, term: t });
  const build = (items, flags) => {
    if (!items.length) return null;
    items.sort((a, b) => b.label.length - a.label.length);
    const alt = items.map((i) => `(${escapeRe(i.label)}${/[A-Za-z]$/.test(i.label) ? "s?" : ""})`).join("|");
    return { re: new RegExp(`(?<![\\p{L}\\p{N}_-])(?:${alt})(?![\\p{L}\\p{N}_-])`, flags), items };
  };
  return [build(groups.ci, "giu"), build(groups.cs, "gu")].filter(Boolean);
}

/* [{ start, end, term }] for every term in `text`, left to right, no overlaps (earlier start wins, then the longer match). */
export function findTermHits(text, compiled) {
  const hits = [];
  for (const { re, items } of compiled) {
    re.lastIndex = 0;
    for (const m of text.matchAll(re)) {
      const g = m.findIndex((x, i) => i > 0 && x !== undefined) - 1;
      if (g >= 0) hits.push({ start: m.index, end: m.index + m[0].length, term: items[g].term });
    }
  }
  hits.sort((a, b) => a.start - b.start || b.end - a.end);
  const out = [];
  for (const x of hits) if (!out.length || x.start >= out[out.length - 1].end) out.push(x);
  return out;
}

/* "First occurrence per section": take(section, id) is true the first time a term is seen in a section. */
export function sectionTracker() {
  const seen = new Map();
  return { take(section, id) { let set = seen.get(section); if (!set) seen.set(section, (set = new Set())); if (set.has(id)) return false; set.add(id); return true; } };
}

/* ================================================================== DOM layer */

const root = typeof document !== "undefined" ? document.documentElement : null;

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode: the choice just is not remembered */ } },
};
const readJSON = (k) => { try { return JSON.parse(store.get(k)); } catch { return null; } };

function h(tag, props = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "html") n.innerHTML = v;                          // static icon markup from ICON only
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}
const svg = (d, s = 16) => `<svg viewBox="0 0 24 24" width="${s}" height="${s}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${d}</svg>`;
const ICON = {
  link: svg('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>', 15),
  chev: svg('<path d="M9 6l6 6-6 6"/>', 14),
  prev: svg('<path d="M15 6l-6 6 6 6"/>', 16),
  next: svg('<path d="M9 6l6 6-6 6"/>', 16),
  collapse: svg('<path d="M7 9l5-5 5 5M7 15l5 5 5-5"/>', 15),
  expand: svg('<path d="M7 4l5 5 5-5M7 20l5-5 5 5"/>', 15),
};

const R = {
  started: false, cfg: null, cc: null, prefs: null, chapter: "", main: null, article: null, doc: null, banner: null,
  heads: [], spy: [], plan: null, labels: null, tocEl: null, tocLinks: new Map(), activeLink: null, autoGroup: null,
  active: -1, raf: 0, saveT: 0, hold: false, bar: null, barOn: false, aa: null, progress: null, toasts: null,
  tip: null, tipFor: null, tipTimer: 0, tipAt: 0,
};

function safe(name, fn) {
  try { return fn(); } catch (err) { console.warn(`[atlas reader] ${name} failed:`, err); return null; }
}
const wide = () => window.matchMedia(WIDE).matches;
const clamp01 = (n) => Math.min(1, Math.max(0, n));
const cssPx = (name, fallback) => {
  const v = parseFloat(getComputedStyle(root).getPropertyValue(name));
  return Number.isFinite(v) ? v : fallback;
};
const topbarH = () => { const t = document.querySelector(".mm-top"); return t ? t.getBoundingClientRect().bottom : 52; };
/* Headings count as "reached" once they cross this line (just under the top bar and the chapter bar). */
const readingLine = () => topbarH() + cssPx("--rd-bar-h", 38) + 24;
const instant = (fn) => { root.style.scrollBehavior = "auto"; try { fn(); } finally { root.style.scrollBehavior = ""; } };   // the old page CSS sets smooth scrolling

/* ------------------------------------------------------------------ boot */
function loadConfig() {
  return fetch(new URL("content/reader.json", BASE)).then((r) => { if (!r.ok) throw new Error(`reader.json: ${r.status}`); return r.json(); })
    .then(mergeConfig).catch((err) => { console.warn("[atlas reader] using built-in defaults:", err); return mergeConfig(null); });
}
function loadCss() {
  return new Promise((resolve) => {
    const href = new URL("assets/css/reader.css", BASE).href;
    if ([...document.styleSheets].some((s) => s.href === href)) { resolve(); return; }
    const link = h("link", { rel: "stylesheet", href });
    link.addEventListener("load", resolve, { once: true });
    link.addEventListener("error", resolve, { once: true });          // unstyled but working beats waiting forever
    setTimeout(resolve, 2000);
    document.head.append(link);
  });
}
/* The serif face is applied only once it is downloaded (or 600 ms have passed): one visible change, not two. */
function fontsReady() {
  if (!document.fonts || !document.fonts.load) return Promise.resolve();
  return Promise.race([document.fonts.load('400 1em "STIX Two Text"').catch(() => null), new Promise((r) => setTimeout(r, 600))]);
}

export async function initReader(opts = {}) {
  if (!root || R.started) return;
  const main = document.querySelector("main");
  if (!main || !main.querySelector(".bk-banner, .doc article")) return;
  R.started = true;
  R.main = main;
  R.chapter = document.body.dataset.page || (location.pathname.split("/").pop() || "").replace(/\.html$/, "");
  const [cfg] = await Promise.all([loadConfig(), loadCss()]);
  R.cfg = cfg;
  R.cc = chapterConfig(cfg, R.chapter);
  R.prefs = normalizePrefs(readJSON(KEY_PREFS), cfg);
  if (R.prefs.font === "serif") await fontsReady();

  R.article = main.querySelector(".doc article");
  R.doc = main.querySelector(".doc");
  R.banner = main.querySelector(".bk-banner");

  // One synchronous block: the browser does not paint between these steps, so the page changes once.
  main.classList.add("rd-main", R.article ? "rd-main--doc" : "rd-main--embed");
  if (R.article) {
    safe("headings", collectHeadings);
    safe("numbering", applyNumbering);
    safe("callouts", applyCallouts);
    safe("tables", enhanceTables);
    safe("code", enhanceCode);
    safe("anchors", addAnchors);
    safe("toc", buildToc);
    if (R.cc.glossary !== false) safe("glossary", startGlossary);
  }
  safe("banner", tuneBanner);
  safe("bar", buildBar);
  safe("progress", buildProgress);
  applyPrefs();
  if (wide() && store.get(KEY_TOC) === "closed") root.dataset.toc = "closed";
  safe("events", bindEvents);
  safe("realign", realignHash);
  update();

  if (opts.navReady && typeof opts.navReady.then === "function") opts.navReady.then((info) => safe("nav", () => applyNav(info)), () => {});
  safe("resume", offerResume);
}

/* ------------------------------------------------------------------ preferences */
function applyPrefs() {
  const sizes = R.cfg.typography.sizes;
  root.style.setProperty("--rd-fs", `${sizes[R.prefs.size]}rem`);
  root.dataset.readerFont = R.prefs.font;
  root.dataset.reader = "1";
  if (R.aa) syncAa();
}
function setPrefs(patch) {
  const next = normalizePrefs({ ...R.prefs, ...patch }, R.cfg);
  if (next.font === R.prefs.font && next.size === R.prefs.size) return;
  keepPosition(() => { R.prefs = next; applyPrefs(); });
  store.set(KEY_PREFS, JSON.stringify(R.prefs));
}
/* Changing the text size re-flows the page; this keeps the section you are reading where it was on screen. */
function keepPosition(change) {
  const i = activeIndex(), el = i >= 0 ? R.spy[i].el : null;
  const before = el ? el.getBoundingClientRect().top : 0;
  change();
  if (el) instant(() => window.scrollBy(0, el.getBoundingClientRect().top - before));
}

/* ------------------------------------------------------------------ headings, numbering, anchors */
function collectHeadings() {
  const taken = new Set(Array.from(document.querySelectorAll("[id]"), (n) => n.id));
  for (const el of R.article.querySelectorAll("h1, h2, h3, h4")) {
    if (el.closest(".bk-footer")) continue;
    const text = el.textContent.replace(/\s+/g, " ").trim();
    if (!text) continue;
    if (!el.id) el.id = uniqueId(slugify(text), taken);                 // existing ids are never touched
    if (el.tagName !== "H4") R.heads.push({ el, id: el.id, level: Number(el.tagName[1]), text });
  }
  R.plan = planToc(R.heads);
  const inToc = new Set(R.plan.items.map((i) => i.id));
  R.spy = R.heads.filter((x) => inToc.has(x.id));
}

function applyNumbering() {
  if (!R.cc.numbered || !R.plan) return;
  if (!canNumber(R.plan.items)) { console.info(`[atlas reader] ${R.chapter}: numbering skipped, its headings already start with numbers`); return; }
  R.labels = planNumbers(R.plan.items);
  const byId = new Map(R.heads.map((x) => [x.id, x.el]));
  for (const [id, label] of R.labels) byId.get(id).setAttribute("data-rd-num", label);
}

function addAnchors() {
  for (const el of R.article.querySelectorAll("h1[id], h2[id], h3[id], h4[id]")) {
    if (el.closest(".bk-footer") || el.querySelector(".rd-anchor")) continue;
    const label = el.textContent.replace(/\s+/g, " ").trim();
    el.append(h("a", { class: "rd-anchor", href: `#${el.id}`, "aria-label": `Copy link to section: ${label}`, html: ICON.link }));
  }
  R.article.addEventListener("click", (e) => {
    const a = e.target.closest(".rd-anchor");
    if (!a) return;
    copyText(`${location.origin}${location.pathname}${a.getAttribute("href")}`).then((ok) => toast(ok ? "Link copied" : "Could not copy the link"));
  });
}

/* ------------------------------------------------------------------ callouts */
function applyCallouts() {
  const rules = compileCallouts(R.cfg.callouts);
  if (!rules.length) return;
  for (const p of R.article.querySelectorAll(":scope > p")) {
    const rule = classifyCallout(p.textContent, rules);
    if (!rule) continue;
    p.classList.add("mm-callout", `mm-callout--${rule.type}`, "rd-callout");   // the P01 component, applied in place
    if (rule.muted) p.classList.add("rd-callout--muted");
    p.setAttribute("role", "note");
    p.prepend(h("span", { class: "mm-callout__title" }, rule.label, rule.href ? h("a", { class: "rd-callout__ref", href: rule.href }, rule.hrefLabel || rule.href) : null));
  }
}

/* ------------------------------------------------------------------ glossary tooltips */
const TERM_SKIP_TAGS = new Set(["PRE", "CODE", "A", "BUTTON", "KBD", "SAMP", "SCRIPT", "STYLE", "TEXTAREA", "INPUT", "SELECT", "SVG", "SUMMARY", "TIME"]);
const TERM_SKIP_CLASS = /(?:^|\s)(?:mm-callout__title|rd-term|rd-anchor|rd-copy|rd-filter|rd-tip)(?:\s|$)/;

function startGlossary() {
  const idle = window.requestIdleCallback || ((f) => setTimeout(f, 300));
  idle(() => {
    fetch(new URL("content/glossary.json", BASE)).then((r) => { if (!r.ok) throw new Error(`glossary.json: ${r.status}`); return r.json(); })
      .then((raw) => safe("glossary", () => markTerms(normalizeGlossary(raw))))
      .catch((err) => console.warn("[atlas reader] no glossary tooltips:", err));
  });
}

/* Walks the article's text (not headings, code, links or buttons) and wraps the first use of each term per section. Section = the text
   between two headings (h1 to h3). Runs in small slices so a 260 KB chapter never blocks scrolling. */
function markTerms(terms) {
  if (!terms.length || !R.article) return;
  const compiled = compileTerms(terms);
  if (!compiled.length) return;
  const nodes = [];
  let section = 0;
  const walker = document.createTreeWalker(R.article, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (n.nodeType === 3) return n.nodeValue.trim().length > 2 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      if (/^H[1-3]$/.test(n.tagName)) { section++; return NodeFilter.FILTER_REJECT; }
      if (/^H[4-6]$/.test(n.tagName) || TERM_SKIP_TAGS.has(n.tagName.toUpperCase()) || TERM_SKIP_CLASS.test(n.className || "")) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_SKIP;
    },
  });
  for (let n = walker.nextNode(); n; n = walker.nextNode()) nodes.push({ node: n, section });
  const tracker = sectionTracker();
  let i = 0, used = 0;
  const slice = () => {
    const stop = Math.min(nodes.length, i + 120);
    for (; i < stop; i++) {
      const { node, section: sec } = nodes[i];
      if (!node.isConnected) continue;
      const text = node.nodeValue;
      const hits = findTermHits(text, compiled).filter((x) => tracker.take(sec, x.term.id));
      if (!hits.length) continue;
      const frag = document.createDocumentFragment();
      let at = 0;
      for (const x of hits) {
        if (x.start > at) frag.append(text.slice(at, x.start));
        frag.append(h("span", { class: "rd-term", tabindex: "0", role: "button", "data-term": x.term.id }, text.slice(x.start, x.end)));
        at = x.end;
        used++;
      }
      if (at < text.length) frag.append(text.slice(at));
      node.replaceWith(frag);
    }
    if (i < nodes.length) setTimeout(slice, 16);
    else if (used) bindTips(new Map(terms.map((t) => [t.id, t])));
  };
  slice();
}

function bindTips(byId) {
  const tip = h("div", { class: "rd-tip", role: "tooltip", id: "rd-tip", hidden: "" });
  document.body.append(tip);
  R.tip = tip;
  const termOf = (e) => (e.target && e.target.closest ? e.target.closest(".rd-term") : null);
  const close = (restore = false) => {
    clearTimeout(R.tipTimer);
    if (!R.tipFor) return;
    const t = R.tipFor;
    t.removeAttribute("aria-describedby");
    t.setAttribute("aria-expanded", "false");
    tip.hidden = true;
    R.tipFor = null;
    if (restore && tip.contains(document.activeElement)) t.focus({ preventScroll: true });
  };
  const open = (t) => {
    const def = byId.get(t.dataset.term);
    if (!def) return;
    if (R.tipFor && R.tipFor !== t) close();
    R.tipFor = t;
    R.tipAt = Date.now();
    tip.replaceChildren(
      h("div", { class: "rd-tip__t" }, h("b", {}, def.term), def.category ? h("span", { class: "rd-tip__c" }, def.category) : null),
      h("p", { class: "rd-tip__s" }, def.short),
      h("a", { class: "rd-tip__m", href: `${GLOSSARY_PAGE}#${def.id}` }, "Full definition \u2192"));
    t.setAttribute("aria-describedby", "rd-tip");
    t.setAttribute("aria-expanded", "true");
    tip.hidden = false;
    const r = t.getClientRects()[0] || t.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight, m = 8;
    const left = Math.min(Math.max(m, r.left), Math.max(m, window.innerWidth - tw - m));
    const below = r.bottom + 6, top = below + th + m > window.innerHeight && r.top - th - 6 > m ? r.top - th - 6 : below;
    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
  };
  const later = (fn, ms) => { clearTimeout(R.tipTimer); R.tipTimer = setTimeout(fn, ms); };

  R.article.addEventListener("pointerover", (e) => { const t = termOf(e); if (t && e.pointerType === "mouse") later(() => open(t), 140); });
  R.article.addEventListener("pointerout", (e) => { if (termOf(e) && e.pointerType === "mouse") later(close, 220); });
  tip.addEventListener("pointerenter", () => clearTimeout(R.tipTimer));
  tip.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") later(close, 220); });
  R.article.addEventListener("focusin", (e) => { const t = termOf(e); if (t) open(t); });
  R.article.addEventListener("focusout", (e) => { if (termOf(e) && !(e.relatedTarget && tip.contains(e.relatedTarget))) close(); });
  tip.addEventListener("focusout", (e) => { if (!(e.relatedTarget && (tip.contains(e.relatedTarget) || (R.tipFor && R.tipFor.contains(e.relatedTarget))))) close(); });
  // With a mouse, hover and focus already opened it, so a click keeps it open; on a touch screen a second tap closes it.
  R.article.addEventListener("click", (e) => { const t = termOf(e); if (!t) return; if (R.tipFor === t && !tip.hidden && window.matchMedia("(hover: none)").matches) close(); else open(t); });
  R.article.addEventListener("keydown", (e) => {
    const t = termOf(e);
    if (t && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); if (R.tipFor === t && !tip.hidden) close(); else open(t); }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && R.tipFor) { close(true); e.stopPropagation(); } }, true);
  document.addEventListener("click", (e) => { if (R.tipFor && !e.target.closest(".rd-term, .rd-tip")) close(); });
  window.addEventListener("scroll", () => { if (R.tipFor && Date.now() - R.tipAt > 250) close(); }, { passive: true });   // focusing a term can scroll it into view
  window.addEventListener("resize", () => close(), { passive: true });
}

/* ------------------------------------------------------------------ tables and code */
function enhanceTables() {
  const min = Number(R.cc.tableFilterMinRows) || 25;
  const maxVh = Number(R.cc.tableMaxHeightVh) || 75;
  R.article.style.setProperty("--rd-table-max", `${maxVh}vh`);
  for (const table of R.article.querySelectorAll("table")) {
    let wrap = table.parentElement;
    if (!wrap.classList.contains("tw")) { wrap = h("div", { class: "tw" }); table.before(wrap); wrap.append(table); }
    wrap.classList.add("rd-tablewrap");
    const rows = Array.from(table.querySelectorAll("tbody tr"));
    const n = rows.length || Math.max(0, table.rows.length - 1);
    wrap.style.setProperty("--rd-rows", String(Math.min(n + 1, 30)));
    const cols = table.rows[0] ? table.rows[0].cells.length : 0;
    if (n > 12 || cols > 5) { wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", `Table, ${n} rows`); }   // a scroll box must be reachable by keyboard
    if (n > min) addFilter(wrap, rows);
  }
}
function addFilter(wrap, rows) {
  const texts = rows.map((r) => r.textContent);
  const q = h("input", { type: "search", class: "mm-input rd-tbar__q", placeholder: `Filter ${rows.length} rows`, "aria-label": `Filter this table, ${rows.length} rows`, autocomplete: "off" });
  const n = h("span", { class: "rd-tbar__n", role: "status" }, `${rows.length} rows`);
  let t = 0;
  const run = () => {
    let shown = 0;
    rows.forEach((r, i) => { const ok = matchesAll(texts[i], q.value); r.hidden = !ok; if (ok) shown += 1; });
    n.textContent = q.value.trim() ? `${shown} of ${rows.length} rows` : `${rows.length} rows`;
  };
  q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(run, 80); });
  q.addEventListener("keydown", (e) => { if (e.key === "Escape" && q.value) { q.value = ""; run(); e.stopPropagation(); } });
  wrap.before(h("div", { class: "rd-tbar" }, q, n));
}

function enhanceCode() {
  for (const pre of R.article.querySelectorAll("pre")) {
    if (pre.parentElement.classList.contains("rd-pre")) continue;
    const box = h("div", { class: "rd-pre" });
    pre.before(box);
    box.append(pre, h("button", { class: "rd-copy", type: "button", "aria-label": "Copy this code" }, "Copy"));
  }
  R.article.addEventListener("click", (e) => {
    const b = e.target.closest(".rd-copy");
    if (!b) return;
    const pre = b.parentElement.querySelector("pre");
    copyText(pre ? pre.textContent : "").then((ok) => { b.textContent = ok ? "Copied" : "Failed"; setTimeout(() => { b.textContent = "Copy"; }, 1400); });
  });
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* not a secure context, or denied: fall back */ }
  const ta = h("textarea", { "aria-hidden": "true", tabindex: "-1", style: "position:fixed;top:0;left:0;opacity:0" });
  ta.value = text;
  document.body.append(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  ta.remove();
  return ok;
}

/* ------------------------------------------------------------------ toast */
function toast(text, ms = 1600) {
  if (!R.toasts) { R.toasts = h("div", { class: "mm-toasts rd-toasts", role: "status", "aria-live": "polite" }); document.body.append(R.toasts); }
  const t = h("div", { class: "mm-toast" }, text);
  R.toasts.replaceChildren(t);
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.remove(), ms);
}

/* ------------------------------------------------------------------ On this page */
function buildToc() {
  const plan = R.plan;
  if (!plan || !plan.items.length) return;
  let toc = R.doc.querySelector(".toc");
  if (!toc) { toc = h("div", { class: "toc" }); R.doc.append(toc); }
  for (const c of Array.from(toc.children)) if (!c.classList.contains("toc-mhdr")) c.remove();   // keep the shell's mobile header
  toc.classList.add("rd-toc");
  toc.setAttribute("role", "navigation");
  toc.setAttribute("aria-label", "On this page");
  R.tocEl = toc;

  const openAll = plan.items.length <= 45;
  const list = h("ol", { class: "rd-toc__list" });
  const entry = (n) => h("a", { class: "rd-toc__a", href: `#${n.id}`, "data-depth": String(n.depth) },
    R.labels && R.labels.get(n.id) ? h("span", { class: "rd-toc__n" }, R.labels.get(n.id)) : null, n.text);
  plan.tree.forEach((g, gi) => {
    const a = entry(g);
    R.tocLinks.set(g.id, a);
    if (!g.children.length) { list.append(h("li", { class: "rd-toc__g" }, h("div", { class: "rd-toc__row" }, h("span", { class: "rd-toc__tw" }), a))); return; }
    const subId = `rd-toc-sub-${gi}`;
    const tw = h("button", { class: "rd-toc__tw", type: "button", "aria-expanded": String(openAll), "aria-controls": subId, "aria-label": `Subsections of ${g.text}`, html: ICON.chev });
    const sub = h("ol", { class: "rd-toc__sub", id: subId }, g.children.map((c) => { const ca = entry(c); R.tocLinks.set(c.id, ca); return h("li", {}, ca); }));
    const li = h("li", { class: "rd-toc__g has-sub" + (openAll ? " is-open" : "") }, h("div", { class: "rd-toc__row" }, tw, a), sub);
    tw.addEventListener("click", () => { li.dataset.auto = ""; setGroup(li, !li.classList.contains("is-open")); });
    list.append(li);
  });

  const groups = plan.tree.filter((g) => g.children.length).length;
  const all = groups >= 4 ? h("button", { class: "rd-toc__all", type: "button", title: "Collapse all sections", "aria-label": "Collapse all sections", html: ICON.collapse }) : null;
  if (all) all.addEventListener("click", () => {
    const open = !toc.querySelector(".rd-toc__g.is-open");            // everything closed -> open all, otherwise close all
    toc.querySelectorAll(".rd-toc__g.has-sub").forEach((g) => { g.dataset.auto = ""; setGroup(g, open); });
    all.innerHTML = open ? ICON.collapse : ICON.expand;
    const label = open ? "Collapse all sections" : "Expand all sections";
    all.title = label; all.setAttribute("aria-label", label);
  });
  toc.append(h("div", { class: "rd-toc__hd" }, h("b", {}, "On this page"), all), list);
}
function setGroup(li, open) {
  li.classList.toggle("is-open", open);
  const b = li.querySelector(":scope > .rd-toc__row > .rd-toc__tw");
  if (b && b.hasAttribute("aria-expanded")) b.setAttribute("aria-expanded", String(open));
}
/* The active entry's group opens by itself (and closes again when you leave it, unless you opened it by hand). */
function followActive(link) {
  const g = link ? link.closest(".rd-toc__g.has-sub") : null;
  if (R.autoGroup && R.autoGroup !== g) { if (R.autoGroup.dataset.auto === "1") setGroup(R.autoGroup, false); R.autoGroup.dataset.auto = ""; R.autoGroup = null; }
  if (g && !g.classList.contains("is-open")) { setGroup(g, true); g.dataset.auto = "1"; R.autoGroup = g; }
  const toc = R.tocEl;
  if (!link || !toc || !toc.offsetParent) return;                       // rail not visible: nothing to scroll
  const t = link.getBoundingClientRect(), c = toc.getBoundingClientRect();
  if (t.top < c.top + 44) toc.scrollTop -= c.top + 44 - t.top;
  else if (t.bottom > c.bottom - 24) toc.scrollTop += t.bottom - (c.bottom - 24);
}

function toggleToc() {
  if (wide()) {
    const next = root.dataset.toc === "closed" ? "open" : "closed";
    if (next === "closed") root.dataset.toc = "closed"; else delete root.dataset.toc;
    store.set(KEY_TOC, next);
    const b = document.querySelector(".mm-top__toc");
    if (b) b.setAttribute("aria-expanded", String(next === "open"));
  } else {
    const b = document.querySelector(".mm-top__toc");                    // the shell owns the bottom sheet (body.toc-open)
    if (b) b.click();
  }
}

/* ------------------------------------------------------------------ banner, chapter bar, Aa popover */
function tuneBanner() {
  if (!R.banner) return;
  const actions = R.banner.querySelector(".bk-actions");
  if (actions && !actions.querySelector(".rd-aa-btn")) actions.append(aaButton("bk-pill-link rd-aa-btn"));
}
function aaButton(cls) {
  const b = h("button", { class: cls, type: "button", "aria-haspopup": "dialog", "aria-expanded": "false", title: "Reading settings: typeface and text size" }, h("span", { class: "rd-aa-glyph", "aria-hidden": "true" }, "Aa"), h("span", { class: "mm-sr-only" }, "Reading settings"));
  b.addEventListener("click", () => toggleAa(b));
  return b;
}

function bannerFacts() {
  const b = R.banner;
  const links = b ? Array.from(b.querySelectorAll(".bk-prevnext a")) : [];
  const pick = (a) => (a ? { url: a.getAttribute("href"), title: a.textContent.replace(/^[\s\u2190]+|[\s\u2192]+$/g, "").trim() } : null);
  return {
    chip: chipText(b && b.querySelector(".bk-ch") ? b.querySelector(".bk-ch").textContent : ""),
    minutes: readMinutes(b && b.querySelector(".bk-meta") ? b.querySelector(".bk-meta").textContent : ""),
    prev: pick(links.find((a) => !a.classList.contains("bk-next"))),
    next: pick(links.find((a) => a.classList.contains("bk-next"))),
  };
}

function navLink(kind, target) {
  const label = kind === "prev" ? "Previous chapter" : "Next chapter";
  if (!target) return h("span", { class: `rd-bar__nav rd-bar__nav--${kind}`, "aria-disabled": "true", html: ICON[kind] });
  return h("a", { class: `rd-bar__nav rd-bar__nav--${kind}`, href: target.url, rel: kind, title: `${label}: ${target.title}`, "aria-label": `${label}: ${target.title}`, html: ICON[kind] });
}

function buildBar() {
  const f = bannerFacts();
  R.facts = f;
  const bar = h("div", { class: "rd-bar", role: "region", "aria-label": "Chapter bar" },
    f.chip ? h("span", { class: "rd-bar__ch" }, f.chip) : null,
    f.minutes ? h("span", { class: "rd-bar__min" }, `${f.minutes} min read`) : null,
    h("span", { class: "rd-bar__sec" }),
    h("span", { class: "rd-bar__sp" }),
    h("span", { class: "rd-bar__pct", "aria-label": "Percent read" }),
    navLink("prev", f.prev), navLink("next", f.next),
    aaButton("rd-bar__aa"));
  document.body.append(bar);
  R.bar = bar;
  R.barSec = bar.querySelector(".rd-bar__sec");
  R.barPct = bar.querySelector(".rd-bar__pct");
  if (R.banner && "IntersectionObserver" in window) {
    // the top bar covers the first 52px of the viewport, so the banner counts as gone once it has slid under it
    const m = Math.round(cssPx("--topbar-h", 52));
    new IntersectionObserver(([e]) => setBar(!e.isIntersecting && e.boundingClientRect.bottom < topbarH() + 4), { rootMargin: `-${m}px 0px 0px 0px` }).observe(R.banner);
  }
}
function setBar(on) {
  if (on === R.barOn || !R.bar) return;
  R.barOn = on;
  R.bar.classList.toggle("is-on", on);
  root.toggleAttribute("data-rdbar", on);
}
/* Once nav.json is known, prev / next come from its chapter order (the banner's own links stay as the fallback). */
function applyNav(info) {
  const n = info && info.nav ? neighbours(info.nav, R.chapter) : null;
  if (!n || !R.bar) return;
  const tgt = (it) => (it ? { url: it.url, title: it.title } : null);
  R.bar.querySelector(".rd-bar__nav--prev").replaceWith(navLink("prev", tgt(n.prev)));
  R.bar.querySelector(".rd-bar__nav--next").replaceWith(navLink("next", tgt(n.next)));
  if (!R.facts.chip && n.item) R.bar.prepend(h("span", { class: "rd-bar__ch" }, n.item.part === "appendix" ? `App. ${n.item.chapter}` : `Ch. ${n.item.chapter}`));
}

function buildProgress() {
  R.progress = h("div", { class: "rd-progress", "aria-hidden": "true" }, h("i"));
  document.body.append(R.progress);
}

function toggleAa(btn) {
  if (R.aa && !R.aa.hidden) { closeAa(); return; }
  if (!R.aa) R.aa = buildAa();
  const r = btn.getBoundingClientRect();
  R.aa.style.top = `${Math.round(r.bottom + 6)}px`;
  R.aa.style.right = `${Math.max(8, Math.round(window.innerWidth - r.right))}px`;
  R.aa.hidden = false;
  R.aaBtn = btn;
  btn.setAttribute("aria-expanded", "true");
  syncAa();
  R.aa.querySelector("button").focus({ preventScroll: true });
}
function closeAa(restoreFocus = false) {
  if (!R.aa || R.aa.hidden) return;
  R.aa.hidden = true;
  if (R.aaBtn) { R.aaBtn.setAttribute("aria-expanded", "false"); if (restoreFocus) R.aaBtn.focus({ preventScroll: true }); }
}
function buildAa() {
  const seg = (label, key, val) => h("button", { class: "rd-aa__opt", type: "button", "data-key": key, "data-val": val, "aria-pressed": "false", onclick: () => setPrefs({ [key]: val }) }, label);
  const box = h("div", { class: "rd-aa", role: "dialog", "aria-label": "Reading settings", hidden: true },
    h("div", { class: "rd-aa__row", role: "group", "aria-label": "Typeface" }, seg("Serif", "font", "serif"), seg("Sans", "font", "sans")),
    h("div", { class: "rd-aa__row", role: "group", "aria-label": "Text size" },
      h("button", { class: "rd-aa__opt", type: "button", "data-step": "-1", "aria-label": "Smaller text", onclick: () => setPrefs({ size: R.prefs.size - 1 }) }, "A\u2212"),
      h("span", { class: "rd-aa__val", "aria-live": "polite" }),
      h("button", { class: "rd-aa__opt", type: "button", "data-step": "1", "aria-label": "Larger text", onclick: () => setPrefs({ size: R.prefs.size + 1 }) }, "A+")),
    h("button", { class: "rd-aa__reset", type: "button", onclick: () => setPrefs({ font: R.cfg.typography.defaultFont, size: R.cfg.typography.defaultSize }) }, "Reset"));
  document.body.append(box);
  return box;
}
function syncAa() {
  const sizes = R.cfg.typography.sizes;
  R.aa.querySelectorAll("[data-key]").forEach((b) => b.setAttribute("aria-pressed", String(R.prefs[b.dataset.key] === (b.dataset.key === "size" ? Number(b.dataset.val) : b.dataset.val))));
  R.aa.querySelector(".rd-aa__val").textContent = `${Math.round(sizes[R.prefs.size] / sizes[R.cfg.typography.defaultSize] * 100)}%`;
  R.aa.querySelector('[data-step="-1"]').disabled = R.prefs.size <= 0;
  R.aa.querySelector('[data-step="1"]').disabled = R.prefs.size >= sizes.length - 1;
}

/* ------------------------------------------------------------------ scroll: spy, progress, position memory */
/* Last tracked heading whose top has crossed the reading line. Headings are in document order, so this is a binary search. */
function activeIndex() {
  const s = R.spy;
  if (!s.length) return -1;
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) return s.length - 1;   // bottom of the page: the last section
  const line = readingLine();
  let lo = 0, hi = s.length - 1, ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (s[mid].el.getBoundingClientRect().top <= line) { ans = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return ans;
}
function pctNow() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  return max > 0 ? clamp01(window.scrollY / max) : 0;
}
function sectionLabel(i) {
  if (i < 0) return "";
  const hd = R.spy[i];
  const num = R.labels && R.labels.get(hd.id);
  return num ? `${num} ${hd.text}` : hd.text;
}
function setActive(i) {
  if (i === R.active) return;
  R.active = i;
  const link = i >= 0 ? R.tocLinks.get(R.spy[i].id) : null;
  if (R.activeLink && R.activeLink !== link) { R.activeLink.classList.remove("is-active"); R.activeLink.removeAttribute("aria-current"); }
  if (link) { link.classList.add("is-active"); link.setAttribute("aria-current", "location"); }
  R.activeLink = link;
  followActive(link);
  if (R.barSec) R.barSec.textContent = sectionLabel(i);
}
let lastPct = -1;
function update() {
  setActive(activeIndex());
  const p = pctNow();
  if (R.progress) R.progress.firstChild.style.transform = `scaleX(${p.toFixed(4)})`;
  const pc = Math.round(p * 100);
  if (pc !== lastPct) { lastPct = pc; if (R.barPct) R.barPct.textContent = `${pc}%`; }
  if (!R.banner) setBar(window.scrollY > 320);                         // no banner to watch: show the bar after a little scrolling
}
function onScroll() {
  if (!R.raf) R.raf = requestAnimationFrame(() => { R.raf = 0; update(); });
  clearTimeout(R.saveT);
  R.saveT = setTimeout(savePosition, 600);
}

function savePosition() {
  if (R.hold) return;
  const i = activeIndex();
  const pct = Math.round(pctNow() * 100);
  if (i < 0 || pct < 3) return;                                        // do not overwrite a saved position with "top of page"
  const el = R.spy[i].el;
  const map = readJSON(KEY_POS) || {};
  map[R.chapter] = { id: R.spy[i].id, off: Math.round(window.scrollY - (el.getBoundingClientRect().top + window.scrollY)), pct, t: Date.now() };
  store.set(KEY_POS, JSON.stringify(prunePositions(map)));
}

function offerResume() {
  if (!R.spy.length) return;
  const saved = (readJSON(KEY_POS) || {})[R.chapter];
  if (!shouldOfferResume(saved, location.hash.length > 1)) return;
  const target = document.getElementById(saved.id);
  if (!target) return;
  const idx = R.spy.findIndex((x) => x.id === saved.id);
  const name = idx >= 0 ? sectionLabel(idx) : target.textContent.trim();
  R.hold = true;                                                        // keep the saved spot until the reader decides
  const box = h("div", { class: "mm-toasts rd-resume", role: "status" });
  const done = () => { R.hold = false; clearTimeout(timer); box.remove(); window.removeEventListener("scroll", onFirstScroll); };
  const onFirstScroll = () => { if (window.scrollY > 240) done(); };   // reading on by hand counts as a decision
  const timer = setTimeout(done, 14000);
  box.append(h("div", { class: "mm-toast" },
    h("span", { class: "rd-resume__t" }, "Continue where you left off: ", h("b", {}, name)),
    h("button", { class: "rd-resume__go", type: "button", onclick: () => { instant(() => window.scrollTo(0, target.getBoundingClientRect().top + window.scrollY + (saved.off || 0))); done(); } }, "Resume"),
    h("button", { class: "rd-resume__no", type: "button", "aria-label": "Dismiss", onclick: done }, "\u2715")));
  document.body.append(box);
  window.addEventListener("scroll", onFirstScroll, { passive: true });
}

/* The old page CSS and the new reader CSS lay the page out differently, so a link like #3-chat opened from outside would land
   a little off. Once the reader layer is on, jump to the target again. */
function realignHash() {
  if (location.hash.length < 2) return;
  let id = location.hash.slice(1);
  try { id = decodeURIComponent(id); } catch { /* keep the raw text */ }
  const t = document.getElementById(id);
  if (t) instant(() => t.scrollIntoView({ block: "start" }));
}

/* ------------------------------------------------------------------ events */
function bindEvents() {
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", () => { if (R.raf === 0) onScroll(); closeAa(); }, { passive: true });
  window.addEventListener("pagehide", savePosition);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") savePosition(); });
  document.addEventListener("minime:toc-toggle", toggleToc);
  // On a wide screen the top bar's "Contents" button (shown only when the rail is closed) re-opens the rail instead of the sheet.
  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest(".mm-top__toc");
    if (!b || !wide()) return;
    e.preventDefault(); e.stopPropagation();
    toggleToc();
  }, true);
  document.addEventListener("click", (e) => { if (R.aa && !R.aa.hidden && !e.target.closest(".rd-aa") && !e.target.closest(".rd-aa-btn, .rd-bar__aa")) closeAa(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAa(true); });
  window.matchMedia(WIDE).addEventListener("change", (e) => {
    if (!e.matches) return;
    document.body.classList.remove("toc-open");                         // the sheet makes no sense on a wide screen
    const b = document.querySelector(".mm-top__toc");
    if (b) b.setAttribute("aria-expanded", String(root.dataset.toc !== "closed"));
  });
}
