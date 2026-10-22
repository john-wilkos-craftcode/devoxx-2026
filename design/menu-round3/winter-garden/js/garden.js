/* Winter Garden: the window behind the wall. Devoxx Belgium 2026 hall-screen menu, round 3 (design A).
   Everything alive is code: eight plants grown from the eight verdicts (a leaf per talk counted), a trellis per bed,
   one sun on a fixed low arc that the pointer carries, shadows that only turn, rain beads that glint. The glasshouse
   itself is a painted plate (assets/plate-*.webp, AI-generated, see LOG.md); without it a CSS vault stands in. */
(function () {
  'use strict';
  const M = window.MENU;
  if (!M) return;
  const $ = (s, el) => (el || document).querySelector(s);
  const menu = $('#menu');
  const PHONE = new URLSearchParams(location.search).get('shape') === 'phone';
  if (PHONE) { menu.classList.remove('laptop'); menu.classList.add('phone'); }
  const W = PHONE ? 340 : 980, H = PHONE ? 690 : 613;
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const trends = M.recap.trends, talks = M.talks, picks = M.picks;
  const byId = new Map(talks.map((t) => [t.id, t]));
  const pickOf = (i) => picks.find((p) => p.verdict === trends[i].title) || picks[i];

  /* ---------- geometry: where the painted beds are (fractions of the canvas), the vanishing point ---------- */
  // laptop plate (assets/plate-wide, 1536x1024 shown with object-fit: cover, object-position 50% 60%)
  const GEO = PHONE ? { // phone plate (assets/plate-tall, 1024x1536 shown with object-fit: cover, centred: 60 px lost a side)
    vp: [0.5, 0.42],
    beds: [ // [x, y, scale] of each plant's foot; order: near-left, near-right, then back
      [0.124, 0.681, 0.5], [0.876, 0.681, 0.5], [0.176, 0.539, 0.42], [0.824, 0.539, 0.42],
      [0.25, 0.464, 0.3], [0.75, 0.464, 0.3], [0.309, 0.438, 0.22], [0.691, 0.438, 0.22]],
    tags: null, slates: null, // the phone has no room for eight signs: its verdicts are the sheet on the first Walk
    sun: (t) => [30 + t * (W - 60), 150 - Math.sin(t * Math.PI) * 90],
  } : {
    vp: [0.5, 0.483],
    beds: [
      [0.153, 0.742, 1.12], [0.847, 0.742, 1.12], [0.26, 0.59, 0.7], [0.74, 0.59, 0.7],
      [0.352, 0.519, 0.46], [0.648, 0.519, 0.46], [0.39, 0.496, 0.34], [0.61, 0.496, 0.34]],
    // plant labels, one per bed. At rest: a short name on a stake beside its bed (box centre, px). One step in: the full
    // verdict and its count (box centre at step 1, max width). Each stake runs from the label to its plant.
    tags: [[165, 487], [815, 487], [318, 392], [662, 392], [380, 345], [600, 345], [368, 232], [612, 232]],
    slates: [[172, 512, 220], [808, 512, 220], [112, 146, 200], [868, 146, 200], [330, 398, 214], [650, 398, 224], [345, 204, 240], [636, 204, 262]],
    sun: (t) => [70 + t * (W - 140), 165 - Math.sin(t * Math.PI) * 110],
  };
  const px = ([fx, fy]) => [fx * W, fy * H];

  /* ---------- deterministic growth ---------- */
  function rng(seed) {
    let a = (seed * 2654435761) >>> 0 || 7;
    return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const f1 = (n) => Math.round(n * 10) / 10;
  function curve(p) { // Catmull-Rom through points -> cubic path
    if (p.length < 2) return '';
    let d = `M${f1(p[0][0])} ${f1(p[0][1])}`;
    for (let i = 0; i < p.length - 1; i++) {
      const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2;
      d += ` C${f1(p1[0] + (p2[0] - p0[0]) / 6)} ${f1(p1[1] + (p2[1] - p0[1]) / 6)} ${f1(p2[0] - (p3[0] - p1[0]) / 6)} ${f1(p2[1] - (p3[1] - p1[1]) / 6)} ${f1(p2[0])} ${f1(p2[1])}`;
    }
    return d;
  }
  function spiral(x, y, r0, dir) { const p = []; for (let k = 0; k <= 14; k++) { const a = k * 0.6, r = r0 * (1 - k / 16); p.push([x + dir * Math.cos(a) * r, y - Math.sin(a) * r]); } return curve(p); }
  // leaves spread along polylines by arc length, alternating sides
  function along(lines, n, shape, size, r, spread, skipHead) {
    const segs = [];
    for (const ln of lines) for (let i = 0; i < ln.length - 1; i++) {
      const [ax, ay] = ln[i], [bx, by] = ln[i + 1]; const L = Math.hypot(bx - ax, by - ay);
      segs.push({ ax, ay, bx, by, L, ang: Math.atan2(bx - ax, -(by - ay)) * 180 / Math.PI });
    }
    const total = segs.reduce((s, g) => s + g.L, 0), head = skipHead || 0;
    const out = [];
    for (let k = 0; k < n; k++) {
      let d = head + (k + 0.5) * (total - head) / n, g = segs[0];
      for (const s of segs) { if (d <= s.L) { g = s; break; } d -= s.L; }
      const u = clamp(d / g.L, 0, 1), side = k % 2 ? 1 : -1;
      out.push({ x: g.ax + (g.bx - g.ax) * u, y: g.ay + (g.by - g.ay) * u, a: g.ang + side * spread + (r() - .5) * 18, s: size[0] + (size[1] - size[0]) * k / n, shape });
    }
    return out;
  }
  const LEAF = { // each points up from its stalk at (0,0), about 20 units long
    heart: 'M0 0C-3-3-11-8-11-15C-11-20-6-23-2-20C-1-19 0-18 0-17C0-18 1-19 2-20C6-23 11-20 11-15C11-8 3-3 0 0Z',
    lance: 'M0 0C-3-6-3.5-16 0-25C3.5-16 3-6 0 0Z',
    oval: 'M0 0C-6-4-7.5-14 0-21C7.5-14 6-4 0 0Z',
    ivy: 'M0 0C-4-4-13-5-12-11C-11-14-7-13-6-12C-8-17-4-22 0-22C4-22 8-17 6-12C7-13 11-14 12-11C13-5 4-4 0 0Z',
    pinna: 'M0 0C-2.4-3-2.4-8 0-12C2.4-8 2.4-3 0 0Z',
    monstera: 'M0 0C-9-3-17-11-16-21C-15-27-9-26-9-21L-6-30C-5-35-2-33-1.5-28L0-36L1.5-28C2-33 5-35 6-30L9-21C9-26 15-27 16-21C17-11 9-3 0 0Z',
    spike: 'M0 0C-4.5-12-3.5-45 0-66C3.5-45 4.5-12 0 0Z',
    fan: 'M0 0L-3.2-30L0-35L3.2-30Z',
  };
  function leafMarkup(l, named) {
    const cls = `leaf${named ? ' named' : ''}`;
    const tr = `translate(${f1(l.x)} ${f1(l.y)}) rotate(${f1(l.a)}) scale(${f1(l.s / 20)})`;
    if (l.shape === 'palmate') {
      return `<g class="${cls}" transform="${tr}">` + [-52, -26, 0, 26, 52].map((a) => `<path d="${LEAF.oval}" transform="translate(0 -6) rotate(${a}) scale(.9)"/>`).join('') + `<path class="vein" d="M0 0V-6"/></g>`;
    }
    const vein = l.shape === 'heart' || l.shape === 'oval' || l.shape === 'ivy' || l.shape === 'monstera' ? `<path class="vein" d="M0 0V-${l.shape === 'monstera' ? 30 : 16}"/>` : '';
    return `<g class="${cls}" transform="${tr}"><path d="${LEAF[l.shape]}"/>${vein}</g>`;
  }

  const SPECIES = {
    vine(n, r) { // the harness: a vine that climbs the lattice and takes its shape, two trained side branches
      const pts = [[0, 0]];
      for (let i = 1; i <= 7; i++) pts.push([Math.sin(i * 1.25) * 34 + (r() - .5) * 8, -i * 21]);
      const bL = [pts[3], [pts[3][0] - 22, pts[3][1] - 24], [-56, pts[3][1] - 48]];
      const bR = [pts[5], [pts[5][0] + 24, pts[5][1] - 18], [55, pts[5][1] - 42]];
      const stems = [{ d: curve(pts), w: 3.4 }, { d: curve(bL), w: 2 }, { d: curve(bR), w: 2 }];
      for (const [p, dir] of [[pts[2], 1], [pts[4], -1], [pts[6], 1]]) stems.push({ d: spiral(p[0] + dir * 8, p[1] - 4, 7, dir), w: 1 });
      return { stems, leaves: along([pts, bL, bR], n, 'heart', [23, 15], r, 72, 10), flower: pts[7], sides: [bL[2], bR[2]], trellis: 'lattice', box: [124, 154] };
    },
    palmate(n, r) { // broad palmate leaves on upright stems: the plant at the foot of the real tree beside the screen
      const xs = [-27, -9, 9, 27], hs = [142, 126, 150, 118], lines = [], stems = [];
      xs.forEach((x, i) => { const ln = [[x * .4, 0], [x * .8, -hs[i] * .5], [x + (r() - .5) * 6, -hs[i]]]; lines.push(ln); stems.push({ d: curve(ln), w: 2.4 }); });
      return { stems, leaves: along(lines, n, 'palmate', [19, 14], r, 62, 30), flower: lines[2][2], sides: [lines[0][2], lines[2][2], lines[3][2]], trellis: 'lattice', box: [124, 158] };
    },
    ivy(n, r) { // ivy: three stems trained diagonally across the lattice, small lobed leaves
      const lines = [], stems = [];
      for (let k = 0; k < 3; k++) { const x0 = -48 + k * 48, ln = [[x0 * .5, 0]]; for (let i = 1; i <= 6; i++) ln.push([x0 + Math.sin(i * .9 + k) * 18, -i * 22 - k * 3]); lines.push(ln); stems.push({ d: curve(ln), w: 1.8 }); }
      return { stems, leaves: along(lines, n, 'ivy', [17, 12], r, 70, 14), flower: lines[1][6], sides: [lines[0][6], lines[2][6]], trellis: 'lattice', box: [124, 150] };
    },
    fern(n, r) { // fern: four fronds from one crown, a leaflet per talk
      const lines = [], stems = [];
      for (const a of [-58, -22, 22, 58]) { const s = Math.sin(a * Math.PI / 180), ln = [[0, -4], [s * 30, -52 - (1 - Math.abs(s)) * 10], [s * 64, -98 - (1 - Math.abs(s)) * 22]]; lines.push(ln); stems.push({ d: curve(ln), w: 1.8 }); }
      return { stems, leaves: along(lines, n, 'pinna', [20, 14], r, 74, 18), flower: lines[1][2], sides: [lines[0][2], lines[3][2]], trellis: 'fan', box: [124, 128] };
    },
    bamboo(n, r) { // bamboo: three culms, lean and fast; narrow leaves at the nodes
      const culms = [[-30, 152], [1, 134], [31, 118]], lines = [], stems = [];
      for (const [x, h] of culms) { const ln = [[x, 0], [x + (r() - .5) * 4, -h * .5], [x + (r() - .5) * 8, -h]]; lines.push(ln); stems.push({ d: curve(ln), w: 3.2 }); for (let y = -24; y > -h; y -= 26) stems.push({ d: `M${x - 3.5} ${y}h7`, w: 2 }); }
      return { stems, leaves: along(lines, n, 'lance', [25, 17], r, 52, 40), flower: lines[0][2], sides: [lines[0][2], lines[2][2]], trellis: 'tiers', box: [124, 156] };
    },
    agave(n, r) { // agave: a rosette, one spike per talk, and the famous flower stalk
      const leaves = [], stems = [{ d: 'M0 -6C1 -50 -1 -100 0 -146', w: 2.2 }];
      for (let k = 0; k < n; k++) { const a = -82 + 164 * k / Math.max(1, n - 1), len = 54 + 18 * Math.sin(k / (n - 1) * Math.PI) + (r() - .5) * 8; leaves.push({ x: 0, y: -6, a, s: len / 66 * 20, shape: 'spike' }); }
      const tip = (k) => { const l = leaves[k], a = l.a * Math.PI / 180, L = l.s / 20 * 66; return [Math.sin(a) * L, -6 - Math.cos(a) * L]; };
      return { stems, leaves, flower: [0, -146], sides: [tip(0), tip(n - 1)], trellis: 'fan', box: [124, 150] };
    },
    espalier(n, r) { // espalier: a tree trained flat in tiers along wires, clear boundaries
      const stems = [{ d: 'M0 0C1 -40 -1 -100 0 -140', w: 3.4 }], lines = [];
      for (const y of [-46, -86, -126]) for (const dir of [-1, 1]) { const ln = [[0, y], [dir * 28, y - 5], [dir * 54, y - 9]]; lines.push(ln); stems.push({ d: curve(ln), w: 2 }); }
      return { stems, leaves: along(lines, n, 'oval', [18, 14], r, 28, 10), flower: [0, -140], sides: [lines[4][2], lines[5][2]], trellis: 'tiers', box: [124, 150] };
    },
    palm(n, r) { // fan palm: five fans, one segment per talk, held up like hands that judge
      const stems = [{ d: 'M-3 0C-2 -20 -1 -40 0 -56M3 0C2 -20 1 -40 0 -56', w: 4 }], leaves = [], sides = [];
      const fans = [-62, -31, 0, 31, 62], per = [4, 4, 5, 4, 4];
      let left = n;
      fans.forEach((fa, i) => {
        const rad = fa * Math.PI / 180, L = 46 + 14 * Math.cos(rad), hx = Math.sin(rad) * L, hy = -56 - Math.cos(rad) * L;
        stems.push({ d: `M0 -56L${f1(hx)} ${f1(hy)}`, w: 1.8 });
        const k = Math.min(per[i], left); left -= k;
        for (let j = 0; j < k; j++) leaves.push({ x: hx, y: hy, a: fa + (-34 + 68 * (j + .5) / k), s: 28 + 8 * Math.cos(rad), shape: 'fan' });
        if (i === 0 || i === 4) sides.push([hx, hy]);
      });
      return { stems, leaves, flower: [0, -58], sides, trellis: 'fan', box: [124, 148] };
    },
  };
  const PLAN = [ // one species per verdict, in the data's order
    { sp: 'vine', fill: '#3a8152', stroke: '#22553a' },
    { sp: 'palmate', fill: '#64944a', stroke: '#41652f' },
    { sp: 'ivy', fill: '#2c5f42', stroke: '#1b3f2c' },
    { sp: 'fern', fill: '#55883c', stroke: '#345a25' },
    { sp: 'bamboo', fill: '#8fb158', stroke: '#6b8440' },
    { sp: 'agave', fill: '#71988f', stroke: '#4c736b' },
    { sp: 'espalier', fill: '#33694b', stroke: '#5a4630' },
    { sp: 'palm', fill: '#2b6658', stroke: '#5a4630' },
  ];
  function trellisMarkup(kind, [w, h]) {
    const x0 = -w / 2, x1 = w / 2;
    if (kind === 'tiers') {
      let s = `<path class="trellis-frame" d="M${x0} 2V${-h}M${x1} 2V${-h}"/>`;
      for (const y of [-46, -86, -126]) s += `<path class="trellis-wire" d="M${x0} ${y}H${x1}"/>`;
      return s + `<path class="trellis" d="M${x0 - 2} ${-h}H${x1 + 2}"/>`;
    }
    if (kind === 'fan') {
      let s = '';
      for (let k = -3; k <= 3; k++) { const a = k * 19 * Math.PI / 180; s += `<path class="trellis" d="M0 -4L${f1(Math.sin(a) * h * .92)} ${f1(-4 - Math.cos(a) * h * .92)}"/>`; }
      s += `<path class="trellis" d="M${f1(-Math.sin(1.0) * h * .55)} ${f1(-4 - Math.cos(1.0) * h * .55)}A${h * .55} ${h * .55} 0 0 1 ${f1(Math.sin(1.0) * h * .55)} ${f1(-4 - Math.cos(1.0) * h * .55)}"/>`;
      s += `<path class="trellis-frame" d="M${f1(-Math.sin(1.0) * h * .92)} ${f1(-4 - Math.cos(1.0) * h * .92)}A${h * .92} ${h * .92} 0 0 1 ${f1(Math.sin(1.0) * h * .92)} ${f1(-4 - Math.cos(1.0) * h * .92)}"/>`;
      return s;
    }
    let s = `<path class="trellis-frame" d="M${x0} 2V${-h}H${x1}V2"/>`;
    for (let k = -8; k <= 8; k++) {
      const o = k * 22;
      s += `<path class="trellis" d="M${x0 + o} 0L${x0 + o + h} ${-h}"/><path class="trellis" d="M${x1 - o} 0L${x1 - o - h} ${-h}"/>`;
    }
    return `<g clip-path="url(#tclip)">${s}</g>`;
  }
  const FLOWER = (() => { let p = ''; for (let k = 0; k < 5; k++) p += `<path class="petal" d="M0 0C-4.6-4.6-4.6-11 0-13.5C4.6-11 4.6-4.6 0 0Z" transform="rotate(${k * 72})"/>`; return p + '<circle class="eye" r="3"/>'; })();

  /* ---------- build the garden ---------- */
  const garden = $('#garden');
  garden.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const grown = trends.map((t, i) => SPECIES[PLAN[i].sp](t.count, rng(i + 11)));
  const named = trends.map((t) => t.talkIds.length);
  const mix = (a, b, t) => '#' + [1, 3, 5].map((k) => Math.round(parseInt(a.substr(k, 2), 16) * (1 - t) + parseInt(b.substr(k, 2), 16) * t).toString(16).padStart(2, '0')).join('');
  let defs = `<defs><clipPath id="tclip"><rect x="-64" y="-160" width="128" height="164"/></clipPath>` +
    `<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>` +
    // each leaf is shaded on its own: lit on the sun's side, dark on the far side, so the plants pick up the plate's light
    PLAN.map((c, i) => `<linearGradient id="lg-${i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${mix(c.fill, '#eaf2b8', .38)}"/><stop offset=".5" stop-color="${c.fill}"/><stop offset="1" stop-color="${mix(c.fill, '#0f2116', .42)}"/></linearGradient>`).join('');
  grown.forEach((g, i) => {
    defs += `<symbol id="plant-${i}" overflow="visible">` + g.stems.map((s) => `<path class="stem" d="${s.d}" stroke-width="${s.w}"/>`).join('') +
      g.leaves.map((l, k) => leafMarkup(l, k < named[i])).join('') + `</symbol>`;
  });
  defs += '</defs>';
  // the five days: a row of stepping stones (HTML buttons), the one you stand on marked
  const DAYS = ['Mon 5', 'Tue 6', 'Wed 7', 'Thu 8', 'Fri 9'];
  const DAY_LONG = ['Monday 5 October', 'Tuesday 6 October', 'Wednesday 7 October', 'Thursday 8 October', 'Friday 9 October'];
  let beds = '';
  trends.forEach((t, i) => {
    const [x, y] = px(GEO.beds[i]), s = GEO.beds[i][2], g = grown[i], c = PLAN[i];
    beds += `<g class="bed${s < .5 ? ' far' : ''}" data-i="${i}" tabindex="0" role="button" aria-label="Bed ${i + 1}: ${esc(t.title)}, ${t.count} talks. Enter to face it." transform="translate(${f1(x)} ${f1(y)}) scale(${s})">` +
      `<ellipse class="contact" cx="0" cy="1" rx="${f1(g.box[0] * .5)}" ry="9" filter="url(#soft)"/>` +
      `<g class="trellis-g">${trellisMarkup(g.trellis, g.box)}</g>` +
      `<g class="shadow-wrap"><use href="#plant-${i}" class="shadow" transform="scale(1 -.42)"/></g>` +
      `<g class="plant"><g class="rim"><use href="#plant-${i}"/></g><g class="body" fill="url(#lg-${i})" stroke="${c.stroke}"><use href="#plant-${i}"/></g></g>` +
      `<g class="flower" transform="translate(${f1(g.flower[0])} ${f1(g.flower[1])})"><g class="turn">${FLOWER}</g></g>` +
      `<rect class="hit" x="-70" y="-168" width="140" height="178" rx="8"/></g>`;
  });
  garden.innerHTML = defs + beds;
  const bedEls = [...garden.querySelectorAll('.bed')];

  // plant labels (HTML): a short name at rest, the whole verdict and its count one step in; a stake to the plant
  const SHORT = ['Harness over model', 'Review bottleneck', 'Untrusted agents', 'Faster patching', 'Leaner JVM', 'Native & GPUs', 'Boundaries first', 'Judging code'];
  const slatesBox = $('#slates'), slabsBox = $('#days');
  slatesBox.innerHTML = PHONE ? '' : trends.map((t, i) =>
    `<i class="stake" data-i="${i}"></i><div class="slate" data-i="${i}"><span class="n">${i + 1}</span><span class="nm short">${esc(SHORT[i])}</span><span class="nm full">${esc(t.title)}</span><span class="count">${t.count} talks</span></div>`).join('');
  const slateEls = [...slatesBox.querySelectorAll('.slate')], stakeEls = [...slatesBox.querySelectorAll('.stake')];
  const bedAt = (i, s) => { const [vx, vy] = px(GEO.vp), [bx, by] = px(GEO.beds[i]); return [vx + (bx - vx) * s, vy + (by - vy) * s]; };
  function placeSlates(k) { // labels follow their beds into the zoom and never leave the screen; stakes are re-cut each time
    if (PHONE) return;
    const s = 1 + 0.085 * k, [vx, vy] = px(GEO.vp);
    slateEls.forEach((el, i) => {
      const at = k ? GEO.slates[i] : GEO.tags[i], sk = 1; // the signs stand still while the beds come closer
      el.style.maxWidth = k ? at[2] + 'px' : el.classList.contains('is-current') ? '290px' : '';
      const w = el.offsetWidth, h = el.offsetHeight;
      const x = clamp(vx + (at[0] - vx) * sk, w / 2 + 8, W - w / 2 - 8), y = clamp(vy + (at[1] - vy) * sk, h / 2 + 8, H - h / 2 - 8);
      el.style.left = f1(x) + 'px'; el.style.top = f1(y) + 'px';
      // the stake: from the label's edge nearest the bed to the plant (its foot when the label hangs below, its crown when above)
      const [bx, by] = bedAt(i, s), sc = GEO.beds[i][2] * s, below = y > by - 10;
      const ty = below ? by - 4 * sc : by - grown[i].box[1] * sc * .55;
      const sx0 = clamp(bx, x - w / 2 + 10, x + w / 2 - 10), sy0 = below ? y - h / 2 : y + h / 2;
      const dx = bx - sx0, dy = ty - sy0, len = Math.hypot(dx, dy);
      const st = stakeEls[i];
      st.style.left = f1(sx0) + 'px'; st.style.top = f1(sy0) + 'px'; st.style.width = f1(Math.max(0, len)) + 'px';
      st.style.transform = `rotate(${f1(Math.atan2(dy, dx) * 180 / Math.PI)}deg)`;
      st.classList.toggle('none', len < 4 || (k > 0 && (bx < -20 || bx > W + 20 || by > H + 20)));
    });
  }
  slabsBox.innerHTML = DAYS.map((d, k) => `<button class="slab-label" type="button" data-day="${k}" aria-label="${DAY_LONG[k]}: the programme">${d}</button>`).join('');
  const slabLabelEls = [...slabsBox.querySelectorAll('.slab-label')];

  /* ---------- the plate, or the CSS house ---------- */
  const plate = $('#plate');
  if (PHONE) plate.src = 'assets/plate-tall.webp';
  plate.style.objectPosition = PHONE ? '50% 50%' : '50% 60%';
  plate.addEventListener('error', () => menu.classList.add('no-plate'));
  if (plate.complete && plate.naturalWidth === 0) menu.classList.add('no-plate');
  $('#scene').style.transformOrigin = `${GEO.vp[0] * 100}% ${GEO.vp[1] * 100}%`;

  /* ---------- the sun: one low arc, carried by the pointer ---------- */
  const light = $('#light'), beadsC = $('#beads');
  light.width = beadsC.width = W; light.height = beadsC.height = H;
  const lctx = light.getContext('2d'), bctx = beadsC.getContext('2d');
  const br = rng(99);
  const beads = Array.from({ length: PHONE ? 70 : 120 }, () => ({ x: br() * W, y: br() * H * (PHONE ? .5 : .6), r: 1.4 + br() * 2.8, ph: br() * 6.28, run: 0 }));
  const REST_T = 0.22, IDLE_MS = 1200;
  let sunT = RM ? REST_T : -0.06, sunTarget = REST_T, lastDrawT = -9, lastInput = performance.now(), growT0 = performance.now();
  let raf = 0;
  // dust in the light: motes live in shaft coordinates (u along the beam, v across it), so they follow the sun
  const mr = rng(42);
  const motes = Array.from({ length: PHONE ? 26 : 46 }, () => ({ u: mr(), v: mr() * 2 - 1, s: mr(), sp: .00002 + mr() * .00004, ph: mr() * 6.28, beam: Math.floor(mr() * 4) }));
  const BEAMS = [[-0.22, 0.05, .5], [-0.07, 0.065, .58], [0.08, 0.045, .5], [0.21, 0.03, .4]];

  function drawLight(sx, sy, now) {
    lctx.clearRect(0, 0, W, H);
    const g = lctx.createRadialGradient(sx, sy, 0, sx, sy, PHONE ? 60 : 95);
    g.addColorStop(0, 'rgba(251,247,228,.95)'); g.addColorStop(.3, 'rgba(251,247,228,.6)'); g.addColorStop(1, 'rgba(251,247,228,0)');
    lctx.fillStyle = g; lctx.fillRect(sx - 100, sy - 100, 200, 200);
    const tx = W * .5 + (sx - W * .5) * .3, ty = H + 160, base = Math.atan2(ty - sy, tx - sx), L = H * 1.7;
    for (const [off, half, a] of BEAMS) {
      const ang = base + off;
      lctx.beginPath(); lctx.moveTo(sx, sy);
      lctx.lineTo(sx + Math.cos(ang - half) * L, sy + Math.sin(ang - half) * L);
      lctx.lineTo(sx + Math.cos(ang + half) * L, sy + Math.sin(ang + half) * L); lctx.closePath();
      const lg = lctx.createLinearGradient(sx, sy, sx + Math.cos(ang) * L, sy + Math.sin(ang) * L);
      lg.addColorStop(0, `rgba(220,235,160,${a})`); lg.addColorStop(.5, `rgba(220,235,160,${a * .5})`); lg.addColorStop(1, 'rgba(220,235,160,0)');
      lctx.fillStyle = lg; lctx.fill();
    }
    if (RM || now == null) return;
    for (const m of motes) { // slow dust turning in the beams, brightest near the glass, gone by the floor
      const [off, half] = BEAMS[m.beam], u = .12 + .62 * ((m.u + now * m.sp) % 1);
      const v = m.v + Math.sin(now / 2400 + m.ph) * .25, ang = base + off + v * half * .8, d = u * L * .62;
      const x = sx + Math.cos(ang) * d, y = sy + Math.sin(ang) * d;
      const a = (1 - u) * (.35 + .35 * Math.sin(now / 1300 + m.ph * 3) ** 2);
      lctx.beginPath(); lctx.arc(x, y, .7 + m.s * 1.3, 0, 6.3); lctx.fillStyle = `rgba(255,251,226,${f1(a * 100) / 100})`; lctx.fill();
    }
  }
  function drawBeads(sx, sy, now) {
    bctx.clearRect(0, 0, W, H);
    for (const b of beads) {
      const y = b.y + b.run;
      const ang = Math.atan2(sy - y, sx - b.x);
      const sh = RM ? .5 : .35 + .65 * Math.max(0, Math.cos(ang * 5 + b.ph + sunT * 9));
      bctx.beginPath(); bctx.ellipse(b.x, y, b.r, b.r * 1.2, 0, 0, 6.3);
      bctx.fillStyle = 'rgba(235,245,230,.10)'; bctx.fill();
      bctx.strokeStyle = 'rgba(23,39,30,.14)'; bctx.lineWidth = .6; bctx.stroke();
      if (b.run > 0) { bctx.beginPath(); bctx.moveTo(b.x, b.y); bctx.lineTo(b.x, y); bctx.strokeStyle = 'rgba(255,255,255,.18)'; bctx.lineWidth = b.r * .7; bctx.stroke(); }
      bctx.beginPath(); bctx.arc(b.x + Math.cos(ang) * b.r * .42, y + Math.sin(ang) * b.r * .42, b.r * .3, 0, 6.3);
      bctx.fillStyle = `rgba(255,255,255,${.2 + .6 * sh})`; bctx.fill();
    }
  }
  let domT = -9, domAt = -1e9;
  function placeSun(t, now) {
    const [sx, sy] = GEO.sun(t);
    drawLight(sx, sy, now);
    // ambient frames only redraw the canvas. The plants answer a hand on the sun at once; while the sun drifts on its
    // own they turn in a tick every 1.5 s (eased by CSS), a sundial's pace, which also leaves them still enough to click
    if (Math.abs(t - domT) < 0.0004) return;
    const t0 = now == null ? 0 : now;
    if (now != null && t0 - lastInput > IDLE_MS && t0 - domAt < 1500) return;
    domT = t; domAt = t0;
    bedEls.forEach((el, i) => {
      const [bx, by] = px(GEO.beds[i]);
      const theta = Math.atan2(by - sy, bx - sx) * 180 / Math.PI;
      const lean = RM ? 0 : clamp((sx - bx) / W * 12, -6, 6);
      // rim light: a pale copy of the plant nudged toward the sun, so each leaf has a lit edge on the sun's side
      const rl = Math.hypot(sx - bx, sy - by) || 1, sc = GEO.beds[i][2];
      el.querySelector('.rim').setAttribute('transform', `translate(${f1((sx - bx) / rl * 1.6 / sc)} ${f1((sy - by) / rl * 1.6 / sc)})`);
      el.querySelector('.shadow-wrap').setAttribute('transform', `rotate(${f1(RM ? 0 : theta - 90)})`);
      el.querySelector('.flower .turn').setAttribute('transform', `rotate(${f1(lean * 2.5)})`);
      el.dataset.lean = lean;
    });
  }
  let tick = 0;
  function frame(now) {
    raf = 0;
    let busy = false;
    // entrance: the plants grow in; then each breathes a little on its own phase (a draught under the glass)
    bedEls.forEach((el, i) => {
      const d = RM ? 1 : clamp((now - growT0 - 250 - i * 70) / 1000, 0, 1), e = 1 - Math.pow(1 - d, 3);
      const sc = .06 + .94 * e, lean = +el.dataset.lean || 0;
      const sway = RM ? 0 : Math.sin(now / (2600 + i * 230) + i * 1.7) * (.9 - GEO.beds[i][2] * .3) * e;
      el.querySelector('.plant').setAttribute('transform', `rotate(${f1((lean + sway) * 10) / 10}) scale(1 ${f1(sc)})`);
      if (d < 1) busy = true;
    });
    // idle: the sun soon drifts along its arc (an attract loop for the wall); a bead runs down the glass now and then
    const idle = now - lastInput;
    if (!RM && idle > IDLE_MS && !openPanel) sunTarget = REST_T + .34 * (1 - Math.cos((idle - IDLE_MS) / 30000 * 6.283)) / 2;
    if (!RM) {
      for (const b of beads) if (b.run > 0) { b.run += 1.6; if (b.run > H * .5) b.run = 0; }
      if (idle > IDLE_MS && Math.random() < 0.003) { const b = beads[Math.floor(Math.random() * beads.length)]; if (!b.run) b.run = .1; }
    }
    if (Math.abs(sunT - sunTarget) > 0.0005) { sunT += (sunTarget - sunT) * (RM ? 1 : .11); busy = true; }
    tick++;
    if (RM) { if (Math.abs(sunT - lastDrawT) > 0.0004) { placeSun(sunT); drawBeads(...GEO.sun(sunT), now); lastDrawT = sunT; } }
    else if (busy || tick % 2 === 0) { placeSun(sunT, now); drawBeads(...GEO.sun(sunT), now); lastDrawT = sunT; } // ambient at ~30 fps
    if (busy || !RM) raf = requestAnimationFrame(frame);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
  function carrySun(clientX) {
    if (RM) return;
    const r = menu.getBoundingClientRect(), x = clientX - r.left, [x0] = GEO.sun(0), [x1] = GEO.sun(1);
    sunTarget = clamp((x - x0) / (x1 - x0), 0, 1); kick();
  }
  menu.addEventListener('pointermove', (e) => { lastInput = performance.now(); carrySun(e.clientX); });
  menu.addEventListener('pointerleave', () => { lastInput = performance.now(); sunTarget = REST_T; kick(); });

  /* ---------- walking the path ---------- */
  const scene = $('#scene');
  let step = 0, current = -1, openPanel = null;
  if (PHONE) $('#q').placeholder = 'Search';
  function setStep(k) {
    step = clamp(k, 0, 5);
    scene.style.transform = `scale(${1 + 0.085 * step})`;
    menu.classList.toggle('stepped', step > 0);
    placeSlates(step);
    slabLabelEls.forEach((el, d) => { el.classList.toggle('is-here', d === step - 1); if (d === step - 1) el.setAttribute('aria-current', 'step'); else el.removeAttribute('aria-current'); });
    const w = $('#walk'); w.setAttribute('aria-label', step === 0 ? 'Walk one step down the path: the story of the week' : step >= 5 ? 'Walk back to the entrance' : `Walk on to ${DAY_LONG[step]}`);
    if (step >= 5) w.querySelector('.back').innerHTML = 'Entrance<i>‹</i>'; else w.querySelector('.back').innerHTML = 'Walk on<i>›</i>';
  }
  $('#walk').addEventListener('click', () => {
    lastInput = performance.now();
    if (PHONE && step === 0) { setStep(1); showList({ kind: 'verdicts' }); return; }
    setStep(step >= 5 ? 0 : step + 1);
  });
  $('#back').addEventListener('click', () => { lastInput = performance.now(); setStep(step - 1); if (step === 0) $('#walk').focus({ preventScroll: true }); });
  let wheelAt = 0;
  menu.addEventListener('wheel', (e) => {
    if (openPanel) return;
    e.preventDefault(); const now = performance.now(); if (now - wheelAt < 450) return; wheelAt = now; lastInput = now;
    setStep(step + (e.deltaY > 0 ? 1 : -1));
  }, { passive: false });
  let touchY = null;
  menu.addEventListener('touchstart', (e) => { touchY = e.touches[0].clientY; }, { passive: true });
  menu.addEventListener('touchend', (e) => {
    if (touchY == null || openPanel) return; const dy = e.changedTouches[0].clientY - touchY; touchY = null;
    if (Math.abs(dy) > 44) { lastInput = performance.now(); setStep(step + (dy < 0 ? 1 : -1)); }
  });

  /* ---------- beds: hover, select, face ---------- */
  function setCurrent(i, focus) {
    current = i;
    bedEls.forEach((el, k) => el.classList.toggle('is-current', k === i));
    slateEls.forEach((el, k) => el.classList.toggle('is-current', k === i));
    placeSlates(step);
    if (focus && i >= 0) bedEls[i].focus({ preventScroll: true });
  }
  bedEls.forEach((el, i) => {
    el.addEventListener('pointerenter', () => setCurrent(i));
    el.addEventListener('focus', () => setCurrent(i));
    el.addEventListener('click', () => { lastInput = performance.now(); face(i); });
    el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); face(i); } });
  });
  slateEls.forEach((el, i) => el.addEventListener('click', () => face(i)));
  garden.addEventListener('pointerleave', () => { if (!openPanel) setCurrent(-1); });
  slabLabelEls.forEach((el, d) => el.addEventListener('click', () => day(d)));

  /* ---------- signals, sorting, rows ---------- */
  const fmt = (n) => n.toLocaleString('en-GB');
  const tz = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Brussels', hour: '2-digit', minute: '2-digit', hour12: false });
  const dayIdx = (t) => (new Date(t.start).getUTCDate() - 5);  // the week runs Mon 5 to Fri 9 Oct; no talk starts before 06:00 UTC
  const timeOf = (t) => tz.format(new Date(t.start));
  const speakers = (t) => t.speakers.map((s) => s.name).join(', ');
  const SORTS = {
    views: { label: 'Most seen', key: (t) => t.views == null ? -1 : t.views, signal: (t) => t.views == null ? 'no video, summary only' : `<b>${fmt(t.views)}</b> views` },
    likeRate: { label: 'Best liked', key: (t) => (t.thin ? -1000 : 0) + (t.likeRate || 0), signal: (t) => t.views == null ? 'no video, summary only' : `<b>${t.likeRate}</b> likes per 100 views${t.thin ? ' <span class="few">· few votes</span>' : ''}` },
    hearts: { label: 'Most hearts', key: (t) => t.hearts || 0, signal: (t) => `<b>${fmt(t.hearts || 0)}</b> hearts before the talk` },
    time: { label: 'Time order', key: (t) => -new Date(t.start).getTime(), signal: (t) => t.views == null ? 'no video, summary only' : `<b>${fmt(t.views)}</b> views` },
  };
  function sorted(list, by) { const k = SORTS[by].key; return [...list].sort((a, b) => k(b) - k(a)); }
  function row(t, by, extra) {
    const x = extra || {};
    return `<button class="row" type="button" data-id="${t.id}"${x.label ? ` aria-label="${esc(x.label)}"` : ''}>${x.before || ''}<span class="t">${x.num ? `<span class="pn">${x.num}</span>` : ''}${by === 'time' ? `<span class="time">${timeOf(t)}</span>` : ''}${esc(t.title)}</span>` +
      `<span class="m">${esc(speakers(t))} · ${esc(t.room)} · ${t.minutes} min · ${SORTS[by].signal(t)}</span>${x.after || ''}</button>`;
  }

  /* ---------- the list on the path ---------- */
  const listEl = $('#list'), faceEl = $('#face');
  let listState = null;
  function showList(state) {
    listState = Object.assign({ by: 'views' }, state);
    const { kind } = listState;
    let items, title, sub, sorts = ['views', 'likeRate', 'hearts'], extra = () => '';
    if (kind === 'search') {
      const q = listState.q.trim().toLowerCase();
      items = talks.filter((t) => hay(t).includes(q));
      title = `“${esc(listState.q.trim())}”`; sub = items.length === 1 ? '1 talk' : `${items.length} talks`;
    } else if (kind === 'day') {
      items = talks.filter((t) => dayIdx(t) === listState.day); title = DAY_LONG[listState.day]; sub = `${items.length} talks`;
      sorts = ['time', 'views', 'likeRate', 'hearts']; if (!state.by) listState.by = 'time';
    } else if (kind === 'verdict') {
      const tr = trends[listState.i]; items = tr.talkIds.map((id) => byId.get(id)).filter(Boolean);
      title = tr.title; sub = `${items.length} talks cited, ${tr.count} in all`;
    } else if (kind === 'picks') {
      items = picks.map((p) => byId.get(p.talkId)).filter(Boolean); title = 'Watch first'; sub = 'one pick per verdict, numbered like the beds'; sorts = [];
      extra = (t) => { const p = picks.find((x) => x.talkId === t.id), n = trends.findIndex((tr) => tr.title === p.verdict) + 1;
        return { num: n, label: `Verdict ${n}, ${p.verdict}: ${t.title}`, after: `<span class="why">${esc(p.why)}</span>` }; };
    } else if (kind === 'verdicts') {
      items = []; title = 'The 8 verdicts'; sub = 'the story of the week'; sorts = [];
    } else { items = talks; title = 'Every talk'; sub = `${talks.length}, summarised`; }
    if (sorts.length) items = sorted(items, listState.by);
    const head = `<div class="panel-head"><h2>${title}<small>${sub}</small></h2>` +
      (sorts.length && items.length ? `<div class="sorts"><span>Sort</span>${sorts.map((s) => `<button type="button" data-by="${s}" aria-pressed="${s === listState.by}">${SORTS[s].label}</button>`).join('')}</div>` : '') +
      `</div><button class="close" type="button" aria-label="Close">×</button>`;
    const by = sorts.length ? listState.by : 'views';
    const body = kind === 'verdicts' ? `<div class="rows">${trends.map((t, i) => `<button class="row verdict" type="button" data-i="${i}"><span class="t"><span class="n">${i + 1}</span> ${esc(t.title)}</span><span class="m">${t.count} talks · ${esc(t.consensus.split(/(?<=[.!?])\s/)[0])}</span></button>`).join('')}</div>` :
      items.length ? `<div class="rows">${items.map((t) => row(t, by, extra(t))).join('')}</div>` :
      `<div class="empty">No talk matches “${esc(listState.q)}”.<small>Try a speaker, a company, a topic such as “Valhalla” or “MCP”, or walk the path instead.</small></div>`;
    listEl.innerHTML = head + body;
    listEl.classList.toggle('narrow', kind === 'search');
    listEl.classList.toggle('picks', kind === 'picks');
    listEl.hidden = false; faceEl.hidden = true; openPanel = 'list';
    menu.classList.add('deep'); menu.classList.toggle('cover', kind !== 'search');
    if (kind === 'picks') listEl.setAttribute('aria-label', 'Watch first: eight picks with their reasons'); else listEl.setAttribute('aria-label', title);
    const first = listEl.querySelector('.rows .row');
    if (first && kind !== 'search' && !state.keepFocus) first.focus({ preventScroll: true });
    cue(listEl.querySelector('.rows'));
  }
  // a scroll cue on any list that runs past its panel: a strip that says how much is below, gone at the bottom
  function cue(box) {
    if (!box) return;
    const host = box.parentElement;
    let c = host.querySelector(':scope > .cue');
    const upd = () => {
      const left = box.scrollHeight - box.clientHeight - box.scrollTop;
      if (left > 6) {
        if (!c) { c = document.createElement('div'); c.className = 'cue'; c.setAttribute('aria-hidden', 'true'); host.appendChild(c); }
        const rows = [...box.querySelectorAll('.row, .side')].filter((r) => r.offsetTop + r.offsetHeight > box.scrollTop + box.clientHeight + 4).length;
        c.textContent = rows > 1 ? `↓ ${rows} more below` : '↓ more below';
        c.style.top = (box.offsetTop + box.clientHeight - 30) + 'px';
        c.hidden = false;
      } else if (c) c.hidden = true;
    };
    upd(); box.addEventListener('scroll', upd, { passive: true });
  }
  listEl.addEventListener('click', (e) => {
    const s = e.target.closest('.sorts button'); if (s) { showList(Object.assign({}, listState, { by: s.dataset.by })); return; }
    if (e.target.closest('.close')) { closeAll(); return; }
    const r = e.target.closest('.row'); if (!r) return;
    if (r.classList.contains('verdict')) face(+r.dataset.i); else window.openTalk(+r.dataset.id);
  });
  const hayCache = new Map();
  function hay(t) {
    if (!hayCache.has(t.id)) hayCache.set(t.id, [t.title, speakers(t), t.speakers.map((s) => s.company || '').join(' '), (t.keywords || []).join(' '), (t.themes || []).join(' '), t.tldr, t.track].join(' | ').toLowerCase());
    return hayCache.get(t.id);
  }
  function day(d) { lastInput = performance.now(); showList({ kind: 'day', day: d, by: 'time' }); }

  /* ---------- search: the sun finds the leaves ---------- */
  const q = $('#q');
  let searchTimer = 0;
  function lightLeaves(query) {
    const s = query.trim().toLowerCase();
    if (!s) { bedEls.forEach((el) => el.classList.remove('lit', 'shade')); return; }
    const hit = new Set(talks.filter((t) => hay(t).includes(s)).map((t) => t.id));
    trends.forEach((tr, i) => {
      const on = tr.talkIds.some((id) => hit.has(id));
      bedEls[i].classList.toggle('lit', on); bedEls[i].classList.toggle('shade', !on);
    });
  }
  q.addEventListener('input', () => {
    lastInput = performance.now();
    clearTimeout(searchTimer);
    const v = q.value;
    lightLeaves(v);
    searchTimer = setTimeout(() => { if (v.trim()) showList({ kind: 'search', q: v, keepFocus: true }); else if (listState && listState.kind === 'search') closeAll(true); }, 90);
  });
  $('#search').addEventListener('submit', (e) => { e.preventDefault(); if (q.value.trim()) showList({ kind: 'search', q: q.value }); });

  /* ---------- a bed faced: consensus, debate, the pick, the talks ---------- */
  function faceSvg(i) {
    const g = grown[i], c = PLAN[i];
    return `<svg viewBox="-82 -186 164 212" aria-hidden="true"><g transform="translate(0 0)">` +
      `<g class="trellis-g">${trellisMarkup(g.trellis, g.box)}</g>` +
      `<g class="shadow-wrap" transform="rotate(-28)"><use href="#plant-${i}" class="shadow" transform="scale(1 -.42)"/></g>` +
      `<g class="plant" fill="${c.fill}" stroke="${c.stroke}"><use href="#plant-${i}"/></g>` +
      `<g class="flower" transform="translate(${f1(g.flower[0])} ${f1(g.flower[1])}) scale(1.25)">${FLOWER}</g></g></svg>`;
  }
  function face(i) {
    const tr = trends[i], p = pickOf(i), pt = byId.get(p.talkId);
    setCurrent(i);
    const sides = tr.debate.sides.map((s, k) => {
      const m = s.stance.match(/^(.*?[.!?])\s+(.*)$/), lead = m ? m[1] : s.stance, rest = m ? m[2] : '';
      const who = s.who.map((name) => {
        const t = s.talkIds.map((id) => byId.get(id)).find((x) => x && x.speakers.some((sp) => sp.name === name)) || s.talkIds.map((id) => byId.get(id))[0];
        return t ? `<button type="button" data-id="${t.id}" title="${esc(t.title)}">${esc(name)}</button>` : `<button type="button" disabled>${esc(name)}</button>`;
      }).join('');
      return `<div class="side" data-k="${k}"><b>${esc(lead)}</b><span class="st">${esc(rest)}</span><div class="who">${who}</div></div>`;
    }).join('');
    faceEl.innerHTML = `<div class="plantside">${faceSvg(i)}` +
      `<button class="pick" type="button" data-id="${pt.id}">✿ Watch first: <b>${esc(pt.title)}</b>${esc(speakers(pt))} · ${pt.minutes} min</button></div>` +
      `<div class="board"><div class="panel-head"><h2><span class="n">${i + 1}</span> ${esc(tr.title)}<small>${tr.count} talks</small></h2></div>` +
      `<p class="consensus">${esc(tr.consensus)}</p>` +
      `<div class="debate"><p class="q"><span>THE DEBATE</span>${esc(tr.debate.question)}</p><div class="sides" style="--n:${tr.debate.sides.length}">${sides}</div></div>` +
      `<div class="tail"><button class="chalk-btn list-talks" type="button">The ${tr.talkIds.length} talks cited, sorted ›</button>` +
      `<div class="nav"><button class="chalk-btn prev" type="button" aria-label="Previous bed">‹</button><button class="chalk-btn next" type="button" aria-label="Next bed">›</button></div></div></div>` +
      `<button class="close" type="button" aria-label="Close, back to the path">×</button>`;
    faceEl.hidden = false; listEl.hidden = true; openPanel = 'face';
    menu.classList.add('deep', 'cover');
    faceEl.querySelector('h2').setAttribute('tabindex', '-1');
    faceEl.querySelector('h2').focus({ preventScroll: true });
    cue(faceEl.querySelector('.debate'));
  }
  faceEl.addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.classList.contains('close')) closeAll();
    else if (b.classList.contains('prev')) face((current + 7) % 8);
    else if (b.classList.contains('next')) face((current + 1) % 8);
    else if (b.classList.contains('list-talks')) showList({ kind: 'verdict', i: current });
    else if (b.dataset.id) window.openTalk(+b.dataset.id);
  });
  $('#watch-first').addEventListener('click', () => { lastInput = performance.now(); showList({ kind: 'picks' }); });
  $('#brand').addEventListener('click', (e) => { e.preventDefault(); lastInput = performance.now(); showList({ kind: 'all' }); });

  function closeAll(keepSearch) {
    const was = openPanel;
    listEl.hidden = true; faceEl.hidden = true; openPanel = null; listState = null;
    menu.classList.remove('deep', 'cover');
    if (!keepSearch) { q.value = ''; lightLeaves(''); }
    if (was === 'face' && current >= 0) bedEls[current].focus({ preventScroll: true });
    else if (was) menu.focus({ preventScroll: true });
  }

  /* ---------- open a talk ---------- */
  const toast = $('#toast');
  let toastTimer = 0;
  const LEAF_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20C4 10 10 4 21 3C20 14 14 20 4 20Z" fill="currentColor"/><path d="M4 20L14 10" stroke="#22302f" stroke-width="1.6" fill="none"/></svg>';
  window.openTalk = function (id) {
    const t = byId.get(id); if (!t) return;
    toast.innerHTML = LEAF_ICON + `<span>${t.seat ? `Walking to <b>${esc(t.room)}</b>` : 'Opening the summary'}</span>`;
    toast.classList.add('show');
    menu.querySelectorAll('.chosen').forEach((el) => el.classList.remove('chosen'));
    menu.querySelectorAll(`[data-id="${id}"]`).forEach((el) => el.classList.add('chosen'));
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.classList.remove('show'); menu.querySelectorAll('.chosen').forEach((el) => el.classList.remove('chosen')); }, 2600);
  };

  /* ---------- keys ---------- */
  document.addEventListener('keydown', (e) => {
    lastInput = performance.now();
    const inField = e.target === q;
    if (e.key === 'Escape') {
      e.preventDefault();
      if (openPanel) { closeAll(); return; }
      if (q.value) { q.value = ''; lightLeaves(''); return; }
      setStep(0); setCurrent(-1); menu.focus({ preventScroll: true }); return;
    }
    if (inField) return;
    if (e.target.closest && e.target.closest('#list, #face') && !['ArrowLeft', 'ArrowRight'].includes(e.key)) {
      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && /\S/.test(e.key)) { q.focus(); }
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); setStep(step + 1); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); setStep(step - 1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); if (openPanel === 'face') face((current + 1) % 8); else setCurrent(current < 0 ? 0 : (current + 1) % 8, true); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); if (openPanel === 'face') face((current + 7) % 8); else setCurrent(current < 0 ? 7 : (current + 7) % 8, true); }
    else if (/^[1-8]$/.test(e.key) && !e.ctrlKey && !e.metaKey) { e.preventDefault(); setCurrent(+e.key - 1, true); if (!menu.classList.contains('stepped')) setStep(1); }
    else if (e.key === 'Enter' && current >= 0 && document.activeElement === bedEls[current]) { /* handled on the bed */ }
    else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && /\S/.test(e.key) && !(e.target.tagName === 'BUTTON' && e.key === ' ')) { q.focus(); }
  });
  menu.addEventListener('pointerdown', () => { lastInput = performance.now(); });
  $('#text-version').addEventListener('click', () => { lastInput = performance.now(); });

  /* ---------- go ---------- */
  setStep(0);
  if (document.fonts) document.fonts.ready.then(() => placeSlates(step));
  placeSun(sunT); drawBeads(...GEO.sun(sunT), performance.now());
  kick();
})();
