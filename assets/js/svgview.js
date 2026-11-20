/* MiniMe Atlas 2 - shared SVG viewing helpers (P26). One ES module, no dependencies.

   Factored out of topology.js (P08) so the architecture views (assets/js/arch/*.js) and the topology use the same code for:
     pure     zoom limits, where a line leaves a box, arrow-key neighbours, minimal DOM builders' child filter
     DOM      h() / svg() / put() builders; a zoom controller (buttons, readout, Ctrl+wheel); mouse-drag panning of a zoomed
              diagram; dragging one element (edit mode); the bottom sheet flag; Copy text; Export SVG with the colours resolved
   Nothing here knows about folders, flows or the model. Pure helpers are exported so scripts can run them in Node with no browser. */

/* ================================================================== pure helpers (no DOM) */

export const NS = "http://www.w3.org/2000/svg";
export const MQ_SHEET = "(max-width: 959px)";            // below this a details card is a bottom sheet and hover does nothing
export const ZOOM = { min: 1, max: 4, step: 1.25 };

export const clampZoom = (z) => Math.min(ZOOM.max, Math.max(ZOOM.min, Math.round((Number(z) || 1) * 100) / 100));

/* parent.replaceChildren(...kids), minus the null / false entries a conditional leaves behind: replaceChildren(null) writes the text "null". */
export const liveKids = (kids) => kids.flat(Infinity).filter((c) => c != null && c !== false);

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

/* The pins of content/arch-layout.json after dragging: every other key keeps its place, only x and y of the moved nodes change.
   Same idea as topology.js exportSpec(). `moved` is {id: {x, y}}. */
export function exportPins(layoutJson, moved) {
  const out = JSON.parse(JSON.stringify(layoutJson || {}));
  out.pins = out.pins && typeof out.pins === "object" ? out.pins : {};
  for (const id of Object.keys(moved || {}).sort()) {
    const p = moved[id];
    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) out.pins[id] = { x: Math.round(p.x), y: Math.round(p.y) };
  }
  out.pins = Object.fromEntries(Object.keys(out.pins).sort().map((k) => [k, out.pins[k]]));
  return JSON.stringify(out, null, 2) + "\n";
}

/* ================================================================== DOM */

export const reduced = () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
export const isSheet = () => typeof matchMedia !== "undefined" && matchMedia(MQ_SHEET).matches;

export function h(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
    else n.setAttribute(k, v === true ? "" : v);
  }
  n.append(...kids.flat(Infinity).filter((c) => c != null && c !== false).map((c) => (c.nodeType ? c : document.createTextNode(String(c)))));
  return n;
}

export function svg(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null && v !== false) n.setAttribute(k, v);
  for (const c of kids) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}

export function put(parent, ...kids) { parent.replaceChildren(...liveKids(kids)); }

/* ---- zoom: the SVG is drawn wider inside a box that scrolls, so touch, trackpad and scrollbars all pan it.
   opts: stage (the scrolling box), getSvg() (the current <svg>; it is replaced on every redraw), root (holds the buttons),
   labelSel (the % readout), onChange(zoom). Buttons are [data-zoom="in|out|reset"] under root. */
export function createZoom({ stage, getSvg, root, labelSel = ".tp-zoomv", initial = 1, onChange = null }) {
  let zoom = clampZoom(initial);
  function set(z, ax = 0.5, ay = 0.5) {
    const old = zoom, el = getSvg();
    if (!el) return zoom;
    const fx = (stage.scrollLeft + stage.clientWidth * ax) / (stage.scrollWidth || 1), fy = (stage.scrollTop + stage.clientHeight * ay) / (stage.scrollHeight || 1);
    zoom = clampZoom(z);
    el.style.width = `${zoom * 100}%`;
    stage.dataset.zoomed = zoom > 1 ? "true" : "false";
    if (zoom !== old) {
      stage.scrollLeft = fx * stage.scrollWidth - stage.clientWidth * ax;
      stage.scrollTop = fy * stage.scrollHeight - stage.clientHeight * ay;
    }
    const label = root.querySelector(labelSel);
    if (label) label.textContent = `${Math.round(zoom * 100)} %`;
    for (const b of root.querySelectorAll("[data-zoom]")) b.disabled = (b.dataset.zoom === "in" && zoom >= ZOOM.max) || (b.dataset.zoom === "out" && zoom <= ZOOM.min) || (b.dataset.zoom === "reset" && zoom === 1);
    if (onChange) onChange(zoom);
    return zoom;
  }
  return { set, value: () => zoom, in: () => set(zoom * ZOOM.step), out: () => set(zoom / ZOOM.step), reset: () => set(1) };
}

/* Ctrl / Cmd + wheel zooms (so the page still scrolls under the diagram); a mouse drag on empty space scrolls a zoomed diagram.
   `blocked()` (e.g. edit mode) turns the drag off; `skip` is a selector of things that must keep their own click and drag. */
