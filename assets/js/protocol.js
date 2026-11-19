/* MiniMe Atlas 2 - the Protocol, M2C and Decision-records pages (P24). Loaded by protocol.html, m2c.html and adrs.html, which are shells:
   this module draws whichever one it finds (#pr-app, #m2c-app or #adr-app) from
     data/code/protocol.json   written by scripts/refresh_protocol.py from MiniMe's protocol/ folder, read from git at the census commit
     content/system/m2c.json   the few sentences a person wrote (what the M2C page is for, which chapters belong to it)
     data/index/notes.json, data/notes/<file>.json   AI notes, only where they exist; always labelled AI-written
     data/index/mentions.json   the chapter sections that name a file
   The pure logic is in protocolpages.js (Node tests it). All text goes in through h(), never as HTML. */
import { h } from "./explorer/dom.js";
import * as P from "./protocolpages.js";
import { getJSON, empty, badge, kpiGrid, freshLine, section, linkRow, copyButton, bookSection, makeTable } from "./codeui.js";
import { loadLinkOptions, codeLinks } from "./links.js";

const firstSentence = (s) => { const m = /^(.+?[.!?])(\s|$)/.exec(String(s || "")); return m ? m[1] : String(s || ""); };
const code = (t) => h("code", null, t);
const ghLinks = (path, opts) => { const l = codeLinks({ path }, opts); l.explorer = P.fileHref(path); return l; };

/* ------------------------------------------------------------------ shared pieces */
function riskBadge(r, doc) {
  const meaning = P.riskMap(doc)[String(r).slice(0, 2)] || "";
  return h("span", { class: `pr-risk pr-risk--${P.riskLevel(r)}`, title: meaning ? `${r}: ${meaning}` : String(r) },
    h("span", { class: "pr-risk__pips", "aria-hidden": "true" }, P.riskPips(r)), h("span", null, ` ${r}`));
}

/* A field table: name, type, required, details. Nested fields are indented. */
function fieldTable(fields, caption) {
  const rows = P.flattenFields(fields);
  if (!rows.length) return h("p", { class: "cp-dim" }, "No fields: the payload is an empty object.");
  const body = rows.map((f) => h("tr", null,
    h("td", { class: "pr-fname", style: `padding-left:calc(var(--space-3) + var(--space-4) * ${f.depth})` }, code(f.name),
      f.secret ? [" ", badge("stale", "secret", "Marked x-m2c-secret: never logged, and replaced in the example shown here.")] : null),
    h("td", null, code(f.type)),
    h("td", null, f.required ? "required" : h("span", { class: "cp-dim" }, "optional")),
    h("td", null, f.desc ? h("span", null, f.desc) : null, P.fieldFacts(f).map((x) => h("span", { class: "pr-fact" }, x)))));
  return h("div", { class: "mm-tablewrap pr-fields" }, h("table", { class: "mm-table is-compact" },
    caption ? h("caption", { class: "pr-sr" }, caption) : null,
    h("thead", null, h("tr", null, ["Field", "Type", "Rule", "Details"].map((c) => h("th", { scope: "col" }, c)))), h("tbody", null, body)));
}

function exampleBlock(ex) {
  if (!ex) return h("p", { class: "cp-dim" }, "No golden transcript contains this message yet, so there is no example.");
  const text = P.exampleText(ex);
  return h("div", null, h("pre", { class: "pr-code", tabindex: "0" }, h("code", null, text)),
    h("p", { class: "cp-dim cp-caveat" }, `From ${ex.fixture}, line ${ex.line}. Long values are cut, and a field the schema marks secret is replaced.`), h("p", null, copyButton(text, "Copy example")));
}

function whereUsed() {
  return section("Where it is used",
    h("ul", { class: "cp-list" },
      h("li", null, "Client (the device): ", h("a", { href: P.dirHref(P.LINKS.client) }, code(P.LINKS.client)), ", with the synced schemas in ", h("a", { href: P.dirHref(P.LINKS.clientCopy) }, code(P.LINKS.clientCopy))),
      h("li", null, "Server: ", h("a", { href: P.dirHref(P.LINKS.server) }, code(P.LINKS.server))),
      h("li", null, "Contract: ", h("a", { href: P.dirHref(P.LINKS.schemas) }, code(P.LINKS.schemas)), " and its ", h("a", { href: P.fileHref(P.LINKS.readme) }, code(P.LINKS.readme)))));
}

