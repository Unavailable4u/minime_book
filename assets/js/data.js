/* MiniMe Atlas 2 - the Data model page (P18). Loaded by data.html, which is a shell: this module draws everything from
     data/code/schema.json   tables, columns, foreign keys, policies, migrations, who mentions a table (scripts/refresh_schema.py reads the SQL)
   The pure logic (KPIs, the ER layout, hashes, drift sentences) is in dataviews.js, which Node tests. A relationship is drawn only
   when the SQL declares a foreign key; "who touches this table" is a text match from the census and the page says so. Every piece
   of text goes in through h() or createTextNode, never as HTML. */
import { h } from "./explorer/dom.js";
import * as D from "./dataviews.js";
import { getJSON, empty, badge, kpiGrid, freshLine, section, copyButton, makeTable } from "./codeui.js";

const SVG = "http://www.w3.org/2000/svg";
const s = (tag, attrs, ...kids) => {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null && v !== false) el.setAttribute(k, String(v));
  for (const k of kids) if (k != null) el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return el;
};
const fileLink = (p, opts) => h("a", { href: D.explorerHref(p, opts || {}) }, h("code", null, p));
const tableLink = (key, text) => h("a", { href: `#${encodeURIComponent(key)}` }, h("code", null, text || key));
const trunc = (t, n) => (t.length > n ? `${t.slice(0, n - 1)}\u2026` : t);

/* ------------------------------------------------------------------ ER diagram */
function drawER(doc, pick) {
  const L = D.erLayout(doc);
  const E = D.ER;
  const svg = s("svg", { viewBox: `0 0 ${L.width} ${L.height}`, width: L.width, height: L.height, role: "img", "aria-label": "Foreign keys between the tables of the public schema", class: "cp-er__svg" });
  svg.append(s("defs", null, s("marker", { id: "er-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto" }, s("path", { d: "M0,0 L8,4 L0,8z", class: "cp-er__arrow" }))));
  const edgeEls = L.edges.map((e) => {
    const p = s("path", { d: e.d, class: "cp-er__edge", "marker-end": "url(#er-arrow)" }, s("title", null, `${D.bare(e.from)}(${e.cols.join(", ")}) \u2192 ${e.to}${e.toCols.length ? `(${e.toCols.join(", ")})` : ""}${e.onDelete ? ` on delete ${e.onDelete}` : ""}`));
    svg.append(p);
    return [e, p];
  });
  const boxEls = new Map();
  if (L.ghost) {
    const g = L.ghost;
    const grp = s("g", { class: "cp-er__ghost" }, s("rect", { x: g.x, y: g.y, width: g.w, height: g.h, rx: 6 }), s("text", { x: g.x + 10, y: g.y + 17, class: "cp-er__name" }, g.label));
    g.rows.forEach((k, i) => {
      const t = s("text", { x: g.x + 10, y: g.y + E.head + E.pad + E.row * (i + 0.75), class: "cp-er__col cp-er__link", tabindex: 0, role: "link" }, k);
      t.addEventListener("click", () => pick(k));
      t.addEventListener("keydown", (ev) => { if (ev.key === "Enter") pick(k); });
      grp.append(t);
    });
    svg.append(grp);
  }
  if (L.bandLabelY != null) svg.append(s("text", { x: E.margin, y: L.bandLabelY, class: "cp-er__band" }, "No foreign key to or from these tables"));
  for (const n of L.nodes) {
    const g = s("g", { class: "cp-er__box", tabindex: 0, role: "button", "data-key": n.key, "aria-label": `Table ${n.name}` },
      s("rect", { x: n.x, y: n.y, width: n.w, height: n.h, rx: 6 }),
      s("rect", { x: n.x, y: n.y, width: n.w, height: E.head, rx: 6, class: "cp-er__head" }),
      s("text", { x: n.x + 10, y: n.y + 17, class: "cp-er__name" }, trunc(n.name, 27)));
    n.shown.forEach((c, i) => {
      const y = n.y + E.head + E.pad + E.row * (i + 0.75);
      g.append(s("text", { x: n.x + 10, y, class: "cp-er__col" }, `${c.pk ? "PK " : c.fk ? "FK " : ""}${trunc(c.name, 20)}`), s("text", { x: n.x + n.w - 10, y, class: "cp-er__type", "text-anchor": "end" }, trunc(c.type, 14)));
    });
    if (n.more) g.append(s("text", { x: n.x + 10, y: n.y + E.head + E.pad + E.row * (n.shown.length + 0.75), class: "cp-er__more" }, `+${n.more} more`));
    g.addEventListener("click", () => pick(n.key));
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(n.key); } });
    svg.append(g);
    boxEls.set(n.key, g);
  }
  const mark = (key) => {
    const near = key ? D.neighbours(L.edges, key) : null;
    boxEls.forEach((g, k) => { g.classList.toggle("is-on", k === key); g.classList.toggle("is-dim", !!near && !near.has(k)); });
    edgeEls.forEach(([e, p]) => { p.classList.toggle("is-on", !!key && (e.from === key || e.to === key)); p.classList.toggle("is-dim", !!key && e.from !== key && e.to !== key); });
  };
  return { el: h("div", { class: "cp-er" }, svg), mark, layout: L };
}

