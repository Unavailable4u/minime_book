/* MiniMe Atlas 2 - architecture layout, pure geometry (P26). One ES module, no DOM, no dependencies except svgview.js's pure helpers.

   Five kinds of drawing, one set of rules: a deterministic layout (same input, same picture) so a diagram never changes shape between runs.
     structure  boxes of the derived model at their pinned positions (content/topology.json, content/arch-layout.json); a box nobody pinned
                is placed automatically inside its group, so a fresh census never gives an empty or broken diagram
     layered    steps of a flow: longest-path layers, barycentre ordering inside a layer, one lane per actor ("swimlanes")
     sequence   one lifeline per actor, one message per step
     lifecycle  states on the same layered layout, the longest chain on the first row
     catalog    cards of route groups, packed into columns
   Rects are {x, y, w, h} with x, y the centre, like topology.js. */

import { edgePath, clipToRect } from "../svgview.js";
import { FLOW_EDGE_KINDS, wrapText, textWidth } from "./model.js";

export { edgePath, clipToRect };

/* ================================================================== structure */

export const BOX = { w0: 112, w1: 156, h0: 44, h1: 60 };
export const KID = { w: 72, h: 42 };               // the parts of an opened node (as topology.js CHILD): small, and labelled at 12.5px
export const SMALL = { store: { w: 128, h: 46 }, external: { w: 136, h: 46 }, queue: { w: 128, h: 46 } };
export const LABEL_PAD = 12;

/* Box size from code lines (the area grows with the lines, so the root), widened when the label would not fit. */
export function nodeBox(node, maxCode) {
  const label = textWidth(node.label || node.id, node.parent ? 12.5 : 14.5);
  if (node.parent) return { w: Math.max(KID.w, label + 12), h: KID.h };
  if (SMALL[node.kind]) return { w: Math.max(SMALL[node.kind].w, label + 2 * LABEL_PAD), h: SMALL[node.kind].h };
  const t = maxCode > 0 ? Math.sqrt(Math.max(0, node.code || 0) / maxCode) : 0;
  return { w: Math.max(Math.round(BOX.w0 + (BOX.w1 - BOX.w0) * t), label + 2 * LABEL_PAD), h: Math.round(BOX.h0 + (BOX.h1 - BOX.h0) * t) };
}

const overlaps = (a, b, gap) => Math.abs(a.x - b.x) < (a.w + b.w) / 2 + gap && Math.abs(a.y - b.y) < (a.h + b.h) / 2 + gap;

/* First free spot (scanning rows left to right) inside rect `area` for a box w x h that touches none of `taken`; null when full. */
export function freeSpot(area, w, h, taken, gap = 10, step = 14) {
  const top = area.y + 30;                                         // the group's title sits in the first 30 units
  for (let y = top + h / 2; y <= area.y + area.h - h / 2 - 4; y += step) {
    for (let x = area.x + w / 2 + 8; x <= area.x + area.w - w / 2 - 8; x += step) {
      const r = { x, y, w, h };
      if (!taken.some((t) => overlaps(r, t, gap))) return { x, y };
    }
  }
  return null;
}

/* nodes: the model's nodes (no groups); layout: model.layout {groups, pins, view}.
   -> { pos: Map id -> {x, y}, box: Map id -> {w, h}, auto: Set of ids placed by this function, groups: [rect + id/label/align], size: [W, H] } */
