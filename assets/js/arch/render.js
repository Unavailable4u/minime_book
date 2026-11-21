/* MiniMe Atlas 2 - architecture renderer (P26). One ES module, vanilla SVG, no library, no build step.

   Draws every view of the architecture model (data/arch/model.json and views/*.json, written by scripts/arch.py in P25):
     layered / gated   the structure of the code (folders, stores, outside services) or the steps of a flow in swimlanes (one lane per actor)
     sequence          sequence.js     lifecycle   lifecycle.js     catalog   catalog.js
   Nothing is drawn by hand. Structure comes from the census, so it cannot be stale. A flow was traced by Copilot: every step shows the
   status of the code it cites (fresh / stale / broken / unverified), an AI-written label and a confidence. A flow that is not written yet
   degrades: the derived part is drawn and the page says "not written yet" (it never fails).

   Entry points
     mountArch(root, {view, flow, focus, level, embed, edit, theme})   draw one view into root; returns a controller
     [data-arch-view="<id>"] (optional data-arch-flow, data-arch-embed)   mounted automatically on load (the System page, P09)
     [data-arch-page]       a page that takes ?view= &flow= &embed=1 &theme=paper|dark &edit=1 &level=0|1|2 (arch-view.html)
   Pure helpers live in model.js and layout.js and are tested in Node; this file is the DOM. */

import { h, svg, put, createZoom, wirePan, startDrag, setSheet, isSheet, reduced, copyText, svgText, download, nearestInDirection, exportPins } from "../svgview.js";
import { loadLinkOptions } from "../links.js";
import * as Model from "./model.js";
import * as Lay from "./layout.js";
import * as Seq from "./sequence.js";
import * as Life from "./lifecycle.js";
import * as Cat from "./catalog.js";
import { panelContent, statusBadge, aiBadge } from "./panel.js";

const BASE = typeof document !== "undefined" ? new URL("../../../", import.meta.url) : null;
async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}
export const LOADER = Model.makeLoader(getJSON);

const HOW_TO_WRITE = "python scripts/arch.py todo --minime ../MiniMe, then Copilot prompt C (UPDATING.md, Step 2c), then python scripts/update_all.py";
const LEVELS = [{ id: 0, text: "Groups", title: "The four groups: your machine, the contract, the browser, the server" }, { id: 1, text: "Folders", title: "One box per folder of the repository" }, { id: 2, text: "Parts", title: "Open the M2C client into its parts" }];
let UID = 0;

/* ================================================================== shared drawing helpers */