/* ------------------------------------------------------------------ the table list */
const COLS = [
  { id: "name", label: "Table", get: (r) => r.name, mono: true },
  { id: "cols", label: "Columns", get: (r) => r.columnCount, num: true },
  { id: "fks", label: "Foreign keys", get: (r) => r.fkCount, num: true },
  { id: "rls", label: "Row-level security", get: (r) => r.rlsText, render: (r) => (r.rls === "forced" ? badge("ok", "forced") : r.rls ? badge("here", r.rls) : badge("stale", "none")) },
  { id: "pol", label: "Policies", get: (r) => r.policyCount, num: true },
  { id: "from", label: "Built by", get: (r) => r.createdText },
  { id: "code", label: "Code files", get: (r) => r.codeRefs, num: true },
  { id: "tests", label: "Test files", get: (r) => r.testRefs, num: true },
  { id: "src", label: "In", get: (r) => r.origin, render: (r) => badge(r.origin === "both" ? "ok" : "here", r.origin === "both" ? "migrations + dump" : r.origin, r.drifted ? D.driftText(r) : null) },
];
const rowText = (r) => [r.key, r.createdText, r.origin, r.comment || "", ...r.columns.map((c) => c.name), ...(r.policies || []).map((p) => p.name), ...(r.refs ? r.refs.code : [])].join(" ");

/* ------------------------------------------------------------------ one table */
function columnsTable(t, doc) {
  const rel = D.relationsOf(doc, t.key);
  const fkOf = (c) => (c.fk ? rel.references.find((r) => r.cols.includes(c.name)) : null);
  return h("div", { class: "mm-tablewrap cp-tablewrap" }, h("table", { class: "mm-table is-compact" },
    h("thead", null, h("tr", null, ["Column", "Type", "Flags", "Default", "References"].map((x) => h("th", { scope: "col" }, x)))),
    h("tbody", null, t.columns.map((c) => {
      const fk = fkOf(c) || (c.fk ? { table: c.fk.to, tableCols: c.fk.col ? [c.fk.col] : [], onDelete: c.fk.on_delete || "" } : null);
      return h("tr", null,
        h("td", { class: "is-mono" }, c.name, c.added_in ? [" ", badge("here", `added in ${D.migNumber(c.added_in) || "a later file"}`, c.added_in)] : null),
        h("td", { class: "is-mono" }, c.type),
        h("td", null, D.columnFlags(c).join(" · ")),
        h("td", { class: "is-mono" }, c.default || ""),
        h("td", null, fk ? [tableLink(fk.table), fk.tableCols && fk.tableCols.length ? ` (${fk.tableCols.join(", ")})` : "", fk.onDelete ? ` on delete ${fk.onDelete}` : ""] : ""));
    }))));
}

function relationsBlock(t, doc) {
  const rel = D.relationsOf(doc, t.key);
  const line = (x, dir) => h("li", null, dir === "out" ? [h("code", null, x.cols.join(", ")), " \u2192 ", tableLink(x.table), x.tableCols.length ? ` (${x.tableCols.join(", ")})` : ""] : [tableLink(x.table), " (", x.cols.join(", "), ") \u2192 here"],
    x.onDelete ? ` on delete ${x.onDelete}` : "", x.origin !== "both" ? [" ", badge("here", `only in ${x.origin}`, "Only one of the two kinds of SQL declares this key.")] : null);
  return section("Relationships",
    rel.references.length ? [h("p", { class: "cp-label" }, "References"), h("ul", { class: "cp-list" }, rel.references.map((x) => line(x, "out")))] : h("p", { class: "cp-dim" }, "Declares no foreign key."),
    rel.referencedBy.length ? [h("p", { class: "cp-label" }, "Referenced by"), h("ul", { class: "cp-list" }, rel.referencedBy.map((x) => line(x, "in")))] : h("p", { class: "cp-dim" }, "No table declares a foreign key to it."));
}