export function structureLayout(nodes, layout) {
  const lay = layout || {}, pins = lay.pins || {}, groups = lay.groups || [];
  const maxCode = Math.max(1, ...nodes.filter((n) => !n.parent).map((n) => n.code || 0));
  const box = new Map(nodes.map((n) => [n.id, nodeBox(n, maxCode)]));
  const pos = new Map(), auto = new Set(), taken = [];
  for (const n of nodes) {
    const p = pins[n.id];
    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) { pos.set(n.id, { x: p.x, y: p.y }); taken.push({ ...p, ...box.get(n.id) }); }
  }
  let [W, H] = Array.isArray(lay.view) && lay.view.length === 2 ? lay.view : [1000, 640];
  const rectOf = (g) => ({ x: g.x, y: g.y, w: g.w, h: g.h });
  let spill = H;                                                    // a node that fits nowhere goes below the diagram, row by row
  for (const n of nodes) {
    if (pos.has(n.id)) continue;
    const b = box.get(n.id), g = groups.find((x) => x.id === n.group);
    const spot = g ? freeSpot(rectOf(g), b.w, b.h, taken) : null;
    let p;
    if (spot) p = spot;
    else { p = { x: 20 + b.w / 2 + ((auto.size * (b.w + 14)) % Math.max(b.w + 14, W - 40)), y: spill + b.h / 2 + 10 }; if (p.x + b.w / 2 > W - 20) { spill += b.h + 14; p = { x: 20 + b.w / 2, y: spill + b.h / 2 + 10 }; } H = Math.max(H, p.y + b.h / 2 + 16); }
    pos.set(n.id, p); auto.add(n.id); taken.push({ ...p, ...b });
  }
  const present = new Set(nodes.map((n) => n.group).filter(Boolean));
  return { pos, box, auto, groups: groups.filter((g) => present.has(g.id)), size: [Math.round(W), Math.round(H)] };
}

/* ---- zoom levels of the structure: 0 = the four groups, 1 = the containers, 2 = containers with their parts opened */

/* Parallel edges between the same two boxes become one: kinds merged, weights added, gate if any is a gate. `map` sends a node id to
   the id of the box that stands for it at this level (or null to drop the edge); `allow(edge)` filters by kind. */
export function rollupEdges(edges, map, allow = null) {
  const m = new Map();
  for (const e of edges || []) {
    if (allow && !allow(e)) continue;
    const a = map(e.from), b = map(e.to);
    if (!a || !b || a === b) continue;
    const lo = a < b ? a : b, hi = a < b ? b : a, key = `${lo}|${hi}`;
    const r = m.get(key) || { id: key, a: lo, b: hi, kinds: new Set(), weight: 0, gate: false, labels: [], arrowAB: false, arrowBA: false };
    r.kinds.add(e.kind); r.weight += e.weight || 0; r.gate = r.gate || !!e.gate;
    if (e.label && !r.labels.includes(e.label)) r.labels.push(e.label);
    if (e.directed !== false && e.kind !== "graph") { if (a === lo) r.arrowAB = true; else r.arrowBA = true; }
    m.set(key, r);
  }
  return [...m.values()].map((r) => ({ ...r, kinds: [...r.kinds].sort(), flow: [...r.kinds].some((k) => FLOW_EDGE_KINDS.includes(k)) })).sort((x, y) => (x.id < y.id ? -1 : 1));
}

/* What is drawn at a zoom level: { nodes: [boxes], edges: rolled up, groupBoxes: true at level 0, frameOf: parent id or null }. Nodes of
   the level keep the model's fields; at level 0 a box is a group (kind "group"). */
export function levelGraph(nodes, groups, edges, level, allow = null) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  if (level <= 0) {
    const gid = (id) => { const n = byId.get(id); return n ? n.group || null : null; };
    const used = new Set(nodes.map((n) => n.group).filter(Boolean));
    const boxes = groups.filter((g) => used.has(g.id)).map((g) => ({ id: g.id, label: g.label || g.id, kind: "group", code: nodes.filter((n) => n.group === g.id && !n.parent).reduce((s, n) => s + (n.code || 0), 0), files: nodes.filter((n) => n.group === g.id && !n.parent).reduce((s, n) => s + (n.files || 0), 0), group: g.id }));
    return { nodes: boxes, edges: rollupEdges(edges, gid, allow), groupBoxes: true, frameOf: null };
  }
  if (level === 1) {
    const up = (id) => { const n = byId.get(id); return n ? n.parent || n.id : null; };
    return { nodes: nodes.filter((n) => !n.parent), edges: rollupEdges(edges, up, allow), groupBoxes: false, frameOf: null };
  }
  const opened = nodes.filter((n) => (n.children || []).length).map((n) => n.id);
  return { nodes: nodes.filter((n) => !opened.includes(n.id)), edges: rollupEdges(edges, (id) => (byId.has(id) ? id : null), allow), groupBoxes: false, frameOf: opened };
}

