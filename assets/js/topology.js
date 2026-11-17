/* MiniMe Atlas 2 - Live topology (P08). One ES module, no dependencies. Loaded by index.html; draws into <div data-topology>.

   The diagram is curated, the numbers are live:
     content/topology.json         the layout: groups (your machine / contract / browser / server), nodes with the real folders each one
                                   stands for, the edges worth drawing, and which node is a child of which (the M2C client opens up)
     data/index/vitals.json        census.topology: code lines, files, functions and docstring coverage per node (refresh_atlas.py);
                                   census and graph commits and dates, for the freshness line
     data/graph/folders.json       graph links between folders (refresh_graph.py): they set the width of every solid line
     content/system/request-path.json   the "request path" highlight: each step's code files say which nodes it touches
     data/index/stats.json         the MiniMe commit, so folder links on GitHub point at the source that was indexed

   Box size = code lines. Line width = graph links between the two parts. A dashed line is a relationship declared in topology.json
   because the graph has no links across it (HTTP, a WebSocket, an approval). Nothing here is a number typed by hand.
   Add ?edit=1 to the page address to drag boxes and copy the new layout as JSON.
   Pure helpers are exported so scripts/test_topology.py can run them in Node with no browser. */

import { fmtN, fmtDate } from "./library.js";

const GITHUB = "https://github.com/Unavailable4u/MiniMe";
const BASE = typeof document !== "undefined" ? new URL("../../", import.meta.url) : null;

/* ================================================================== pure helpers (no DOM) */

export { fmtN, fmtDate };

export const BOX = { w0: 112, w1: 156, h0: 44, h1: 60 };      // a box grows from w0 x h0 to w1 x h1 with its code lines
export const CHILD = { w: 72, h: 42 };                          // the parts of an opened node are all the same height; the width grows if a label needs it
export const LABEL_PAD = 10;                                    // room left and right of a label inside a box
export const KID_PAD = 6;                                       // the same for the small parts, which sit in a tight grid
export const ZOOM = { min: 1, max: 4, step: 1.25 };

export const sameCommit = (a, b) => !!a && !!b && (String(a).startsWith(String(b)) || String(b).startsWith(String(a)));

/* 18638 -> "18.6k", 640 -> "640", 120400 -> "120k". */
export function fmtK(n) {
  n = Number(n) || 0;
  if (n < 1000) return String(n);
  return n < 100000 ? `${(Math.round(n / 100) / 10).toFixed(1)}k` : `${Math.round(n / 1000)}k`;
}

/* Box size from code lines: the area grows with the lines, so the root is used. max is the largest node's lines. */
export function nodeSize(code, max) {
  const t = max > 0 ? Math.sqrt(Math.max(0, code || 0) / max) : 0;
  return { w: Math.round(BOX.w0 + (BOX.w1 - BOX.w0) * t), h: Math.round(BOX.h0 + (BOX.h1 - BOX.h0) * t) };
}

/* Line width from graph links, logarithmic because the counts run from 1 to 500+. No links: a thin dashed line. */
export function edgeWidth(links, max) {
  if (!(links > 0) || !(max > 0)) return 1.5;
  return Math.round((1.5 + 8.5 * Math.log1p(links) / Math.log1p(max)) * 10) / 10;
}

/* Box width: the size from code lines, or wider when the widest text (measured in diagram units) would not fit with pad each side. */
export const fitWidth = (w, textWidth, pad = LABEL_PAD) => Math.max(w, Math.ceil((Number(textWidth) || 0) + 2 * pad));

export const clampZoom = (z) => Math.min(ZOOM.max, Math.max(ZOOM.min, Math.round((Number(z) || 1) * 100) / 100));

/* The node a folder belongs to: the longest "folders" prefix wins. `nodes` is the list to choose from (the top-level ones). */
export function nodeOf(folder, nodes) {
  let best = null, len = -1;
  for (const n of nodes) for (const f of n.folders || []) {
    if ((folder === f || folder.startsWith(f + "/")) && f.length > len) { best = n.id; len = f.length; }
  }
  return best;
}

/* Directed link counts between nodes, from folder pairs [from, to, n]. Links inside a node and links to a folder no node claims are dropped. */
export function linkWeights(pairs, nodes) {
  const w = new Map();
  for (const [a, b, n] of pairs || []) {
    const na = nodeOf(a, nodes), nb = nodeOf(b, nodes);
    if (na && nb && na !== nb) w.set(`${na}>${nb}`, (w.get(`${na}>${nb}`) || 0) + n);
  }
  return w;
}

/* Each edge of the spec with its live numbers: fwd (from -> to), bwd, links (both ways) and live (the graph has links across it). */
export function edgeRows(edges, pairs, nodes) {
  const w = linkWeights(pairs, nodes);
  return (edges || []).map((e) => {
    const fwd = w.get(`${e.from}>${e.to}`) || 0, bwd = w.get(`${e.to}>${e.from}`) || 0;
    return { ...e, fwd, bwd, links: fwd + bwd, live: fwd + bwd > 0 };
  });
}

