// coverage.html (P22) and the top-bar status chip in jsdom, on a synthetic census and a miniature status.json.
// codeui.js caches fetched JSON for the life of the page, so every scenario runs in its own Node process:  node coverage.mjs [normal|nostatus|audit|chip|chipstale]
// Skips (exit 77) when jsdom is not installed:  npm install --prefix scripts/explorer_tests jsdom
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { jsdomOrSkip, writeFixture, ROOT, makeOk } from "./fixture.mjs";

const HERE = fileURLToPath(import.meta.url);
const SCENARIOS = ["normal", "nostatus", "audit", "chip", "chipstale"];
const which = process.argv[2];
if (!which) {
  let bad = 0;
  for (const sc of SCENARIOS) {
    const r = spawnSync(process.execPath, [HERE, sc], { encoding: "utf8", env: { ...process.env, NODE_NO_WARNINGS: "1" } });
    if (r.status === 77) { process.stdout.write(r.stdout); process.exit(77); }
    process.stdout.write(`--- ${sc}\n${r.stdout}${r.stderr}`);
    if (r.status !== 0) bad++;
  }
  process.exit(bad ? 1 : 0);
}

const JSDOM = await jsdomOrSkip();
const { ok, done } = makeOk();

const prompts = JSON.parse(fs.readFileSync(path.join(ROOT, "content/copilot-prompts.json"), "utf8"));
const iso = (daysAgo) => new Date(Date.now() - daysAgo * 86400000).toISOString().slice(0, 10);

function status({ censusAge = 2, graphAge = 3, graphCommit = "a1389bf", notesCommit = "a1389bfdeadbeef" + "0".repeat(25), withFlows = true } = {}) {
  return {
    schema: 1,
    sources: { census: { commit: "a1389bf", date: iso(censusAge) }, graph: { commit: graphCommit, date: iso(graphAge) }, notes: { commit: notesCommit, date: iso(5) }, arch: { commit: "a1389bf", flow_commits: [] }, docs: { date: iso(10) } },
    totals: { files: 3, symbols: 5 },
    notes: { blobs_known: true, totals: { files: 3, noted: 1, fresh: 1, stale: 0, missing: 2, symbols_wanted: 6, symbols_covered: 3 },
      tiers: { 1: { files: 1, noted: 1, fresh: 1, stale: 0, missing: 0, symbols_wanted: 3, symbols_covered: 3 }, 2: { files: 2, noted: 0, fresh: 0, stale: 0, missing: 2, symbols_wanted: 3, symbols_covered: 0 }, 3: { files: 0, noted: 0, fresh: 0, stale: 0, missing: 0, symbols_wanted: 0, symbols_covered: 0 } } },
    folders: {
      backend: { files: 2, symbols: 5, elig: 3, noted: 1, fresh: 1, stale: 0 },
      "backend/agents": { files: 1, symbols: 4, elig: 1, noted: 1, fresh: 1, stale: 0 },
      "backend/api": { files: 1, symbols: 1, elig: 2, noted: 0, fresh: 0, stale: 0 },
    },
    flows: withFlows ? {
      "request-path": { title: "Request path", kind: "sequence", status: "missing", items: 0, counts: {}, commit: null, incomplete: [], views: ["task-sequence"] },
      "task-pipeline": { title: "Task pipeline", kind: "pipeline", status: "missing", items: 0, counts: {}, commit: null, incomplete: [], views: ["task-pipeline"] },
      memory: { title: "Memory", kind: "pipeline", status: "missing", items: 0, counts: {}, commit: null, incomplete: [], views: ["memory"] },
    } : {},
    flow_order: withFlows ? ["request-path", "task-pipeline", "memory"] : [],
    flow_totals: { flows: 3, written: 0 },
    stale: [],
    next: { basis: "Preview basis text.", needing: 2, per_tier: { 1: 0, 2: 2, 3: 0 }, files: [
      { path: "backend/api/b.py", tier: 2, reason: "new", links: 9, commits: 4, lines: 40, symbols: 1, tier_exact: false },
      { path: "backend/agents/c.py", tier: 2, reason: "new", links: 3, commits: 1, lines: 10, symbols: 2, tier_exact: false }] },
  };
}

