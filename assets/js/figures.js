/* MiniMe Atlas 2 - figure layer (P06). One ES module, no dependencies.

   Puts diagrams into the 15 untouched chapter pages (doc-*.html) AT RUN TIME. The chapter bodies come from an external
   builder and would be overwritten, so nothing here is written back to the HTML: the figures are listed in one manifest
   per chapter, content/figures/<chapter id>.json, and this module inserts them after the heading the manifest names.

   Loaded by shell.js once the reader layer (reader.js) has finished, so every heading already has an id. It fetches
   content/figures/<chapter>.json (a 404 just means "this chapter has no figures yet") and assets/css/figures.css.

   Manifest entry   { id, after, place, type, src | code, caption, alt, wide, size }
     id       lower-case letters, digits, hyphens; unique in the chapter; the figure gets the anchor #fig-<id>
     after    id of the heading the figure follows
     place    "end" (default): last thing in that heading's section, i.e. just before the next heading (h1-h4)
              "start": right under the heading
     type     arch      (P26) a generated architecture view drawn inline, no iframe: view = a view id of data/arch/model.json, optional
              flow (a flow id to lay over the unified view) and focus (a step / box key to open); needs neither src nor size
              archify   an iframe of architecture/<x>.html?embed=1&theme=...  (needs size: [width, height] of its SVG)
              svg       an inline SVG from src (content/figures/**.svg) or code; inherits the page's colour tokens
              mermaid   a Mermaid diagram from code (or src *.mmd); the library is loaded only when one is on the page
              graph-slice (P20) the graph neighbourhood of one file or folder, drawn inline from data/graph/file-links.json: focus = a path
                        from data/index/paths.json, optional limit (3 to 24 neighbours, default 12); needs neither src nor size
              (chart is reserved and is skipped with a console warning)
     caption  shown under the figure and in the viewer;   alt   what the figure shows, for screen readers (required;
              scripts/check_site.py enforces it, here a missing alt falls back to the caption)
     wide     true: use the whole ~100ch track instead of the 72ch text column

   Numbers are chapter-relative and follow the order on the page (Figure 4.2), not the order in the manifest.

   What each figure gets: a dot-grid frame, a caption bar, an Expand button (full-screen viewer with wheel / pinch zoom,
   drag pan, + - 0 1 keys, Esc), "Copy source" for svg / mermaid, "Open interactive diagram" for archify. Inline archify
   frames are previews (they do not catch the mouse, so they never trap page scrolling); the viewer shows the same page
   zoomable, and the link opens the full interactive diagram.

   Theme: archify frames and Mermaid diagrams are redrawn when the reader switches Dark / Paper (event minime:theme).
   Pure helpers are exported so scripts/test_figures.py can run them in Node with no browser. */

const BASE = new URL("../../", import.meta.url);
const CSS_PATH = "assets/css/figures.css";
export const MERMAID_SRC = "assets/vendor/mermaid/mermaid.min.js";   // written by scripts/vendor_mermaid.py (pinned)
export const TYPES = ["arch", "archify", "svg", "mermaid", "graph-slice"];
export const RESERVED_TYPES = ["chart"];
export const ARCHIFY_PAD = 24;            // px the diagram page adds around its SVG in embed mode (16 padding + 8 slack)
export const ZOOM_MAX = 8;

const ID_RE = /^[a-z0-9][a-z0-9-]{0,62}$/;
/* graph-slice (P20): the same rules as assets/js/graphslice.js, which is only loaded when a figure needs drawing (this file has no imports) */
const SLICE_FOCUS = /^[A-Za-z0-9._@+-]+(?:\/[A-Za-z0-9._@+-]+)*\/?$/;
const SLICE_MIN = 3, SLICE_MAX = 24;
const ARCHIFY_SRC = /^architecture\/[A-Za-z0-9._-]+\.html$/;
const CONTENT_SRC = /^content\/figures\/(?!.*\.\.)[A-Za-z0-9._/-]+$/;

/* ================================================================== pure helpers (no DOM) */

const str = (v) => typeof v === "string" && v.trim() !== "";

/* Checks one manifest and returns { figures, problems }. Entries with a problem that would make them unusable are dropped
   (and listed in problems); a missing alt only warns. Never throws: a half-written manifest must not break a chapter. */
