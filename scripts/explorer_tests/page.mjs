// explorer.html in jsdom with a synthetic census: routes, tree keys, filter, tabs, symbols, degraded data, scale.
// model.js caches fetched JSON for the life of the page, so every scenario runs in its own Node process:  node page.mjs [normal|degraded|broken|scale]
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const SCENARIOS = ["normal", "degraded", "broken", "scale", "source", "nomanifest", "fetchfail", "drift", "symbol", "nocallers", "walkthrough", "walknarrow", "walklong", "docs", "book", "nobook"];
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
  await P.nav("#/f/backend/api/b.py?tab=source");
  ok(P.doc.querySelectorAll(".ex-line").length === 1000 && !P.doc.querySelector(".ex-src__more").hidden, "a 2,500-line file is drawn 1,000 lines at a time");
  P.doc.querySelector(".ex-src__more").click(); ok(P.doc.querySelectorAll(".ex-line").length === 2000, "Show more adds 1,000 lines");
  await P.nav("#/f/backend/api/b.py@2400-2410?tab=source"); ok(P.doc.querySelectorAll(".ex-line").length === 2500 && P.doc.querySelector(".ex-src__more").hidden && P.doc.querySelectorAll(".ex-line.is-sel").length === 11, "a range far down is drawn and marked, nothing is left hidden");
  await P.nav("#/f/backend/api/b.py@1500?tab=source"); ok(P.doc.querySelectorAll(".ex-line").length === 1700 && P.doc.getElementById("ex-L1500").classList.contains("is-sel"), `a range past the first chunk draws up to it (${P.doc.querySelectorAll(".ex-line").length})`);
  allErrors.push(...P.errors);
}
if (which === "book") {                         // P15: "Discussed in the book" on the file and symbol pages
  const P = await boot({ hash: "#/f/backend/agents/a.py" });
  const { doc, nav, errors } = P;
  const sec = () => doc.querySelector(".ex-book");
  const items = () => [...doc.querySelectorAll(".ex-book li")].map((li) => li.textContent.replace(/\s+/g, " ").trim());
  ok(!!sec() && sec().querySelector("h3").textContent === "Discussed in the book (2)", `a file lists the sections that mention it and its symbols (${sec()?.querySelector("h3").textContent})`);
  ok(items()[0].startsWith("Chapter X › Intro") && items()[0].includes("×2") && items()[1].startsWith("Chapter Y › Running it") && items()[1].includes("run"), `chapter order, counts and the symbol (${JSON.stringify(items())})`);
  ok(doc.querySelector(".ex-book a").getAttribute("href") === "doc-x.html#intro", "each item links to the chapter section");
  ok(!!doc.querySelector(".ex-tabs") && sec().compareDocumentPosition(doc.querySelector(".ex-tabs")) & 4, "the section sits above the tabs");
  await nav("#/f/backend/agents/a.py::run?tab=symbols");
  ok(items().length === 1 && items()[0].startsWith("Chapter Y"), `a symbol page lists only that symbol's mentions (${JSON.stringify(items())})`);
  await nav("#/f/backend/agents/a.py::Agent.step?tab=symbols");
  ok(!sec(), "a symbol nobody mentions has no section");
  await nav("#/f/backend/api/b.py");
  ok(!sec(), "a file nobody mentions has no section");
  done(errors);
}

if (which === "nobook") {                       // P15: mentions.json is optional
  const P = await boot({ hash: "#/f/backend/agents/a.py", omit: ["data/index/mentions.json"] });
  ok(!P.doc.querySelector(".ex-book") && !!P.doc.querySelector(".ex-file") && !!P.doc.querySelector(".ex-tabs"), "without mentions.json the file page is the same as before, with no error");
  done(P.errors);
}