/* Everything the drawing needs, in one object. spec = topology.json, counts = vitals.census.topology, folders = folders.json. */
export function buildModel(spec, counts, folders) {
  const nodes = (spec.nodes || []).map((n) => ({ ...(counts && counts[n.id] || {}), ...n, parent: n.parent || null }));
  const top = nodes.filter((n) => !n.parent);
  const maxCode = Math.max(1, ...top.map((n) => n.code || 0));
  const kidMax = Math.max(1, ...nodes.filter((n) => n.parent).map((n) => n.code || 0));
  const rows = edgeRows(spec.edges, folders && folders.pairs, top);
  const maxLinks = Math.max(0, ...rows.map((r) => r.links));
  const edges = rows.map((r) => ({ ...r, width: r.live ? edgeWidth(r.links, maxLinks) : 1.5 }));
  const io = new Map(nodes.map((n) => [n.id, { in: 0, out: 0 }]));
  for (const r of rows) { io.get(r.from).out += r.fwd; io.get(r.to).in += r.fwd; io.get(r.from).in += r.bwd; io.get(r.to).out += r.bwd; }
  return { nodes, top, byId: new Map(nodes.map((n) => [n.id, n])), maxCode, kidMax, edges, maxLinks, io };
}

/* Where a line from the middle of rect a towards (tx, ty) leaves it. Rects are {x, y, w, h} with x, y the centre. */
export function clipToRect(r, tx, ty) {
  const dx = tx - r.x, dy = ty - r.y;
  if (!dx && !dy) return { x: r.x, y: r.y };
  const t = Math.min(dx ? r.w / 2 / Math.abs(dx) : Infinity, dy ? r.h / 2 / Math.abs(dy) : Infinity);
  return { x: r.x + dx * t, y: r.y + dy * t };
}

/* The SVG path of an edge between two rects. bend (optional) pushes the middle of the line sideways, in diagram units.
   at (0..1, default the middle) is where along the line, from a to b, the label sits: mid is that point. */
export function edgePath(a, b, bend = 0, at = 0.5) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
  const cx = mx + (-(b.y - a.y) / len) * bend, cy = my + ((b.x - a.x) / len) * bend;
  const p = clipToRect(a, bend ? cx : b.x, bend ? cy : b.y), q = clipToRect(b, bend ? cx : a.x, bend ? cy : a.y);
  const r = (v) => Math.round(v * 10) / 10;
  const t = Math.min(1, Math.max(0, Number.isFinite(at) ? at : 0.5)), u = 1 - t;
  const mid = bend
    ? { x: u * u * p.x + 2 * u * t * cx + t * t * q.x, y: u * u * p.y + 2 * u * t * cy + t * t * q.y }
    : { x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t };
  return { d: bend ? `M${r(p.x)} ${r(p.y)}Q${r(cx)} ${r(cy)} ${r(q.x)} ${r(q.y)}` : `M${r(p.x)} ${r(p.y)}L${r(q.x)} ${r(q.y)}`, mid: { x: r(mid.x), y: r(mid.y) } };
}

/* The box around the opened parts of a node: their bounding box plus a margin, with extra room on top for the title. */
export function frameRect(kids, pad = 12, title = 26) {
  if (!kids.length) return null;
  const x0 = Math.min(...kids.map((k) => k.x - k.w / 2)) - pad, x1 = Math.max(...kids.map((k) => k.x + k.w / 2)) + pad;
  const y0 = Math.min(...kids.map((k) => k.y - k.h / 2)) - pad - title, y1 = Math.max(...kids.map((k) => k.y + k.h / 2)) + pad;
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0 };
}

/* "Request path": each step of request-path.json touches the nodes whose folders hold its code. -> [{id, title, nodes: [node ids in order]}] */
export function stepNodes(steps, nodes) {
  return (steps || []).map((s) => {
    const ids = [];
    for (const c of s.code || []) {
      const id = nodeOf(c.path, nodes);
      if (id && !ids.includes(id)) ids.push(id);
    }
    return { id: s.id, title: s.title, what: s.what, nodes: ids };
  });
}

/* The whole path as one list of node ids: every step's nodes in order, a repeat of the node just before it dropped. */
export function pathSequence(stepList) {
  const out = [];
  for (const s of stepList) for (const id of s.nodes) if (out[out.length - 1] !== id) out.push(id);
  return out;
}

/* Arrow keys: the nearest node in a direction ("left", "right", "up", "down"), or null. Candidates are {id, x, y}. */
export function nearestInDirection(cands, fromId, dir) {
  const from = cands.find((c) => c.id === fromId);
  if (!from) return null;
  const v = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] }[dir];
  if (!v) return null;
  let best = null, bestScore = Infinity;
  for (const c of cands) {
    if (c.id === fromId) continue;
    const dx = c.x - from.x, dy = c.y - from.y, along = dx * v[0] + dy * v[1], across = Math.abs(dx * v[1] + dy * v[0]);
    if (along <= 0) continue;
    const score = along + 2 * across;
    if (score < bestScore) { best = c.id; bestScore = score; }
  }
  return best;
}

/* "82 % of 461 Python functions have a docstring", or why there is no figure. */
export function docsLabel(documented, pyFunctions) {
  if (!pyFunctions) return "No Python functions here, so no docstring figure.";
  return `${Math.round((documented / pyFunctions) * 100)} % of ${fmtN(pyFunctions)} Python functions have a docstring.`;
}

