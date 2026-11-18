// P16: audit.js, the rules and the store. No DOM: an in-memory Storage and a fake Sync stand in for the browser.
import assert from "node:assert/strict";
import * as A from "../../assets/js/explorer/audit.js";
let n = 0;
const t = (name, f) => { try { f(); n++; console.log(`ok: ${name}`); } catch (e) { console.log(`FAIL: ${name}\n  ${e.message}`); process.exitCode = 1; } };

const memStorage = (init = {}) => { const m = { ...init }; return { m, getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); } }; };
let clock = 0;
const now = () => new Date(Date.UTC(2026, 10, 18, 9, 0, clock++)).toISOString();
const mk = (storage = memStorage()) => A.createAudit({ storage, now });
const P = "backend/eo/router.py";

t("auditId fits api/todo.js ID_RE, is stable, differs per symbol, survives odd paths", () => {
  const RE = /^[A-Za-z0-9_.-]{1,64}$/;
  for (const [p, q] of [[P, "route"], ["a b/ü.py", "A.m"], ["x/".repeat(150), "q"], ["f.py", "<lambda>"]]) assert.ok(RE.test(A.auditId(p, q)), `${p}`);
  assert.equal(A.auditId(P, "route"), A.auditId(P, "route"));
  assert.notEqual(A.auditId(P, "route"), A.auditId(P, "route2"));
  const ids = new Set(); for (let i = 0; i < 20000; i++) ids.add(A.auditId(`backend/f${i % 400}.py`, `fn${i}`)); assert.equal(ids.size, 20000, "no collisions over 20,000 symbols");
});

t("normalizeMark: accepts a good mark, cleans fields, rejects bad ones", () => {
  const m = A.normalizeMark({ path: P, qual: "route", state: "reviewed", note: "  a\n\tb  ", hash: "ab12", commit: "ABCDEF1", start: 3, end: 9, at: "2026-11-18T09:00:00Z" });
  assert.deepEqual([m.note, m.hash, m.commit, m.start, m.end, m.at], ["a b", "ab12", "abcdef1", 3, 9, "2026-11-18T09:00:00.000Z"]);
  assert.equal(A.normalizeMark({ path: P, qual: "x", state: "nope" }), null);
  assert.equal(A.normalizeMark({ path: "a::b", qual: "x", state: "todo" }), null);
  assert.equal(A.normalizeMark({ path: P, qual: "x::y", state: "todo" }), null);
  assert.equal(A.normalizeMark({ path: "", qual: "x", state: "todo" }), null);
  assert.equal(A.normalizeMark(null), null); assert.equal(A.normalizeMark([]), null); assert.equal(A.normalizeMark("x"), null);
  const odd = A.normalizeMark({ path: P, qual: "x", state: "todo", hash: "bad hash!", commit: "zz", start: -4, end: 1.5, note: "n".repeat(500), at: "garbage" });
  assert.deepEqual([odd.hash, odd.commit, odd.start, odd.end, odd.note.length, odd.at], ["", "", 0, 0, 200, "1970-01-01T00:00:00.000Z"]);
});

t("auditStatus: none / todo / reviewed / rereview / concern / gone / unverified", () => {
  const m = (state, hash = "h1") => ({ state, hash });
  assert.equal(A.auditStatus(null, "h1").status, "none");
  assert.equal(A.auditStatus(m("todo"), "h1").status, "todo");
  assert.equal(A.auditStatus(m("reviewed"), "h1").status, "reviewed");
  assert.equal(A.auditStatus(m("reviewed"), "h1").unverified, false);
  const re = A.auditStatus(m("reviewed"), "h2"); assert.deepEqual([re.status, re.changed], ["rereview", true]);
  const c = A.auditStatus(m("concern"), "h2"); assert.deepEqual([c.status, c.changed], ["concern", true]);
  const un = A.auditStatus(m("reviewed"), undefined); assert.deepEqual([un.status, un.unverified], ["reviewed", true]);
  assert.equal(A.auditStatus(m("reviewed", ""), "h2").unverified, true, "a mark without a hash can not be compared");
  assert.equal(A.auditStatus(m("reviewed"), "").status, "reviewed", "a symbol with no census hash is not called changed");
  assert.equal(A.auditStatus(m("reviewed"), null).status, "gone");
});