export function normalizeManifest(raw) {
  const figures = [], problems = [], seen = new Set();
  const list = Array.isArray(raw) ? raw : raw && Array.isArray(raw.figures) ? raw.figures : null;
  if (!list) return { figures, problems: ['expected {"figures": [...]}'] };
  list.forEach((f, i) => {
    const at = f && typeof f === "object" && typeof f.id === "string" ? `"${f.id}"` : `#${i}`;
    const bad = (why) => { problems.push(`figure ${at}: ${why}`); };
    if (!f || typeof f !== "object" || Array.isArray(f)) return bad("is not an object");
    if (typeof f.id !== "string" || !ID_RE.test(f.id)) return bad('needs an "id" of lower-case letters, digits and hyphens');
    if (seen.has(f.id)) return bad("duplicate id");
    if (!str(f.after)) return bad('needs "after" (the id of a heading)');
    if (!str(f.caption)) return bad('needs a "caption"');
    if (RESERVED_TYPES.includes(f.type)) return bad(`type "${f.type}" is not available yet (a later patch)`);
    if (!TYPES.includes(f.type)) return bad(`unknown type "${f.type}" (use ${TYPES.join(", ")})`);
    const out = {
      id: f.id, after: f.after.trim(), place: f.place === "start" ? "start" : "end", type: f.type, src: null, code: null,
      caption: f.caption.trim(), alt: str(f.alt) ? f.alt.trim() : f.caption.trim(), wide: f.wide === true, size: null,
    };
    if (!str(f.alt)) problems.push(`figure ${at}: has no "alt"; the caption is used instead`);
    if (f.type === "arch") {
      if (typeof f.view !== "string" || !ID_RE.test(f.view)) return bad('needs "view": the id of a view of data/arch/model.json');
      if (f.flow != null && (typeof f.flow !== "string" || !ID_RE.test(f.flow))) return bad('"flow" must be a flow id');
      if (f.focus != null && !str(f.focus)) return bad('"focus" must be text');
      out.view = f.view; out.flow = f.flow || null; out.focus = f.focus || null;
    } else if (f.type === "graph-slice") {
      if (!str(f.focus)) return bad('needs "focus": a file or folder path from data/index/paths.json');
      const focus = f.focus.trim();
      if (!SLICE_FOCUS.test(focus) || focus.split("/").some((x) => x === "." || x === "..")) return bad('"focus" must be a repo-relative path of letters, digits and . _ @ + - separated by /, with no . or .. segment');
      if (f.limit != null && (!Number.isInteger(f.limit) || f.limit < SLICE_MIN || f.limit > SLICE_MAX)) return bad(`"limit" must be a whole number from ${SLICE_MIN} to ${SLICE_MAX}`);
      out.focus = focus.replace(/\/+$/, ""); out.limit = f.limit == null ? null : f.limit;
    } else if (f.type === "archify") {
      if (!str(f.src) || !ARCHIFY_SRC.test(f.src)) return bad('needs "src": "architecture/<name>.html"');
      const s = f.size;
      if (!Array.isArray(s) || s.length !== 2 || !s.every((n) => Number.isFinite(n) && n >= 100 && n <= 20000)) return bad('needs "size": [width, height], the pixel size of the diagram\'s SVG');
      out.src = f.src; out.size = [s[0], s[1]];
    } else {
      const hasSrc = str(f.src), hasCode = str(f.code);
      if (hasSrc === hasCode) return bad('needs exactly one of "src" or "code"');
      const ext = f.type === "svg" ? ".svg" : ".mmd";
      if (hasSrc && !(CONTENT_SRC.test(f.src) && f.src.endsWith(ext))) return bad(`"src" must be content/figures/...${ext}`);
      if (hasCode && f.type === "svg" && !/^\s*<svg[\s>]/i.test(f.code)) return bad('"code" must start with <svg');
      out.src = hasSrc ? f.src : null; out.code = hasCode ? f.code : null;
    }
    seen.add(f.id);
    figures.push(out);
  });
  return { figures, problems };
}

/* The nav.json entry of a chapter, or null. */
export function chapterItem(nav, id) {
  for (const w of (nav && nav.wings) || []) for (const it of (w && w.items) || []) if (it && it.id === id) return it;
  return null;
}
export const figureLabel = (chapter, n) => (chapter == null || chapter === "" ? `Figure ${n}` : `Figure ${chapter}.${n}`);

/* archify's own URL parameters: theme is light|dark, embed=1 hides its toolbar and cards. */
export const archifyTheme = (theme) => (theme === "paper" ? "light" : "dark");
export const archifyUrl = (src, theme) => `${src}?embed=1&theme=${archifyTheme(theme)}`;
export const ratioOf = (size) => Math.round((size[1] / size[0]) * 10000) / 10000;

/* Is this SVG text safe to put into the page? Rejects, never repairs. scripts/check_site.py has the same rules in Python
   (svg_problem); test_figures.py runs both on one list of samples. */
