/* Two voices: the hall screen as one argument seen from two angles, one poster in a series of eight.
   Rest: a masthead names the series; the debate question is split between two fields (forest = serif voice, chalk =
   grotesk voice) by a 12° divide. Each half of the question sits right on top of its answer, set huge on one shared
   baseline, and under each answer the way in: "Watch <names>  2 talks". A rail under both fields carries the
   numbered index of the eight debates (also the progress bar) and the two routes to the talks.
   Lean (pointer, focus or ←/→): the divide springs over and the side you lean to shows its argument; the other side
   shrinks as one unit (its half of the question rides with its answer) and keeps at least 35% of the width.
   One step: you stand inside one voice. Its answer is the mast, cropped at the top; under it one reading column
   (stance, the talk to start with, the side's other talks, all talks on the verdict). The other answer fills a
   wedge on the right that is itself the door to that side. Watch first and All talks keep a sliver of the debate at
   the right edge, which is the way back. */
'use strict';
(() => {
  const M = window.MENU;
  if (!M) return;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  const PHONE = new URLSearchParams(location.search).get('shape') === 'phone';
  document.documentElement.classList.toggle('phone', PHONE);
  const W = PHONE ? 340 : 980, H = PHONE ? 690 : 613;
  const TAN = Math.tan(12 * Math.PI / 180);
  const RAIL_H = PHONE ? 100 : 60;
  const RAIL_TOP = H - RAIL_H;
  const MG = PHONE ? 22 : 48;          // outer margin
  const G = PHONE ? 22 : 32;           // clear space on each side of a divide
  const TOP = PHONE ? 62 : 82;         // the question never rises above this: the masthead sits over it
  const QG = PHONE ? 20 : 20;          // the question's last line → its answer (scales with a shrinking voice)
  const AG = 22;                       // the argument ↔ the answer, when a side opens
  const BOT = PHONE ? 22 : 26;         // the fields' bottom margin above the rail
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const RM = () => motion.matches;

  const menu = $('#menu');
  const trends = M.recap.trends;
  const talkById = new Map(M.talks.map((t) => [t.id, t]));
  const NUMW = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
  const MAST = `Devoxx Belgium 2026: the week in ${NUMW[trends.length] || trends.length} arguments`;

  /* ---- words ------------------------------------------------------------------------------------------------ */
  // The big answer for each side: a few words lifted from the start (or the heart) of that side's stance.
  const ANSWERS = {
    'The harness outweighs the model': ['CLIs.', 'MCP.'],
    'Review is the new bottleneck': ['None.', 'Less.', 'A human.'],
    'Treat coding agents as untrusted code': ['No.', 'Yes, as one layer.'],
    'AI-found CVEs force faster patching': ['The findings are real.', 'Volume is not security.'],
    'The JVM gets leaner and faster': ['Valhalla removes it.', 'Measured limits.'],
    'Java reaches native code and GPUs': ['Nearly everywhere.', 'Native libraries still win.'],
    'Boundaries before services': ['Only where change justifies them.', 'Yes, especially with agents.'],
    'From writing code to judging it': ['Let them go.', 'Keep them on purpose.'],
  };
  // The question cut where the voices change: each part sits on top of its own answer. Only the first one is
  // reordered (so "plain CLIs" lands with the CLIs side); the screen reader gets the question as written.
  const QSPLIT = {
    'The harness outweighs the model': ['Should coding agents reach tools through plain CLIs', 'or MCP servers?'],
    'Review is the new bottleneck': ['How much human code review does', 'agent-written code', 'still need?'],
    'Treat coding agents as untrusted code': ['Are prompt-level defences against injection', 'worth keeping at all?'],
    'AI-found CVEs force faster patching': ['Does the flood of AI-found vulnerabilities', 'make software safer?'],
    'The JVM gets leaner and faster': ['Will Valhalla value classes close', 'Java’s memory-layout gap?'],
    'Java reaches native code and GPUs': ['Can pure Java kernels match', 'native code for AI workloads?'],
    'Boundaries before services': ['Are hexagonal and clean-architecture layers', 'worth their cost?'],
    'From writing code to judging it': ['Should developers keep', 'hands-on skills like debugging?'],
  };
  const firstSentence = (s) => { const m = s.match(/^[^.]{1,40}\./); return m ? m[0] : s.split(' ').slice(0, 3).join(' ') + '…'; };
  const answerFor = (trend, k) => (ANSWERS[trend.title] || [])[k] || firstSentence(trend.debate.sides[k].stance);
  function partsFor(trend, n) {
    const q = QSPLIT[trend.title];
    if (q && q.length === n) return q;
    const w = trend.debate.question.split(/\s+/), per = Math.ceil(w.length / n);
    return Array.from({ length: n }, (_, k) => w.slice(k * per, (k + 1) * per).join(' '));
  }
  // keep short words with their neighbour so a line never holds "A" or "it." alone
  const tie = (a) => { const w = a.split(' '); return w.map((x, i) => x + (i === w.length - 1 ? '' : (x.length <= 2 || (i === w.length - 2 && w[i + 1].length <= 4)) ? '\u00a0' : ' ')).join(''); };
  const NB = (s) => s.replace(/ /g, '\u00a0');
  const surname = (nm) => nm.split(' ').slice(1).join(' ') || nm;
  const joinNames = (a) => (a.length < 2 ? a.join('') : `${a.slice(0, -1).join(', ')} + ${a[a.length - 1]}`);
  const speakers = (t) => t.speakers.map((s) => s.name).join(', ');
  const talks = (c) => `${c} talk${c === 1 ? '' : 's'}`;

  const TZ = 'Europe/Brussels';
  const fDay = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, weekday: 'short', day: 'numeric' });
  const fLongDay = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, weekday: 'long', day: 'numeric', month: 'long' });
  const fTime = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false });
  const fKey = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' });
  const day = (t) => fDay.format(new Date(t.start));
  const time = (t) => fTime.format(new Date(t.start));
  const dayKey = (t) => fKey.format(new Date(t.start));
  // a date never breaks across lines: "Thu 8, 13:50" is one unit
  const where = (t) => `${NB(t.room)}, ${NB(`${day(t)}, ${time(t)}`)}`;
  const DAYS = [...new Set(M.talks.map(dayKey))].sort().map((k) => {
    const t = M.talks.find((x) => dayKey(x) === k);
    return { key: k, label: day(t), long: fLongDay.format(new Date(t.start)) };
  });

  /* ---- openTalk ------------------------------------------------------------------------------------------- */
  const toast = document.createElement('div');
  toast.className = 'toast'; toast.setAttribute('role', 'status'); toast.setAttribute('aria-live', 'polite');
  let toastTimer = 0;
  function openTalk(id) {
    const t = talkById.get(+id);
    if (!t) return;
    toast.textContent = t.seat ? `Walking to ${t.room}` : 'Opening the summary';
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
  }
  window.openTalk = openTalk;

  /* ---- build ---------------------------------------------------------------------------------------------- */
  const SVG = (d, extra = '') => `<svg viewBox="0 0 16 16" aria-hidden="true"${extra}><path d="${d}"/></svg>`;
  const BACK = SVG('M14 8H3M7 3.5L2.5 8 7 12.5');
  const ON = SVG('M2 8h11M9 3.5L13.5 8 9 12.5', ' class="on"');
  const SORTI = SVG('M8 2.5v11M4 9.5l4 4 4-4', ' class="si"');
  const LENS = SVG('M10.2 10.2L14 14M11.5 6.75a4.75 4.75 0 1 1-9.5 0 4.75 4.75 0 0 1 9.5 0z', ' class="lens"');
  const TONES = ['forest', 'chalk', 'forest'];
  const two = (i) => String(i + 1).padStart(2, '0');
  menu.setAttribute('aria-label', MAST);
  menu.innerHTML = `<h1 class="sr" id="question"></h1>
    <div class="stage" id="stage">${TONES.map((tone, k) => `<div class="layer ${tone}" data-k="${k}">
      <p class="mast" aria-hidden="true">${esc(MAST)}</p><p class="qb" aria-hidden="true"></p><div class="vslot"></div></div>`).join('')}</div>
    <a class="skip" href="../../../site/index.html">Text version</a>
    <nav class="rail" aria-label="Debates and talks">
      <div class="nav">
        <button class="back" data-act="close" hidden aria-label="Back to the debate (Esc)">${BACK}<span class="bt">Back</span></button>
        <ol class="index" aria-label="The ${trends.length} debates">${trends.map((t, i) => `<li><button class="ix" data-act="go" data-i="${i}"
          aria-label="Debate ${i + 1} of ${trends.length}: ${esc(t.debate.question)}">${two(i)}</button></li>`).join('')}<li class="bar" aria-hidden="true"></li></ol>
        <p class="peek" aria-hidden="true"></p>
      </div>
      <div class="go">
        <button class="pk" data-act="watch">${M.picks.length} picks to watch first</button>
        <button class="major" data-act="all">All ${M.talks.length} talks${ON}</button>
      </div>
    </nav>`;
  const stage = $('#stage');
  const layers = $$('.layer', stage);
  const rail = $('.rail', menu);
  const ixs = $$('.ix', rail);
  const sheet = document.createElement('div');
  sheet.className = 'sheet'; sheet.hidden = true; sheet.setAttribute('role', 'region');
  sheet.setAttribute('aria-labelledby', 'sheet-h');
  menu.append(sheet, toast);

  /* ---- state ---------------------------------------------------------------------------------------------- */
  let cur = 0, n = 2, rest = [0.52];
  const springs = [{ x: 0.52, v: 0, t: 0.52 }, { x: 0.86, v: 0, t: 0.86 }];
  let leanState = null;           // null = rest, a side index, 'pointer' or 'keys'
  let keyStep = 0;
  let wiping = false;             // a new debate is sliding in: lay out for the rest position
  let blocks = [], voices = [];   // per side: question block metrics, voice element
  let baseY = 470;                // the answers' shared baseline
  let restFs = 200;               // the answers' size at rest; a side keeps it (capped) when you open it
  const restCache = new Map();    // debate → its best rest position and question size
  let sortKey = 'views';
  const allState = { q: '', day: 'all', verdict: null };
  let sheetState = null, lastFocus = null;

  /* ---- geometry ------------------------------------------------------------------------------------------- */
  // Laptop: divide i is a 12° line, x at height y. Phone: a near-horizontal line, y at x (px positions in phoneD).
  let phoneD = [];
  const curD = () => springs.slice(0, n - 1).map((s) => s.x);
  function edge(i, c, ds) {
    if (PHONE) return phoneD[i] + (W / 2 - c) * TAN;
    return ds[i] * W + (H / 2 - c) * TAN;
  }
  function poly(a, b, ds = curD()) {
    const lo = (c) => (a < 0 ? -2 : edge(a, c, ds)), hi = (c) => (b >= n - 1 ? (PHONE ? H : W) + 2 : edge(b, c, ds));
    return PHONE
      ? `polygon(-2px ${lo(-2)}px, ${W + 2}px ${lo(W + 2)}px, ${W + 2}px ${hi(W + 2)}px, -2px ${hi(-2)}px)`
      : `polygon(${lo(-2)}px -2px, ${hi(-2)}px -2px, ${hi(H + 2)}px ${H + 2}px, ${lo(H + 2)}px ${H + 2}px)`;
  }
  function share(k, ds = curD()) {     // fraction of the width side k holds, across the middle
    const lo = k === 0 ? 0 : clamp(edge(k - 1, H / 2, ds), 0, W), hi = k === n - 1 ? W : clamp(edge(k, H / 2, ds), 0, W);
    return (hi - lo) / W;
  }
  const anchorOf = (k) => (k === 0 ? 'left' : k === n - 1 ? 'right' : 'mid');

  /* Place a block of lines (unscaled offsets) in field k at scale s with its top at y; returns its left x and
     whether every line keeps the gutter from both divides. "/" slant: the left divide bites at a line's top,
     the right one at its bottom. */
  function place(k, it, s, y, ds) {
    let bx;
    if (it.anchor === 'left') bx = MG;
    else if (it.anchor === 'right') bx = W - MG - it.bw * s;
    else bx = Math.max(...it.lines.map((l) => edge(k - 1, y + l.lt * s, ds) + G - l.off * s));
    let ok = true;
    for (const l of it.lines) {
      const L = bx + l.off * s, R = L + l.w * s, yt = y + l.lt * s, yb = y + l.lb * s;
      if (k > 0 && L < edge(k - 1, yt, ds) + G - 0.5) ok = false;
      if (k < n - 1 && R > edge(k, yb, ds) - G + 0.5) ok = false;
      if (R > W - MG + 0.5) ok = false;
    }
    return { bx, ok };
  }
  // biggest scale in [floor, 1] at which the block fits; yFn(s) gives its top for that scale
  function fit(k, it, yFn, ds, floor, extra = () => true) {
    const test = (s) => place(k, it, s, yFn(s), ds).ok && extra(s);
    if (test(1)) return 1;
    let lo = floor, hi = 1;
    if (!test(lo)) return lo;
    for (let i = 0; i < 12; i++) { const m = (lo + hi) / 2; if (test(m)) lo = m; else hi = m; }
    return lo;
  }

  /* ---- render a debate ------------------------------------------------------------------------------------ */
  function render(i, dir = 0) {
    const had = document.activeElement;
    const focusSide = had?.classList?.contains('voice') ? +had.dataset.side : null;
    cur = (i + trends.length) % trends.length;
    const trend = trends[cur], sides = trend.debate.sides;
    n = Math.min(sides.length, 3);
    layers.forEach((L, k) => { L.hidden = k >= n; L.style.clipPath = ''; });
    $('#question').textContent = trend.debate.question;
    syncIndex();
    voices = layers.map((L, k) => {
      const slot = $('.vslot', L);
      slot.innerHTML = k < n ? voiceHTML(trend, k) : '';
      return $('.voice', slot);
    }).slice(0, n);
    stage.classList.toggle('n3', n === 3);
    while (springs.length < n - 1) springs.push({ x: 0.9, v: 0, t: 0.9 });
    if (PHONE) { layoutPhone(trend); }
    else {
      // per debate: the divide's rest position and the question size that let the answers grow largest while the
      // question stays a headline (a three-voice debate with a long third answer needs its third field wider)
      let best = restCache.get(cur);
      if (!best) {
        const cands = n === 3 ? [[0.355, 0.68], [0.33, 0.63], [0.31, 0.6]] : [[0.52], [0.49], [0.55]];
        for (const c of cands) {
          rest = c;
          const r = chooseQs(trend);
          const score = r.fs + 2.5 * r.qs;
          if (!best || score > best.score + 4) best = { c, ...r, score };
        }
        restCache.set(cur, best);
      }
      rest = best.c;
      layoutQuestion(trend, best.qs);
      fitAnswers();
      keyStep = 0; leanState = null;
      wiping = !!dir && !RM();
      springs.slice(0, n - 1).forEach((s, j) => { s.t = rest[j]; s.v = 0; s.x = wiping ? (dir > 0 ? 1.14 : -0.14) : rest[j]; });
      kick();
    }
    if (focusSide !== null) voices[Math.min(focusSide, n - 1)]?.focus({ preventScroll: true });
  }
  // The biggest question size that still leaves the answers at poster size (about 3x the question).
  function chooseQs(trend) {
    const ladder = [52, 48, 44, 40, 36, 32];
    let bestR = null;
    for (const qs of ladder) {
      layoutQuestion(trend, qs);
      fitAnswers();
      const r = { qs, fs: restFs };
      if (restFs >= (n === 3 ? 2 : 3.4) * qs) return r;
      if (!bestR || restFs > bestR.fs) bestR = r;
    }
    return bestR;
  }

  function voiceHTML(trend, k) {
    const side = trend.debate.sides[k], ans = answerFor(trend, k), c = side.talkIds.length;
    const end = PHONE ? k % 2 === 1 : k > 0 && k === n - 1;
    // the way in says what it is: a verb, the people, and how many talks
    return `<button class="voice${end ? ' end' : ''}" data-act="side" data-side="${k}"${PHONE ? '' : ` aria-describedby="arg-${k}"`}
        aria-label="${esc(ans)} Watch ${esc(joinNames(side.who))}, ${talks(c)}">
      <span class="answer">${esc(tie(ans))}<i class="bl"></i></span>
      <span class="entry"><span class="nm">Watch\u00a0${esc(joinNames(side.who.map((x) => NB(surname(x)))).replace(' + ', ' +\u00a0'))}</span> <span class="ct">${NB(talks(c))}${ON}</span></span>
    </button>${PHONE ? '' : `<p class="argue" id="arg-${k}">${esc(side.stance)}</p>`}`;
  }

  /* The question, laptop: each part broken into balanced lines that keep clear of the divides wherever the part
     can end up (it rides on top of its answer, so its height is not known yet: measured against the narrowest). */
  function layoutQuestion(trend, qs) {
    const parts = partsFor(trend, n), ds = rest;
    const LH = Math.round(qs * 1.2);
    menu.style.setProperty('--qs', qs + 'px');
    menu.style.setProperty('--lh', LH + 'px');
    const yLow = RAIL_TOP - 130;
    blocks = parts.map((text, k) => {
      const qb = $('.qb', layers[k]), anchor = anchorOf(k);
      qb.className = 'qb' + (anchor === 'right' ? ' end' : '');
      qb.style.transform = 'none'; qb.style.width = '';
      const words = text.split(/\s+/);
      qb.innerHTML = `<span class="ln">${words.map((w) => `<span class="w">${esc(w)}</span>`).join(' ')}</span>`;
      const ws = $$('.w', qb), wid = ws.map((w) => w.offsetWidth);
      const space = ws.length > 1 ? ws[1].offsetLeft - ws[0].offsetLeft - wid[0] : 0;
      const room = (i) => {
        const L = k > 0 ? edge(k - 1, TOP + i * LH, ds) + G : MG, R = k < n - 1 ? edge(k, yLow, ds) - G : W - MG;
        return R - L;
      };
      const breakAt = (cap) => {
        const lines = []; let curL = [], curW = 0;
        ws.forEach((_, j) => {
          const add = curL.length ? space + wid[j] : wid[j];
          if (curL.length && curW + add > Math.min(cap, room(lines.length))) { lines.push(curL); curL = []; curW = 0; }
          curL.push(j); curW += curL.length > 1 ? space + wid[j] : wid[j];
        });
        if (curL.length) lines.push(curL);
        return lines;
      };
      // balance: the narrowest measure that keeps the same number of lines (no orphan "CLIs" on a line alone)
      let lines = breakAt(Infinity);
      if (lines.length > 1) {
        let lo = 40, hi = Math.max(...ws.map((_, j) => j).map(() => room(0)));
        for (let it = 0; it < 14; it++) { const m = (lo + hi) / 2; if (breakAt(m).length > lines.length) lo = m; else hi = m; }
        lines = breakAt(hi + 0.5);
      }
      qb.innerHTML = lines.map((ln) => `<span class="ln">${ln.map((j) => esc(words[j])).join(' ')}</span>`).join('');
      const lnEls = $$('.ln', qb);
      const meta = lnEls.map((el, i) => ({ w: el.offsetWidth, lt: i * LH, lb: (i + 1) * LH, off: 0 }));
      const bw = Math.max(...meta.map((m) => m.w));
      if (anchor === 'right') meta.forEach((m) => { m.off = bw - m.w; });
      qb.style.width = Math.ceil(bw) + 'px';
      return { qb, lines: meta, bw, anchor, h: lines.length * LH };
    });
  }

  /* Answers: one size for every side, as big as fits above the rail, inside the gutters, with each side's half of
     the question on top of it and below the masthead. */
  function fitAnswers() {
    stage.classList.add('fitting');
    const ds = rest;
    let last = null;
    const tryFs = (fs) => {
      menu.style.setProperty('--fs', fs + 'px');
      // answer width: the field's width over the answer's own height (the "/" divide bites at the top on a
      // field's left edge, at the bottom on its right edge); two passes so the height is the real one
      let ms = null, by = RAIL_TOP - 60;
      for (let pass = 0; pass < 2; pass++) {
        voices.forEach((v, k) => {
          const top = ms ? by - ms[k].a : by - fs, bot = RAIL_TOP - BOT;
          const L = k > 0 ? edge(k - 1, top, ds) + G : MG, R = k < n - 1 ? edge(k, bot, ds) - G : W - MG;
          v.style.setProperty('--aw', Math.max(120, R - L) + 'px');
        });
        ms = voices.map(measureVoice);
        by = RAIL_TOP - BOT - Math.max(...ms.map((m) => m.b));
      }
      last = by;
      return ms.every((m, k) => {
        const a = $('.answer', voices[k]);
        if (a.scrollWidth > a.clientWidth + 1) return false;
        const top = by - m.a;
        if (!place(k, itemOf(m, k), 1, top, ds).ok) return false;
        const qt = top - QG - blocks[k].h;
        return qt >= TOP && place(k, blocks[k], 1, qt, ds).ok;
      });
    };
    let chosen = 0;
    for (let fs = 250; fs >= 40; fs -= 10) if (tryFs(fs)) { chosen = fs; break; }
    if (chosen && chosen < 250) for (let fs = chosen + 8; fs > chosen; fs -= 2) if (tryFs(fs)) { chosen = fs; break; }
    if (!chosen) chosen = 40;
    tryFs(chosen);
    baseY = last;
    restFs = chosen;
    void stage.offsetWidth;
    stage.classList.remove('fitting');
  }
  // A wrapped line box is as wide as its max-width, so measure the ink: the union of the text's line rects.
  const range = document.createRange();
  function inkWidth(v) {
    const vr = v.getBoundingClientRect(), k = vr.width / v.offsetWidth || 1;
    let lo = Infinity, hi = -Infinity;
    for (const el of $$('.answer, .entry', v)) {
      range.selectNodeContents(el);
      for (const r of range.getClientRects()) { if (r.width) { lo = Math.min(lo, r.left); hi = Math.max(hi, r.right); } }
    }
    return hi > lo ? (hi - lo) / k : v.offsetWidth;
  }
  function measureVoice(v) {
    const a = $('.bl', v).offsetTop;
    return { a, b: v.offsetHeight - a, w: v.offsetWidth, ink: Math.min(v.offsetWidth, inkWidth(v)), h: v.offsetHeight };
  }
  const itemOf = (m, k) => {
    const right = voices[k]?.classList.contains('end');
    return { anchor: anchorOf(k), bw: m.w, lines: [{ w: m.ink, lt: 0, lb: m.h, off: right ? m.w - m.ink : 0 }] };
  };

  /* ---- the divide: springs + per-frame layout (laptop) ---------------------------------------------------- */
  const K = 190, C = 26;
  let raf = 0, lastT = 0, holdUntil = 0;
  function setTargets(arr) {
    wiping = false;
    arr.forEach((t, i) => { springs[i].t = t; if (RM()) { springs[i].x = t; springs[i].v = 0; } });
    kick();
  }
  function kick(hold = 0) {
    if (PHONE) return;
    holdUntil = Math.max(holdUntil, performance.now() + hold);
    if (!raf) { lastT = performance.now(); raf = requestAnimationFrame(tick); }
  }
  function tick(now) {
    // rAF's timestamp can precede the performance.now() taken in kick() after a long layout: never step backwards
    const dt = clamp((now - lastT) / 1000, 0, 0.032); lastT = Math.max(lastT, now);
    let moving = false;
    for (const s of springs.slice(0, n - 1)) {
      const a = K * (s.t - s.x) - C * s.v;
      s.v += a * dt; s.x += s.v * dt;
      if (Math.abs(s.t - s.x) > 1e-4 || Math.abs(s.v) > 1e-3) moving = true; else { s.x = s.t; s.v = 0; }
    }
    if (!moving) wiping = false;
    layout();
    raf = moving || now < holdUntil ? requestAnimationFrame(tick) : 0;
  }
  const OPEN_AT = () => (n === 2 ? 0.57 : 0.45);
  function layout() {
    const ds = curD(), dsFit = wiping ? rest : ds;
    for (let k = 0; k < n; k++) layers[k].style.clipPath = poly(k - 1, k, ds);
    voices.forEach((v, k) => {
      const b = blocks[k], m = measureVoice(v), it = itemOf(m, k), arg = $('.argue', layers[k]);
      // the side you lean to opens its argument between its half of the question and its answer
      let open = leanState !== null && !wiping && share(k, ds) >= OPEN_AT(), hs = 0, sw = 0;
      if (open) {
        const yT = TOP + b.h, yB = baseY - m.a * 0.7;
        const L = k > 0 ? edge(k - 1, yT, dsFit) + G : MG, R = k < n - 1 ? edge(k, yB, dsFit) - G : W - MG;
        sw = Math.min(470, R - L);
        if (sw < 250) open = false;
        else { arg.style.width = sw + 'px'; hs = arg.offsetHeight; }
      }
      // a side moves as one unit: its half of the question scales and drops with its answer (and, when the side
      // opens, makes room for the argument the same way)
      const solve = (op) => {
        const room = op ? hs + AG : 0;
        const qsOf = (s) => s;
        const qTopAt = (s) => baseY - m.a * s - room - QG * qsOf(s) - b.h * qsOf(s);
        const extra = (s) => qTopAt(s) >= TOP && place(k, b, qsOf(s), qTopAt(s), dsFit).ok;
        const s = fit(k, it, (s) => baseY - m.a * s, dsFit, 0.42, extra);
        return { s, qs: qsOf(s), qt: qTopAt(s), ok: extra(s) && place(k, it, s, baseY - m.a * s, dsFit).ok };
      };
      let r = solve(open);
      if (open && !r.ok) { open = false; r = solve(false); }
      v.classList.toggle('open', open);
      arg.classList.toggle('on', open);
      const top = baseY - m.a * r.s;
      const { bx } = place(k, it, r.s, top, dsFit);
      v.style.transform = `translate(${bx.toFixed(1)}px, ${top.toFixed(1)}px) scale(${r.s.toFixed(3)})`;
      const qx = place(k, b, r.qs, r.qt, dsFit).bx;
      b.qb.style.transform = `translate(${qx.toFixed(1)}px, ${r.qt.toFixed(1)}px) scale(${r.qs.toFixed(3)})`;
      if (open) {
        const ay = top - AG - hs;
        const ax = it.anchor === 'left' ? MG : it.anchor === 'right' ? W - MG - sw : edge(k - 1, ay, dsFit) + G;
        arg.style.left = ax.toFixed(1) + 'px'; arg.style.top = ay.toFixed(1) + 'px';
      }
    });
  }

  /* ---- phone: stacked fields, no lean. Each field holds its half of the question and then its answer; the
     forest field ends just under its names, the chalk field takes the rest. ----------------------------------- */
  function layoutPhone(trend) {
    const parts = partsFor(trend, n);
    const qbs = layers.slice(0, n).map((L, k) => {
      const qb = $('.qb', L);
      qb.className = 'qb' + (k % 2 ? ' end' : '');
      qb.textContent = parts[k];
      qb.style.transform = 'none';
      return qb;
    });
    layers.slice(n).forEach((L) => { $('.qb', L).textContent = ''; });
    const top0 = TOP, bottomN = RAIL_TOP - BOT;
    stage.classList.add('fitting');
    let pos = null, last = null;
    // the question shrinks only if the answers cannot fit at a readable size (a three-voice debate on the totem)
    const tries = [];
    // answers first (they are the poster), then the largest question that still fits with them
    for (let fs = 168; fs >= 56; fs -= 4) for (const qs of [27, 25, 23, 20]) tries.push([qs, fs]);
    for (let fs = 52; fs >= 30; fs -= 4) tries.push([17, fs]);
    for (const [qs, fs] of tries) {
      if (menu.style.getPropertyValue('--qs') !== qs + 'px') { menu.style.setProperty('--qs', qs + 'px'); menu.style.setProperty('--lh', Math.round(qs * 1.28) + 'px'); }
      menu.style.setProperty('--fs', fs + 'px');
      voices.forEach((v) => v.style.setProperty('--aw', (W - 2 * MG) + 'px'));
      if (voices.some((v) => { const a = $('.answer', v); return a.scrollWidth > a.clientWidth + 1; })) continue;
      const ms = voices.map(measureVoice);
      const qh = qbs.map((q) => q.offsetHeight), qw = qbs.map((q) => Math.min(W - 2 * MG, q.offsetWidth));
      const xr = ms.map((m, k) => (k % 2 ? [W - MG - m.w, W - MG] : [MG, MG + m.w]));          // answers
      const qx = qw.map((w, k) => (k % 2 ? [W - MG - w, W - MG] : [MG, MG + w]));              // question parts
      const bh = ms.map((m, k) => qh[k] + QG + m.h);
      const gaps = ms.slice(1).map((_, k) => 2 * G + Math.max(0, (xr[k][1] - qx[k + 1][0]) * TAN));
      const need = bh.reduce((a, h) => a + h, 0) + gaps.reduce((a, g) => a + g, 0);
      last = { ms, xr, qx, qh, bh, gaps, restFs: fs };
      if (need > bottomN - top0) continue;
      const spare = bottomN - top0 - need;
      const tops = [];
      if (n === 2) {
        // a little air under the masthead; the forest field then ends right under its names
        tops[0] = top0 + Math.min(spare * 0.3, 40);
        tops[1] = bottomN - bh[1];
      } else {
        let y = top0; const extra = spare / (n - 1);
        bh.forEach((h, k) => { tops.push(y); y += h + (k < n - 1 ? gaps[k] + extra : 0); });
        tops[n - 1] = bottomN - bh[n - 1];
      }
      phoneD = ms.slice(1).map((_, k) => {
        const lo = tops[k] + bh[k] + G - (W / 2 - xr[k][1]) * TAN;
        const hi = tops[k + 1] - G - (W / 2 - qx[k + 1][0]) * TAN;
        return n === 2 ? lo + Math.min(14, (hi - lo) * 0.2) : (lo + hi) / 2;
      });
      pos = { ms, xr, qx, qh, tops, restFs: fs }; break;
    }
    stage.classList.remove('fitting');
    if (!pos && last) {          // nothing fits: stack what we have from the top rather than leave it unplaced
      const tops = []; let y = top0;
      last.bh.forEach((h, k) => { tops.push(y); y += h + (last.gaps[k] || 0); });
      phoneD = last.gaps.map((g, k) => tops[k] + last.bh[k] + g / 2);
      pos = { ...last, tops };
    }
    if (!pos) return;
    restFs = pos.restFs;
    qbs.forEach((qb, k) => { qb.style.transform = `translate(${pos.qx[k][0]}px, ${pos.tops[k]}px)`; qb.style.width = (pos.qx[k][1] - pos.qx[k][0]) + 'px'; });
    voices.forEach((v, k) => { v.style.transform = `translate(${pos.xr[k][0]}px, ${pos.tops[k] + pos.qh[k] + QG}px)`; });
    for (let k = 0; k < n; k++) layers[k].style.clipPath = poly(k - 1, k);
  }

  /* ---- leaning (laptop) ----------------------------------------------------------------------------------- */
  const LEAN = { 2: [[0.65], [0.35]], 3: [[0.52, 0.78], [0.27, 0.73], [0.22, 0.48]] };
  function lean(k) {
    if (PHONE) return;
    if (k === null || k === undefined) { leanState = null; keyStep = 0; setTargets(rest); return; }
    leanState = k; setTargets(LEAN[n][k]);
  }
  const sideAt = (px, py) => {
    for (let k = 0; k < n - 1; k++) {
      const e = PHONE ? edge(k, px) : edge(k, py, curD());
      if ((PHONE ? py : px) < e) return k;
    }
    return n - 1;
  };
  function pointerLean(px, py) {
    if (RM() || n === 3) { const k = sideAt(px, py); if (leanState !== k) lean(k); return; }
    // the divide moves away from the pointer, so the voice under it widens; the other keeps 35%
    const p = (px + (py - H / 2) * TAN) / W;
    leanState = 'pointer';
    setTargets([clamp(rest[0] + (rest[0] - p) * 1.6, 0.35, 0.65)]);
  }
  function keyLean(dir) {      // ← widens the left voice (as moving the pointer left does), → the right
    if (n === 2) {
      keyStep = clamp(keyStep + dir, -2, 2);
      leanState = keyStep ? 'keys' : null;
      setTargets([[0.65, 0.585, rest[0], 0.435, 0.35][keyStep + 2]]);
      return;
    }
    const order = [0, null, 1, 2];
    const at = order.indexOf(typeof leanState === 'number' ? leanState : null);
    lean(order[clamp(at + dir, 0, order.length - 1)]);
  }

  /* ---- the index: eight numbers, the current one heavy, a bar over it on the rail's hairline --------------- */
  const peek = $('.peek', rail), bar = $('.bar', rail);
  function syncIndex() {
    ixs.forEach((b, i) => {
      const on = i === cur;
      if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
      b.tabIndex = on ? 0 : -1;
    });
    const b = ixs[cur];
    bar.style.transform = `translateX(${b.parentElement.offsetLeft + (b.offsetWidth - 22) / 2}px)`;
    showPeek(null);
  }
  // the hovered or focused number shows that debate's question in full, never cut
  function showPeek(i) {
    if (i === null || i === cur || PHONE) { peek.textContent = ''; peek.classList.remove('on'); return; }
    peek.textContent = trends[i].debate.question;
    peek.classList.add('on');
  }
  rail.addEventListener('pointerover', (e) => { const b = e.target.closest('.ix'); if (b) showPeek(+b.dataset.i); });
  rail.addEventListener('pointerout', (e) => {
    const b = e.target.closest('.ix');
    if (b && !b.contains(e.relatedTarget)) showPeek(document.activeElement?.classList.contains('ix') ? +document.activeElement.dataset.i : null);
  });
  rail.addEventListener('focusin', (e) => { const b = e.target.closest('.ix'); showPeek(b ? +b.dataset.i : null); });
  rail.addEventListener('focusout', (e) => { if (!e.relatedTarget?.classList?.contains('ix')) showPeek(null); });
  function goTo(i) {
    if (sheetState) closeSheet(false);
    if (i !== cur) render(i, i > cur ? 1 : -1);
  }

  /* ---- events on the first screen ------------------------------------------------------------------------- */
  const local = (e) => { const r = menu.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  stage.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse' || sheetState || PHONE) return;
    const [x, y] = local(e); pointerLean(x, y);
  });
  stage.addEventListener('pointerleave', (e) => {
    if (e.pointerType === 'mouse' && !sheetState && !stage.contains(document.activeElement)) lean(null);
  });
  menu.addEventListener('focusin', (e) => {
    if (sheetState) return;
    const v = e.target.closest('.voice');
    if (v) { const k = +v.dataset.side; if (leanState !== k) lean(k); }
    else if (!stage.contains(e.target) && leanState !== null) lean(null);
  });

  // touch: swipe up/down changes the debate; a tap on a field opens that side
  let down = null, swallowClick = false;
  stage.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') down = { x: e.clientX, y: e.clientY }; });
  stage.addEventListener('pointerup', (e) => {
    if (!down || e.pointerType === 'mouse') return;
    const dy = e.clientY - down.y, dx = e.clientX - down.x; down = null;
    if (Math.abs(dy) > 50 && Math.abs(dy) > Math.abs(dx)) { swallowClick = true; render(cur + (dy < 0 ? 1 : -1), dy < 0 ? 1 : -1); }
  });

  let wheelAcc = 0, wheelLock = 0;
  stage.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (performance.now() < wheelLock) return;
    wheelAcc += e.deltaY;
    if (Math.abs(wheelAcc) > 40) { const d = Math.sign(wheelAcc); wheelAcc = 0; wheelLock = performance.now() + 700; render(cur + d, d); }
  }, { passive: false });

  menu.addEventListener('click', (e) => {
    if (swallowClick) { swallowClick = false; return; }
    const a = e.target.closest('[data-act]');
    if (a) {
      const act = a.dataset.act;
      e.preventDefault();
      if (act === 'side') openSheet('side', +a.dataset.side, sheetState ? wedgeClip() : null);
      else if (act === 'talk') openTalk(+a.dataset.id);
      else if (act === 'go') goTo(+a.dataset.i);
      else if (act === 'watch') openSheet('watch');
      else if (act === 'all') { allState.verdict = null; openSheet('all'); }
      else if (act === 'close') closeSheet();
      else if (act === 'sort') { sortKey = ORDER[(ORDER.indexOf(sortKey) + 1) % ORDER.length]; refreshLists(); }
      else if (act === 'verdict') { Object.assign(allState, { q: '', day: 'all', verdict: cur }); openSheet('all', 0, FULL_SHEET); }
      else if (act === 'unscope') { allState.verdict = null; openSheet('all', 0, FULL_SHEET); }
      else if (act === 'day') { allState.day = a.dataset.day; refreshLists(); }
      else if (act === 'clear') { allState.q = ''; const s = $('.search', sheet); s.value = ''; refreshLists(); s.focus(); }
      return;
    }
    if (!sheetState && e.target.closest('.layer')) { const [x, y] = local(e); openSheet('side', sideAt(x, y)); }
  });

  document.addEventListener('keydown', (e) => {
    // the index is one tab stop: ←/→, Home and End move along the numbers, Enter jumps
    if (e.target.classList?.contains('ix')) {
      const i = +e.target.dataset.i;
      const to = { ArrowLeft: i - 1, ArrowRight: i + 1, Home: 0, End: ixs.length - 1 }[e.key];
      if (to !== undefined) { e.preventDefault(); const b = ixs[(to + ixs.length) % ixs.length]; ixs.forEach((x) => { x.tabIndex = x === b ? 0 : -1; }); b.focus(); return; }
    }
    if (sheetState) {
      if (e.key === 'Escape') { e.preventDefault(); closeSheet(); }
      else if (e.target.closest?.('[role="tablist"]') && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
        const tabs = $$('[role="tab"]', sheet), i = tabs.indexOf(e.target);
        const next = tabs[(i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
        next.focus(); next.click(); e.preventDefault();
      }
      return;
    }
    if (e.target.matches?.('input, textarea')) return;
    const onIx = e.target.classList?.contains('ix');
    if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); render(cur + 1, 1); if (onIx) ixs[cur].focus(); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); render(cur - 1, -1); if (onIx) ixs[cur].focus(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); keyLean(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); keyLean(1); }
    else if (e.key === 'Escape') lean(null);
  });

  /* ---- the second screen ---------------------------------------------------------------------------------- */
  const SH = RAIL_TOP;            // the sheet stops at the rail, which stays as the index and the way back
  const METRIC = {
    views: (t) => (t.views == null ? '<small>no video</small>' : t.views.toLocaleString('en-GB')),
    likeRate: (t) => (t.likeRate == null ? '<small>no video</small>' : `${t.likeRate.toFixed(2)}${t.thin ? '<small>few votes</small>' : ''}`),
    hearts: (t) => t.hearts.toLocaleString('en-GB'),
  };
  // One sort control: the number column's own header. It names the unit and cycles views → likes → hearts.
  const UNITS = { views: 'views', likeRate: 'likes per 100 views', hearts: 'hearts' };
  const ORDER = ['views', 'likeRate', 'hearts'];
  const sorter = () => {
    const nx = ORDER[(ORDER.indexOf(sortKey) + 1) % ORDER.length];
    return `<button class="sorter" data-act="sort" aria-label="Sorted by ${UNITS[sortKey]}, highest first. Sort by ${UNITS[nx]} instead">${UNITS[sortKey]}${SORTI}</button>`;
  };
  const sorted = (list) => [...list].sort((a, b) => ((b[sortKey] ?? -1) - (a[sortKey] ?? -1)) || a.title.localeCompare(b.title));
  const voiceOf = (j) => (TONES[j] === 'forest' ? 'v-serif' : 'v-grot');
  // which side of which debate a talk argued for: its tag in All talks, set in that side's voice
  const sideOfTalk = new Map();
  trends.forEach((tr, i) => tr.debate.sides.slice(0, 3).forEach((s, j) => s.talkIds.forEach((id) => { if (!sideOfTalk.has(id)) sideOfTalk.set(id, { i, j }); })));
  const tagOf = (t) => {
    const s = sideOfTalk.get(t.id);
    return s ? `<span class="tag ${voiceOf(s.j)}" title="Debate ${s.i + 1}">${esc(NB(answerFor(trends[s.i], s.j)))}</span>` : '';
  };
  const row = (t, { timed = false, metric = true, tag = false } = {}) => `<li><button class="talk${timed ? ' timed' : ''}${metric && !timed ? '' : ' bare'}" data-act="talk" data-id="${t.id}">
      ${timed ? `<span class="t-time">${time(t)}</span>` : ''}
      <span><span class="t-title">${esc(t.title)}</span><span class="t-meta"><span>${esc(speakers(t))}, ${esc(timed ? t.room : where(t))}</span>${tag ? tagOf(t) : ''}</span></span>
      ${metric && !timed ? `<span class="t-metric">${METRIC[sortKey](t)}</span>` : ''}</button></li>`;
  const pickOf = (trend) => M.picks.find((p) => p.verdict === trend.title);
  const tk = (ids) => ids.map((id) => talkById.get(id)).filter(Boolean);

  // The talk a side starts with always comes from that side: the verdict's pick when it is on this side (with its
  // "why"), otherwise this side's most-watched talk (with its own "watch if").
  function heroFor(trend, k) {
    const side = trend.debate.sides[k], pick = pickOf(trend);
    if (pick && side.talkIds.includes(pick.talkId) && talkById.get(pick.talkId)) return { t: talkById.get(pick.talkId), why: pick.why };
    const own = tk(side.talkIds).sort((a, b) => (b.views ?? -1) - (a.views ?? -1));
    return own[0] ? { t: own[0], why: own[0].watchIf } : null;
  }

  // the wedge: the other side's answer, full height on the right; the whole wedge is the door to that side
  const WT = PHONE ? 0 : 226, WB = WT + SH * TAN;
  function sideBody(k) {
    const trend = trends[cur], side = trend.debate.sides[k], hero = heroFor(trend, k);
    const others = trend.debate.sides.map((_, j) => j).filter((j) => j !== k && j < n);
    const wedgeTone = TONES[k] === 'forest' ? 'chalk' : 'forest';
    const wedge = `<div class="wedge ${wedgeTone}${others.length > 1 ? ' multi' : ''}">${others.length > 1 ? '<p class="wl">Hear the other sides</p>' : ''}
      ${others.map((j) => `<button class="wbtn" data-act="side" data-side="${j}" aria-label="Hear the other side: ${esc(answerFor(trend, j))}">
        ${others.length === 1 ? `<span class="wl">Hear the other side${ON}</span>` : ''}<span class="wa ${voiceOf(j)}">${esc(tie(answerFor(trend, j)))}</span></button>`).join('')}</div>`;
    return `<div class="sheet-in side">
      <h2 id="sheet-h" class="big" tabindex="-1"><span>${esc(tie(answerFor(trend, k)))}</span></h2>
      <div class="col">
        <p class="stance">${esc(side.stance)}</p>
        ${hero ? `<section class="hero" aria-label="Start here">
          <p class="hero-title">${esc(hero.t.title)}</p>
          <p class="hero-meta"><span>${esc(speakers(hero.t))}, ${esc(where(hero.t))}</span>
            <button class="go-link" data-act="talk" data-id="${hero.t.id}">${hero.t.seat ? 'Watch' : 'Read the summary'}${ON}</button></p>
          ${hero.why ? `<p class="why">${esc(hero.why)}</p>` : ''}
        </section>` : ''}
        <ul class="rows" aria-label="More from this side"></ul>
        <button class="all-link" data-act="verdict">All ${trend.talkIds.length} talks on this verdict${ON}</button>
      </div></div>${wedge}`;
  }
  // The side's other talks, added while they fit (at most three), so nothing scrolls; the rest is one click away.
  function fitSideRows() {
    const trend = trends[cur], k = sheetState.k, side = trend.debate.sides[k];
    const heroId = heroFor(trend, k)?.t.id;
    const own = tk(side.talkIds.filter((id) => id !== heroId)).sort((a, b) => (b.views ?? -1) - (a.views ?? -1));
    const col = $('.col', sheet), ul = $('.rows', col);
    ul.innerHTML = '';
    const fits = () => col.scrollHeight <= col.clientHeight + 1;
    for (const t of own.slice(0, 3)) { ul.insertAdjacentHTML('beforeend', row(t, { metric: false })); if (!fits()) { ul.lastElementChild.remove(); break; } }
    ul.hidden = !ul.children.length;
  }
  // The mast keeps the answer's rest size where it can; the hero drops its "why" before anything overflows.
  function fitSide() {
    const big = $('.big', sheet), span = $('span', big), forest = sheet.classList.contains('forest');
    const maxW = PHONE ? 300 : 560, maxH = PHONE ? 104 : 150;
    let f = Math.min(Math.round(restFs * (forest ? 1.08 : 1)), PHONE ? 132 : 196);
    for (; f > 30; f -= 4) {
      big.style.fontSize = f + 'px';
      span.style.maxWidth = maxW + 'px';
      if (span.scrollWidth <= span.clientWidth + 1 && span.offsetWidth <= maxW + 1 && span.offsetHeight <= maxH) break;
    }
    // cropped at the top only, like a poster trimmed at the edge; the left edge is the column's edge
    const crop = Math.round(0.12 * f);
    big.style.marginTop = -crop + 'px';
    const col = $('.col', sheet);
    if (!PHONE) col.style.top = Math.round(big.offsetHeight - crop + 22) + 'px';
    // the side's other talks come before the hero's "why": take the why out, fit the rows, then put it back if it fits
    const why = $('.why', col), hero = $('.hero', col);
    why?.remove();
    fitSideRows();
    if (why) { hero.append(why); if (col.scrollHeight > col.clientHeight + 1) why.remove(); }
    fitWedge();
  }
  // the other answer in its wedge: as large as the slanted strip allows (every line clear of the slant)
  function fitWedge() {
    const wg = $('.wedge', sheet);
    if (!wg) return;
    const words = $$('.wa', wg);
    const clear = (q, wr) => (PHONE
      ? q.top - wr.top >= 72 * (1 - (q.left - wr.left) / W) + 10
      : q.left - wr.left >= (WB - WT) * (1 - (q.top - wr.top) / SH) + 16 && q.top - wr.top >= 24);
    const range = document.createRange();
    for (let f = PHONE ? 54 : 156; f >= 24; f -= 2) {
      words.forEach((w) => { w.style.fontSize = (w.classList.contains('v-serif') ? f * 1.08 : f) + 'px'; });
      const wr = wg.getBoundingClientRect();
      const ok = words.every((w) => w.scrollWidth <= w.clientWidth + 1) && $$('.wa, .wl', wg).every((el) => {
        range.selectNodeContents(el);
        return [...range.getClientRects()].filter((q) => q.width).every((q) => clear(q, wr));
      });
      if (ok) break;
    }
  }

  // Watch first and All talks keep a sliver of the debate at the right edge: the way back to it
  const sliver = (tone) => (PHONE ? '' : `<button class="sliver ${tone}" data-act="close" aria-label="Back to debate ${cur + 1}"></button>`);
  function watchBody() {
    return `<div class="sheet-in watch">
      <div class="cols">
        <section class="col-a">
          <h2 id="sheet-h" class="big" tabindex="-1">Watch first</h2>
          <p class="lead">${esc(M.recap.intro)}</p>
          <p class="note">Picks are ${esc(M.picksNote)}.</p>
        </section>
        <section class="col-b" aria-label="Watch first: one talk per verdict">
          <ul class="list picks">${M.picks.map((p) => {
            const t = talkById.get(p.talkId); if (!t) return '';
            return `<li><button class="talk bare" data-act="talk" data-id="${t.id}"><span>
              <span class="vd">${esc(p.verdict)}</span><span class="t-title">${esc(t.title)}</span>
              <span class="t-meta">${esc(speakers(t))}, ${esc(where(t))}</span>
              <span class="why">${esc(p.why)}</span></span></button></li>`;
          }).join('')}</ul>
        </section>
      </div></div>${sliver('chalk')}`;
  }

  function allBody() {
    const vt = allState.verdict !== null ? trends[allState.verdict] : null;
    return `<div class="sheet-in all">
      <h2 id="sheet-h" tabindex="-1">${vt ? esc(vt.title) : 'All talks'}</h2>
      ${vt ? `<p class="consensus">${esc(vt.consensus)}</p>` : ''}
      <label class="sbox">${LENS}<input class="search" type="search" placeholder="${vt ? `Search these ${vt.talkIds.length} talks` : 'Search talks, speakers, topics'}" aria-label="Search talks, speakers, topics" value="${esc(allState.q)}" autocomplete="off" spellcheck="false">
        <button class="clear" data-act="clear" type="button"${allState.q ? '' : ' hidden'}>Clear</button></label>
      <div class="tools">
        <div class="tabs" role="tablist" aria-label="Programme by day">
          ${[{ key: 'all', label: 'All days' }, ...DAYS].map((d) =>
            `<button role="tab" data-act="day" data-day="${d.key}" aria-selected="${allState.day === d.key}" tabindex="${allState.day === d.key ? 0 : -1}">${esc(d.label)}<span class="n"></span></button>`).join('')}
        </div>
        ${vt ? `<button class="unscope" data-act="unscope">Show all ${M.talks.length} talks</button>` : ''}
      </div>
      <div class="lhead"><p class="count-line" aria-live="polite"></p><span class="sort-slot"></span></div>
      <div class="list" data-list="all"></div></div>${sliver('forest')}`;
  }
  const fold = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const hay = new Map(M.talks.map((t) => [t.id, fold([t.title, speakers(t), t.speakers.map((s) => s.company).join(' '),
    (t.keywords || []).join(' '), (t.themes || []).join(' '), t.track, t.room, t.tldr].join(' \n '))]));
  function allList() {
    const q = fold(allState.q.trim()), tokens = q.split(/\s+/).filter(Boolean);
    const base = allState.verdict !== null ? tk(trends[allState.verdict].talkIds) : M.talks;
    const matched = base.filter((t) => tokens.every((tok) => hay.get(t.id).includes(tok)));
    $$('[role="tab"]', sheet).forEach((b) => {
      const c = b.dataset.day === 'all' ? matched.length : matched.filter((t) => dayKey(t) === b.dataset.day).length;
      $('.n', b).textContent = ` (${c})`;
    });
    const dayInfo = DAYS.find((d) => d.key === allState.day);
    let list = matched;
    if (dayInfo) list = list.filter((t) => dayKey(t) === dayInfo.key).sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, 'en', { numeric: true }));
    else list = sorted(list);
    const scope = dayInfo ? dayInfo.long : '';
    $('.count-line', sheet).textContent = tokens.length
      ? `${list.length} ${list.length === 1 ? 'talk matches' : 'talks match'} “${allState.q.trim()}”${scope ? ` on ${scope}` : ''}`
      : dayInfo ? `${scope}, Brussels time` : `${list.length} talks`;
    $('.sort-slot', sheet).innerHTML = dayInfo || !list.length ? '' : sorter();
    const clr = $('.clear', sheet); if (clr) clr.hidden = !allState.q;
    if (!list.length) return `<p class="empty">No talk matches “${esc(allState.q.trim())}”${scope ? ' that day' : ''}. Try a speaker, a topic or a word from a title.</p>`;
    return `<ul>${list.map((t) => row(t, { timed: !!dayInfo, tag: true })).join('')}</ul>`;
  }
  function refreshLists() {
    if (!sheetState) return;
    const focusKey = document.activeElement?.dataset?.act === 'sort' ? 'sort' : document.activeElement?.dataset?.day;
    if (sheetState.kind === 'side') fitSideRows();
    else if (sheetState.kind === 'all') {
      $('.list', sheet).innerHTML = allList();
      $$('[role="tab"]', sheet).forEach((b) => { const on = b.dataset.day === allState.day; b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1; });
    }
    if (focusKey === 'sort') $('[data-act="sort"]', sheet)?.focus({ preventScroll: true });
    else if (focusKey) $(`[data-day="${focusKey}"]`, sheet)?.focus({ preventScroll: true });
  }

  function syncRail() {
    const on = !!sheetState;
    $('.back', rail).hidden = !on;
    rail.classList.toggle('in-sheet', on);
    for (const kind of ['watch', 'all']) {
      const b = $(`[data-act="${kind}"]`, rail);
      if (sheetState?.kind === kind) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
    }
    const b = ixs[cur];
    bar.style.transform = `translateX(${b.parentElement.offsetLeft + (b.offsetWidth - 22) / 2}px)`;
  }

  const wedgeClip = () => (PHONE ? `polygon(-2px ${SH - 36}px, ${W + 2}px ${SH - 108}px, ${W + 2}px ${SH + 2}px, -2px ${SH + 2}px)`
    : `polygon(${W - WT}px -2px, ${W + 2}px -2px, ${W + 2}px ${SH + 2}px, ${W - WB}px ${SH + 2}px)`);
  const FULL_SHEET = `polygon(-2px -2px, ${W + 2}px -2px, ${W + 2}px ${SH + 2}px, -2px ${SH + 2}px)`;
  function openSheet(kind, k = 0, from = null) {
    if (!sheetState) lastFocus = document.activeElement;
    const region = kind === 'side' ? k : kind === 'watch' ? 0 : Math.min(1, n - 1);
    const tone = kind === 'side' ? TONES[k] : kind === 'watch' ? 'forest' : 'chalk';
    sheetState = { kind, region, k };
    sheet.className = `sheet ${tone}`;
    sheet.innerHTML = kind === 'side' ? sideBody(k) : kind === 'watch' ? watchBody() : allBody();
    sheet.hidden = false;
    stage.inert = true;
    syncRail();
    if (kind === 'all') {
      const input = $('.search', sheet);
      input.addEventListener('input', () => { allState.q = input.value; refreshLists(); });
    }
    sheet.style.transition = 'none'; sheet.style.clipPath = 'none';
    if (kind === 'side') fitSide(); else refreshLists();
    if (!RM()) {
      sheet.style.clipPath = from || (PHONE ? poly(region - 1, region) : poly(region - 1, region));
      void sheet.offsetWidth;
      sheet.style.transition = '';
      sheet.style.clipPath = FULL_SHEET;
    }
    (kind === 'all' ? $('.search', sheet) : $('#sheet-h', sheet)).focus({ preventScroll: true });
  }
  function closeSheet(restoreFocus = true) {
    if (!sheetState) return;
    const { region } = sheetState;
    sheetState = null;
    stage.inert = false;
    syncRail();
    const done = () => { if (!sheetState) { sheet.hidden = true; sheet.innerHTML = ''; sheet.style.clipPath = ''; } };
    if (RM() || !restoreFocus) done();
    else {
      sheet.style.clipPath = poly(region - 1, region);
      sheet.addEventListener('transitionend', done, { once: true });
      setTimeout(done, 700);
    }
    if (!restoreFocus) return;
    const back = lastFocus && lastFocus.isConnected && menu.contains(lastFocus) && !lastFocus.closest('.sheet') ? lastFocus : voices[0];
    back?.focus({ preventScroll: true });
    if (!back?.classList?.contains('voice')) lean(null);
  }

  /* ---- start ---------------------------------------------------------------------------------------------- */
  render(0);
  const fontsIn = Promise.all([
    document.fonts.load('italic 400 40px "Instrument Serif"'),
    document.fonts.load('400 20px "Instrument Serif"'),
    document.fonts.load('500 34px "Archivo"'),
    document.fonts.load('600 200px "Archivo"'),
  ]).catch(() => {});
  Promise.race([fontsIn, new Promise((r) => setTimeout(r, 2500))]).then(() => { restCache.clear(); if (!sheetState) render(cur); });
  motion.addEventListener?.('change', () => lean(null));
  addEventListener('resize', () => { restCache.clear(); if (!sheetState) render(cur); });
})();