export function wirePan(stage, zoom, { blocked = () => false, skip = "" } = {}) {
  stage.addEventListener("wheel", (ev) => {
    if (!ev.ctrlKey && !ev.metaKey) return;
    ev.preventDefault();
    const r = stage.getBoundingClientRect();
    zoom.set(zoom.value() * (ev.deltaY < 0 ? ZOOM.step : 1 / ZOOM.step), (ev.clientX - r.left) / r.width, (ev.clientY - r.top) / r.height);
  }, { passive: false });
  let drag = null;
  stage.addEventListener("pointerdown", (ev) => {
    if (ev.pointerType !== "mouse" || ev.button !== 0 || zoom.value() === 1 || blocked() || (skip && ev.target.closest(skip))) return;
    drag = { x: ev.clientX, y: ev.clientY, l: stage.scrollLeft, t: stage.scrollTop };
    stage.setPointerCapture(ev.pointerId);
    stage.dataset.drag = "true";
  });
  stage.addEventListener("pointermove", (ev) => { if (drag) { stage.scrollLeft = drag.l - (ev.clientX - drag.x); stage.scrollTop = drag.t - (ev.clientY - drag.y); } });
  const end = () => { drag = null; stage.dataset.drag = "false"; };
  stage.addEventListener("pointerup", end);
  stage.addEventListener("pointercancel", end);
}

/* Drag one element in diagram units (edit mode). getPos() -> {x, y}; setPos({x, y}) moves it and redraws what hangs on it.
   Returns nothing; `state.dragged` is true after a real move so the click that follows can be ignored. */
export function startDrag(ev, { svgEl, el, getPos, setPos, state }) {
  ev.preventDefault();
  const inv = svgEl.getScreenCTM().inverse();
  const pt = (e) => { const p = svgEl.createSVGPoint(); p.x = e.clientX; p.y = e.clientY; return p.matrixTransform(inv); };
  const start = pt(ev), orig = { ...getPos() };
  state.dragged = false;
  el.setPointerCapture(ev.pointerId);
  const move = (e) => {
    const p = pt(e);
    if (Math.abs(p.x - start.x) + Math.abs(p.y - start.y) > 2) state.dragged = true;
    setPos({ x: Math.round(orig.x + p.x - start.x), y: Math.round(orig.y + p.y - start.y) });
  };
  const up = () => { el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up); el.removeEventListener("pointercancel", up); };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", up);
  el.addEventListener("pointercancel", up);
}

/* The details card is a bottom sheet on a phone; CSS reads this flag to leave room. */
export function setSheet(open, key = "archSheet") {
  if (typeof document !== "undefined") document.body.dataset[key] = open && isSheet() ? "open" : "closed";
}

/* Copy text to the clipboard; if that is refused, show it in a textarea under `out` so it can be copied by hand. */
export async function copyText(text, out, { done = "Copied.", manual = "Select all and copy.", label = "Text to copy", cls = "tp-json" } = {}) {
  try { await navigator.clipboard.writeText(text); out.textContent = done; }
  catch {
    const ta = h("textarea", { class: cls, readonly: true, rows: 8, "aria-label": label }, text);
    put(out, manual, ta);
    ta.select();
  }
}

/* A copy of the <svg> with every colour, stroke and font written into the elements, so it looks the same outside the page
   (the page's colours are CSS variables). Needs a browser: it asks the browser for the resolved style of each element. */
const EXPORT_PROPS = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-dasharray", "stroke-linecap", "stroke-linejoin", "opacity",
  "font-family", "font-size", "font-weight", "letter-spacing", "text-anchor", "paint-order", "text-transform", "dominant-baseline", "display"];

export function inlineStyles(srcSvg) {
  const clone = srcSvg.cloneNode(true);
  const a = [srcSvg, ...srcSvg.querySelectorAll("*")], b = [clone, ...clone.querySelectorAll("*")];
  a.forEach((el, i) => {
    const cs = getComputedStyle(el), t = b[i];
    t.removeAttribute("class");
    t.removeAttribute("style");
    t.setAttribute("style", EXPORT_PROPS.map((p) => `${p}:${cs.getPropertyValue(p)}`).join(";"));
  });
  clone.removeAttribute("style");
  clone.setAttribute("xmlns", NS);
  const vb = (clone.getAttribute("viewBox") || "0 0 1000 600").split(/\s+/).map(Number);
  clone.setAttribute("width", String(vb[2])); clone.setAttribute("height", String(vb[3]));
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#fff";
  const rect = document.createElementNS(NS, "rect");
  for (const [k, v] of Object.entries({ x: vb[0], y: vb[1], width: vb[2], height: vb[3], fill: bg })) rect.setAttribute(k, v);
  clone.insertBefore(rect, clone.firstChild);
  return clone;
}

export const svgText = (srcSvg) => '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(inlineStyles(srcSvg)) + "\n";

export function download(name, text, mime = "image/svg+xml") {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = h("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
