// P16: api/todo.js accepts the "audit" record kind, and nothing else new. Upstash is replaced by a fake; no network.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { auditId } from "../../assets/js/explorer/audit.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
process.env.KV_REST_API_URL = "http://upstash.test";
process.env.KV_REST_API_TOKEN = "t";
const handler = createRequire(import.meta.url)(path.join(ROOT, "api", "todo.js"));

let evals = [];
let stored = [];
globalThis.fetch = async (url, init) => {
  const body = JSON.parse(init.body);
  const run = (cmd) => {
    const [name, ...a] = cmd;
    if (name === "EVAL") { evals.push(cmd); const fields = []; for (let i = 7; i < cmd.length; i += 3) fields.push(cmd[i]); return ["7", ...fields]; }
    if (name === "EXISTS") return 1;
    if (name === "INCR" || name === "EXPIRE") return 1;
    if (name === "HGETALL") return stored;
    return null;
  };
  const j = String(url).endsWith("/pipeline") ? body.map((c) => ({ result: run(c) })) : { result: run(body) };
  return { ok: true, status: 200, json: async () => j };
};

async function call(method, payload) {
  const res = { statusCode: 0, headers: {}, body: "", setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b; } };
  await handler({ method, headers: { "content-length": "100", "x-forwarded-for": "9.9.9.9" }, body: payload, query: {}, url: "/api/todo" }, res);
  return { status: res.statusCode, json: JSON.parse(res.body) };
}
const op = (k, id, v) => ({ ops: [{ k, id, v: { updatedAt: new Date().toISOString(), ...v } }] });
let n = 0;
const t = async (name, f) => { try { await f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };

await t("an audit record is accepted and stored under audit:<id>", async () => {
  evals = [];
  const id = auditId("backend/eo/router.py", "route");          // the id the Explorer really makes
  const r = await call("POST", op("audit", id, { path: "backend/eo/router.py", qual: "route", state: "reviewed", hash: "ab12", note: "ok" }));
  assert.equal(r.status, 200); assert.deepEqual(r.json.applied, [`audit:${id}`]); assert.deepEqual(r.json.rejected, []);
  assert.equal(JSON.parse(evals[0][9]).path, "backend/eo/router.py");
});

await t("a tombstone for an audit record is accepted", async () => {
  const r = await call("POST", op("audit", auditId("a.py", "f"), { path: "a.py", qual: "f", deleted: true }));
  assert.equal(r.status, 200); assert.equal(r.json.applied.length, 1);
});

await t("the old kinds still work", async () => {
  for (const k of ["person", "project", "task", "master", "settings"]) assert.equal((await call("POST", op(k, "x1", { name: "n" }))).status, 200, k);
});

await t("nothing else got in: other kinds and look-alikes are refused", async () => {
  for (const k of ["audits", "Audit", "audit:x", "__proto__", "constructor", ""]) { const r = await call("POST", op(k, "x1", {})); assert.equal(r.status, 400, `kind ${JSON.stringify(k)}`); assert.equal(r.json.error, "bad_op"); }
});

await t("the id rule is unchanged: path::qual itself is not a valid id (that is why the Explorer hashes it)", async () => {
  for (const id of ["backend/eo/router.py::route", "a:b", "a b", "x".repeat(65), ""]) assert.equal((await call("POST", op("audit", id, {}))).status, 400, JSON.stringify(id));
});

await t("size limit still applies to audit records", async () => {
  const r = await call("POST", op("audit", "a1", { note: "x".repeat(41000) }));
  assert.equal(r.status, 413); assert.equal(r.json.error, "entity_too_big");
});

await t("reads return audit records together with the rest", async () => {
  stored = [`audit:${auditId("a.py", "f")}`, JSON.stringify({ id: auditId("a.py", "f"), path: "a.py", qual: "f", state: "todo", updatedAt: "2026-11-18T00:00:00.000Z" })];
  const r = await call("GET", undefined);
  assert.equal(r.status, 200); assert.equal(r.json.ents.length, 1); assert.match(r.json.ents[0].key, /^audit:a/);
});

console.log(`${n} ran`);
