/*
  Visual views for todo.html: who is doing how much work, which work, and what is coming up.

  Workload tab (uses the range at the top of the page; day, week or month buckets by length):
    1. Team load: stacked columns per period, one colour per person, capacity ticks.
    2. Heatmap: person by period, how full each person is (green, amber, red when over).
    3. Who works on what: each person's hours split by project, against their capacity.
    4. Swimlanes: every person's tasks on one time axis, late parts hatched.
    5. Projects: planned, done and remaining hours, with deadlines.
  Upcoming tab: what is due or starting, per-person next-up lists, free capacity,
  and the master plan milestones for the next six months.

  The person and project filters at the top apply to every view here.
  Hours of a task are spread evenly over its days (start to target, plus the overrun
  while it is late) and split equally between the people assigned to it.
*/
(function (root) {
  'use strict';
  const E = s => esc(s);
  const ovl = (a0, a1, b0, b1) => { const s = maxS(a0, b0), e = minS(a1, b1); return e < s ? 0 : dd(s, e) + 1; };
  const hh = n => (Math.round(n * 10) / 10).toFixed(n >= 100 ? 0 : 1);
  const tasksFiltered = () => live().filter(t => !ui.proj || t.project === ui.proj);
  const peopleFiltered = () => ppl().filter(p => !ui.who || p.id === ui.who);
  const wnd = t => [t.start, taskEnd(t, stateOf(t))];

  function buckets(r0, r1) {
    const N = dd(r0, r1) + 1, B = [];
    if (N <= 31) {
      for (let i = 0; i < N; i++) { const s = add(r0, i), d = D(s); B.push({ s, e: s, n: 1, l: String(d.getDate()), sub: d.toLocaleDateString('en-GB', { weekday: 'short' }).slice(0, 2) }); }
      return { unit: 'day', B };
    }
    if (N <= 210) {
      let s = r0;
      while (s <= r1) { const dow = (D(s).getDay() + 6) % 7, e = minS(add(s, 6 - dow), r1); B.push({ s, e, n: dd(s, e) + 1, l: fmt(s), sub: '' }); s = add(e, 1); }
      return { unit: 'week', B };
    }
    let s = r0;
    while (s <= r1) { const d = D(s), e = minS(iso(new Date(d.getFullYear(), d.getMonth() + 1, 0)), r1); B.push({ s, e, n: dd(s, e) + 1, l: MN[d.getMonth()] + " '" + String(d.getFullYear()).slice(2), sub: '' }); s = add(e, 1); }
    return { unit: 'month', B };
  }

  // person x bucket matrix of scheduled hours
  function matrix() {
    const P = peopleFiltered(), { unit, B } = buckets(ui.r0, ui.r1), M = { unit, B, P, cell: {}, proj: {}, tot: {} };
    for (const p of P) {
      M.cell[p.id] = B.map(b => ({ h: 0, cap: (p.cap ?? 15) / 7 * b.n, items: [] }));
      M.proj[p.id] = {}; M.tot[p.id] = { h: 0, cap: 0 };
      M.cell[p.id].forEach(c => { M.tot[p.id].cap += c.cap; });
    }
    for (const t of tasksFiltered()) {
      if (!t.assignees.length) continue;
      const [w0, w1] = wnd(t), wd = dd(w0, w1) + 1, h = hrs(t) / t.assignees.length;
      for (const pid of t.assignees) {
        const c = M.cell[pid]; if (!c) continue;
        B.forEach((b, i) => {
          const o = ovl(w0, w1, b.s, b.e); if (!o) return;
          const x = h * o / wd;
          c[i].h += x; c[i].items.push({ t, h: x });
          M.proj[pid][t.project] = (M.proj[pid][t.project] || 0) + x; M.tot[pid].h += x;
        });
      }
    }
    return M;
  }

  const empty = '<p class="dim">Nothing to show. Add people, projects and tasks, or widen the date range at the top.</p>';

  // ---- 1. team load: stacked columns ----
  function teamLoad(M) {
    const nB = M.B.length, Wd = 1100, Ht = 280, L = 46, R = 12, T = 14, Bm = 40, pw = Wd - L - R, ph = Ht - T - Bm, bw = pw / nB;
    const tot = M.B.map((b, i) => M.P.reduce((a, p) => a + M.cell[p.id][i].h, 0)), cap = M.B.map((b, i) => M.P.reduce((a, p) => a + M.cell[p.id][i].cap, 0));
    const mx = Math.max(1, ...tot, ...cap) * 1.12, Y = v => T + ph - v / mx * ph, t0 = today();
    let g = `<svg viewBox="0 0 ${Wd} ${Ht}" width="100%" style="display:block;min-width:640px" xmlns="http://www.w3.org/2000/svg" font-family="Sora,Inter,system-ui,sans-serif">`;
    for (let k = 0; k <= 4; k++) { const v = mx * k / 4, y = Y(v); g += `<line x1="${L}" x2="${Wd - R}" y1="${y}" y2="${y}" stroke="#26262e"/><text x="${L - 6}" y="${y + 4}" font-size="10" fill="#8a8882" text-anchor="end">${hh(v)}</text>`; }
    g += `<text x="10" y="${T + ph / 2}" font-size="10" fill="#8a8882" transform="rotate(-90 10 ${T + ph / 2})" text-anchor="middle">hours</text>`;
    const step = Math.ceil(nB / 28);
    M.B.forEach((b, i) => {
      const x = L + i * bw + bw * .15, w = bw * .7;
      let acc = 0;
      for (const p of M.P) {
        const h = M.cell[p.id][i].h; if (h < .01) continue;
        const y1 = Y(acc + h), y0 = Y(acc);
        g += `<rect x="${x}" y="${y1}" width="${w}" height="${Math.max(.5, y0 - y1)}" fill="${p.color}"><title>${E(p.name)}: ${hh(h)} h (${E(b.l)})</title></rect>`;
        acc += h;
      }
      const over = tot[i] > cap[i] + .01;
      g += `<line x1="${x - 3}" x2="${x + w + 3}" y1="${Y(cap[i])}" y2="${Y(cap[i])}" stroke="${over ? '#ff2052' : '#f2f1ed'}" stroke-width="2" stroke-dasharray="4 2"><title>Team capacity ${hh(cap[i])} h${over ? ', over by ' + hh(tot[i] - cap[i]) + ' h' : ''}</title></line>`;
      if (i % step === 0) g += `<text x="${x + w / 2}" y="${Ht - 22}" font-size="10" fill="#a8a6a0" text-anchor="middle">${E(b.l)}</text>` + (b.sub ? `<text x="${x + w / 2}" y="${Ht - 10}" font-size="9" fill="#6d6b66" text-anchor="middle">${b.sub}</text>` : '');
      if (t0 >= b.s && t0 <= b.e) g += `<rect x="${L + i * bw}" y="${T}" width="${bw}" height="${ph}" fill="#ff2052" fill-opacity=".08"/><text x="${L + i * bw + bw / 2}" y="${T - 3}" font-size="9" fill="#ff7a96" text-anchor="middle">today</text>`;
    });
    return g + '</svg>';
  }

  // ---- 2. heatmap ----
  const heat = r => { if (r <= 0) return 'transparent'; const hue = r <= 1 ? 150 - 110 * r : 350, a = Math.min(.9, .18 + Math.min(r, 1.4) * .5); return `hsla(${hue},78%,52%,${a})`; };
  function heatmap(M) {
    let h = `<div class="tw"><table class="hm"><tr><th></th>${M.B.map(b => `<th>${E(b.l)}${b.sub ? `<br><span class="dim">${b.sub}</span>` : ''}</th>`).join('')}<th>Total</th></tr>`;
    for (const p of M.P) {
      h += `<tr><th class="who-h"><i style="background:${p.color}"></i>${E(p.name)}</th>`;
      M.cell[p.id].forEach((c, i) => {
        const r = c.cap ? c.h / c.cap : 0, tip = c.items.length ? c.items.sort((a, b) => b.h - a.h).map(x => x.t.title + ': ' + hh(x.h) + ' h').join('\n') : 'Free';
        h += `<td style="background:${heat(r)}" title="${E(M.B[i].l + ' - ' + p.name + ': ' + hh(c.h) + ' of ' + hh(c.cap) + ' h (' + Math.round(r * 100) + '%)\n' + tip)}">${c.h >= .05 ? hh(c.h) : ''}</td>`;
      });
      const tt = M.tot[p.id], r = tt.cap ? tt.h / tt.cap : 0;
      h += `<td class="tot" style="background:${heat(r)}"><b>${hh(tt.h)}</b> <span class="dim">/ ${hh(tt.cap)} h</span></td></tr>`;
    }
    return h + `</table></div><div class="lg"><span><i style="background:${heat(.25)}"></i>light</span><span><i style="background:${heat(.7)}"></i>busy</span><span><i style="background:${heat(1)}"></i>full</span><span><i style="background:${heat(1.3)}"></i>over capacity</span><span class="dim">Hours scheduled in each ${M.unit}, against each person's hours-per-week setting.</span></div>`;
  }

  // ---- 3. who works on what (hours by project) ----
  function byProject(M) {
    const pr = projs(), mx = Math.max(1, ...M.P.map(p => Math.max(M.tot[p.id].h, M.tot[p.id].cap))) * 1.05;
    let h = '';
    for (const p of M.P) {
      const used = pr.filter(x => M.proj[p.id][x.id] > .01).sort((a, b) => M.proj[p.id][b.id] - M.proj[p.id][a.id]), tt = M.tot[p.id], pc = tt.cap ? Math.round(tt.h / tt.cap * 100) : 0;
      h += `<div class="pb"><div class="pbn"><i style="background:${p.color}"></i>${E(p.name)}</div><div class="pbt">${used.map(x => `<span class="seg" style="width:${M.proj[p.id][x.id] / mx * 100}%;background:${x.color}" title="${E(x.name)}: ${hh(M.proj[p.id][x.id])} h"><em>${M.proj[p.id][x.id] / mx > .09 ? E(x.name) : ''}</em></span>`).join('') || '<span class="dim sm" style="padding-left:8px">Nothing scheduled in this range</span>'}<span class="capm" style="left:${tt.cap / mx * 100}%" title="Capacity ${hh(tt.cap)} h"></span></div><div class="pbv ${pc > 100 ? 'fail' : ''}">${hh(tt.h)} h <span class="dim">of ${hh(tt.cap)}</span> (${pc}%)</div></div>`;
    }
    const used = pr.filter(x => M.P.some(p => M.proj[p.id][x.id] > .01));
    return h + `<div class="lg">${used.map(x => `<span><i style="background:${x.color}"></i>${E(x.name)}</span>`).join('')}<span><i style="background:#f2f1ed;width:3px"></i>capacity</span></div>`;
  }

  // ---- 4. swimlanes: each person's tasks over time ----
  function swimlanes(M) {
    const r0 = ui.r0, r1 = ui.r1, N = dd(r0, r1) + 1, Wd = 1100, LWd = 150, pw = Wd - LWd - 8, RHt = 21, t0 = today();
    const X = s => LWd + dd(r0, maxS(minS(s, add(r1, 1)), r0)) / N * pw, Xe = s => LWd + (dd(r0, minS(maxS(s, r0), add(r1, 1)))) / N * pw;
    const T = ticks(r0, N);
    const blocks = [];
    let y = 26;
    for (const p of M.P) {
      const ts = tasksFiltered().filter(t => t.assignees.includes(p.id)).filter(t => taskHits(t, stateOf(t))).sort((a, b) => a.start.localeCompare(b.start) || a.target.localeCompare(b.target));
      const lanes = [], put = [];
      for (const t of ts) {
        const [w0, w1] = wnd(t); let li = lanes.findIndex(e => e < w0);
        if (li < 0) { li = lanes.length; lanes.push(''); }
        lanes[li] = w1; put.push({ t, li, w0, w1 });
      }
      const hgt = Math.max(1, lanes.length) * RHt + 12;
      blocks.push({ p, put, y, hgt });
      y += hgt + 4;
    }
    const Ht = y + 6;
    let g = `<svg viewBox="0 0 ${Wd} ${Ht}" width="100%" style="display:block;min-width:760px" xmlns="http://www.w3.org/2000/svg" font-family="Sora,Inter,system-ui,sans-serif">`
      + `<defs><pattern id="slate" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="8" fill="#f59e0b"/><rect x="4" width="4" height="8" fill="#92400e"/></pattern><pattern id="sfail" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="8" fill="#ff2052"/><rect x="4" width="4" height="8" fill="#7f1d1d"/></pattern></defs>`;
    T.forEach(k => { const x = X(k.s); g += `<line x1="${x}" x2="${x}" y1="18" y2="${Ht}" stroke="${k.mj ? '#2a2a33' : '#1a1a21'}"/><text x="${x + (k.c ? pw / N / 2 : 3)}" y="12" font-size="10" fill="#a8a6a0" ${k.c ? 'text-anchor="middle"' : ''}>${E(String(k.l))}</text>`; });
    let cid = 0;
    for (const b of blocks) {
      g += `<rect x="0" y="${b.y}" width="${Wd}" height="${b.hgt}" fill="${b.y % 2 ? '#101015' : '#0d0d11'}" fill-opacity=".9"/><rect x="0" y="${b.y}" width="4" height="${b.hgt}" fill="${b.p.color}"/>`
        + `<text x="12" y="${b.y + 18}" font-size="13" font-weight="600" fill="#f2f1ed">${E(b.p.name)}</text><text x="12" y="${b.y + 33}" font-size="10" fill="#8a8882">${hh(M.tot[b.p.id].h)} of ${hh(M.tot[b.p.id].cap)} h</text>`;
      if (!b.put.length) g += `<text x="${LWd + 10}" y="${b.y + b.hgt / 2 + 4}" font-size="11" fill="#6d6b66">Free in this range</text>`;
      for (const o of b.put) {
        const t = o.t, s = stateOf(t), pj = projOf(t), yy = b.y + 6 + o.li * RHt, x0 = X(o.w0), x1 = Xe(add(maxS(t.target, o.w0), 1)), w = Math.max(5, x1 - x0), id = 'c' + (cid++);
        g += `<g style="cursor:pointer" onclick="editTask('${t.id}')"><clipPath id="${id}"><rect x="${x0}" y="${yy}" width="${w}" height="${RHt - 4}"/></clipPath>`
          + `<rect x="${x0}" y="${yy}" width="${w}" height="${RHt - 4}" rx="4" fill="${pj.color}" fill-opacity="${s.done ? .35 : .9}"><title>${E(t.title)} (${E(pj.name)})\n${fmt(t.start)} to ${fmt(t.target)}, ${hh(hrs(t) / Math.max(1, t.assignees.length))} h each\n${E(whenText(t, s))}</title></rect>`
          + (w > 34 ? `<text clip-path="url(#${id})" x="${x0 + 5}" y="${yy + 11}" font-size="10" fill="#0a0a0c" font-weight="600">${s.done ? '✓ ' : ''}${E(t.title)}</text>` : '');
        for (const ov of overruns(t, s)) {
          const a = X(ov.from), c = Xe(add(ov.to, 1));
          if (c > a) g += `<rect x="${a}" y="${yy}" width="${Math.max(2, c - a)}" height="${RHt - 4}" fill="url(#${ov.cls === 'fail' ? 'sfail' : 'slate'})"><title>${ov.cls === 'fail' ? 'Past the deadline' : 'Past the target'}: ${E(t.title)}</title></rect>`;
        }
        if (s.dl && s.dl !== t.target && s.dl >= r0 && s.dl <= r1) g += `<rect x="${X(s.dl) + pw / N - 1}" y="${yy - 1}" width="2" height="${RHt - 2}" fill="#f2f1ed"><title>Hard deadline ${fmt(s.dl)}</title></rect>`;
        g += '</g>';
      }
    }
    if (t0 >= r0 && t0 <= r1) { const x = X(t0) + (N <= 60 ? pw / N / 2 : 0); g += `<line x1="${x}" x2="${x}" y1="18" y2="${Ht}" stroke="#ff2052" stroke-width="2"/>`; }
    return g + '</svg>';
  }

  // ---- 5. projects ----
  function projectCards() {
    const t0 = today();
    const L = projs().filter(p => !ui.proj || p.id === ui.proj).sort((a, b) => (a.deadline || '9').localeCompare(b.deadline || '9'));
    if (!L.length) return empty;
    return `<div class="pcs">${L.map(p => {
      const ts = live().filter(t => t.project === p.id), tot = ts.reduce((a, t) => a + hrs(t), 0), dn = ts.filter(t => t.status === 'done').reduce((a, t) => a + hrs(t), 0);
      const late = ts.filter(t => { const s = stateOf(t); return s.late && !s.done; }).length, fl = ts.filter(t => stateOf(t).failed && !t.ack).length;
      const left = p.deadline ? dd(t0, p.deadline) : null, who = [...new Set(ts.flatMap(t => t.assignees))].map(id => `<span class="who" style="--c:${per(id).color}">${E(per(id).name)}</span>`).join('');
      return `<div class="card pc" onclick="editProject('${p.id}')" style="cursor:pointer;border-top:3px solid ${p.color}"><div class="nm"><b>${E(p.name)}</b><span class="dim">${p.scope === 'personal' ? 'personal' : 'team'}</span></div>
      <div class="bar"><span style="width:${tot ? dn / tot * 100 : 0}%;background:#34d399"></span></div>
      <div class="stats"><span><b>${ts.filter(t => t.status === 'done').length}</b>/${ts.length} tasks done</span><span><b>${hh(dn)}</b> of ${hh(tot)} h</span>${late ? `<span class="late"><b>${late}</b> late</span>` : ''}${fl ? `<span class="fail"><b>${fl}</b> failed</span>` : ''}</div>
      <div class="dim sm" style="margin:6px 0">${p.deadline ? (left < 0 ? `deadline ${fmt(p.deadline)}, ${pl(-left, 'day')} ago` : left === 0 ? 'deadline today' : `deadline ${fmt(p.deadline)}, in ${pl(left, 'day')}`) : 'no deadline'}</div><div>${who}</div></div>`;
    }).join('')}</div>`;
  }

  const Insights = {
    workload() {
      const M = matrix();
      if (!M.P.length) return empty;
      const n = dd(ui.r0, ui.r1) + 1;
      return `<p class="sub">${fmt(ui.r0)} to ${fmt(ui.r1)}, ${pl(n, 'day')}, shown by ${M.unit}. Change the range at the top to zoom. Person and project filters apply.</p>
      <div class="vz"><h2>Team load</h2><p class="lgn">Stacked hours per ${M.unit}, one colour per person. The dashed line is the team's capacity; it turns red where the team is over.</p><div class="tlw" style="padding:8px">${teamLoad(M)}</div><div class="lg">${M.P.map(p => `<span><i style="background:${p.color}"></i>${E(p.name)}</span>`).join('')}</div></div>
      <div class="vz"><h2>Who is busy when</h2>${heatmap(M)}</div>
      <div class="vz"><h2>Who works on what</h2><p class="lgn">Each person's hours in this range, split by project. The white line is their capacity.</p>${byProject(M)}</div>
      <div class="vz"><h2>Who is doing which task, and when</h2><p class="lgn">Click a bar to open the task. Hatched amber = past the target day, hatched red = past the hard deadline, white tick = hard deadline, pale = done.</p><div class="tlw" style="padding:6px">${swimlanes(M)}</div></div>
      <div class="vz"><h2>Projects</h2>${projectCards()}</div>`;
    },

    upcoming() {
      const t0 = today(), HZ = ui.up || 14, end = add(t0, HZ), items = [], P = peopleFiltered(), T = tasksFiltered().filter(t => !ui.who || t.assignees.includes(ui.who));
      let dueToday = 0, due7 = 0, lateN = 0, failN = 0, startN = 0;
      for (const t of T) {
        const s = stateOf(t); if (s.done) continue;
        if (s.late) { lateN++; if (s.failed && !t.ack) failN++; continue; }
        if (t.target === t0) dueToday++;
        if (t.target >= t0 && t.target <= add(t0, 7)) due7++;
        if (t.target <= end) items.push({ d: t.target, k: 'due', t });
        if (t.start > t0 && t.start <= end) { items.push({ d: t.start, k: 'start', t }); if (t.start <= add(t0, 7)) startN++; }
        if (s.dl && s.dl !== t.target && s.dl >= t0 && s.dl <= end) items.push({ d: s.dl, k: 'hard', t });
      }
      if (!ui.who) for (const p of projs()) if ((!ui.proj || p.id === ui.proj) && p.deadline >= t0 && p.deadline <= end) items.push({ d: p.deadline, k: 'proj', p });
      items.sort((a, b) => a.d.localeCompare(b.d) || a.k.localeCompare(b.k));
      const day = d => { const n = dd(t0, d), w = D(d).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' }); return (n === 0 ? 'Today' : n === 1 ? 'Tomorrow' : w) + ` <span class="dim sm">${n === 0 ? w : 'in ' + pl(n, 'day')}</span>`; };
      const KL = { due: ['due', 'Due', '#ff7a96'], start: ['start', 'Starts', '#60a5fa'], hard: ['hard', 'Hard deadline', '#f59e0b'], proj: ['proj', 'Project deadline', '#a78bfa'] };
      let ag = '', cur = '';
      for (const it of items) {
        if (it.d !== cur) { cur = it.d; ag += `<h3 class="dh">${day(it.d)}</h3>`; }
        const [, lbl, col] = KL[it.k];
        if (it.p) ag += `<div class="ag" onclick="editProject('${it.p.id}')"><span class="kd" style="--c:${col}">${lbl}</span><div class="tt"><b>${E(it.p.name)}</b><small>${it.p.scope === 'personal' ? 'personal project' : 'team project'}</small></div></div>`;
        else ag += `<div class="ag" onclick="editTask('${it.t.id}')"><span class="kd" style="--c:${col}">${lbl}</span><div class="tt"><b>${E(it.t.title)}</b><small>${E(projOf(it.t).name)}</small></div><div>${it.t.assignees.map(who).join('')}</div><span class="dim sm">${hh(hrs(it.t))} h</span></div>`;
      }
      const hz = [7, 14, 30, 90].map(n => `<button class="${HZ === n ? 'on' : ''}" onclick="ui.up=${n};render()">${n} days</button>`).join('');
      // per person next-up + free capacity next 7 days
      const free = pid => { const p = per(pid), cap = (p.cap ?? 15); let used = 0; for (const t of live()) { if (!t.assignees.includes(pid)) continue; const [w0, w1] = wnd(t); const o = ovl(w0, w1, t0, add(t0, 6)); if (o) used += hrs(t) / t.assignees.length * o / (dd(w0, w1) + 1); } return { cap, used }; };
      const cards = P.map(p => {
        const mine = live().filter(t => t.assignees.includes(p.id) && (!ui.proj || t.project === ui.proj) && !stateOf(t).done).map(t => [t, stateOf(t)]).sort((a, b) => (b[1].failed - a[1].failed) || (b[1].late - a[1].late) || a[0].target.localeCompare(b[0].target));
        const f = free(p.id), left = f.cap - f.used;
        return `<div class="card"><div class="nm"><i style="background:${p.color}"></i><b>${E(p.name)}</b><span class="dim ${left < 0 ? 'fail' : ''}">${left >= 0 ? hh(left) + ' h free this week' : hh(-left) + ' h over this week'}</span></div>
        <div class="bar ${left < 0 ? 'over' : ''}"><span style="width:${Math.min(100, f.cap ? f.used / f.cap * 100 : 0)}%;background:${p.color}"></span></div>
        ${mine.slice(0, 6).map(([t, s]) => `<div class="ai" onclick="editTask('${t.id}')"><div class="tt"><b>${E(t.title)}</b><small>${E(projOf(t).name)} &middot; ${E(whenText(t, s))}</small></div>${s.failed ? '<span class="bd fail">Failed</span>' : s.late ? '<span class="bd late">Late</span>' : ''}<span class="dim sm">${fmt(t.target)}</span></div>`).join('') || '<p class="dim sm" style="margin:6px 0 0">Nothing open. Free to pick up work.</p>'}
        ${mine.length > 6 ? `<p class="dim sm" style="margin:6px 0 0">and ${mine.length - 6} more in the Tasks tab</p>` : ''}</div>`;
      }).join('');
      // master plan, next six months
      const mEndI = mi(t0.slice(0, 7)) + 6, mStartI = mi(t0.slice(0, 7)), ev = [];
      for (const r of (root.MASTER_R || []).filter(x => !x.derived).map(mrow)) {
        const tk = linkedTasks(r.id), tag = tk.length ? ` <span class="dim sm">${tk.filter(t => t.status === 'done').length}/${tk.length} team tasks done</span>` : '';
        const add1 = (i, what) => { if (i >= mStartI && i <= mEndI) ev.push({ i, r, what, tag }); };
        if (r.kind === 'bar') { if (!r.As) add1(mi(r.Ps), 'starts'); if (!r.Ae) add1(mi(r.Pe), 'ends'); } else if (!r.As) add1(mi(r.Ps), r.kind === 'gate' ? 'gate' : 'milestone');
      }
      ev.sort((a, b) => a.i - b.i || a.r.label.localeCompare(b.r.label));
      const ymName = i => { const t = i - 1; return MN[t % 12] + ' ' + Math.floor(t / 12); };
      let mp = '', cm = -1;
      for (const e of ev) { if (e.i !== cm) { cm = e.i; mp += `<h3 class="dh">${ymName(e.i)}${e.i === mStartI ? ' <span class="dim sm">this month</span>' : ''}</h3>`; } mp += `<div class="ag" onclick="editMaster('${e.r.id}')"><span class="kd" style="--c:${e.r.kind === 'gate' ? '#f59e0b' : e.r.col}">${e.what}</span><div class="tt"><b>${E(e.r.label.trim())}</b><small>${E(e.r.lane)}</small></div>${e.tag}</div>`; }
      const kp = [[dueToday, 'due today', dueToday ? '' : 'dim'], [due7, 'due in 7 days', ''], [startN, 'start in 7 days', ''], [lateN, 'running late', lateN ? 'late' : 'dim'], [failN, 'failed, not reviewed', failN ? 'fail' : 'dim']].map(([v, l, c]) => `<div class="card"><div class="k ${c}">${v}</div><div class="dim sm">${l}</div></div>`).join('');
      return `<div class="grid" style="margin:4px 0 14px">${kp}</div>
      <div class="vz2"><div><div class="bar1" style="margin-top:0"><h2 style="margin:0">Coming up</h2><span class="sp"></span><div class="chips">${hz}</div></div><div class="card agenda">${ag || `<p class="dim sm" style="margin:6px 0">Nothing due or starting in the next ${HZ} days.</p>`}</div></div>
      <div><h2>Next up, by person</h2>${cards || empty}</div></div>
      <div class="vz"><h2>Master plan, next 6 months</h2><p class="lgn">Items from the Roadmap whose planned start or end falls in the next six months and has no actual date yet. Click one to edit its dates.</p><div class="card agenda">${mp || '<p class="dim sm" style="margin:6px 0">Nothing planned to start or end in the next six months.</p>'}</div></div>`;
    },
    matrix, buckets
  };
  root.Insights = Insights;
})(typeof window !== 'undefined' ? window : globalThis);
