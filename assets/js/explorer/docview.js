/* MiniMe Atlas 2 - Explorer view tab for files that are not code (P14e).

   A Markdown file is a document, a JSON file is data, a SQL file is a list of things done to a database. For those three the file page
   gets one more tab, first in the row and open by default, whose name says what it is:

     .md / .markdown   Document    markdown.js   headings, lists, tables, code, links that open the repository's own files
     .json / .jsonc    Structure   jsonview.js   a folding tree, plus a property table when the file is a JSON Schema
     .sql              Outline     sql.js        statements in file order: kind, object, detail, lines, the comment above

   The tab works from the embedded copy of the file (data/src/<path>.txt, P12), the same text the Source tab shows, so a link from
   here to "line 40" and the Source tab's line 40 are the same line. Without an embedded copy there is no tab and the page is exactly
   what P13 made. The Source tab stays the way to read the exact text, and every view here links to it. */
import { h } from "./dom.js";
import { buildRoute } from "./router.js";
import { getText } from "./model.js";
import { codeLinks } from "../links.js";
import { renderMarkdown, MAX_CHARS as MD_MAX } from "./markdown.js";
import { renderJson } from "./jsonview.js";
import { renderSql } from "./sql.js";

export const DOC_LABEL = { markdown: "Document", json: "Structure", sql: "Outline" };
const BY_EXT = { md: "markdown", markdown: "markdown", json: "json", jsonc: "json", sql: "sql" };

/* "docs/a.MD" -> "markdown"; "x.py" -> null. Pure. */
export function docKind(path) {
  const name = String(path || "").split("/").pop().toLowerCase();
  const dot = name.lastIndexOf(".");
  return dot > 0 ? BY_EXT[name.slice(dot + 1)] || null : null;
}

/* Does this file get the tab? It needs a kind and an embedded copy to read. */
export function docViewFor(file, linkOpts) {
  if (!file || file.binary) return null;
  const kind = docKind(file.path);
  return kind && codeLinks({ path: file.path }, linkOpts || {}).src ? kind : null;
}

/* ctx: { core, file, kind, linkOpts } */
export function renderDocView(panel, { core, file, kind, linkOpts = {} }) {
  const src = codeLinks({ path: file.path }, linkOpts).src;
  const toSource = buildRoute({ view: "file", path: file.path, tab: "source" });
  panel.replaceChildren(h("p", { class: "ex-dim" }, `Loading ${file.name}…`));
  getText(src).then((text) => {
    const head = h("p", { class: "ex-dim ex-doc__from" }, `Read from the embedded copy${linkOpts.commit ? ` at commit ${String(linkOpts.commit).slice(0, 7)}` : ""}. `, h("a", { href: toSource }, "Show the exact text in the Source tab"), ".");
    let body;
    if (kind === "markdown") {
      if (text.length > MD_MAX) { panel.replaceChildren(h("p", { class: "ex-callout ex-callout--warn" }, "This document is too big to render here. ", h("a", { href: toSource }, "Read it in the Source tab"), ".")); return; }
      const tree = core && core.tree;
      body = renderMarkdown(text, { path: file.path, hasFile: (p) => !!tree && tree.files.has(p), hasDir: (p) => !!tree && tree.dirs.has(p), self: buildRoute({ view: "file", path: file.path, tab: "view" }) }).el;
    } else if (kind === "json") body = renderJson(text, { path: file.path }).el;
    else body = renderSql(text, { path: file.path }).el;
    panel.replaceChildren(head, body);
  }).catch((e) => {
    panel.replaceChildren(h("p", { class: "ex-callout ex-callout--warn" }, `The embedded copy could not be loaded (${e.message}). `, h("a", { href: toSource }, "Try the Source tab"), "."));
  });
}
