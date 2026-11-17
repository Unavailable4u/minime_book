/* MiniMe Atlas 2 - Explorer SQL outline (P14e). A .sql file as a list of what it does, with a link to the lines of each statement.

   A migration is hard to read as text: 400 lines of GRANTs and policies around the three tables it is really about. The Outline lists
   the statements in file order, each with its kind, the object it touches, a short detail, the comment written directly above it, and
   the first and last line (a link into the Source tab). A CREATE TABLE unfolds into its columns and constraints.

   Pure half (Node tests it):
     scanSql(text)         -> { statements: [{ text, line, end, comment }], header }
                              a real tokenizer: -- and nested block comments, 'strings' (with '' and E'\\'), "identifiers", $$dollar quoting$$
                              and psql \\commands, so a ';' inside a function body or a string never splits a statement
     classify(text)        -> { kind, name, detail, columns?, constraints? }
     sqlOutline(text)      -> { header, statements: [{ kind, name, detail, line, end, comment, columns?, constraints? }], counts }
   DOM half:
     renderSql(text, ctx)  -> { el }

   This is a reader's aid, not a SQL parser: it recognises the statements this repository uses (tables, views, indexes, policies,
   functions, triggers, types, grants, comments, ALTERs, DROPs, plain DML) and calls anything else "other" with its first words. It never
   executes anything and never sends the file anywhere. Text only ever goes in as text nodes. */
import { h, num } from "./dom.js";
import { buildRoute } from "./router.js";

export const MAX_CHARS = 1500000;

/* ------------------------------------------------------------------ tokenizer */
const cleanComment = (raw) => { const t = raw.replace(/^[\s*]+|[\s*]+$/g, "").trim(); return /^[-=*#_~\s]*$/.test(t) ? "" : t; };

/* Runs of consecutive comment lines: [[{line,text}...], ...]. */
function runs(list) {
  const out = [];
  for (const c of list) {
    const last = out[out.length - 1];
    if (last && last[last.length - 1].line === c.line - 1) last.push(c); else out.push([c]);
  }
  return out;
}

export function scanSql(text) {
  const src = String(text == null ? "" : text).replace(/\r\n?/g, "\n");
  const n = src.length;
  const statements = [];
  let line = 1;
  let cur = "";
  let startLine = 0;
  let lastCode = 0;
  let codeOnLine = false;
  let comments = [];                            // comment lines seen since the last statement ended (or since this one began)
  let pre = [];                                 // the comment lines that came before the current statement's first character
  let header = "";
  let first = true;
  const newlines = (s) => { let k = 0; for (let p = s.indexOf("\n"); p >= 0; p = s.indexOf("\n", p + 1)) k++; return k; };

  const finish = (hasStatement) => {
    if (hasStatement && cur.trim() && cur.trim() !== ";") {
      const rs = runs(pre);
      const adj = rs.length && rs[rs.length - 1][rs[rs.length - 1].length - 1].line === startLine - 1 ? rs[rs.length - 1] : null;
      if (first) { const head = rs.find((r) => r !== adj); if (head) header = head.map((c) => c.text).filter(Boolean).join("\n"); }
      statements.push({ text: cur.trim(), line: startLine, end: lastCode || startLine, comment: adj ? adj.map((c) => c.text).filter(Boolean).join(" ") : "" });
      first = false;
    }
    cur = ""; startLine = 0; lastCode = 0; pre = []; comments = [];
  };

  let i = 0;
  while (i < n) {
    const c = src[i];
    if (c === "\n") { line++; codeOnLine = false; if (startLine) cur += "\n"; i++; continue; }
    if (c === "-" && src[i + 1] === "-") {
      let e = src.indexOf("\n", i);
      if (e < 0) e = n;
      if (!codeOnLine) comments.push({ line, text: cleanComment(src.slice(i + 2, e)) });
      i = e;
      continue;
    }
    if (c === "/" && src[i + 1] === "*") {                                    // block comments nest in PostgreSQL
      let depth = 1;
      let j = i + 2;
      while (j < n && depth) { if (src[j] === "/" && src[j + 1] === "*") { depth++; j += 2; } else if (src[j] === "*" && src[j + 1] === "/") { depth--; j += 2; } else j++; }
      const body = src.slice(i + 2, Math.max(i + 2, j - 2));
      body.split("\n").forEach((part, k) => { if (!(k === 0 && codeOnLine)) comments.push({ line: line + k, text: cleanComment(part) }); });
      if (startLine) cur += " ";
      line += newlines(src.slice(i, j));
      if (newlines(src.slice(i, j))) codeOnLine = false;
      i = j;
      continue;
    }
    if (/\s/.test(c)) { if (startLine) cur += c; i++; continue; }

    if (!startLine) { startLine = line; pre = comments; comments = []; }
    codeOnLine = true;
    lastCode = line;

    if (c === "\\" && cur === "") {                                           // a psql meta-command is a whole line
      let e = src.indexOf("\n", i);
      if (e < 0) e = n;
      cur = src.slice(i, e);
      lastCode = line;
      i = e;
      finish(true);
      codeOnLine = false;
      continue;
    }
    if (c === "'" || c === '"') {
      const esc = c === "'" && /[eE]/.test(src[i - 1] || "") && !/[\w$]/.test(src[i - 2] || "");
      let j = i + 1;
      while (j < n) {
        if (esc && src[j] === "\\") { j += 2; continue; }
        if (src[j] === c) { if (src[j + 1] === c) { j += 2; continue; } break; }
        j++;
      }
      const raw = src.slice(i, j + 1);
      cur += raw;
      line += newlines(raw);
      lastCode = line;
      i = j + 1;
      continue;
    }
    if (c === "$" && !/[\w$]/.test(src[i - 1] || "")) {
      const m = /^\$([A-Za-z_]\w*)?\$/.exec(src.slice(i, i + 80));
      if (m) {
        const e = src.indexOf(m[0], i + m[0].length);
        const stop = e < 0 ? n : e + m[0].length;
        const raw = src.slice(i, stop);
        cur += raw;
        line += newlines(raw);
        lastCode = line;
        i = stop;
        continue;
      }
    }
    if (c === ";") { cur += ";"; i++; finish(true); continue; }
    cur += c;
    i++;
  }
  if (cur.trim()) finish(true);
  else if (first && comments.length) { const r = runs(comments)[0]; header = r.map((x) => x.text).filter(Boolean).join("\n"); }
  return { statements, header };
}

/* ------------------------------------------------------------------ classification */
const ID = String.raw`(?:"(?:[^"]|"")+"|[A-Za-z_][\w$]*)`;
const QN = String.raw`(${ID}(?:\s*\.\s*${ID})*)`;
const unq = (s) => String(s || "").replace(/\s*\.\s*/g, ".").replace(/"((?:[^"]|"")+)"/g, "$1");
const cut = (s, k) => { const t = String(s || "").trim(); return t.length > k ? `${t.slice(0, k - 1)}…` : t; };
const re = (src) => new RegExp(src, "i");

