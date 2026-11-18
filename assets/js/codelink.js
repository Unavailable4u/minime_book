/* MiniMe Atlas 2 - chapter <-> code links, browser half (P15, plan section 6.5). One ES module, no dependencies, no DOM at import time
   (tests run the pure parts in node and the page parts in jsdom).

   scripts/build_index.py writes data/index/linkables.json from the text of every <code> span of every chapter:

     { links:    { text: target },                         one answer everywhere
       choices:  { text: [target, ...] },                  several candidates: the reader picks
       sections: { "doc-x.html#heading-id": { text: target } } }   answers that depend on the section the span sits in
     target = "path[::qual][@start[-end]]"  for a file, a symbol or a line range,   "folder/"  for a folder

   initCodeLinks() fetches that file once, wraps every matching <code> of the chapter in <a class="mm-codelink"> (dotted underline) and
   shows a hover / focus card: what it is, its signature, the AI note's summary, freshness, and the buttons
   Open in Explorer . Source . GitHub . VS Code. A text with several candidates becomes a button that opens a chooser.

   Only <code> spans are linked: never plain prose, never a <pre> block, never text that is already inside a link. The build and this
   file read the same spans in the same order, so a section key always means the same section on both sides.
   Nothing here can break a chapter: any failure leaves the page exactly as it was. All text goes in with textContent. */
import { codeLinks, loadLinkOptions } from "./links.js";
import { buildRoute } from "./explorer/router.js";
import { h, num } from "./explorer/dom.js";
import { CODE, getJSON, buildTree, noteStatus, symbolRows, loadRecord, loadNote } from "./explorer/model.js";

const LINKABLES = "data/index/linkables.json";
const NOTES = "data/index/notes.json";
const SKIP = "pre, a, button, summary, nav, svg, figure, script, style, .toc, .mm-sb, .mm-cc";
const own = (o, k) => !!o && Object.prototype.hasOwnProperty.call(o, k);

/* ------------------------------------------------------------------ targets (pure) */
/* "a/b.py::Cls.m@10-20" -> { kind: "file", path, qual, start, end };  "a/b/" -> { kind: "dir", path };  null when it is neither. */
export function parseTarget(t) {
  if (typeof t !== "string" || !t.trim()) return null;
  if (t.endsWith("/")) { const p = t.replace(/\/+$/, ""); return p && !p.includes("..") ? { kind: "dir", path: p } : null; }
  const m = /^(.+?)(?:::([^@]+?))?(?:@(\d+)(?:-(\d+))?)?$/.exec(t);
  if (!m || !m[1] || m[1].includes("..")) return null;
  const start = m[3] ? Number(m[3]) : null;
  const end = m[4] ? Number(m[4]) : null;
  return { kind: "file", path: m[1], qual: m[2] || "", start: start && start > 0 ? start : null, end: start && end && end > start ? end : null };
}

/* Where "Open in Explorer" goes. A symbol opens on its Symbols tab, a line range on the Source tab, a folder on its page. */
export function explorerHref(pt) {
  if (!pt) return null;
  if (pt.kind === "dir") return `explorer.html${buildRoute({ view: "dir", path: pt.path })}`;
  const tab = pt.qual ? "symbols" : pt.start ? "source" : "";
  return `explorer.html${buildRoute({ view: "file", path: pt.path, qual: pt.qual, start: pt.start, end: pt.end, tab })}`;
}

/* What a <code> text is: { kind: "link", target } | { kind: "choices", targets } | null. A section's own answer wins. */
export function lookup(data, text, sectionKey = "") {
  if (!data || typeof text !== "string") return null;
  const sec = sectionKey && data.sections ? data.sections[sectionKey] : null;
  if (own(sec, text)) return { kind: "link", target: sec[text] };
  if (own(data.links, text)) return { kind: "link", target: data.links[text] };
  if (own(data.choices, text) && Array.isArray(data.choices[text]) && data.choices[text].length) return { kind: "choices", targets: data.choices[text] };
  return null;
}

/* "doc-x.html" for /doc-x.html, /guides/doc-x.html and the clean URL /doc-x */
export function pageName(pathname) {
  const last = String(pathname || "").split("/").filter(Boolean).pop() || "";
  return last && !/\.html?$/i.test(last) ? `${last}.html` : last;
}