/* ------------------------------------------------------------------ the Protocol page */
function messageDetail(m, doc, opts, close, rowsByKey) {
  const facts = [["Direction", m.dirLabel], ["Data class", m.data_class || "not stated"], ["Routing", P.routingText(m)],
    ["Extra fields", m.closed ? "rejected (closed schema)" : "allowed"], ["Schema", code(m.file)]];
  const subs = m.type === "run_event" ? section(`Subtypes (${doc.run_events.length})`,
    h("p", { class: "cp-dim" }, "A run_event's payload.type picks one of these."),
    h("ul", { class: "cp-list" }, doc.run_events.map((e) => h("li", null, h("a", { href: P.rowHash(rowsByKey.get(`e:${e.type}`)) }, code(e.type)), " ", h("span", { class: "cp-dim" }, firstSentence(e.description)))))) : null;
  const fx = m.fixtures && m.fixtures.length
    ? h("ul", { class: "cp-list" }, m.fixtures.map((f) => h("li", null, code(f.name), ` \u00d7 ${f.count}`)))
    : h("p", { class: "cp-dim" }, "Not used in any golden transcript.");
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, code(m.type), " ", h("span", { class: "pr-dir" }, m.dirLabel)),
      h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", { class: "cp-lede" }, m.description || h("span", { class: "cp-dim" }, "The schema gives no description.")),
    h("dl", { class: "cp-facts" }, facts.map(([k, v]) => [h("dt", null, k), h("dd", null, v)])), linkRow(ghLinks(m.file, opts)),
    section(`Fields (${m.fields.length})`, fieldTable(m.fields, `Fields of ${m.type}`)), subs,
    m.type === "run_event" ? null : section("Example", exampleBlock(m.example)), section("Golden transcripts", fx), whereUsed(), bookSection({ path: m.file }));
}

function eventDetail(e, doc, opts, close) {
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, code("run_event"), " \u203a ", code(e.type)),
      h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", { class: "cp-lede" }, e.description || h("span", { class: "cp-dim" }, "The schema gives no description.")),
    h("dl", { class: "cp-facts" }, [["Data class", e.data_class || "not stated"], ["Schema", code("protocol/v1/run_event.json")]].map(([k, v]) => [h("dt", null, k), h("dd", null, v)])),
    linkRow(ghLinks("protocol/v1/run_event.json", opts)), section(`Fields (${e.fields.length})`, fieldTable(e.fields, `Fields of run_event ${e.type}`)),
    section("Example", exampleBlock(e.example)), whereUsed());
}

function toolDetail(t, doc, opts, close) {
  const map = P.riskMap(doc);
  const risks = [h("li", null, riskBadge(t.risk, doc), " ", map[t.risk] || "")];
  if (t.risk_max) risks.push(h("li", null, riskBadge(t.risk_max, doc), " ", `${map[t.risk_max] || ""}, for a call that goes beyond the usual level`));
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, code(t.name), " ", h("span", { class: "pr-dir" }, t.version)),
      h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", { class: "cp-lede" }, t.description), section("Risk", h("ul", { class: "cp-list pr-nobullet" }, risks),
      h("p", { class: "cp-dim cp-caveat" }, "The device's policy engine decides allow, ask or deny, and may raise a call's risk, never lower it.")),
    h("dl", { class: "cp-facts" }, [["Required inputs", t.required.length ? t.required.map((r, i) => [i ? ", " : "", code(r)]) : "none"], ["Schema", code(t.file)]].map(([k, v]) => [h("dt", null, k), h("dd", null, v)])),
    linkRow(ghLinks(t.file, opts)), section(`Inputs (${t.fields.length})`, fieldTable(t.fields, `Inputs of ${t.name}`)), whereUsed());
}

