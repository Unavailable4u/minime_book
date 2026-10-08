/*
  Live sync client shared by todo.html and roadmap.html. Talks to /api/todo.

  - Local cache in localStorage, so the pages open instantly and keep working offline.
  - Every change is pushed in the background; others see it within a few seconds.
  - Per record, the newest updatedAt wins. Deletes are tombstones ({deleted:true}).
  - Polling is cheap: one tiny request that only asks "has the revision changed?".
    It slows down when you are idle and pauses while the tab is hidden.
*/
(function (root) {
  'use strict';
  const API = 'api/todo', KEY = 'minime_sync_v2';
  const iso = () => new Date().toISOString();
  const H = { change: [], status: [] };
  const emit = ev => H[ev].forEach(fn => { try { fn(); } catch (e) { console.error(e); } });

  function load() {
    try { const c = JSON.parse(localStorage.getItem(KEY)); if (c && c.ents) return { rev: c.rev == null ? null : c.rev, ents: c.ents, dirty: c.dirty || {}, pend: c.pend || [], feed: c.feed || [], seeding: !!c.seeding }; } catch (e) {}
    return { rev: null, ents: {}, dirty: {}, pend: [], feed: [], seeding: false };
  }
  let C = load(), inflight = false, pulling = false, pollT = 0, pushT = 0, failN = 0, lastAct = Date.now();

  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(C)); } catch (e) { /* quota: keep working in memory */ } };
  const kindOf = key => key.slice(0, key.indexOf(':'));

  const Sync = {
    status: 'connecting',          // connecting | live | saving | offline | nobackend
    lastOk: 0,                     // ms timestamp of the last successful exchange
    remoteEmpty: null,             // true when the shared database has no data yet
    me: (function () { try { return localStorage.getItem('minime_todo_me') || ''; } catch (e) { return ''; } })(),

    on(ev, fn) { H[ev].push(fn); },
    list(kind) { const p = kind + ':'; return Object.keys(C.ents).filter(k => k.startsWith(p)).map(k => C.ents[k]); },
    get(kind, id) { return C.ents[kind + ':' + id] || null; },
    feed() { return C.feed; },
    pending() { return Object.keys(C.dirty).length; },
    setMe(id) { Sync.me = id || ''; try { localStorage.setItem('minime_todo_me', Sync.me); } catch (e) {} },

    // Create or update a record. `text` (optional) goes to the shared activity feed.
    put(kind, v, text) {
      v.id = v.id || ('x' + Math.random().toString(36).slice(2, 9));
      v.updatedAt = iso();
      v.updatedBy = Sync.me;
      const key = kind + ':' + v.id;
      C.ents[key] = v; C.dirty[key] = 1;
      if (text) C.pend.push({ by: Sync.me, text });
      save(); emit('change'); schedulePush(300);
      return v;
    },

    // First-run only: upload starter data without overwriting anything that already exists.
    seed(list) {
      const t = iso();
      for (const { k, v } of list) { v.updatedAt = v.updatedAt || t; C.ents[k + ':' + v.id] = v; C.dirty[k + ':' + v.id] = 1; }
      C.seeding = true; save(); emit('change'); schedulePush(0);
    },

    refresh() { failN = 0; return pull(true).then(() => push()); },
    flush() { return push(); },

    async snapshots() {
      const r = await fetch(API + '?snap=list', { cache: 'no-store' });
      if (!r.ok) throw new Error('no backend');
      return (await r.json()).snaps || [];
    },
    async snapshot(date) {
      const r = await fetch(API + '?snap=' + encodeURIComponent(date), { cache: 'no-store' });
      if (!r.ok) throw new Error('missing');
      return (await r.json()).ents || [];
    },

    start() { if (!Sync.ready) Sync.ready = pull(false).then(() => { loop(); }); return Sync.ready; }
  };

  function setStatus(s) { if (Sync.status !== s) { Sync.status = s; emit('status'); } }

  // ---------- pull ----------
  async function pull(force) {
    if (pulling) return;
    pulling = true;
    try {
      const qs = [];
      if (C.rev != null) qs.push('rev=' + encodeURIComponent(C.rev));
      if (force) qs.push('full=1');
      const r = await fetch(API + (qs.length ? '?' + qs.join('&') : ''), { cache: 'no-store' });
      const isJson = (r.headers.get('content-type') || '').includes('json');
      // 503 = function exists but no database linked; 404 / HTML = site served without the function.
      if (r.status === 503 || r.status === 404 || (r.ok && !isJson)) { setStatus('nobackend'); return; }
      if (!r.ok || !isJson) throw new Error('http ' + r.status);
      const j = await r.json();
      failN = 0; Sync.lastOk = Date.now();
      if (j.changed) {
        Sync.remoteEmpty = j.ents.length === 0;
        merge(j.ents);
        C.rev = j.rev; C.feed = j.feed || [];
        save(); emit('change');
      } else if (C.rev == null) { C.rev = j.rev; }
      setStatus(Sync.pending() ? 'saving' : 'live');
    } catch (e) {
      failN++; setStatus('offline');
    } finally { pulling = false; }
  }

  function merge(ents) {
    const seen = new Set();
    for (const { key, v } of ents) {
      seen.add(key);
      const cur = C.ents[key];
      if (C.dirty[key]) {
        // I have an unsent edit: keep it unless the server copy is newer.
        if (cur && (v.updatedAt || '') > (cur.updatedAt || '')) { C.ents[key] = v; delete C.dirty[key]; }
      } else C.ents[key] = v;
    }
    if (!ents.length) { for (const k of Object.keys(C.ents)) C.dirty[k] = 1; return; } // database was reset: re-upload what we have
    const old = Date.now() - 60000;
    for (const k of Object.keys(C.ents)) {
      if (!seen.has(k) && !C.dirty[k] && Date.parse(C.ents[k].updatedAt || 0) < old) delete C.ents[k];
    }
  }

  // ---------- push ----------
  function schedulePush(ms) { clearTimeout(pushT); pushT = setTimeout(push, ms); }

  function body(keys, feed) {
    return { ops: keys.filter(k => C.ents[k]).map(k => ({ k: kindOf(k), id: C.ents[k].id, v: C.ents[k] })), feed, seed: !!C.seeding };
  }

  async function push() {
    const keys = Object.keys(C.dirty).slice(0, 100);
    if (inflight || (!keys.length && !C.pend.length)) return;
    if (Sync.status === 'nobackend') return;
    inflight = true; setStatus('saving');
    const feed = C.pend.splice(0, 20);
    const stamps = {}; keys.forEach(k => { stamps[k] = C.ents[k] && C.ents[k].updatedAt; });
    const seeding = !!C.seeding;
    try {
      const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body(keys, feed)) });
      if (r.status === 503 || r.status === 404) { C.pend.unshift(...feed); setStatus('nobackend'); return; }
      if (r.status === 429) throw new Error('slow down');
      if (!r.ok) throw new Error('http ' + r.status);
      const j = await r.json();
      for (const k of keys) if (!C.ents[k] || C.ents[k].updatedAt === stamps[k]) delete C.dirty[k];
      if (seeding && !Object.keys(C.dirty).length) C.seeding = false;
      failN = 0; Sync.lastOk = Date.now(); save();
      if (j.rejected && j.rejected.length) await pull(true); // a teammate's newer version exists: adopt it
      setStatus(Object.keys(C.dirty).length ? 'saving' : 'live');
    } catch (e) {
      C.pend.unshift(...feed); failN++; setStatus('offline'); save();
      schedulePush(Math.min(60000, 4000 * 2 ** Math.min(failN, 4)));
    } finally {
      inflight = false;
      if (Object.keys(C.dirty).length || C.pend.length) { if (Sync.status !== 'offline' && Sync.status !== 'nobackend') schedulePush(200); }
    }
  }

  // ---------- polling loop ----------
  function delay() {
    if (Sync.status === 'nobackend') return 120000;
    if (failN) return Math.min(60000, 5000 * 2 ** Math.min(failN, 4));
    return Date.now() - lastAct < 60000 ? 5000 : 20000;
  }
  function loop() {
    clearTimeout(pollT);
    if (typeof document !== 'undefined' && document.hidden) return;
    pollT = setTimeout(async () => { await pull(false); await push(); loop(); }, delay());
  }
  if (typeof window !== 'undefined') {
    ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach(ev => window.addEventListener(ev, () => { lastAct = Date.now(); }, { passive: true }));
    document.addEventListener('visibilitychange', () => { if (!document.hidden) { failN = 0; pull(false).then(() => { push(); loop(); }); } });
    window.addEventListener('online', () => { failN = 0; Sync.refresh().then(loop); });
    window.addEventListener('storage', e => { if (e.key === KEY) { C = load(); emit('change'); } });
    // Last chance to save an edit made just before closing the tab.
    window.addEventListener('pagehide', () => {
      const keys = Object.keys(C.dirty);
      if ((!keys.length && !C.pend.length) || Sync.status === 'nobackend' || !navigator.sendBeacon) return;
      navigator.sendBeacon(API, new Blob([JSON.stringify(body(keys.slice(0, 100), C.pend.slice(0, 20)))], { type: 'application/json' }));
    });
  }

  root.Sync = Sync;
})(typeof window !== 'undefined' ? window : globalThis);