/* explore.html opens a file from its hash. It cannot open a folder yet (P13), so a node links to its largest source file. */
export const explorerHref = (path) => `explore.html#${encodeURIComponent(path)}`;

export const githubTree = (folder, commit) => `${GITHUB}/tree/${commit || "main"}/${String(folder).split("/").map(encodeURIComponent).join("/")}`;

/* "doc-minime-feature-guide#5-the-agent-system" -> "doc-minime-feature-guide.html#5-the-agent-system" */
export const chapterHref = (ref) => { const [id, frag] = String(ref).split("#"); return `${id}.html${frag ? "#" + frag : ""}`; };

/* The two commits and days the picture rests on, as a line. state "stale" when the graph and the census describe different commits. */
export function sourceLine(census, graph) {
  const c = census || {}, g = graph || {};
  const parts = [], notes = [];
  if (c.commit) parts.push(`Sizes: census of MiniMe ${String(c.commit).slice(0, 7)}, ${fmtDate(c.generated)}`);
  if (g.commit) parts.push(`Line widths: ${g.source === "seed" ? "the Graph page's folder table" : "graph"} of ${g.commit}, ${fmtDate(g.date)}`);
  if (g.source === "seed") notes.push("These widths are an approximation from the 14 busiest folders on the Graph page. The next update_all.py run replaces them with the full graph.");
  const stale = !!(c.commit && g.commit && !sameCommit(c.commit, g.commit));
  if (stale) notes.push(`The census (${String(c.commit).slice(0, 7)}) and the graph (${g.commit}) describe different commits, so a size and a width can disagree.`);
  if (!parts.length) notes.push("The numbers could not be loaded, so boxes are all the same size.");
  return { text: parts.join(" · "), notes, state: stale || (g.source === "seed") || !parts.length ? "stale" : "fresh" };
}

/* The layout as the text of content/topology.json after dragging: only x and y change, every other key keeps its place. */
export function exportSpec(spec, pos) {
  const out = JSON.parse(JSON.stringify(spec));
  for (const n of out.nodes || []) {
    const p = pos[n.id];
    if (p) { n.x = Math.round(p.x); n.y = Math.round(p.y); }
  }
  return JSON.stringify(out, null, 2) + "\n";
}

/* ================================================================== DOM */

const NS = "http://www.w3.org/2000/svg";
const MQ_SHEET = "(max-width: 959px)";                 // below this the details card is a bottom sheet and hover does nothing
const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

function h(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
    else n.setAttribute(k, v === true ? "" : v);
  }
  n.append(...kids.flat().filter((c) => c != null && c !== false).map((c) => (c.nodeType ? c : document.createTextNode(String(c)))));
  return n;
}

/* parent.replaceChildren(...kids), minus the null / false entries a conditional leaves behind: replaceChildren(null) writes the text "null". */
export const liveKids = (kids) => kids.flat(Infinity).filter((c) => c != null && c !== false);
function put(parent, ...kids) { parent.replaceChildren(...liveKids(kids)); }

function svg(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  for (const c of kids) if (c != null) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}
const soft = (rel) => getJSON(rel).catch((err) => { console.warn("[atlas topology]", err); return null; });

const S = {
  spec: null, vitals: null, folders: null, steps: null, stats: {}, model: null, stepList: [],
  pos: {}, fit: new Map(), expanded: false, selected: null, preview: null, path: { on: false, step: -1 }, edit: false, zoom: 1,
};
const E = { root: null, wrap: null, stage: null, svg: null, card: null, nodes: new Map(), edges: [], frame: null, pathLayer: null, groups: null };

const isSheet = () => matchMedia(MQ_SHEET).matches;
/* The nodes drawn now: every top-level node, and the parts of an opened one (the opened node itself becomes a frame). */
function drawn() {
  const out = [];
  for (const n of S.model.nodes) {
    if (!n.parent) out.push(n);
    else if (S.expanded && S.model.byId.get(n.parent)) out.push(n);
  }
  return out;
}

const isOpened = (n) => S.expanded && (n.children || []).length > 0;

function rectOf(n) {
  const p = S.pos[n.id], fit = S.fit.get(n.id) || 0;
  if (n.parent) return { x: p.x, y: p.y, w: fitWidth(CHILD.w, fit, KID_PAD), h: CHILD.h };
  const sz = nodeSize(n.code, S.model.maxCode);
  return { x: p.x, y: p.y, w: fitWidth(sz.w, fit), h: sz.h };
}

/* Measure every label as drawn, which depends on the font the browser resolved, and widen the boxes that are too narrow.
   Run after drawing and again when the web fonts arrive. */
function fitLabels() {
  const next = new Map();
  for (const [id, el] of E.nodes) {
    const t = el.querySelector(".tp-label"), s = el.querySelector(".tp-sub");
    const w = Math.max(t ? t.getComputedTextLength() : 0, s ? s.getComputedTextLength() : 0);
    if (w > 0) next.set(id, w);
  }
  const same = next.size === S.fit.size && [...next].every(([id, w]) => Math.abs((S.fit.get(id) || 0) - w) < 0.5);
  if (same) return;
  S.fit = next;
  for (const [id, el] of E.nodes) {
    const n = S.model.byId.get(id), r = rectOf(n), box = el.querySelector("rect.tp-box"), bar = el.querySelector("rect.tp-bar");
    box.setAttribute("x", -r.w / 2); box.setAttribute("width", r.w);
    if (bar) { bar.setAttribute("x", -r.w / 2 + 6); bar.setAttribute("width", Math.max(2, (r.w - 12) * (n.code / S.model.kidMax))); }
  }
  place();
  applyState();                                           // the numbered badges sit on the box's right edge
}