function enumsSection(doc) {
  const map = P.riskMap(doc);
  const risk = doc.enums && doc.enums.risk;
  const legend = risk ? h("section", { class: "mm-card" }, h("h3", { class: "mm-card__title" }, "Risk levels"),
    h("ul", { class: "pr-legend" }, risk.values.map((r) => h("li", null, riskBadge(r, doc), " ", map[r] || ""))),
    h("p", { class: "cp-dim cp-caveat" }, "Amber is the Atlas's gate colour: these are the levels that decide whether the device asks before it acts.")) : null;
  const others = Object.entries(doc.enums || {}).filter(([k]) => k !== "risk").sort((a, b) => (a[0] < b[0] ? -1 : 1))
    .map(([k, e]) => h("details", { class: "mm-card pr-enum" }, h("summary", null, code(k), " ", h("span", { class: "cp-dim" }, `${e.values.length} values`)),
      e.description ? h("p", { class: "cp-dim" }, e.description) : null, h("p", { class: "cp-pills" }, e.values.map((v) => h("span", { class: "cp-pill" }, String(v))))));
  return h("div", { class: "pr-enums" }, legend, others);
}

function fixturesSection(doc, opts) {
  const rows = doc.fixtures.map((f) => {
    const types = f.types ? Object.entries(f.types).map(([t, n]) => `${t}\u00d7${n}`).join(", ") : "cases that must all be rejected";
    return h("tr", null, h("td", null, code(f.name)), h("td", null, f.kind === "invalid" ? "invalid examples" : "golden transcript"), h("td", { class: "is-num" }, P.fmtN(f.messages)),
      h("td", { class: "pr-types" }, types), h("td", null, h("a", { href: codeLinks({ path: f.path }, opts).github, target: "_blank", rel: "noopener" }, "GitHub")));
  });
  return h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact" },
    h("thead", null, h("tr", null, ["File", "Kind", "Lines", "Messages in it", "Source"].map((c, i) => h("th", { scope: "col", class: i === 2 ? "is-num" : null }, c)))), h("tbody", null, rows)));
}