async function boot({ hash = "", omitStatus = false, seed = {}, stat = status(), shell = false } = {}) {
  const data = fs.mkdtempSync(path.join(os.tmpdir(), "coverage-"));
  writeFixture(data, {});
  const W = (rel, o) => { const p = path.join(data, rel); fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, JSON.stringify(o)); };
  if (!omitStatus) W("data/index/status.json", stat);
  W("content/copilot-prompts.json", prompts);
  W("content/config.json", { freshness: { warnDays: { census: 14, graph: 14, notes: 30, docs: 60 } } });
  W("data/index/stats.json", { commit: "a1389bf", generated: iso(2), files: 3 });
  if (shell) W("content/nav.json", JSON.parse(fs.readFileSync(path.join(ROOT, "content/nav.json"), "utf8")));
  const html = fs.readFileSync(path.join(ROOT, "coverage.html"), "utf8").replace(/<script[\s\S]*?<\/script>/g, "");
  const dom = new JSDOM(html, { url: `http://localhost:8000/coverage.html${hash}`, pretendToBeVisual: true });
  const w = dom.window;
  const set = (k, v) => Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
  for (const k of ["document", "location", "history", "localStorage", "sessionStorage", "Node", "HTMLElement", "requestAnimationFrame", "cancelAnimationFrame", "CustomEvent", "KeyboardEvent"]) set(k, w[k]);
  set("window", w); set("navigator", w.navigator); set("getComputedStyle", w.getComputedStyle.bind(w));
  w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
  w.matchMedia = w.matchMedia || ((q) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} }));
  set("matchMedia", w.matchMedia);
  for (const [k, v] of Object.entries(seed)) w.localStorage.setItem(k, v);
  const errors = [];
  w.addEventListener("error", (e) => errors.push(e.message));
  process.on("unhandledRejection", (e) => errors.push(`rejection: ${e}`));
  const rootPath = pathToFileURL(ROOT).pathname.replace(/\/?$/, "/");
  globalThis.fetch = async (u) => {
    const rel = decodeURIComponent(new URL(String(u)).pathname).slice(rootPath.length);
    const f = path.join(data, rel);
    return fs.existsSync(f) ? { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(f, "utf8")), text: async () => fs.readFileSync(f, "utf8") } : { ok: false, status: 404, json: async () => ({}), text: async () => "" };
  };
  const wait = (ms = 80) => new Promise((r) => setTimeout(r, ms));
  if (shell) w.document.documentElement.dataset.sidebar = "open";
  await import(`${pathToFileURL(path.join(ROOT, "assets/js/coverage.js")).href}?${Math.random()}`);
  if (shell) await import(`${pathToFileURL(path.join(ROOT, "assets/js/shell.js")).href}?${Math.random()}`);
  await wait(300);
  const doc = w.document;
  return { w, doc, errors, wait, text: (sel) => [...doc.querySelectorAll(sel)].map((n) => n.textContent.replace(/\s+/g, " ").trim()).join(" | ") };
}

const folderNames = (doc) => [...doc.querySelectorAll(".cv-heattable tbody th a")].map((a) => a.textContent);

if (which === "normal") {
  const P = await boot();
  const { doc, text, wait, w, errors } = P;
  ok(text("main h2").includes("How fresh is the Atlas?") && text("main h2").includes("Notes by tier") && text("main h2").includes("Where the coverage is")
    && text("main h2").includes("Architecture flows") && text("main h2").includes("Stale notes") && text("main h2").includes("Annotate next"), "all six sections are drawn");
  ok(doc.querySelectorAll(".cv-tile").length === 4, "four freshness tiles");
  ok(text(".cv-tile--stale") === "", "nothing is amber when everything is recent and from one commit");
  ok(text("#tiers tbody").includes("T1") && text("#tiers tbody").includes("33 %"), "the tier table shows T1 and the 33 % total");
  ok(folderNames(doc).join() === "backend", `only the top folder is shown at first (${folderNames(doc)})`);
  doc.querySelector(".cv-tog").click(); await wait();
  ok(folderNames(doc).join() === "backend,agents,api", `the toggle opens the folder (${folderNames(doc)})`);
  ok(doc.querySelector(".cv-tog").getAttribute("aria-expanded") === "true", "aria-expanded follows");
  const links = [...doc.querySelectorAll(".cv-heattable tbody th a")].map((a) => a.getAttribute("href"));
  ok(links[0] === "explorer.html#/d/backend" && links[1] === "explorer.html#/d/backend/agents", `folder names open the Explorer (${links})`);
  ok(text("#heat .cv-foot").includes("You have not marked any symbol yet"), "no marks: the footer says how to start");
  ok(text("#next .cv-next").indexOf("backend/api/b.py") < text("#next .cv-next").indexOf("backend/agents/c.py"), "the next list keeps the order of status.json");
  const pres = [...doc.querySelectorAll("#next .cv-pre")].map((p) => p.textContent);
  ok(pres.length === 2, "two prompts: notes and flows");
  ok(pres[0].includes("python scripts/notes.py todo --tier 2 --limit 20") && pres[0].includes("backend/api/b.py") && pres[0].includes(prompts.A.slice(0, 60)), "the notes prompt has the command, the files and prompt A");
  ok(pres[1].includes("request-path, task-pipeline") && !pres[1].includes("memory,") && pres[1].includes(prompts.C.slice(0, 60)), "the flow prompt is C and names two flows");
  ok(text("#flows tbody").includes("Request path") && text("#flows tbody").includes("missing"), "the flow table lists the flows");
  ok(text("#stale").includes("Every note matches the code"), "no stale notes says so");
  const clone = doc.querySelector("main").cloneNode(true);
  clone.querySelectorAll(".cv-pre").forEach((n) => n.remove());          // the Copilot prompts legitimately contain the word null
  ok(!/undefined|null|NaN/.test(clone.textContent), "no stray undefined/null/NaN text");
  ok(doc.querySelector(".cv-tog--none") !== null, "a folder without children has no toggle");
  ok(errors.length === 0, `no page errors (${errors})`);
  done(errors);
}

