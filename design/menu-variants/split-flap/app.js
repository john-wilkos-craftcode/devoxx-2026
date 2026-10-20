(function () {
  'use strict';
  var M = window.MENU;
  var $menu = document.getElementById('menu');
  var PHONE = new URLSearchParams(location.search).get('shape') === 'phone';
  var REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  $menu.dataset.shape = PHONE ? 'phone' : 'laptop';
  var TEXT_SITE = '../../../site/index.html';
  var TZ = 'Europe/Brussels';

  /* ---------- helpers ---------- */
  function el(tag, attrs) {
    var n = document.createElement(tag);
    for (var k in (attrs || {})) {
      var v = attrs[k];
      if (v == null || v === false) continue;
      if (k.slice(0, 2) === 'on') n.addEventListener(k.slice(2), v);
      else if (k === 'class') n.className = v;
      else if (k === 'text') n.textContent = v;
      else if (k === 'style') n.style.cssText = v;
      else n.setAttribute(k, v === true ? '' : v);
    }
    for (var i = 2; i < arguments.length; i++) add(n, arguments[i]);
    return n;
  }
  function add(n, k) {
    if (k == null || k === false) return;
    if (Array.isArray(k)) k.forEach(function (x) { add(n, x); });
    else n.appendChild(typeof k === 'string' ? document.createTextNode(k) : k);
  }
  function fold(s) { return String(s).normalize('NFD').replace(/[̀-ͯ]/g, ''); }

  /* ---------- the drum ---------- */
  var DRUM = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;-'/?&+*()%#!";
  var N = DRUM.length;
  function norm(s) {
    return fold(s).toUpperCase().replace(/[–—]/g, '-').replace(/[‘’`“”"]/g, "'")
      .replace(/[^ A-Z0-9.,:;\-'\/?&+*()%#!]/g, ' ');
  }
  var STEP = REDUCED ? 0 : 32;
  document.documentElement.style.setProperty('--S', STEP + 'ms');

  function Cell() {
    var mk = function (c) { return el('span', { class: 'h ' + c }, el('i', { text: ' ' })); };
    this.t = mk('t'); this.b = mk('b'); this.ft = mk('ft'); this.fb = mk('fb');
    this.node = el('span', { class: 'c' }, this.t, this.b, this.ft, this.fb);
    this.cur = ' '; this.tgt = ' '; this.timer = null; this.hit = false; this.phase = 0;
  }
  Cell.prototype.paint = function (ch) {
    var v = ch === ' ' ? ' ' : ch;
    this.t.firstChild.textContent = v; this.b.firstChild.textContent = v;
  };
  Cell.prototype.set = function (ch, delay, hit) {
    this.hit = !!hit;
    if (REDUCED) {
      clearTimeout(this.timer); this.timer = null;
      this.cur = this.tgt = ch; this.paint(ch); this.node.classList.toggle('hit', this.hit); return;
    }
    if (this.timer == null && ch === this.cur) { this.tgt = ch; this.node.classList.toggle('hit', this.hit); return; }
    this.tgt = ch;
    if (this.timer != null) return;
    var self = this;
    this.K = 2 + ((Math.random() * 4) | 0);
    this.timer = setTimeout(function () { self.step(); }, delay);
  };
  Cell.prototype.step = function () {
    var ci = DRUM.indexOf(this.cur), ti = DRUM.indexOf(this.tgt);
    if (ci === ti) { this.land(); return; }
    this.node.classList.remove('hit');
    var rem = (ti - ci + N) % N;
    var ni = rem > this.K ? (ti - this.K + 1 + N) % N : (ci + 1) % N;
    var nx = DRUM[ni], cur = this.cur, self = this;
    var v = function (c) { return c === ' ' ? ' ' : c; };
    this.t.firstChild.textContent = v(nx); this.fb.firstChild.textContent = v(nx);
    this.b.firstChild.textContent = v(cur); this.ft.firstChild.textContent = v(cur);
    this.phase = 3 - this.phase || 1;
    this.node.classList.remove('go1', 'go2');
    this.node.classList.add('go' + this.phase);
    this.timer = setTimeout(function () {
      self.cur = nx; self.paint(nx);
      self.node.classList.remove('go1', 'go2');
      self.step();
    }, STEP);
  };
  Cell.prototype.land = function () {
    this.timer = null;
    if (this.hit) {
      this.node.classList.add('hit', 'found');
      var n = this.node;
      setTimeout(function () { n.classList.remove('found'); }, 600);
    }
  };

  function Strip(n) {
    this.n = n; this.cells = [];
    this.node = el('span', { class: 'strip', 'aria-hidden': 'true' });
    for (var i = 0; i < n; i++) { var c = new Cell(); this.cells.push(c); this.node.appendChild(c.node); }
  }
  Strip.prototype.set = function (str, o) {
    o = o || {};
    var s = norm(str || '').slice(0, this.n);
    var hits = o.hits;
    if (o.right) { var pad = this.n - s.length; s = ' '.repeat(pad) + s; if (hits) hits = new Array(pad).fill(0).concat(hits); }
    else s = s + ' '.repeat(this.n - s.length);
    var d = o.delay || 0;
    for (var i = 0; i < this.n; i++) this.cells[i].set(s[i], d + i * 5 + ((Math.random() * 16) | 0), hits && hits[i]);
  };

  /* ---------- data prep ---------- */
  var talks = M.talks, byId = {};
  talks.forEach(function (t) {
    byId[t.id] = t;
    t._f = {
      title: fold(t.title).toLowerCase(),
      who: fold(t.speakers.map(function (s) { return s.name + ' ' + (s.company || ''); }).join(' ')).toLowerCase(),
      kw: fold((t.keywords || []).join(' ')).toLowerCase(),
      th: fold((t.themes || []).join(' ') + ' ' + (t.track || '')).toLowerCase(),
      tldr: fold(t.tldr || '').toLowerCase()
    };
  });
  var tf = function (o) { return new Intl.DateTimeFormat('en-GB', Object.assign({ timeZone: TZ }, o)); };
  var fKey = tf({ year: 'numeric', month: '2-digit', day: '2-digit' }), fTime = tf({ hour: '2-digit', minute: '2-digit', hour12: false }),
    fDay = tf({ weekday: 'short', day: 'numeric' });
  talks.forEach(function (t) {
    var d = new Date(t.start);
    var p = fKey.formatToParts(d).reduce(function (a, x) { a[x.type] = x.value; return a; }, {});
    t._day = p.year + '-' + p.month + '-' + p.day;
    t._time = fTime.format(d);
    t._dayLabel = fDay.format(d).replace(',', '');
  });
  var DAYS = [];
  talks.forEach(function (t) { if (!DAYS.some(function (d) { return d.key === t._day; })) DAYS.push({ key: t._day, label: t._dayLabel }); });
  DAYS.sort(function (a, b) { return a.key < b.key ? -1 : 1; });

  var TYPE = { 'Conference': 'CONF', 'Tools-in-Action': 'TOOLS', 'Lunch Talk': 'LUNCH', 'Keynote': 'KEY', 'Keynote Overflow': 'KEY',
    'Closing Keynote': 'KEY', 'Deep Dive': 'DEEP', 'BOF': 'BOF', 'Hands-on Lab': 'LAB', 'Documentary': 'DOC' };
  function roomCode(r) { return String(r).replace(/^Room\s*/i, 'R').replace(/^BOF\s*/i, 'B'); }
  function fViews(n) { return n == null ? '-' : n >= 10000 ? Math.round(n / 1000) + 'K' : n >= 1000 ? (n / 1000).toFixed(1) + 'K' : String(n); }
  function fRate(t) { return t.likeRate == null ? '-' : t.likeRate.toFixed(2) + (t.thin ? '*' : ''); }
  function names(t) { return t.speakers.map(function (s) { return s.name; }).join(', '); }
  function trendOfPick(p) { return p.verdict; }

  /* ---------- state ---------- */
  var S = { mode: 'story', prev: 'story', q: '', sort: 'views', day: 0, page: 0, detail: null, active: 0 };
  var PAGE_LAP = 8;
  function pageSize() { return PHONE ? (S.mode === 'story' ? 8 : 6) : PAGE_LAP; }
  var tokens = [];

  function matchInfo(t) {
    var score = 0, where = null;
    for (var i = 0; i < tokens.length; i++) {
      var k = tokens[i], hit = false;
      if (t._f.title.indexOf(k) >= 0) { score += 5 + (new RegExp('(^|[^a-z0-9])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(t._f.title) ? 2 : 0); hit = true; }
      if (t._f.who.indexOf(k) >= 0) { score += 4; hit = true; if (!where) where = 'speaker or company'; }
      if (t._f.kw.indexOf(k) >= 0) { score += 3; hit = true; if (!where) where = 'keywords'; }
      if (t._f.th.indexOf(k) >= 0) { score += 2; hit = true; if (!where) where = 'theme or track'; }
      if (t._f.tldr.indexOf(k) >= 0) { score += 1; hit = true; if (!where) where = 'summary'; }
      if (!hit) return null;
    }
    return { score: score, where: where };
  }
  function byViews(a, b) { return (b.t.views == null ? -1 : b.t.views) - (a.t.views == null ? -1 : a.t.views); }
  function sorted(arr) {
    var s = S.sort;
    arr.sort(function (a, b) {
      var r = 0;
      if (s === 'match') r = (b.score || 0) - (a.score || 0);
      else if (s === 'rate') { r = (a.t.thin ? 1 : 0) - (b.t.thin ? 1 : 0) || (b.t.likeRate || 0) - (a.t.likeRate || 0); }
      else if (s === 'hearts') r = (b.t.hearts || 0) - (a.t.hearts || 0);
      return r || byViews(a, b) || a.t.id - b.t.id;
    });
    return arr;
  }
  function items() {
    if (S.mode === 'story') return M.recap.trends.map(function (t, i) { return { kind: 'verdict', i: i, v: t }; });
    if (S.mode === 'picks') return M.picks.map(function (p) { return { kind: 'pick', p: p, t: byId[p.talkId] }; });
    if (S.mode === 'prog') {
      var key = DAYS[S.day].key;
      return talks.filter(function (t) { return t._day === key; })
        .sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : a.room < b.room ? -1 : a.room > b.room ? 1 : 0; })
        .map(function (t) { return { kind: 'prog', t: t }; });
    }
    var arr = [];
    talks.forEach(function (t) {
      if (!tokens.length) arr.push({ t: t });
      else { var m = matchInfo(t); if (m) arr.push({ t: t, score: m.score, where: m.where }); }
    });
    return sorted(arr).map(function (x) { x.kind = 'talk'; return x; });
  }

  /* ---------- text fitting ---------- */
  function cut(s, n) {
    if (s.length <= n) return s;
    var k = s.lastIndexOf(' ', n - 2);
    if (k < n * 0.55) k = n - 2;
    return s.slice(0, k).replace(/[ ,:;-]+$/, '') + '..';
  }
  function wrap2(s, n) {
    if (s.length <= n) return [s, ''];
    var k = s.lastIndexOf(' ', n);
    if (k < 4) k = n;
    return [s.slice(0, k), cut(s.slice(k).trim(), n)];
  }
  function hitMask(str) {
    if (!tokens.length) return null;
    var up = norm(str), m = new Array(up.length).fill(0), any = false;
    tokens.forEach(function (tk) {
      var k = norm(tk), i = -1;
      if (!k.trim()) return;
      while ((i = up.indexOf(k, i + 1)) >= 0) { any = true; for (var j = 0; j < k.length; j++) m[i + j] = 1; }
    });
    return any ? m : null;
  }
  function highlight(text) {
    if (!tokens.length) return text;
    var lo = fold(text).toLowerCase(), mask = new Array(text.length).fill(0), any = false;
    if (lo.length !== text.length) return text;
    tokens.forEach(function (k) { var i = -1; while ((i = lo.indexOf(k, i + 1)) >= 0) { any = true; for (var j = 0; j < k.length; j++) mask[i + j] = 1; } });
    if (!any) return text;
    var out = [], cur = '', on = false;
    for (var i = 0; i < text.length; i++) {
      if (!!mask[i] !== on) { out.push(on ? el('mark', { text: cur }) : cur); cur = ''; on = !!mask[i]; }
      cur += text[i];
    }
    out.push(on ? el('mark', { text: cur }) : cur);
    return out;
  }

  /* ---------- rows ---------- */
  var COLS = PHONE ? null : [5, 38, 8, 5, 4];
  function Row(idx) {
    var self = this;
    this.idx = idx;
    this.node = el('button', { class: 'row', type: 'button', tabindex: '-1',
      onclick: function () { if (self.item) activate(self.item, self.node); },
      onmouseenter: function () { if (self.item) setActive(idx, false); },
      onfocus: function () { if (self.item) setActive(idx, false); },
      onkeydown: rowKey });
    this.strips = [];
    if (PHONE) {
      this.gate = new Strip(3); this.l1 = new Strip(19); this.l2 = new Strip(19);
      this.meta = el('div', { class: 'meta', 'aria-hidden': 'true' });
      this.strips = [this.gate, this.l1, this.l2];
      this.node.appendChild(el('div', { class: 'lines' },
        el('div', { class: 'line' }, this.gate.node, this.l1.node),
        el('div', { class: 'line' }, el('span', { class: 'strip', style: 'width:calc(3*(var(--cw) + 1px) - 1px)', 'aria-hidden': 'true' }), this.l2.node),
        this.meta));
    } else {
      COLS.forEach(function (n) { var s = new Strip(n); self.strips.push(s); self.node.appendChild(s.node); });
    }
  }
  Row.prototype.show = function (item) {
    this.item = item;
    var d = this.idx * 30;
    var n = this.node;
    if (!item) {
      n.disabled = true; n.setAttribute('aria-label', ''); n.setAttribute('tabindex', '-1'); n.removeAttribute('aria-current');
      this.strips.forEach(function (s) { s.set('', { delay: d }); });
      if (this.meta) this.meta.hidden = true;
      return;
    }
    n.disabled = false;
    if (!PHONE) { var story = item.kind === 'verdict'; this.strips[3].node.style.display = story ? 'none' : ''; this.strips[4].node.style.display = story ? 'none' : ''; }
    var sp = spec(item);
    n.setAttribute('aria-label', sp.aria);
    if (PHONE) {
      var w = wrap2(sp.title, 19);
      this.gate.set(sp.gate, { delay: d, right: true });
      this.l1.set(w[0], { delay: d, hits: hitMask(w[0]) });
      this.l2.set(w[1], { delay: d + 30, hits: hitMask(w[1]) });
      this.meta.hidden = !(sp.meta && sp.meta.length);
      this.meta.textContent = ''; (sp.meta || []).forEach(function (m) { this.meta.appendChild(el('span', { text: m })); }, this);
    } else {
      var t = cut(sp.title, 38);
      this.strips[0].set(sp.cols[0], { delay: d, right: true });
      this.strips[1].set(t, { delay: d, hits: hitMask(t) });
      for (var i = 2; i < 5; i++) this.strips[i].set(sp.cols[i], { delay: d, right: true });
    }
  };

  function spec(it) {
    if (it.kind === 'verdict') {
      var v = it.v, split = v.debate.sides.map(function (s) { return s.who.length; }).join('V');
      return { title: v.title, gate: String(v.count), cols: [String(v.count), '', split, '', ''],
        aria: v.title + '. ' + v.count + ' talks. Open the verdict.', meta: null };
    }
    var t = it.t;
    if (it.kind === 'prog') {
      return { title: t.title, gate: roomCode(t.room), cols: [t._time, '', t.room, TYPE[t.type] || '', t.minutes + 'M'],
        meta: [t._dayLabel + ' ' + t._time, t.room, t.type, t.minutes + ' min'],
        aria: t.title + ', ' + t._dayLabel + ' ' + t._time + ', ' + t.room };
    }
    var meta = it.kind === 'pick' ? ['For: ' + it.p.verdict] : [fViews(t.views) + ' views', fRate(t) + ' likes/100 views', t.hearts + ' hearts'];
    return { title: t.title, gate: roomCode(t.room), cols: [roomCode(t.room), '', fViews(t.views), fRate(t), String(t.hearts)],
      meta: meta, aria: t.title + ', ' + names(t) + ', ' + t.room + '. ' + (t.views == null ? 'No video yet' : t.views + ' views') +
        (t.thin ? ', few votes' : ', like rate ' + t.likeRate) + ', ' + t.hearts + ' hearts' };
  }

  /* ---------- skeleton ---------- */
  var tabsDef = [['story', 'The story'], ['picks', 'Watch first'], ['talks', 'All talks'], ['prog', 'Programme']];
  var $tabs = el('div', { class: 'tabs', role: 'group', 'aria-label': 'Board' });
  var tabBtns = {};
  tabsDef.forEach(function (d) {
    var b = el('button', { class: 'tab', type: 'button', 'aria-pressed': 'false', text: d[1], onclick: function () { go(d[0]); } });
    tabBtns[d[0]] = b; $tabs.appendChild(b);
  });
  var $input = el('input', { type: 'search', placeholder: 'Search talks, speakers, tools, topics', 'aria-label': 'Search talks, speakers, companies, keywords, themes',
    autocomplete: 'off', spellcheck: 'false', oninput: onInput, onkeydown: function (e) {
      if (e.key === 'Escape') { if ($input.value) { $input.value = ''; onInput(); e.stopPropagation(); } }
      else if (e.key === 'ArrowDown') { e.preventDefault(); focusRow(S.active); }
    } });
  var $clear = el('button', { class: 'clear', type: 'button', 'aria-label': 'Clear search', text: '×', onclick: function () { $input.value = ''; onInput(); $input.focus(); } });
  var $search = el('div', { class: 'search' }, $input, $clear);
  var $sub = el('div', { class: 'sub' });
  var $heads = el('div', { class: 'heads', 'aria-hidden': 'false' });
  var rows = [];
  var $rows = el('div', { class: 'rows', role: 'list', 'aria-label': 'Departures' });
  for (var ri = 0; ri < (PHONE ? 8 : PAGE_LAP); ri++) { var rw = new Row(ri); rows.push(rw); $rows.appendChild(rw.node); }
  var $board = el('div', { class: 'board' }, $heads, $rows);
  var $annTxt = el('div', { class: 'txt', 'aria-live': 'polite' });
  var $prev = el('button', { type: 'button', 'aria-label': 'Previous page', text: '‹', onclick: function () { turn(-1); } });
  var $next = el('button', { type: 'button', 'aria-label': 'Next page', text: '›', onclick: function () { turn(1); } });
  var $count = el('span', { 'aria-live': 'polite' });
  var $pager = el('div', { class: 'pager' }, $prev, $count, $next);
  var $ann = el('div', { class: 'ann' }, $annTxt, $pager);
  var $main = el('div', { class: 'mainview' });
  $main.style.cssText = 'display:flex;flex-direction:column;flex:1;min-height:0';
  $main.append($sub, $board, $ann);
  var $detail = null;
  var $toast = el('div', { class: 'toast', role: 'status', hidden: true });

  $menu.append(
    el('div', { class: 'top' },
      el('div', { class: 'mark' }, 'DEVOX', el('b', { text: 'X' }), el('span', { text: 'Belgium 2026' })),
      el('a', { class: 'textlink', href: TEXT_SITE, text: 'Text version of every talk' })),
    el('div', { class: 'ctrl' }, $tabs, $search),
    $main, $toast);

  /* ---------- behaviour ---------- */
  function go(mode) {
    closeDetail(true);
    if (mode !== 'talks' && $input.value) { $input.value = ''; setQuery(''); }
    S.mode = mode; S.prev = mode; S.page = 0; S.active = 0;
    if (mode === 'talks' && S.sort === 'match') S.sort = 'views';
    render();
  }
  function setQuery(v) {
    tokens = fold(v).toLowerCase().split(/\s+/).filter(Boolean);
    S.q = v;
    $search.classList.toggle('has', !!v);
  }
  function onInput() {
    var had = S.q.length > 0;
    closeDetail(true);
    setQuery($input.value);
    if (S.q) {
      if (!had) { S.prev = S.mode; S.sort = 'match'; }
      S.mode = 'talks';
    } else {
      if (S.sort === 'match') S.sort = 'views';
      S.mode = S.prev === 'talks' ? 'talks' : S.prev;
    }
    S.page = 0; S.active = 0;
    render();
  }
  function setSort(k) { S.sort = k; S.page = 0; S.active = 0; if (S.mode !== 'talks') { S.mode = 'talks'; S.prev = 'talks'; } render(); }
  function turn(d) { var tot = Math.ceil(items().length / pageSize()); S.page = Math.max(0, Math.min(tot - 1, S.page + d)); S.active = 0; render(); }
  var list = [];
  function activate(it, opener) {
    if (it.kind === 'verdict') openVerdict(it.i, opener);
    else if (it.kind === 'pick' || it.kind === 'talk' || it.kind === 'prog') openTalk((it.t || byId[it.p.talkId]).id);
  }
  function setActive(i, focus) {
    S.active = i;
    rows.forEach(function (r) {
      if (r.item) { r.node.setAttribute('aria-current', r.idx === i ? 'true' : 'false'); r.node.setAttribute('tabindex', r.idx === i ? '0' : '-1'); }
    });
    renderAnn();
    if (focus) rows[i].node.focus();
  }
  function focusRow(i) { var r = rows[Math.min(i, pageCount() - 1)]; if (r && r.item) { setActive(r.idx, true); } }
  function pageCount() { return Math.min(pageSize(), list.length - S.page * pageSize()); }
  function rowKey(e) {
    var k = e.key, n = pageCount();
    if (k === 'ArrowDown') { e.preventDefault(); if (S.active < n - 1) setActive(S.active + 1, true); else if ((S.page + 1) * pageSize() < list.length) { turn(1); focusRow(0); } }
    else if (k === 'ArrowUp') { e.preventDefault(); if (S.active > 0) setActive(S.active - 1, true); else if (S.page > 0) { turn(-1); focusRow(pageSize() - 1); } else $input.focus(); }
    else if (k === 'Home') { e.preventDefault(); setActive(0, true); }
    else if (k === 'End') { e.preventDefault(); setActive(n - 1, true); }
    else if (k === 'PageDown' || k === 'ArrowRight') { e.preventDefault(); turn(1); focusRow(0); }
    else if (k === 'PageUp' || k === 'ArrowLeft') { e.preventDefault(); turn(-1); focusRow(0); }
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && $detail) { closeDetail(); e.preventDefault(); }
    else if (e.key === '/' && document.activeElement !== $input && !e.ctrlKey && !e.metaKey) { e.preventDefault(); $input.focus(); $input.select(); }
  });

  function renderHeads() {
    $heads.textContent = '';
    if (PHONE) return;
    var m = S.mode, def;
    if (m === 'story') def = [['Talks', 5, 1], ['Verdict', 38], ['Split', 8, 1], ['', 5], ['', 4]];
    else if (m === 'prog') def = [['Time', 5, 1], ['Talk', 38], ['Room', 8, 1], ['Type', 5, 1], ['Min', 4, 1]];
    else def = [['Room', 5, 1], ['Talk', 38], ['Views', 8, 1, 'views'], ['Like rate', 5, 1, 'rate'], ['Hearts', 4, 1, 'hearts']];
    def.forEach(function (d) {
      var node;
      if (d[3] && m === 'talks') node = el('button', { type: 'button', 'aria-pressed': String(S.sort === d[3]), text: d[0], title: 'Sort by ' + d[0].toLowerCase(), onclick: function () { setSort(d[3]); } });
      else node = el('span', { text: d[0] });
      var w = el('div', { class: d[2] ? 'r' : '', style: '--n:' + d[1] }, node);
      $heads.appendChild(w);
    });
    $heads.style.gap = '12px';
  }
  function renderSub() {
    $sub.textContent = '';
    var intro = M.recap.intro, first = intro.split(/(?<=\.)\s/)[0];
    if (PHONE && /^Devoxx Belgium 2026 was mostly about working with coding agents/.test(intro))
      first = 'Mostly about working with coding agents: how to check, review and contain them.';
    if (S.mode === 'story') $sub.appendChild(el('p', { class: 'lede', text: first }));
    else if (S.mode === 'picks') $sub.appendChild(el('p', {}, 'One talk per verdict to watch first, ' + (M.picksNote ? M.picksNote.replace(/^provisional, /, 'provisional: ') : '') + '. Open one to walk to its seat.'));
    else if (S.mode === 'prog') {
      var chips = el('div', { class: 'chips', role: 'group', 'aria-label': 'Day' });
      DAYS.forEach(function (d, i) { chips.appendChild(el('button', { class: 'chip', type: 'button', 'aria-pressed': String(S.day === i), text: d.label, onclick: function () { S.day = i; S.page = 0; S.active = 0; render(); } })); });
      $sub.appendChild(chips);
      var jumps = el('div', { class: 'chips', role: 'group', 'aria-label': 'Jump to' });
      [['Morning', '00:00'], ['Lunch', '12:00'], ['Afternoon', '14:00'], ['Evening', '17:30']].forEach(function (j) {
        jumps.appendChild(el('button', { class: 'chip jump', type: 'button', text: j[0], title: 'Jump to ' + j[1], onclick: function () {
          var l = items(), k = l.findIndex(function (x) { return x.t._time >= j[1]; });
          S.page = Math.max(0, Math.floor((k < 0 ? l.length - 1 : k) / pageSize())); S.active = 0; render();
        } }));
      });
      $sub.appendChild(jumps);
      if (PHONE) { $sub.style.flexDirection = 'column'; $sub.style.alignItems = 'flex-start'; $sub.style.gap = '4px'; }
      else $sub.appendChild(el('p', { class: 'legend', text: 'Europe/Brussels time.' }));
    } else {
      var ch = el('div', { class: 'chips', role: 'group', 'aria-label': 'Sort by' });
      var opts = [['views', 'Views'], ['rate', 'Like rate'], ['hearts', 'Hearts']];
      if (S.q) opts.unshift(['match', 'Best match']);
      opts.forEach(function (o) { ch.appendChild(el('button', { class: 'chip', type: 'button', 'aria-pressed': String(S.sort === o[0]), text: o[1], onclick: function () { setSort(o[0]); } })); });
      if (PHONE) { $sub.appendChild(ch); }
      else $sub.appendChild(ch);
      $sub.appendChild(el('p', { class: 'legend', text: PHONE ? '* few votes (under 20 likes). Hearts are interest before the talk, not quality.'
        : 'Views: reach. Like rate: likes per 100 views; * means few votes (under 20 likes), so those sort last. Hearts: Devoxx app favourites before the talk, interest not quality.' }));
      if (PHONE) $sub.style.flexDirection = 'column', $sub.style.alignItems = 'flex-start', $sub.style.gap = '4px';
    }
    if (PHONE && S.mode !== 'talks' && S.mode !== 'prog') { $sub.style.flexDirection = ''; $sub.style.alignItems = ''; $sub.style.gap = ''; }
  }
  function renderAnn() {
    if (PHONE) return;
    var it = list[S.page * pageSize() + S.active];
    $annTxt.textContent = '';
    if (!it) {
      if (S.mode === 'talks' && S.q) $annTxt.append(el('p', { class: 'ttl', text: 'No talks match "' + S.q + '".' }), el('p', { class: 'dim', text: 'Try a speaker, a company, a tool or a topic, with fewer words.' }));
      return;
    }
    if (it.kind === 'verdict') {
      var v = it.v;
      $annTxt.append(el('p', { class: 'ttl', text: v.title }),
        el('p', { class: 'clamp' }, el('span', { class: 'dim', text: 'Agreed: ' }), v.consensus),
        el('p', { class: 'dim', text: 'Split (' + v.debate.sides.map(function (x) { return x.who.length; }).join(' v ') + ' speakers): ' + v.debate.question }));
      return;
    }
    var t = it.t;
    var when = t._dayLabel + ' ' + t._time + ', ' + t.room;
    if (it.kind === 'pick') {
      $annTxt.append(el('p', { class: 'ttl' }, highlight(t.title)),
        el('p', { class: 'dim', text: names(t) + ' (' + when + ')' }),
        el('p', { class: 'clamp' }, el('span', { class: 'dim', text: 'Watch first for "' + trendOfPick(it.p) + '": ' }), it.p.why));
      return;
    }
    $annTxt.append(el('p', { class: 'ttl' }, highlight(t.title)),
      el('p', { class: 'dim' }, highlight(t.speakers.map(function (s) { return s.name + (s.company ? ', ' + s.company : ''); }).join('; ')), ' (' + when + ')'),
      el('p', { class: 'clamp' }, it.where ? [el('span', { class: 'dim', text: 'Matches ' + it.where + ': ' }), highlight(t.tldr)] : highlight(t.tldr)));
  }
  function render() {
    list = items();
    var ps = pageSize(), tot = Math.max(1, Math.ceil(list.length / ps));
    S.page = Math.min(S.page, tot - 1);
    if (S.active >= Math.min(ps, list.length - S.page * ps)) S.active = 0;
    $menu.dataset.mode = S.mode;
    Object.keys(tabBtns).forEach(function (k) { tabBtns[k].setAttribute('aria-pressed', String(S.mode === k)); });
    renderHeads(); renderSub();
    var slice = list.slice(S.page * ps, S.page * ps + ps);
    var empty = !slice.length && S.mode === 'talks';
    rows.forEach(function (r, i) {
      var it = i < ps ? slice[i] : null;
      r.node.style.display = i < ps ? '' : 'none';
      r.show(it);
      if (it) { r.node.setAttribute('aria-current', i === S.active ? 'true' : 'false'); r.node.setAttribute('tabindex', i === S.active ? '0' : '-1'); }
    });
    $count.textContent = list.length ? (S.page * ps + 1) + '–' + Math.min(list.length, S.page * ps + ps) + ' of ' + list.length : '0 results';
    $pager.style.visibility = tot > 1 || S.mode === 'talks' ? 'visible' : 'hidden';
    $prev.disabled = S.page === 0; $next.disabled = S.page >= tot - 1;
    renderAnn();
    if (empty) { rows[0].strips[1].set('NO TALKS MATCH', { delay: 0 }); }
  }

  /* ---------- verdict detail ---------- */
  function openVerdict(i, opener) {
    var v = M.recap.trends[i];
    var pick = M.picks.filter(function (p) { return p.verdict === v.title; })[0];
    S.detail = i;
    $main.style.display = 'none';
    var split = v.debate.sides.map(function (s) { return s.who.length; }).join('V');
    var flap = el('div', { class: 'dflap', role: 'img', 'aria-label': v.title }), ss = [];
    if (PHONE) {
      var w = wrap2(norm(v.title), 19);
      [w[0], w[1]].forEach(function (txt, k) {
        var g = new Strip(3), t = new Strip(19); ss.push([g, k ? '' : String(v.count), true], [t, txt]);
        flap.appendChild(el('div', { class: 'line', style: 'gap:6px' }, g.node, t.node));
      });
    } else {
      var a = new Strip(5), b = new Strip(38), c = new Strip(8);
      ss.push([a, String(v.count), true], [b, v.title], [c, split, true]);
      flap.appendChild(el('div', { class: 'line' }, a.node, b.node, c.node));
      var qq = wrap2(norm(v.debate.question), 58);
      qq.forEach(function (txt) {
        if (!txt) return;
        var s = new Strip(58); ss.push([s, txt]);
        flap.appendChild(el('div', { class: 'line' }, s.node));
      });
    }
    var tb = function (id) {
      var t = byId[id];
      return el('li', {}, el('button', { class: 'tl', type: 'button', onclick: function () { openTalk(id); }, title: t.title },
        t.title, el('small', { text: t.room + (t.views != null ? ', ' + fViews(t.views) + ' views' : '') })));
    };
    var sides = v.debate.sides.map(function (sd) {
      return el('div', { class: 'side' }, el('p', { text: sd.stance }), el('p', { class: 'who', text: sd.who.join(', ') }),
        el('ul', {}, sd.talkIds.map(tb)));
    });
    var back = el('button', { class: 'back', type: 'button', onclick: function () { closeDetail(); }, text: '‹ Back to the board (Esc)' });
    $detail = el('div', { class: 'detail' }, back, flap,
      PHONE ? el('p', { class: 'q', text: v.debate.question }) : null,
      el('p', { class: 'cons' }, el('b', { text: 'Everyone agreed: ' }), v.consensus),
      PHONE ? el('p', { class: 'q', text: 'Where they split' }) : null,
      el('div', { class: 'sides', style: '--sides:' + v.debate.sides.length }, sides),
      pick ? el('p', { class: 'pickline' }, 'Watch first: ', el('button', { type: 'button', onclick: function () { openTalk(pick.talkId); } }, byId[pick.talkId].title),
        ' (' + names(byId[pick.talkId]) + '). ' + pick.why) : null);
    $menu.insertBefore($detail, $toast);
    $detail._opener = opener;
    ss.forEach(function (x, k) { x[0].set(x[1], { delay: k * 70, right: x[2] }); });
    back.focus();
  }
  function closeDetail(quiet) {
    if (!$detail) return;
    var op = $detail._opener;
    $detail.remove(); $detail = null; S.detail = null;
    $main.style.display = 'flex';
    if (!quiet) { render(); if (op && op.isConnected) op.focus(); }
  }

  /* ---------- open a talk ---------- */
  var toastTimer;
  function openTalk(id) {
    var t = byId[id]; if (!t) return;
    $toast.textContent = t.seat ? 'Walking to ' + t.room + ', seat ready' : 'Opening the summary';
    $toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { $toast.hidden = true; }, 2600);
  }
  window.openTalk = openTalk;

  render();
})();
