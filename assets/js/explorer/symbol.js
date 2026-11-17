/* MiniMe Atlas 2 - Explorer symbol panel (P14c). Everything known about one function, method or class, in one card above the symbols list.

   Shown on the Symbols tab when the address names a symbol (#/f/<path>::<qual>?tab=symbols). Sections, each only when it has content:
     header      kind, signature, badges: AI note fresh / stale, confidence, async, private, decorators
     summary     the AI note's summary, else the docstring's first line, with its source named; then the note's details
     parameters  name, type, default, description (names and types from the census, descriptions from the note)
     returns, raises, side effects
     calls       what the function calls: links for the ones the census could resolve to a file of the repo, plain names for the rest
     called by   who calls it (callers/<shard>.json), tests in a group of their own; each one a link to that symbol's panel
     methods     for a class
     evidence    the line ranges the note cites, as links into the Source tab
   Calls and callers are static and best effort (the census reads the code, it does not run it); the panel says so rather than
   implying that "no callers" means "unused". All text goes in with textContent. */
import { h, num, copyText, toast } from "./dom.js";
import { buildRoute } from "./router.js";
import { symbolDetail } from "./model.js";
import { codeLinks } from "../links.js";

const SHOW = 12;                 // callers and calls shown before "Show all"
const FRESH = { fresh: ["mm-badge mm-badge--ok", "AI note fresh"], stale: ["mm-badge mm-badge--stale", "code changed since the note"], unverified: ["mm-badge", "note freshness unknown"] };

const symHref = (path, qual, tab = "symbols") => buildRoute({ view: "file", path, qual, tab });

function sec(title, ...kids) {
  const body = kids.filter((k) => k != null && k !== false);
  return body.length ? h("section", { class: "ex-symp__sec" }, h("h4", null, title), body) : null;
}

/* A list that shows the first SHOW items and the rest behind a button. */
function more(items, draw, what) {
  const ul = h("ul", { class: "ex-symp__list" });
  const btn = h("button", { type: "button", class: "ex-link", hidden: items.length <= SHOW });
  const paint = (all) => {
    ul.replaceChildren(...(all ? items : items.slice(0, SHOW)).map(draw));
    btn.hidden = all || items.length <= SHOW;
    btn.textContent = `Show all ${num(items.length)} ${what}`;
  };
  btn.addEventListener("click", () => paint(true));
  paint(false);
  return h("div", null, ul, btn);
}

/* d: symbolDetail(); ctx: { file, here (path of this file), files (core.tree.files), linkOpts, openSymbol(path, qual) } */
function symbolLink(ctx, path, qual, label) {
  const known = ctx.files.has(path);
  const text = path === ctx.file.path ? label || qual : `${path}::${label || qual}`;
  if (!known) return h("code", { title: "not a file of this census" }, text);
  return h("a", { class: "ex-symp__ref", href: symHref(path, qual), onclick: (e) => { if (ctx.openSymbol && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); ctx.openSymbol(path, qual); } } }, text);
}

function paramsTable(d) {
  if (!d.params.length) return null;
  const rows = d.params.map((p) => h("tr", null,
    h("td", null, h("code", null, p.name), p.noteOnly ? h("span", { class: "ex-from", title: "named by the AI note; the census has no parameter list for this file" }, "note") : null),
    h("td", null, p.annotation ? h("code", null, p.annotation) : h("span", { class: "ex-dim" }, "–")),
    h("td", null, p.default ? h("code", null, p.default) : h("span", { class: "ex-dim" }, "–")),
    h("td", null, p.desc || h("span", { class: "ex-dim" }, "–"))));
  return h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact ex-symp__params" },
    h("thead", null, h("tr", null, ["Name", "Type", "Default", "Description"].map((t) => h("th", { scope: "col" }, t)))), h("tbody", null, rows)));
}

function callsSection(d, ctx) {
  if (d.kind === "class") return null;
  if (d.calls == null) return sec("Calls", h("p", { class: "ex-dim" }, "The census has no call data for this symbol (it is JavaScript, or the census is older than version 2)."));
  const linked = d.calls.filter((c) => c.target);
  const rest = d.calls.filter((c) => !c.target);
  if (!d.calls.length) return sec("Calls", h("p", { class: "ex-dim" }, "Calls nothing by name."));
  return sec(`Calls (${num(d.calls.length)})`,
    linked.length ? more(linked, (c) => h("li", null, symbolLink(ctx, c.target.path, c.target.qual), c.name !== c.target.qual && c.name !== c.target.qual.split(".").pop() ? h("span", { class: "ex-dim" }, ` as ${c.name}`) : null), "calls in the repo") : null,
    rest.length ? h("details", { class: "ex-symp__rest" }, h("summary", null, `${num(rest.length)} other name${rest.length === 1 ? "" : "s"}: libraries, built-ins, methods of objects, or calls the census could not resolve`),
      h("p", { class: "ex-chips" }, rest.map((c) => h("code", null, c.name)))) : null);
}

