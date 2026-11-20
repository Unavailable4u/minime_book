/* MiniMe Atlas 2 - System page, pure helpers (P09). One ES module, no DOM, no network.

   The System page (architecture.html, assets/js/system.js) draws nothing by hand and types nothing twice: its sections come from the
   architecture model (data/arch/model.json, written by scripts/arch.py), its steps from the flows Copilot traced (with the code each one
   cites), and only the short prose around them from content/system/views.json. The functions here turn those documents into the plain lists
   the DOM layer renders, so scripts/test_system.py can test them in Node.

   A flow that is not written yet is a status ("missing"), never an error: every function here accepts null and returns something drawable. */

import { itemsOf, worstStatus, evidenceTargets, chapterHref, STATUS_ORDER } from "./arch/model.js";

export { chapterHref };

const str = (v) => typeof v === "string" && v !== "";
const arr = (v) => (Array.isArray(v) ? v : []);

export const SECTION_COUNT_KEYS = [...STATUS_ORDER, "missing"];

export const shortSha = (sha) => (str(sha) ? sha.slice(0, 7) : "unknown");

/* The sections of the page, in reading order: the views named in prose.order first, then any other view of the model (a new view appears
   without anyone editing the prose). Each section carries its prose (possibly empty) so a view without text still renders. */
export function viewSections(model, prose) {
  const views = arr(model && model.views).filter((v) => v && str(v.id));
  const byId = new Map(views.map((v) => [v.id, v]));
  const order = arr(prose && prose.order).filter((id) => byId.has(id));
  for (const v of views) if (!order.includes(v.id)) order.push(v.id);
  const texts = (prose && prose.views) || {};
  return order.map((id) => {
    const v = byId.get(id), t = texts[id] || {};
    return {
      id, title: v.title || id, type: v.type || "layered", source: v.source || "derived", flow: v.flow || null,
      status: v.status || "derived", replaces: v.replaces || null,
      what: t.what || "", reading: t.reading || "", chapters: arr(t.chapters).filter((c) => c && str(c.ref)), pages: arr(t.pages).filter((p) => p && str(p.url)),
    };
  });
}

/* What the strip at the top says: how many flows are written, how many of each status, which are missing. `index` is data/index/arch.json. */
export function flowSummary(index) {
  const flows = (index && index.flows) || {};
  const ids = Object.keys(flows);
  const counts = Object.fromEntries(SECTION_COUNT_KEYS.map((k) => [k, 0]));
  const missing = [];
  for (const id of ids) {
    const f = flows[id], st = f.status || "missing";
    counts[st in counts ? st : "unverified"] += 1;
    if (st === "missing") missing.push({ id, title: f.title || id, kind: f.kind || "" });
  }
  return { total: ids.length, written: ids.length - missing.length, counts, missing };
}

/* The place (a box of the model) an actor id stands for: its label, or the last part of its path. */
export const actorLabel = (id, nodes) => {
  const n = nodes && (nodes.get ? nodes.get(id) : nodes[id]);
  return (n && n.label) || String(id || "").split("/").filter(Boolean).pop() || "";
};

/* The numbered list under one diagram. A step flow gives its steps; a lifecycle gives its transitions (from -> to, and what triggers it).
   Everything shown is read from the flow, so nothing here can drift from the diagram above it. */
export function stepRows(flow, commit, nodes) {
  return itemsOf(flow).map(({ kind, item }, i) => {
    const row = {
      n: i + 1, id: item.id || `#${i + 1}`, type: kind, text: item.text || "",
      status: item.status || "unverified", confidence: item.confidence || "", unknowns: arr(item.unknowns).filter(str),
      evidence: evidenceTargets(item, commit),
    };
    if (kind === "transition") {
      row.title = `${item.from || "?"} \u2192 ${item.to || "?"}`;
      row.trigger = item.trigger || "";
      row.actor = "";
    } else {
      row.title = item.title || item.id || `Step ${i + 1}`;
      row.actor = item.actor ? actorLabel(item.actor, nodes) : "";
      row.gate = item.gate && typeof item.gate === "object" ? { tier: item.gate.tier || "", who: item.gate.who || "" } : null;
      row.kindText = item.kind || "";
    }
    return row;
  });
}

