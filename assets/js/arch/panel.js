/* MiniMe Atlas 2 - architecture details panel (P26). One ES module.

   What a click on a box, a step, a state, a route or a message shows: the text, the status of the cited code, the confidence,
   an "AI-written" label for everything a flow says (flows are traced by Copilot; the structure is derived by script, so it has none),
   and the code it cites with one link per way of getting there: Explorer, raw source, GitHub, VS Code (assets/js/links.js codeLinks).
   The panel is a column beside the diagram on a wide screen and a bottom sheet on a phone (arch.css). */

import { h } from "../svgview.js";
import { codeLinks } from "../links.js";
import { STATUS_TEXT, STATUS_GLYPH, CONFIDENCE_TEXT, evidenceTargets, chapterHref } from "./model.js";

const GITHUB = "https://github.com/Unavailable4u/MiniMe";
const fmtN = (n) => Number(n || 0).toLocaleString("en-US");

export const statusBadge = (status) => h("span", { class: `mm-badge ar-status ar-status--${status}`, title: STATUS_TEXT[status] || "" }, STATUS_GLYPH[status] ? `${STATUS_GLYPH[status]} ` : "", status);
export const aiBadge = () => h("span", { class: "mm-badge mm-badge--ai", title: "Written by Copilot from the code, with the evidence below. Read it against the code before relying on it." }, "AI-written");

function fact(label, value) { return [h("dt", {}, label), h("dd", {}, value)]; }

/* The four buttons for one place in the code. `opts` is loadLinkOptions() (repo, commit, vscode root, embedded files). */
export function linkRow(target, opts) {
  const l = codeLinks(target, opts || {});
  const btn = (href, text, ext) => h("a", { class: "mm-btn ar-lb", href, ...(ext ? { target: "_blank", rel: "noopener" } : {}) }, text);
  return h("span", { class: "ar-links" },
    l.explorer ? btn(l.explorer, "Explorer") : null,
    l.src ? btn(l.src, "Source", true) : null,
    l.github ? btn(l.github, "GitHub", true) : null,
    l.vscode ? btn(l.vscode, "VS Code") : null);
}

function evidenceList(item, commit, opts) {
  const list = evidenceTargets(item, commit);
  if (!list.length) return null;
  return h("div", { class: "ar-evid" },
    h("h4", {}, "Evidence in the code"),
    h("ul", {}, list.map((t) => h("li", {},
      h("code", {}, t.qual ? `${t.path}::${t.qual}` : t.path),
      t.start != null ? h("span", { class: "ar-lines" }, ` lines ${t.start}–${t.end}`) : null,
      t.status && t.status !== "fresh" ? h("span", { class: `ar-status ar-status--${t.status} ar-evid__s`, title: STATUS_TEXT[t.status] }, ` ${t.status}`) : null,
      linkRow(t, opts)))));
}