function frameOf(n) {
  return frameRect((n.children || []).map((id) => S.model.byId.get(id)).filter(Boolean).map(rectOf));
}

/* The rect a line attaches to: an opened node's frame (or the one part the edge names), else its box. */
function endRect(id, child) {
  const n = S.model.byId.get(id);
  if (!isOpened(n)) return rectOf(n);
  const kid = child && S.model.byId.get(child);
  return kid ? rectOf(kid) : frameOf(n);
}

/* ---- details card */
function fact(label, value) { return [h("dt", {}, label), h("dd", {}, value)]; }

function cardBody(n, pinned) {
  const m = S.model, kids = (n.children || []).length > 0, io = m.io.get(n.id) || { in: 0, out: 0 };
  const parent = n.parent && m.byId.get(n.parent);
  const commit = (S.vitals && S.vitals.commit) || S.stats.commit || "main";
  const facts = h("dl", { class: "tp-facts" },
    fact("Folders", (n.folders || []).map((f) => h("code", {}, f))),
    n.files != null ? fact("Size", `${fmtN(n.code || 0)} code lines in ${fmtN(n.files)} files, ${fmtN(n.functions || 0)} functions`) : null,
    n.files != null ? fact("Docstrings", docsLabel(n.documented, n.python_functions)) : null,
    !n.parent ? fact("Graph links", io.in + io.out > 0 ? `${fmtN(io.in)} in, ${fmtN(io.out)} out, counted on the solid lines` : "none on the lines drawn here") : null);
  const links = [];
  if (pinned) {
    const top = n.top || [];
    if (top[0]) links.push(h("a", { class: "mm-btn mm-btn--primary", href: explorerHref(top[0].path) }, "Open in the Explorer: ", h("code", {}, top[0].path.split("/").pop())));
    if (n.chapter) links.push(h("a", { class: "mm-btn", href: chapterHref(n.chapter) }, "Read it in the book"));
    if (n.diagram) links.push(h("a", { class: "mm-btn", href: n.diagram }, "See its diagram"));
    if (n.folders && n.folders[0]) links.push(h("a", { class: "mm-btn", href: githubTree(n.folders[0], commit), target: "_blank", rel: "noopener" }, "Folder on GitHub"));
    if (kids) links.push(h("button", { class: "mm-btn", type: "button", on: { click: () => setExpanded(!S.expanded) } }, S.expanded ? "Fold its parts" : "Show its parts"));
  }
  const more = pinned && (n.top || []).length > 1
    ? h("p", { class: "tp-more" }, "Largest source files: ", ...n.top.flatMap((t, i) => [i ? ", " : "", h("a", { href: explorerHref(t.path) }, h("code", {}, t.path.split("/").pop()))]))
    : null;
  const hint = pinned ? null : h("p", { class: "tp-hint" }, "Click or press Enter to keep this open and get its links.");
  const note = n.top && pinned ? h("p", { class: "tp-note" }, "The Explorer opens files for now; a link opens the folder's largest file until folders get their own page.") : null;
  return [
    parent ? h("p", { class: "tp-crumb" }, "Part of ", h("button", { class: "tp-linkbtn", type: "button", on: { click: () => select(parent.id) } }, parent.label)) : null,
    h("p", { class: "tp-what" }, n.what), facts, links.length ? h("div", { class: "tp-actions" }, links) : null, more, note, hint,
  ];
}

function showCard() {
  const id = S.selected || S.preview;
  const n = id && S.model.byId.get(id);
  const card = E.card;
  if (!n) {
    card.dataset.state = "idle";
    put(card, h("p", { class: "tp-idle" }, "Hover or focus a box to see what it is. Click one to keep it open. Boxes are drawn from the real folders of the repository."));
    return;
  }
  const pinned = S.selected === id;
  card.dataset.state = pinned ? "pinned" : "preview";
  put(card,
    h("div", { class: "tp-card__head" },
      h("h3", { id: "tp-card-title" }, n.label),
      pinned ? h("button", { class: "mm-btn tp-close", type: "button", "aria-label": "Close the details", on: { click: () => select(null) } }, "Close") : null),
    ...cardBody(n, pinned));
}