/* Where code and book disagree, the flow says so (it follows the code). Each conflict links to the chapter section it names. */
export function conflictRows(flow) {
  return arr(flow && flow.doc_conflicts).filter((c) => c && (str(c.note) || str(c.chapter))).map((c) => ({ chapter: c.chapter || "", href: c.chapter ? chapterHref(c.chapter) : "", note: c.note || "" }));
}

/* The status line of a flow: its own status when it has one, else the worst of its steps; "missing" when there is no flow. */
export function flowStatus(flow) {
  if (!flow) return "missing";
  return flow.status || worstStatus(itemsOf(flow).map((i) => i.item.status));
}

/* Flow-level confidence = the weakest step's: one low step is enough to say "check this against the code". */
export function flowConfidence(flow) {
  const order = ["high", "medium", "low"];
  let worst = -1;
  for (const { item } of itemsOf(flow)) { const i = order.indexOf(item.confidence); if (i > worst) worst = i; }
  return worst < 0 ? "" : order[worst];
}

/* "Anatomy of a request": the steps of flow `request-path` when it is written, otherwise the hand-drafted content/system/request-path.json
   (the one the Overview shows), so the stepper never disappears. Both end up in one shape. `source` tells the page which label to show. */
export function anatomySteps(flow, draft, commit, nodes) {
  const written = itemsOf(flow).length ? stepRows(flow, commit, nodes) : [];
  if (written.length) {
    return {
      source: "flow", intro: flow.summary || "", status: flowStatus(flow), confidence: flowConfidence(flow), commit: flow.commit || commit || "",
      steps: written.map((r) => ({ id: r.id, title: r.title, what: r.text, actor: r.actor, gate: r.gate, status: r.status, confidence: r.confidence, code: r.evidence, chapter: "", diagram: "", unknowns: r.unknowns })),
    };
  }
  const steps = arr(draft && draft.steps).filter((s) => s && str(s.id) && str(s.title));
  return {
    source: steps.length ? "draft" : "none", intro: (draft && draft.intro) || "", status: "unverified", confidence: "", commit: commit || "",
    needsReview: !!(draft && draft.needs_review), reviewNote: (draft && draft.review_note) || "",
    steps: steps.map((s) => ({
      id: s.id, title: s.title, what: s.what || "", actor: "", gate: s.gate && typeof s.gate === "object" ? { tier: s.gate.tier || "", who: s.gate.who || "" } : null,
      status: "unverified", confidence: "", chapter: s.chapter || "", diagram: s.diagram || "", unknowns: [],
      code: arr(s.code).filter((c) => c && str(c.path)).map((c) => ({ path: c.path, qual: c.qual || null, start: undefined, end: undefined, status: null, commit: commit || "" })),
    })),
  };
}

/* The view that replaces a legacy hand-made diagram ("architecture/task-sequence.html" -> "task-sequence"), or null. Lets a step of the
   hand-drafted request path keep its "See the diagram" link without pointing at a diagram that is no longer updated. */
export function viewForLegacy(model, url) {
  const v = arr(model && model.views).find((x) => x && x.replaces === url);
  return v ? v.id : null;
}

/* The first view that draws a flow (the page anchor of a flow that is not written yet), or null. */
export function viewIdForFlow(model, flowId) {
  const v = arr(model && model.views).find((x) => x && x.flow === flowId);
  return v ? v.id : null;
}

/* The shell command that writes a missing flow: shown once, next to the list of what is missing. */
export const HOW_TO_WRITE = "python scripts/arch.py todo --minime ../MiniMe, then Copilot prompt C (UPDATING.md, Step 2c), then python scripts/update_all.py";