/* The box around the opened parts of a node: their bounding box plus a margin, with extra room on top for the title. */
export function frameRect(kids, pad = 12, title = 26) {
  if (!kids.length) return null;
  const x0 = Math.min(...kids.map((k) => k.x - k.w / 2)) - pad, x1 = Math.max(...kids.map((k) => k.x + k.w / 2)) + pad;
  const y0 = Math.min(...kids.map((k) => k.y - k.h / 2)) - pad - title, y1 = Math.max(...kids.map((k) => k.y + k.h / 2)) + pad;
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, w: x1 - x0, h: y1 - y0 };
}

/* Line width from the weight (graph links, imports, calls), logarithmic because the counts run from 1 to 500+. No weight: thin and dashed. */
export function edgeWidth(weight, max) {
  if (!(weight > 0) || !(max > 0)) return 1.5;
  return Math.round((1.5 + 4 * Math.log1p(weight) / Math.log1p(max)) * 10) / 10;
}

/* ================================================================== layered (swimlanes) */

/* items: [{id, lane, w, h}]; edges: [{from, to}] (cycles are fine: a back edge is detected and drawn round the side).
   opts: axis "down" (layers top to bottom, lanes are columns; default) or "right"; laneOrder; gapU, gapV, laneGap, pad, head.
   -> { pos: Map id -> rect, layer: Map, lanes: [{id, label?, x, y, w, h}], back: Set of edge indexes, size: [W, H] } */