/* ---- state -> picture */
function applyState() {
  const seq = S.path.on ? (S.path.step >= 0 ? S.stepList[S.path.step].nodes : pathSequence(S.stepList)) : null;
  const active = seq ? new Set(seq) : null;
  for (const [id, el] of E.nodes) {
    el.classList.toggle("tp-node--sel", S.selected === id);
    el.classList.toggle("tp-node--dim", !!active && !active.has(id));
    el.setAttribute("aria-pressed", S.selected === id ? "true" : "false");
    const badges = el.querySelector(".tp-badges");
    const nums = [];
    if (S.path.on) S.stepList.forEach((s, i) => { if (s.nodes.includes(id) && (S.path.step < 0 || S.path.step === i)) nums.push(i + 1); });
    const box = el.querySelector("rect.tp-box"), bw = +box.getAttribute("width"), bh = +box.getAttribute("height");
    put(badges, ...nums.map((k, i) => svg("g", { transform: `translate(${bw / 2 - 6 - i * 20},${-bh / 2})` },
      svg("circle", { r: 9, class: "tp-badge" }), svg("text", { class: "tp-badge__t", "text-anchor": "middle", y: 4 }, k))));
  }
  for (const e of E.edges) e.path.classList.toggle("tp-edge--dim", !!active && !(active.has(e.edge.from) && active.has(e.edge.to)));
  put(E.pathLayer);
  if (seq && seq.length > 1) {
    for (let i = 1; i < seq.length; i++) {
      const a = S.model.byId.get(seq[i - 1]), b = S.model.byId.get(seq[i]);
      const p = edgePath(endRect(a.id), endRect(b.id));
      E.pathLayer.append(svg("path", { d: p.d, class: `tp-flow${reduced() ? "" : " tp-flow--move"}` }));
    }
  }
  E.svg.dataset.path = S.path.on ? "on" : "off";
  showCard();
  renderPathPanel();
  document.body.dataset.tpSheet = S.selected && isSheet() ? "open" : "closed";
}

function select(id, focus = true) {
  const prev = S.selected;
  S.selected = id;
  applyState();
  if (id && focus) E.card.focus({ preventScroll: true });
  if (!id && prev && E.nodes.get(prev)) E.nodes.get(prev).focus({ preventScroll: true });
}

function preview(id) {
  if (S.selected || (id && isSheet())) return;
  S.preview = id;
  showCard();
}

function setExpanded(on) {
  S.expanded = !!on;
  if (!S.expanded && S.selected && S.model.byId.get(S.selected).parent) S.selected = S.model.byId.get(S.selected).parent;
  draw();
}

/* ---- geometry: positions of boxes, frame and lines; also used while a box is dragged */
function place() {
  for (const [id, el] of E.nodes) {
    const p = S.pos[id];
    el.setAttribute("transform", `translate(${p.x},${p.y})`);
  }
  if (E.frame) {
    const f = E.frame, r = frameOf(S.model.byId.get(f.id));
    f.rect.setAttribute("x", r.x - r.w / 2); f.rect.setAttribute("y", r.y - r.h / 2); f.rect.setAttribute("width", r.w); f.rect.setAttribute("height", r.h);
    f.text.setAttribute("x", r.x - r.w / 2 + 12); f.text.setAttribute("y", r.y - r.h / 2 + 19);
  }
  for (const e of E.edges) {
    const p = edgePath(endRect(e.edge.from, e.edge.from_child), endRect(e.edge.to, e.edge.to_child), e.edge.bend || 0, e.edge.label_t);
    e.path.setAttribute("d", p.d);
    if (e.label) { e.label.setAttribute("x", p.mid.x); e.label.setAttribute("y", p.mid.y - 5); }
  }
}

function edgeTitle(e) {
  const a = S.model.byId.get(e.from).label, b = S.model.byId.get(e.to).label;
  const rel = e.label ? `${e.label}. ` : "";
  if (e.live) return `${a} and ${b}: ${rel}${fmtN(e.links)} graph links (${fmtN(e.fwd)} from ${a} to ${b}, ${fmtN(e.bwd)} back).`;
  return `${a} and ${b}: ${rel}declared here; the graph has no links across it.`;
}

