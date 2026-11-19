/* MiniMe Atlas 2 - helpers for the Protocol, M2C and Decision-records pages (P24). One ES module, no DOM, no network: Node tests every
   function here (scripts/test_refresh_protocol.py). protocol.js does the drawing.

   Input, written by scripts/refresh_protocol.py from MiniMe's protocol/ folder (read from git at the census commit, never typed here):
     data/code/protocol.json   envelope, message types, run_event subtypes, tools, enums, fixtures, the client-copy comparison,
                               the M2C package map and commands, and the decision records
     data/index/notes.json     which files have an AI note (P11); the M2C package map shows a note summary only when one exists
   Nothing here invents a fact: a note, a fixture or a link is shown only when the data has it. */

import { buildRoute } from "./explorer/router.js";
import { fmtN, filterRows, sortRows, noteState } from "./codepages.js";

export { fmtN, filterRows, sortRows, noteState };

/* ------------------------------------------------------------------ links into the Explorer */
export const fileHref = (path) => `explorer.html${buildRoute({ view: "file", path })}`;
export const dirHref = (path) => `explorer.html${buildRoute({ view: "dir", path })}`;

/* Where the contract is used. The server side is what the plan names (backend/codeagent); the client side is the package that
   carries the synced copy of the schemas. */
export const LINKS = {
  schemas: "protocol/v1",
  readme: "protocol/README.md",
  validator: "protocol/validate.py",
  client: "m2c/src/m2c",
  clientCopy: "m2c/src/m2c/protocol",
  server: "backend/codeagent",
};

/* ------------------------------------------------------------------ messages */
export const DIRECTIONS = {
  client_to_server: { label: "client \u2192 server", short: "C\u2192S" },
  server_to_client: { label: "server \u2192 client", short: "S\u2192C" },
};
export const directionLabel = (d) => (DIRECTIONS[d] ? DIRECTIONS[d].label : String(d || ""));

/* run_id / seq rules come from the envelope's own if/then branches: "required", "forbidden" or "optional" */
export const routingText = (m) => `run_id ${m.run_id || "optional"} \u00b7 seq ${m.seq || "optional"}`;

export function messageRows(doc) {
  return ((doc && doc.messages) || []).map((m) => ({
    ...m,
    key: `m:${m.type}`,
    kind: "message",
    dirLabel: directionLabel(m.direction),
    nfields: (m.fields || []).length,
    nrequired: (m.fields || []).filter((f) => f.required).length,
    nfixtures: (m.fixtures || []).reduce((n, f) => n + f.count, 0),
  }));
}

export function eventRows(doc) {
  return ((doc && doc.run_events) || []).map((e) => ({ ...e, key: `e:${e.type}`, kind: "event", nfields: (e.fields || []).length }));
}

export function toolRows(doc) {
  return ((doc && doc.tools) || []).map((t) => ({
    ...t,
    key: `t:${t.name}`,
    kind: "tool",
    nfields: (t.fields || []).length,
    level: riskLevel(t.risk_max || t.risk),
  }));
}

/* ------------------------------------------------------------------ risk */
export const riskLevel = (r) => { const m = /^R(\d)$/.exec(String(r || "")); return m ? Number(m[1]) : -1; };

/* "R0 read-only, R1 write inside project, R2 run command, ..." (common.json's own description) -> { R0: "read-only", ... } */
export function riskMap(doc) {
  const text = (doc && doc.enums && doc.enums.risk && doc.enums.risk.description) || "";
  const out = {};
  for (const m of text.matchAll(/\b(R\d)\s+([^,.]+?)(?=,\s*R\d|\.|$)/g)) out[m[1]] = m[2].trim();
  return out;
}

/* Five pips, filled up to the level: the badge says the level in words and shape too, so colour is never the only signal. */
export const riskPips = (r, total = 5) => {
  const n = riskLevel(r);
  return n < 0 ? "" : "\u25cf".repeat(Math.min(n + 1, total)) + "\u25cb".repeat(Math.max(total - n - 1, 0));
};

/* A tool's risk as text: "R1", or "R1 (R4 outside the project)" when risk_max says a call can be riskier. */
export const toolRiskText = (t) => (t.risk_max ? `${t.risk} up to ${t.risk_max}` : t.risk);

/* ------------------------------------------------------------------ fields */
/* Rows of a field table, nested fields flattened with a depth so the table can indent them. */
export function flattenFields(fields, depth = 0, out = []) {
  for (const f of fields || []) {
    out.push({ ...f, depth });
    if (f.fields && f.fields.length) flattenFields(f.fields, depth + 1, out);
  }
  return out;
}