export function layeredLayout(items, edges, opts = {}) {
  const axis = opts.axis === "right" ? "right" : "down";
  const gapU = opts.gapU ?? 40, gapV = opts.gapV ?? 22, laneGap = opts.laneGap ?? 30, pad = opts.pad ?? 20;
  const head = opts.head ?? (axis === "down" ? 34 : 130);
  const ids = items.map((i) => i.id), by = new Map(items.map((i) => [i.id, i]));
  const valid = [];
  (edges || []).forEach((e, index) => { if (by.has(e.from) && by.has(e.to) && e.from !== e.to) valid.push({ ...e, index }); });

  const outs = new Map(ids.map((i) => [i, []]));
  for (const e of valid) outs.get(e.from).push(e);
  const hasIn = new Set(valid.map((e) => e.to));
  const back = new Set(), state = new Map();
  const visit = (u) => {
    state.set(u, 1);
    for (const e of outs.get(u)) {
      const s = state.get(e.to);
      if (s === 1) back.add(e.index);
      else if (!s) visit(e.to);
    }
    state.set(u, 2);
  };
  for (const id of ids.filter((i) => !hasIn.has(i)).concat(ids)) if (!state.get(id)) visit(id);

  const fwd = valid.filter((e) => !back.has(e.index));
  const layer = new Map(ids.map((i) => [i, 0])), indeg = new Map(ids.map((i) => [i, 0]));
  for (const e of fwd) indeg.set(e.to, indeg.get(e.to) + 1);
  const queue = ids.filter((i) => indeg.get(i) === 0), fouts = new Map(ids.map((i) => [i, []]));
  for (const e of fwd) fouts.get(e.from).push(e.to);
  while (queue.length) {
    const u = queue.shift();
    for (const v of fouts.get(u)) { layer.set(v, Math.max(layer.get(v), layer.get(u) + 1)); indeg.set(v, indeg.get(v) - 1); if (indeg.get(v) === 0) queue.push(v); }
  }

  const laneIds = [];
  for (const l of opts.laneOrder || []) if (items.some((i) => i.lane === l) && !laneIds.includes(l)) laneIds.push(l);
  for (const i of items) if (!laneIds.includes(i.lane)) laneIds.push(i.lane);
  const laneIx = new Map(laneIds.map((l, i) => [l, i]));
  const nLayers = Math.max(0, ...layer.values()) + 1;

  // cells hold the items of one layer in one lane, in drawing order; barycentre sweeps order them by where their neighbours sit
  const cells = new Map(), vpos = new Map();
  const cellKey = (id) => `${layer.get(id)}|${laneIx.get(by.get(id).lane)}`;
  for (const id of ids) { const k = cellKey(id); if (!cells.has(k)) cells.set(k, []); cells.get(k).push(id); }
  const reslot = () => { for (const list of cells.values()) list.forEach((id, s) => vpos.set(id, laneIx.get(by.get(id).lane) * 1000 + s)); };
  reslot();
  const preds = new Map(ids.map((i) => [i, []])), succs = new Map(ids.map((i) => [i, []]));
  for (const e of fwd) { preds.get(e.to).push(e.from); succs.get(e.from).push(e.to); }
  const sweep = (order, nb) => {
    for (const l of order) {
      for (const [k, list] of cells) {
        if (!k.startsWith(`${l}|`) || list.length < 2) continue;
        const key = (id) => { const n = nb.get(id); return n.length ? n.reduce((s, x) => s + vpos.get(x), 0) / n.length : vpos.get(id); };
        const decorated = list.map((id, i) => ({ id, i, v: key(id) }));
        decorated.sort((a, b) => a.v - b.v || a.i - b.i);
        cells.set(k, decorated.map((d) => d.id));
      }
      reslot();
    }
  };
  const up = Array.from({ length: nLayers }, (_, i) => i), down = [...up].reverse();
  sweep(up.slice(1), preds); sweep(down.slice(1), succs); sweep(up.slice(1), preds);

  const su = (i) => (axis === "down" ? i.h : i.w), sv = (i) => (axis === "down" ? i.w : i.h);
  const layerSize = Array(nLayers).fill(0);
  for (const i of items) layerSize[layer.get(i.id)] = Math.max(layerSize[layer.get(i.id)], su(i));
  const layerAt = [];
  let u0 = pad + head;
  for (let l = 0; l < nLayers; l++) { layerAt.push(u0); u0 += layerSize[l] + gapU; }
  const totalU = Math.max(u0 - gapU + pad, pad * 2 + head);

  const laneSize = Array(laneIds.length).fill(0), cellTotal = new Map();
  for (const [k, list] of cells) {
    const total = list.reduce((s, id) => s + sv(by.get(id)), 0) + gapV * (list.length - 1);
    cellTotal.set(k, total);
    const lane = Number(k.split("|")[1]);
    laneSize[lane] = Math.max(laneSize[lane], total);
  }
  const laneAt = [];
  let v0 = pad;
  laneIds.forEach((_, i) => { laneAt.push(v0); v0 += Math.max(laneSize[i], 60) + laneGap; });
  const totalV = Math.max(v0 - laneGap + pad, pad * 2);

  const pos = new Map();
  for (const [k, list] of cells) {
    const [l, lane] = k.split("|").map(Number);
    let cur = laneAt[lane] + (Math.max(laneSize[lane], 60) - cellTotal.get(k)) / 2;
    for (const id of list) {
      const it = by.get(id), a = cur + sv(it) / 2, b = layerAt[l] + layerSize[l] / 2;
      pos.set(id, axis === "down" ? { x: a, y: b, w: it.w, h: it.h } : { x: b, y: a, w: it.w, h: it.h });
      cur += sv(it) + gapV;
    }
  }
  const lanes = laneIds.map((id, i) => {
    const thick = Math.max(laneSize[i], 60);
    return axis === "down"
      ? { id, x: laneAt[i] - 8, y: pad, w: thick + 16, h: totalU - pad * 2 + 0, label: id }
      : { id, x: pad, y: laneAt[i] - 8, w: totalU - pad * 2, h: thick + 16, label: id };
  });
  const size = axis === "down" ? [Math.round(totalV), Math.round(totalU)] : [Math.round(totalU), Math.round(totalV)];
  return { pos, layer, lanes, back, size, axis, layers: nLayers };
}