if (which === "symbol") {                       // P14c: the symbol panel
  const P = await boot({ hash: "#/f/backend/agents/a.py::run@10-20?tab=symbols" });
  const { doc, w, wait, nav, text, errors } = P;
  const panel = () => doc.querySelector(".ex-symp");
  const sec = (name) => [...doc.querySelectorAll(".ex-symp__sec")].find((x) => x.querySelector("h4")?.textContent.startsWith(name));
  ok(!!panel() && panel().querySelector(".ex-symp__title").textContent.startsWith("run"), "a symbol route shows the symbol panel");
  ok(panel().querySelector(".ex-symp__sig").textContent === "run(x: int) -> str", `signature is the census one (${panel().querySelector(".ex-symp__sig").textContent})`);
  ok(text("ex-main").includes("Runs the agent.") && text("ex-main").includes("Longer text about run."), "note summary and details");
  ok(!!panel().querySelector(".mm-badge--ai") && !!panel().querySelector(".mm-badge--ok") && text("ex-main").includes("medium confidence"), "AI-written, fresh and confidence badges");
  ok(text("ex-main").includes("@cached"), "decorator shown");
  const rows = [...sec("Parameters").querySelectorAll("tbody tr")].map((r) => [...r.children].map((c) => c.textContent.replace(/\s+/g, " ").trim()));
  ok(rows.length === 2 && rows[0][0] === "x" && rows[0][1] === "int" && rows[0][3] === "the input value", `parameters table joins census and note (${JSON.stringify(rows[0])})`);
  ok(rows[1][0].startsWith("extra") && rows[1][0].includes("note") && rows[1][3] === "only the note knows", "a parameter only the note knows is kept and marked");
  ok(sec("Returns").textContent.includes("str") && sec("Returns").textContent.includes("the result text"), "returns: type and note text");
  ok(sec("Raises").textContent.includes("ValueError") && sec("Raises").textContent.includes("KeyError when missing"), "raises: census and note");
  ok(sec("Side effects").textContent.includes("writes a log"), "side effects");
  const ev = [...sec("Evidence").querySelectorAll("a")].map((a) => a.getAttribute("href"));
  ok(ev.join() === "#/f/backend/agents/a.py::run@12-14?tab=source,#/f/backend/agents/a.py::run@18?tab=source", `evidence links into the Source tab (${ev})`);
  const calls = sec("Calls");
  ok(calls.querySelector("h4").textContent === "Calls (5)", `calls counted without duplicates (${calls.querySelector("h4").textContent})`);
  const refs = [...calls.querySelectorAll("a.ex-symp__ref")].map((a) => [a.textContent, a.getAttribute("href")]);
  ok(refs.length === 2 && refs[0][0] === "Agent" && refs[1][1] === "#/f/backend/api/b.py::route?tab=symbols" && refs[1][0] === "backend/api/b.py::route", `resolved calls are links, other files show their path (${JSON.stringify(refs)})`);
  ok(calls.textContent.includes("gone/x.py::f") && !calls.querySelector('a[href*="gone"]'), "a call into a file the census does not have is plain text, not a dead link");
  ok(calls.querySelector("details").textContent.includes("print") && calls.querySelector("details").textContent.includes("os.path.join"), "unresolved names are tucked away in a details element");
  const by = sec("Called by");
  ok(by.querySelector("h4").textContent === "Called by (4)" && [...by.querySelectorAll("ul")[0].querySelectorAll("li")].map((l) => l.textContent).join() === "Agent.step", "callers: code first");
  ok(by.querySelector("details")?.textContent.includes("3 from tests") && by.querySelector("details a")?.getAttribute("href").startsWith("#/f/backend/api/b.py::"), "callers from tests are grouped and linked");
  ok(doc.querySelectorAll(".ex-sym__row.is-selected").length === 1, "the list below still marks the row");
  ok(doc.querySelectorAll(".ex-symp__sec h4").length >= 7 && !/null|undefined/.test(text("ex-main")), `no stray null/undefined text (${(text("ex-main").match(/.{0,30}(null|undefined).{0,30}/) || [])[0]})`);
  const view = panel().querySelector(".ex-go a").getAttribute("href");
  ok(view === "#/f/backend/agents/a.py::run@10-20?tab=source", `View source keeps the symbol and its lines (${view})`);
  panel().querySelector('a.ex-symp__ref[href*="b.py"]').click(); await wait(200);
  ok(w.location.hash === "#/f/backend/api/b.py::route?tab=symbols" || w.location.hash.startsWith("#/f/backend/api/b.py::route"), `clicking a call opens that symbol (${w.location.hash})`);
  ok(panel()?.querySelector(".ex-symp__title").textContent.startsWith("route"), "its panel is shown");
  ok(text("ex-main").includes("No description yet") && sec("Called by").textContent.includes("1") , "a symbol without a note says so and still shows facts");
  await nav("#/f/backend/agents/a.py::Agent@25-50?tab=symbols");
  ok(panel().querySelector(".ex-pill").textContent === "class" && text("ex-main").includes("Inherits from") && !!sec("Methods (1)") && !sec("Calls"), "class panel: bases, methods, no calls");
  ok(sec("Called by")?.querySelector("h4").textContent === "Called by (1)", "class: constructor callers");
  await nav("#/f/backend/agents/a.py::nothing?tab=symbols");
  ok(!panel() && text("ex-main").includes("no function or class named nothing"), "an unknown symbol says so instead of an empty panel");
  await nav("#/f/backend/agents/a.py?tab=symbols"); ok(!panel(), "no panel without a symbol in the route");
  done(errors);
}
if (which === "nocallers") {                    // an Atlas without data/code/callers/
  const P = await boot({ hash: "#/f/backend/agents/a.py::run@10-20?tab=symbols", omit: ["data/code/callers/s0.json"] });
  const { doc, text, errors } = P;
  ok(!!doc.querySelector(".ex-symp") && text("ex-main").includes("Caller data is not in this Atlas"), "missing callers file: the panel still opens and says why there are no callers");
  ok(text("ex-main").includes("Calls (5)"), "calls come from the census and still show");
  done(errors);
}
if (which === "source") {
  const P = await boot({ hash: "#/f/backend/agents/a.py?tab=source" });
  const { doc, w, wait, nav, key, text, errors } = P;
  const tabSel = () => doc.querySelector('[role="tab"][aria-selected="true"]')?.id;
  const lines = () => doc.querySelectorAll(".ex-line");
  const sel = () => [...doc.querySelectorAll(".ex-line.is-sel")].map((e) => e.id);
  const click = (n, o = {}) => doc.querySelector(`#ex-L${n} .ex-line__n`).dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true, ...o }));
  const info = () => text("ex-main").match(/\d[\d,]* lines?( ·[^A-Z]*?)?(?= Raw source| Copy|$)/)?.[0];
  const btn = (re) => [...doc.querySelectorAll("#ex-main button")].find((b) => re.test(b.textContent));
  let copied = ""; Object.defineProperty(w.navigator, "clipboard", { value: { writeText: async (t) => { copied = t; } }, configurable: true });

  ok(tabSel() === "ex-tab-source", "?tab=source opens the Source tab");
  ok(lines().length === 150, `every line of a short file is drawn (${lines().length})`);
  ok(doc.querySelector("#ex-L7 .ex-line__n").textContent === "7" && doc.querySelector("#ex-L7 .ex-line__t").textContent === "line 7", "line number and text");
  ok(doc.querySelector("#ex-L10 .ex-line__t").textContent === "def run(x):  # <b>not html</b>" && !doc.querySelector(".ex-code b"), "code is shown as text, never parsed as markup");
  ok(doc.querySelector("#ex-L11 .ex-line__t").textContent === "" && doc.querySelector("#ex-L12 .ex-line__t").textContent === "\treturn '&amp;'", "blank lines, tabs and entities are kept");
  /* P14b: the colours arrive after the plain text (boot waits long enough for the import of the vendored engine) */
  ok(doc.querySelector(".ex-code")?.classList.contains("is-hl") && doc.querySelector(".ex-code").dataset.lang === "python", "syntax colours are on and the file is read as python");
  ok(doc.querySelector("#ex-L10 .hljs-keyword")?.textContent === "def" && doc.querySelector("#ex-L10 .hljs-comment")?.textContent.startsWith("# <b>not html"), "keyword and comment are coloured spans");
  ok(!doc.querySelector(".ex-code b") && doc.querySelector("#ex-L10 .ex-line__t").textContent === "def run(x):  # <b>not html</b>", "colours change no text and add no markup");
  ok(doc.querySelectorAll(".ex-line").length === 150 && doc.querySelector("#ex-L12 .ex-line__t").textContent === "\treturn '&amp;'", "every line is still there after the colours");
  ok(doc.querySelector(".ex-src__more").hidden === true, "no 'Show more lines' button when the whole file is drawn");
  const hlBox = [...doc.querySelectorAll(".ex-src__tools label")].find((l) => /Syntax colours/.test(l.textContent))?.querySelector("input");
  ok(!!hlBox && hlBox.checked && !hlBox.closest("label").hidden, "a Syntax colours checkbox appears, ticked");
  hlBox.checked = false; hlBox.dispatchEvent(new w.Event("change")); ok(!doc.querySelector(".ex-code").classList.contains("is-hl") && w.localStorage.getItem("minime_ex_hl") === "0", "unticking turns the colours off and remembers it");
  hlBox.checked = true; hlBox.dispatchEvent(new w.Event("change")); ok(doc.querySelector(".ex-code").classList.contains("is-hl") && w.localStorage.getItem("minime_ex_hl") === "1", "ticking turns them back on");
  ok(doc.querySelector("#ex-L5 .ex-line__n").getAttribute("href") === "#/f/backend/agents/a.py@5?tab=source" && doc.querySelector("#ex-L5 .ex-line__n").getAttribute("aria-label") === "Line 5", "a line number is a real link with a label");
  ok(text("ex-main").includes("150 lines") && sel().length === 0, "no selection without a range");
  ok(!doc.querySelector("#ex-main .ex-callout--warn"), "no warning when the copy and the census agree");
  ok(!/null|undefined/.test(text("ex-main")), "no stray null/undefined text");
  const gh = () => doc.querySelector(".ex-src__go a[target=_blank]:nth-of-type(2)")?.getAttribute("href") || "";
  ok(/\/blob\/a1389bfdeadbeef0+\/backend\/agents\/a\.py$/.test(gh()), `GitHub button without a selection (${gh()})`);

  click(20); await wait(20);
  ok(w.location.hash === "#/f/backend/agents/a.py@20?tab=source", `a click selects a line and rewrites the address (${w.location.hash})`);
  ok(sel().join() === "ex-L20" && text("ex-main").includes("line 20 selected"), "one line is marked");
  ok(gh().endsWith("#L20"), `GitHub button follows the selection (${gh()})`);
  ok(!!btn(/^Copy line$/), "copy button says Copy line");
  click(25, { shiftKey: true }); await wait(20);
  ok(w.location.hash === "#/f/backend/agents/a.py@20-25?tab=source" && sel().length === 6, `Shift+click extends the range (${w.location.hash}, ${sel().length} marked)`);
  ok(gh().endsWith("#L20-L25"), "GitHub range");
  btn(/^Copy lines$/).click(); await wait(20); ok(copied === ["line 20", "line 21", "line 22", "line 23", "line 24", "line 25"].join("\n"), "Copy lines copies exactly the selected lines");
  key(doc.querySelector(".ex-code"), "Escape"); await wait(20);
  ok(sel().length === 0 && w.location.hash === "#/f/backend/agents/a.py?tab=source", `Esc clears the selection and the range in the address (${w.location.hash})`);
  click(30); click(30); ok(sel().length === 0, "clicking the only selected line clears it");
  btn(/^Copy file$/).click(); await wait(20); ok(copied.split("\n").length === 150 && copied.startsWith("def") === false && copied.startsWith("line 1\n"), "Copy file copies all 150 lines without a trailing blank");

  const go = (v) => { const i = doc.querySelector(".ex-src__goto"); i.value = v; i.form.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); };
  go("100-105"); await wait(20); ok(sel().length === 6 && w.location.hash.endsWith("@100-105?tab=source"), `Go to line takes a range (${w.location.hash})`);
  go("77"); await wait(20); ok(sel().join() === "ex-L77", "Go to line takes one line");
  go("999x"); await wait(20); ok(sel().join() === "ex-L77" && text("ex-toast").includes("Enter a line"), "a bad entry changes nothing and says why");
  btn(/Copy link/).click(); await wait(20); ok(copied.endsWith("explorer.html#/f/backend/agents/a.py@77?tab=source"), `Copy link (${copied})`);
  const wrap = doc.querySelector(".ex-src__tools input[type=checkbox]"); wrap.checked = true; wrap.dispatchEvent(new w.Event("change"));
  ok(doc.querySelector(".ex-code").classList.contains("is-wrap") && w.localStorage.getItem("minime_ex_wrap") === "1", "wrap toggle works and is remembered");

  await nav("#/f/backend/agents/a.py@120-141?tab=source");
  ok(tabSel() === "ex-tab-source" && sel().length === 22 && sel()[0] === "ex-L120", "a deep link marks its lines");
  await nav("#/f/backend/agents/a.py@10-20");
  ok(tabSel() === "ex-tab-source" && sel().length === 11, "a bare line range opens the Source tab");
  await nav("#/f/backend/agents/a.py::_clean_query@120-141");
  ok(tabSel() === "ex-tab-symbols", "a symbol route still opens the Symbols tab");
  const view = [...doc.querySelectorAll(".ex-sym__view")].find((a) => a.getAttribute("href").includes("_clean_query"));
  ok(view?.getAttribute("href") === "#/f/backend/agents/a.py::_clean_query@120-141?tab=source", "each symbol row links to its source");
  view.click(); await wait(200);
  ok(tabSel() === "ex-tab-source" && sel().length === 22 && text("ex-main").includes("_clean_query"), "View source opens the lines of the symbol and names it");
  await nav("#/f/backend/agents/a.py");
  ok(tabSel() === "ex-tab-explain", "no hint: Explain is still the default");
  ok(doc.querySelector(".ex-blocks a")?.getAttribute("href") === "#/f/backend/agents/a.py@10-20?tab=source", "walkthrough blocks link to their lines in the Source tab");
  await nav("#/f/README.md?tab=source");
  ok(tabSel() === "ex-tab-source" && text("ex-main").includes("not in the embedded source copy"), "a file with no embedded copy says so");
  allErrors.push(...errors);
}

