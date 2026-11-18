/* MiniMe Atlas 2 - Explorer audit mode, the parts that draw (P16). The rules and the store are in audit.js.

     auditMark(status)       one glyph: ○ to do, ✓ reviewed, ↻ needs re-review, ! concern, ∅ gone. Shape and a label carry the meaning, not colour alone.
     progressEl(progress)    "✓ 3/12" for a file or folder row in the tree and on folder pages
     auditSection(...)       the Audit card of the symbol panel: state buttons, one-line comment, "needs re-review" notice, next symbol
     auditFileSection(...)   the Audit block of the inspector: progress bar and the marked symbols of the file
     renderAuditPage(...)    #/audit: totals, concerns, re-reviews, export / import, sharing
     installAuditKeys(...)   r = reviewed, c = concern, n = to do on the symbol that is open (the same key again clears it)
     loadSync(src)           loads sync.js on demand (shared mode only; the Explorer does not load it otherwise)
   Everything the reader typed (comments) or an import brought in goes into the page with textContent. */
import { h, num, day, copyText, toast } from "./dom.js";
import { buildRoute } from "./router.js";
import { GLYPH, LABEL, KEY_STATE, nextToReview, concernsMarkdown, markKey } from "./audit.js";
import { codeLinks } from "../links.js";

export const AUDIT_HASH = "#/audit";

const symHref = (path, qual, start, end) => buildRoute({ view: "file", path, qual, start, end, tab: "symbols" });
const short = (c) => String(c || "").slice(0, 7);

export function auditMark(status, extra = "") {
  if (!GLYPH[status]) return null;
  const label = `${LABEL[status]}${extra}`;
  return h("span", { class: `ex-aud ex-aud--${status}`, title: label, "aria-label": label, role: "img" }, GLYPH[status]);
}

export function describeToggle(result, state) {
  if (result === "cleared") return "Mark cleared";
  if (result === "renewed") return "Reviewed again: the current code is recorded";
  if (result === "set") return `Marked ${LABEL[state]}`;
  return "Could not save that mark";
}

/* p: audit.fileProgress() / dirProgress(): { reviewed, rereview, concern, todo, marked, total } or null. */
export function progressEl(p) {
  if (!p || !p.marked) return null;
  const parts = [`${num(p.reviewed)} of ${num(p.total)} symbols reviewed`];
  if (p.rereview) parts.push(`${num(p.rereview)} need re-review`);
  if (p.concern) parts.push(`${num(p.concern)} concern${p.concern === 1 ? "" : "s"}`);
  if (p.todo) parts.push(`${num(p.todo)} to do`);
  const lead = p.concern ? "concern" : p.rereview ? "rereview" : p.reviewed ? "reviewed" : "todo";
  const text = parts.join(", ");
  return h("span", { class: `ex-audp ex-audp--${lead}`, title: text, "aria-label": text },
    h("span", { class: `ex-aud ex-aud--${lead}`, "aria-hidden": "true" }, GLYPH[lead]), ` ${num(p.reviewed)}${p.total ? `/${num(p.total)}` : ""}`);
}