/* The text inside the first "(" ... ")" after `from`, balancing parentheses and skipping quotes. null when there is none. */
function parens(s, from) {
  const open = s.indexOf("(", from);
  if (open < 0) return null;
  let depth = 0;
  for (let j = open; j < s.length; j++) {
    const c = s[j];
    if (c === "'" || c === '"') { const e = s.indexOf(c, j + 1); j = e < 0 ? s.length : e; continue; }
    if (c === "(") depth++;
    else if (c === ")" && --depth === 0) return s.slice(open + 1, j);
  }
  return null;
}

function splitTop(s) {
  const parts = [];
  let depth = 0;
  let cur = "";
  for (let j = 0; j < s.length; j++) {
    const c = s[j];
    if (c === "'" || c === '"') { const e = s.indexOf(c, j + 1); const stop = e < 0 ? s.length : e; cur += s.slice(j, stop + 1); j = stop; continue; }
    if (c === "(") depth++;
    else if (c === ")") depth--;
    if (c === "," && depth === 0) { parts.push(cur.trim()); cur = ""; } else cur += c;
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

const COL_STOP = /\s+(?:not null|null|default|primary key|references|unique|check|generated|constraint|collate)\b/i;

function tableBody(sq, afterName) {
  const inner = parens(sq, afterName);
  const columns = [];
  const constraints = [];
  if (inner == null) return { columns, constraints };
  for (const part of splitTop(inner)) {
    if (/^(?:constraint\s+\S+\s+)?(?:primary key|foreign key|unique|check|exclude)\b/i.test(part) || /^like\b/i.test(part)) { constraints.push(cut(part.replace(/\s+/g, " "), 140)); continue; }
    const m = new RegExp(`^(${ID})\\s+([\\s\\S]*)$`).exec(part);
    if (!m) { constraints.push(cut(part.replace(/\s+/g, " "), 140)); continue; }
    const rest = m[2].replace(/\s+/g, " ");
    const stop = COL_STOP.exec(rest);
    const dflt = /\bdefault\s+(.+?)(?=\s+(?:not null|null|primary key|references|unique|check|constraint|collate)\b|$)/i.exec(rest);
    const ref = new RegExp(`\\breferences\\s+${QN}(?:\\s*\\(([^)]*)\\))?`, "i").exec(rest);
    columns.push({
      name: unq(m[1]), type: cut(stop ? rest.slice(0, stop.index) : rest, 60), notNull: /\bnot null\b/i.test(rest) || /\bprimary key\b/i.test(rest), pk: /\bprimary key\b/i.test(rest),
      unique: /\bunique\b/i.test(rest), def: dflt ? cut(dflt[1], 50) : "", ref: ref ? `${unq(ref[1])}${ref[2] ? `(${ref[2].trim()})` : ""}` : "",
    });
  }
  return { columns, constraints };
}

const RULES = [];
const rule = (pattern, fn) => RULES.push([re(pattern), fn]);

rule(String.raw`^create (?:or replace )?(?:(?:global |local )?(?:temp|temporary) |unlogged )?table (?:if not exists )?${QN}`, (m, sq) => {
  const t = tableBody(sq, m[0].length);
  return { kind: "table", name: unq(m[1]), detail: `${t.columns.length} column${t.columns.length === 1 ? "" : "s"}${t.constraints.length ? `, ${t.constraints.length} constraint${t.constraints.length === 1 ? "" : "s"}` : ""}`, ...t };
});
rule(String.raw`^create (?:or replace )?(materialized )?(?:(?:temp|temporary) )?(?:recursive )?view (?:if not exists )?${QN}`, (m) => ({ kind: "view", name: unq(m[2]), detail: m[1] ? "materialized view" : "" }));
rule(String.raw`^create (unique )?index (?:concurrently )?(?:if not exists )?(?:${QN} )?on (?:only )?${QN}(?: using \w+)?\s*(\(.*)?`, (m) => ({
  kind: "index", name: unq(m[2]) || "(unnamed)", detail: `${m[1] ? "unique, " : ""}on ${unq(m[3])}${m[4] ? ` ${cut(m[4].replace(/\)\s*(where|include|with|tablespace)\b[\s\S]*$/i, ")").replace(/;\s*$/, ""), 80)}` : ""}`,
}));
rule(String.raw`^create policy ${QN} on ${QN}(?: as (permissive|restrictive))?(?: for (all|select|insert|update|delete))?(?: to ([^\s(]+(?:\s*,\s*[^\s(]+)*))?`, (m, sq) => ({
  kind: "policy", name: unq(m[1]), detail: [`on ${unq(m[2])}`, m[4] ? `for ${m[4].toLowerCase()}` : "for all", m[5] ? `to ${m[5].replace(/\s+/g, " ")}` : "", /\bwith check\b/i.test(sq) ? "with check" : "", /\busing\b/i.test(sq) ? "using" : ""].filter(Boolean).join(" · "),
}));
rule(String.raw`^create (?:or replace )?(function|procedure) ${QN}`, (m, sq) => {
  const args = parens(sq, m[0].length);
  const ret = /\breturns\s+(setof\s+)?(.+?)(?=\s+(?:language|as|volatile|stable|immutable|security|strict|cost|rows|set|parallel|returns)\b|$)/i.exec(sq);
  return { kind: m[1].toLowerCase() === "procedure" ? "procedure" : "function", name: unq(m[2]), detail: `(${cut((args || "").replace(/\s+/g, " "), 70)})${ret ? ` returns ${cut(`${ret[1] || ""}${ret[2]}`, 40)}` : ""}` };
});
rule(String.raw`^create (?:or replace )?(?:constraint )?trigger ${QN}\s+((?:before|after|instead of)\s+[\s\S]*?)\s+on ${QN}`, (m) => ({ kind: "trigger", name: unq(m[1]), detail: `${cut(m[2].replace(/\s+/g, " ").toLowerCase(), 50)} on ${unq(m[3])}` }));
rule(String.raw`^create (?:or replace )?(?:unlogged )?(type|domain|extension|schema|sequence|role|user|group|publication|aggregate|operator|collation|event trigger|rule|cast) (?:if not exists )?${QN}`, (m) => ({ kind: m[1].toLowerCase(), name: unq(m[2]), detail: "" }));
rule(String.raw`^alter table (?:if exists )?(?:only )?${QN}\s+([\s\S]*)$`, (m) => ({ kind: "alter", name: unq(m[1]), detail: cut(m[2].replace(/\s+/g, " ").replace(/;$/, ""), 120) }));
rule(String.raw`^alter default privileges\s*([\s\S]*)$`, (m) => ({ kind: "alter", name: "default privileges", detail: cut(m[1].replace(/\s+/g, " ").replace(/;$/, ""), 120) }));
rule(String.raw`^alter (policy|index|sequence|view|materialized view|function|type|role|user|schema|default privileges|publication|extension|database|domain|trigger|system)\s+(?:if exists )?(?:${QN})?\s*([\s\S]*)$`, (m) => ({ kind: "alter", name: unq(m[2]) || m[1].toLowerCase(), detail: cut(`${m[1].toLowerCase()} ${m[3].replace(/\s+/g, " ").replace(/;$/, "")}`, 120) }));
rule(String.raw`^drop (policy|table|index|function|procedure|trigger|view|materialized view|type|schema|extension|role|user|sequence|constraint|domain|publication|rule)\s+(?:if exists )?(?:concurrently )?${QN}(?:\s*\([^)]*\))?(?: on ${QN})?`, (m) => ({ kind: "drop", name: unq(m[2]) + (m[3] ? ` on ${unq(m[3])}` : ""), detail: m[1].toLowerCase() }));
rule(String.raw`^(grant|revoke)\s+(?:grant option for\s+)?([\s\S]+?)\s+on\s+([\s\S]+?)\s+(?:to|from)\s+([\s\S]+?)(?:\s+with grant option)?;?$`, (m) => ({
  kind: m[1].toLowerCase(), name: cut(unq(m[3].replace(/\s+/g, " ").replace(/^table\s+/i, "")), 80), detail: `${cut(m[2].replace(/\s+/g, " ").toLowerCase(), 60)} ${m[1].toLowerCase() === "grant" ? "to" : "from"} ${cut(m[4].replace(/\s+/g, " "), 60)}`,
}));
rule(String.raw`^(grant|revoke)\s+([\s\S]+?)\s+(?:to|from)\s+([\s\S]+?);?$`, (m) => ({ kind: m[1].toLowerCase(), name: cut(m[2].replace(/\s+/g, " "), 80), detail: `${m[1].toLowerCase() === "grant" ? "to" : "from"} ${cut(m[3].replace(/\s+/g, " "), 60)}` }));
rule(String.raw`^comment on (\w+(?: \w+)?)\s+${QN}(?:\s+on ${QN})?\s+is\s+([\s\S]*)$`, (m) => ({ kind: "comment", name: `${m[1].toLowerCase()} ${unq(m[2])}${m[3] ? ` on ${unq(m[3])}` : ""}`, detail: cut(m[4].replace(/\s+/g, " ").replace(/^'|'?;?$/g, ""), 100) }));
rule(String.raw`^insert into ${QN}`, (m) => ({ kind: "data", name: unq(m[1]), detail: "insert" }));
rule(String.raw`^update (?:only )?${QN}`, (m) => ({ kind: "data", name: unq(m[1]), detail: "update" }));
rule(String.raw`^delete from (?:only )?${QN}`, (m) => ({ kind: "data", name: unq(m[1]), detail: "delete" }));
rule(String.raw`^truncate (?:table )?(?:only )?${QN}`, (m) => ({ kind: "data", name: unq(m[1]), detail: "truncate" }));
rule(String.raw`^do\b`, (m, sq) => ({ kind: "do", name: "(anonymous block)", detail: cut(sq.replace(/^do\s+(?:language \w+\s+)?\$\w*\$\s*/i, ""), 100) }));
rule(String.raw`^(begin|commit|end|rollback|start transaction|savepoint|release)\b`, (m) => ({ kind: "txn", name: m[1].toLowerCase(), detail: "" }));

export function classify(text) {
  const sq = String(text || "").replace(/\s+/g, " ").trim();
  for (const [pattern, fn] of RULES) {
    const m = pattern.exec(sq);
    if (m) return fn(m, sq);
  }
  const word = (/^[\\\w]+/.exec(sq) || ["statement"])[0].toLowerCase();
  return { kind: "other", name: word, detail: cut(sq.slice(word.length).replace(/;$/, ""), 100) };
}

export function sqlOutline(text) {
  const { statements, header } = scanSql(text);
  const out = statements.map((s) => ({ ...classify(s.text), line: s.line, end: s.end, comment: s.comment }));
  const counts = {};
  out.forEach((s) => { counts[s.kind] = (counts[s.kind] || 0) + 1; });
  return { header, statements: out, counts };
}

/* ------------------------------------------------------------------ DOM */
const ORDER = ["table", "view", "index", "policy", "function", "procedure", "trigger", "type", "domain", "extension", "schema", "sequence", "role", "user", "group", "alter", "grant", "revoke", "comment", "data", "do", "drop", "txn", "other"];
const kindRank = (k) => { const i = ORDER.indexOf(k); return i < 0 ? ORDER.length : i; };

function columnsTable(s) {
  const head = h("tr", null, ["Column", "Type", "Constraints", "Default", "References"].map((x) => h("th", { scope: "col" }, x)));
  const body = s.columns.map((c) => h("tr", null, h("td", null, h("code", null, c.name)), h("td", null, c.type),
    h("td", null, [c.pk ? "primary key" : null, c.notNull && !c.pk ? "not null" : null, c.unique ? "unique" : null].filter(Boolean).join(", ")), h("td", null, c.def ? h("code", null, c.def) : ""), h("td", null, c.ref)));
  const box = h("div", { class: "ex-sql__cols" }, h("div", { class: "mm-tablewrap" }, h("table", { class: "mm-table is-compact" }, h("thead", null, head), h("tbody", null, body))));
  if (s.constraints.length) box.append(h("ul", { class: "ex-list ex-sql__cons" }, s.constraints.map((x) => h("li", null, h("code", null, x)))));
  return box;
}

/* ctx = { path } */
export function renderSql(text, ctx = {}) {
  const root = h("div", { class: "ex-sql" });
  if (String(text).length > MAX_CHARS) {
    root.append(h("p", { class: "ex-callout ex-callout--warn" }, `This file is ${num(String(text).length)} characters, too big to outline here. Use the Source tab.`));
    return { el: root };
  }
  const o = sqlOutline(text);
  const link = (s) => buildRoute({ view: "file", path: ctx.path, start: s.line, end: s.end > s.line ? s.end : null, tab: "source" });

  if (o.header) {
    const lines = o.header.split("\n");
    root.append(h("details", { class: "ex-sql__head", open: lines.length <= 6 }, h("summary", null, `Comment at the top of the file (${lines.length} line${lines.length === 1 ? "" : "s"})`), h("pre", { class: "ex-pre" }, o.header)));
  }
  if (!o.statements.length) { root.append(h("p", { class: "ex-dim" }, "No SQL statements found in this file.")); return { el: root }; }

  const kinds = Object.keys(o.counts).sort((a, b) => kindRank(a) - kindRank(b) || (a < b ? -1 : 1));
  let only = "";
  const chips = h("p", { class: "ex-sql__chips", role: "group", "aria-label": "Show only one kind of statement" });
  const tbody = h("tbody");
  const stat = h("span", { class: "ex-dim ex-sql__stat", "aria-live": "polite" });
  const paint = () => {
    chips.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String((b.dataset.kind || "") === only)));
    const rows = o.statements.filter((s) => !only || s.kind === only);
    stat.textContent = `${num(rows.length)} of ${num(o.statements.length)} statements`;
    tbody.replaceChildren(...rows.map((s) => {
      const detail = h("td", { class: "ex-sql__detail" });
      if (s.kind === "table" && s.columns.length) detail.append(h("details", null, h("summary", null, s.detail), columnsTable(s)));
      else if (s.detail) detail.append(s.detail);
      if (s.comment) detail.append(h("span", { class: "ex-sql__note ex-dim", title: s.comment }, cut(s.comment, 160)));
      return h("tr", null,
        h("td", { class: "is-num" }, h("a", { href: link(s), title: `Show lines ${s.line}-${s.end} in the Source tab` }, s.end > s.line ? `${s.line}–${s.end}` : String(s.line))),
        h("td", null, h("span", { class: "ex-pill" }, s.kind)), h("td", null, h("code", null, s.name)), detail);
    }));
  };
  const chip = (kind, label) => { const b = h("button", { type: "button", class: "mm-btn", dataset: { kind }, onclick: () => { only = only === kind ? "" : kind; paint(); } }, label); chips.append(b); };
  chip("", `All (${o.statements.length})`);
  kinds.forEach((k) => chip(k, `${k} ${o.counts[k]}`));
  root.append(chips, stat, h("div", { class: "mm-tablewrap ex-tablewrap" }, h("table", { class: "mm-table is-compact ex-sql__table" },
    h("thead", null, h("tr", null, [["Lines", "is-num"], ["Kind", ""], ["Object", ""], ["Detail", ""]].map(([x, c]) => h("th", { scope: "col", class: c || null }, x)))), tbody)));
  paint();
  return { el: root, outline: o };
}