if (which === "nostatus") {
  const P = await boot({ omitStatus: true });
  ok(P.text("#cv-app").includes("status.json could not be loaded"), "a missing status.json is explained, not a blank page");
  ok(P.text("#cv-app").includes("build_status.py"), "and says how to fix it");
  done(P.errors);
}

if (which === "audit") {
  const marks = { v: 1, marks: [
    { path: "backend/agents/a.py", qual: "run", state: "reviewed", note: "", hash: "h_run", commit: "a1389bf", start: 10, end: 20, at: "2026-11-01T10:00:00.000Z" },
    { path: "backend/agents/a.py", qual: "Agent.step", state: "reviewed", note: "", hash: "OLDHASH", commit: "a1389bf", start: 30, end: 40, at: "2026-11-01T10:00:00.000Z" },
    { path: "backend/agents/a.py", qual: "Agent", state: "concern", note: "x", hash: "h_Agent", commit: "a1389bf", start: 25, end: 50, at: "2026-11-01T10:00:00.000Z" }] };
  const P = await boot({ seed: { minime_audit_v1: JSON.stringify(marks) } });
  const { doc, wait, text } = P;
  doc.querySelector(".cv-tog").click(); await wait();
  const row = [...doc.querySelectorAll(".cv-heattable tbody tr")].find((r) => r.querySelector("th a").textContent === "agents");
  const audit = row.querySelectorAll("td")[2];
  ok(audit.textContent.includes("50 %"), `2 of 4 symbols are counted as reviewed before checking (${audit.textContent.trim()})`);
  ok(audit.querySelector(".cv-flag--concern") !== null, "the concern is flagged with a glyph");
  ok(text("#heat .cv-foot").includes("have not been compared with the current code yet"), "the footer says the reviews are not compared yet");
  doc.querySelector("#heat .cv-tools .mm-btn:nth-child(3)").click();
  await wait(400);
  const row2 = [...doc.querySelectorAll(".cv-heattable tbody tr")].find((r) => r.querySelector("th a").textContent === "agents");
  const cell = row2.querySelectorAll("td")[2];
  ok(cell.textContent.includes("25 %") && cell.querySelector(".cv-flag:not(.cv-flag--concern)") !== null, `after the check the changed review needs re-review (${cell.textContent.trim()})`);
  ok(!text("#heat .cv-foot").includes("have not been compared"), "the footer no longer says unchecked");
  done(P.errors);
}

if (which === "chip") {
  const P = await boot({ shell: true });
  const chip = P.doc.querySelector(".mm-top .mm-chip");
  ok(!!chip && chip.tagName === "A" && chip.getAttribute("href").endsWith("/coverage.html"), "the chip is a link to coverage.html");
  ok(chip && chip.textContent.includes("census 2 days") && chip.textContent.includes("notes 33%"), `the chip shows ages and notes % (${chip && chip.textContent.trim()})`);
  ok(chip && !chip.classList.contains("mm-chip--stale"), "not amber when everything is in date and in step");
  done(P.errors);
}

if (which === "chipstale") {
  const P = await boot({ shell: true, stat: status({ censusAge: 20, graphCommit: "50e25b5" }) });
  const chip = P.doc.querySelector(".mm-top .mm-chip");
  ok(!!chip && chip.classList.contains("mm-chip--stale"), "amber when the census is older than its limit and the graph is from another commit");
  ok(chip && chip.querySelector(".mm-chip__flag") !== null && chip.textContent.includes("Out of step"), "the amber state is also a glyph and words");
  ok(chip && chip.getAttribute("title").includes("50e25b5"), "the tooltip says why");
  done(P.errors);
}