function calledBySection(d, ctx) {
  if (d.calledBy == null) return sec("Called by", h("p", { class: "ex-dim" }, "Caller data is not in this Atlas (data/code/callers/ is missing for this folder)."));
  if (!d.calledBy.length) return sec("Called by", h("p", { class: "ex-dim" }, "Nothing in the repo calls this by name. That does not mean it is unused: routes, decorators, callbacks, dynamic calls and code outside the census are not seen."));
  const code = d.calledBy.filter((c) => !c.test);
  const tests = d.calledBy.filter((c) => c.test);
  const draw = (c) => h("li", null, symbolLink(ctx, c.path, c.qual));
  return sec(`Called by (${num(d.calledBy.length)})`,
    code.length ? more(code, draw, "callers") : null,
    tests.length ? h("details", { class: "ex-symp__rest" }, h("summary", null, `${num(tests.length)} from tests`), more(tests, draw, "test callers")) : null);
}

export function renderSymbolPanel(ctx, input) {
  const d = symbolDetail(input);
  const links = codeLinks({ path: ctx.file.path, start: d.start, end: d.end }, ctx.linkOpts || {});
  const badges = h("p", { class: "ex-symp__badges" },
    h("span", { class: "ex-pill" }, d.kind),
    FRESH[d.fresh] ? h("span", { class: FRESH[d.fresh][0] }, FRESH[d.fresh][1]) : null,
    d.hasNote ? h("span", { class: "mm-badge mm-badge--ai" }, "AI-written") : null,
    d.confidence ? h("span", { class: "ex-pill", title: "the note's own confidence" }, `${d.confidence} confidence`) : null,
    d.visibility === "private" ? h("span", { class: "ex-pill" }, "private") : null,
    d.async ? h("span", { class: "ex-pill" }, "async") : null,
    d.decorators.map((x) => h("code", { class: "ex-symp__deco" }, String(x).startsWith("@") ? x : `@${x}`)));

  const go = h("p", { class: "ex-go" },
    h("a", { class: "mm-btn", href: buildRoute({ view: "file", path: ctx.file.path, qual: d.qual, start: d.start, end: d.end, tab: "source" }) }, "View source"),
    links.github ? h("a", { class: "mm-btn", href: links.github, target: "_blank", rel: "noopener" }, "GitHub") : null,
    links.vscode ? h("a", { class: "mm-btn", href: links.vscode }, "VS Code") : null,
    h("button", { type: "button", class: "mm-btn", onclick: async () => toast((await copyText(d.sig)) ? "Signature copied" : "Could not copy") }, "Copy signature"),
    h("button", { type: "button", class: "mm-btn", onclick: async () => toast((await copyText(`${location.href.split("#")[0]}${symHref(ctx.file.path, d.qual)}`)) ? "Link copied" : "Could not copy") }, "Copy link"));

  const root = h("section", { class: "ex-symp", "aria-label": `Symbol ${d.qual}` },
    h("h3", { class: "ex-symp__title" }, d.qual, h("span", { class: "ex-symp__where" }, ` lines ${num(d.start)}–${num(d.end)} · ${num(d.loc)} loc${d.cc != null ? ` · cc ${d.cc}` : ""}`)),
    h("pre", { class: "ex-symp__sig" }, d.sig), badges);

  if (d.fresh === "stale") root.append(h("p", { class: "ex-callout ex-callout--warn" }, "The code of this symbol has changed since its AI note was written. Read the note as a hint, not as a fact."));
  root.append(
    d.summary ? h("p", { class: "ex-symp__sum" }, d.summary, " ", h("span", { class: d.from === "note" ? "mm-badge mm-badge--ai" : "ex-from" }, d.from === "note" ? "AI note" : "docstring")) : h("p", { class: "ex-dim" }, "No description yet: this symbol has no AI note and no docstring."),
    ...(d.details ? [h("p", { class: "ex-symp__details" }, d.details)] : []), go);

  const parts = [
    sec("Parameters", paramsTable(d)),
    sec("Returns", d.returns.type || d.returns.desc ? h("p", null, d.returns.type ? h("code", null, d.returns.type) : null, d.returns.type && d.returns.desc ? " " : null, d.returns.desc || null) : null),
    sec("Raises", d.raises.length ? h("p", { class: "ex-chips" }, d.raises.map((r) => h("code", null, r))) : null),
    sec("Side effects", d.sideEffects.length ? h("ul", { class: "ex-symp__list" }, d.sideEffects.map((x) => h("li", null, x))) : null),
    sec(d.bases.length ? "Inherits from" : "", d.bases.length ? h("p", { class: "ex-chips" }, d.bases.map((b) => h("code", null, b))) : null),
    sec(`Methods (${num(d.methods.length)})`, d.methods.length ? more(d.methods, (m) => h("li", null, symbolLink(ctx, ctx.file.path, m.qual, m.name), h("span", { class: "ex-dim" }, ` lines ${m.start}–${m.end}`)), "methods") : null),
    callsSection(d, ctx),
    calledBySection(d, ctx),
    sec("Evidence cited by the note", d.evidence.length ? h("p", { class: "ex-chips" }, d.evidence.map((e) => h("a", { href: buildRoute({ view: "file", path: ctx.file.path, qual: d.qual, start: e.start, end: e.end, tab: "source" }) }, e.end > e.start ? `lines ${e.start}–${e.end}` : `line ${e.start}`))) : null),
  ];
  root.append(...parts.filter(Boolean));                         // Node.append(null) would write the text "null"
  return root;
}