async function protocolPage(app, doc, opts) {
  const msgs = P.messageRows(doc), evs = P.eventRows(doc), tools = P.toolRows(doc);
  const all = [...msgs, ...evs, ...tools];
  const byKey = new Map(all.map((r) => [r.key, r]));
  const copy = P.clientCopyInfo(doc);
  const detail = h("aside", { class: "cp-detail", "aria-label": "Details", hidden: true });
  const tables = [];
  const mk = (cols, rows, ph, text) => { const t = makeTable({ cols, rows, key: (r) => r.key, filterText: text, placeholder: ph, onPick: (r) => { location.hash = P.rowHash(r); } }); tables.push(t); return t; };
  const mt = mk([
    { id: "type", label: "Type", get: (r) => r.type, mono: true }, { id: "dir", label: "Direction", get: (r) => r.dirLabel },
    { id: "class", label: "Data class", get: (r) => r.data_class }, { id: "fields", label: "Fields", get: (r) => r.nfields, num: true },
    { id: "route", label: "Routing", get: (r) => P.routingText(r) }, { id: "fx", label: "In transcripts", get: (r) => r.nfixtures, num: true },
    { id: "what", label: "What it is", get: (r) => firstSentence(r.description) }], msgs, "Filter message types…", (r) => [r.type, r.dirLabel, r.data_class, r.description, r.fields.map((f) => f.name).join(" ")].join(" "));
  const et = mk([
    { id: "type", label: "payload.type", get: (r) => r.type, mono: true }, { id: "class", label: "Data class", get: (r) => r.data_class },
    { id: "fields", label: "Fields", get: (r) => r.nfields, num: true }, { id: "what", label: "What it is", get: (r) => firstSentence(r.description) }],
    evs, "Filter run_event subtypes…", (r) => [r.type, r.description, r.fields.map((f) => f.name).join(" ")].join(" "));
  const tt = mk([
    { id: "name", label: "Tool", get: (r) => r.name, mono: true },
    { id: "risk", label: "Risk", get: (r) => r.level, num: true, render: (r) => h("span", null, riskBadge(r.risk, doc), r.risk_max ? [" \u2192 ", riskBadge(r.risk_max, doc)] : null) },
    { id: "inputs", label: "Inputs", get: (r) => r.nfields, num: true }, { id: "what", label: "What it does", get: (r) => firstSentence(r.description) }],
    tools, "Filter tools by name, risk, description…", (r) => [r.name, r.risk, r.risk_max || "", r.description, r.fields.map((f) => f.name).join(" ")].join(" "));

  const close = () => { history.pushState(null, "", location.pathname + location.search); show(null); };
  function show(row) {
    split.classList.toggle("has-detail", !!row);
    detail.hidden = !row;
    for (const t of tables) t.select(row ? row.key : "");
    if (!row) { detail.replaceChildren(); return; }
    const body = row.kind === "message" ? messageDetail(row, doc, opts, close, byKey) : row.kind === "event" ? eventDetail(row, doc, opts, close) : toolDetail(row, doc, opts, close);
    detail.replaceChildren(body); detail.scrollTop = 0;
  }
  const rule = doc.envelope.description || "";
  const split = h("div", { class: "cp-split" }, detail, h("div", { class: "cp-main" },
    h("h2", { id: "messages" }, `Message types (${msgs.length})`), mt.el,
    h("h2", { id: "run-events" }, `run_event subtypes (${evs.length})`), h("p", { class: "cp-dim" }, "One message type, seven kinds of event. The payload's type field picks the shape."), et.el,
    h("h2", { id: "tools" }, `Tools (${tools.length})`), h("p", { class: "cp-dim" }, "What the model may ask the device to run. Risk is shown in the gate colour: the more filled the dots, the more the device should ask first."), tt.el));

  window.addEventListener("hashchange", () => show(P.rowFromHash(all, location.hash)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !detail.hidden && !/^(INPUT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName)) close(); });
  app.replaceChildren(
    freshLine([{ text: `Protocol v${doc.versions.join(", v")} from MiniMe ${doc.short} \u00b7 ${doc.generated}` }]),
    h("p", { class: "cp-badges" }, badge(copy.kind, copy.text, copy.title),
      h("span", { class: "cp-dim" }, " Schemas and fixtures are read from git at that commit; nothing on this page is typed by hand.")),
    kpiGrid(P.protocolKpis(doc)),
    h("section", { class: "mm-card pr-env" }, h("h2", { id: "envelope" }, "The envelope"), h("p", { class: "cp-lede" }, rule),
      fieldTable(doc.envelope.fields, "Fields of the envelope"), linkRow(ghLinks(doc.envelope.file, opts))),
    split, h("h2", { id: "enums" }, "Shared values"), enumsSection(doc),
    h("h2", { id: "fixtures" }, "Golden transcripts"), h("p", { class: "cp-dim" }, "Real message sequences the client and the server must both accept. The credential-shaped strings in them are placeholders, and are never shown here."), fixturesSection(doc, opts));
  show(P.rowFromHash(all, location.hash));
}