t("set / toggle: the key of the current state clears it, another key switches, r renews a stale review", () => {
  const a = mk();
  assert.equal(a.toggle(P, "route", "reviewed", { hash: "h1", commit: "c".repeat(40), start: 5, end: 9 }), "set");
  assert.equal(a.get(P, "route").hash, "h1");
  assert.equal(a.toggle(P, "route", "concern", { hash: "h1" }), "set");
  assert.equal(a.get(P, "route").state, "concern");
  assert.equal(a.toggle(P, "route", "concern", { hash: "h1" }), "cleared");
  assert.equal(a.get(P, "route"), null);
  a.toggle(P, "route", "reviewed", { hash: "h1" });
  a.observe(P, [{ qual: "route", hash: "h2" }]);
  assert.equal(a.statusOf(P, "route").status, "rereview");
  assert.equal(a.toggle(P, "route", "reviewed", { hash: "h2" }), "renewed");
  assert.deepEqual([a.statusOf(P, "route").status, a.get(P, "route").hash], ["reviewed", "h2"]);
  assert.equal(a.toggle(P, "route", "reviewed", { hash: "h2" }), "cleared");
  assert.throws(() => a.set(P, "x", "bogus"), RangeError);
});

t("a changed hash resets a review (needs re-review) but keeps the mark; a concern survives a change", () => {
  const a = mk();
  a.set(P, "f", "reviewed", { hash: "old" }); a.set(P, "g", "concern", { hash: "old", note: "leaks" }); a.set(P, "h", "reviewed", { hash: "same" });
  a.observe(P, [{ qual: "f", hash: "new" }, { qual: "g", hash: "new" }, { qual: "h", hash: "same" }]);
  assert.deepEqual(["f", "g", "h"].map((q) => a.statusOf(P, q).status), ["rereview", "concern", "reviewed"]);
  assert.equal(a.statusOf(P, "g").changed, true);
  const p = a.fileProgress(P, 10);
  assert.deepEqual([p.reviewed, p.rereview, p.concern, p.marked, p.total], [1, 1, 1, 3, 10]);
});

t("observe: marks whose symbol is missing become gone; hooks fire only when a status moved", () => {
  const a = mk(); let fired = 0; a.on(() => { fired++; });
  a.set(P, "f", "reviewed", { hash: "h" }); a.set(P, "gone", "todo", {});
  fired = 0;
  a.observe(P, [{ qual: "f", hash: "h" }]);
  assert.equal(a.statusOf(P, "gone").status, "gone"); assert.equal(fired, 1);
  fired = 0; a.observe(P, [{ qual: "f", hash: "h" }]); assert.equal(fired, 0, "same answer, no event");
  a.observe("other.py", []); assert.equal(fired, 0);
});

t("setNote keeps the hash (a comment is not a re-read) and needs an existing mark", () => {
  const a = mk();
  assert.equal(a.setNote(P, "f", "x"), null);
  a.set(P, "f", "reviewed", { hash: "h1" });
  a.setNote(P, "f", "  checked the\nretry path  ");
  assert.deepEqual([a.get(P, "f").note, a.get(P, "f").hash], ["checked the retry path", "h1"]);
});

t("progress adds up per file, per folder and overall", () => {
  const a = mk();
  a.set("backend/eo/a.py", "f", "reviewed", { hash: "1" }); a.set("backend/eo/a.py", "g", "todo", {}); a.set("backend/api/b.py", "h", "concern", {});
  assert.equal(a.fileProgress("backend/eo/a.py", 4).marked, 2);
  const d = a.dirProgress("backend", 50); assert.deepEqual([d.marked, d.reviewed, d.todo, d.concern, d.total], [3, 1, 1, 1, 50]);
  assert.equal(a.dirProgress("backend/eo", 9).marked, 2);
  assert.equal(a.dirProgress("frontend", 9), null);
  assert.equal(a.totals(100).marked, 3);
  assert.equal(mk().totals(100).marked, 0);
  assert.equal(a.totals(100).unchecked, 1, "the one review is not yet compared with the census");
});

t("marks survive a reload and a second tab can pick them up", () => {
  const st = memStorage(); const a = mk(st);
  a.set(P, "f", "reviewed", { hash: "h", note: "ok" });
  const b = mk(st); assert.deepEqual([b.get(P, "f").state, b.get(P, "f").note], ["reviewed", "ok"]);
  b.set(P, "g", "todo", {}); a.reload(); assert.equal(a.get(P, "g").state, "todo");
  assert.ok(a.persistent);
  assert.ok(JSON.parse(st.m[A.KEY_AUDIT]).marks.length === 2);
});