const UNSAFE_SVG = [
  /<\s*(?:script|foreignObject|iframe|object|embed|image|set|animate)\b/i,
  /\son[a-z]+\s*=/i,
  /javascript:/i,
  /@import/i,
  /url\(\s*["']?\s*(?!#)/i,
  /\b(?:xlink:)?href\s*=\s*["']\s*(?!#)/i,
];
export function svgLooksSafe(text) {
  const t = String(text);
  if (!/^\s*(?:<\?xml[^>]*\?>\s*)?(?:<!--[\s\S]*?-->\s*)*<svg[\s>]/i.test(t)) return false;
  return !UNSAFE_SVG.some((re) => re.test(t));
}

/* Natural size of an SVG element or text: its viewBox, else width / height, else a default. */
export function svgSize(attrs) {
  const vb = String(attrs.viewBox || "").trim().split(/[\s,]+/).map(Number);
  if (vb.length === 4 && vb[2] > 0 && vb[3] > 0) return { w: vb[2], h: vb[3] };
  const w = parseFloat(attrs.width), hh = parseFloat(attrs.height);
  if (w > 0 && hh > 0) return { w, h: hh };
  return { w: 800, h: 500 };
}

/* ---- viewer maths. A transform is { k, x, y }: screen = content * k + (x, y). box = { w, h } of the stage. */
export function fitTransform(box, size, pad = 24, maxK = 2.5) {
  const k = Math.max(0.05, Math.min((box.w - 2 * pad) / size.w, (box.h - 2 * pad) / size.h, maxK));
  return { k, x: (box.w - size.w * k) / 2, y: (box.h - size.h * k) / 2 };
}
/* Zoom by `factor` keeping the content point under (px, py) where it is. k stays within [min, max]. */
export function zoomAt(t, factor, px, py, min, max = ZOOM_MAX) {
  const k = Math.min(max, Math.max(min, t.k * factor));
  const f = k / t.k;
  return { k, x: px - (px - t.x) * f, y: py - (py - t.y) * f };
}
/* Lets you pan anywhere, but never lose the figure: at least `margin` px of it stay inside the stage. */
export function keepVisible(t, box, size, margin = 80) {
  const w = size.w * t.k, hh = size.h * t.k;
  return { k: t.k, x: Math.min(box.w - margin, Math.max(margin - w, t.x)), y: Math.min(box.h - margin, Math.max(margin - hh, t.y)) };
}
export function wheelFactor(deltaY, deltaMode = 0, ctrl = false) {
  const px = deltaMode === 1 ? deltaY * 16 : deltaMode === 2 ? deltaY * 400 : deltaY;
  return Math.exp(Math.max(-120, Math.min(120, -px)) * (ctrl ? 0.01 : 0.0018));   // a trackpad pinch arrives as ctrl + wheel
}
/* Two pointers moved from (a0, b0) to (a1, b1): the zoom factor and how far their midpoint travelled. */
export function pinchStep(a0, b0, a1, b1) {
  const d0 = Math.hypot(b0.x - a0.x, b0.y - a0.y) || 1, d1 = Math.hypot(b1.x - a1.x, b1.y - a1.y) || 1;
  const m0 = { x: (a0.x + b0.x) / 2, y: (a0.y + b0.y) / 2 }, m1 = { x: (a1.x + b1.x) / 2, y: (a1.y + b1.y) / 2 };
  return { factor: d1 / d0, from: m0, dx: m1.x - m0.x, dy: m1.y - m0.y };
}

/* ---- Mermaid: colours come from the design tokens (get(name) returns the resolved value of a CSS variable). */
export function mermaidThemeVariables(get) {
  const c = (n, d) => get(n) || d;
  return {
    background: c("--panel", "#ffffff"), primaryColor: c("--panel-2", "#f3f1ea"), primaryTextColor: c("--ink", "#1b1b1f"),
    primaryBorderColor: c("--line-strong", "#8b8779"), secondaryColor: c("--panel", "#ffffff"), tertiaryColor: c("--panel", "#ffffff"),
    lineColor: c("--flow", "#0e7490"), textColor: c("--ink", "#1b1b1f"), mainBkg: c("--panel-2", "#f3f1ea"), nodeBorder: c("--line-strong", "#8b8779"),
    clusterBkg: c("--panel", "#ffffff"), clusterBorder: c("--line", "#dcd8cc"), edgeLabelBackground: c("--panel", "#ffffff"),
    noteBkgColor: c("--panel-2", "#f3f1ea"), noteTextColor: c("--ink", "#1b1b1f"), noteBorderColor: c("--gate", "#a64a07"),
    fontFamily: c("--font-ui", "sans-serif"), fontSize: "14px",
  };
}
/* The Atlas's semantic colours as Mermaid classes: write  A:::gate  in the source. Colour is never the only carrier:
   gate is dashed, here is thick. An author's own `classDef <name>` wins. */
const SEMANTIC = [
  ["flow", "--flow", "stroke-width:2px"],
  ["gate", "--gate", "stroke-width:2px,stroke-dasharray:5 3"],
  ["here", "--brand", "stroke-width:4px"],
  ["ok", "--ok", "stroke-width:2px"],
  ["rel", "--graph", "stroke-width:2px"],
];
const MERMAID_CLASSABLE = /^\s*(?:%%[^\n]*\n\s*)*(?:flowchart|graph|stateDiagram(?:-v2)?)\b/;
export function withSemanticClasses(code, get) {
  if (!MERMAID_CLASSABLE.test(code)) return code;
  const defs = SEMANTIC.filter(([name]) => !new RegExp(`\\bclassDef\\s+${name}\\b`).test(code))
    .map(([name, token, extra]) => `classDef ${name} stroke:${get(token) || "#888"},${extra}`);
  return defs.length ? `${code.replace(/\s+$/, "")}\n${defs.join("\n")}\n` : code;
}

/* ================================================================== DOM part (browser only) */

const root = typeof document !== "undefined" ? document.documentElement : null;

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
const svgIcon = (d) => `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${d}</svg>`;
const ICON = {
  expand: svgIcon('<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'),
  close: svgIcon('<path d="M6 6l12 12M18 6L6 18"/>'),
  plus: svgIcon('<path d="M12 5v14M5 12h14"/>'),
  minus: svgIcon('<path d="M5 12h14"/>'),
  fit: svgIcon('<rect x="5" y="7" width="14" height="10" rx="1.5"/>'),
  copy: svgIcon('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>'),
  open: svgIcon('<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>'),
};

const F = { started: false, recs: [], theme: "dark", mermaid: null, queue: Promise.resolve(), n: 0, lb: null };
const safe = (name, fn) => { try { return fn(); } catch (err) { console.warn(`[atlas figures] ${name} failed:`, err); return null; } };
const instant = (fn) => { root.style.scrollBehavior = "auto"; try { fn(); } finally { root.style.scrollBehavior = ""; } };   // the old page CSS sets smooth scrolling
const withTimeout = (p, ms) => Promise.race([Promise.resolve(p).catch(() => null), new Promise((r) => setTimeout(() => r(null), ms))]);

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* insecure context or denied: fall back */ }
  const ta = h("textarea", { "aria-hidden": "true", tabindex: "-1", style: "position:fixed;top:0;left:0;opacity:0" });
  ta.value = text;
  document.body.append(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { ok = false; }
  ta.remove();
  return ok;
}
/* A button whose label says "Copied" for a moment; no toast, so it also works inside the viewer. */
function copyButton(cls, get) {
  const label = h("span", {}, "Copy source");
  const b = h("button", { class: cls, type: "button" }, h("span", { html: ICON.copy }), label);
  b.addEventListener("click", async () => {
    const text = get();
    if (!text) return;
    label.textContent = (await copyText(text)) ? "Copied" : "Could not copy";
    clearTimeout(b._t);
    b._t = setTimeout(() => { label.textContent = "Copy source"; }, 1600);
  });
  return b;
}

function loadCss() {
  return new Promise((resolve) => {
    const href = new URL(CSS_PATH, BASE).href;
    if ([...document.styleSheets].some((s) => s.href === href)) { resolve(); return; }
    const link = h("link", { rel: "stylesheet", href });
    link.addEventListener("load", resolve, { once: true });
    link.addEventListener("error", resolve, { once: true });          // unstyled but present beats waiting forever
    setTimeout(resolve, 2000);
    document.head.append(link);
  });
}

/* ------------------------------------------------------------------ boot */
export async function initFigures(opts = {}) {
  if (!root || F.started) return;
  const article = document.querySelector("main .doc article");
  if (!article) return;
  const chapter = document.body.dataset.page || (location.pathname.split("/").pop() || "").replace(/\.html$/, "");
  if (!chapter) return;

  let raw;
  try {
    const r = await fetch(new URL(`content/figures/${chapter}.json`, BASE));
    if (r.status === 404) return;                                     // most chapters have no figures (yet)
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    raw = await r.json();
  } catch (err) { console.warn("[atlas figures] manifest not loaded:", err); return; }

  F.started = true;
  const { figures, problems } = normalizeManifest(raw);
  for (const p of problems) console.warn("[atlas figures]", p);
  if (!figures.length) return;
  const [info] = await Promise.all([withTimeout(opts.navReady, 1500), loadCss()]);
  F.theme = root.dataset.theme === "paper" ? "paper" : "dark";
  F.chapter = (chapterItem(info && info.nav, chapter) || {}).chapter;

  const tails = new Map();
  for (const fig of figures) {
    const heading = document.getElementById(fig.after);
    if (!heading || !article.contains(heading)) { console.warn(`[atlas figures] figure "${fig.id}": no heading with id "${fig.after}" in this chapter`); continue; }
    if (document.getElementById(`fig-${fig.id}`)) { console.warn(`[atlas figures] figure "${fig.id}": the id fig-${fig.id} is already used on this page`); continue; }
    const rec = safe(`build ${fig.id}`, () => buildFigure(fig));
    if (!rec) continue;
    insert(heading, fig.place, rec.el, tails);
    F.recs.push(rec);
  }
  renumber();
  document.addEventListener("minime:theme", (e) => onTheme(e.detail));
  safe("lazy", lazyRender);

  // The page grew above the reader's position: put a #heading or #fig-... link back where it points.
  let hash = "";
  try { hash = decodeURIComponent((location.hash || "").slice(1)); } catch { hash = ""; }
  const target = hash && document.getElementById(hash);
  if (target) instant(() => target.scrollIntoView({ block: "start" }));
  document.dispatchEvent(new CustomEvent("minime:figures", { detail: { count: F.recs.length } }));
}

/* Where a figure goes. "end": before the next heading (or the chapter footer); several figures for one spot keep their order. */
const STOP = "h1, h2, h3, h4, .bk-footer";
function insert(heading, place, node, tails) {
  const key = `${heading.id}|${place}`;
  const parent = heading.parentNode;
  if (tails.has(key)) { const t = tails.get(key); parent.insertBefore(node, t.nextSibling); }
  else if (place === "start") parent.insertBefore(node, heading.nextSibling);
  else {
    let n = heading.nextElementSibling;
    while (n && !n.matches(STOP)) n = n.nextElementSibling;
    parent.insertBefore(node, n);                                      // n === null appends
  }
  tails.set(key, node);
}

function renumber() {
  const order = new Map([...document.querySelectorAll(".mm-figure[data-fig]")].map((el, i) => [el, i + 1]));
  for (const rec of F.recs) {
    const label = figureLabel(F.chapter, order.get(rec.el) || 0);
    rec.label = label;
    rec.numEl.textContent = label;
    rec.expand.setAttribute("aria-label", `Expand ${label}: ${rec.fig.caption}`);
  }
}

/* ------------------------------------------------------------------ one figure */
function buildFigure(fig) {
  const rec = { fig, kind: fig.type, size: null, svg: null, source: null, label: "Figure", failed: false, rendered: false };
  rec.numEl = h("span", { class: "mm-figure__num" }, "Figure");
  rec.expand = h("button", { class: "mm-btn fg__tool fg__expand", type: "button", onclick: () => openViewer(rec) }, h("span", { html: ICON.expand }), h("span", {}, "Expand"));
  const tools = h("span", { class: "fg__tools" }, rec.expand);
  rec.canvas = h("div", { class: "mm-figure__canvas fg__canvas" });
  rec.el = h("figure", { class: `mm-figure fg fg--${fig.type}${fig.wide ? " fg--wide" : ""}`, id: `fig-${fig.id}`, "data-fig": fig.id });

  if (fig.type === "arch") {
    rec.holder = h("div", { class: "fg__arch", role: "group", "aria-label": fig.alt });
    rec.holder.append(h("p", { class: "fg__wait" }, "Diagram loads as you scroll to it."));
    rec.canvas.append(rec.holder);
    rec.expand.disabled = true;                                        // until the diagram is drawn
    rec.href = `arch-view.html?view=${encodeURIComponent(fig.view)}${fig.flow ? `&flow=${encodeURIComponent(fig.flow)}` : ""}`;
    tools.append(copyButton("mm-btn fg__tool", () => rec.source), h("a", { class: "mm-btn fg__tool", href: rec.href, target: "_blank", rel: "noopener" }, h("span", { html: ICON.open }), h("span", {}, "Open interactive diagram")));
    rec.print = h("p", { class: "fg__print" }, `Interactive diagram: ${new URL(rec.href, location.href).href}`);
  } else if (fig.type === "graph-slice") {
    rec.holder = h("div", { class: "fg__svg", role: "img", "aria-label": fig.alt });
    rec.holder.append(h("p", { class: "fg__wait" }, "Diagram loads as you scroll to it."));
    rec.canvas.append(rec.holder);
    rec.expand.disabled = true;                                        // until the diagram is drawn
    tools.append(copyButton("mm-btn fg__tool", () => rec.source));     // Open in Explorer / Open in graph are added once the data says whether the focus is a file or a folder
    rec.tools = tools;
  } else if (fig.type === "archify") {
    rec.size = { w: fig.size[0] + 16, h: fig.size[1] + ARCHIFY_PAD };
    rec.iframe = h("iframe", { class: "fg__iframe", src: archifyUrl(fig.src, F.theme), loading: "lazy", tabindex: "-1", "aria-hidden": "true", title: fig.alt });
    const frame = h("div", { class: "fg__frame", role: "img", "aria-label": fig.alt, style: `--fig-r:${ratioOf(fig.size)};--fig-w:${fig.size[0]};--fig-h:${fig.size[1]}` }, rec.iframe);
    const hit = h("button", { class: "fg__hit", type: "button", tabindex: "-1", "aria-hidden": "true", onclick: () => openViewer(rec) });   // the whole preview is a click target (keyboard users have the Expand button)
    rec.canvas.append(frame, hit);
    tools.append(h("a", { class: "mm-btn fg__tool", href: fig.src, target: "_blank", rel: "noopener" }, h("span", { html: ICON.open }), h("span", {}, "Open interactive diagram")));
    rec.print = h("p", { class: "fg__print" }, `Interactive diagram: ${new URL(fig.src, location.href).href}`);
  } else {
    rec.holder = h("div", { class: "fg__svg", role: "img", "aria-label": fig.alt });
    rec.canvas.append(rec.holder);
    tools.append(copyButton("mm-btn fg__tool", () => rec.source));
    if (fig.type === "svg") safe(`svg ${fig.id}`, () => loadSvg(rec)); else rec.holder.append(h("p", { class: "fg__wait" }, "Diagram loads as you scroll to it."));
  }
  rec.el.append(rec.canvas, h("figcaption", { class: "mm-figure__caption fg__cap" }, rec.numEl, h("span", { class: "fg__text" }, fig.caption), tools), rec.print || "");
  return rec;
}

/* ------------------------------------------------------------------ svg */
async function loadSvg(rec) {
  let text = rec.fig.code;
  try {
    if (!text) {
      const r = await fetch(new URL(rec.fig.src, BASE));
      if (!r.ok) throw new Error(`${rec.fig.src}: HTTP ${r.status}`);
      text = await r.text();
    }
    if (!svgLooksSafe(text)) throw new Error("the SVG contains something that is not allowed (script, event handler, external reference...)");
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    const node = doc.documentElement;
    if (!node || node.nodeName.toLowerCase() !== "svg" || doc.querySelector("parsererror")) throw new Error("the SVG is not well-formed");
    showSvg(rec, document.importNode(node, true), text);
  } catch (err) { fail(rec, err, text); }
}
function showSvg(rec, svg, source) {
  rec.size = svgSize({ viewBox: svg.getAttribute("viewBox"), width: svg.getAttribute("width"), height: svg.getAttribute("height") });
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  if (!svg.getAttribute("viewBox")) svg.setAttribute("viewBox", `0 0 ${rec.size.w} ${rec.size.h}`);
  rec.holder.replaceChildren(svg);
  rec.svg = svg;
  rec.source = source;
  rec.rendered = true;
}
function fail(rec, err, source) {
  console.warn(`[atlas figures] ${rec.fig.id}:`, err);
  rec.failed = true;
  rec.expand.disabled = true;
  const body = [h("p", { class: "fg__failmsg" }, "This figure could not be drawn.")];
  if (source) body.push(h("details", {}, h("summary", {}, "Show source"), h("pre", {}, source)));
  (rec.holder || rec.canvas).replaceChildren(h("div", { class: "fg__fail" }, ...body));
}

/* ------------------------------------------------------------------ mermaid (library loaded on first use) */
/* An arch figure draws itself with assets/js/arch/render.js (loaded only when a chapter has one), embedded: no toolbar, the details card under the diagram. */
async function renderArch(rec) {
  try {
    if (!document.querySelector('link[data-arch-css]')) {
      const link = h("link", { rel: "stylesheet", href: new URL("assets/css/arch.css", BASE).href, "data-arch-css": "" });
      await new Promise((ok) => { link.addEventListener("load", ok, { once: true }); link.addEventListener("error", ok, { once: true }); document.head.append(link); });
    }
    const { mountArch } = await import("./arch/render.js");
    const ctl = await mountArch(rec.holder, { view: rec.fig.view, flow: rec.fig.flow || "", focus: rec.fig.focus || "", embed: true });
    if (!ctl) throw new Error(`view "${rec.fig.view}" could not be loaded`);
    rec.ctl = ctl;
    const [w, hh] = ctl.size();
    rec.size = { w, h: hh };
    rec.source = ctl.mermaid();
    rec.expand.disabled = false;
  } catch (err) { fail(rec, err, null); }
}
/* A graph-slice figure: the neighbourhood of one file or folder, drawn as SVG by graphslice.js from data/graph/file-links.json. The SVG
   paints with the page's tokens, so the theme needs no redraw; its links are real <a>s, and a list of the same links sits under it
   for keyboard and screen-reader users (the SVG itself is aria-hidden like every figure). */
async function renderSlice(rec) {
  try {
    const { loadSlice, explorerHref, viewerHref } = await import("./graphslice.js");
    const { model, svg, note } = await loadSlice(rec.fig, BASE);
    const node = new DOMParser().parseFromString(svg, "image/svg+xml").documentElement;     // generated here from escaped data, so it skips the author-SVG safety check
    if (!node || node.nodeName.toLowerCase() !== "svg") throw new Error("the diagram could not be built");
    showSvg(rec, document.importNode(node, true), svg);
    const items = [model.centre, ...model.nodes].map((n, i) => h("li", {}, h("a", { href: explorerHref(n.kind, n.path) }, n.path), i === 0 ? " (this one)" : ` \u2014 ${n.links} link${n.links === 1 ? "" : "s"}${n.kind === "folder" ? `, ${n.files} file${n.files === 1 ? "" : "s"}` : ""}`));
    rec.canvas.append(h("details", { class: "fg__slicelist" }, h("summary", {}, `List the ${model.nodes.length} neighbour${model.nodes.length === 1 ? "" : "s"}`), h("ul", {}, ...items), h("p", { class: "fg__slicenote" }, note)));
    const where = explorerHref(model.centre.kind, model.centre.path);
    rec.tools.append(h("a", { class: "mm-btn fg__tool", href: where }, h("span", { html: ICON.open }), h("span", {}, "Open in Explorer")),
                     h("a", { class: "mm-btn fg__tool", href: viewerHref(model.centre.path), target: "_blank", rel: "noopener" }, h("span", { html: ICON.open }), h("span", {}, "Open in graph")));
    rec.print = rec.print || h("p", { class: "fg__print" }, `Explorer: ${new URL(where, location.href).href}`);
    rec.el.append(rec.print);
    rec.expand.disabled = false;
  } catch (err) { fail(rec, err, null); }
}
function lazyRender() {
  const todo = F.recs.filter((r) => r.kind === "mermaid" || r.kind === "arch" || r.kind === "graph-slice");
  if (!todo.length) return;
  const run = (rec) => { if (!rec.queued) { rec.queued = true; if (rec.kind === "arch") renderArch(rec); else if (rec.kind === "graph-slice") renderSlice(rec); else renderMermaid(rec); } };
  if (!("IntersectionObserver" in window)) { todo.forEach(run); return; }
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { io.unobserve(e.target); run(todo.find((r) => r.el === e.target)); }
  }, { rootMargin: "500px 0px" });
  todo.forEach((r) => io.observe(r.el));
}
function loadMermaid() {
  if (F.mermaid) return F.mermaid;
  F.mermaid = new Promise((resolve, reject) => {
    if (window.mermaid) { resolve(window.mermaid); return; }
    const s = h("script", { src: new URL(MERMAID_SRC, BASE).href, async: true });
    s.addEventListener("load", () => (window.mermaid ? resolve(window.mermaid) : reject(new Error("the script loaded but defines no mermaid"))), { once: true });
    s.addEventListener("error", () => reject(new Error(`could not load ${MERMAID_SRC}; run: python scripts/vendor_mermaid.py`)), { once: true });
    document.head.append(s);
  });
  F.mermaid.catch(() => { F.mermaid = null; });
  return F.mermaid;
}
/* Mermaid is not safe to run twice at once, so renders are queued. */
function renderMermaid(rec) {
  F.queue = F.queue.then(async () => {
    let code = rec.fig.code;
    try {
      if (!code) {
        const r = await fetch(new URL(rec.fig.src, BASE));
        if (!r.ok) throw new Error(`${rec.fig.src}: HTTP ${r.status}`);
        code = await r.text();
      }
      const m = await loadMermaid();
      const cs = getComputedStyle(root);
      const get = (n) => cs.getPropertyValue(n).trim();
      m.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base", themeVariables: mermaidThemeVariables(get), fontFamily: get("--font-ui") });
      const { svg } = await m.render(`mm-mmd-${rec.fig.id}-${++F.n}`, withSemanticClasses(code, get));
      const tpl = document.createElement("template");
      tpl.innerHTML = svg;                                             // already sanitised by Mermaid (securityLevel: strict)
      const node = tpl.content.querySelector("svg");
      if (!node) throw new Error("Mermaid returned no SVG");
      node.removeAttribute("style");
      showSvg(rec, node, code);
    } catch (err) { fail(rec, err, code); }
  });
  return F.queue;
}

