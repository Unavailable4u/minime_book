/* MiniMe Atlas 2 - the System page (P09: architecture.html). One ES module, vanilla DOM, no library, no build step.

   Sections, top to bottom:
     status strip      which flows are written, how many are fresh / stale / broken / unverified, which are still missing
     Anatomy           one chat message, step by step (flow `request-path`; the hand-drafted copy until that flow is written)
     one section per view of the architecture model: what you are looking at, legend, the live diagram (assets/js/arch/render.js, embedded and
                       expandable), the numbered steps of the flow with the code each cites, a freshness badge, and the places where the book
                       disagrees with the code
     Modules           the directory table (same data as the Overview)
   The legacy hand-made diagrams are plain links in architecture.html itself, in a collapsed block.

   Nothing on this page is typed twice: sections and steps come from data/arch/ (scripts/arch.py), the prose from content/system/views.json.
   Everything degrades: a flow that is not written yet is a status, a missing file is a note, never a blank page.
   The pure parts are in system-model.js and tested in Node by scripts/test_system.py. The DOM is built with h() only (never markup strings) and nothing is kept in the browser. */

import { h, put } from "./svgview.js";
import { mountArch, LOADER } from "./arch/render.js";
import { linkRow, statusBadge, aiBadge } from "./arch/panel.js";
import { loadLinkOptions } from "./links.js";
import { STATUS_TEXT, CONFIDENCE_TEXT } from "./arch/model.js";
import { directoryRows, fmtN, fmtDate } from "./overview.js";
import * as S from "./system-model.js";

const BASE = typeof document !== "undefined" ? new URL("../../", import.meta.url) : null;
const LOCAL_HINT = "If you opened this file directly, start the local server: python scripts/serve.py";

async function getJSON(rel) {
  const r = await fetch(new URL(rel, BASE));
  if (!r.ok) throw new Error(`${rel}: ${r.status}`);
  return r.json();
}
const soft = (rel) => getJSON(rel).catch(() => null);
const note = (text) => h("p", { class: "sy-note" }, text);

/* ================================================================== small pieces */

const confBadge = (c) => (c ? h("span", { class: `mm-badge ar-conf ar-conf--${c}`, title: CONFIDENCE_TEXT[c] || "" }, `${c} confidence`) : null);

function codeItem(t, linkOpts) {
  return h("li", { class: "sy-code__i" },
    h("code", {}, t.qual ? `${t.path}::${t.qual}` : t.path),
    t.start != null ? h("span", { class: "ar-lines" }, ` lines ${t.start}\u2013${t.end}`) : null,
    t.status && t.status !== "fresh" ? h("span", { class: `ar-status ar-status--${t.status}`, title: STATUS_TEXT[t.status] || "" }, ` ${t.status}`) : null,
    linkRow(t, linkOpts));
}

function gateNote(g) {
  return g ? h("p", { class: "sy-gate" }, h("b", {}, "Approval gate"), ` ${g.tier || ""} \u00b7 decided by ${g.who || "?"}`) : null;
}

/* ================================================================== status strip */

function renderStrip(D) {
  const sum = S.flowSummary(D.index), c = sum.counts;
  const chip = (label, n, cls) => (n ? h("li", { class: `sy-chip sy-chip--${cls}` }, h("b", {}, fmtN(n)), ` ${label}`) : null);
  const miss = sum.missing.length
    ? h("details", { class: "sy-missing" },
      h("summary", {}, `${sum.missing.length} flow${sum.missing.length === 1 ? " is" : "s are"} not written yet`),
      h("ul", {}, sum.missing.map((f) => h("li", {}, h("a", { href: `#${S.viewIdForFlow(D.model, f.id) || f.id}` }, f.title), f.kind ? h("span", { class: "sy-dim" }, ` (${f.kind})`) : null))),
      h("p", { class: "sy-dim" }, "To write one: ", h("code", {}, S.HOW_TO_WRITE), "."))
    : null;
  return h("div", { class: "sy-strip mm-card", role: "group", "aria-label": "How current the diagrams are" },
    h("p", { class: "sy-strip__t" }, "Built from MiniMe ", h("code", {}, S.shortSha(D.model.commit)), ` \u00b7 ${sum.written} of ${sum.total} flows written`),
    h("ul", { class: "sy-chips" }, chip("fresh", c.fresh, "fresh"), chip("stale", c.stale, "stale"), chip("broken", c.broken, "broken"), chip("unverified", c.unverified, "unverified"), chip("not written", c.missing, "missing")),
    miss);
}

