/*
  Master plan view for todo.html: the whole Roadmap timeline, inside the to-do page.

  Shows every master item (planned bar, your actual dates, phases of the two products,
  how many workstreams run at once), the plan-vs-actual summary, the editable date table,
  and the Pathways and gates map. Team projects linked to a master item add a blue bar
  (span of their tasks) and a "Team work" column, so plan and daily work are one picture.

  Depends on helpers defined by todo.html (mrow, mStatus, linkedTasks, projs, live, stateOf,
  mi, lab, esc, today, pl, ...). They are only looked up when a function runs, so script order
  does not matter as long as todo.html has finished loading.
*/
(function (root) {
  'use strict';
  const W = 1180, LW = 300, RH = 26, HH = 26;
  const E = s => esc(s);

  // Fractional month index of a date, same scale as mi() (month m of year y starts at y*12+m).
  function fIdx(s) {
    const [y, m, d] = s.split('-').map(Number), dim = new Date(y, m, 0).getDate();
    return y * 12 + m + (d - 1) / dim;
  }
  const ymOf = i => { const t = i - 1; return Math.floor(t / 12) + '-' + String(t % 12 + 1).padStart(2, '0'); };

  function rows() {
    const out = [], all = (root.MASTER_R || []).map(mrow), by = Object.fromEntries(all.map(r => [r.id, r]));
    let lane = null;
    for (const r of all) {
      if (r.lane !== lane) { out.push({ head: r.lane }); lane = r.lane; }
      if (r.derived) {
        const p = by[r.derived[0]];
        if (!p || !p.Ps) continue;
        const a = mi(p.Ps), d = mi(p.Pe) + 1 - a;
        r._a = a + r.derived[1] * d; r._b = a + r.derived[2] * d;
      }
      out.push(r);
    }
    return out;
  }

  const isLate = r => (r.Ae && mi(r.Ae) > mi(r.Pe)) || (r.kind !== 'bar' && r.As && mi(r.As) > mi(r.Ps));
  const isOk = r => (r.Ae && mi(r.Ae) <= mi(r.Pe)) || (r.kind !== 'bar' && r.As && mi(r.As) <= mi(r.Ps));

  function slip(r) {
    const sl = (d, w) => d === 0 ? `<span style="color:#34d399">${w} on time</span>` : d > 0 ? `<span style="color:#ff6b86">${w} ${d} mo late</span>` : `<span style="color:#34d399">${w} ${-d} mo early</span>`;
    if (!r.As && !r.Ae) return '<span class="dim">no actual yet</span>';
    if (r.kind !== 'bar') return sl(mi(r.As) - mi(r.Ps), 'date');
    if (!r.Ae) return '<span style="color:#f59e0b">in progress since ' + lab(r.As) + '</span>';
    return sl(mi(r.Ae) - mi(r.Pe), 'finish');
  }

  function build() {
    const list = rows(), acts = list.filter(r => !r.head && !r.derived);
    const t0 = today(), ti = fIdx(t0);
    let m0 = Math.floor(ti), m1 = Math.ceil(ti) + 1;
    for (const r of acts) {
      for (const s of [r.Ps, r.As]) if (s) m0 = Math.min(m0, mi(s));
      for (const s of [r.Pe || r.Ps, r.Ae || r.As || r.Ps]) if (s) m1 = Math.max(m1, mi(s) + 1);
    }
    if (m1 - m0 < 12) m1 = m0 + 12;
    const N = m1 - m0, mw = (W - LW) / N, X = i => LW + (i - m0) * mw;
    const H = 40 + list.reduce((a, r) => a + (r.head ? HH : RH), 0);
    const lk = Object.fromEntries(acts.map(r => [r.id, linkedTasks(r.id)]));

    let g = `<svg viewBox="0 0 ${W} ${H + 150}" width="100%" style="display:block;min-width:900px" xmlns="http://www.w3.org/2000/svg" font-family="Sora,Inter,system-ui,sans-serif">`
      + `<defs><pattern id="mlate" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="8" fill="#f59e0b"/><rect x="4" width="4" height="8" fill="#92400e"/></pattern>`
      + `<pattern id="mfail" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="8" fill="#ff2052"/><rect x="4" width="4" height="8" fill="#7f1d1d"/></pattern></defs>`;
    // year lines and quarter lines
    for (let i = m0; i <= m1; i++) {
      const month = (i - 1) % 12 + 1, x = X(i);
      if (month === 1 && i > m0) g += `<line x1="${x}" x2="${x}" y1="20" y2="${H}" stroke="#2a2a33"/>`;
      else if ((month - 1) % 3 === 0 && i < m1) g += `<line x1="${x}" x2="${x}" y1="22" y2="${H}" stroke="#17171d"/>`;
      if (month === 1 || i === m0) g += `<text x="${x + 6}" y="14" fill="#a8a6a0" font-size="12">${ymOf(i).slice(0, 4)}</text>`;
      if (N <= 30 && i < m1) g += `<text x="${x + mw / 2}" y="31" fill="#6d6b66" font-size="9" text-anchor="middle">${MN[month - 1]}</text>`;
    }
    const wl = Array(N).fill(0), wa = Array(N).fill(0), isW = r => !r.head && r.kind === 'bar' && !r.derived && /Tech|Research|Products/.test(r.lane);
    let y = 34;
    for (const r of list) {
      if (r.head) {
        g += `<rect x="0" y="${y}" width="${W}" height="${HH - 4}" fill="#17171d"/><text x="8" y="${y + 15}" fill="#ff7a96" font-size="11" font-weight="700" letter-spacing=".06em">${E(r.head.toUpperCase())}</text>`;
        y += HH; continue;
      }
      const ty = y + RH / 2 + 4, lbl = r.label.trim();
      g += `<g class="mr" ${r.derived ? '' : `onclick="editMaster('${r.id}')" style="cursor:pointer"`}><rect x="0" y="${y}" width="${W}" height="${RH}" fill="transparent"/>`
        + `<text x="${LW - 12}" y="${ty}" fill="${r.derived ? '#a8a6a0' : '#e8e6e0'}" font-size="${r.derived ? 11 : 12}" text-anchor="end">${E(lbl.length > 46 ? lbl.slice(0, 45) + '…' : lbl)}</text>`;
      let a, b;
      if (r.derived) { a = r._a; b = r._b; } else { a = mi(r.Ps); b = r.kind === 'bar' ? mi(r.Pe) + 1 : a + 1; }
      if (r.kind === 'bar' || r.derived) {
        const op = (r.dash && !r.derived) ? .22 : (r.derived ? .55 : .95);
        g += `<rect x="${X(a)}" y="${y + 3}" width="${Math.max(4, (b - a) * mw)}" height="${r.derived ? 10 : 13}" rx="5" fill="${r.col}" fill-opacity="${op}" stroke="${r.col}" ${r.dash && !r.derived ? 'stroke-dasharray="5 4"' : ''}><title>${E(lbl)}: ${lab(r.Ps) || ''} to ${lab(r.Pe) || ''} (planned)</title></rect>`;
        if (r.derived) g += `<text x="${X(b) + 6}" y="${y + 13}" font-size="10" fill="#8a8882">${Math.round((r.derived[2] - r.derived[1]) * 100)}% of effort</text>`;
      } else {
        const cx = X(a) + mw / 2, col = r.kind === 'gate' ? '#f59e0b' : r.col;
        g += `<path d="M${cx},${y + 3} l8,9 l-8,9 l-8,-9z" fill="${col}"><title>${E(lbl)}: ${lab(r.Ps)} (planned)</title></path>`;
      }
      if (r.As) {
        if (r.kind === 'bar' && !r.derived) {
          const ea = mi(r.As), pend = mi(r.Pe) + 1, eb = r.Ae ? mi(r.Ae) + 1 : Math.max(ea + 1, ti), late = r.Ae && mi(r.Ae) > mi(r.Pe), c = r.Ae ? (late ? '#ff6b86' : '#34d399') : '#f59e0b';
          g += `<rect x="${X(ea)}" y="${y + 16}" width="${Math.max(4, (eb - ea) * mw)}" height="5" rx="2.5" fill="${c}"${r.Ae ? '' : ` fill-opacity=".55" stroke="${c}" stroke-dasharray="3 2"`}><title>Actual: ${lab(r.As)} to ${r.Ae ? lab(r.Ae) : 'in progress'}</title></rect>`;
          if (eb > pend) g += `<rect x="${X(pend)}" y="${y + 14}" width="${(eb - pend) * mw}" height="9" fill="url(#${r.Ae ? 'mfail' : 'mlate'})"><title>Past the planned end: ${E(slipText(r))}</title></rect>`;
          for (let i = Math.max(m0, ea); i < Math.min(m1, eb); i++) wa[i - m0] += isW(r) ? 1 : 0;
        } else if (r.kind !== 'bar') {
          const cx = X(mi(r.As)) + mw / 2, late = mi(r.As) > mi(r.Ps);
          g += `<path d="M${cx},${y + 16} l6,6 l-6,6 l-6,-6z" fill="none" stroke="${late ? '#ff6b86' : '#34d399'}" stroke-width="2"><title>Actual: ${lab(r.As)}</title></path>`;
        }
      }
      const tk = lk[r.id];
      if (tk && tk.length) {
        const lo = tk.map(t => t.start).reduce(minS), hi = tk.map(t => t.target).reduce(maxS), dn = tk.filter(t => t.status === 'done').length;
        g += `<rect x="${X(fIdx(lo))}" y="${y + 22}" width="${Math.max(4, (fIdx(add(hi, 1)) - fIdx(lo)) * mw)}" height="3" rx="1.5" fill="#60a5fa"><title>Linked team tasks: ${dn}/${tk.length} done (${fmt(lo)} to ${fmt(hi)})</title></rect>`;
      }
      g += '</g>';
      if (isW(r)) {
        for (let i = Math.max(m0, a); i < Math.min(m1, b); i++) wl[Math.floor(i) - m0]++;
        if (!r.As) for (let i = Math.max(m0, a); i < Math.min(m1, b); i++) wa[Math.floor(i) - m0]++;
      }
      y += RH;
    }
    const tx = X(ti);
    g += `<line x1="${tx}" x2="${tx}" y1="20" y2="${y}" stroke="#ff2052" stroke-width="2"/><text x="${tx + 5}" y="${y + 12}" fill="#ff7a96" font-size="12">today</text>`;
    y += 30;
    g += `<text x="8" y="${y}" fill="#ff7a96" font-size="11" font-weight="700" letter-spacing=".06em">WORKSTREAMS AT ONCE (TECH, RESEARCH, PRODUCTS)</text><text x="${LW - 12}" y="${y + 60}" fill="#a8a6a0" font-size="11" text-anchor="end">planned (filled)</text><text x="${LW - 12}" y="${y + 76}" fill="#a8a6a0" font-size="11" text-anchor="end">with your actuals (outline)</text>`;
    const mx = Math.max(4, ...wl, ...wa), base = y + 110;
    for (let i = 0; i < N; i++) {
      const h = wl[i] / mx * 62, h2 = wa[i] / mx * 62, ymv = ymOf(m0 + i);
      g += `<rect x="${X(m0 + i) + 1}" y="${base - h}" width="${mw - 2}" height="${Math.max(0, h)}" rx="2" fill="${wl[i] >= 4 ? '#ff2052' : wl[i] >= 3 ? '#f59e0b' : '#60a5fa'}" fill-opacity=".75"><title>${lab(ymv)}: ${wl[i]} planned workstreams${wa[i] !== wl[i] ? ', ' + wa[i] + ' with your actuals' : ''}</title></rect>`;
      if (h2 !== h) g += `<rect x="${X(m0 + i) + 1}" y="${base - h2}" width="${mw - 2}" height="${Math.max(0, h2)}" rx="2" fill="none" stroke="#fff" stroke-opacity=".8"/>`;
      if (wl[i] > 0 && (N <= 30 || i % 2 === 0)) g += `<text x="${X(m0 + i) + mw / 2}" y="${base - h - 3}" font-size="9" fill="#a8a6a0" text-anchor="middle">${wl[i]}</text>`;
    }
    g += '</svg>';

    // summary cards
    const late = acts.filter(isLate).length, ok = acts.filter(isOk).length, prog = acts.filter(r => r.kind === 'bar' && r.As && !r.Ae).length;
    const due = acts.filter(r => !r.As && mi(r.Ps) + 1 <= ti).length;
    const allTasks = [...new Set(acts.flatMap(r => lk[r.id]))], tdone = allTasks.filter(t => t.status === 'done').length;
    const cards = [[acts.length, 'tracked items'], [ok, 'finished on time or early'], [late, 'finished late'], [prog, 'in progress'], [due, 'planned start passed, no actual entered'], [allTasks.length ? tdone + ' / ' + allTasks.length : '0', 'linked team tasks done']]
      .map(([v, l]) => `<div class="card"><div class="k">${v}</div><div class="dim sm">${l}</div></div>`).join('');

    // editable table
    let h = '';
    for (const r of list) {
      if (r.head) { h += `<tr><td colspan="7" style="background:#17171d;color:#ff7a96;font-size:11px;font-weight:700;letter-spacing:.06em">${E(r.head.toUpperCase())}</td></tr>`; continue; }
      if (r.derived) continue;
      const ms = r.kind !== 'bar', inp = (f, v, dis) => dis ? '<span class="dim">·</span>' : `<input type="month" data-mid="${r.id}" data-f="${f}" value="${v || ''}" min="2026-01" max="2031-12">`;
      const tk = lk[r.id], dn = tk.filter(t => t.status === 'done').length, ps = projs().filter(p => p.master === r.id);
      const team = tk.length ? `<b>${dn}/${tk.length}</b> tasks <span class="pg" style="display:inline-block;vertical-align:middle;width:60px"><b style="width:${dn / tk.length * 100}%"></b></span><br><span class="dim sm">${ps.map(p => E(p.name)).join(', ')}</span>` : (ps.length ? '<span class="dim sm">' + ps.map(p => E(p.name)).join(', ') + ', no tasks yet</span>' : '<span class="dim sm">no project linked</span>');
      h += `<tr><td>${E(r.label.trim())}</td><td>${inp('ps', r.Ps)}</td><td>${inp('pe', r.Pe, ms)}</td><td>${inp('as', r.As)}</td><td>${inp('ae', r.Ae, ms)}</td><td>${slip(r)} <a data-mreset="${r.id}" style="cursor:pointer;font-size:12px;margin-left:6px">reset</a></td><td>${team}</td></tr>`;
    }
    const table = `<tr><th>Item</th><th>Planned start</th><th>Planned end</th><th>Actual start</th><th>Actual end</th><th>Plan vs actual</th><th>Team work</th></tr>` + h;
    return { svg: g, cards, table };
  }
  const slipText = r => r.Ae ? mStatus(r) : 'still in progress';

  let pathHtml = null, pathTried = false;
  function pathwaysCard() {
    return `<div class="card" id="pathways"><div class="dim sm">${pathHtml || (pathTried ? 'The Pathways map could not be loaded here. <a href="roadmap.html">Open it on the Roadmap page</a>.' : 'Loading the Pathways map...')}</div></div>`;
  }
  async function loadPathways() {
    if (pathHtml || pathTried) return;
    pathTried = true;
    try {
      const t = await (await fetch('roadmap.html', { cache: 'no-cache' })).text();
      const doc = new DOMParser().parseFromString(t, 'text/html');
      const h2 = [...doc.querySelectorAll('h2')].find(x => /^Pathways and gates/.test(x.textContent));
      const sub = h2 && h2.nextElementSibling, svg = sub && sub.nextElementSibling && sub.nextElementSibling.querySelector('svg');
      if (!svg) throw new Error('not found');
      pathHtml = (sub.textContent ? `<p class="dim sm" style="margin:0 0 10px">${E(sub.textContent)}</p>` : '') + svg.outerHTML;
    } catch (e) { pathHtml = null; }
    const el = document.getElementById('pathways');
    if (el) el.outerHTML = pathwaysCard();
  }

  const Master = {
    html() {
      const b = build();
      return `<h2 style="margin-top:6px">Master plan: plan vs actual</h2><p class="sub">The whole roadmap, live for the team. Bars are the plan (dashed = gated, so the date moves if launch slips), diamonds are single dates (amber = gates). Your real dates appear as a thin bar under the plan: green = on time, amber = in progress, red = finished late. Hatched = past the planned end. The thin blue bar is the span of the team tasks linked to that item. Click any row to edit its dates.</p>
      <div class="grid" style="margin:12px 0">${b.cards}</div>
      <div class="card" style="overflow-x:auto;padding:8px 6px">${b.svg}</div>
      <details open class="card" style="margin-top:14px"><summary style="cursor:pointer;font-weight:600">Edit dates: planned and actual</summary>
      <p class="lgn">Type the real dates here. Everyone on the team sees them live. Link a team project to an item from the project's Edit dialog to fill the Team work column.</p>
      <div class="tw mtab"><table>${b.table}</table></div><p style="margin:10px 0 0"><button id="mrall" onclick="Master.resetAll()">Reset all dates</button></p></details>
      <h2>Pathways and gates, all tracks together</h2>${pathwaysCard()}`;
    },
    after() { loadPathways(); },
    save(id, f, value) {
      const o = Object.assign({ id, ps: '', pe: '', as: '', ae: '' }, Sync.get('master', id) || {});
      o[f] = value || '';
      if (o.ps && o.pe && o.pe < o.ps || o.as && o.ae && o.ae < o.as) { alert('An end month cannot be before its start month.'); render(); return; }
      ui.own = true;
      Sync.put('master', o, 'updated the dates of "' + MR.find(x => x.id === id).label.trim() + '" on the master timeline');
    },
    reset(id) {
      ui.own = true;
      Sync.put('master', { id, ps: '', pe: '', as: '', ae: '' }, 'reset the dates of "' + MR.find(x => x.id === id).label.trim() + '" on the master timeline');
    },
    resetAll() {
      if (!confirm('Clear every planned override and actual date for everyone on the team?')) return;
      ui.own = true; let first = true;
      MR.filter(x => Sync.get('master', x.id)).forEach(x => { Sync.put('master', { id: x.id, ps: '', pe: '', as: '', ae: '' }, first ? 'reset all dates on the master timeline' : ''); first = false; });
    },
    rows, build, fIdx
  };
  root.Master = Master;
})(typeof window !== 'undefined' ? window : globalThis);