function securityBlock(t) {
  const pol = t.policies || [];
  if (t.schema !== D.PUBLIC && !t.rls && !pol.length) return null;
  return section("Who can see it",
    h("p", null, "Row-level security: ", t.rls ? badge(t.rls === "forced" ? "ok" : "here", t.rls) : badge("stale", "none recorded")),
    pol.length ? h("ul", { class: "cp-list" }, pol.map((p) => h("li", null, h("code", null, p.name), ` \u2014 ${p.cmd}${p.roles && p.roles.length ? ` to ${p.roles.join(", ")}` : ""} `, h("span", { class: "cp-dim" }, "(", D.migNumber(p.file) ? `migration ${D.migNumber(p.file)}` : p.file, ")"))))
      : h("p", { class: "cp-dim" }, "No policy in the migrations."));
}

function refsBlock(t) {
  const groups = D.refGroups(t);
  if (!groups) return section("Who touches this table", h("p", { class: "cp-dim" }, "Only tables of the public schema are matched to files: the name of a table in another schema is not unique."));
  const total = groups.reduce((n, g) => n + g.files.length, 0);
  return section(`Who touches this table (${total})`,
    total ? groups.filter((g) => g.files.length).map((g) => [h("p", { class: "cp-label" }, `${g.label} (${g.files.length})`), h("ul", { class: "cp-list" }, g.files.map((f) => h("li", null, fileLink(f))))])
      : h("p", { class: "cp-dim" }, "No file the census scanned names this table."),
    h("p", { class: "cp-dim cp-caveat" }, D.REFS_CAVEAT));
}

function renderTable(t, doc, close) {
  const facts = [["Schema", t.schema], ["Primary key", t.pk.length ? t.pk.join(", ") : "none declared"],
    ["First created", t.created_in ? h("span", null, fileLink(t.created_in, t.created_line ? { start: t.created_line } : {})) : "?"],
    ["Seen in", t.origin === "both" ? "the migrations and the Supabase dump" : t.origin === "migrations" ? "the migrations only" : "the Supabase dump only"]];
  const drift = D.driftText(t);
  const touched = (t.touched || []).filter((x) => D.migNumber(x.file));
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, h("code", null, t.key)), h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", null, copyButton(t.key, "Copy name")),
    t.comment ? h("p", { class: "cp-lede" }, t.comment, " ", h("span", { class: "cp-dim" }, "(COMMENT ON TABLE)")) : null,
    h("dl", { class: "cp-facts" }, facts.map(([k, v]) => [h("dt", null, k), h("dd", null, v)])),
    drift ? h("p", { class: "cp-caveat" }, badge("stale", "drift"), " ", drift, ". The dump says it may be behind the migrations.") : null,
    section(`Columns (${t.columns.length})`, columnsTable(t, doc)),
    relationsBlock(t, doc), securityBlock(t),
    (t.unique || []).length || (t.checks || []).length || (t.indexes || []).length || (t.triggers || []).length ? section("Constraints, indexes, triggers",
      (t.unique || []).length ? h("p", null, "Unique: ", t.unique.map((u, i) => [i ? "; " : "", h("code", null, u.join(", "))])) : null,
      (t.checks || []).length ? [h("p", { class: "cp-label" }, "Checks"), h("ul", { class: "cp-list" }, t.checks.map((c) => h("li", null, h("code", null, c))))] : null,
      (t.indexes || []).length ? [h("p", { class: "cp-label" }, "Indexes"), h("ul", { class: "cp-list" }, t.indexes.map((i) => h("li", null, h("code", null, i.name), i.unique ? " (unique)" : "", " on ", h("code", null, i.on))))] : null,
      (t.triggers || []).length ? [h("p", { class: "cp-label" }, "Triggers"), h("ul", { class: "cp-list" }, t.triggers.map((g) => h("li", null, h("code", null, g.name), ` \u2014 ${g.when}`)))] : null) : null,
    touched.length ? section("Migrations that changed it", h("ul", { class: "cp-list" }, touched.map((x) => h("li", null, fileLink(x.file), " ", h("span", { class: "cp-dim" }, x.op))))) : null,
    refsBlock(t));
}