function draw() {
  const m = S.model, [W, H] = S.spec.view || [1000, 640];
  const svgEl = svg("svg", { class: "tp-svg", viewBox: `0 0 ${W} ${H}`, role: "group", "aria-labelledby": "tp-title", "aria-describedby": "tp-keys", preserveAspectRatio: "xMidYMid meet" });
  const groups = svg("g", { class: "tp-groups" });
  for (const g of S.spec.groups || []) {
    groups.append(svg("g", { class: `tp-group tp-group--${g.id}` },
      svg("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14 }),
      svg("text", g.align === "end" ? { x: g.x + g.w - 12, y: g.y + 20, "text-anchor": "end" } : { x: g.x + 12, y: g.y + 20 }, g.label)));
  }
  const edgesLayer = svg("g", { class: "tp-edges" });
  E.edges = [];
  for (const e of m.edges) {
    if (!m.byId.get(e.from) || !m.byId.get(e.to)) continue;
    const cls = ["tp-edge", e.live ? "tp-edge--live" : "tp-edge--declared", e.gate ? "tp-edge--gate" : ""].join(" ");
    const path = svg("path", { class: cls, "stroke-width": e.width }, svg("title", {}, edgeTitle(e)));
    const label = e.label ? svg("text", { class: `tp-edge__l${e.gate ? " tp-edge__l--gate" : ""}`, "text-anchor": "middle" }, e.label) : null;
    edgesLayer.append(path);
    if (label) edgesLayer.append(label);
    E.edges.push({ edge: e, path, label });
  }
  E.pathLayer = svg("g", { class: "tp-pathlayer", "aria-hidden": "true" });
  const nodesLayer = svg("g", { class: "tp-nodes" });
  E.nodes = new Map();
  E.frame = null;
  for (const n of drawn()) {
    if (isOpened(n)) {
      const rect = svg("rect", { class: "tp-frame__r", rx: 12 }), text = svg("text", { class: "tp-frame__t" }, n.label);
      groups.append(svg("g", { class: "tp-frame" }, rect, text));
      E.frame = { id: n.id, rect, text };
      continue;                                         // an opened node is only its frame; its parts are drawn instead
    }
    const r = rectOf(n), kid = !!n.parent, t = kid ? n.code / m.kidMax : 0;
    const g = svg("g", { class: `tp-node${kid ? " tp-node--kid" : ""}${n.gate ? " tp-node--gate" : ""}`, tabindex: 0, role: "button", "data-id": n.id,
      "aria-pressed": "false", "aria-label": `${n.label}${n.files != null ? `, ${fmtN(n.code || 0)} code lines in ${fmtN(n.files)} files` : ""}` },
      svg("rect", { class: "tp-box", x: -r.w / 2, y: -r.h / 2, width: r.w, height: r.h, rx: 9 }),
      svg("text", { class: "tp-label", "text-anchor": "middle", y: kid ? -2 : -3 }, n.label),
      svg("text", { class: "tp-sub", "text-anchor": "middle", y: kid ? 13 : 14 }, n.files != null ? `${fmtK(n.code)} lines` : ""),
      kid ? svg("rect", { class: "tp-bar", x: -r.w / 2 + 6, y: r.h / 2 - 7, width: Math.max(2, (r.w - 12) * t), height: 3, rx: 1.5 }) : null,
      svg("g", { class: "tp-badges" }));
    wireNode(g, n);
    nodesLayer.append(g);
    E.nodes.set(n.id, g);
  }
  svgEl.append(groups, edgesLayer, E.pathLayer, nodesLayer);
  svgEl.addEventListener("keydown", onKeys);
  put(E.stage, svgEl);
  E.svg = svgEl;
  setZoom(S.zoom);
  S.fit = new Map();
  fitLabels();
  place();
  applyState();
  syncExpandButton();
}

function wireNode(g, n) {
  g.addEventListener("pointerenter", (ev) => { if (ev.pointerType === "mouse" && !S.edit) preview(n.id); });
  g.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse") preview(null); });
  g.addEventListener("focus", () => { if (!S.edit) preview(n.id); });
  g.addEventListener("blur", () => preview(null));
  g.addEventListener("click", () => { if (E.dragged) { E.dragged = false; return; } if (!S.edit) select(S.selected === n.id ? null : n.id); });
  g.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); if (!S.edit) select(S.selected === n.id ? null : n.id); }
  });
  g.addEventListener("pointerdown", (ev) => { if (S.edit) startDrag(ev, g, n); });
}

/* Arrow keys move to the nearest box in that direction; Escape closes the card. */
function onKeys(ev) {
  const dir = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" }[ev.key];
  const cur = ev.target.closest && ev.target.closest(".tp-node");
  if (dir && cur) {
    const cands = [...E.nodes].map(([id]) => ({ id, x: S.pos[id].x, y: S.pos[id].y }));
    const next = nearestInDirection(cands, cur.dataset.id, dir);
    if (next) { ev.preventDefault(); E.nodes.get(next).focus(); E.nodes.get(next).scrollIntoView({ block: "nearest", inline: "nearest" }); }
  } else if (ev.key === "Escape" && S.selected) select(null);
}

/* ---- zoom: the SVG is drawn wider inside a box that scrolls, so touch, trackpad and scrollbars all pan it */
function setZoom(z, ax = 0.5, ay = 0.5) {
  const old = S.zoom, st = E.stage;
  const fx = (st.scrollLeft + st.clientWidth * ax) / (st.scrollWidth || 1), fy = (st.scrollTop + st.clientHeight * ay) / (st.scrollHeight || 1);
  S.zoom = clampZoom(z);
  E.svg.style.width = `${S.zoom * 100}%`;
  E.stage.dataset.zoomed = S.zoom > 1 ? "true" : "false";
  if (S.zoom !== old) {
    st.scrollLeft = fx * st.scrollWidth - st.clientWidth * ax;
    st.scrollTop = fy * st.scrollHeight - st.clientHeight * ay;
  }
  const label = E.root.querySelector(".tp-zoomv");
  if (label) label.textContent = `${Math.round(S.zoom * 100)} %`;
  for (const b of E.root.querySelectorAll("[data-zoom]")) b.disabled = (b.dataset.zoom === "in" && S.zoom >= ZOOM.max) || (b.dataset.zoom === "out" && S.zoom <= ZOOM.min) || (b.dataset.zoom === "reset" && S.zoom === 1);
}

