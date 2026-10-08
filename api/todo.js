/*
  Shared storage for the team to-do and the master timeline dates.

  - Runs as a Vercel serverless function at /api/todo (no npm packages needed).
  - Stores everything in a hosted Redis (Upstash) through its REST API.
  - NO AUTH on purpose: anyone who has the site link can read and edit, so the team
    can fix each other's work. Writes are rate limited and size limited.

  Data model: one Redis hash, field "<kind>:<id>" -> JSON.
  kinds: person, project, task, master, settings.
  Conflicts: per record, the newest updatedAt wins (a stale write is rejected, and the
  client then adopts the newer record). Deletes are tombstones ({deleted:true}), so
  nothing is ever really lost. Each day the first read or write also stores a snapshot
  of the whole list (kept 35 days).
*/

const P = 'minime:todo:v1:';
const KINDS = new Set(['person', 'project', 'task', 'master', 'settings']);
const ID_RE = /^[A-Za-z0-9_.-]{1,64}$/;
const LIMITS = { body: 1500000, ops: 200, entity: 40000, feedKeep: 200, feedSend: 60, perMinute: 150, snapDays: 35 };

// Atomic "write if not older" for a batch of records. Returns [rev, appliedField...]
// ARGV: n, seedFlag, then (field, updatedAt, json) triples. In seed mode nothing existing is overwritten.
const LUA = `
local n=tonumber(ARGV[1]); local seed=(ARGV[2]=='1'); local applied={}
for i=0,n-1 do
  local f=ARGV[3+i*3]; local ts=ARGV[4+i*3]; local val=ARGV[5+i*3]
  local cur=redis.call('HGET',KEYS[1],f); local ok=true
  if cur then
    if seed then ok=false else
      local good,obj=pcall(cjson.decode,cur)
      if good and type(obj)=='table' and type(obj.updatedAt)=='string' and obj.updatedAt>ts then ok=false end
    end
  end
  if ok then redis.call('HSET',KEYS[1],f,val); applied[#applied+1]=f end
end
if #applied>0 then redis.call('INCR',KEYS[2]) end
local out={ redis.call('GET',KEYS[2]) or '0' }
for i=1,#applied do out[#out+1]=applied[i] end
return out`;

// Vercel Marketplace (Upstash) sets KV_REST_API_*; a database made at upstash.com sets
// UPSTASH_REDIS_REST_*. A custom prefix on the integration is handled too.
function creds() {
  const e = process.env;
  for (const k of Object.keys(e)) {
    const m = k.match(/^(.*)(KV_REST_API_URL|UPSTASH_REDIS_REST_URL)$/);
    if (!m || !e[k]) continue;
    const token = e[m[1] + (m[2].startsWith('KV') ? 'KV_REST_API_TOKEN' : 'UPSTASH_REDIS_REST_TOKEN')];
    if (token) return { url: e[k].replace(/\/+$/, ''), token };
  }
  return null;
}

async function call(c, path, body) {
  const r = await fetch(c.url + path, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + c.token, 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || 'redis http ' + r.status);
  return j;
}
async function cmd(c, command) {
  const j = await call(c, '', command);
  if (j.error) throw new Error(j.error);
  return j.result;
}
async function pipe(c, commands) {
  const list = await call(c, '/pipeline', commands);
  return list.map(x => { if (x.error) throw new Error(x.error); return x.result; });
}

const send = (res, code, obj) => { res.statusCode = code; res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(obj)); };
const parse = s => { try { return JSON.parse(s); } catch (e) { return null; } };
const clean = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u001f]/g, ' ').slice(0, n);

function queryOf(req) {
  if (req.query && typeof req.query === 'object') return req.query;
  return Object.fromEntries(new URL(req.url, 'http://x').searchParams);
}

// HGETALL comes back as a flat list [field, value, ...] (or an object on some clients).
function entsOf(all) {
  const flat = Array.isArray(all) ? all : Object.entries(all || {}).flat();
  const ents = [];
  for (let i = 0; i + 1 < flat.length; i += 2) {
    const v = parse(flat[i + 1]);
    if (v && typeof v === 'object') ents.push({ key: flat[i], v });
  }
  return ents;
}

// Store today's snapshot once. Called before the first change of the day, so the snapshot
// is "how it looked before today's edits", and on the first full read of the day.
async function snapshot(c) {
  const day = new Date().toISOString().slice(0, 10);
  const [has] = await pipe(c, [['EXISTS', P + 'snap:' + day]]);
  if (has) return;
  const [all] = await pipe(c, [['HGETALL', P + 'data']]);
  const ents = entsOf(all);
  if (ents.length) await cmd(c, ['SET', P + 'snap:' + day, JSON.stringify(ents), 'NX', 'EX', String(LIMITS.snapDays * 86400)]);
}