/* The line between two step boxes: a curve between facing sides; a back edge goes round the outside. -> {d, mid} */
export function routeEdge(a, b, { axis = "down", back = false } = {}) {
  const r = (v) => Math.round(v * 10) / 10;
  const cubic = (p0, c1, c2, p1) => {
    const mid = { x: (p0.x + 3 * c1.x + 3 * c2.x + p1.x) / 8, y: (p0.y + 3 * c1.y + 3 * c2.y + p1.y) / 8 };
    return { d: `M${r(p0.x)} ${r(p0.y)}C${r(c1.x)} ${r(c1.y)} ${r(c2.x)} ${r(c2.y)} ${r(p1.x)} ${r(p1.y)}`, mid: { x: r(mid.x), y: r(mid.y) } };
  };
  if (axis === "down") {
    if (back) {
      const s = { x: a.x + a.w / 2, y: a.y }, t = { x: b.x + b.w / 2, y: b.y }, out = Math.max(s.x, t.x) + 64;
      return cubic(s, { x: out, y: s.y }, { x: out, y: t.y }, t);
    }
    const sameRow = Math.abs(b.y - a.y) < (a.h + b.h) / 2 + 4;
    if (sameRow) {
      const dir = b.x >= a.x ? 1 : -1, s = { x: a.x + dir * a.w / 2, y: a.y }, t = { x: b.x - dir * b.w / 2, y: b.y };
      return { d: `M${r(s.x)} ${r(s.y)}L${r(t.x)} ${r(t.y)}`, mid: { x: r((s.x + t.x) / 2), y: r((s.y + t.y) / 2) } };
    }
    const s = { x: a.x, y: a.y + a.h / 2 }, t = { x: b.x, y: b.y - b.h / 2 }, dy = Math.max(16, (t.y - s.y) / 2);
    return cubic(s, { x: s.x, y: s.y + dy }, { x: t.x, y: t.y - dy }, t);
  }
  if (back) {
    const s = { x: a.x, y: a.y + a.h / 2 }, t = { x: b.x, y: b.y + b.h / 2 }, lo = Math.max(s.y, t.y) + 58;
    return cubic(s, { x: s.x, y: lo }, { x: t.x, y: lo }, t);
  }
  const sameCol = Math.abs(b.x - a.x) < (a.w + b.w) / 2 + 4;
  if (sameCol) {
    const dir = b.y >= a.y ? 1 : -1, s = { x: a.x, y: a.y + dir * a.h / 2 }, t = { x: b.x, y: b.y - dir * b.h / 2 };
    return { d: `M${r(s.x)} ${r(s.y)}L${r(t.x)} ${r(t.y)}`, mid: { x: r((s.x + t.x) / 2), y: r((s.y + t.y) / 2) } };
  }
  const s = { x: a.x + a.w / 2, y: a.y }, t = { x: b.x - b.w / 2, y: b.y }, dx = Math.max(16, (t.x - s.x) / 2);
  return cubic(s, { x: s.x + dx, y: s.y }, { x: t.x - dx, y: t.y }, t);
}

/* Step boxes for a flow: width fixed, height from the wrapped title (and a line for a gate), lane = actor. */
export const STEP = { w: 176, lineH: 15, padY: 11, charsPerLine: 24, maxLines: 3 };
export function stepBox(step) {
  const lines = wrapText(step.title || step.id, STEP.charsPerLine, STEP.maxLines);
  const extra = step.gate ? 1 : 0;
  return { w: STEP.w, h: STEP.padY * 2 + (lines.length + extra) * STEP.lineH + 6, lines };
}

/* ================================================================== lifecycle */