/* env: { linkOpts, commit, nodes: Map id -> node, flow }.  target: {type, ...} as the renderers register it. -> [elements] */
export function panelContent(target, env) {
  const nodeLabel = (id) => (env.nodes && env.nodes.get(id) ? env.nodes.get(id).label : id);
  const T = target.type;
  if (T === "step" || T === "transition") {
    const it = target.item, flow = env.flow || {}, gate = it.gate;
    return [
      h("p", { class: "ar-crumb" }, flow.title || "Flow", " · ", T === "step" ? `step ${it.id}` : `transition ${it.id}`),
      h("div", { class: "ar-badges" }, statusBadge(it.status || "unverified"), aiBadge(), it.confidence ? h("span", { class: `mm-badge ar-conf ar-conf--${it.confidence}`, title: CONFIDENCE_TEXT[it.confidence] || "" }, it.confidence) : null),
      it.text ? h("p", { class: "ar-what" }, it.text) : null,
      gate ? h("p", { class: "ar-gatenote" }, h("b", {}, "Approval gate"), ` ${gate.tier || ""} · decided by ${gate.who || "?"}`) : null,
      h("dl", { class: "ar-facts" },
        it.actor ? fact("Where", nodeLabel(it.actor)) : null,
        it.kind && T === "step" ? fact("Kind", it.kind) : null,
        T === "transition" ? fact("Moves", `${target.fromLabel || it.from} → ${target.toLabel || it.to}`) : null,
        T === "transition" && it.trigger ? fact("Trigger", it.trigger) : null,
        it.subflow ? fact("Continues in", h("code", {}, it.subflow)) : null),
      evidenceList(it, flow.commit || env.commit, env.linkOpts),
      (it.unknowns || []).length ? h("div", { class: "ar-unk" }, h("h4", {}, "Not confirmed"), h("ul", {}, it.unknowns.map((u) => h("li", {}, u)))) : null,
      h("p", { class: "ar-hint" }, STATUS_TEXT[it.status || "unverified"]),
    ];
  }
  if (T === "state") {
    const s = target.state;
    return [
      h("p", { class: "ar-crumb" }, (env.flow && env.flow.title) || "Lifecycle", " · state"),
      h("div", { class: "ar-badges" }, aiBadge(), s.terminal ? h("span", { class: "mm-badge" }, "end state") : null),
      h("p", { class: "ar-what" }, s.label || s.id),
      target.in.length ? h("div", {}, h("h4", {}, "Reached by"), h("ul", { class: "ar-tlist" }, target.in.map((t) => h("li", {}, `${target.label(t.from)} — ${t.trigger || t.text || t.id}`)))) : h("p", { class: "ar-hint" }, "A start state: nothing moves into it."),
      target.out.length ? h("div", {}, h("h4", {}, "Leaves by"), h("ul", { class: "ar-tlist" }, target.out.map((t) => h("li", {}, `${t.trigger || t.text || t.id} → ${target.label(t.to)}`)))) : h("p", { class: "ar-hint" }, "Nothing leaves this state."),
    ];
  }
  if (T === "message") {
    const m = target.message;
    return [
      h("p", { class: "ar-crumb" }, "M2C protocol · message"),
      h("div", { class: "ar-badges" }, h("span", { class: "mm-badge ar-status ar-status--derived", title: STATUS_TEXT.derived }, "derived")),
      h("p", { class: "ar-what" }, m.title),
      h("dl", { class: "ar-facts" }, fact("Direction", m.direction === "server_to_client" ? "server to device" : "device to server"), fact("From", nodeLabel(m.actor)), fact("To", nodeLabel(m.to))),
      h("p", { class: "ar-actions" }, h("a", { class: "mm-btn mm-btn--primary", href: "protocol.html" }, "Fields of this message on the Protocol page")),
      h("p", { class: "ar-hint" }, "Listed in the order protocol/v1 declares them, not the order of a run: the run itself needs the m2c-protocol flow."),
    ];
  }
  if (T === "route") {
    const [method, path, handler, line, model] = target.route, g = target.group;
    const t = { path: g.file, start: line || undefined, end: undefined, commit: env.commit };
    return [
      h("p", { class: "ar-crumb" }, "API surface · ", g.router || g.file),
      h("div", { class: "ar-badges" }, h("span", { class: "mm-badge ar-status ar-status--derived", title: STATUS_TEXT.derived }, "derived")),
      h("p", { class: "ar-what" }, h("b", { class: `ar-m ar-m--${String(method).toLowerCase()}` }, method), " ", h("code", {}, path)),
      h("dl", { class: "ar-facts" }, fact("Handler", h("code", {}, handler)), fact("File", h("code", {}, `${g.file}${line ? `:${line}` : ""}`)), model ? fact("Response", h("code", {}, model)) : null, g.prefix ? fact("Router prefix", h("code", {}, g.prefix)) : null),
      h("p", { class: "ar-actions" }, linkRow(t, env.linkOpts)),
      h("p", { class: "ar-hint" }, h("a", { href: "api.html" }, "All routes with their callers and notes are on the API page.")),
    ];
  }
  if (T === "edge") {
    const e = target.edge;
    return [
      h("p", { class: "ar-crumb" }, "Connection"),
      h("p", { class: "ar-what" }, `${nodeLabel(e.a)} and ${nodeLabel(e.b)}`),
      h("dl", { class: "ar-facts" },
        fact("Kinds", e.kinds.join(", ")),
        e.weight ? fact("Weight", `${fmtN(e.weight)} (imports, graph links or call sites, summed over the kinds)`) : fact("Weight", "declared in content/topology.json; the code has nothing to count across it"),
        e.labels.length ? fact("Declared as", e.labels.join(", ")) : null,
        e.gate ? fact("Gate", "needs your approval before anything crosses it") : null),
      h("p", { class: "ar-hint" }, "Derived from the census and the declared links; this cannot be stale."),
    ];
  }
  // node or group
  const n = target.node, commit = env.commit || "main";
  const folder = (n.folders || [])[0];
  const links = [];
  if (folder) {
    const ex = codeLinks({ path: folder }, env.linkOpts || {}).explorer;
    if (ex) links.push(h("a", { class: "mm-btn mm-btn--primary", href: ex }, "Open ", h("code", {}, folder), " in the Explorer"));
    links.push(h("a", { class: "mm-btn", href: `${GITHUB}/tree/${commit}/${folder.split("/").map(encodeURIComponent).join("/")}`, target: "_blank", rel: "noopener" }, "Folder on GitHub"));
  }
  if (n.chapter) links.push(h("a", { class: "mm-btn", href: chapterHref(n.chapter) }, "Read it in the book"));
  return [
    h("p", { class: "ar-crumb" }, n.kind === "group" ? "Group" : n.kind === "container" ? "Folder of the repository" : n.kind),
    h("div", { class: "ar-badges" }, h("span", { class: "mm-badge ar-status ar-status--derived", title: STATUS_TEXT.derived }, "derived")),
    n.what ? h("p", { class: "ar-what" }, n.what) : null,
    h("dl", { class: "ar-facts" },
      (n.folders || []).length ? fact("Folders", n.folders.map((f) => h("code", {}, f))) : null,
      n.files != null ? fact("Size", `${fmtN(n.code)} code lines in ${fmtN(n.files)} files, ${fmtN(n.functions)} functions`) : null,
      target.degree != null ? fact("Connections", `${target.degree} drawn here`) : null,
      n.kind === "store" || n.kind === "external" ? fact("Kind", n.kind === "store" ? "a store (declared in content/arch-layout.json)" : "an outside service (declared in content/arch-layout.json)") : null),
    links.length ? h("div", { class: "ar-actions" }, links) : null,
    n.diagram ? h("p", { class: "ar-hint" }, "Hand-made diagram (legacy, not updated): ", h("a", { href: n.diagram }, n.diagram)) : null,
  ];
}