/* ------------------------------------------------------------------ the symbol panel card */
/* audit, path, row (a symbolRows() row: qual, start, end, hash), rows (all rows of the file), commit (the census commit, full) */
export function auditSection({ audit, path, row, rows, commit }) {
  const info = () => ({ hash: row.hash, commit, start: row.start, end: row.end });
  const state = h("span", { class: "ex-pill ex-audit__state" });
  const defs = [["reviewed", "r", "Reviewed"], ["concern", "c", "Concern"], ["todo", "n", "To do"]];
  const press = (st) => toast(describeToggle(audit.toggle(path, row.qual, st, info()), st));
  const btns = defs.map(([st, key, label]) => h("button", { type: "button", class: "mm-btn ex-audit__btn", dataset: { state: st }, "aria-pressed": "false", onclick: () => press(st) },
    h("span", { class: `ex-aud ex-aud--${st}`, "aria-hidden": "true" }, GLYPH[st]), h("span", { class: "ex-audit__label" }, label), " ", h("kbd", null, key)));
  const clearBtn = h("button", { type: "button", class: "ex-link", onclick: () => { audit.clear(path, row.qual); toast("Mark cleared"); } }, "Clear mark");
  const next = h("a", { class: "mm-btn ex-audit__next", hidden: true }, "Next to review →");
  const note = h("input", { type: "text", class: "ex-q ex-audit__note", maxlength: "200", autocomplete: "off", "aria-label": "One-line comment on this symbol", placeholder: "One-line comment (saved when you leave the box)" });
  const warn = h("p", { class: "ex-callout ex-callout--warn", hidden: true });
  const meta = h("p", { class: "ex-audit__meta ex-dim" });
  const root = h("section", { class: "ex-symp__sec ex-audit", "aria-label": "Audit" },
    h("h4", null, "Audit ", state), h("div", { class: "ex-audit__row" }, btns, next), warn, note, meta, h("p", null, clearBtn));

  note.addEventListener("change", () => { audit.setNote(path, row.qual, note.value); });
  note.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); note.blur(); }
    else if (e.key === "Escape") { const m = audit.get(path, row.qual); note.value = m ? m.note : ""; note.blur(); }
  });

  function paint() {
    const m = audit.get(path, row.qual);
    const st = audit.statusOf(path, row.qual, row.hash);
    state.textContent = st.status === "none" ? LABEL.none : `${GLYPH[st.status]} ${LABEL[st.status]}`;
    state.className = `ex-pill ex-audit__state${st.status === "none" ? "" : ` ex-audit__state--${st.status}`}`;
    btns.forEach((b) => { const on = !!m && m.state === b.dataset.state; b.setAttribute("aria-pressed", String(on)); b.classList.toggle("is-on", on); });
    btns[0].querySelector(".ex-audit__label").textContent = st.status === "rereview" ? "Reviewed again" : "Reviewed";
    note.disabled = !m;
    if (document.activeElement !== note) note.value = m ? m.note : "";
    clearBtn.parentElement.hidden = !m;
    warn.hidden = !(m && st.changed);
    if (m && st.changed) warn.textContent = m.state === "reviewed" ? `The code of this symbol has changed since you reviewed it${m.commit ? ` (against census commit ${short(m.commit)})` : ""}. Read it again, then press r to record the new version.` : "The code of this symbol has changed since you flagged it. The concern is kept; check whether it still applies.";
    meta.textContent = m
      ? `${LABEL[m.state][0].toUpperCase()}${LABEL[m.state].slice(1)}, marked ${day(m.at)}${m.commit ? ` against census commit ${short(m.commit)}` : ""}${m.hash ? "" : " (no code hash, so a change can not be detected)"}. ${audit.mode === "shared" ? "Shared with the team." : audit.persistent ? "Stored in this browser." : "Kept in this tab only: the browser refused to store it."}`
      : "Not marked. Press r when you have read it, c to flag a concern, n to put it on your to-do list; the same key again clears the mark.";
    const n = nextToReview(rows || [], row.qual, (r) => audit.statusOf(path, r.qual, r.hash));
    next.hidden = !n;
    if (n) { next.href = symHref(path, n.qual, n.start, n.end); next.title = `${n.qual}, line ${n.start}`; }
  }
  paint();
  const off = audit.on(() => { if (!root.isConnected) off(); else paint(); });
  return root;
}