/* Lane (row) of each state: the longest chain from a start state on row 0, every other state below it. -> Map id -> lane index (0, 1, ...) */
export function lifecycleLanes(states, transitions) {
  const ids = states.map((s) => s.id), idset = new Set(ids);
  const edges = (transitions || []).filter((t) => idset.has(t.from) && idset.has(t.to) && t.from !== t.to).map((t) => ({ from: t.from, to: t.to }));
  const L = layeredLayout(ids.map((id) => ({ id, lane: "x", w: 10, h: 10 })), edges, {});
  const ending = new Set(states.filter((x) => x.terminal).map((x) => x.id));      // an end state is never part of the main chain: it hangs below the row
  const outs = new Map(ids.map((i) => [i, []]));
  edges.forEach((e, i) => { if (!L.back.has(i) && !ending.has(e.to)) outs.get(e.from).push(e.to); });
  const depth = new Map(), next = new Map();                         // longest forward chain starting at each state
  const dfs = (u) => {
    if (depth.has(u)) return depth.get(u);
    let best = 0, nx = null;
    for (const v of outs.get(u)) { const d = dfs(v) + 1; if (d > best) { best = d; nx = v; } }
    depth.set(u, best); next.set(u, nx);
    return best;
  };
  ids.forEach(dfs);
  const hasIn = new Set(edges.filter((_, i) => !L.back.has(i)).map((e) => e.to));
  const starts = ids.filter((i) => !hasIn.has(i));
  let head = starts.length ? starts.reduce((a, b) => (depth.get(b) > depth.get(a) ? b : a)) : ids[0];
  const main = new Set();
  for (let u = head; u != null; u = next.get(u)) main.add(u);
  return new Map(ids.map((id) => [id, main.has(id) && !ending.has(id) ? 0 : 1]));
}

export const STATE = { w: 132, h: 46 };

/* ================================================================== sequence */

export const SEQ = { colW: 190, head: 48, pad: 24, lineH: 14 };

/* actors: [{id, label}] in lifeline order; messages: [{id, from, to, label}] in order.
   -> { cols: Map actor -> x, rows: [{id, y, x1, x2, self, lines, h}], size: [W, H], head } */
export function sequenceLayout(actors, messages, opts = {}) {
  const pad = opts.pad ?? SEQ.pad;
  const colW = opts.colW ?? Math.max(SEQ.colW, actors.length < 4 ? Math.floor(760 / Math.max(1, actors.length)) : 0);      // few lifelines: wide enough that the text is not scaled up to a poster
  const cols = new Map(actors.map((a, i) => [a.id, pad + colW * i + colW / 2]));
  let y = pad + SEQ.head + 14;
  const rows = [];
  for (const m of messages) {
    if (!cols.has(m.from) || !cols.has(m.to)) continue;
    const x1 = cols.get(m.from), x2 = cols.get(m.to), self = m.from === m.to;
    const room = self ? colW - 40 : Math.max(Math.abs(x2 - x1), colW * 0.9) - 20;
    const lines = wrapText(m.label || m.id, Math.max(12, Math.floor(room / 7.2)), 3);
    const h = 20 + lines.length * SEQ.lineH + (self ? 14 : 0) + (m.gate ? SEQ.lineH : 0);
    rows.push({ id: m.id, y: y + h - 10, top: y, x1, x2, self, lines, h });
    y += h + 8;
  }
  return { cols, rows, size: [Math.round(pad * 2 + colW * actors.length), Math.round(y + pad)], head: SEQ.head, colW };
}

/* ================================================================== catalog */

export const CARD = { w: 380, head: 46, row: 17, gap: 18, pad: 20 };

/* groups: [{id, title, count, rows}] -> cards packed into as many columns as fit `width`, each into the shortest column.
   -> { cards: [{id, x, y, w, h}], size: [W, H], columns } */
export function catalogLayout(groups, width = 1100) {
  const cols = Math.max(1, Math.floor((width - CARD.pad * 2 + CARD.gap) / (CARD.w + CARD.gap)));
  const tops = Array(cols).fill(CARD.pad);
  const cards = [];
  for (const g of groups) {
    const c = tops.indexOf(Math.min(...tops));
    const h = CARD.head + g.rows * CARD.row + 12;
    cards.push({ id: g.id, x: CARD.pad + c * (CARD.w + CARD.gap), y: tops[c], w: CARD.w, h });
    tops[c] += h + CARD.gap;
  }
  return { cards, size: [Math.round(CARD.pad * 2 + cols * CARD.w + (cols - 1) * CARD.gap), Math.round(Math.max(...tops, CARD.pad * 2) - CARD.gap + CARD.pad)], columns: cols };
}