if (which === "nomanifest") {
  const P = await boot({ hash: "#/f/backend/agents/a.py::_clean_query@120-141?tab=source", omit: ["data/src/manifest.json"] });
  const t = P.text("ex-main");
  ok(t.includes("built without an embedded copy") && !P.doc.querySelector(".ex-line"), "no manifest: the tab explains and draws no code");
  ok(t.includes("No link can be made yet"), "and says why there is no GitHub / VS Code button");
  ok(t.includes("_clean_query(x: int) -> str") && t.includes("lines 120–141"), "the census signature and lines stand in for the code");
  await P.nav("#/f/backend/agents/a.py?tab=source"); ok(P.text("ex-main").includes("Module docstring") && P.text("ex-main").includes("Agents."), "without a symbol it shows the module docstring");
  allErrors.push(...P.errors);
}

if (which === "fetchfail") {
  const P = await boot({ hash: "#/f/backend/agents/a.py@10-20?tab=source", omit: ["data/src/backend/agents/a.py.txt"] });
  ok(P.text("ex-main").includes("could not be loaded") && !P.doc.querySelector(".ex-line"), "a failed fetch is explained, not a blank tab");
  ok([...P.doc.querySelectorAll(".ex-src__go a")].some((a) => (a.getAttribute("href") || "").endsWith("#L10-L20")), "GitHub still opens the exact lines");
  allErrors.push(...P.errors);
}