/* ------------------------------------------------------------------ theme */
function onTheme(next) {
  F.theme = next === "paper" ? "paper" : "dark";
  for (const rec of F.recs) {
    if (rec.kind === "archify" && rec.iframe) rec.iframe.src = archifyUrl(rec.fig.src, F.theme);
    else if (rec.kind === "mermaid" && rec.queued && !rec.failed) renderMermaid(rec);   // an arch figure follows the page's CSS variables: nothing to redo
  }
}

/* ------------------------------------------------------------------ the viewer (Expand) */
function viewerContent(rec) {
  if (rec.kind === "arch") {                                           // a copy of what is drawn now: the lightbox gives it zoom and pan
    const live = rec.ctl && rec.ctl.svg();
    if (!live) return null;
    const c = live.cloneNode(true);
    c.removeAttribute("style");
    rec.size = { w: +live.dataset.w || rec.size.w, h: +live.dataset.h || rec.size.h };
    c.setAttribute("width", String(rec.size.w));
    c.setAttribute("height", String(rec.size.h));
    return { node: c, size: rec.size };
  }
  if (rec.kind === "archify") {
    const f = h("iframe", { class: "mm-lb__iframe", src: archifyUrl(rec.fig.src, F.theme), tabindex: "-1", "aria-hidden": "true", title: rec.fig.alt, style: `width:${rec.size.w}px;height:${rec.size.h}px` });
    return { node: f, size: rec.size, iframe: f };
  }
  if (!rec.svg) return null;
  const c = rec.svg.cloneNode(true);
  c.removeAttribute("style");
  c.setAttribute("width", String(rec.size.w));
  c.setAttribute("height", String(rec.size.h));
  return { node: c, size: rec.size };
}