t("storage that refuses to write or to read never throws; persistent says so", () => {
  const bad = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("quota"); } };
  const a = A.createAudit({ storage: bad, now }); a.set(P, "f", "todo", {});
  assert.equal(a.get(P, "f").state, "todo"); assert.equal(a.persistent, false);
  const none = A.createAudit({ storage: null, now }); none.set(P, "f", "todo", {}); assert.equal(none.size(), 1);
  const junk = A.createAudit({ storage: memStorage({ [A.KEY_AUDIT]: "{not json" }), now }); assert.equal(junk.size(), 0);
  const half = A.createAudit({ storage: memStorage({ [A.KEY_AUDIT]: JSON.stringify({ v: 1, marks: [{ path: P, qual: "f", state: "todo" }, { path: 3 }, null] }) }), now }); assert.equal(half.size(), 1);
});

t("export / import round trip; newest wins; invalid skipped; hostile input is harmless", () => {
  const a = mk(); a.set(P, "f", "reviewed", { hash: "h", commit: "a".repeat(40), start: 1, end: 4 }); a.set(P, "g", "concern", { note: "x" });
  const doc = a.exportDoc({ commit: "a".repeat(40) });
  assert.deepEqual([doc.v, doc.app, doc.marks.length], [1, "minime-atlas-audit", 2]);
  const b = mk(); const r = b.importDoc(JSON.stringify(doc)); assert.deepEqual([r.ok, r.added, r.invalid], [true, 2, 0]);
  assert.deepEqual(b.exportDoc().marks, doc.marks);
  const again = b.importDoc(JSON.stringify(doc)); assert.deepEqual([again.same, again.added], [2, 0]);
  const fMark = doc.marks.find((x) => x.qual === "f");
  const older = b.importDoc(JSON.stringify([{ ...fMark, state: "todo", at: "2020-01-01T00:00:00Z" }])); assert.equal(older.older, 1); assert.equal(b.get(P, "f").state, "reviewed");
  const newer = b.importDoc(JSON.stringify([{ ...fMark, state: "todo", at: "2099-01-01T00:00:00Z" }])); assert.equal(newer.updated, 1); assert.equal(b.get(P, "f").state, "todo");
  assert.equal(b.importDoc("{nope").ok, false); assert.equal(b.importDoc("{}").ok, false); assert.equal(b.importDoc(JSON.stringify({ v: 9, marks: [] })).ok, false);
  assert.equal(b.importDoc("x".repeat(A.LIMITS.file + 1)).ok, false);
  const bad = b.importDoc(`{"marks":[{"path":"__proto__","qual":"constructor","state":"todo"},{"path":"a::b","qual":"c","state":"todo"},7,{"path":"p.py","qual":"q","state":"evil"}]}`);
  assert.deepEqual([bad.added, bad.invalid], [1, 3]); assert.equal(({}).polluted, undefined);
});