if (which === "drift") {
  const P = await boot({ hash: "#/f/backend/agents/a.py?tab=source", drift: true });
  const warn = [...P.doc.querySelectorAll("#ex-main .ex-callout--warn")].map((e) => e.textContent);
  ok(warn.length === 2 && warn[0].includes("ddddddd") && warn[0].includes("a1389bf"), `copy/census commit mismatch is named (${warn[0]})`);
  ok(warn[1].includes("different version of this file"), "note written for another blob is flagged");
  ok(P.doc.querySelectorAll(".ex-card").length === 4 && P.doc.querySelectorAll(".ex-card.is-stale").length === 4 && P.doc.querySelectorAll(".ex-card .ex-card__chip--stale").length === 4, "P14d: when the note is for another version, every card says the code changed");
  allErrors.push(...P.errors);
}

/* P14d: the walkthrough cards. jsdom has no layout, so the geometry is faked: line N sits at 20 N px, each line is 20 px high, and the code box
   scrolls through a plain property. That is enough to check which block and function the reader is in and where n / p take them. */
const fakeLayout = (P) => {
  const { w, doc } = P;
  const lineNo = (el) => { const m = /^ex-L(\d+)$/.exec(el.id || ""); return m ? Number(m[1]) : 0; };
  Object.defineProperty(w.HTMLElement.prototype, "offsetTop", { configurable: true, get() { return lineNo(this) * 20; } });
  Object.defineProperty(w.HTMLElement.prototype, "offsetHeight", { configurable: true, get() { return lineNo(this) ? 20 : this.classList.contains("ex-card") ? 60 : 0; } });
  const code = doc.querySelector(".ex-code");
  let top = 0;
  Object.defineProperty(code, "scrollTop", { configurable: true, get: () => top, set: (v) => { if (v !== top) setTimeout(() => code.dispatchEvent(new w.Event("scroll")), 0); top = v; } });   // like a browser, a script-made scroll fires a scroll event later
  Object.defineProperty(code, "scrollHeight", { configurable: true, get: () => 3000 });
  Object.defineProperty(code, "clientHeight", { configurable: true, get: () => 400 });
  const scrollTo = async (px) => { top = px; code.dispatchEvent(new w.Event("scroll")); await P.wait(60); };
  return { code, scrollTo, top: () => top };
};

