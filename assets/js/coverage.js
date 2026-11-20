/* MiniMe Atlas 2 - the Coverage & freshness page (P22). Loaded by coverage.html, a shell: this module draws the page from
     data/index/status.json     written by scripts/build_status.py (notes coverage, flows, stale files, a preview of the next files)
     content/config.json        "freshness".warnDays: when a source turns amber
     content/copilot-prompts.json   prompts A to D, the same text as UPDATING.md (scripts/test_status.py keeps them equal)
     the audit marks            this browser's own, read with audit.js (the Explorer's store). Shared (live-sync) marks are not read here:
                                the Explorer's Audit page shows those.
   The logic is in coverage-core.js (Node tests it). All text goes in through h(), never as HTML. */
import { h, clear, num, day } from "./explorer/dom.js";
import { buildRoute } from "./explorer/router.js";
import { createAudit } from "./explorer/audit.js";
import { loadCore, loadRecords } from "./explorer/model.js";
import * as C from "./coverage-core.js";
import { getJSON, empty, badge, copyButton } from "./codeui.js";

const $ = (id) => document.getElementById(id);
const code = (t) => h("code", null, t);
const dirHref = (p) => `explorer.html${buildRoute({ view: "dir", path: p })}`;
const fileHref = (p) => `explorer.html${buildRoute({ view: "file", path: p, tab: "" })}`;
const pctText = (n, d) => { const p = C.pct(n, d); return p == null ? "–" : `${p} %`; };

function bar(ratio, label) {
  const w = ratio == null ? 0 : Math.max(0, Math.min(100, Math.round(ratio * 100)));
  return h("span", { class: "cv-bar", role: "img", "aria-label": label, title: label }, h("i", { style: `width:${w}%` }));
}

function sec(id, title, lead, ...kids) {
  return h("section", { class: "cv-sec", id }, h("h2", null, title), lead ? h("p", { class: "cp-sub" }, lead) : null, kids);
}

/* ------------------------------------------------------------------ freshness strip */
function freshness(status, cfg) {
  const chip = C.chipModel(status, cfg);
  const tiles = chip.items.map((i) => h("div", { class: `mm-card cv-tile cv-tile--${i.tone}` },
    h("span", { class: "cv-tile__k" }, i.label),
    h("span", { class: "cv-tile__v" }, i.date ? C.dayWord(i.age) : "none yet"),
    h("span", { class: "cv-tile__s" }, i.date ? `${day(i.date)}${i.commit ? ` · ${i.commit.slice(0, 7)}` : ""}` : "nothing to judge"),
    i.id === "notes" && i.percent != null ? h("span", { class: "cv-tile__s" }, `${i.percent} % of the files that want a note have one`) : null,
    i.tone === "stale" ? badge("stale", `older than ${i.limit} days`, "Amber threshold: content/config.json, freshness.warnDays") : (i.tone === "ok" ? badge("ok", "in date") : null)));
  return sec("freshness", "How fresh is the Atlas?", "Everything on this site is built from one MiniMe commit. These are the ages of the four things built from it; the chip in the top bar turns amber when one is too old or when they come from different commits.",
    h("div", { class: "cv-tiles" }, tiles),
    chip.state === "stale"
      ? h("ul", { class: "cv-why" }, chip.reasons.map((r) => h("li", null, r)))
      : h("p", { class: "cp-dim" }, "Census, graph and notes come from the same commit and are inside their limits."));
}