/* ------------------------------------------------------------------ security overview and migrations */
function securityList(doc) {
  const rows = [];
  for (const t of D.tableRows(doc).filter((x) => x.schema === D.PUBLIC)) {
    if (!t.policies || !t.policies.length) rows.push({ key: `${t.key}|`, table: t.name, tk: t.key, rls: t.rlsText, policy: "(none)", cmd: "", roles: "", file: "" });
    for (const p of t.policies || []) rows.push({ key: `${t.key}|${p.name}`, table: t.name, tk: t.key, rls: t.rlsText, policy: p.name, cmd: p.cmd, roles: (p.roles || []).join(", "), file: p.file });
  }
  const cols = [
    { id: "table", label: "Table", get: (r) => r.table, mono: true }, { id: "rls", label: "RLS", get: (r) => r.rls },
    { id: "policy", label: "Policy", get: (r) => r.policy, mono: true }, { id: "cmd", label: "Applies to", get: (r) => r.cmd },
    { id: "roles", label: "Roles", get: (r) => r.roles }, { id: "mig", label: "Migration", get: (r) => D.migNumber(r.file), render: (r) => (r.file ? h("a", { href: D.explorerHref(r.file) }, D.migNumber(r.file)) : "") },
  ];
  return makeTable({ cols, rows, key: (r) => r.key, filterText: (r) => Object.values(r).join(" "), placeholder: "Filter by table, policy, role…", onPick: (r) => { location.hash = `#${encodeURIComponent(r.tk)}`; } });
}

function migrationsBlock(doc) {
  const rows = D.migrationRows(doc);
  return section(`Migrations (${rows.length})`, h("p", { class: "cp-dim" }, "Applied in file order. What each file creates and changes is read from its SQL, so it can not drift from it."),
    h("ol", { class: "cp-timeline" }, rows.map((m) => h("li", { id: `m${m.key}` },
      h("div", { class: "cp-timeline__head" }, h("b", null, m.id || ""), " ", fileLink(m.file, {}), " ", h("span", { class: "cp-dim" }, m.title)),
      m.summary ? h("p", { class: "cp-dim" }, m.summary) : null,
      h("div", { class: "cp-pills" },
        m.creates.map((k) => h("a", { class: "cp-pill", href: `#${encodeURIComponent(k)}`, title: "creates this table" }, `+ ${D.bare(k)}`)),
        m.addedColumns.map((c) => h("span", { class: "cp-pill", title: "adds this column" }, `+ ${c}`)),
        m.touches.map((k) => h("a", { class: "cp-pill", href: `#${encodeURIComponent(k)}`, title: "changes this table" }, D.bare(k))),
        m.policies ? h("span", { class: "cp-pill" }, `${m.policies} ${m.policies === 1 ? "policy" : "policies"}`) : null,
        m.indexes ? h("span", { class: "cp-pill" }, `${m.indexes} ${m.indexes === 1 ? "index" : "indexes"}`) : null,
        m.triggers ? h("span", { class: "cp-pill" }, `${m.triggers} ${m.triggers === 1 ? "trigger" : "triggers"}`) : null,
        m.functions.map((f) => h("span", { class: "cp-pill", title: "function" }, `${f}()`)))))));
}