function makeCtx(A) {
  const uid = A.uid;
  const ctx = {
    uid, svg, h,
    arrow: (name) => `url(#${uid}-a-${name})`,
    /* The <svg> of one diagram: viewBox, a label, and the arrowheads (one per meaning, so colour is never the only carrier: shape and dash differ too). */
    root(W, H) {
      const el = svg("svg", { class: "ar-svg", viewBox: `0 0 ${W} ${H}`, role: "group", "aria-label": `${A.shard.title}. ${A.summary || ""}`.trim(), preserveAspectRatio: "xMidYMin meet", "data-w": W, "data-h": H });
      const defs = svg("defs");
      for (const name of ["flow", "rel", "gate", "dim"]) {
        defs.append(svg("marker", { id: `${uid}-a-${name}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 9, markerHeight: 9, markerUnits: "userSpaceOnUse", orient: "auto-start-reverse" },
          svg("path", { d: "M0 0L10 5L0 10z", class: `ar-arrowhead ar-arrowhead--${name}` })));
      }
      el.append(defs);
      return el;
    },
    /* A status glyph for anything that is not plainly fresh, drawn at x, y. Fresh and derived items show nothing: the banner says so once. */
    mark(status, x, y) {
      const g = Model.STATUS_GLYPH[status];
      if (!g) return null;
      return svg("g", { class: `ar-mark ar-mark--${status}`, transform: `translate(${x},${y})` }, svg("title", {}, Model.STATUS_TEXT[status]), svg("circle", { r: 8 }), svg("text", { "text-anchor": "middle", y: 4 }, g));
    },
    /* Make an element interactive: focusable, named, selectable, remembered under `key` so a redraw can keep the selection. */
    mk(key, el, target, label) {
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-pressed", "false");
      el.setAttribute("aria-label", label);
      el.dataset.key = key;
      A.targets.set(key, { el, target });
      el.addEventListener("click", () => { if (A.drag.dragged) { A.drag.dragged = false; return; } A.select(A.sel === key ? null : key); });
      el.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); A.select(A.sel === key ? null : key); } });
      el.addEventListener("pointerenter", (ev) => { if (ev.pointerType === "mouse" && !A.edit) A.preview(key); });
      el.addEventListener("pointerleave", (ev) => { if (ev.pointerType === "mouse") A.preview(null); });
      el.addEventListener("focus", () => { if (!A.edit) A.preview(key); });
      el.addEventListener("blur", () => A.preview(null));
    },
  };
  return ctx;
}

/* ================================================================== structure (system, dataflow, unified, and any flow not written yet) */

const KIND_TEXT = { import: "imports", "api-call": "API calls", protocol: "protocol", db: "database", env: "environment", declared: "declared", graph: "graph links" };

function drawStructure(A, ctx) {
  const nodesAll = A.shard.nodes.filter((n) => n.kind !== "group");
  const ml = (A.model && A.model.layout) || { groups: [], view: [1000, 640] };
  const base = Lay.structureLayout(nodesAll, { groups: ml.groups, pins: { ...(A.shard.pins || {}), ...A.moved }, view: ml.view });
  const allow = (e) => A.kinds.has(e.kind);
  const G = Lay.levelGraph(nodesAll, ml.groups, A.shard.edges || [], A.level, allow);
  const byId = new Map(nodesAll.map((n) => [n.id, n]));
  const pos = new Map(base.pos);
  A.moved && Object.entries(A.moved).forEach(([id, p]) => pos.set(id, p));
  const gRect = new Map(ml.groups.map((g) => [g.id, { x: g.x + g.w / 2, y: g.y + g.h / 2, w: g.w, h: g.h }]));
  const opened = new Set(G.frameOf || []);
  const boxOf = (n) => (G.groupBoxes ? gRect.get(n.id) : { ...pos.get(n.id), ...base.box.get(n.id) });
  const rectOf = (id) => {
    if (opened.has(id)) return Lay.frameRect((byId.get(id).children || []).map((k) => (byId.has(k) ? { ...pos.get(k), ...base.box.get(k) } : null)).filter(Boolean));
    const n = G.nodes.find((x) => x.id === id);
    return n ? boxOf(n) : null;
  };
  const size = base.size;
  const s = ctx.root(size[0], size[1]);
  const groupsLayer = svg("g", { class: "ar-groups" }), edgeLayer = svg("g", { class: "ar-edges" }), pathLayer = svg("g", { class: "ar-pathlayer", "aria-hidden": "true" }), nodeLayer = svg("g", { class: "ar-nodes" });
  const els = { nodes: new Map(), edges: [], frames: [] };
  if (!G.groupBoxes) for (const g of base.groups) {
    groupsLayer.append(svg("g", { class: `ar-group ar-group--${g.id.replace("group:", "")}` }, svg("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 14 }),
      svg("text", g.align === "end" ? { x: g.x + g.w - 12, y: g.y + 20, "text-anchor": "end" } : { x: g.x + 12, y: g.y + 20 }, g.label)));
  }
  for (const id of opened) {
    const n = byId.get(id), r = svg("rect", { class: "ar-frame__r", rx: 12 }), t = svg("text", { class: "ar-frame__t" }, n.label);
    groupsLayer.append(svg("g", { class: "ar-frame" }, r, t));
    els.frames.push({ id, rect: r, text: t });
  }
  const maxW = Math.max(1, ...G.edges.map((e) => e.weight));
  const deg = new Map();
  for (const e of G.edges) { deg.set(e.a, (deg.get(e.a) || 0) + 1); deg.set(e.b, (deg.get(e.b) || 0) + 1); }
  for (const e of G.edges) {
    const gate = e.gate, cls = gate ? "gate" : e.flow ? "flow" : "rel", decl = !e.weight;
    const w = Lay.edgeWidth(e.weight, maxW);
    const head = ctx.arrow(gate ? "gate" : cls);
    const path = svg("path", { class: `ar-edge ar-edge--${cls}${decl ? " ar-edge--declared" : ""}`, "stroke-width": w, "marker-end": e.arrowAB ? head : null, "marker-start": e.arrowBA ? head : null });
    const hit = svg("path", { class: "ar-hit", fill: "none", "stroke-width": Math.max(14, w + 8), "data-edge": e.id });
    const lab = e.labels[0] ? svg("text", { class: `ar-edge__l${gate ? " ar-edge__l--gate" : ""}`, "text-anchor": "middle" }, e.labels[0]) : null;
    const nm = (id) => (byId.get(id) || (G.groupBoxes && ml.groups.find((g) => g.id === id)) || {}).label || id;
    path.append(svg("title", {}, `${nm(e.a)} and ${nm(e.b)}: ${e.kinds.map((k) => KIND_TEXT[k] || k).join(", ")}${e.weight ? `, weight ${e.weight}` : ""}${e.labels.length ? `. ${e.labels.join(", ")}` : ""}`));
    edgeLayer.append(path, hit);
    if (lab) edgeLayer.append(lab);
    hit.addEventListener("click", () => A.select(`e:${e.id}`));
    A.targets.set(`e:${e.id}`, { el: hit, target: { type: "edge", edge: e } });
    els.edges.push({ e, path, hit, lab });
  }
  const centers = [];
  for (const n of G.nodes) {
    const r = boxOf(n), kid = !!n.parent, cls = n.kind === "group" ? "ar-node--group" : `ar-node--${n.kind}`;
    const g = svg("g", { class: `ar-node ${cls}${kid ? " ar-node--kid" : ""}${n.gate ? " ar-node--gate" : ""}${base.auto.has(n.id) ? " ar-node--auto" : ""}`, "data-id": n.id });
    if (n.kind === "store") {
      const rx = r.w / 2, ry = 7;
      g.append(svg("path", { class: "ar-box", d: `M${-rx} ${-r.h / 2 + ry}a${rx} ${ry} 0 0 1 ${r.w} 0v${r.h - 2 * ry}a${rx} ${ry} 0 0 1 ${-r.w} 0z` }), svg("path", { class: "ar-box ar-box--line", d: `M${-rx} ${-r.h / 2 + ry}a${rx} ${ry} 0 0 0 ${r.w} 0` }));
    } else {
      g.append(svg("rect", { class: "ar-box", x: -r.w / 2, y: -r.h / 2, width: r.w, height: r.h, rx: n.kind === "group" ? 14 : 9 }));
      if (n.kind === "external") g.append(svg("rect", { class: "ar-box ar-box--inner", x: -r.w / 2 + 4, y: -r.h / 2 + 4, width: r.w - 8, height: r.h - 8, rx: 6 }));
    }
    g.append(svg("text", { class: "ar-label", "text-anchor": "middle", y: n.files != null ? -3 : 5 }, n.label),
      n.files != null ? svg("text", { class: "ar-sub", "text-anchor": "middle", y: 14 }, `${fmtK(n.code)} lines`) : null,
      svg("g", { class: "ar-badges" }));
    ctx.mk(n.id, g, { type: n.kind === "group" ? "group" : "node", node: n, degree: deg.get(n.id) || 0 }, `${n.label}${n.files != null ? `, ${fmtK(n.code)} code lines in ${n.files} files` : ""}`);
    g.addEventListener("pointerdown", (ev) => { if (A.edit && !G.groupBoxes) startDrag(ev, { svgEl: s, el: g, getPos: () => pos.get(n.id), state: A.drag, setPos: (p) => { pos.set(n.id, p); A.moved[n.id] = p; place(); } }); });
    nodeLayer.append(g);
    els.nodes.set(n.id, g);
    centers.push({ id: n.id, x: r.x, y: r.y });
  }
  s.append(groupsLayer, edgeLayer, pathLayer, nodeLayer);

  function place() {
    for (const [id, el] of els.nodes) { const n = G.nodes.find((x) => x.id === id), r = boxOf(n); el.setAttribute("transform", `translate(${r.x},${r.y})`); }
    for (const f of els.frames) { const r = rectOf(f.id); if (r) { f.rect.setAttribute("x", r.x - r.w / 2); f.rect.setAttribute("y", r.y - r.h / 2); f.rect.setAttribute("width", r.w); f.rect.setAttribute("height", r.h); f.text.setAttribute("x", r.x - r.w / 2 + 12); f.text.setAttribute("y", r.y - r.h / 2 + 19); } }
    for (const q of els.edges) {
      const a = rectOf(q.e.a), b = rectOf(q.e.b);
      if (!a || !b) continue;
      const p = Lay.edgePath(a, b);
      q.path.setAttribute("d", p.d); q.hit.setAttribute("d", p.d);
      if (q.lab) { q.lab.setAttribute("x", p.mid.x); q.lab.setAttribute("y", p.mid.y - 5); }
    }
    overlay();
  }
  /* A flow laid over the structure (unified view): its steps numbered on the boxes they happen in, and the path between them. */
  function overlay() {
    put(pathLayer);
    for (const el of els.nodes.values()) put(el.querySelector(".ar-badges"));
    const ov = A.overlay;
    if (!ov) return;
    const toBox = (id) => (G.groupBoxes ? (byId.get(id) || {}).group : opened.has(id) ? id : (byId.get(id) || {}).parent && !opened.has((byId.get(id) || {}).parent) ? byId.get(id).parent : id);
    const seq = [], nums = new Map();
    ov.steps.forEach((st, i) => {
      const id = toBox(st.actor);
      if (!id || !els.nodes.has(id)) return;
      if (seq[seq.length - 1] !== id) seq.push(id);
      if (!nums.has(id)) nums.set(id, []);
      nums.get(id).push(i + 1);
    });
    for (let i = 1; i < seq.length; i++) {
      const a = rectOf(seq[i - 1]), b = rectOf(seq[i]);
      if (a && b) pathLayer.append(svg("path", { d: Lay.edgePath(a, b).d, class: `ar-flowpath${reduced() ? "" : " ar-flowpath--move"}`, "marker-end": ctx.arrow("dim") }));
    }
    for (const [id, list] of nums) {
      const el = els.nodes.get(id), r = rectOf(id);
      list.slice(0, 4).forEach((k, i) => el.querySelector(".ar-badges").append(svg("g", { class: "ar-num", transform: `translate(${r.w / 2 - 8 - i * 21},${-r.h / 2})` }, svg("circle", { r: 9.5 }), svg("text", { "text-anchor": "middle", y: 3.5 }, String(k)))));
      if (list.length > 4) el.querySelector(".ar-badges").append(svg("text", { class: "ar-more", x: r.w / 2 - 8 - 4 * 21 + 4, y: -r.h / 2 + 4 }, "+" + (list.length - 4)));
    }
    for (const [id, el] of els.nodes) el.classList.toggle("ar-node--dim", !nums.has(id));
    for (const q of els.edges) q.path.classList.toggle("ar-edge--dim", !(nums.has(q.e.a) && nums.has(q.e.b)));
  }
  place();
  const spec = { type: "layered", nodes: G.nodes.map((n) => ({ id: n.id, label: n.label, lane: n.group && !G.groupBoxes ? (ml.groups.find((g) => g.id === n.group) || {}).label : "" })), edges: G.edges.map((e) => ({ from: e.a, to: e.b, label: e.kinds.join("+") })) };
  return { el: s, size, centers, mermaid: spec, edit: { auto: base.auto } };
}

const fmtK = (n) => { n = Number(n) || 0; return n < 1000 ? String(n) : n < 100000 ? `${(Math.round(n / 100) / 10).toFixed(1)}k` : `${Math.round(n / 1000)}k`; };

/* ================================================================== a flow of steps in swimlanes (task-pipeline, daemon-approval, memory) */

function drawFlow(A, ctx) {
  const flow = A.shard.flow_data, steps = (flow.steps || []).filter((x) => x && x.id);
  const labelOf = (id) => (A.nodesById.get(id) || {}).label || id || "?";
  const items = steps.map((st) => ({ id: st.id, lane: st.actor || "?", ...Lay.stepBox(st) }));
  const edges = Model.stepEdgesOrChain(flow);
  const L = Lay.layeredLayout(items, edges, { axis: "down", laneOrder: Model.actorOrder(flow) });
  const [W, H] = [L.size[0], L.size[1] + (L.back.size ? 0 : 0)];
  const s = ctx.root(W + (L.back.size ? 70 : 0), H);
  const laneLayer = svg("g", { class: "ar-lanes" }), edgeLayer = svg("g", { class: "ar-edges" }), nodeLayer = svg("g", { class: "ar-nodes" }), centers = [];
  for (const lane of L.lanes) {
    laneLayer.append(svg("g", { class: "ar-lane" }, svg("rect", { x: lane.x, y: lane.y, width: lane.w, height: lane.h, rx: 12 }),
      svg("text", { class: "ar-lane__t", x: lane.x + lane.w / 2, y: lane.y + 20, "text-anchor": "middle" }, Lay_trim(labelOf(lane.id), Math.max(10, Math.floor(lane.w / 8))))));
  }
  const byStep = new Map(steps.map((st) => [st.id, st]));
  edges.forEach((e, i) => {
    const a = L.pos.get(e.from), b = L.pos.get(e.to);
    if (!a || !b) return;
    const back = L.back.has(i), gate = !!(byStep.get(e.to) || {}).gate;
    const r = Lay.routeEdge(a, b, { axis: "down", back });
    edgeLayer.append(svg("path", { class: `ar-edge ar-edge--${gate ? "gate" : "flow"}${back ? " ar-edge--back" : ""}`, d: r.d, "stroke-width": 2, "marker-end": ctx.arrow(gate ? "gate" : "flow") }));
  });
  steps.forEach((st, i) => {
    const r = L.pos.get(st.id), box = Lay.stepBox(st), status = st.status || "unverified", kind = st.kind || "control", gate = !!st.gate;
    const g = svg("g", { class: `ar-node ar-step ar-step--${kind}${gate ? " ar-step--gate" : ""} ar-st--${status}`, transform: `translate(${r.x},${r.y})`, "data-id": st.id });
    if (kind === "store") {
      const rx = r.w / 2, ry = 6;
      g.append(svg("path", { class: "ar-box", d: `M${-rx} ${-r.h / 2 + ry}a${rx} ${ry} 0 0 1 ${r.w} 0v${r.h - 2 * ry}a${rx} ${ry} 0 0 1 ${-r.w} 0z` }), svg("path", { class: "ar-box ar-box--line", d: `M${-rx} ${-r.h / 2 + ry}a${rx} ${ry} 0 0 0 ${r.w} 0` }));
    } else {
      g.append(svg("rect", { class: "ar-box", x: -r.w / 2, y: -r.h / 2, width: r.w, height: r.h, rx: kind === "data" ? 4 : 9 }));
      if (kind === "external") g.append(svg("rect", { class: "ar-box ar-box--inner", x: -r.w / 2 + 4, y: -r.h / 2 + 4, width: r.w - 8, height: r.h - 8, rx: 6 }));
      if (kind === "data") g.append(svg("rect", { class: "ar-databar", x: -r.w / 2, y: -r.h / 2, width: 6, height: r.h, rx: 2 }));
    }
    const tx = svg("text", { class: "ar-label ar-label--step", "text-anchor": "middle", y: -((box.lines.length + (gate ? 1 : 0) - 1) * Lay.STEP.lineH) / 2 + 4 });
    box.lines.forEach((ln, k) => tx.append(svg("tspan", { x: 0, dy: k ? Lay.STEP.lineH : 0 }, ln)));
    if (gate) tx.append(svg("tspan", { class: "ar-gate-t", x: 0, dy: Lay.STEP.lineH }, `Gate ${st.gate.tier || ""} · ${st.gate.who || ""}`.trim()));
    g.append(tx, svg("g", { class: "ar-num", transform: `translate(${-r.w / 2 + 2},${-r.h / 2 + 2})` }, svg("circle", { r: 10 }), svg("text", { "text-anchor": "middle", y: 3.5 }, String(i + 1))));
    const mk = ctx.mark(status, r.w / 2 - 2, -r.h / 2 + 2);
    if (mk) g.append(mk);
    ctx.mk(`s:${st.id}`, g, { type: "step", item: st }, `${i + 1}. ${st.title || st.id}${gate ? ", approval gate" : ""}, ${status}`);
    nodeLayer.append(g);
    centers.push({ id: `s:${st.id}`, x: r.x, y: r.y });
  });
  s.append(laneLayer, edgeLayer, nodeLayer);
  return { el: s, size: [W, H], centers, mermaid: { type: "layered", nodes: steps.map((st) => ({ id: st.id, label: st.title || st.id, lane: labelOf(st.actor) })), edges } };
}
const Lay_trim = (t, n) => (String(t).length > n ? String(t).slice(0, n - 1) + "…" : String(t));

/* ================================================================== the empty state of a lifecycle or sequence nobody has written */

function drawEmpty(A, ctx, what) {
  const s = ctx.root(760, 150);
  s.append(svg("rect", { class: "ar-empty__r", x: 10, y: 10, width: 740, height: 130, rx: 14 }),
    svg("text", { class: "ar-label", x: 380, y: 58, "text-anchor": "middle" }, `${what} is traced by Copilot from the code and has not been written yet.`),
    svg("text", { class: "ar-sub", x: 380, y: 88, "text-anchor": "middle" }, "Nothing of it is derived, so there is nothing to draw: structure views show what the code contains."),
    svg("text", { class: "ar-sub", x: 380, y: 112, "text-anchor": "middle" }, "How to write it is under the diagram."));
  return { el: s, size: [760, 150], centers: [], mermaid: { type: "layered", nodes: [], edges: [] } };
}

/* ================================================================== the page around a diagram */

function banner(A) {
  const sh = A.shard, st = Model.viewStatus(sh), flow = sh.flow_data;
  const commit = (flow && flow.commit) || sh.commit || "";
  const kids = [];
  if (sh.source !== "flow") {
    kids.push(statusBadge("derived"), h("span", { class: "ar-banner__t" }, `Drawn from the census of MiniMe ${String(commit).slice(0, 7)}. Rebuilt on every update, so it cannot be stale.`));
  } else if (!flow) {
    kids.push(statusBadge("missing"), h("span", { class: "ar-banner__t" }, "Flow not written yet: the part that is derived from the code is drawn below."));
  } else {
    const c = flow.counts || {};
    kids.push(statusBadge(st), aiBadge(),
      h("span", { class: "ar-banner__t" }, `Traced by Copilot at MiniMe ${String(commit).slice(0, 7)}`, Object.keys(c).length ? ` · ${Object.entries(c).map(([k, v]) => `${v} ${k}`).join(", ")}` : "",
        (flow.steps || flow.transitions || []).some((i) => i.confidence === "low") ? " · some steps are low confidence" : ""));
  }
  return h("div", { class: `ar-banner ar-banner--${st}`, "data-status": st }, kids);
}

function notes(A) {
  const sh = A.shard, flow = sh.flow_data, out = [];
  if (flow && flow.summary) out.push(h("p", { class: "ar-summary" }, flow.summary));
  if (flow && (flow.doc_conflicts || []).length) {
    out.push(h("div", { class: "mm-callout mm-callout--warning ar-conflicts" }, h("p", { class: "mm-callout__title" }, "The book disagrees with the code"),
      h("ul", {}, flow.doc_conflicts.map((c) => h("li", {}, h("a", { href: Model.chapterHref(c.chapter) }, c.chapter), ": ", c.note))),
      h("p", {}, "The diagram follows the code. The chapter needs correcting.")));
  }
  const miss = flow && flow.stage_check && flow.stage_check.missing;
  if (miss && miss.length) out.push(h("div", { class: "mm-callout mm-callout--note" }, h("p", { class: "mm-callout__title" }, "Incomplete"), h("p", {}, "The code registers these stages and the flow has no step for them: ", miss.map((m, i) => [i ? ", " : "", h("code", {}, m)]))));
  if (flow && (flow.unknowns || []).length) out.push(h("details", { class: "ar-unk" }, h("summary", {}, `${flow.unknowns.length} thing(s) Copilot could not confirm`), h("ul", {}, flow.unknowns.map((u) => h("li", {}, u)))));
  if (sh.source === "flow" && !flow) {
    out.push(h("div", { class: "mm-callout mm-callout--note" }, h("p", { class: "mm-callout__title" }, "How this flow gets written"), h("p", {}, h("code", {}, HOW_TO_WRITE), ".")));
    const stages = A.stages || [];
    if (stages.length) out.push(h("div", { class: "ar-stages" }, h("h4", {}, "Stages the code registers (read with ast, not guessed)"), stages.map((x) => h("p", {}, h("b", {}, x.name), x.found ? ": " : ": not found (" + (x.reason || "?") + ")", x.found ? x.items.map((it, i) => [i ? ", " : "", h("code", {}, it)]) : null))));
  }
  return out;
}

function legend(A) {
  const sw = (cls, text, title) => h("li", { title: title || null }, h("span", { class: `ar-sw ${cls}`, "aria-hidden": "true" }), text);
  const t = A.kind;
  if (t === "structure") return [sw("ar-sw--flow", "Cyan: data flows (API calls, protocol, database)"), sw("ar-sw--rel", "Violet: imports and graph links"), sw("ar-sw--decl", "Dashed: declared, nothing to count across it"), sw("ar-sw--gate", "Amber: needs your approval"), sw("ar-sw--box", "Box size: code lines"), sw("ar-sw--auto", "Dotted outline: placed automatically (not pinned)")];
  if (t === "flow" || t === "sequence" || t === "lifecycle") return [
    sw("ar-sw--flow", "Cyan: the order things happen in"), sw("ar-sw--gate", "Amber: an approval gate"),
    sw("ar-sw--stale", "Dashed outline ~: the cited code changed since this was written"), sw("ar-sw--broken", "! the cited code is gone"), sw("ar-sw--unverified", "? nothing to compare it with"),
    ...(t === "flow" ? [sw("ar-sw--data", "Bar on the left: data is handed over"), sw("ar-sw--store", "Can: a database, cache or file write"), sw("ar-sw--ext", "Double border: a network or model-provider call")] : [])];
  if (t === "catalog") return [sw("ar-sw--box", "A card is one router file; a row is one route"), sw("ar-sw--flow", "Click a row for its handler and the code")];
  return [];
}

function listFor(A) {
  const sh = A.shard, flow = sh.flow_data, lab = (id) => (A.nodesById.get(id) || {}).label || id;
  let rows = [];
  if (A.kind === "flow" || A.kind === "sequence") rows = Model.itemsOf(flow || {}).map(({ item }, i) => [String(i + 1), item.title, lab(item.actor), item.status || "", (item.evidence || []).length]);
  else if (A.kind === "lifecycle") rows = Model.itemsOf(flow || {}).map(({ item }, i) => [String(i + 1), `${item.trigger || item.id}: ${item.from} → ${item.to}`, "", item.status || "", (item.evidence || []).length]);
  if (!rows.length) return null;
  return h("details", { class: "ar-list" }, h("summary", {}, "The same as a list"),
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table" }, h("thead", {}, h("tr", {}, ["#", "Step", "Where", "Status", "Evidence"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c, i) => h(i === 0 ? "th" : "td", i === 0 ? { scope: "row" } : {}, c))))))));
}

/* ================================================================== mount */

export async function mountArch(root, opts = {}) {
  const A = {
    root, opts, uid: `ar${++UID}`, embed: !!opts.embed, edit: !!opts.edit, sel: null, prev: null, targets: new Map(), drag: { dragged: false },
    level: opts.level != null && opts.level !== "" && [0, 1, 2].includes(Number(opts.level)) ? Number(opts.level) : 1, kinds: new Set(), moved: {}, overlay: null, filter: "", result: null, svg: null,
  };
  root.classList.add("ar");
  root.dataset.arch = "loading";
  root.dataset.embed = A.embed ? "1" : "0";
  put(root, h("p", { class: "ar-wait" }, "Drawing the diagram…"));
  const L = opts.loader || LOADER;
  try {
    A.shard = await L.view(opts.view);
  } catch (err) {
    console.warn("[atlas arch]", err);
    put(root, h("p", { class: "ar-fail" }, `The view "${opts.view}" could not be loaded. `, h("code", {}, `data/arch/views/${opts.view}.json`), ". If you opened this file directly, start the local server: python scripts/serve.py, and run python scripts/arch.py build."));
    root.dataset.arch = "error";
    return null;
  }
  const sh = A.shard;
  const [model, derived, registry, index, layoutJson, linkOpts] = await Promise.all([L.model(), L.derived(), L.registry(), L.index(), A.edit ? L.layout() : null, loadLinkOptions().catch(() => ({}))]);
  Object.assign(A, { model, derived, registry, index, layoutJson, linkOpts });
  A.nodesById = new Map((sh.nodes || []).map((n) => [n.id, n]));
  const flow = sh.flow_data;
  A.kind = sh.type === "catalog" ? "catalog" : sh.type === "sequence" ? "sequence" : sh.type === "lifecycle" ? "lifecycle" : (sh.source === "flow" && flow) ? "flow" : "structure";
  A.stages = sh.source === "flow" && !flow ? Model.derivedStages(registry, derived, sh.flow) : [];
  A.summary = (flow && flow.summary) || (sh.source === "flow" ? "" : "Derived from the code.");
  const present = [...new Set((sh.edges || []).map((e) => e.kind))].sort();
  for (const k of present) if (k !== "graph") A.kinds.add(k);
  if (!A.kinds.size) for (const k of present) A.kinds.add(k);
  A.allKinds = present;

  const ctx = makeCtx(A);
  const stage = h("div", { class: "ar-stage", tabindex: -1 });
  const card = h("div", { class: "ar-card", role: "group", tabindex: -1, "aria-live": "polite", "aria-label": "Details", "data-state": "idle", on: { keydown: (ev) => { if (ev.key === "Escape" && A.sel) { ev.preventDefault(); A.select(null); } } } });
  const msg = h("span", { class: "ar-msg", role: "status" });
  const zoom = createZoom({ stage, getSvg: () => A.svg, root, labelSel: ".ar-zoomv" });
  const btn = (text, extra = {}, fn = null) => h("button", { class: "mm-btn", type: "button", ...extra, on: fn ? { click: fn } : {} }, text);
  A.stage = stage; A.card = card;

  /* ---- selection and the details card */
  const env = () => ({ linkOpts: A.linkOpts, commit: (A.shard.flow_data && A.shard.flow_data.commit) || A.shard.commit, nodes: A.nodesById, flow: A.shard.flow_data });
  A.show = () => {
    const key = A.sel || A.prev, t = key && A.targets.get(key);
    if (!t) { card.dataset.state = "idle"; put(card, h("p", { class: "ar-idle" }, A.kind === "catalog" ? "Click a route to see its handler and the code it lives in." : "Hover or focus a box to see what it is; click one to keep it open. Every box is drawn from the code.")); return; }
    const pinned = !!A.sel;
    card.dataset.state = pinned ? "pinned" : "preview";
    put(card, h("div", { class: "ar-card__head" }, h("h3", {}, titleOf(t.target)), pinned ? btn("Close", { class: "mm-btn ar-close", "aria-label": "Close the details" }, () => A.select(null)) : null),
      ...panelContent(t.target, env()), pinned ? null : h("p", { class: "ar-hint" }, "Click or press Enter to keep this open and get its links."));
  };
  const titleOf = (t) => t.type === "step" || t.type === "transition" ? (t.item.title || t.item.trigger || t.item.id) : t.type === "state" ? t.state.label : t.type === "message" ? t.message.title : t.type === "route" ? `${t.route[0]} ${t.route[1]}` : t.type === "edge" ? "Connection" : t.node.label;
  A.select = (key) => {
    const old = A.sel;
    A.sel = key && A.targets.has(key) ? key : null;
    for (const [k, t] of A.targets) { const on = k === A.sel; if (t.el.dataset.key) { t.el.classList.toggle("ar-sel", on); t.el.setAttribute("aria-pressed", on ? "true" : "false"); } }
    A.show();
    setSheet(!!A.sel, "archSheet");
    if (A.sel) card.focus({ preventScroll: true });
    else if (old && A.targets.get(old) && A.targets.get(old).el.dataset.key) A.targets.get(old).el.focus({ preventScroll: true });
  };
  A.preview = (key) => { if (A.sel || (key && isSheet())) return; A.prev = key; A.show(); };

  /* ---- drawing */
  A.draw = () => {
    const keep = A.sel;
    A.targets = new Map();
    let res;
    if (A.kind === "catalog") res = Cat.draw(ctx, Cat.groupsOf((derived && derived.catalogues && derived.catalogues.routes) || sh.catalogue || [], A.filter), 1240);
    else if (A.kind === "flow") res = drawFlow(A, ctx);
    else if (A.kind === "sequence") {
      const lab = (id) => (A.nodesById.get(id) || {}).label || id;
      if (flow && Model.itemsOf(flow).length) res = Seq.draw(ctx, Seq.prepareFlow(flow, lab), flow);
      else if (sh.flow === "m2c-protocol" && derived) res = Seq.draw(ctx, Seq.prepareProtocol(derived, sh.nodes, lab), null);
      else res = drawEmpty(A, ctx, "This sequence");
    } else if (A.kind === "lifecycle") {
      if (flow && (flow.states || []).length) res = Life.draw(ctx, Life.prepare(flow, (id) => id), flow);
      else res = drawEmpty(A, ctx, "This lifecycle");
    } else res = drawStructure(A, ctx);
    A.result = res;
    A.svg = res.el;
    put(stage, res.el);
    res.el.addEventListener("keydown", onKeys);
    zoom.set(zoom.value());
    if (keep && A.targets.has(keep)) A.select(keep); else { A.sel = null; A.show(); setSheet(false); }
    root.dataset.edit = A.edit ? "on" : "off";
    syncBar();
  };
  function onKeys(ev) {
    const dir = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" }[ev.key], cur = ev.target.closest && ev.target.closest("[data-key]");
    if (dir && cur) {
      const next = nearestInDirection(A.result.centers, cur.dataset.key, dir);
      if (next && A.targets.get(next)) { ev.preventDefault(); A.targets.get(next).el.focus(); A.targets.get(next).el.scrollIntoView({ block: "nearest", inline: "nearest" }); }
    } else if (ev.key === "Escape" && A.sel) A.select(null);
  }

  /* ---- toolbar (not in an embedded figure) */
  const bar = h("div", { class: "ar-bar", role: "toolbar", "aria-label": "Diagram controls" });
  const syncBar = () => {
    for (const b of bar.querySelectorAll("[data-level]")) b.setAttribute("aria-pressed", String(+b.dataset.level === A.level));
    for (const b of bar.querySelectorAll("[data-kind]")) b.setAttribute("aria-pressed", String(A.kinds.has(b.dataset.kind)));
  };
  if (!A.embed) {
    if (A.kind === "structure") {
      bar.append(h("span", { class: "ar-seg", role: "group", "aria-label": "Zoom level of the structure" }, LEVELS.map((l) => btn(l.text, { "data-level": l.id, title: l.title, "aria-pressed": "false" }, () => { A.level = l.id; A.draw(); }))));
      if (A.allKinds.length > 1) bar.append(h("span", { class: "ar-seg", role: "group", "aria-label": "Which connections are drawn" }, A.allKinds.map((k) => btn(KIND_TEXT[k] || k, { "data-kind": k, "aria-pressed": "false", title: `Draw ${KIND_TEXT[k] || k}` }, () => { if (A.kinds.has(k)) A.kinds.delete(k); else A.kinds.add(k); A.draw(); }))));
      if (sh.id === "unified") {
        const sel = h("select", { class: "ar-pick", "aria-label": "Lay a flow over the structure" }, h("option", { value: "" }, "No flow over it"), Model.flowChoices(index).map((f) => h("option", { value: f.id }, `${f.title} (${f.status})`)));
        sel.addEventListener("change", async () => { await setOverlay(sel.value); });
        bar.append(h("label", { class: "ar-picklab" }, "Flow: ", sel));
        A.pick = sel;
      }
    }
    if (A.kind === "catalog") {
      const inp = h("input", { class: "ar-filter", type: "search", placeholder: "Filter by method, path or handler", "aria-label": "Filter the routes" });
      inp.addEventListener("input", () => { A.filter = inp.value; A.draw(); });
      bar.append(inp);
    }
    bar.append(h("span", { class: "ar-zoom", role: "group", "aria-label": "Zoom" },
      btn("−", { "data-zoom": "out", "aria-label": "Zoom out" }, () => zoom.out()), h("span", { class: "ar-zoomv", "aria-live": "polite" }, "100 %"),
      btn("+", { "data-zoom": "in", "aria-label": "Zoom in" }, () => zoom.in()), btn("Reset", { "data-zoom": "reset" }, () => zoom.reset())));
    bar.append(btn("Export SVG", { "data-act": "svg" }, () => { download(`${sh.id}.svg`, svgText(A.svg)); msg.textContent = "SVG saved, with the colours written into it."; }),
      btn("Copy as Mermaid", { "data-act": "mermaid" }, () => copyText(Model.toMermaid(A.result.mermaid), msg, { done: "Mermaid source copied (text only; paste it into any Mermaid renderer).", manual: "Select all and copy.", label: "Mermaid source" })));
    if (A.edit && A.kind === "structure") {
      bar.append(h("span", { class: "ar-edit" }, h("b", {}, "Edit mode: "), "drag the boxes (not at level Groups), then ",
        btn("Copy JSON", { class: "mm-btn mm-btn--primary" }, () => copyText(exportPins(A.layoutJson || {}, A.moved), msg, { done: "Copied. Paste it over content/arch-layout.json.", manual: "Select all and copy, then paste it over content/arch-layout.json.", label: "content/arch-layout.json with the new pins" })),
        btn("Reset layout", {}, () => { A.moved = {}; A.draw(); })));
    }
  }

  async function setOverlay(id) {
    if (!id) { A.overlay = null; msg.textContent = ""; A.draw(); return; }
    const f = await L.flow(id);
    if (!f) { A.overlay = null; msg.textContent = "That flow is not written yet, so there is no path to draw."; if (A.pick) A.pick.value = ""; A.draw(); return; }
    A.overlay = { id, steps: Model.itemsOf(f).map(({ item }) => (item.actor ? item : { ...item, actor: (f.actors || [])[0] })) };      // a transition has no actor of its own: it happens where the lifecycle's flow does
    msg.textContent = `${f.title || id}: ${A.overlay.steps.length} steps, numbered on the boxes they happen in.`;
    A.draw();
  }

  /* ---- the page */
  const grid = h("div", { class: "ar-grid" }, h("div", { class: "ar-stagewrap" }, stage), card);
  put(root, A.embed ? null : h("h2", { class: "ar-title", id: `${A.uid}-t` }, sh.title), banner(A), ...notes(A).slice(0, A.embed ? 1 : 99), A.embed ? null : bar, msg, grid,
    A.embed ? null : h("ul", { class: "ar-legend" }, legend(A)),
    A.embed ? null : listFor(A),
    A.embed || !sh.replaces ? null : h("p", { class: "ar-legacy" }, "Legacy diagram this replaces (hand-made, not updated): ", h("a", { href: sh.replaces }, sh.replaces)));
  stage.addEventListener("keydown", onKeys);
  wirePan(stage, zoom, { blocked: () => A.edit, skip: "[data-key]" });
  A.draw();
  if (opts.flow && A.pick) { A.pick.value = opts.flow; await setOverlay(opts.flow); }
  if (opts.focus && A.targets.has(opts.focus)) A.select(opts.focus);
  root.dataset.arch = "ready";
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (A.svg && A.svg.isConnected) A.draw(); });
  document.addEventListener("minime:theme", () => { /* colours are CSS variables: nothing to redraw */ });

  return {
    root, svg: () => A.svg, size: () => A.result.size, view: sh.id, select: A.select,
    mermaid: () => Model.toMermaid(A.result.mermaid), exportSvg: () => svgText(A.svg),
    setLevel: (l) => { A.level = l; A.draw(); }, setOverlay, keys: () => [...A.targets.keys()],
    destroy: () => { put(root); root.classList.remove("ar"); delete root.dataset.arch; },
  };
}

/* ================================================================== pages */

function fail(root, msg) { put(root, h("p", { class: "ar-fail" }, msg, " If you opened this file directly, start the local server: python scripts/serve.py")); }

export async function bootPage(root) {
  const q = new URLSearchParams(location.search);
  const embed = q.get("embed") === "1";
  const theme = q.get("theme");
  if (embed) document.documentElement.dataset.archEmbed = "1";
  if (theme === "paper" || theme === "dark") document.documentElement.dataset.theme = theme;
  const model = await LOADER.model();
  if (!model) return fail(root, "The architecture model could not be loaded: data/arch/model.json.");
  const views = model.views || [];
  const id = views.some((v) => v.id === q.get("view")) ? q.get("view") : "system";
  const keep = (extra) => { const p = new URLSearchParams(location.search); p.delete("flow"); p.delete("focus"); for (const [k, v] of Object.entries(extra)) p.set(k, v); return `?${p}`; };
  const tabs = h("nav", { class: "ar-tabs", "aria-label": "Architecture views" }, views.map((v) => h("a", { class: "ar-tab", href: keep({ view: v.id }), "aria-current": v.id === id ? "page" : null, title: Model.STATUS_TEXT[v.status] || "" },
    v.title, v.status === "missing" ? h("span", { class: "ar-tab__s", "aria-label": "not written yet" }, " ∅") : v.status !== "derived" && v.status !== "fresh" ? h("span", { class: `ar-tab__s ar-tab__s--${v.status}` }, ` ${Model.STATUS_GLYPH[v.status] || ""}`) : null)));
  const host = h("div", { class: "ar-host" });
  put(root, embed ? null : tabs, host);
  await mountArch(host, { view: id, flow: q.get("flow") || "", focus: q.get("focus") || "", level: q.get("level"), embed, edit: q.get("edit") === "1", theme });
}

if (typeof document !== "undefined") {
  const start = () => {
    for (const el of document.querySelectorAll("[data-arch-view]")) {
      if (el.dataset.arch) continue;
      mountArch(el, { view: el.dataset.archView, flow: el.dataset.archFlow || "", embed: el.dataset.archEmbed === "1", edit: /[?&]edit=1(&|$)/.test(location.search) }).catch((err) => { console.warn("[atlas arch]", err); fail(el, "The diagram could not be drawn."); });
    }
    const page = document.querySelector("[data-arch-page]");
    if (page && !page.dataset.arch) bootPage(page).catch((err) => { console.warn("[atlas arch]", err); fail(page, "The diagram could not be drawn."); });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true }); else start();
}