/* ------------------------------------------------------------------ notes coverage by tier */
const TIER_NAME = { 1: "Full note, with walkthrough", 2: "File note and its main symbols", 3: "File note and public symbols", 4: "One line (optional)" };
function tiers(status) {
  const t = (status.notes && status.notes.tiers) || {};
  const tot = (status.notes && status.notes.totals) || {};
  const rows = ["1", "2", "3"].filter((k) => t[k]).map((k) => {
    const r = t[k];
    return h("tr", null,
      h("th", { scope: "row" }, `T${k}`, " ", h("span", { class: "cp-dim" }, TIER_NAME[k])),
      h("td", { class: "cv-n" }, num(r.files)), h("td", { class: "cv-n" }, num(r.noted)), h("td", { class: "cv-n" }, num(r.fresh)),
      h("td", { class: "cv-n" }, r.stale ? badge("stale", num(r.stale)) : "0"), h("td", { class: "cv-n" }, num(r.missing)),
      h("td", null, bar(r.files ? r.noted / r.files : null, `${pctText(r.noted, r.files)} of the T${k} files have a note`), " ", pctText(r.noted, r.files)),
      h("td", { class: "cv-n" }, `${num(r.symbols_covered)} / ${num(r.symbols_wanted)}`));
  });
  if (!rows.length) return sec("tiers", "Notes by tier", null, empty("data/index/notes.json has no tiers yet. Run python scripts/notes.py ingest."));
  rows.push(h("tr", { class: "cv-total" }, h("th", { scope: "row" }, "T1–T3"), h("td", { class: "cv-n" }, num(tot.files)), h("td", { class: "cv-n" }, num(tot.noted)), h("td", { class: "cv-n" }, num(tot.fresh)),
    h("td", { class: "cv-n" }, num(tot.stale)), h("td", { class: "cv-n" }, num(tot.missing)),
    h("td", null, bar(tot.files ? tot.noted / tot.files : null, `${pctText(tot.noted, tot.files)} of all files that want a note`), " ", pctText(tot.noted, tot.files)),
    h("td", { class: "cv-n" }, `${num(tot.symbols_covered)} / ${num(tot.symbols_wanted)}`)));
  const cols = ["Tier", "Files", "Noted", "Fresh", "Stale", "Missing", "Coverage", "Symbols covered / wanted"];
  return sec("tiers", "Notes by tier", "A note is AI-written and labelled so. Tier 1 files get the full treatment, tier 3 only their public symbols; tests and fixtures (tier 4) are not counted.",
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact cv-table" },
      h("thead", null, h("tr", null, cols.map((c) => h("th", { scope: "col" }, c)))), h("tbody", null, rows))));
}

/* ------------------------------------------------------------------ folder heatmap */
function heatmap(status, audit, state) {
  const host = h("div", { class: "cv-heatwrap" });
  const draw = () => {
    clear(host);
    const roll = C.auditRollup(audit.entries());
    const rows = C.folderRows(status.folders, state.open);
    if (!rows.length) { host.append(empty("No folders in status.json.")); return; }
    const head = h("tr", null, [["Folder", "col"], ["Files", "col"], ["Notes", "col"], ["Audit", "col"], ["Symbols", "col"]].map(([c, s]) => h("th", { scope: s }, c)));
    const body = rows.map((r) => {
      const a = roll[r.path];
      const aRatio = r.symbols ? (a ? a.reviewed / r.symbols : 0) : null;
      const nLvl = C.heatLevel(r.notesRatio), aLvl = C.heatLevel(aRatio);
      const toggle = r.hasKids
        ? h("button", { type: "button", class: "cv-tog", "aria-expanded": String(state.open.has(r.path)), "aria-label": `${state.open.has(r.path) ? "Collapse" : "Expand"} ${r.path}`,
            onclick: () => { if (state.open.has(r.path)) state.open.delete(r.path); else state.open.add(r.path); draw(); } }, state.open.has(r.path) ? "▾" : "▸")
        : h("span", { class: "cv-tog cv-tog--none", "aria-hidden": "true" }, "·");
      const noteText = r.elig ? `${r.noted} of ${r.elig} files have a note${r.stale ? `, ${r.stale} stale` : ""}` : "no file here wants a note";
      const auditText = a ? `${a.reviewed} of ${r.symbols} symbols reviewed${a.rereview ? `, ${a.rereview} need re-review` : ""}${a.concern ? `, ${a.concern} concern${a.concern === 1 ? "" : "s"}` : ""}` : `0 of ${r.symbols} symbols reviewed`;
      return h("tr", null,
        h("th", { scope: "row", class: "cv-name", style: `padding-left:calc(var(--space-3) + var(--space-4) * ${r.depth})` }, toggle, h("a", { href: dirHref(r.path), title: r.path }, r.name)),
        h("td", { class: "cv-n" }, num(r.files)),
        h("td", null, h("span", { class: `cv-heat cv-heat--${nLvl}`, title: noteText }, h("span", { class: "cv-heat__t" }, r.notesRatio == null ? "–" : pctText(r.noted, r.elig)), r.stale ? h("span", { class: "cv-flag", title: `${r.stale} stale`, "aria-label": `${r.stale} stale` }, "◆") : null)),
        h("td", null, h("span", { class: `cv-heat cv-heat--${aLvl}`, title: auditText }, h("span", { class: "cv-heat__t" }, aRatio == null ? "–" : pctText(a ? a.reviewed : 0, r.symbols)),
          a && a.concern ? h("span", { class: "cv-flag cv-flag--concern", title: `${a.concern} concern(s)`, "aria-label": `${a.concern} concerns` }, "!") : null,
          a && a.rereview ? h("span", { class: "cv-flag", title: `${a.rereview} need re-review`, "aria-label": `${a.rereview} need re-review` }, "↻") : null)),
        h("td", { class: "cv-n" }, num(r.symbols)));
    });
    host.append(h("div", { class: "mm-tablewrap cv-heatscroll" }, h("table", { class: "mm-table is-compact cv-table cv-heattable" },
      h("caption", { class: "cv-sr" }, "Folders with notes coverage and audit coverage"), h("thead", null, head), h("tbody", null, body))));
    const tot = roll[""];
    host.append(h("p", { class: "cp-dim cv-foot" }, tot
      ? `${num(tot.reviewed)} of ${num(status.totals.symbols)} symbols reviewed in this browser (${C.pct(tot.reviewed, status.totals.symbols)} %), ${num(tot.concern)} concern${tot.concern === 1 ? "" : "s"}, ${num(tot.rereview)} needing re-review${tot.unchecked ? `; ${num(tot.unchecked)} reviews have not been compared with the current code yet` : ""}.`
      : "You have not marked any symbol yet. Open a function in the Explorer and press r (reviewed), c (concern) or n (to do)."));
  };
  draw();
  const off = audit.on(draw);
  return { el: host, redraw: draw, off };
}

