/* MiniMe Atlas 2 - the Infra page (P18). Loaded by infra.html, which is a shell: this module draws everything from
     data/code/infra.json   compose services, Dockerfiles, CI jobs, dependency manifests and every environment variable the code reads
                            (scripts/refresh_atlas.py writes it from the census)
   The pure logic is in dataviews.js (Node tests it). Only variable NAMES are ever shown: the census holds no values. Every
   file name links to the Explorer; the files that read a variable are listed in full when the variable is selected. */
import { h } from "./explorer/dom.js";
import * as D from "./dataviews.js";
import { getJSON, empty, badge, kpiGrid, barsCard, freshLine, section, copyButton, makeTable } from "./codeui.js";

const fileLink = (p, text) => h("a", { href: D.explorerHref(p) }, h("code", null, text || p));
const pills = (items, kind) => h("div", { class: "cp-pills" }, items.map((x) => h("span", { class: "cp-pill", "data-kind": kind || null }, x)));

/* ------------------------------------------------------------------ services and Dockerfiles */
function serviceCard(s) {
  const how = s.build ? "Built from its Dockerfile" : s.image ? `Image ${s.image}` : "";
  return h("section", { class: "mm-card" }, h("h3", { class: "mm-card__title" }, s.name), how ? h("p", { class: "cp-dim" }, how) : null,
    pills([...s.ports.map((p) => `port ${p}`), ...s.depends_on.map((d) => `needs ${d}`), ...s.env_names]));
}

function dockerCard(d) {
  const stages = D.stageSummary(d.stages);
  return h("section", { class: "mm-card" }, h("h3", { class: "mm-card__title" }, d.file ? fileLink(d.file, d.name) : d.name),
    pills(stages.map((s) => (s.n > 1 ? `${s.image} ×${s.n}` : s.image))),
    h("p", { class: "cp-dim" }, d.expose.length ? `Port ${d.expose.join(", ")} · ` : "", d.cmd ? ["starts with ", h("code", null, d.cmd)] : "no start command found"));
}

function servicesBlock(doc) {
  const compose = doc.compose_files || [];
  return section("Services",
    compose.length ? h("p", { class: "cp-dim" }, "From ", compose.map((f, i) => [i ? ", " : "", fileLink(f)]), ".") : null,
    h("div", { class: "cp-two" }, (doc.services || []).map(serviceCard)),
    h("h3", null, "Dockerfiles"), h("div", { class: "cp-two" }, (doc.dockerfiles || []).map(dockerCard)));
}

/* ------------------------------------------------------------------ CI */
function ciBlock(doc) {
  return section("CI pipeline", (doc.ci || []).map((wf) => h("div", null,
    h("h3", null, fileLink(wf.file, wf.name), " ", h("span", { class: "cp-dim" }, wf.triggers.length ? `runs on ${wf.triggers.join(", ")}` : "")),
    h("div", { class: "cp-two" }, wf.jobs.map((j) => h("section", { class: "mm-card" }, h("h3", { class: "mm-card__title" }, j.name),
      h("ol", { class: "cp-list" }, j.steps.map((st) => h("li", null, st.text, st.pin ? [" ", badge("here", `pinned ${st.pin}`, "The step is pinned to this commit of the action, not to a tag.")] : null)))))))));
}

/* ------------------------------------------------------------------ dependencies */
function depsBlock(doc) {
  const total = (doc.dependencies || []).reduce((n, m) => n + D.depCount(m), 0);
  return section(`Dependencies (${D.fmtN(total)})`, (doc.dependencies || []).map((m) => {
    const label = D.manifestLabel(m);
    if (!m.parsed) return h("p", { class: "cp-dim" }, fileLink(m.file), " is not listed: the census keeps only the head of this kind of file.");
    return h("details", { class: "mm-card cp-deps" }, h("summary", null, h("b", null, label), " ", h("span", { class: "cp-dim" }, `${D.fmtN(D.depCount(m))} · `), fileLink(m.file)),
      m.groups.map((g) => [m.groups.length > 1 ? h("p", { class: "cp-label" }, `${g.title} (${g.items.length})`) : null,
        h("div", { class: "cp-pills" }, g.items.map((it) => h("span", { class: "cp-pill" }, it.name, it.spec ? [" ", h("span", { class: "cp-dim" }, it.spec)] : null)))]));
  }));
}

/* ------------------------------------------------------------------ environment variables */
const ENV_COLS = [
  { id: "name", label: "Variable", get: (r) => r.name, mono: true },
  { id: "uses", label: "Files using it", get: (r) => r.uses, num: true },
  { id: "first", label: "First file", get: (r) => r.short, mono: true, render: (r) => (r.first ? h("a", { href: D.explorerHref(r.first) }, r.short) : "") },
  { id: "doc", label: "In .env.example", get: (r) => (r.documented ? "yes" : "no"), render: (r) => (r.documented ? badge("ok", "yes", r.docText) : badge("stale", "no", "No .env.example names this variable")) },
  { id: "kind", label: "Read by", get: (r) => (r.testOnly ? "tests only" : "code"), render: (r) => (r.testOnly ? badge("reviewed", "tests only", "Every file that reads it is a test") : "code") },
];
const envText = (r) => [r.name, ...r.files, ...r.documented_in, r.comment].join(" ");