/* ------------------------------------------------------------------ the M2C page */
async function m2cPage(app, doc, opts) {
  let text = {}, index = null;
  try { text = await getJSON("content/system/m2c.json"); } catch { text = {}; }
  try { index = await getJSON("data/index/notes.json"); } catch { index = null; }
  const m = doc.m2c, rows = P.packageRows(doc, index);
  const cmdRows = m.commands.map((c) => h("tr", null, h("td", null, code(c.command)), h("td", null, c.what)));
  const cols = [
    { id: "name", label: "Package or module", get: (r) => r.name, mono: true, render: (r) => h("a", { href: r.href }, r.name) },
    { id: "kind", label: "Kind", get: (r) => r.kindLabel }, { id: "files", label: "Files", get: (r) => r.files, num: true },
    { id: "doc", label: "What it is (from its docstring)", get: (r) => r.doc },
    { id: "note", label: "AI note", get: (r) => (r.note ? r.note.summary : ""),
      render: (r) => (r.note ? h("span", null, r.note.summary, " ", badge("ai", "AI-written"), r.note.state === "stale" ? [" ", badge("stale", "code changed")] : null) : h("span", { class: "cp-dim" }, "none yet")) }];
  const table = makeTable({ cols, rows, key: (r) => r.key, filterText: (r) => [r.name, r.doc, r.note ? r.note.summary : "", r.path].join(" "), placeholder: "Filter packages…", onPick: (r) => { location.href = r.href; } });
  const book = (text.book || []).map((b) => h("li", null, h("a", { href: b.url }, b.label), b.note ? h("span", { class: "cp-dim" }, ` \u2013 ${b.note}`) : null));
  app.replaceChildren(
    freshLine([{ text: `M2C client from MiniMe ${doc.short} \u00b7 ${doc.generated}` }]),
    h("p", { class: "cp-badges" }, badge(m.status === "early" ? "stale" : "ok", m.status ? `status: ${m.status}` : "status not stated", "Read from m2c/README.md."),
      h("span", { class: "cp-dim" }, " Status comes from the client's own README.")),
    text.intro ? h("p", { class: "cp-lede" }, text.intro) : null, m.doc ? h("p", { class: "cp-dim" }, `The package says: ${m.doc}`) : null,
    kpiGrid(P.m2cKpis(doc)),
    h("h2", { id: "map" }, "Package map"), table.el,
    h("h2", { id: "commands" }, `Commands (${m.commands.length})`), h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact" },
      h("thead", null, h("tr", null, h("th", { scope: "col" }, "Command"), h("th", { scope: "col" }, "What it does"))), h("tbody", null, cmdRows))),
    h("p", null, h("a", { class: "mm-btn", href: P.fileHref(m.readme) }, "Read the client's README")),
    h("h2", { id: "connects" }, "Where it connects"),
    h("ul", { class: "cp-list" },
      h("li", null, "The wire format shared with the server: ", h("a", { href: "protocol.html" }, "Protocol"), " \u2013 ", String(doc.totals.messages), " message types, ", String(doc.totals.tools), " tools."),
      h("li", null, "The server side, ", h("a", { href: P.dirHref(P.LINKS.server) }, code(P.LINKS.server)), "."),
      h("li", null, "The device client in the Explorer: ", h("a", { href: P.dirHref(P.LINKS.client) }, code(P.LINKS.client)), ".")),
    book.length ? h("h2", { id: "book" }, "In the book") : null, book.length ? h("ul", { class: "cp-list" }, book) : null);
}

/* ------------------------------------------------------------------ the Decision-records page */
async function adrPage(app, doc, opts) {
  const rows = P.adrRows(doc);
  const cards = rows.map((a) => {
    const [kind, label] = P.adrBadge(a);
    return h("article", { class: "mm-card pr-adr", id: `adr-${a.number}` },
      h("h3", { class: "mm-card__title" }, h("span", { class: "pr-adr__n" }, a.number), " ", a.title), h("p", { class: "cp-badges" }, badge(kind, label)),
      a.status_text && a.status_text.toLowerCase() !== a.status ? h("p", { class: "cp-dim" }, a.status_text) : null,
      h("div", { class: "cp-links" }, h("a", { class: "mm-btn", href: a.href }, "Read the record"), h("a", { class: "mm-btn", href: codeLinks({ path: a.path }, opts).github, target: "_blank", rel: "noopener" }, "GitHub")),
      bookSection({ path: a.path }));
  });
  app.replaceChildren(
    freshLine([{ text: `${rows.length} decision records in MiniMe ${doc.short} \u00b7 ${doc.generated}` }]),
    h("p", { class: "cp-dim" }, "These are MiniMe's own architecture decision records (docs/decisions). The book's Golden Rules and locks are on ", h("a", { href: "decisions.html" }, "Decisions"), "; a record is linked to a rule only where a person has said so."),
    h("div", { class: "pr-adrs" }, cards.length ? cards : empty("MiniMe has no decision records at this commit.")));
}

async function main() {
  const app = document.getElementById("pr-app") || document.getElementById("m2c-app") || document.getElementById("adr-app");
  if (!app) return;
  let doc;
  try { doc = await getJSON("data/code/protocol.json"); } catch (e) { app.replaceChildren(empty(`Could not load data/code/protocol.json (${e.message}). Run python scripts/refresh_protocol.py --minime ../MiniMe.`)); return; }
  let opts = {};
  try { opts = await loadLinkOptions(); } catch { opts = {}; }
  if (app.id === "pr-app") await protocolPage(app, doc, opts);
  else if (app.id === "m2c-app") await m2cPage(app, doc, opts);
  else await adrPage(app, doc, opts);
}

main();