function renderJump(sections) {
  return h("nav", { class: "sy-jump", "aria-label": "On this page" }, h("ul", {},
    h("li", {}, h("a", { href: "#anatomy" }, "Anatomy of a request")),
    sections.map((s) => h("li", {}, h("a", { href: `#${s.id}` }, s.title))),
    h("li", {}, h("a", { href: "#modules" }, "Modules")),
    h("li", {}, h("a", { href: "#legacy" }, "Legacy diagrams"))));
}

/* ================================================================== anatomy of a request */

async function renderAnatomy(D) {
  const box = h("div", { class: "sy-anatomy" });
  const flow = await LOADER.flow("request-path").catch(() => null);
  const viewId = ((D.index && D.index.flows && D.index.flows["request-path"] && D.index.flows["request-path"].views) || [])[0] || "task-sequence";
  const shard = await LOADER.view(viewId).catch(() => null);
  const nodes = new Map(((shard && shard.nodes) || []).map((n) => [n.id, n]));
  const A = S.anatomySteps(flow, D.draft, D.model.commit, nodes);
  if (!A.steps.length) { put(box, note(`The request path could not be loaded. ${LOCAL_HINT}`)); return box; }

  const strip = h("ol", { class: "mm-stepper sy-strip__list", "aria-label": "Steps of a request" });
  const panel = h("div", { class: "mm-card sy-step", "aria-live": "polite", id: "sy-step-panel" });
  const buttons = A.steps.map((s, i) => h("button", { type: "button", class: "sy-strip__b", "aria-controls": "sy-step-panel", on: { click: () => pick(i) } }, s.title));
  buttons.forEach((b) => strip.append(h("li", {}, b)));
  let cur = -1;

  function pick(i, focus) {
    if (i < 0 || i >= A.steps.length) return;
    cur = i;
    const s = A.steps[i];
    [...strip.children].forEach((li, j) => { li.classList.toggle("is-done", j < i); if (j === i) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current"); });
    if (focus) buttons[i].focus();
    const [cid, frag] = String(s.chapter || "").split("#");
    const legacy = s.diagram ? S.viewForLegacy(D.model, s.diagram) : null;
    panel.classList.toggle("sy-step--gate", !!s.gate);
    put(panel,
      h("h3", { class: "sy-step__t" }, h("span", { class: "sy-step__n" }, `${i + 1} / ${A.steps.length}`), s.title),
      h("div", { class: "sy-badges" },
        A.source === "flow" ? [statusBadge(s.status), aiBadge(), confBadge(s.confidence)] : h("span", { class: "mm-badge mm-badge--stale", title: "Drafted by hand from the diagrams; not yet traced from the code with evidence." }, "hand-drafted"),
        s.gate ? h("span", { class: "mm-badge mm-badge--stale" }, "approval gate") : null),
      s.actor ? h("p", { class: "sy-dim" }, "Happens in: ", s.actor) : null,
      h("p", { class: "sy-step__what" }, s.what),
      gateNote(s.gate),
      s.code.length ? h("ul", { class: "sy-code" }, s.code.map((t) => codeItem(t, D.linkOpts))) : null,
      s.unknowns && s.unknowns.length ? h("div", { class: "ar-unk" }, h("h4", {}, "Not confirmed"), h("ul", {}, s.unknowns.map((u) => h("li", {}, u)))) : null,
      h("p", { class: "sy-step__more" },
        cid ? h("a", { href: S.chapterHref(s.chapter) }, "Read it in the book") : null,
        legacy ? h("a", { href: `arch-view.html?view=${encodeURIComponent(legacy)}` }, "See the diagram") : null),
      h("div", { class: "sy-step__nav" },
        h("button", { type: "button", class: "mm-btn", disabled: i === 0 ? "" : null, on: { click: () => pick(i - 1, true) } }, "Back"),
        h("button", { type: "button", class: "mm-btn mm-btn--primary", disabled: i === A.steps.length - 1 ? "" : null, on: { click: () => pick(i + 1, true) } }, "Next step")));
  }
  strip.addEventListener("keydown", (e) => {
    const d = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    pick(Math.min(A.steps.length - 1, Math.max(0, cur + d)), true);
  });

  const banner = A.source === "flow"
    ? h("p", { class: "sy-dim" }, statusBadge(A.status), " ", aiBadge(), " ", confBadge(A.confidence), ` traced from the code at ${S.shortSha(A.commit)}. `, A.intro)
    : h("p", { class: "sy-dim" }, h("span", { class: "mm-badge mm-badge--stale" }, "hand-drafted"), " ", A.intro, " ",
      A.needsReview ? (A.reviewNote || "Needs your review.") : "", " The flow ", h("code", {}, "request-path"), " is not written yet; when it is, this stepper reads it instead.");
  put(box, banner, strip, panel);
  pick(0);
  return box;
}

/* ================================================================== one view */

function legendList(legend) {
  return h("ul", { class: "sy-legend", "aria-label": "Legend" }, (legend || []).map((l) => h("li", { class: `sy-legend__i sy-legend__i--${l.id}` }, h("b", {}, l.label), ` ${l.text}`)));
}

function viewSkeleton(sec, D) {
  const written = sec.source === "flow" && sec.status !== "missing";
  const host = h("div", { class: "sy-diagram__host" });
  const frame = h("div", { class: "sy-diagram", "data-expanded": "false" }, host);
  const expand = h("button", { type: "button", class: "mm-btn", "aria-expanded": "false", on: { click: () => {
    const open = frame.dataset.expanded !== "true";
    frame.dataset.expanded = String(open);
    expand.setAttribute("aria-expanded", String(open));
    expand.textContent = open ? "Collapse" : "Expand";
  } } }, "Expand");
  const detail = h("div", { class: "sy-detail" });
  const el = h("section", { class: "sy-view", id: sec.id, "aria-labelledby": `${sec.id}-h`, "data-status": sec.status },
    h("header", { class: "sy-view__h" },
      h("h2", { id: `${sec.id}-h` }, sec.title),
      h("div", { class: "sy-badges", "data-slot": "badges" }, statusBadge(sec.status), written ? aiBadge() : null)),
    sec.what ? h("p", { class: "sy-what" }, sec.what) : null,
    sec.reading ? h("p", { class: "sy-reading" }, h("b", {}, "How to read it: "), sec.reading) : null,
    legendList(D.prose.legend),
    h("div", { class: "sy-tools" }, expand, h("a", { class: "mm-btn", href: `arch-view.html?view=${encodeURIComponent(sec.id)}` }, "Open interactive view")),
    frame, detail,
    sec.chapters.length || sec.pages.length ? h("p", { class: "sy-refs" },
      sec.chapters.length ? [h("b", {}, "In the book: "), sec.chapters.map((c, i) => [i ? " \u00b7 " : "", h("a", { href: S.chapterHref(c.ref) }, c.label || c.ref)])] : null,
      sec.chapters.length && sec.pages.length ? h("br") : null,
      sec.pages.length ? [h("b", {}, "Also: "), sec.pages.map((p, i) => [i ? " \u00b7 " : "", h("a", { href: p.url }, p.label || p.url)])] : null) : null);
  return { el, host, detail, sec };
}

/* Fills in a section once it is near the screen: the diagram first, then the numbered steps read from the same flow. */
async function fillView(v, D) {
  const { sec, host, detail, el } = v;
  mountArch(host, { view: sec.id, embed: true }).catch((err) => { console.warn("[atlas system]", err); put(host, h("p", { class: "ar-fail" }, `The diagram could not be drawn. ${LOCAL_HINT}`)); });
  const shard = await LOADER.view(sec.id).catch(() => null);
  if (!shard) { put(detail, note(`This view could not be loaded: data/arch/views/${sec.id}.json. ${LOCAL_HINT}`)); return; }
  const flow = shard.flow_data || null;
  const nodes = new Map((shard.nodes || []).map((n) => [n.id, n]));
  const status = sec.source === "flow" ? S.flowStatus(flow) : "derived";
  const slot = el.querySelector('[data-slot="badges"]');
  if (flow) put(slot, statusBadge(status), aiBadge(), confBadge(S.flowConfidence(flow)), h("span", { class: "sy-dim" }, `written against ${S.shortSha(flow.commit)}`));
  el.dataset.status = status;

  const kids = [];
  if (!flow && sec.source === "flow") {
    kids.push(h("p", { class: "sy-missingflow" }, h("b", {}, "This flow is not written yet. "), "The diagram shows only what is derived from the code. To write it: ", h("code", {}, S.HOW_TO_WRITE), "."));
  } else if (sec.source !== "flow") {
    const boxes = (shard.nodes || []).filter((n) => n.kind !== "group").length;
    kids.push(h("p", { class: "sy-dim" }, STATUS_TEXT.derived, boxes ? ` ${fmtN(boxes)} boxes, ${fmtN((shard.edges || []).length)} connections.` : ""));
  }
  const conflicts = S.conflictRows(flow);
  if (conflicts.length) {
    kids.push(h("div", { class: "sy-conflicts mm-card" }, h("h3", {}, "Where the book and the code disagree"),
      h("p", { class: "sy-dim" }, "The flow follows the code. These sections of the book probably need correcting."),
      h("ul", {}, conflicts.map((c) => h("li", {}, c.href ? h("a", { href: c.href }, c.chapter) : null, c.href && c.note ? ": " : "", c.note)))));
  }
  const rows = S.stepRows(flow, flow && flow.commit, nodes);
  if (rows.length) {
    const lifecycle = rows[0].type === "transition";
    kids.push(h("h3", { class: "sy-steps__h" }, lifecycle ? "Transitions" : "Steps"),
      h("ol", { class: "sy-steps" }, rows.map((r) => h("li", { class: `sy-steps__i${r.gate ? " sy-steps__i--gate" : ""}`, id: `${sec.id}-${r.id}` },
        h("div", { class: "sy-steps__top" }, h("b", {}, r.title), statusBadge(r.status), confBadge(r.confidence), r.gate ? h("span", { class: "mm-badge mm-badge--stale" }, "approval gate") : null),
        r.actor ? h("p", { class: "sy-dim" }, "Happens in: ", r.actor) : null,
        r.trigger ? h("p", { class: "sy-dim" }, "Trigger: ", r.trigger) : null,
        r.text ? h("p", { class: "sy-steps__what" }, r.text) : null,
        gateNote(r.gate),
        r.evidence.length ? h("ul", { class: "sy-code" }, r.evidence.map((t) => codeItem(t, D.linkOpts))) : null,
        r.unknowns.length ? h("div", { class: "ar-unk" }, h("h4", {}, "Not confirmed"), h("ul", {}, r.unknowns.map((u) => h("li", {}, u)))) : null))));
  }
  put(detail, ...kids);
}

/* ================================================================== modules */

function renderModules(D) {
  const box = h("div", { class: "sy-modules" });
  const c = D.vitals && D.vitals.census;
  if (!D.subsystems || !c || !c.subsystems || !Object.keys(c.subsystems).length) { put(box, note(`The module directory could not be built. ${LOCAL_HINT}`)); return box; }
  const { rows, totals } = directoryRows(D.subsystems, c.subsystems, D.nav, D.book, c.commit);
  const num = (n) => h("td", { class: "is-num" }, fmtN(n));
  const head = h("tr", {}, ["Module", "What it does", "Files", "Code lines", "Functions", "Book", "Key files"].map((t, i) => h("th", { class: i >= 2 && i <= 4 ? "is-num" : "", scope: "col" }, t)));
  const body = rows.map((r) => h("tr", { id: `mod-${r.id}` },
    h("th", { scope: "row" }, h("b", {}, r.name), r.folder ? h("span", { class: "sy-dir__f" }, h("code", {}, r.folder)) : null),
    h("td", {}, r.what), num(r.files), num(r.code), num(r.functions),
    h("td", {}, r.chapter ? h("a", { href: r.chapter.url, title: r.chapter.title }, r.chapter.label) : "\u2013"),
    h("td", {}, r.keyFiles.length ? r.keyFiles.map((k) => h("a", { class: "sy-dir__k", href: k.url, target: "_blank", rel: "noopener", title: k.title }, h("code", {}, k.text))) : "\u2013")));
  const foot = h("tr", {}, h("th", { scope: "row", colspan: 2 }, "All of the repository"), num(totals.files), num(totals.code), num(totals.functions), h("td", { colspan: 2 }));
  put(box, h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table sy-dir" },
    h("caption", { class: "sy-dim" }, `Counted from MiniMe ${S.shortSha(c.commit)}, ${fmtDate(c.generated)}. Code lines exclude comments and blanks.`),
    h("thead", {}, head), h("tbody", {}, body), h("tfoot", {}, foot))));
  return box;
}