t("concernsMarkdown: one checkbox per concern with lines, note, permalink; empty case", () => {
  const e = [{ mark: A.normalizeMark({ path: P, qual: "route", state: "concern", note: "swallows `errors`", start: 10, end: 20 }), changed: true }];
  const md = A.concernsMarkdown(e, { commit: "a".repeat(40), date: "2026-11-18", link: (m) => `https://example.test/${m.path}#L${m.start}` });
  assert.match(md, /^## Audit concerns/); assert.match(md, /MiniMe census commit aaaaaaa · 2026-11-18 · 1 concern/);
  assert.match(md, /- \[ \] `backend\/eo\/router\.py::route` \(lines 10–20\): swallows `errors`.*code has changed/);
  assert.match(md, /\n  - https:\/\/example\.test\/backend\/eo\/router\.py#L10\n/);
  assert.match(A.concernsMarkdown([]), /No concerns flagged/);
  assert.ok(!A.concernsMarkdown([{ mark: A.normalizeMark({ path: "a`b.py", qual: "q", state: "concern" }), changed: false }]).includes("a`b"), "backticks in a path can not break out of the code span");
});

t("nextToReview: by line, wraps round, skips reviewed and concerns, null when nothing is left", () => {
  const rows = [{ qual: "a", start: 1 }, { qual: "b", start: 10 }, { qual: "c", start: 20 }, { qual: "d", start: 30 }];
  const st = { a: "reviewed", b: "none", c: "reviewed", d: "rereview" };
  const f = (r) => ({ status: st[r.qual] });
  assert.equal(A.nextToReview(rows, "a", f).qual, "b");
  assert.equal(A.nextToReview(rows, "b", f).qual, "d");
  assert.equal(A.nextToReview(rows, "d", f).qual, "b", "wraps round");
  assert.equal(A.nextToReview(rows, "", f).qual, "b");
  assert.equal(A.nextToReview(rows, "a", () => ({ status: "reviewed" })), null);
  assert.equal(A.nextToReview(rows, "a", (r) => ({ status: r.qual === "c" ? "concern" : "reviewed" })), null);
});

t("auditFilterMatch", () => {
  assert.ok(A.auditFilterMatch("open", "none") && A.auditFilterMatch("open", "rereview") && !A.auditFilterMatch("open", "reviewed") && !A.auditFilterMatch("open", "concern"));
  assert.ok(A.auditFilterMatch("all", "gone") && A.auditFilterMatch("concern", "concern") && !A.auditFilterMatch("concern", "todo"));
});

/* ---------------------------------------------------------------- shared mode */
function fakeSync() {
  const ents = {}; const h = { change: [], status: [] }; let t0 = 0;
  const S = {
    status: "live", started: 0, puts: [],
    on: (ev, fn) => h[ev].push(fn),
    list: (k) => Object.keys(ents).filter((x) => x.startsWith(`${k}:`)).map((x) => ents[x]),
    start() { S.started++; },
    put(kind, v) { v.updatedAt = new Date(Date.UTC(2026, 11, 1, 0, 0, t0++)).toISOString(); ents[`${kind}:${v.id}`] = v; S.puts.push([kind, JSON.parse(JSON.stringify(v))]); h.change.forEach((f) => f()); return v; },
    ents,
  };
  return S;
}

t("shared mode: records are kind audit with a hashed id and path/qual inside; clear is a tombstone", () => {
  const st = memStorage(); const a = mk(st); const S = fakeSync();
  a.useShared(S);
  assert.equal(a.mode, "shared"); assert.equal(st.m[A.KEY_MODE], "shared"); assert.equal(S.started, 1);
  a.toggle(P, "route", "reviewed", { hash: "h1", commit: "b".repeat(40) });
  const [kind, rec] = S.puts[0];
  assert.equal(kind, "audit"); assert.equal(rec.id, A.auditId(P, "route")); assert.deepEqual([rec.path, rec.qual, rec.state, rec.hash], [P, "route", "reviewed", "h1"]);
  assert.ok(/^[A-Za-z0-9_.-]{1,64}$/.test(rec.id));
  assert.equal(a.get(P, "route").state, "reviewed");
  a.toggle(P, "route", "reviewed", { hash: "h1" });
  assert.equal(S.puts[1][1].deleted, true); assert.equal(a.get(P, "route"), null);
  assert.equal(JSON.parse(st.m[A.KEY_AUDIT] || '{"marks":[]}').marks.length, 0, "nothing is written to the local store in shared mode");
});

t("shared mode: a teammate's record shows up on a change event; a record with a wrong id is ignored", () => {
  const a = mk(); const S = fakeSync(); a.useShared(S); let fired = 0; a.on(() => { fired++; });
  S.put("audit", { id: A.auditId("x.py", "f"), path: "x.py", qual: "f", state: "concern", note: "hm", hash: "h" });
  assert.equal(a.get("x.py", "f").state, "concern"); assert.ok(fired > 0);
  S.put("audit", { id: "a0000000000000", path: "y.py", qual: "g", state: "todo" });
  assert.equal(a.get("y.py", "g"), null);
  S.put("audit", { id: A.auditId("z.py", "h"), path: "z.py", qual: "h", deleted: true });
  assert.equal(a.get("z.py", "h"), null);
});

t("switching to shared never touches local marks; uploadLocal sends only missing or newer ones; back to local works", () => {
  const st = memStorage(); const a = mk(st); a.set(P, "f", "reviewed", { hash: "h" }); a.set(P, "g", "todo", {});
  const S = fakeSync();
  S.put("audit", { id: A.auditId(P, "g"), path: P, qual: "g", state: "concern" });       // the team already has a newer g
  S.puts.length = 0;
  a.useShared(S);
  assert.equal(a.size(), 1, "shared view starts with the team's marks only"); assert.equal(a.localSize(), 2);
  assert.equal(a.uploadLocal(), 1); assert.deepEqual(S.puts.map((p) => p[1].qual), ["f"]);
  assert.equal(a.get(P, "g").state, "concern");
  a.useLocal(); assert.equal(a.mode, "local"); assert.equal(a.get(P, "g").state, "todo"); assert.equal(st.m[A.KEY_MODE], "local");
  assert.equal(mk(memStorage()).wantsShared(), false); assert.equal(mk(memStorage({ [A.KEY_MODE]: "shared" })).wantsShared(), true);
});

console.log(`${n} ran`);
