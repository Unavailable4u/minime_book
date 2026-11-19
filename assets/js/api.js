/* MiniMe Atlas 2 - the API page (P17). Loaded by api.html, which is a shell: this module draws everything from
     data/code/routes.json   every route, with the frontend files that call it (refresh_atlas.py writes the routes, refresh_graph.py the callers)
     data/index/notes.json, data/notes/<file>.json   the AI note of the handler's file, only for the route on screen
     data/index/mentions.json   the chapter sections that name the handler
   The pure logic is in codepages.js (Node tests it). A caller is shown only when the scan found it, and always as inferred. */
import { h } from "./explorer/dom.js";
import * as P from "./codepages.js";
import { getJSON, empty, badge, kpiGrid, barsCard, freshLine, section, linkRow, copyButton, noteSection, bookSection, makeTable } from "./codeui.js";
import { loadLinkOptions, codeLinks } from "./links.js";

const COLS = [
  { id: "method", label: "Method", get: (r) => r.method, render: (r) => h("span", { class: `cp-method cp-method--${r.method.toLowerCase()}` }, r.method) },
  { id: "path", label: "Path", get: (r) => r.path, mono: true },
  { id: "handler", label: "Handler", get: (r) => r.handler, mono: true },
  { id: "file", label: "File", get: (r) => r.short, mono: true },
  { id: "line", label: "Line", get: (r) => r.line, num: true },
  { id: "deps", label: "Auth / deps", get: (r) => r.depsText },
  { id: "model", label: "Response model", get: (r) => r.response_model || "", mono: true },
  { id: "called", label: "Frontend callers", get: (r) => r.called, num: true },
];
const rowText = (r) => [r.method, r.path, r.handler, r.file, r.depsText, r.response_model || "", ...(r.callers || []).map((c) => c.file)].join(" ");
const VIA_BADGE = {
  0: ["ok", "method named", "The best path match, and the code names this HTTP method."],
  1: ["here", "best path match", "The best path match; the code names no HTTP method."],
  2: ["stale", "path shape only", "Only the shape of the path matched. A weaker guess: the HTTP method is ignored."],
};

function callersSection(r, doc) {
  const scan = P.scanInfo(doc);
  const sorted = (r.callers || []).slice().sort((a, b) => P.viaRank(a.via) - P.viaRank(b.via) || (a.file < b.file ? -1 : a.file > b.file ? 1 : 0));
  const items = sorted.map((c) => {
    const [kind, text] = VIA_BADGE[P.viaRank(c.via)] || ["stale", "unknown"];
    return h("li", null, h("a", { href: P.explorerHref(c.file) }, h("code", null, P.baseName(c.file))), " ", h("span", { class: "cp-dim" }, c.file.replace(/^frontend\//, "").replace(/[^/]*$/, "")), " ", badge(kind, text, P.viaText(c.via)));
  });
  return section(`Frontend callers (${sorted.length})`,
    sorted.length ? h("ul", { class: "cp-list" }, items) : h("p", { class: "cp-dim" }, "No frontend file was found calling this route."),
    h("p", { class: "cp-dim cp-caveat" }, P.CALLERS_CAVEAT), h("p", { class: scan.stale ? "cp-dim cp-fresh__stale" : "cp-dim" }, scan.text));
}

function chainSection(r) {
  const chain = P.prefixChain(r);
  return section("Where the path comes from", h("ol", { class: "cp-chain" }, chain.map((c) => h("li", null, h("span", { class: "cp-dim" }, c.label), " ", h("code", null, c.prefix === "" ? "(no prefix)" : c.prefix)))),
    h("p", { class: "cp-dim" }, "Only what the census knows. A router that no include could be matched to by name is not shown."));
}

function renderRoute(r, doc, opts, close) {
  const range = r.end && r.end > r.line ? `${r.line}-${r.end}` : String(r.line);
  const links = codeLinks({ path: r.file, start: r.line, end: r.end }, opts);
  links.explorer = P.explorerHref(r.file, { qual: r.handler, start: r.line, end: r.end });
  const facts = [["Handler", h("code", null, `${r.handler}()${r.async ? " (async)" : ""}`)], ["File", h("code", null, `${r.file}:${range}`)],
    ["Auth / deps", r.deps.length ? r.deps.map((d, i) => [i ? ", " : "", h("code", null, d)]) : "none declared"], ["Response model", r.response_model ? h("code", null, r.response_model) : "none declared"]];
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, h("span", { class: `cp-method cp-method--${r.method.toLowerCase()}` }, r.method), " ", h("code", null, r.path)),
      h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("dl", { class: "cp-facts" }, facts.map(([k, v]) => [h("dt", null, k), h("dd", null, v)])),
    linkRow(links), h("p", null, copyButton(`${r.method} ${r.path}`, "Copy route")),
    noteSection({ path: r.file, qual: r.handler }), callersSection(r, doc), chainSection(r), bookSection({ path: r.file, qual: r.handler }));
}

async function main() {
  const app = document.getElementById("cp-app");
  if (!app) return;
  let doc;
  try { doc = await getJSON("data/code/routes.json"); } catch (e) { app.replaceChildren(empty(`Could not load data/code/routes.json (${e.message}). Run python scripts/refresh_atlas.py.`)); return; }
  let opts = {};
  try { opts = await loadLinkOptions(); } catch { opts = {}; }
  const rows = P.routeRows(doc);
  const scan = P.scanInfo(doc);
  const detail = h("aside", { class: "cp-detail", "aria-label": "Route details", hidden: true });
  const table = makeTable({ cols: COLS, rows, key: (r) => r.key, filterText: rowText, placeholder: "Filter by method, path, handler, file, caller…", onPick: (r) => { location.hash = P.routeHash(r); } });
  const split = h("div", { class: "cp-split" }, detail, h("div", { class: "cp-main" }, h("h2", null, "All routes"), table.el));
  const close = () => { history.pushState(null, "", location.pathname + location.search); show(null); };
  function show(r) {
    split.classList.toggle("has-detail", !!r);
    detail.hidden = !r;
    table.select(r ? r.key : "");
    if (r) { detail.replaceChildren(renderRoute(r, doc, opts, close)); detail.scrollTop = 0; } else detail.replaceChildren();
  }
  window.addEventListener("hashchange", () => show(P.routeFromHash(rows, location.hash)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !detail.hidden && !/^(INPUT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName)) close(); });
  app.replaceChildren(
    freshLine([{ text: `Routes from MiniMe ${doc.commit} · ${doc.generated}` }, { text: scan.text, stale: scan.stale }]),
    kpiGrid(P.routeKpis(rows)),
    h("div", { class: "cp-two" }, barsCard("Routes per file", P.routesPerFile(rows), { href: (i) => P.explorerHref(i.title) }),
      barsCard("Frontend files that call the API most", P.callerFiles(rows), { href: (i) => P.explorerHref(i.title), note: "Counted per route a file calls. Inferred, see the caveat under any route's callers." })),
    split);
  show(P.routeFromHash(rows, location.hash));
}

main();