/* ------------------------------------------------------------------ inspector block */
export function auditFileSection({ audit, path, rows }) {
  const root = h("section", { class: "ex-insp__sec ex-audsec", "aria-label": "Audit" });
  const total = rows.length;
  function paint() {
    const p = audit.fileProgress(path, total);
    const kids = [h("h3", null, "Audit", h("span", { class: "ex-dim" }, ` ${num(p ? p.reviewed : 0)} of ${num(total)} reviewed`))];
    if (!total) { kids.push(h("p", { class: "ex-dim" }, "This file has no functions or classes to mark.")); root.replaceChildren(...kids); return; }
    const pct = (n) => `${Math.round((n / total) * 1000) / 10}%`;
    const bar = h("div", { class: "ex-audbar", role: "img", "aria-label": p ? `${p.reviewed} reviewed, ${p.rereview} need re-review, ${p.concern} concerns, ${p.todo} to do, of ${total}` : `none of ${total} reviewed` });
    if (p) for (const k of ["reviewed", "rereview", "concern", "todo"]) if (p[k]) bar.append(h("i", { class: `ex-audbar__${k}`, style: `width:${pct(p[k])}` }));
    kids.push(bar);
    if (p) kids.push(h("p", { class: "ex-insp__note" }, [p.reviewed && `${p.reviewed} reviewed`, p.rereview && `${p.rereview} need re-review`, p.concern && `${p.concern} concern${p.concern === 1 ? "" : "s"}`, p.todo && `${p.todo} to do`].filter(Boolean).join(" · ")));
    const marked = audit.marksOf(path).sort((a, b) => a.start - b.start);
    if (!marked.length) kids.push(h("p", { class: "ex-dim" }, "Nothing marked in this file yet. Open a symbol and press r, c or n."));
    const li = (m) => h("li", null, auditMark(audit.statusOf(path, m.qual).status), " ", h("a", { href: symHref(path, m.qual, m.start, m.end) }, m.qual), m.note ? h("span", { class: "ex-dim" }, ` ${m.note}`) : null);
    if (marked.length) {
      const ul = h("ul", { class: "ex-insp__list ex-audsec__list" }, marked.slice(0, 12).map(li));
      kids.push(ul);
      if (marked.length > 12) kids.push(h("button", { type: "button", class: "ex-link", onclick: (e) => { ul.replaceChildren(...marked.map(li)); e.currentTarget.remove(); } }, `Show all ${num(marked.length)}`));
    }
    const n = nextToReview(rows, "", (r) => audit.statusOf(path, r.qual, r.hash));
    if (n) kids.push(h("p", null, h("a", { class: "mm-btn", href: symHref(path, n.qual, n.start, n.end) }, "Start with the next to review")));
    root.replaceChildren(...kids);
  }
  paint();
  const off = audit.on(() => { if (!root.isConnected) off(); else paint(); });
  return root;
}

/* ------------------------------------------------------------------ the Audit page (#/audit) */
const SYNC_TEXT = {
  connecting: "connecting to the shared store",
  live: "connected: marks are shared as you make them",
  saving: "sending changes",
  offline: "offline: your changes are kept here and sent when the connection is back",
  nobackend: "the shared store is not set up on this site (api/todo answered 503 or 404), so marks stay in this browser for now",
};