function wireStage() {
  const st = E.stage;
  st.addEventListener("wheel", (ev) => {                 // only Ctrl/pinch zooms, so the page still scrolls under the diagram
    if (!ev.ctrlKey && !ev.metaKey) return;
    ev.preventDefault();
    const r = st.getBoundingClientRect();
    setZoom(S.zoom * (ev.deltaY < 0 ? ZOOM.step : 1 / ZOOM.step), (ev.clientX - r.left) / r.width, (ev.clientY - r.top) / r.height);
  }, { passive: false });
  let drag = null;                                       // a mouse drag on empty space scrolls a zoomed diagram
  st.addEventListener("pointerdown", (ev) => {
    if (ev.pointerType !== "mouse" || ev.button !== 0 || S.zoom === 1 || S.edit || ev.target.closest(".tp-node")) return;
    drag = { x: ev.clientX, y: ev.clientY, l: st.scrollLeft, t: st.scrollTop };
    st.setPointerCapture(ev.pointerId);
    st.dataset.drag = "true";
  });
  st.addEventListener("pointermove", (ev) => { if (drag) { st.scrollLeft = drag.l - (ev.clientX - drag.x); st.scrollTop = drag.t - (ev.clientY - drag.y); } });
  const end = () => { drag = null; st.dataset.drag = "false"; };
  st.addEventListener("pointerup", end);
  st.addEventListener("pointercancel", end);
}

/* ---- edit mode (?edit=1): drag the boxes, copy the JSON */
function startDrag(ev, g, n) {
  ev.preventDefault();
  const inv = E.svg.getScreenCTM().inverse();
  const pt = (e) => { const p = E.svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; return p.matrixTransform(inv); };
  const start = pt(ev), orig = { ...S.pos[n.id] };
  E.dragged = false;
  g.setPointerCapture(ev.pointerId);
  const move = (e) => {
    const p = pt(e);
    if (Math.abs(p.x - start.x) + Math.abs(p.y - start.y) > 2) E.dragged = true;
    S.pos[n.id] = { x: Math.round(orig.x + p.x - start.x), y: Math.round(orig.y + p.y - start.y) };
    place();
  };
  const up = () => { g.removeEventListener("pointermove", move); g.removeEventListener("pointerup", up); g.removeEventListener("pointercancel", up); };
  g.addEventListener("pointermove", move);
  g.addEventListener("pointerup", up);
  g.addEventListener("pointercancel", up);
}

async function copyJSON(out) {
  const text = exportSpec(S.spec, S.pos);
  try { await navigator.clipboard.writeText(text); out.textContent = "Copied. Paste it over content/topology.json."; }
  catch {
    const ta = h("textarea", { class: "tp-json", readonly: true, rows: 8, "aria-label": "content/topology.json with the new layout" }, text);
    put(out, "Select all and copy, then paste it over content/topology.json.", ta);
    ta.select();
  }
}

/* ---- request path */
function renderPathPanel() {
  const box = E.root.querySelector(".tp-pathpanel");
  box.hidden = !S.path.on;
  if (!S.path.on) { put(box); return; }
  const list = S.stepList, i = S.path.step, s = list[i];
  const go = (k) => { S.path.step = Math.max(-1, Math.min(list.length - 1, k)); applyState(); };
  put(box,
    h("p", { class: "tp-pathpanel__t" }, i < 0 ? `One chat message touches ${pathSequence(list).length} stops, numbered by step.` : `Step ${i + 1} of ${list.length}: ${s.title}`),
    i >= 0 ? h("p", { class: "tp-pathpanel__w" }, s.what) : null,
    h("div", { class: "tp-pathpanel__nav" },
      h("button", { class: "mm-btn", type: "button", disabled: i < 0, on: { click: () => go(i - 1) } }, i <= 0 ? "All steps" : "Previous"),
      h("button", { class: "mm-btn", type: "button", disabled: i >= list.length - 1, on: { click: () => go(i + 1) } }, i < 0 ? "Start at step 1" : "Next"),
      h("a", { href: "#anatomy" }, "Read the steps below")));
}

function setPath(on) {
  S.path = { on, step: -1 };
  E.root.querySelector("[data-act=path]").setAttribute("aria-pressed", on ? "true" : "false");
  applyState();
}

/* ---- list of all parts: the same facts without the picture */
function renderList() {
  const rows = S.model.nodes.map((n) => {
    const io = S.model.io.get(n.id);
    return h("tr", {},
      h("th", { scope: "row" }, h("button", { class: "tp-linkbtn", type: "button", on: { click: () => { if (n.parent && !S.expanded) setExpanded(true); select(n.id); } } }, n.label), n.parent ? h("span", { class: "tp-dim-t" }, " (part of the M2C client)") : null),
      h("td", {}, (n.folders || []).map((f) => h("code", {}, f))),
      h("td", { class: "n" }, n.files != null ? fmtN(n.code || 0) : "–"),
      h("td", { class: "n" }, n.files != null ? fmtN(n.files) : "–"),
      h("td", { class: "n" }, n.parent ? "–" : fmtN(io.in + io.out)));
  });
  return h("details", { class: "tp-list" },
    h("summary", {}, "All parts as a list"),
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table" },
      h("caption", { class: "tp-cap" }, "Every box in the diagram. Graph links count the solid lines only."),
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Part"), h("th", { scope: "col" }, "Folders"), h("th", { scope: "col", class: "n" }, "Code lines"), h("th", { scope: "col", class: "n" }, "Files"), h("th", { scope: "col", class: "n" }, "Graph links"))),
      h("tbody", {}, rows))));
}

/* ---- the page */
function legend() {
  const sw = (cls) => h("span", { class: `tp-sw ${cls}`, "aria-hidden": "true" });
  return h("ul", { class: "tp-legend" },
    h("li", {}, sw("tp-sw--box"), "Box size: code lines"),
    h("li", {}, sw("tp-sw--live"), "Line width: graph links between the two parts"),
    h("li", {}, sw("tp-sw--decl"), "Dashed: declared here, no graph links across it"),
    h("li", {}, sw("tp-sw--gate"), "Amber: needs your approval"));
}

