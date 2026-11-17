// explorer.html in jsdom with a synthetic census: routes, tree keys, filter, tabs, symbols, degraded data, scale.
// model.js caches fetched JSON for the life of the page, so every scenario runs in its own Node process:  node page.mjs [normal|degraded|broken|scale]
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const SCENARIOS = ["normal", "degraded", "broken", "scale"];
const which = process.argv[2];
if (!which) {
  let bad = 0;
  for (const sc of SCENARIOS) {
    const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), sc], { encoding: "utf8", env: { ...process.env, NODE_NO_WARNINGS: "1" } });
    if (r.status === 77) { process.stdout.write(r.stdout); process.exit(77); }
    process.stdout.write(`--- ${sc}\n${r.stdout}${r.stderr}`);
    if (r.status !== 0) bad++;
  }
  process.exit(bad ? 1 : 0);
}
const { boot, makeOk } = await import("./fixture.mjs");
const { ok, done } = makeOk();
const allErrors = [];

if (which === "normal") {
  const P = await boot({ hash: "#/f/backend/agents/a.py" });
  const { doc, w, wait, nav, key, text, rows, errors } = P;
  const tree = doc.getElementById("ex-tree");
  ok(doc.querySelector(".ex-row.is-selected")?.title === "backend/agents/a.py", "deep link selects the file in the tree");
  ok(rows().includes("agents/") && rows().includes("a.py"), "folders above the file are open");
  tree.focus(); key(tree, "Home"); key(tree, "j");
  ok(doc.querySelector(".ex-row.is-cursor")?.title === "backend/agents", "j moves the cursor");
  key(tree, "h"); await wait(); ok(!rows().includes("a.py"), "h closes a folder");
  key(tree, "l"); await wait(); ok(rows().includes("a.py"), "l opens a folder");
  key(tree, "j"); key(tree, "Enter"); await wait(150);
  ok(w.location.hash === "#/f/backend/agents/a.py", `Enter opens the file (${w.location.hash})`);
  ok(doc.getElementById("ex-side").contains(doc.activeElement), "focus stays in the tree after Enter");
  let opened = null; w.open = (u) => { opened = u; }; key(tree, "o"); ok(!!opened && opened.includes("github"), "o opens GitHub");
  const q = doc.getElementById("ex-q"); q.value = "api"; q.dispatchEvent(new w.Event("input")); await wait(220);
  ok(rows().join() === "backend/,api/,b.py", `filter keeps matches and their folders (${rows()})`);
  ok(text("ex-count").trim() === "1 files", "filter count");
  await nav("#/f/README.md"); ok(q.value === "" && rows().includes("README.md"), "opening a file the filter hides clears the filter");
  doc.body.focus(); key(doc, "/"); ok(doc.activeElement === q && doc.getElementById("ex").classList.contains("is-sheet"), "/ focuses the filter");
  doc.getElementById("ex-sheet-close").click(); ok(!doc.getElementById("ex").classList.contains("is-sheet"), "sheet closes");
  doc.getElementById("ex-tree-btn").click(); ok(doc.getElementById("ex-tree-btn").getAttribute("aria-expanded") === "true", "Files button opens the sheet");
  await nav("#/f/backend/agents/a.py"); ok(!doc.getElementById("ex").classList.contains("is-sheet"), "a route closes the sheet");
  ok(!/null|undefined/.test(text("ex-main")), "no stray null/undefined text on a file page");
  ok(text("ex-main").includes("Walkthrough") && text("ex-main").includes("Module docstring"), "Explain tab shows walkthrough and docstring");
  ok(text("ex-insp").includes("backend/api/b.py") && text("ex-insp").includes("httpx"), "inspector: imported-by and external packages");
  ok(!!doc.querySelector(".ex-spark"), "inspector: churn sparkline");
  doc.getElementById("ex-tab-symbols").click(); await wait(150);
  ok(w.location.hash === "#/f/backend/agents/a.py?tab=symbols", "Symbols tab route");
  const sym = () => [...doc.querySelectorAll(".ex-sym__row")];
  ok(sym().length === 4, "all 4 symbols listed");
  ok(text("ex-main").includes("Runs the agent.") && text("ex-main").includes("no description yet"), "note, then docstring, then 'no description yet'");
  ok(!!doc.querySelector(".ex-mark--stale") && !!doc.querySelector(".ex-mark--fresh"), "fresh and stale marks");
  const sort = doc.querySelector('select[aria-label="Sort by"]'); sort.value = "size"; sort.dispatchEvent(new w.Event("change")); ok(sym()[0].dataset.qual === "Agent", "sort by size");
  const chk = doc.querySelector(".ex-check input"); chk.checked = true; chk.dispatchEvent(new w.Event("change")); ok(sym().length === 2, "has-note filter"); chk.checked = false; chk.dispatchEvent(new w.Event("change"));
  doc.querySelector(".ex-sym__sig").click(); await wait(150); ok(/::.+@\d+/.test(w.location.hash), `clicking a symbol writes a symbol route (${w.location.hash})`);
  await nav("#/f/backend/agents/a.py::_clean_query@120-141"); ok(doc.querySelectorAll(".ex-sym__row.is-selected").length === 1 && text("ex-main").includes("_clean_query"), "symbol deep link selects its row");
  await nav("#/backend/agents/a.py@10-20"); ok(doc.querySelector("#ex-main h1")?.textContent === "a.py", "legacy links.js hash opens the file");
  await nav("#/d/backend"); ok(text("ex-main").includes("agents/") && text("ex-main").includes("api/"), "folder page lists children");
  await nav("#/d/backend?tab=symbols"); await wait(200); ok(doc.querySelectorAll(".ex-sym__row").length === 5, "folder Symbols tab loads every symbol below it");
  await nav("#/f/nope.py"); ok(text("ex-main").includes("not in the census"), "unknown path says so");
  await nav("#/f/README.md");
  let copied = ""; Object.defineProperty(w.navigator, "clipboard", { value: { writeText: async (t) => { copied = t; } }, configurable: true });
  [...doc.querySelectorAll("button")].find((b) => /Copilot prompt/.test(b.textContent)).click(); await wait();
  ok(copied.includes("README.md") && copied.includes("atlas-notes"), "copy-prompt button copies the prompt");
  const bar = doc.getElementById("ex-resize"); key(bar, "ArrowRight"); ok(bar.getAttribute("aria-valuenow") === "316", "resize bar keyboard");
  await nav("#/"); ok(text("ex-main").includes("3 files") && text("ex-insp").includes("Keys"), "start page");
  allErrors.push(...errors);
}