if (which === "walkthrough") {
  const P = await boot({ hash: "#/f/backend/agents/a.py?tab=source" });
  const { doc, w, wait, key, text, errors } = P;
  const L = fakeLayout(P);
  const cards = () => [...doc.querySelectorAll(".ex-card")];
  const titles = () => cards().map((c) => c.querySelector(".ex-card__t").textContent);
  const active = () => cards().filter((c) => c.classList.contains("is-active")).map((c) => c.querySelector(".ex-card__t").textContent);
  const bar = () => doc.querySelector(".ex-src__now");
  const barText = () => bar().textContent.replace(/\s+/g, " ").trim();
  ok(doc.querySelector(".ex-src")?.classList.contains("has-notes"), "a note with blocks turns the margin on");
  ok(titles().join() === "Run,Step,Cleaning,Tail", `4 of the 6 blocks are placed, in line order (${titles()})`);
  ok(cards().map((c) => c.getAttribute("aria-label")).join("|") === "Walkthrough note 1 of 4: Run|Walkthrough note 2 of 4: Step|Walkthrough note 3 of 4: Cleaning|Walkthrough note 4 of 4: Tail", "each card is labelled with its place");
  ok(doc.querySelectorAll(".ex-code .ex-bhead").length === 4, "the same notes are also drawn as headers inside the code, for narrow screens");
  const chips = (i) => [...cards()[i].querySelectorAll(".ex-card__chip")].map((c) => c.textContent);
  ok(chips(0).length === 0 && chips(1).length === 0 && chips(2).join() === "moved" && chips(3).join() === "not checked", `moved and unchecked blocks are marked, the rest are not (${chips(2)} / ${chips(3)})`);
  ok(cards()[2].querySelector(".ex-card__chip--shifted").title.includes("125-146") && cards()[2].querySelector(".ex-card__chip--shifted").title.includes("120-141"), "the mark says where the block was found and where the note had it");
  ok(cards()[2].querySelector("button.ex-link").textContent === "lines 125–146", "a moved block is shown at the lines where it really is");
  ok(doc.querySelector(".ex-code .ex-bhead").nextElementSibling?.id === "ex-L10", "an inline header sits right before the first line of its block");
  const callout = [...doc.querySelectorAll("#ex-main .ex-callout")].map((c) => c.textContent).join(" | ");
  ok(/2 walkthrough notes could not be placed/.test(callout) && callout.includes("Past the end: its lines are past the end of this file") && callout.includes("Broken: its line range is not valid"), `blocks that cannot be placed are listed, not dropped silently (${callout})`);
  ok(text("ex-main").includes("4 walkthrough notes"), "the line under the tools counts the notes");
  ok(!doc.querySelector(".ex-code b") && !/null|undefined/.test(text("ex-main")), "card text is text; no stray null/undefined");

  /* where the reader is */
  ok(!bar().hidden && barText().includes("Top of the file"), `at the top the bar says so (${barText()})`);
  await L.scrollTo(300);                          // first line whose bottom is below 301 px: line 15
  ok(barText().includes("run") && barText().includes("lines 10–20") && barText().includes("Runs the agent.") && barText().includes("walkthrough: Run"), `line 15: function, its range and summary, and the block (${barText()})`);
  ok(active().join() === "Run" && doc.querySelectorAll(".ex-card[aria-current]").length === 1, "exactly one card is current");
  ok(!doc.querySelector(".ex-band").hidden && doc.querySelector(".ex-band").style.top === "200px" && doc.querySelector(".ex-band").style.height === "220px", `a tint covers the block's lines (${doc.querySelector(".ex-band").style.top}, ${doc.querySelector(".ex-band").style.height})`);
  ok(doc.querySelector(".ex-src__now a.ex-link")?.getAttribute("href") === "#/f/backend/agents/a.py::run?tab=symbols", "the bar links to the symbol panel");
  await L.scrollTo(680);                          // line 34: Agent.step, block Step
  ok(barText().includes("Agent.step") && barText().includes("walkthrough: Step") && active().join() === "Step", `line 34 is in the method, not in its class (${barText()})`);
  await L.scrollTo(520);                          // line 27: Agent (class), no block
  ok(barText().includes("Agent") && !barText().includes("Agent.step") && !barText().includes("walkthrough:") && active().length === 0 && doc.querySelector(".ex-band").hidden, `line 27: the class, no block, no tint (${barText()})`);
  await L.scrollTo(100);                          // line 5: no symbol, no block
  ok(barText().includes("Top of the file") === true || barText().includes("Outside any function"), `outside any function (${barText()})`);

  /* n / p and the cards */
  key(L.code, "n"); await wait(30);              // reading line 5 -> the first block that starts after it
  ok(L.top() === 10 * 20 - 2 && active().join() === "Run", `n goes to the next block and puts its first line at the top (${L.top()})`);
  key(L.code, "n"); key(L.code, "n"); await wait(30);
  ok(active().join() === "Cleaning" && L.top() === 125 * 20 - 2 && barText().includes("_clean_query"), `n, n reaches the moved block at its real line, inside _clean_query (${active()}, ${L.top()})`);
  key(L.code, "n"); await wait(30); ok(active().join() === "Tail", "n reaches the last block");
  key(L.code, "n"); await wait(30); ok(active().join() === "Tail" && text("ex-toast").includes("last walkthrough note"), "n at the end stays and says so");
  key(L.code, "p"); await wait(30); ok(active().join() === "Cleaning", "p goes back one");
  await L.scrollTo(1000);                        // reading by hand (line 50, outside every block) clears the jump
  ok(active().length === 0, `scrolling by hand clears the jumped-to block (${active()})`);
  key(L.code, "n"); await wait(30); ok(active().join() === "Cleaning", "n after scrolling by hand goes to the next block below the reading line");
  cards()[1].querySelector("button.ex-link").click(); await wait(40);
  ok(w.location.hash === "#/f/backend/agents/a.py@30-40?tab=source" && doc.querySelectorAll(".ex-line.is-sel").length === 11 && L.top() === 30 * 20 - 2 && active().join() === "Step", `a card selects its lines, rewrites the address and scrolls to them (${w.location.hash})`);
  doc.querySelector(".ex-code .ex-bhead button.ex-link").click(); await wait(40);
  ok(w.location.hash === "#/f/backend/agents/a.py@10-20?tab=source", "the inline header button does the same");

  /* the checkbox */
  const nb = [...doc.querySelectorAll(".ex-src__tools label")].find((l) => /Walkthrough notes/.test(l.textContent))?.querySelector("input");
  ok(!!nb && nb.checked && !nb.closest("label").hidden, "a Walkthrough notes checkbox appears, ticked");
  nb.checked = false; nb.dispatchEvent(new w.Event("change"));
  ok(doc.querySelector(".ex-src").classList.contains("is-notes-off") && w.localStorage.getItem("minime_ex_notes") === "0", "unticking hides the cards and remembers it");
  ok(barText().includes("Agent") || barText().includes("run") || barText().length > 0, "the explain bar does not depend on the cards");
  nb.checked = true; nb.dispatchEvent(new w.Event("change")); ok(!doc.querySelector(".ex-src").classList.contains("is-notes-off") && w.localStorage.getItem("minime_ex_notes") === "1", "ticking brings them back");

  /* the Explain tab */
  await P.nav("#/f/backend/agents/a.py?tab=explain");
  ok(doc.querySelector(".ex-blocks")?.textContent.includes("Cleaning") && doc.querySelector("#ex-main a.mm-btn[href='#/f/backend/agents/a.py?tab=source']")?.textContent === "Read it beside the code", "the Explain tab points to the code with the notes beside it");
  /* a file with census symbols but no note still gets the explain bar and no cards */
  await P.nav("#/f/backend/api/b.py?tab=source");
  ok(doc.querySelectorAll(".ex-card").length === 0 && !doc.querySelector(".ex-src")?.classList.contains("has-notes"), "no note: no cards and no margin");
  allErrors.push(...errors);
}