function legend() {
  return h("ul", { class: "cv-legend", "aria-label": "Legend" },
    [0, 1, 2, 3, 4].map((l) => h("li", null, h("span", { class: `cv-heat cv-heat--${l}`, "aria-hidden": "true" }, " "), l === 0 ? "none" : l === 4 ? "all" : `${l * 25} %`)),
    h("li", null, h("span", { class: "cv-flag", "aria-hidden": "true" }, "◆"), "stale note"),
    h("li", null, h("span", { class: "cv-flag", "aria-hidden": "true" }, "↻"), "needs re-review"),
    h("li", null, h("span", { class: "cv-flag cv-flag--concern", "aria-hidden": "true" }, "!"), "concern"));
}

/* ------------------------------------------------------------------ architecture flows */
function flows(status) {
  const fl = status.flows || {};
  const order = (status.flow_order && status.flow_order.length ? status.flow_order : Object.keys(fl)).filter((id) => fl[id]);
  if (!order.length) return sec("flows", "Architecture flows", null, empty("No flows are registered (content/arch-flows.json)."));
  const kind = { fresh: "ok", stale: "stale", broken: "stale", unverified: "stale", missing: "stale" };
  const rows = order.map((id) => {
    const f = fl[id];
    const c = f.counts || {};
    const steps = f.status === "missing" ? "not written yet" : ["fresh", "stale", "broken", "unverified"].filter((k) => c[k]).map((k) => `${c[k]} ${k}`).join(", ") || `${f.items} step(s)`;
    return h("tr", null, h("th", { scope: "row" }, f.title, " ", h("span", { class: "cp-dim" }, code(id))),
      h("td", null, badge(kind[f.status] || "stale", f.status, f.status === "missing" ? "Prompt C writes it" : "Prompt D refreshes the steps that went stale")),
      h("td", null, steps), h("td", null, (f.views || []).map((v, i) => [i ? ", " : "", h("a", { href: `arch-view.html?view=${encodeURIComponent(v)}` }, v)])),
      h("td", null, f.incomplete && f.incomplete.length ? `${f.incomplete.length} derived stage(s) without a step` : ""));
  });
  const ft = status.flow_totals || {};
  return sec("flows", "Architecture flows",
    `Structure is derived from the code and never goes stale. Flows are written by Copilot, one file per flow, and every step cites the code it is about. ${ft.written != null ? `${ft.written} of ${ft.flows} are written.` : ""}`,
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact cv-table" },
      h("thead", null, h("tr", null, ["Flow", "Status", "Steps", "Views", "Notes"].map((c) => h("th", { scope: "col" }, c)))), h("tbody", null, rows))));
}