/* ------------------------------------------------------------------ the chapter (DOM) */
/* Wrap every linkable <code> of `root`. Returns { linked, choices, info } where info maps each new <a> to what it stands for. */
export function linkChapter(root, data, page, doc = document) {
  const info = new WeakMap();
  let linked = 0;
  let choices = 0;
  let section = "";
  for (const el of root.querySelectorAll("h2[id], h3[id], code")) {
    if (el.closest("nav, .toc, .mm-sb")) continue;
    if (el.tagName !== "CODE") { section = el.id; continue; }
    if (el.closest(SKIP) || el.closest(".mm-codelink")) continue;
    const text = el.textContent.trim();
    const hit = text ? lookup(data, text, section ? `${page}#${section}` : "") : null;
    if (!hit) continue;
    const a = doc.createElement("a");
    if (hit.kind === "link") {
      const pt = parseTarget(hit.target);
      const href = explorerHref(pt);
      if (!href) continue;
      a.className = "mm-codelink";
      a.href = href;
      info.set(a, { kind: "link", target: hit.target });
      linked++;
    } else {
      const targets = hit.targets.filter((t) => parseTarget(t));
      if (targets.length < 2) continue;
      a.className = "mm-codelink mm-codelink--choice";
      a.href = explorerHref(parseTarget(targets[0]));          // without JavaScript the first candidate is the nearest thing to an answer
      a.setAttribute("aria-haspopup", "dialog");
      info.set(a, { kind: "choices", targets });
      choices++;
    }
    el.replaceWith(a);
    a.append(el);
  }
  return { linked, choices, info };
}

/* ------------------------------------------------------------------ the card's content */
/* env: { tree, notes, linkOpts, loadRecord(file), loadNote(path) }. Returns a plain description (null for a target that is not a target):
     { kind, title, where, sig, summary, from, fresh, stats, buttons: { explorer, source?, github?, vscode? }, missing? } */
export async function describeTarget(target, env) {
  const pt = typeof target === "string" ? parseTarget(target) : target;
  if (!pt) return null;
  const explorer = explorerHref(pt);
  if (pt.kind === "dir") {
    const d = env.tree.dirs.get(pt.path);
    return { kind: "folder", title: `${pt.path}/`, where: "", sig: "", summary: "", from: "", fresh: "", buttons: { explorer },
      stats: d ? `${num(d.n.files)} files · ${num(d.n.lines)} lines · ${num(d.n.functions)} functions` : "", missing: !d };
  }
  const file = env.tree.files.get(pt.path);
  const out = { kind: pt.qual ? "symbol" : "file", title: pt.qual || pt.path.split("/").pop(), where: pt.path, sig: "", summary: "", from: "", fresh: "", stats: "", buttons: { explorer }, missing: !file };
  let start = pt.start;
  let end = pt.end;
  if (file) {
    const [rec, note] = await Promise.all([env.loadRecord(file).catch(() => null), noteStatus(env.notes, pt.path) === "none" ? null : env.loadNote(pt.path).catch(() => null)]);
    if (pt.qual) {
      const row = rec ? symbolRows(rec, note).find((r) => r.qual === pt.qual) : null;
      if (row) {
        out.kind = row.kind === "class" ? "class" : "function";
        out.sig = row.sig;
        out.summary = row.desc;
        out.from = row.from;
        out.fresh = row.fresh;
        out.stats = `lines ${num(row.start)}–${num(row.end)} · ${num(row.loc)} loc${row.cc != null ? ` · cc ${row.cc}` : ""}`;
        if (!start) { start = row.start; end = row.end; }
      } else if (rec) out.summary = "This name is not in the census any more. It may have been renamed or removed.";
    } else {
      const doc = rec && rec.module_doc ? rec.module_doc.split(/\n\s*\n/)[0].replace(/\s+/g, " ").trim() : "";
      out.summary = note && note.summary ? note.summary : doc.length > 220 ? `${doc.slice(0, 220)}…` : doc;
      out.from = note && note.summary ? "note" : doc ? "doc" : "";
      out.fresh = note ? (noteStatus(env.notes, pt.path) === "stale" ? "stale" : "fresh") : "none";
      out.stats = `${num(file.lines)} lines${file.functions ? ` · ${num(file.functions)} functions` : ""}${file.classes ? ` · ${num(file.classes)} classes` : ""}`;
    }
    if (!file.binary) out.buttons.source = `explorer.html${buildRoute({ view: "file", path: pt.path, qual: pt.qual, start, end, tab: "source" })}`;
  }
  const l = codeLinks({ path: pt.path, start, end }, env.linkOpts || {});
  if (l.github) out.buttons.github = l.github;
  if (l.vscode) out.buttons.vscode = l.vscode;
  return out;
}