if (which === "degraded") {
  const P = await boot({ hash: "#/f/backend/agents/a.py", omit: ["data/graph/file-links.json", "data/index/notes.json", "data/code/imports.json", "data/notes/backend__agents__a.py.json"] });
  ok(P.text("ex-main").includes("no note yet") && P.text("ex-main").includes("Agents."), "works with zero notes");
  ok(P.text("ex-insp").includes("Not built yet") && P.text("ex-insp").includes("imports.json is not available"), "inspector names the missing files");
  await P.nav("#/"); ok(P.text("ex-main").includes("3 files"), "start page without notes.json");
  allErrors.push(...P.errors);
}

if (which === "broken") {
  const P = await boot({ omit: ["data/code/tree.json"] });
  ok(P.text("ex-main").includes("could not be loaded"), "missing tree.json gives a readable error");
}

if (which === "scale") {
  const P = await boot({ big: true });
  ok(P.doc.querySelectorAll(".ex-row").length < 60, `tree draws only visible rows (${P.doc.querySelectorAll(".ex-row").length})`);
  await P.nav("#/f/backend/api/b.py?tab=symbols");
  ok(P.doc.querySelectorAll(".ex-sym__row").length === 200, "symbols table draws 200 rows first");
  P.doc.querySelector(".ex-sym__more").click(); ok(P.doc.querySelectorAll(".ex-sym__row").length === 400, "Show more adds 200");
  await P.nav("#/f/backend/api/b.py::f499@1498-1499"); ok(P.doc.querySelectorAll(".ex-sym__row.is-selected").length === 1, "deep link to a symbol past the first page reveals it");
  allErrors.push(...P.errors);
}
done(allErrors);
