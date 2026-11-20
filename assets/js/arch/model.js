/* MiniMe Atlas 2 - architecture model, browser side (P26). One ES module, no dependencies, no DOM.

   Reads what scripts/arch.py (P25) writes and gives the renderers the few facts they share:
     data/arch/views/<view id>.json   one small shard per view (nodes, edges, pins; for a flow view the evaluated flow as flow_data)
     data/arch/derived.json           catalogues (protocol messages, routes) and the stage lists read out of the code (only fetched when needed)
     data/index/arch.json             status of every flow (the flow picker)
     content/arch-flows.json          the registry: which flow has which extractors
     content/arch-layout.json         the hand-kept layout, for edit mode's Copy JSON
   Nothing here is typed by hand: a missing flow is a status ("missing"), never a reason to fail.

   Pure helpers are exported so scripts/test_arch_render.py can run them in Node with no browser. */

export const FLOW_EDGE_KINDS = ["api-call", "protocol", "db", "env", "declared"];     // data flows (cyan); import and graph are relations (violet)
export const STATUS_ORDER = ["fresh", "unverified", "stale", "broken"];                // worst last, as in scripts/arch.py
export const STATUS_TEXT = {
  fresh: "Fresh: the cited code is unchanged since this was written.",
  unverified: "Unverified: there was nothing to compare the cited code with.",
  stale: "Stale: the cited code changed after this was written.",
  broken: "Broken: the cited file or function no longer exists.",
  missing: "Not written yet: only the structure that is derived from the code is drawn.",
  derived: "Derived from the code by script; it cannot be stale.",
};
export const STATUS_GLYPH = { fresh: "", unverified: "?", stale: "~", broken: "!", missing: "", derived: "" };
export const CONFIDENCE_TEXT = { high: "High confidence", medium: "Medium confidence", low: "Low confidence: check this against the code" };

const str = (v) => typeof v === "string" && v !== "";

/* ------------------------------------------------------------------ flows */

/* [{kind: "step" | "transition", item}] : everything of a flow that carries evidence. A lifecycle has transitions, the others steps. */
export function itemsOf(flow) {
  if (!flow || typeof flow !== "object") return [];
  if (flow.kind === "lifecycle") return (flow.transitions || []).filter((t) => t && typeof t === "object").map((item) => ({ kind: "transition", item }));
  return (flow.steps || []).filter((s) => s && typeof s === "object").map((item) => ({ kind: "step", item }));
}

export const worstStatus = (list) => {
  const ok = (list || []).filter((s) => STATUS_ORDER.includes(s));
  return ok.length ? ok.reduce((a, b) => (STATUS_ORDER.indexOf(b) > STATUS_ORDER.indexOf(a) ? b : a)) : "unverified";
};

/* Status of the view as a whole: "derived" for a derived view, "missing" when the flow is not written, else the flow's worst step. */
export function viewStatus(shard) {
  if (!shard) return "missing";
  if (shard.source !== "flow") return "derived";
  return shard.flow_data ? (shard.flow_data.status || worstStatus(itemsOf(shard.flow_data).map((i) => i.item.status))) : "missing";
}

/* Actors in the order a reader meets them: the flow's own `actors` order first, then any step actor it forgot to list. */
export function actorOrder(flow) {
  const out = [];
  const add = (a) => { if (str(a) && !out.includes(a)) out.push(a); };
  for (const a of (flow && flow.actors) || []) add(a);
  for (const { item } of itemsOf(flow)) add(item.actor);
  return out;
}

/* Actors in the order the steps run (array order = execution order), consecutive repeats dropped. Used for sequence lifelines
   and for the path a flow draws over the unified view. */
export function flowActorPath(flow) {
  const seq = [];
  for (const { item } of itemsOf(flow)) if (str(item.actor) && seq[seq.length - 1] !== item.actor) seq.push(item.actor);
  return seq;
}

/* [{id, from, to}] edges of a step flow: `next` links, in step order. A `next` to an unknown id is dropped. */
export function stepEdges(flow) {
  const ids = new Set(itemsOf(flow).map((i) => i.item.id));
  const out = [];
  for (const { item } of itemsOf(flow)) for (const to of Array.isArray(item.next) ? item.next : []) if (ids.has(to) && to !== item.id) out.push({ from: item.id, to });
  return out;
}

/* A step flow that gives no `next` at all still reads top to bottom: chain the steps in order. */
export function stepEdgesOrChain(flow) {
  const e = stepEdges(flow);
  if (e.length || !(flow && flow.steps)) return e;
  const ids = flow.steps.map((s) => s && s.id).filter(str);
  return ids.slice(1).map((to, i) => ({ from: ids[i], to }));
}

