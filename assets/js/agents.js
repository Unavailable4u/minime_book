/* MiniMe Atlas 2 - the Agents page (P17). Loaded by agents.html, which is a shell: this module draws everything from
     data/code/agents.json   agent modules, roles and provider key slots (refresh_atlas.py, from the census registry; key names only, no secrets)
     data/index/notes.json, data/notes/<file>.json   the AI note of the module on screen
     data/index/mentions.json   the chapter sections that name the module's file
   A role is tied to a module only when a module has the same name; nothing else links them. The pure logic is in codepages.js. */
import { h } from "./explorer/dom.js";
import * as P from "./codepages.js";
import { getJSON, empty, badge, kpiGrid, barsCard, freshLine, section, linkRow, copyButton, noteSection, bookSection, makeTable } from "./codeui.js";
import { loadLinkOptions, codeLinks } from "./links.js";

const COLS = [
  { id: "name", label: "Agent", get: (m) => m.name, mono: true },
  { id: "doc", label: "What it does", get: (m) => m.doc },
  { id: "role", label: "Role", get: (m) => (m.role ? m.role.key : ""), mono: true },
  { id: "code", label: "Code lines", get: (m) => m.code, num: true },
  { id: "functions", label: "Functions", get: (m) => m.functions, num: true },
  { id: "tests", label: "Test files", get: (m) => m.testCount, num: true },
  { id: "commits", label: "Commits", get: (m) => m.commits, num: true },
  { id: "last", label: "Last change", get: (m) => m.last },
];
const rowText = (m) => [m.name, m.doc, m.role ? m.role.key : "", m.file].join(" ");
const hashOf = (kind, id) => `#${kind}:${encodeURIComponent(id)}`;

/* slot -> provider name, from the providers list */
const providerOf = (doc) => { const m = new Map(); for (const p of doc.providers || []) for (const s of p.slots) m.set(s, p.name); return m; };

function renderModule(m, doc, opts, close) {
  const links = codeLinks({ path: m.file }, opts);
  const slots = m.role ? m.role.slots : [];
  const facts = [["File", h("code", null, m.file)], ["Code lines", P.fmtN(m.code)], ["Functions", P.fmtN(m.functions)], ["Commits", `${P.fmtN(m.commits)}${m.last ? `, last ${m.last}` : ""}`]];
  const tests = m.tests.length ? h("ul", { class: "cp-list" }, m.tests.map((t) => h("li", null, h("a", { href: P.explorerHref(t) }, h("code", null, t)))))
    : h("p", { class: "cp-dim" }, "No test file has this agent's name in its file name.");
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, h("code", null, m.name)), h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", null, m.doc || h("span", { class: "cp-dim" }, "No module docstring.")),
    h("dl", { class: "cp-facts" }, facts.map(([k, v]) => [h("dt", null, k), h("dd", null, v)])), linkRow(links),
    m.role ? section("Role", h("p", null, "A role with this name exists: ", h("a", { href: hashOf("role", m.role.key) }, h("code", null, m.role.key)), `, served by ${slots.length} key slot${slots.length === 1 ? "" : "s"}.`)) : null,
    noteSection({ path: m.file }), section(`Test files (${m.tests.length})`, tests), bookSection({ path: m.file }));
}

function renderRole(r, doc, close) {
  const prov = providerOf(doc);
  const by = new Map();
  for (const s of r.slots) { const p = prov.get(s) || "unknown"; by.set(p, (by.get(p) || []).concat(s)); }
  const module = (doc.modules || []).find((m) => m.name === r.module);
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, h("code", null, r.key)), h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    r.slots.length ? h("p", null, `${r.slots.length} key slot${r.slots.length === 1 ? "" : "s"} can serve this role.`) : h("p", null, badge("stale", "no key slot"), " No key in AGENT_CAPABILITIES lists this role."),
    h("p", { class: "cp-copy" }, copyButton(r.key, "Copy role key")),
    module ? section("Agent module", h("p", null, h("a", { href: hashOf("agent", module.name) }, h("code", null, module.name)), ` – ${module.doc}`)) : null,
    r.slots.length ? section("Key slots by provider", h("ul", { class: "cp-list" }, [...by].sort((a, b) => b[1].length - a[1].length || (a[0] < b[0] ? -1 : 1)).map(([p, s]) => h("li", null, h("b", null, p), ` (${s.length}) `, s.map((x, i) => [i ? ", " : "", h("code", null, x)]))),
      h("p", { class: "cp-dim" }, "Names of the key slots only. No secret is ever in this data."))) : null,
    (r.aliases || []).length ? section("Aliases", h("p", null, r.aliases.map((a, i) => [i ? ", " : "", h("code", null, a)]))) : null);
}

async function main() {
  const app = document.getElementById("cp-app");
  if (!app) return;
  let doc;
  try { doc = await getJSON("data/code/agents.json"); } catch (e) { app.replaceChildren(empty(`Could not load data/code/agents.json (${e.message}). Run python scripts/refresh_atlas.py.`)); return; }
  let opts = {};
  try { opts = await loadLinkOptions(); } catch { opts = {}; }
  const rows = P.moduleRows(doc);
  const unserved = new Set(P.unservedRoles(doc));
  const detail = h("aside", { class: "cp-detail", "aria-label": "Details", hidden: true });
  const table = makeTable({ cols: COLS, rows, key: (m) => m.name, filterText: rowText, placeholder: "Filter agents, roles, files…", onPick: (m) => { location.hash = hashOf("agent", m.name); } });
  const pills = h("div", { class: "cp-pills" }, (doc.roles || []).map((r) => h("a", { class: "cp-pill", href: hashOf("role", r.key), "data-key": `role:${r.key}` }, r.key, unserved.has(r.key) ? h("span", { class: "cp-dim" }, " · no key slot") : null)));
  const split = h("div", { class: "cp-split" }, detail, h("div", { class: "cp-main" }, h("h2", null, `All ${(doc.roles || []).length} roles`), pills, h("h2", null, "Agent modules"), table.el));
  const close = () => { history.pushState(null, "", location.pathname + location.search); show(); };
  function show() {
    const m = /^#(agent|role):(.+)$/.exec(location.hash);
    let id = "";
    try { id = m ? decodeURIComponent(m[2]) : ""; } catch { id = ""; }
    const mod = m && m[1] === "agent" ? rows.find((r) => r.name === id) : null;
    const role = m && m[1] === "role" ? (doc.roles || []).find((r) => r.key === id) : null;
    split.classList.toggle("has-detail", !!(mod || role));
    detail.hidden = !(mod || role);
    table.select(mod ? mod.name : "");
    for (const a of pills.children) a.setAttribute("aria-current", role && a.dataset.key === `role:${role.key}` ? "true" : "false");
    detail.replaceChildren(mod ? renderModule(mod, doc, opts, close) : role ? renderRole(role, doc, close) : "");
    detail.scrollTop = 0;
  }
  window.addEventListener("hashchange", show);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !detail.hidden && !/^(INPUT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName)) close(); });
  app.replaceChildren(
    freshLine([{ text: `From the MiniMe census ${doc.commit} · ${doc.generated}` }]),
    kpiGrid(P.agentKpis(doc)),
    h("div", { class: "cp-two" }, barsCard("Key slots per provider", P.providerCounts(doc), { note: "Each slot is one API key in AGENT_CAPABILITIES (names only, no secrets)." }),
      barsCard("How many key slots can serve each role", P.roleCounts(doc), { href: (i) => hashOf("role", i.name) })),
    split);
  show();
}

main();