async function read(req, res, c) {
  const q = queryOf(req);

  if (q.snap) {
    const pre = P + 'snap:';
    if (q.snap === 'list') {
      const keys = (await cmd(c, ['KEYS', pre + '*'])) || [];
      return send(res, 200, { snaps: keys.map(k => k.slice(pre.length)).sort().reverse() });
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(q.snap)) return send(res, 400, { error: 'bad_date' });
    const raw = await cmd(c, ['GET', pre + q.snap]);
    if (!raw) return send(res, 404, { error: 'no_snapshot' });
    return send(res, 200, { date: q.snap, ents: parse(raw) || [] });
  }

  // Cheap check first: one command when nothing changed.
  const have = q.rev == null ? '' : String(q.rev);
  const [rev] = await pipe(c, [['GET', P + 'rev']]);
  const cur = rev == null ? '0' : String(rev);
  if (have === cur && !q.full) return send(res, 200, { rev: cur, changed: false });

  const day = new Date().toISOString().slice(0, 10);
  const [rev2, all, feed, hasSnap] = await pipe(c, [
    ['GET', P + 'rev'], ['HGETALL', P + 'data'], ['LRANGE', P + 'feed', 0, LIMITS.feedSend - 1], ['EXISTS', P + 'snap:' + day]
  ]);
  const ents = entsOf(all);
  if (!hasSnap && ents.length) {
    cmd(c, ['SET', P + 'snap:' + day, JSON.stringify(ents), 'NX', 'EX', String(LIMITS.snapDays * 86400)]).catch(() => {});
  }
  return send(res, 200, { rev: rev2 == null ? '0' : String(rev2), changed: true, ents, feed: (feed || []).map(parse).filter(Boolean) });
}

async function write(req, res, c) {
  let body = req.body;
  if (typeof body === 'string') body = parse(body);
  if (!body || typeof body !== 'object' || !Array.isArray(body.ops)) return send(res, 400, { error: 'bad_body' });
  if (body.ops.length > LIMITS.ops) return send(res, 413, { error: 'too_many_ops' });

  const nowIso = new Date().toISOString();
  const soon = Date.now() + 5 * 60000;
  const args = [];
  const fields = [];
  const seen = new Set();
  for (const op of body.ops) {
    if (!op || !KINDS.has(op.k) || !ID_RE.test(String(op.id)) || !op.v || typeof op.v !== 'object' || Array.isArray(op.v)) {
      return send(res, 400, { error: 'bad_op' });
    }
    const v = { ...op.v, id: String(op.id) };
    // One canonical timestamp format, so plain string comparison orders records correctly.
    let ms = Date.parse(v.updatedAt);
    if (isNaN(ms) || ms > soon) ms = Date.now();    // a wrong device clock must not win forever
    v.updatedAt = new Date(ms).toISOString();
    const val = JSON.stringify(v);
    if (val.length > LIMITS.entity) return send(res, 413, { error: 'entity_too_big' });
    const field = op.k + ':' + v.id;
    if (seen.has(field)) continue;
    seen.add(field);
    fields.push(field);
    args.push(field, v.updatedAt, val);
  }

  // Soft rate limit per IP (the site has no logins, so this is the only brake).
  const ip = clean((req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown', 64);
  const rk = P + 'rl:' + ip + ':' + Math.floor(Date.now() / 60000);
  const [hits] = await pipe(c, [['INCR', rk], ['EXPIRE', rk, 120]]);
  if (hits > LIMITS.perMinute) return send(res, 429, { error: 'slow_down' });

  let rev = '0', applied = [];
  if (fields.length) {
    await snapshot(c).catch(() => {});
    const out = await cmd(c, ['EVAL', LUA, 2, P + 'data', P + 'rev', String(fields.length), body.seed ? '1' : '0', ...args]);
    rev = String(out[0]);
    applied = out.slice(1);
  } else {
    const [r] = await pipe(c, [['GET', P + 'rev']]);
    rev = r == null ? '0' : String(r);
  }
  const rejected = fields.filter(f => !applied.includes(f));

  const feed = (Array.isArray(body.feed) ? body.feed : []).slice(0, 20)
    .map(f => ({ at: nowIso, by: clean(f && f.by, 40), text: clean(f && f.text, 200) }))
    .filter(f => f.text);
  if (feed.length) {
    await pipe(c, [['LPUSH', P + 'feed', ...feed.map(f => JSON.stringify(f))], ['LTRIM', P + 'feed', 0, LIMITS.feedKeep - 1]]);
  }
  return send(res, 200, { rev, applied, rejected });
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  const c = creds();
  if (!c) return send(res, 503, { error: 'not_configured' });
  try {
    if (req.method === 'GET') return await read(req, res, c);
    if (req.method === 'POST') {
      const len = Number(req.headers['content-length'] || 0);
      if (len > LIMITS.body) return send(res, 413, { error: 'too_big' });
      return await write(req, res, c);
    }
    res.setHeader('Allow', 'GET, POST');
    return send(res, 405, { error: 'method' });
  } catch (e) {
    console.error('todo api:', e);
    return send(res, 502, { error: 'storage', detail: clean(e && e.message, 200) });
  }
};