/* The small facts of one field, as short strings: its allowed values, constant, default and limits. */
export function fieldFacts(f) {
  const out = [];
  if (f.enum) out.push(`one of: ${f.enum.join(", ")}`);
  if (f.const !== undefined) out.push(`always ${JSON.stringify(f.const)}`);
  if (f.default !== undefined) out.push(`default ${JSON.stringify(f.default)}`);
  if (f.limits) out.push(f.limits);
  return out;
}

export const exampleText = (ex) => (ex && ex.message ? JSON.stringify(ex.message, null, 2) : "");

/* ------------------------------------------------------------------ hash routes: #m/run.start, #t/bash, #e/text_delta */
const PREFIX = { message: "m", tool: "t", event: "e" };
export const rowHash = (row) => `#${PREFIX[row.kind]}/${encodeURIComponent(row.key.slice(2))}`;
export function rowFromHash(rows, hash) {
  const m = /^#([mte])\/(.+)$/.exec(String(hash || ""));
  if (!m) return null;
  let name = "";
  try { name = decodeURIComponent(m[2]); } catch { return null; }
  return rows.find((r) => r.key === `${m[1]}:${name}`) || null;
}

/* ------------------------------------------------------------------ the page's top line */
export function protocolKpis(doc) {
  const t = (doc && doc.totals) || {};
  return [
    { label: "message types", value: t.messages },
    { label: "run_event subtypes", value: t.run_events },
    { label: "tools", value: t.tools },
    { label: "golden transcripts", value: t.fixtures },
  ];
}

/* The chip next to the commit: is the client's copy of the schemas byte for byte the server's? { kind, text, title } */
export function clientCopyInfo(doc) {
  const c = doc && doc.client_copy;
  if (!c || c.state === "none") return { kind: "stale", text: "no client copy found", title: "m2c/src/m2c/protocol/v1 does not exist at this commit, so there is nothing to compare." };
  if (c.state === "identical") return { kind: "ok", text: "client copy identical", title: `All ${fmtN(c.files)} schema files under ${c.dir} are byte for byte the ones in protocol/v1.` };
  const parts = [];
  if (c.differs.length) parts.push(`${c.differs.length} differ`);
  if (c.missing.length) parts.push(`${c.missing.length} missing on the client`);
  if (c.extra.length) parts.push(`${c.extra.length} extra on the client`);
  return { kind: "stale", text: `client copy out of sync (${parts.join(", ")})`, title: [...c.differs, ...c.missing, ...c.extra].slice(0, 12).join(", ") };
}

/* ------------------------------------------------------------------ the M2C package map */
/* The note to show for a package: its __init__.py first, then the lowest tier, then the name. */
export function noteForPackage(index, pkg) {
  const files = (index && index.files) || {};
  const prefix = pkg.kind === "package" ? `${pkg.path}/` : pkg.path;
  const hits = Object.keys(files).filter((p) => (pkg.kind === "package" ? p.startsWith(prefix) : p === prefix) && files[p].summary);
  if (!hits.length) return null;
  const rank = (p) => (p === `${pkg.path}/__init__.py` ? -1 : files[p].tier || 9);
  hits.sort((a, b) => rank(a) - rank(b) || (a < b ? -1 : 1));
  return { path: hits[0], summary: files[hits[0]].summary, state: noteState(index, hits[0]), count: hits.length };
}

export function packageRows(doc, index) {
  return (((doc && doc.m2c) || {}).packages || []).map((p) => ({
    ...p,
    key: p.path,
    kindLabel: p.client_copy ? "package (schema copy)" : p.kind,
    note: noteForPackage(index, p),
    href: p.kind === "package" ? dirHref(p.path) : fileHref(p.path),
  }));
}

export function m2cKpis(doc) {
  const m = (doc && doc.m2c) || {};
  const pk = m.packages || [];
  return [
    { label: "packages", value: pk.filter((p) => p.kind === "package").length },
    { label: "top-level modules", value: pk.filter((p) => p.kind === "module").length },
    { label: "files in the client", value: pk.reduce((n, p) => n + p.files, 0) },
    { label: "commands", value: (m.commands || []).length },
  ];
}

/* ------------------------------------------------------------------ decision records */
export const adrRows = (doc) => ((doc && doc.adrs) || []).map((a) => ({ ...a, key: a.path, href: fileHref(a.path) }));
export const ADR_BADGE = {
  accepted: ["ok", "accepted"],
  superseded: ["stale", "superseded"],
  other: ["here", "see the record"],
};
export const adrBadge = (a) => ADR_BADGE[a.status] || ADR_BADGE.other;