/* ------------------------------------------------------------------ the page */
async function main() {
  const app = document.getElementById("cp-app");
  if (!app) return;
  let doc;
  try { doc = await getJSON("data/code/schema.json"); } catch (e) { app.replaceChildren(empty(`Could not load data/code/schema.json (${e.message}). Run python scripts/refresh_schema.py.`)); return; }
  const rows = D.tableRows(doc);
  const pub = rows.filter((r) => r.schema === D.PUBLIC);
  const other = rows.filter((r) => r.schema !== D.PUBLIC);
  const er = drawER(doc, (k) => { location.hash = `#${encodeURIComponent(k)}`; });
  const detail = h("aside", { class: "cp-detail", "aria-label": "Table details", hidden: true });
  const pubTable = makeTable({ cols: COLS, rows: pub, key: (r) => r.key, filterText: rowText, placeholder: "Filter by table, column, policy, file…", onPick: (r) => { location.hash = D.tableHash(r); } });
  const otherCols = [{ id: "key", label: "Table", get: (r) => r.key, mono: true }, { id: "cols", label: "Columns", get: (r) => r.columnCount, num: true }, { id: "fks", label: "Foreign keys", get: (r) => r.fkCount, num: true }, { id: "rls", label: "Row-level security", get: (r) => r.rlsText }];
  const otherTable = makeTable({ cols: otherCols, rows: other, key: (r) => r.key, filterText: (r) => `${r.key} ${r.columns.map((c) => c.name).join(" ")}`, placeholder: "Filter other schemas…", onPick: (r) => { location.hash = D.tableHash(r); } });
  const split = h("div", { class: "cp-split" }, detail, h("div", { class: "cp-main" }, h("h2", null, `Tables in public (${pub.length})`), pubTable.el,
    h("details", { class: "mm-card cp-deps" }, h("summary", null, h("b", null, `Other schemas (${other.length} tables)`), " ", h("span", { class: "cp-dim" }, "from the Supabase dump; most belong to Supabase itself")), otherTable.el)));
  const close = () => { history.pushState(null, "", location.pathname + location.search); show(null); };
  function show(t) {
    split.classList.toggle("has-detail", !!t);
    detail.hidden = !t;
    pubTable.select(t ? t.key : "");
    otherTable.select(t ? t.key : "");
    er.mark(t ? t.key : "");
    if (t) { detail.replaceChildren(renderTable(t, doc, close)); detail.scrollTop = 0; } else detail.replaceChildren();
  }
  window.addEventListener("hashchange", () => show(D.tableFromHash(rows, location.hash)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !detail.hidden && !/^(INPUT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName)) close(); });

  const drift = doc.drift || {};
  const missing = drift.in_migrations_not_in_dump || [];
  const extra = drift.in_dump_not_in_migrations || [];
  const drifted = pub.filter((r) => r.drifted);
  const srcNote = doc.source === "src" ? "Read from the SQL embedded at that commit." : "The SQL is not embedded for this commit, so this is the census's shorter view: no foreign keys, policies or migrations detail.";
  const driftBlock = missing.length || extra.length || drifted.length ? h("section", { class: "mm-card cp-sec" }, h("h3", { class: "mm-card__title" }, "Migrations and the Supabase dump do not agree"),
    h("p", { class: "cp-dim" }, "scripts/*.sql is a context-only dump of the live database and says it may be behind. A difference is shown, not resolved."),
    missing.length ? h("p", null, `Built by the migrations, missing from the dump (${missing.length}): `, missing.map((k, i) => [i ? ", " : "", tableLink(k, D.bare(k))])) : null,
    extra.length ? h("p", null, `In the dump, built by no migration (${extra.length}): `, extra.map((k, i) => [i ? ", " : "", tableLink(k, D.bare(k))])) : null,
    drifted.length ? h("p", null, `Columns differ in ${drifted.length} ${drifted.length === 1 ? "table" : "tables"}: `, drifted.map((t, i) => [i ? ", " : "", tableLink(t.key, t.name)])) : null) : null;

  app.replaceChildren(
    freshLine([{ text: `Data model from MiniMe ${doc.commit} · ${doc.generated}` }, { text: srcNote }]),
    kpiGrid(D.schemaKpis(doc)),
    h("div", { class: "cp-pills" }, D.schemaCounts(doc).map((x) => h("span", { class: "cp-pill" }, `${x.name}: ${x.tables} ${x.tables === 1 ? "table" : "tables"}`))),
    driftBlock,
    h("section", { class: "mm-card cp-sec" }, h("h3", { class: "mm-card__title" }, "Table relationships"),
      h("p", { class: "cp-dim" }, "Each arrow is a foreign key the SQL declares, drawn from the table that holds it to the table it points at. Select a table to dim the rest. Tables with no foreign key sit below."), er.el),
    split,
    section("Who can see which table", h("p", { class: "cp-dim" }, "Row-level security and the policies that apply, from the migrations."), securityList(doc).el),
    migrationsBlock(doc));
  show(D.tableFromHash(rows, location.hash));
}

main();