function toolbar() {
  const kids = S.model.nodes.some((n) => (n.children || []).length);
  const msg = h("span", { class: "tp-msg", role: "status" });
  const btn = (act, text, extra = {}) => h("button", { class: "mm-btn", type: "button", "data-act": act, ...extra }, text);
  const bar = h("div", { class: "tp-bar-row", role: "toolbar", "aria-label": "Diagram controls" },
    btn("path", "Follow one request", { "aria-pressed": "false", on: { click: () => setPath(!S.path.on) } }),
    kids ? btn("expand", "Show the M2C parts", { "aria-pressed": "false", on: { click: () => setExpanded(!S.expanded) } }) : null,
    h("span", { class: "tp-zoom", role: "group", "aria-label": "Zoom" },
      h("button", { class: "mm-btn", type: "button", "data-zoom": "out", "aria-label": "Zoom out", on: { click: () => setZoom(S.zoom / ZOOM.step) } }, "−"),
      h("span", { class: "tp-zoomv", "aria-live": "polite" }, "100 %"),
      h("button", { class: "mm-btn", type: "button", "data-zoom": "in", "aria-label": "Zoom in", on: { click: () => setZoom(S.zoom * ZOOM.step) } }, "+"),
      h("button", { class: "mm-btn", type: "button", "data-zoom": "reset", on: { click: () => setZoom(1) } }, "Reset")));
  if (S.edit) {
    bar.append(h("span", { class: "tp-edit" }, h("b", {}, "Edit mode: "), "drag the boxes, then ",
      h("button", { class: "mm-btn mm-btn--primary", type: "button", on: { click: () => copyJSON(msg) } }, "Copy JSON"),
      h("button", { class: "mm-btn", type: "button", on: { click: () => { S.pos = initialPositions(); place(); applyState(); } } }, "Reset layout")));
  }
  return [bar, msg];
}

function initialPositions() { return Object.fromEntries(S.spec.nodes.map((n) => [n.id, { x: n.x, y: n.y }])); }

function syncExpandButton() {
  const b = E.root.querySelector("[data-act=expand]");
  if (b) { b.setAttribute("aria-pressed", S.expanded ? "true" : "false"); b.textContent = S.expanded ? "Fold the M2C parts" : "Show the M2C parts"; }
}

function fail(root, msg) {
  put(root, h("p", { class: "ov-empty" }, msg, " If you opened this file directly, start the local server: python scripts/serve.py"));
}

async function boot(root) {
  [S.spec, S.vitals, S.folders, S.steps, S.stats] = await Promise.all([
    soft("content/topology.json"), soft("data/index/vitals.json"), soft("data/graph/folders.json"), soft("content/system/request-path.json"), soft("data/index/stats.json")]);
  if (!S.spec || !(S.spec.nodes || []).length) return fail(root, "The diagram could not be loaded.");
  const census = S.vitals && S.vitals.census;
  S.model = buildModel(S.spec, census && census.topology, S.folders);
  S.stepList = stepNodes(S.steps && S.steps.steps, S.model.top);
  S.stats = S.stats || {};
  S.pos = initialPositions();
  S.edit = /[?&]edit=1(&|$)/.test(location.search);
  const src = sourceLine(census, S.folders);
  E.root = root;
  E.stage = h("div", { class: "tp-stage", tabindex: -1 });
  E.card = h("aside", { class: "tp-card", tabindex: -1, "aria-live": "polite", "aria-labelledby": "tp-card-title", "data-state": "idle",
    on: { keydown: (ev) => { if (ev.key === "Escape" && S.selected) { ev.preventDefault(); select(null); } } } });
  E.wrap = h("div", { class: "tp-grid" }, h("div", { class: "tp-stagewrap" }, E.stage), E.card);
  const [bar, msg] = toolbar();
  put(root,
    h("p", { class: "ov-sub", id: "tp-title" }, S.spec.note || "System diagram"),
    h("div", { class: "ov-fresh tp-fresh", "data-state": src.state }, h("p", { class: "tp-fresh__t" }, src.text), ...src.notes.map((t) => h("p", { class: "ov-fresh__why" }, t))),
    bar, msg, h("div", { class: "tp-pathpanel", hidden: true, "aria-live": "polite" }),
    E.wrap,
    h("p", { class: "tp-keys", id: "tp-keys" }, "Keyboard: Tab moves between boxes, the arrow keys jump to the nearest neighbour, Enter keeps a box open, Escape closes it. Zoom with the buttons or Ctrl and the mouse wheel; on a phone, swipe the diagram to move around it."),
    S.spec.not_drawn ? h("p", { class: "tp-keys" }, S.spec.not_drawn) : null,
    legend(), renderList());
  wireStage();
  draw();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (E.svg && E.svg.isConnected) fitLabels(); });
}

if (typeof document !== "undefined") {
  const root = document.querySelector("[data-topology]");
  const start = () => boot(root).catch((err) => { console.warn("[atlas topology]", err); fail(root, "The diagram could not be drawn."); });
  if (root) { if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true }); else start(); }
}
