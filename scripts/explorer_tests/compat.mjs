// compat.js (P19): where the old explore.html / code.html / functions.html addresses go. Pure: no DOM.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { explorerTarget } from "../../assets/js/compat.js";
import { parseRoute, hashQuery } from "../../assets/js/explorer/router.js";
let n = 0;
const t = (name, f) => { try { f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };

t("no hash: every old page lands on the Explorer start page", () => { for (const p of ["explore", "code", "functions"]) { assert.equal(explorerTarget(p, ""), "explorer.html#/"); assert.equal(explorerTarget(p, "#"), "explorer.html#/"); } });
t("a path written with encodeURIComponent (overview, graph viewer) opens that path", () => {
  assert.equal(explorerTarget("explore", `#${encodeURIComponent("backend/agents/a.py")}`), "explorer.html#/backend/agents/a.py");
  assert.equal(explorerTarget("explore", "#backend/agents/a.py"), "explorer.html#/backend/agents/a.py");      // health.html wrote it unencoded
});
t("spaces and odd characters in a path stay encoded, segment by segment", () => {
  assert.equal(explorerTarget("explore", `#${encodeURIComponent("a b/c#d.py")}`), "explorer.html#/a%20b/c%23d.py");
});
t("a bare file name and a folder with a trailing slash are paths too", () => {
  assert.equal(explorerTarget("explore", "#README.md"), "explorer.html#/README.md");
  assert.equal(explorerTarget("explore", "#backend%2Feo%2F"), "explorer.html#/backend/eo");
  assert.equal(explorerTarget("explore", "#./a/b.py"), "explorer.html#/a/b.py");
});
t("words are a search: they prefill the file filter", () => {
  assert.equal(explorerTarget("explore", "#orchestrator"), "explorer.html#/?q=orchestrator");
  assert.equal(explorerTarget("explore", "#two%20words"), "explorer.html#/?q=two%20words");
  assert.equal(explorerTarget("explore", "#_clean_query"), "explorer.html#/?q=_clean_query");
});
t("an Explorer route that reached an old page is passed on unchanged", () => {
  assert.equal(explorerTarget("code", "#/f/backend/a.py::run@3-9?tab=source"), "explorer.html#/f/backend/a.py::run@3-9?tab=source");
  assert.equal(explorerTarget("functions", "#/d/backend?tab=symbols"), "explorer.html#/d/backend?tab=symbols");
});
t("bad input never throws and never leaves the Explorer", () => {
  for (const h of ["#%E0%A4%A", "#%", "#///", "#%2F", "# ", "#a%2", `#${"x".repeat(5000)}`]) assert.ok(explorerTarget("explore", h).startsWith("explorer.html#/"), h);
  assert.equal(explorerTarget("explore", "#///"), "explorer.html#/");
});
t("the Explorer reads what the redirect wrote: a path comes back as the same path, a search as the same words", () => {
  const r = parseRoute(explorerTarget("explore", "#a%20b%2Fc.py").replace(/^explorer\.html/, ""));
  assert.deepEqual([r.view, r.path], ["auto", "a b/c.py"]);
  const s = explorerTarget("explore", "#two%20words").replace(/^explorer\.html/, "");
  assert.equal(parseRoute(s).view, "home");
  assert.equal(hashQuery(s), "two words");
});
t("hashQuery: only q is read, plus signs are spaces, bad escapes give nothing", () => {
  assert.equal(hashQuery("#/"), "");
  assert.equal(hashQuery("#/?q="), "");
  assert.equal(hashQuery("#/?q=a%2Fb"), "a/b");
  assert.equal(hashQuery("#/?tab=symbols&q=x+y"), "x y");
  assert.equal(hashQuery("#/?q=%E0%A4%A"), "");
  assert.equal(hashQuery(undefined), "");
});
t("every file of the census survives the round trip through the old address form", () => {
  const paths = JSON.parse(readFileSync(fileURLToPath(new URL("../../data/index/paths.json", import.meta.url)), "utf8")).paths;
  assert.ok(paths.length > 500, "paths.json should list the whole census");
  const bad = [];
  for (const raw of paths) {
    const p = typeof raw === "string" ? raw : raw.path || raw[0];
    const r = parseRoute(explorerTarget("explore", `#${encodeURIComponent(p)}`).replace(/^explorer\.html/, ""));
    if (r.path !== p) bad.push(`${p} -> ${r.path} (${r.view})`);
  }
  assert.deepEqual(bad.slice(0, 5), [], `${bad.length} paths did not round trip`);
});
console.log(`${n} passed`);