if (which === "walknarrow") {
  let ro = null;
  globalThis.ResizeObserver = class { constructor(cb) { ro = cb; } observe() {} disconnect() {} };
  const P = await boot({ hash: "#/f/backend/agents/a.py?tab=source" });
  const root = () => P.doc.querySelector(".ex-src");
  ok(typeof ro === "function", "the viewer watches its own width");
  ro([{ contentRect: { width: 500 } }]); ok(root().classList.contains("is-narrow"), "under 760 px the viewer switches to inline headers");
  ro([{ contentRect: { width: 900 } }]); ok(!root().classList.contains("is-narrow"), "and back to the margin when it is wide again");
  ro([{ contentRect: { width: 0 } }]); ok(!root().classList.contains("is-narrow"), "a hidden viewer (width 0) changes nothing");
  allErrors.push(...P.errors);
}

if (which === "walklong") {
  const P = await boot({ hash: "#/f/backend/api/b.py?tab=source", long: true });
  const { doc, wait, nav } = P;
  fakeLayout(P);
  const shown = () => [...doc.querySelectorAll(".ex-card")].filter((c) => !c.hidden).map((c) => c.querySelector(".ex-card__t").textContent);
  ok([...doc.querySelectorAll(".ex-card")].length === 3 && shown().join() === "Top", `cards of lines that are not drawn yet stay hidden (${shown()})`);
  ok(doc.querySelectorAll(".ex-code .ex-bhead").length === 1, "and so do their inline headers");
  doc.querySelector(".ex-src__more").click(); await wait(60);
  ok(shown().join() === "Top,Middle" && doc.querySelectorAll(".ex-code .ex-bhead").length === 2, `Show more lines reveals the next card (${shown()})`);
  doc.querySelector(".ex-src__more").click(); await wait(60);
  ok(shown().join() === "Top,Middle,Late", "and the last one");
  await nav("#/f/backend/api/b.py?tab=source");
  const late = [...doc.querySelectorAll(".ex-card")].find((c) => c.querySelector(".ex-card__t").textContent === "Late");
  late.querySelector("button.ex-link").click(); await wait(60);
  ok(doc.querySelectorAll(".ex-line.is-sel").length === 11 && P.w.location.hash === "#/f/backend/api/b.py@2400-2410?tab=source", "picking a card whose lines are not drawn yet draws them and selects them");
  allErrors.push(...P.errors);
}