function openViewer(rec) {
  if (F.lb || rec.failed) return;
  const content = viewerContent(rec);
  if (!content) return;
  const opener = document.activeElement;
  const size = content.size;
  const st = { k: 1, x: 0, y: 0 };
  let fit = { k: 1, x: 0, y: 0 }, minK = 0.1, touched = false;

  const wrap = h("div", { class: "mm-lb__content", style: `width:${size.w}px;height:${size.h}px` }, content.node);
  const stage = h("div", { class: "mm-lb__stage", tabindex: "0", "aria-label": "Figure viewer. Drag to pan, scroll or pinch to zoom, arrow keys pan, plus and minus zoom, 0 fits the window." }, wrap);
  const readout = h("span", { class: "mm-lb__zoom", "aria-live": "off" }, "100%");
  const btn = (icon, label, fn, extra = "") => h("button", { class: `mm-btn mm-btn--icon mm-lb__b${extra}`, type: "button", "aria-label": label, title: label, onclick: fn, html: icon });
  const box = () => { const r = stage.getBoundingClientRect(); return { w: r.width, h: r.height }; };
  const apply = () => { wrap.style.transform = `translate(${st.x}px, ${st.y}px) scale(${st.k})`; readout.textContent = `${Math.round(st.k * 100)}%`; };
  const set = (t) => { Object.assign(st, keepVisible(t, box(), size)); apply(); };
  const center = () => { const b = box(); return { x: b.w / 2, y: b.h / 2 }; };
  const zoom = (factor, at = center()) => { touched = true; set(zoomAt(st, factor, at.x, at.y, minK)); };
  const doFit = () => { touched = false; const b = box(); fit = fitTransform(b, size); minK = Math.min(fit.k, 1) * 0.5; Object.assign(st, fit); apply(); };
  const actual = () => { touched = true; const c = center(); set(zoomAt(st, 1 / st.k, c.x, c.y, minK)); };

  const tools = [
    btn(ICON.minus, "Zoom out (-)", () => zoom(1 / 1.25)), readout, btn(ICON.plus, "Zoom in (+)", () => zoom(1.25)),
    h("button", { class: "mm-btn mm-lb__b", type: "button", title: "Fit to window (0)", onclick: doFit }, h("span", { html: ICON.fit }), h("span", {}, "Fit")),
  ];
  if (rec.kind === "archify") tools.push(h("a", { class: "mm-btn mm-lb__b", href: rec.fig.src, target: "_blank", rel: "noopener" }, h("span", { html: ICON.open }), h("span", {}, "Open interactive")));
  else tools.push(copyButton("mm-btn mm-lb__b", () => rec.source));
  const close = btn(ICON.close, "Close (Esc)", () => closeViewer(), " mm-lb__close");

  const bar = h("div", { class: "mm-lb__bar" },
    h("div", { class: "mm-lb__title" }, h("b", {}, rec.label), h("span", {}, rec.fig.caption)),
    h("div", { class: "mm-lb__tools" }, ...tools, close));
  const lb = h("div", { class: "mm-lb", role: "dialog", "aria-modal": "true", "aria-label": `${rec.label}: ${rec.fig.caption}` }, bar, stage,
    h("p", { class: "mm-lb__hint" }, "Drag to pan \u00b7 scroll or pinch to zoom \u00b7 + \u2212 0 1 keys \u00b7 Esc closes"));

  // everything behind the viewer is inert while it is open (the palette and toasts are left alone)
  const inerted = [...document.body.children].filter((n) => n !== lb && !n.hasAttribute("inert") && !n.matches(".mmp-backdrop, .mm-toasts"));
  inerted.forEach((n) => n.setAttribute("inert", ""));
  document.body.append(lb);
  root.classList.add("mm-lb-open");
  F.lb = lb;

  // pan (one pointer), pinch (two), wheel, double click
  const pts = new Map();
  stage.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    try { stage.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    stage.classList.add("is-drag");
  });
  stage.addEventListener("pointermove", (e) => {
    const prev = pts.get(e.pointerId);
    if (!prev) return;
    const cur = { x: e.clientX, y: e.clientY };
    touched = true;
    if (pts.size === 1) set({ k: st.k, x: st.x + cur.x - prev.x, y: st.y + cur.y - prev.y });
    else if (pts.size === 2) {
      const [ida, idb] = [...pts.keys()], a0 = pts.get(ida), b0 = pts.get(idb);
      const p = pinchStep(a0, b0, e.pointerId === ida ? cur : a0, e.pointerId === idb ? cur : b0);
      const r = stage.getBoundingClientRect();
      const t = zoomAt(st, p.factor, p.from.x - r.left, p.from.y - r.top, minK);
      set({ k: t.k, x: t.x + p.dx, y: t.y + p.dy });
    }
    pts.set(e.pointerId, cur);
  });
  const release = (e) => { pts.delete(e.pointerId); if (!pts.size) stage.classList.remove("is-drag"); };
  stage.addEventListener("pointerup", release);
  stage.addEventListener("pointercancel", release);
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoom(wheelFactor(e.deltaY, e.deltaMode, e.ctrlKey), { x: e.clientX - r.left, y: e.clientY - r.top });
  }, { passive: false });
  stage.addEventListener("dblclick", () => (Math.abs(st.k - fit.k) < 0.01 ? actual() : doFit()));

  const onKey = (e) => {
    if (document.querySelector(".mmp-backdrop:not([hidden])")) return;   // the command palette is on top: it owns the keys
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeViewer(); return; }
    if (e.key === "Tab") {
      const f = [...lb.querySelectorAll("button:not([disabled]), a[href], [tabindex='0']")];
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const pan = (dx, dy) => { e.preventDefault(); touched = true; set({ k: st.k, x: st.x + dx, y: st.y + dy }); };
    if (e.key === "+" || e.key === "=") { e.preventDefault(); zoom(1.25); }
    else if (e.key === "-" || e.key === "_") { e.preventDefault(); zoom(1 / 1.25); }
    else if (e.key === "0" || e.key === "f") { e.preventDefault(); doFit(); }
    else if (e.key === "1") { e.preventDefault(); actual(); }
    else if (e.key === "ArrowLeft") pan(48, 0);
    else if (e.key === "ArrowRight") pan(-48, 0);
    else if (e.key === "ArrowUp") pan(0, 48);
    else if (e.key === "ArrowDown") pan(0, -48);
  };
  const onResize = () => { if (!touched) doFit(); else set(st); };
  const onViewerTheme = (e) => { if (content.iframe) content.iframe.src = archifyUrl(rec.fig.src, e.detail === "paper" ? "paper" : "dark"); };
  document.addEventListener("keydown", onKey, true);
  window.addEventListener("resize", onResize);
  document.addEventListener("minime:theme", onViewerTheme);

  F.lb.close = () => {
    document.removeEventListener("keydown", onKey, true);
    window.removeEventListener("resize", onResize);
    document.removeEventListener("minime:theme", onViewerTheme);
    inerted.forEach((n) => n.removeAttribute("inert"));
    root.classList.remove("mm-lb-open");
    lb.remove();
    F.lb = null;
    const back = opener && opener.isConnected ? opener : rec.expand;
    if (back && back.focus) back.focus({ preventScroll: true });
  };
  doFit();
  stage.focus({ preventScroll: true });
}
function closeViewer() { if (F.lb && F.lb.close) F.lb.close(); }