const FRESH = { fresh: ["mm-badge mm-badge--ok", "AI note fresh"], stale: ["mm-badge mm-badge--stale", "code changed since the note"] };

export function renderCard(desc) {
  const b = desc.buttons;
  const btn = (label, href, ext) => (href ? h("a", { class: "mm-btn", href, target: ext ? "_blank" : null, rel: ext ? "noopener" : null }, label) : null);
  return [
    desc.where ? h("p", { class: "mm-cc__where" }, desc.where) : null,
    h("p", { class: "mm-cc__title" }, h("span", { class: "mm-cc__kind" }, desc.kind), " ", desc.title),
    desc.sig ? h("pre", { class: "mm-cc__sig" }, desc.sig) : null,
    desc.summary ? h("p", { class: "mm-cc__sum" }, desc.summary, desc.from ? h("span", { class: "mm-cc__from" }, desc.from === "note" ? " AI note" : " docstring") : null) : (desc.missing ? null : h("p", { class: "mm-cc__sum mm-cc__dim" }, "No description yet.")),
    desc.missing ? h("p", { class: "mm-cc__sum mm-cc__dim" }, "Not in the census of this Atlas.") : null,
    desc.stats ? h("p", { class: "mm-cc__stats" }, desc.stats, FRESH[desc.fresh] ? h("span", { class: FRESH[desc.fresh][0] }, FRESH[desc.fresh][1]) : null) : null,
    h("p", { class: "mm-cc__go" }, btn("Open in Explorer", b.explorer), btn("Source", b.source), btn("GitHub", b.github, true), btn("VS Code", b.vscode)),
  ].filter(Boolean);
}

export function renderChooser(targets) {
  return [
    h("p", { class: "mm-cc__title" }, `This name matches ${targets.length} places`),
    h("ul", { class: "mm-cc__list" }, targets.map((t) => {
      const pt = parseTarget(t);
      return h("li", null, h("a", { href: explorerHref(pt) }, pt.kind === "dir" ? `${pt.path}/` : `${pt.path}${pt.qual ? `::${pt.qual}` : ""}`));
    })),
  ];
}

/* ------------------------------------------------------------------ the card (browser only) */
let envPromise = null;
function loadEnv() {
  if (!envPromise) {
    envPromise = Promise.all([getJSON(`${CODE}/tree.json`), getJSON(NOTES).catch(() => null), loadLinkOptions().catch(() => ({}))]).then(([raw, notes, linkOpts]) => {
      const tree = buildTree(raw);
      const core = { tree, notes };
      return { tree, notes, linkOpts, loadRecord: (f) => loadRecord(core, f), loadNote };
    });
    envPromise.catch(() => { envPromise = null; });          // a failed load is tried again on the next hover
  }
  return envPromise;
}

const SHOW_MS = 220;
const HIDE_MS = 180;