if (which === "docs") {
  const P = await boot({ hash: "#/f/README.md", docs: true });
  const { doc, wait, nav, errors } = P;
  const tabs = () => [...doc.querySelectorAll(".ex-tabs [role=tab]")].map((b) => b.textContent.replace(/\s+\(\d+\)/, ""));
  const sel = () => doc.querySelector(".ex-tabs [aria-selected=true]")?.textContent;
  ok(tabs().join() === "Document,Explain,Source,Symbols", `Markdown file: Document tab first (${tabs()})`);
  ok(sel() === "Document", "and it is open by default");
  const md = doc.querySelector(".ex-md");
  ok(!!md && md.querySelector("h2.ex-md__h1")?.textContent.startsWith("Title"), "headings are rendered one level down (the page owns the h1)");
  const hrefs = [...md.querySelectorAll("a")].map((a) => a.getAttribute("href"));
  ok(hrefs.includes("#/f/backend/agents/a.py@3-5?tab=source"), `a repository link with #L3-L5 opens the Source tab (${hrefs.filter((x) => x && x.startsWith("#/"))})`);
  ok(hrefs.includes("#/d/backend"), "a folder link opens the folder");
  ok(!hrefs.some((x) => /javascript/i.test(x || "")), "a javascript: link is not a link");
  ok(md.querySelector(".ex-md__dead")?.textContent === "dead", "a link to a file that is not in the census is plain text");
  ok(md.querySelector('a[href="https://example.org"][rel="noopener noreferrer"]'), "external links open with noopener");
  ok(!md.querySelector("img") && md.querySelector(".ex-md__img"), "images are never loaded");
  ok(md.querySelector("table th[data-align=right]"), "table alignment");
  ok(md.querySelectorAll(".ex-md__toc li").length === 4, "contents list for 4 headings");
  const before = doc.defaultView.location.hash;
  md.querySelector("a[data-anchor=third]").click();
  ok(doc.defaultView.location.hash === before, "an in-page link does not touch the address");
  await wait(200);
  ok(md.querySelector("pre code span[class^=hljs]"), "fenced python is coloured after load");
  md.querySelector(".ex-md__h2 .ex-md__src, .ex-md__h1 .ex-md__src");
  await nav("#/f/README.md?tab=explain"); ok(sel() === "Explain" && !doc.querySelector(".ex-md"), "the Explain tab still works");
  await nav("#/f/README.md@4?tab=source"); ok(sel() === "Source", "a line link opens the Source tab");
  await nav("#/f/conf.json"); await wait(100);
  ok(sel() === "Structure" && doc.querySelectorAll(".ex-j__tree li").length >= 3, "JSON opens the Structure tab with a tree");
  const kb = [...doc.querySelectorAll(".ex-j__k")].map((b) => b.textContent); ok(kb.includes('"name"') && kb.includes('"list"'), `top-level keys are shown (${kb})`);
  doc.querySelectorAll(".ex-j__bar button")[0].click(); ok(doc.querySelectorAll(".ex-j__tree li").length >= 8, "Expand all opens the nested values");
  await nav("#/f/bad.json"); await wait(100);
  ok(/not valid JSON/.test(doc.querySelector(".ex-callout--warn")?.textContent || ""), "invalid JSON says so");
  await nav("#/f/m.sql"); await wait(100);
  ok(sel() === "Outline" && doc.querySelectorAll(".ex-sql__table > tbody > tr").length === 2, "SQL opens the Outline tab with its two statements");
  doc.querySelector('.ex-sql__chips button[data-kind="grant"]').click();
  ok(doc.querySelectorAll(".ex-sql__table > tbody > tr").length === 1, "a kind chip filters the rows");
  await nav("#/f/backend/agents/a.py"); ok(tabs()[0] === "Explain", "a code file gets no extra tab");
  done(errors);
}

done(allErrors);

