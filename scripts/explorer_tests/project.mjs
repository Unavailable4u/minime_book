// decisions.html (P21) in jsdom: the one-time move of the old Golden Rule keys (G1 -> G-01), locks, filter, #G7 -> #G-07.
// Skips (exit 77) when jsdom is not installed:  npm install --prefix scripts/explorer_tests jsdom
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { jsdomOrSkip } from "./fixture.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SRC = readFileSync(join(ROOT, "decisions.html"), "utf8")
  .replace(/<script type="module"[^>]*><\/script>/g, "")
  .replace(/<script src="[^"]*"><\/script>/g, "");

const JSDOM = await jsdomOrSkip();
if (!JSDOM) process.exit(77);

let failed = 0;
const ok = (cond, msg) => { if (!cond) { failed++; console.log("FAIL:", msg); } else console.log("ok:", msg); };

function load({ store = {}, hash = "", throwing = false } = {}) {
  const dom = new JSDOM(SRC, {
    runScripts: "dangerously",
    url: `http://localhost/decisions.html${hash}`,
    beforeParse(w) {
      w.Element.prototype.scrollIntoView = () => {};
      if (throwing) {
        Object.defineProperty(w, "localStorage", { get() { throw new Error("blocked"); } });
      } else {
        for (const [k, v] of Object.entries(store)) w.localStorage.setItem(k, v);
      }
    },
  });
  return dom.window;
}
const text = (w, id) => w.document.getElementById(id).textContent;
const stored = (w, k) => w.localStorage.getItem(k);

{ // old keys move to the stable ids, once
  const w = load({ store: { "atlas:dec:G1": "1", "atlas:dec:G2": "0", "atlas:dec:MK-D1": "1" } });
  ok(stored(w, "atlas:dec:G-01") === "1" && stored(w, "atlas:dec:G1") === null, "G1 lock moved to G-01, old key removed");
  ok(stored(w, "atlas:dec:G-02") === "0" && stored(w, "atlas:dec:G2") === null, "an explicit 'not locked' moves too");
  ok(stored(w, "atlas:dec:MK-D1") === "1", "other decisions keep their keys");
  ok(text(w, "pg") === "2 of 86 decisions locked", `progress text is "${text(w, "pg")}"`);
  ok(w.document.getElementById("G-01").classList.contains("is-locked") && w.document.getElementById("c-G-01").checked, "G-01 is drawn locked");
  ok(w.document.querySelector("#src-rulebook [data-locked]").textContent === "1/15 locked", "group count says 1/15");
  ok(w.document.getElementById("pb").style.width.startsWith("2.3"), `bar width ${w.document.getElementById("pb").style.width}`);
}
{ // a lock already on the new key is not overwritten by the old key
  const w = load({ store: { "atlas:dec:G3": "1", "atlas:dec:G-03": "0" } });
  ok(stored(w, "atlas:dec:G-03") === "0" && stored(w, "atlas:dec:G3") === null, "the new key wins over the old one");
}
{ // ticking a box is saved; ticking again clears it
  const w = load();
  const box = w.document.getElementById("c-G-05");
  box.checked = true; box.dispatchEvent(new w.Event("change", { bubbles: true }));
  ok(stored(w, "atlas:dec:G-05") === "1" && text(w, "pg") === "1 of 86 decisions locked", "tick is saved and counted");
  box.checked = false; box.dispatchEvent(new w.Event("change", { bubbles: true }));
  ok(stored(w, "atlas:dec:G-05") === "0" && text(w, "pg") === "0 of 86 decisions locked", "untick is saved and counted");
}
{ // filter hides cards and empty groups, and shows them again
  const w = load();
  const q = w.document.getElementById("fq");
  q.value = "latest"; q.dispatchEvent(new w.Event("input", { bubbles: true }));
  const shown = [...w.document.querySelectorAll(".dec")].filter((c) => !c.hidden).map((c) => c.id);
  ok(shown.includes("G-03") && shown.length < 5, `"latest" shows ${shown.join(", ")}`);
  ok(w.document.getElementById("src-technical-roadmap").hidden === true, "a group with no match is hidden");
  q.value = ""; q.dispatchEvent(new w.Event("input", { bubbles: true }));
  ok([...w.document.querySelectorAll(".dec")].every((c) => !c.hidden), "empty filter shows everything");
}
{ // the old id in the address is sent to the new one
  const w = load({ hash: "#G7" });
  ok(w.location.hash === "#G-07", `#G7 became ${w.location.hash}`);
  ok(w.document.getElementById("G-07").classList.contains("is-target"), "the card is marked as the target");
}
{ // a target hidden by an old filter is revealed
  const w = load({ hash: "#G-02" });
  ok(w.document.getElementById("G-02").classList.contains("is-target") && !w.document.getElementById("G-02").hidden, "#G-02 opens its card");
}
{ // storage that throws (private mode, blocked cookies) must not break the page
  let w, err = null;
  try { w = load({ throwing: true }); } catch (e) { err = e; }
  ok(!err && w && text(w, "pg") === "0 of 86 decisions locked", "page still draws when localStorage throws");
}
process.exit(failed ? 1 : 0);