/* ------------------------------------------------------------------ stale list */
function symbolList(list) {
  const shown = list.slice(0, 6).flatMap((q, i) => [i ? ", " : "", code(q)]);
  return list.length > 6 ? [...shown, ` and ${list.length - 6} more`] : shown;
}

function stale(status) {
  const list = status.stale || [];
  if (!list.length) return sec("stale", "Stale notes", "A note is stale when the code it describes has changed since it was written.", h("p", { class: "cv-ok" }, badge("ok", "None"), " Every note matches the code at the census commit."));
  const rows = list.map((r) => h("tr", null,
    h("td", null, h("a", { href: fileHref(r.path) }, code(r.path))), h("td", { class: "cv-n" }, `T${r.tier}`),
    h("td", null, badge("stale", r.status === "stale" ? "file changed" : "symbols changed")),
    h("td", null, symbolList(r.bad || [])),
    h("td", { class: "cp-dim" }, day(r.written))));
  return sec("stale", `Stale notes (${list.length})`, "Run prompt B (below) to refresh only these; unchanged symbols keep their text.",
    h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact cv-table" },
      h("thead", null, h("tr", null, ["File", "Tier", "State", "Symbols", "Written"].map((c) => h("th", { scope: "col" }, c)))), h("tbody", null, rows))));
}

/* ------------------------------------------------------------------ annotate next */
function promptBox(title, hint, p, copyLabel) {
  return h("div", { class: "cv-prompt" },
    h("div", { class: "cv-prompt__h" }, h("strong", null, title), h("span", { class: "cp-dim" }, hint), copyButton(p.prompt, copyLabel)),
    h("pre", { class: "cv-pre", tabindex: "0" }, h("code", null, p.prompt)));
}

function annotateNext(status, prompts) {
  const nb = C.notesBatch(status.next, prompts, { limit: 20 });
  const fb = C.flowBatch(status.flows, status.flow_order, prompts);
  const kids = [];
  if (!nb) kids.push(h("p", { class: "cv-ok" }, badge("ok", "Done"), " Every file that wants a note has a fresh one."));
  else {
    const n = status.next || {};
    kids.push(h("p", null, `${num(n.needing)} files still need a note (${["1", "2", "3"].map((t) => `${num((n.per_tier || {})[t] || 0)} in tier ${t}`).join(", ")}). The next ${nb.count} are in tier ${nb.tier}, most-connected first:`));
    kids.push(h("ol", { class: "cv-next" }, nb.files.map((f) => h("li", null,
      h("a", { href: fileHref(f.path) }, code(f.path)), " ", h("span", { class: "cp-dim" }, `T${f.tier} · ${f.reason} · ${num(f.symbols)} symbols · ${num(f.links)} links · ${num(f.commits)} commits`)))));
    kids.push(h("p", { class: "cp-dim" }, status.next.basis));
    kids.push(h("p", null, h("span", { class: "cv-step" }, "1"), " In minime_book: ", copyButton(nb.command, "Copy command"), " ", code(nb.command)));
    kids.push(h("p", null, h("span", { class: "cv-step" }, "2"), ` In MiniMe, with Copilot in Agent mode, paste prompt ${nb.kind}:`));
    kids.push(promptBox(`Prompt ${nb.kind} with the batch preview`, `${nb.count} files`, nb, "Copy prompt"));
    kids.push(h("p", null, h("span", { class: "cv-step" }, "3"), " Back in minime_book: ", code("python scripts/notes.py ingest --minime ../MiniMe"), ", then ", code("python scripts/update_all.py"), "."));
  }
  if (fb) {
    kids.push(h("h3", null, fb.kind === "D" ? "Flows with stale steps" : "Flows not written yet"));
    kids.push(h("p", null, fb.kind === "D" ? `Refresh: ${fb.refresh.join(", ")}.` : `${fb.missing.length} flows have no file yet; prompt C writes two at a time, starting with ${fb.flows.join(" and ")}.`));
    kids.push(h("p", null, h("span", { class: "cv-step" }, "1"), " In minime_book: ", copyButton(fb.command, "Copy command"), " ", code(fb.command)));
    kids.push(h("p", null, h("span", { class: "cv-step" }, "2"), ` In MiniMe, paste prompt ${fb.kind}:`));
    kids.push(promptBox(`Prompt ${fb.kind}`, fb.flows.join(", "), fb, "Copy prompt"));
    if (fb.kind === "D" && fb.missing.length) kids.push(h("p", { class: "cp-dim" }, `${fb.missing.length} more flow(s) are not written yet: run prompt C after this one.`));
  }
  return sec("next", "Annotate next", "Where Copilot's time is best spent: the next files by tier, graph connections and churn, and the architecture flows that need work. Copy a prompt, run it, ingest, and these numbers move.", kids);
}