/* The code an item cites, ready for codeLinks(): lines [first, last] become start / end; the flow's commit pins GitHub links. */
export function evidenceTargets(item, commit) {
  const out = [];
  for (const e of (item && item.evidence) || []) {
    if (!e || !str(e.path)) continue;
    const l = Array.isArray(e.lines) && e.lines.length === 2 && e.lines.every(Number.isFinite) ? e.lines : null;
    out.push({ path: e.path, qual: e.qual || null, start: l ? l[0] : undefined, end: l ? l[1] : undefined, status: e.status || null, commit: commit || "" });
  }
  return out;
}

/* ------------------------------------------------------------------ text */

/* Word-wrap into at most maxLines lines of about maxChars; the last line ends with an ellipsis when text is cut. */
export function wrapText(text, maxChars, maxLines = 3) {
  const words = String(text == null ? "" : text).split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = "";
  for (const w0 of words) {
    let w = w0;
    while (w.length > maxChars) {                                   // a very long token (a path) is cut, not allowed to widen the box
      if (cur) { lines.push(cur); cur = ""; }
      lines.push(w.slice(0, maxChars)); w = w.slice(maxChars);
    }
    if (!cur) cur = w;
    else if ((cur + " " + w).length <= maxChars) cur += " " + w;
    else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  if (lines.length > maxLines) {
    const keep = lines.slice(0, maxLines);
    const last = keep[maxLines - 1];
    keep[maxLines - 1] = (last.length >= maxChars ? last.slice(0, maxChars - 1) : last) + "…";
    return keep;
  }
  return lines.length ? lines : [""];
}

/* Width of a text in diagram units without asking the browser (so layout is identical everywhere, and testable). */
export const textWidth = (text, px = 13, mono = false) => Math.ceil(String(text == null ? "" : text).length * px * (mono ? 0.6 : 0.56));

/* ------------------------------------------------------------------ stages found in the code (derived part of a flow) */

/* The lists the code registers for a flow (router tiers, the agent registry), from the registry's `extractors` and derived.json:
   [{id, name, file, found, reason, items: [text]}]. A flow with no extractor gives []. */
export function derivedStages(registry, derived, flowId) {
  const reg = ((registry && registry.flows) || []).find((f) => f && f.id === flowId);
  const wanted = ((reg && reg.extractors) || []).map((e) => e.id);
  const out = [];
  for (const x of (derived && derived.extractions) || []) {
    if (!wanted.includes(x.id)) continue;
    const items = (x.items || []).map((it) => (typeof it === "string" ? it : Array.isArray(it) ? it.join(" → ") : it && it.key != null ? `${it.key}: ${(it.items || []).join(", ")}` : JSON.stringify(it)));
    out.push({ id: x.id, name: x.name || x.id, file: x.file || null, found: x.found !== false, reason: x.reason || null, items });
  }
  return out;
}

/* ------------------------------------------------------------------ protocol sequence (derived part of m2c-protocol) */

export const PROTOCOL_ENDS = ["m2c/src/m2c/link", "backend/codeagent"];   // the two ends of the wire, when the model has them

/* Messages of the contract in the order protocol.json lists them, as pseudo steps a sequence can draw. */
export function protocolMessages(derived, nodes) {
  const cat = (derived && derived.catalogues && derived.catalogues.protocol) || {};
  const ids = new Set((nodes || []).map((n) => n.id));
  const [client, server] = PROTOCOL_ENDS.map((id, i) => (ids.has(id) ? id : ["client", "server"][i]));
  const messages = (cat.messages || []).map((m, i) => {
    const toServer = m.direction !== "server_to_client";
    return { id: `m${String(i + 1).padStart(2, "0")}`, title: m.type, actor: toServer ? client : server, to: toServer ? server : client, kind: "data", derived: true, direction: m.direction, text: `${m.type}: ${toServer ? "device to server" : "server to device"}` };
  });
  return { client, server, messages, tools: cat.tools || [] };
}

/* ------------------------------------------------------------------ Copy as Mermaid (text only: Mermaid is not loaded for this) */

const mmId = (i) => `n${i}`;
export const mmText = (s) => String(s == null ? "" : s).replace(/"/g, "'").replace(/[\r\n]+/g, " ").replace(/[<>]/g, "").slice(0, 80);

/* spec: {type, title, nodes: [{id, label, lane?}], edges: [{from, to, label?}], actors, messages, states, transitions, groups}.
   Built by the renderers (which know what they drew); this turns it into Mermaid source. */
export function toMermaid(spec) {
  const t = spec.type;
  if (t === "sequence") {
    const lines = ["sequenceDiagram"];
    const idx = new Map();
    spec.actors.forEach((a, i) => { idx.set(a.id, i); lines.push(`  participant p${i} as ${mmText(a.label)}`); });
    for (const m of spec.messages) {
      const a = idx.get(m.from), b = idx.get(m.to);
      if (a == null || b == null) continue;
      lines.push(`  p${a}->>p${b}: ${mmText(m.label)}`);
      if (m.gate) lines.push(`  Note over p${b}: gate ${mmText(m.gate)}`);
    }
    return lines.join("\n") + "\n";
  }
  if (t === "lifecycle") {
    const lines = ["stateDiagram-v2"];
    const ids = new Map(spec.states.map((s, i) => [s.id, `s${i}`]));
    for (const s of spec.states) lines.push(`  ${ids.get(s.id)} : ${mmText(s.label)}`);
    const incoming = new Set(spec.transitions.map((x) => x.to));
    spec.states.forEach((s, i) => { if (i === 0 || !incoming.has(s.id)) lines.push(`  [*] --> ${ids.get(s.id)}`); });   // the first state is a start even when a retry leads back into it
    for (const x of spec.transitions) if (ids.has(x.from) && ids.has(x.to)) lines.push(`  ${ids.get(x.from)} --> ${ids.get(x.to)}${x.label ? " : " + mmText(x.label) : ""}`);
    for (const s of spec.states) if (s.terminal) lines.push(`  ${ids.get(s.id)} --> [*]`);
    return lines.join("\n") + "\n";
  }
  const lines = ["flowchart LR"];
  const idx = new Map(spec.nodes.map((n, i) => [n.id, mmId(i)]));
  const lanes = new Map();
  spec.nodes.forEach((n) => { const k = n.lane || ""; if (!lanes.has(k)) lanes.set(k, []); lanes.get(k).push(n); });
  let g = 0;
  for (const [lane, list] of lanes) {
    if (lane && lanes.size > 1) lines.push(`  subgraph g${g++}["${mmText(lane)}"]`);
    for (const n of list) lines.push(`${lane && lanes.size > 1 ? "    " : "  "}${idx.get(n.id)}["${mmText(n.label)}"]`);
    if (lane && lanes.size > 1) lines.push("  end");
  }
  for (const e of spec.edges) if (idx.has(e.from) && idx.has(e.to)) lines.push(`  ${idx.get(e.from)} -->${e.label ? `|${mmText(e.label)}|` : ""} ${idx.get(e.to)}`);
  return lines.join("\n") + "\n";
}

/* ------------------------------------------------------------------ loading */

/* A loader that remembers what it fetched. `getJSON(rel)` is injected so Node can use files and the page can use fetch. */
export function makeLoader(getJSON) {
  const cache = new Map();
  const get = (rel, soft = true) => {
    if (!cache.has(rel)) cache.set(rel, Promise.resolve().then(() => getJSON(rel)).catch((err) => { if (!soft) throw err; return null; }));
    return cache.get(rel);
  };
  return {
    model: () => get("data/arch/model.json"),
    view: (id) => get(`data/arch/views/${encodeURIComponent(id)}.json`, false),
    derived: () => get("data/arch/derived.json"),
    index: () => get("data/index/arch.json"),
    registry: () => get("content/arch-flows.json"),
    layout: () => get("content/arch-layout.json"),
    /* The evaluated flow of any registered flow id: the shard of a view that draws it carries it as flow_data. null when not written. */
    async flow(id) {
      const idx = await this.index();
      const entry = idx && idx.flows && idx.flows[id];
      for (const v of (entry && entry.views) || []) {
        const shard = await get(`data/arch/views/${encodeURIComponent(v)}.json`);
        if (shard && shard.flow_data) return shard.flow_data;
      }
      return null;
    },
  };
}

/* The list for the flow picker: every flow of the index with its status, written ones first in registry order. */
export function flowChoices(index) {
  const flows = (index && index.flows) || {};
  return Object.keys(flows).map((id) => ({ id, title: flows[id].title || id, kind: flows[id].kind, status: flows[id].status || "missing", views: flows[id].views || [] }));
}

/* "doc-minime-feature-guide#orchestrator" -> "doc-minime-feature-guide.html#orchestrator" */
export const chapterHref = (ref) => { const [id, frag] = String(ref).split("#"); return `${id}.html${frag ? "#" + frag : ""}`; };