/* ================================================================== page */

function lazy(items, fn) {
  if (typeof IntersectionObserver === "undefined") { items.forEach((v) => fn(v)); return; }
  const seen = new Set();
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const v = items.find((x) => x.el === e.target);
      if (v && !seen.has(v)) { seen.add(v); io.unobserve(e.target); fn(v); }
    }
  }, { rootMargin: "400px 0px" });
  items.forEach((v) => io.observe(v.el));
}

export async function boot(root) {
  const [model, index, prose, draft, subsystems, vitals, nav, book, linkOpts] = await Promise.all([
    LOADER.model(), LOADER.index(), getJSON("content/system/views.json").catch(() => null), soft("content/system/request-path.json"),
    soft("content/subsystems.json"), soft("data/index/vitals.json"), soft("content/nav.json"), soft("data/index/book.json"), loadLinkOptions().catch(() => ({})),
  ]);
  if (!model) { put(root, note(`The architecture model could not be loaded: data/arch/model.json. ${LOCAL_HINT}`)); return; }
  const D = { model, index, prose: prose || { legend: [], views: {} }, draft, subsystems, vitals, nav, book, linkOpts };
  const sections = S.viewSections(model, D.prose);
  const views = sections.map((s) => viewSkeleton(s, D));

  put(root,
    h("p", { class: "sy-intro" }, D.prose.intro || ""),
    renderStrip(D), renderJump(sections),
    h("section", { class: "sy-section", id: "anatomy", "aria-labelledby": "anatomy-h" }, h("h2", { id: "anatomy-h" }, "Anatomy of a request"), h("div", { "data-slot": "anatomy" }, note("Loading\u2026"))),
    views.map((v) => v.el),
    h("section", { class: "sy-section", id: "modules", "aria-labelledby": "modules-h" }, h("h2", { id: "modules-h" }, "Modules"),
      h("p", { class: "sy-dim" }, "Every part of the repository, what it does, where the book describes it and the files to open first."), h("div", { "data-slot": "modules" }, note("Loading\u2026"))));

  root.querySelector('[data-slot="anatomy"]').replaceChildren(await renderAnatomy(D).catch((err) => { console.warn("[atlas system]", err); return note(`The request path could not be drawn. ${LOCAL_HINT}`); }));
  root.querySelector('[data-slot="modules"]').replaceChildren(renderModules(D));
  lazy(views, (v) => fillView(v, D).catch((err) => console.warn("[atlas system]", err)));
  if (location.hash) { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
}

if (typeof document !== "undefined") {
  const start = () => { const root = document.querySelector("[data-system-page]"); if (root && !root.dataset.ready) { root.dataset.ready = "1"; boot(root).catch((err) => { console.warn("[atlas system]", err); put(root, note(`The System page could not be drawn. ${LOCAL_HINT}`)); }); } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true }); else start();
}