/* ------------------------------------------------------------------ check marks against the census */
async function recheck(audit, btn, note) {
  btn.disabled = true;
  note.textContent = "Comparing your marks with the census…";
  try {
    const core = await loadCore();
    const paths = [...new Set(audit.entries().map((e) => e.mark.path))];
    for (const p of paths) if (!core.tree.files.has(p)) audit.observe(p, []);
    const files = paths.map((p) => core.tree.files.get(p)).filter(Boolean);
    const { recs, more } = await loadRecords(core, files, 200);
    recs.forEach((r) => audit.observeRecord(r));
    note.textContent = `Checked ${num(paths.length)} marked file${paths.length === 1 ? "" : "s"}${more ? `; ${more} data shard(s) were left out` : ""}.`;
  } catch (e) {
    note.textContent = `Could not check: ${e.message}`;
  } finally { btn.disabled = false; }
}

/* ------------------------------------------------------------------ boot */
export async function initCoverage() {
  const app = $("cv-app");
  if (!app) return;
  let status, cfg = {}, prompts = {};
  try {
    [status, cfg, prompts] = await Promise.all([getJSON("data/index/status.json"), getJSON("content/config.json").catch(() => ({})), getJSON("content/copilot-prompts.json").catch(() => ({}))]);
  } catch (e) {
    clear(app).append(empty(`data/index/status.json could not be loaded (${e.message}). Run python scripts/build_status.py, and open this page through python scripts/serve.py.`));
    return;
  }
  let storage = null;
  try { storage = window.localStorage; } catch { storage = null; }
  const audit = createAudit({ storage });
  const state = { open: new Set() };
  const heat = heatmap(status, audit, state);
  const checkNote = h("span", { class: "cp-dim", role: "status" });
  const checkBtn = h("button", { type: "button", class: "mm-btn", onclick: () => recheck(audit, checkBtn, checkNote) }, "Check my reviews against the code");
  const expandAll = h("button", { type: "button", class: "mm-btn", onclick: () => { Object.keys(status.folders).forEach((p) => state.open.add(p)); heat.redraw(); } }, "Expand all");
  const collapseAll = h("button", { type: "button", class: "mm-btn", onclick: () => { state.open.clear(); heat.redraw(); } }, "Collapse all");

  clear(app).append(
    h("nav", { class: "cv-jump", "aria-label": "On this page" }, [["freshness", "Freshness"], ["tiers", "Tiers"], ["heat", "Folders"], ["flows", "Flows"], ["stale", "Stale"], ["next", "Annotate next"]].map(([id, t]) => h("a", { href: `#${id}` }, t))),
    freshness(status, cfg), tiers(status),
    sec("heat", "Where the coverage is", "Each folder shows how many of its files have a note, and how many of its symbols you have reviewed in this browser. Click a folder name to open it in the Explorer.",
      h("div", { class: "cv-tools" }, expandAll, collapseAll, checkBtn, checkNote), legend(), heat.el),
    flows(status), stale(status), annotateNext(status, prompts));
  if (location.hash.length > 1) { const t = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (t) t.scrollIntoView(); }
  window.addEventListener("pagehide", () => heat.off());
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => initCoverage(), { once: true });
  else initCoverage();
}