function download(name, text) {
  try {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = h("a", { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return true;
  } catch { return false; }
}

const readFile = (f) => (typeof f.text === "function" ? f.text() : new Promise((ok, no) => { const r = new window.FileReader(); r.onload = () => ok(String(r.result)); r.onerror = () => no(r.error); r.readAsText(f); }));

/* ctx: { audit, core, linkOpts, recheck(): Promise<{ files, more }>, setShared(on): Promise<void> } */
export function renderAuditPage(host, ctx) {
  const { audit, core } = ctx;
  const commit = core.tree.commit || "";
  const totalSyms = core.tree.root.n.functions + core.tree.root.n.classes;
  const root = h("div", { class: "ex-auditpage" });
  host.replaceChildren(h("nav", { class: "ex-crumbs", "aria-label": "Location" }, h("a", { href: "#/" }, "repo"), h("span", { "aria-hidden": "true" }, "/"), h("span", { "aria-current": "page" }, "audit")), root);
  let checking = false;

  const link = (m) => codeLinks({ path: m.path, start: m.start, end: m.end, commit: m.commit || commit }, ctx.linkOpts || {}).github || "";
  const item = (e) => {
    const m = e.mark;
    return h("li", { class: "ex-audlist__item" },
      auditMark(e.status), " ", h("a", { href: symHref(m.path, m.qual, m.start, m.end) }, h("code", null, markKey(m.path, m.qual))),
      m.note ? h("span", { class: "ex-audlist__note" }, ` ${m.note}`) : null,
      h("span", { class: "ex-dim" }, ` ${day(m.at)}${m.commit ? ` · commit ${short(m.commit)}` : ""}${e.changed && m.state === "concern" ? " · code changed since" : ""}`),
      " ", h("button", { type: "button", class: "ex-link", onclick: () => { audit.clear(m.path, m.qual); } }, "clear"));
  };
  function list(title, entries, { open = true, extra = null, hint = "" } = {}) {
    if (!entries.length) return null;
    const ul = h("ul", { class: "ex-audlist" }, entries.slice(0, 50).map(item));
    const more = entries.length > 50 ? h("button", { type: "button", class: "ex-link", onclick: (ev) => { ul.replaceChildren(...entries.map(item)); ev.currentTarget.remove(); } }, `Show all ${num(entries.length)}`) : null;
    return h("details", { class: "ex-audsec2", open }, h("summary", null, h("h2", { class: "ex-audsec2__h" }, `${title} (${num(entries.length)})`)), hint ? h("p", { class: "ex-dim" }, hint) : null, extra, ul, more);
  }

  function paint() {
    const t = audit.totals(totalSyms);
    const all = audit.entries();
    const pct = totalSyms ? Math.round((t.reviewed / totalSyms) * 1000) / 10 : 0;
    const concerns = all.filter((e) => e.state === "concern");
    const rereview = all.filter((e) => e.status === "rereview");
    const todo = all.filter((e) => e.status === "todo");
    const gone = all.filter((e) => e.status === "gone");
    const stat = (n, label, cls) => h("span", { class: "ex-audstat" }, h("span", { class: `ex-aud ex-aud--${cls}`, "aria-hidden": "true" }, GLYPH[cls]), h("b", null, num(n)), ` ${label}`);

    const shared = audit.mode === "shared";
    const syncBox = h("section", { class: "ex-audshare" }, h("h2", null, "Where the marks are kept"),
      h("p", null, shared ? "Marks are shared with the team through the live store of the To-do page. Everyone who has the site link sees and edits the same marks (there is no login), and the newest change to a symbol wins."
        : `Marks are kept in this browser${audit.persistent ? "" : ", but the browser refused to store them, so they are lost when the tab closes"}. Use Export to move them or keep a copy.`),
      h("label", { class: "ex-check" }, h("input", { type: "checkbox", checked: shared ? "" : null, onchange: async (e) => { e.currentTarget.disabled = true; try { await ctx.setShared(e.currentTarget.checked); } finally { paint(); } } }), " Share marks with the team (live sync)"),
      shared ? h("p", { class: "ex-dim" }, `Status: ${SYNC_TEXT[audit.syncStatus] || audit.syncStatus || "starting"}.`) : null,
      shared && audit.localSize() ? h("p", null, h("button", { type: "button", class: "mm-btn", onclick: () => { const n = audit.uploadLocal(); toast(n ? `Uploaded ${num(n)} mark${n === 1 ? "" : "s"} from this browser` : "Nothing to upload: the shared store already has newer or equal marks"); } }, `Upload the ${num(audit.localSize())} marks from this browser`)) : null);

    const file = h("input", { type: "file", accept: "application/json,.json", hidden: "", "aria-label": "Audit export to import" });
    file.addEventListener("change", async () => {
      const f = file.files && file.files[0];
      if (!f) return;
      let rep;
      try { rep = audit.importDoc(await readFile(f)); } catch { rep = { ok: false, error: "That file could not be read." }; }
      file.value = "";
      toast(rep.ok ? `Imported: ${num(rep.added)} new, ${num(rep.updated)} updated, ${num(rep.same)} unchanged${rep.older ? `, ${num(rep.older)} older kept as they were` : ""}${rep.invalid ? `, ${num(rep.invalid)} skipped` : ""}` : rep.error);
    });
    const exported = () => `${JSON.stringify(audit.exportDoc({ commit }), null, 2)}\n`;
    const md = () => concernsMarkdown(concerns, { commit, date: new Date().toISOString().slice(0, 10), link: (m) => link(m) });

    const checkBtn = h("button", { type: "button", class: "mm-btn", disabled: checking || !all.length ? "" : null, onclick: async () => {
      checking = true; paint();
      try { const r = await ctx.recheck(); toast(`Checked ${num(r.files)} file${r.files === 1 ? "" : "s"} against the census${r.more ? `; ${r.more} data shard(s) were left out` : ""}`); } catch (e) { toast(`Could not check: ${e.message}`); }
      checking = false; paint();
    } }, checking ? "Checking…" : "Check against the census");

    root.replaceChildren(...[                                       // replaceChildren(null) would write the text "null"
      h("h1", null, "Audit"),
      h("p", { class: "ex-lede" }, "Mark symbols as you read the code: ", h("kbd", null, "r"), " reviewed, ", h("kbd", null, "c"), " concern, ", h("kbd", null, "n"), " to do. A review is tied to the version of the code you read: if that symbol changes, the check turns into \"needs re-review\" until you read it again."),
      h("p", { class: "ex-audstats" }, stat(t.reviewed, `reviewed of ${num(totalSyms)} symbols (${pct}%)`, "reviewed"), stat(t.rereview, "need re-review", "rereview"), stat(t.concern, `concern${t.concern === 1 ? "" : "s"}`, "concern"), stat(t.todo, "to do", "todo"), t.gone ? stat(t.gone, "no longer in the census", "gone") : null),
      t.unchecked ? h("p", { class: "ex-callout" }, `${num(t.unchecked)} reviewed mark${t.unchecked === 1 ? " has" : "s have"} not been compared with the census in this page view yet (that happens for each file when you open it). `, "Use “Check against the census” to compare all of them now.") : null,
      h("p", { class: "ex-go" }, checkBtn,
        h("button", { type: "button", class: "mm-btn", disabled: all.length ? null : "", onclick: () => { toast(download(`minime-audit-${new Date().toISOString().slice(0, 10)}.json`, exported()) ? "Export downloaded" : "Could not start a download here; use Copy JSON"); } }, "Export JSON"),
        h("button", { type: "button", class: "mm-btn", disabled: all.length ? null : "", onclick: async () => toast((await copyText(exported())) ? "JSON copied" : "Could not copy") }, "Copy JSON"),
        h("button", { type: "button", class: "mm-btn", onclick: () => file.click() }, "Import JSON"), file),
      list("Concerns", concerns, { extra: h("p", null, h("button", { type: "button", class: "mm-btn", onclick: async () => toast((await copyText(md())) ? "Concerns copied as Markdown: paste them into an issue" : "Could not copy") }, "Copy as Markdown")) }),
      list("Need re-review", rereview, { hint: "Reviewed before, but the code of the symbol has changed since. Open one, read it, and press r." }),
      list("To do", todo, { open: false }),
      list("No longer in the census", gone, { open: false, hint: "The file or the symbol is gone (renamed, moved or deleted). Clear the mark, or leave it if the code may come back." }),
      !all.length ? h("p", { class: "ex-dim" }, "Nothing is marked yet. Open a symbol from the Symbols tab of any file, then press r, c or n.") : null,
      syncBox].filter(Boolean));
  }
  paint();
  const off = audit.on(() => { if (!root.isConnected) off(); else paint(); });
}

/* ------------------------------------------------------------------ keys */
/* current(): null when no file page is open, otherwise { path, row, rows, commit } where row is the symbol of the address (or null). */
export function installAuditKeys({ audit, current }) {
  const onKey = (e) => {
    if (e.defaultPrevented || e.isComposing || typeof e.key !== "string" || e.ctrlKey || e.metaKey || e.altKey) return;
    const state = KEY_STATE[e.key];
    if (!state) return;
    const t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;       // typing a comment or a filter
    if (document.documentElement.classList.contains("mmp-open")) return;                       // the palette or the shortcut sheet is open
    if (t && t.closest && t.closest("#ex-side")) return;                                      // browsing the tree: its keys are its own
    const c = current();
    if (!c) return;
    e.preventDefault();
    if (!c.row) { toast("Open a symbol first (Symbols tab), then press r, c or n"); return; }
    toast(describeToggle(audit.toggle(c.path, c.row.qual, state, { hash: c.row.hash, commit: c.commit, start: c.row.start, end: c.row.end }), state));
  };
  document.addEventListener("keydown", onKey);
  return () => document.removeEventListener("keydown", onKey);
}

/* sync.js is a classic script that defines window.Sync; it is only loaded when shared mode is on. */
export function loadSync(src) {
  return new Promise((ok, no) => {
    if (window.Sync) { ok(window.Sync); return; }
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => (window.Sync ? ok(window.Sync) : no(new Error("sync.js did not define Sync")));
    s.onerror = () => no(new Error("sync.js could not be loaded"));
    document.head.append(s);
  });
}