function fileList(files) {
  return h("ul", { class: "cp-list" }, files.map((f) => h("li", null, fileLink(f))));
}

function renderEnv(r, close) {
  const testFiles = r.test_files || [];
  return h("div", { class: "cp-detail__in" },
    h("header", { class: "cp-detail__head" }, h("h2", null, h("code", null, r.name)), h("button", { type: "button", class: "mm-btn", "aria-label": "Close the details", onclick: close }, "Close")),
    h("p", null, copyButton(r.name, "Copy name")),
    r.comment ? h("p", { class: "cp-lede" }, r.comment, " ", h("span", { class: "cp-dim" }, "(the comment next to it in .env.example)")) : null,
    h("dl", { class: "cp-facts" }, h("dt", null, "Documented in"), h("dd", null, r.documented_in.length ? r.documented_in.map((f, i) => [i ? ", " : "", fileLink(f)]) : "no .env.example names it"),
      h("dt", null, "Read in"), h("dd", null, `${r.codeFiles.length} code ${r.codeFiles.length === 1 ? "file" : "files"}, ${testFiles.length} ${testFiles.length === 1 ? "test" : "tests"}`)),
    r.codeFiles.length ? section(`Code (${r.codeFiles.length})`, fileList(r.codeFiles)) : null,
    testFiles.length ? section(`Tests (${testFiles.length})`, fileList(testFiles)) : null,
    h("p", { class: "cp-dim cp-caveat" }, "A text match from the census: the file names the variable. Only the name is recorded, never a value."));
}

const envHash = (r) => `#${encodeURIComponent(r.key)}`;
const envFromHash = (rows, hash) => {
  let k = "";
  try { k = decodeURIComponent(String(hash || "").replace(/^#/, "")); } catch { return null; }
  return k ? rows.find((r) => r.key === k) || null : null;
};

function envBlock(doc) {
  const rows = D.envRows(doc);
  const detail = h("aside", { class: "cp-detail", "aria-label": "Variable details", hidden: true });
  const table = makeTable({ cols: ENV_COLS, rows, key: (r) => r.key, filterText: envText, placeholder: "Filter by name, file, comment…", onPick: (r) => { location.hash = envHash(r); } });
  const split = h("div", { class: "cp-split" }, detail, h("div", { class: "cp-main" }, table.el));
  const close = () => { history.pushState(null, "", location.pathname + location.search); show(null); };
  function show(r) {
    split.classList.toggle("has-detail", !!r);
    detail.hidden = !r;
    table.select(r ? r.key : "");
    if (r) { detail.replaceChildren(renderEnv(r, close)); detail.scrollTop = 0; } else detail.replaceChildren();
  }
  window.addEventListener("hashchange", () => show(envFromHash(rows, location.hash)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !detail.hidden && !/^(INPUT|TEXTAREA)$/.test(document.activeElement && document.activeElement.tagName)) close(); });
  show(envFromHash(rows, location.hash));
  const unused = doc.env_unused_examples || [];
  return [
    h("h2", { id: "env" }, `Environment variables used in code (${D.fmtN(rows.length)})`), split,
    unused.length ? h("details", { class: "mm-card cp-deps" }, h("summary", null, h("b", null, `${D.fmtN(unused.length)} names in an .env.example that no code file reads`)),
      h("p", { class: "cp-dim" }, "Documented but never read by the files the census scanned: the name may be read another way (a prefix, a framework), or no longer be used."),
      h("div", { class: "cp-pills" }, unused.map((u) => h("span", { class: "cp-pill", title: u.file }, u.name)))) : null,
  ];
}

async function main() {
  const app = document.getElementById("cp-app");
  if (!app) return;
  let doc;
  try { doc = await getJSON("data/code/infra.json"); } catch (e) { app.replaceChildren(empty(`Could not load data/code/infra.json (${e.message}). Run python scripts/refresh_atlas.py.`)); return; }
  app.replaceChildren(
    freshLine([{ text: `Infra from MiniMe ${doc.commit} · ${doc.generated}` }]),
    kpiGrid(D.infraKpis(doc)),
    servicesBlock(doc), ciBlock(doc), depsBlock(doc),
    h("div", { class: "cp-two" }, barsCard("Variable families", D.envFamilies(doc), { note: "Grouped by the part of the name before the first underscore; a family needs three or more." })),
    ...envBlock(doc));
}

main();
