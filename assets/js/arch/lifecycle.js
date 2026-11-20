/* MiniMe Atlas 2 - architecture: lifecycle view (P26). States and the transitions between them.

   Same layered layout as the step flows, turned on its side: layers run left to right, the longest chain from a start state sits on
   the first row, side exits and end states below it, and a transition that goes back to an earlier state is drawn as a loop under the
   row. A transition is the thing that carries evidence, so a stale transition is dashed, not the state. */

import { layeredLayout, lifecycleLanes, routeEdge, STATE } from "./layout.js";
import { wrapText } from "./model.js";

export function prepare(flow, labelOf) {
  const states = (flow.states || []).filter((s) => s && typeof s.id === "string").map((s) => ({ id: s.id, label: s.label || s.id, terminal: !!s.terminal }));
  const ids = new Set(states.map((s) => s.id));
  const transitions = (flow.transitions || []).filter((t) => t && ids.has(t.from) && ids.has(t.to));
  return { states, transitions, labelOf };
}

export function boxOf(state) {
  const lines = wrapText(state.label, 16, 2);
  return { w: Math.max(STATE.w, Math.min(...[lines.reduce((m, l) => Math.max(m, l.length), 0) * 8 + 28, 190])), h: lines.length > 1 ? 54 : STATE.h, lines };
}

export function draw(ctx, p, flow) {
  const { svg } = ctx;
  const lanes = lifecycleLanes(p.states, p.transitions);
  const items = p.states.map((s) => ({ id: s.id, lane: String(lanes.get(s.id) || 0), ...boxOf(s) }));
  const edges = p.transitions.map((t) => ({ from: t.from, to: t.to }));
  const L = layeredLayout(items, edges, { axis: "right", laneOrder: ["0", "1"], head: 24, gapU: 150, gapV: 34, laneGap: 64, pad: 24 });
  const [W, H] = [L.size[0], L.size[1] + (L.back.size ? 40 : 0)];
  const s = ctx.root(W, H);
  const edgeLayer = svg("g", { class: "ar-edges" }), nodeLayer = svg("g", { class: "ar-nodes" }), centers = [];
  const hasIn = new Set(p.transitions.map((t) => t.to));
  p.transitions.forEach((t, i) => {
    const a = L.pos.get(t.from), b = L.pos.get(t.to);
    const r = routeEdge(a, b, { axis: "right", back: L.back.has(i) });
    const status = t.status || "unverified", gate = !!t.gate;
    const g = svg("g", { class: `ar-edge-g ar-st--${status}${gate ? " ar-msg--gate" : ""}` });
    g.append(svg("path", { class: "ar-hit", d: r.d, fill: "none", "stroke-width": 16 }),
      svg("path", { class: "ar-arrowline", d: r.d, "marker-end": ctx.arrow(gate ? "gate" : "flow") }));
    const lab = wrapText(t.trigger || t.text || t.id, 22, 2);
    const tx = svg("text", { class: "ar-edge__l", "text-anchor": "middle", x: r.mid.x, y: r.mid.y - 6 });
    lab.forEach((ln, k) => tx.append(svg("tspan", { x: r.mid.x, dy: k ? 13 : 0 }, ln)));
    g.append(tx);
    const mk = ctx.mark(status, r.mid.x + 18, r.mid.y + 10);
    if (mk) g.append(mk);
    ctx.mk(`t:${t.id}`, g, { type: "transition", item: t, fromLabel: (p.states.find((x) => x.id === t.from) || {}).label, toLabel: (p.states.find((x) => x.id === t.to) || {}).label }, `${t.trigger || t.id}: ${t.from} to ${t.to}`);
    edgeLayer.append(g);
    centers.push({ id: `t:${t.id}`, x: r.mid.x, y: r.mid.y });
  });
  for (const st of p.states) {
    const r = L.pos.get(st.id), box = boxOf(st);
    const g = svg("g", { class: `ar-node ar-state${st.terminal ? " ar-state--end" : ""}`, transform: `translate(${r.x},${r.y})` });
    g.append(svg("rect", { class: "ar-box", x: -r.w / 2, y: -r.h / 2, width: r.w, height: r.h, rx: Math.min(23, r.h / 2) }));
    if (st.terminal) g.append(svg("rect", { class: "ar-box ar-box--inner", x: -r.w / 2 + 4, y: -r.h / 2 + 4, width: r.w - 8, height: r.h - 8, rx: Math.min(19, r.h / 2 - 4) }));
    const tx = svg("text", { class: "ar-label", "text-anchor": "middle", y: box.lines.length > 1 ? -4 : 5 });
    box.lines.forEach((ln, k) => tx.append(svg("tspan", { x: 0, dy: k ? 15 : 0 }, ln)));
    g.append(tx);
    if (st.id === p.states[0].id || !hasIn.has(st.id)) g.append(svg("path", { class: "ar-start", d: `M${-r.w / 2 - 22} 0H${-r.w / 2 - 3}`, "marker-end": ctx.arrow("flow") }), svg("circle", { class: "ar-startdot", cx: -r.w / 2 - 26, cy: 0, r: 4 }));
    const inn = p.transitions.filter((t) => t.to === st.id), out = p.transitions.filter((t) => t.from === st.id);
    ctx.mk(`st:${st.id}`, g, { type: "state", state: st, in: inn, out, label: (id) => (p.states.find((x) => x.id === id) || {}).label || id }, st.label + (st.terminal ? " (end state)" : ""));
    nodeLayer.append(g);
    centers.push({ id: `st:${st.id}`, x: r.x, y: r.y });
  }
  s.append(edgeLayer, nodeLayer);
  return { el: s, size: [W, H], centers, mermaid: { type: "lifecycle", states: p.states, transitions: p.transitions.map((t) => ({ from: t.from, to: t.to, label: t.trigger || t.text || "" })) } };
}