function createCard(info, doc = document) {
  const win = doc.defaultView;
  const card = h("div", { class: "mm-cc", role: "dialog", "aria-label": "Code reference", hidden: true });
  let current = null;
  let pinned = false;
  let timer = 0;
  let seq = 0;
  let quiet = false;                      // true while this code moves the focus itself
  doc.body.append(card);

  const place = () => {
    if (!current) return;
    const r = current.getBoundingClientRect();
    const w = card.offsetWidth || 320;
    const hgt = card.offsetHeight || 160;
    const left = Math.max(8, Math.min(r.left, win.innerWidth - w - 8));
    const below = r.bottom + 6 + hgt <= win.innerHeight || r.top - 6 - hgt < 0;
    card.style.left = `${Math.round(left)}px`;
    card.style.top = `${Math.round(below ? r.bottom + 6 : r.top - 6 - hgt)}px`;
  };
  const hide = () => {
    win.clearTimeout(timer);
    seq++;
    pinned = false;
    if (current) current.removeAttribute("aria-expanded");
    current = null;
    card.hidden = true;
  };
  const show = async (a, pin) => {
    const what = info.get(a);
    if (!what) return;
    if (current === a && !card.hidden) { pinned = pinned || pin; return; }
    if (current) current.removeAttribute("aria-expanded");
    const my = ++seq;
    current = a;
    pinned = pin;
    a.setAttribute("aria-expanded", "true");
    card.replaceChildren(h("p", { class: "mm-cc__sum mm-cc__dim" }, "Loading…"));
    card.hidden = false;
    place();
    try {
      let kids;
      if (what.kind === "choices") kids = renderChooser(what.targets);
      else { const d = await describeTarget(what.target, await loadEnv()); if (!d) return hide(); kids = renderCard(d); }
      if (my !== seq) return;
      card.replaceChildren(...kids);
    } catch {
      if (my !== seq) return;
      card.replaceChildren(h("p", { class: "mm-cc__sum mm-cc__dim" }, "Could not load details. The link still works."));
    }
    place();
  };
  const later = (fn, ms) => { win.clearTimeout(timer); timer = win.setTimeout(fn, ms); };
  const anchorOf = (e) => (e.target && e.target.closest ? e.target.closest("a.mm-codelink") : null);
  const inCard = (e) => !!(e.target && e.target.closest && e.target.closest(".mm-cc"));
  const canHover = !(win.matchMedia && win.matchMedia("(hover: none)").matches);

  if (canHover) {
    doc.addEventListener("mouseover", (e) => {
      const a = anchorOf(e);
      if (a) { if (!pinned) later(() => show(a, false), current === a ? 0 : SHOW_MS); }
      else if (inCard(e)) win.clearTimeout(timer);
    });
    doc.addEventListener("mouseout", (e) => {
      if ((anchorOf(e) || inCard(e)) && !pinned) later(hide, HIDE_MS);
    });
  }
  doc.addEventListener("focusin", (e) => { const a = anchorOf(e); if (a && !pinned && !quiet) show(a, false); });
  doc.addEventListener("focusout", (e) => { if (anchorOf(e) && !pinned && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".mm-cc"))) later(hide, HIDE_MS); });
  doc.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || card.hidden) return;
    const a = current;
    const hadFocus = card.contains(doc.activeElement);
    hide();
    if (hadFocus && a && a.isConnected) { quiet = true; a.focus({ preventScroll: true }); quiet = false; }     // focus returns to the link only if it was inside the card
  });
  doc.addEventListener("click", (e) => {
    const a = anchorOf(e);
    if (a && a.classList.contains("mm-codelink--choice") && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); show(a, true); return; }
    if (!card.hidden && !inCard(e) && !a) hide();
  });
  win.addEventListener("scroll", () => { if (!card.hidden && !pinned) hide(); }, { passive: true, capture: true });
  win.addEventListener("resize", () => { if (!card.hidden) place(); });
  return { card, show, hide };
}

/* Fire and forget: the links work unstyled, and nothing about the page's layout depends on the stylesheet. */
function loadCss(doc = document) {
  const href = new URL("../css/codelink.css", import.meta.url).href;
  if ([...doc.styleSheets].some((x) => x.href === href) || doc.querySelector(`link[href="${href}"]`)) return;
  doc.head.append(h("link", { rel: "stylesheet", href }));
}

let started = false;

/* Boot: called by shell.js on chapter pages. Resolves to the number of links made (0 when there is nothing to do). Never rejects. */
export async function initCodeLinks({ doc = document, win = doc.defaultView } = {}) {
  try {
    const main = doc.querySelector("main");
    if (started || !main || !main.querySelector(".bk-banner, .doc article")) return 0;
    started = true;
    const data = await getJSON(LINKABLES).catch(() => null);
    if (!data || !data.links) return 0;
    loadCss(doc);
    const { linked, choices, info } = linkChapter(main, data, pageName(win.location.pathname), doc);
    if (linked + choices > 0) createCard(info, doc);
    return linked + choices;
  } catch (err) {
    console.warn("[atlas codelink]", err);
    return 0;
  }
}
