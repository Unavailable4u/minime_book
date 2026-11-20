/* MiniMe Atlas 2 - architecture: sequence view (P26). One lifeline per actor, one message per step.

   The message of step n goes from the actor of step n-1 to the actor of step n (the first step is a loop on its own actor): a flow
   is "who hands over to whom", and the steps are already in execution order. Without a flow (m2c-protocol before its flow is written)
   the messages of the contract itself are drawn, device to server and back, in the order protocol/v1 lists them; they are derived,
   so they carry no evidence and cannot be stale. */

import { SEQ, sequenceLayout } from "./layout.js";
import { itemsOf, protocolMessages, PROTOCOL_ENDS } from "./model.js";

/* -> { actors: [{id, label}], messages: [{id, from, to, label, gate, status, target}] } from an evaluated flow */
export function prepareFlow(flow, labelOf) {
  const actors = [], seen = new Set(), messages = [];
  const add = (id) => { if (id && !seen.has(id)) { seen.add(id); actors.push({ id, label: labelOf(id) }); } };
  let prev = null;
  for (const { item } of itemsOf(flow)) {
    add(item.actor);
    const from = prev || item.actor;
    messages.push({ id: item.id, from, to: item.actor, label: item.title || item.id, gate: item.gate ? `${item.gate.tier || ""} ${item.gate.who || ""}`.trim() : null, status: item.status || "unverified", kind: item.kind,
      target: { type: "step", item } });
    prev = item.actor;
  }
  // a message must start on a lifeline: the first one draws a loop on its own actor, so `from` is always an actor too
  return { actors, messages: messages.filter((m) => seen.has(m.from) && seen.has(m.to)) };
}

const ends_client = () => PROTOCOL_ENDS[0];

/* -> the same shape from the protocol catalogue (derived.json) */
export function prepareProtocol(derived, nodes, labelOf) {
  const p = protocolMessages(derived, nodes);
  const ends = [p.client, p.server];
  return {
    actors: ends.map((id) => ({ id, label: id === "client" || id === ends_client(nodes) ? "M2C client" : id === "server" ? "MiniMe server" : labelOf(id) })),
    messages: p.messages.map((m) => ({ id: m.id, from: m.actor, to: m.to, label: m.title, gate: null, status: "derived", kind: "data", target: { type: "message", message: m } })),
    derived: true,
  };
}

/* ctx: the helpers render.js passes (svg builders, ctx.mk to make an element interactive, ctx.root(W, H) for the <svg>, ctx.arrow(name)). */
export function draw(ctx, prepared, flow) {
  const { svg } = ctx;
  const L = sequenceLayout(prepared.actors, prepared.messages);
  const [W, H] = L.size;
  const s = ctx.root(W, H);
  const life = svg("g", { class: "ar-lifelines" }), msgs = svg("g", { class: "ar-messages" }), heads = svg("g", { class: "ar-heads" });
  const centers = [];
  for (const a of prepared.actors) {
    const x = L.cols.get(a.id);
    life.append(svg("line", { class: "ar-lifeline", x1: x, y1: SEQ.pad + SEQ.head, x2: x, y2: H - SEQ.pad }));
    const w = Math.min(L.colW - 24, Math.max(110, a.label.length * 8 + 24));
    heads.append(svg("g", { class: "ar-head", transform: `translate(${x},${SEQ.pad + SEQ.head / 2})` },
      svg("rect", { class: "ar-box", x: -w / 2, y: -SEQ.head / 2 + 6, width: w, height: SEQ.head - 12, rx: 9 }),
      svg("text", { class: "ar-label", "text-anchor": "middle", y: 5 }, a.label)));
  }
  prepared.messages.forEach((m, i) => {
    const r = L.rows[i];
    if (!r || r.id !== m.id) return;
    const gate = !!m.gate, y = r.y;
    const g = svg("g", { class: `ar-msg ar-st--${m.status}${gate ? " ar-msg--gate" : ""}` });
    let d, mx, labelAnchor = "middle", lx;
    if (r.self) { const x = r.x1; d = `M${x} ${y - 12}h34v24h-34`; mx = x + 40; lx = mx; labelAnchor = "start"; }
    else { d = `M${r.x1} ${y}L${r.x2} ${y}`; lx = (r.x1 + r.x2) / 2; mx = lx; }
    const line = svg("path", { class: "ar-arrowline", d, "marker-end": ctx.arrow(gate ? "gate" : "flow") });
    const hit = svg("path", { class: "ar-hit", d, "stroke-width": 16, fill: "none" });
    const t = svg("text", { class: "ar-msg__t", "text-anchor": labelAnchor, x: lx, y: r.top + 12 });
    r.lines.forEach((ln, k) => t.append(svg("tspan", { x: lx, dy: k ? SEQ.lineH : 0 }, ln)));
    if (m.gate) t.append(svg("tspan", { class: "ar-gate-t", x: lx, dy: SEQ.lineH }, `Gate ${m.gate}`));
    const num = svg("g", { class: "ar-num", transform: `translate(${r.self ? r.x1 - 14 : Math.min(r.x1, r.x2) + 14},${y - 12})` }, svg("circle", { r: 10 }), svg("text", { "text-anchor": "middle", y: 3.5 }, String(i + 1)));
    g.append(hit, line, t, num);
    const mark = ctx.mark(m.status, lx + (r.self ? 0 : 0), y + 14);
    if (mark) g.append(mark);
    ctx.mk(`m:${m.id}`, g, m.target, `${i + 1}. ${m.label}`);
    msgs.append(g);
    centers.push({ id: `m:${m.id}`, x: lx, y });
  });
  s.append(life, heads, msgs);
  return { el: s, size: [W, H], centers, mermaid: { type: "sequence", actors: prepared.actors, messages: prepared.messages } };
}
