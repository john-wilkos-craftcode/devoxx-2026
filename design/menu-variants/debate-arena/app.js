/* Devoxx 2026 menu variant: debate-arena. Plain JS, data from window.MENU. */
(function () {
  "use strict";
  var M = window.MENU;
  var PHONE = /[?&]shape=phone/.test(location.search);
  var menu = document.getElementById("menu");
  menu.className = PHONE ? "phone" : "laptop";
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SVGNS = "http://www.w3.org/2000/svg";
  var TEXT_SITE = "../../../site/index.html";

  /* ---------- helpers ---------- */
  function el(tag, attrs) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      var v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "style") n.style.cssText = v;
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (var i = 2; i < arguments.length; i++) add(n, arguments[i]);
    return n;
  }
  function add(n, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(function (x) { add(n, x); });
    else n.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function norm(s) { return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  function surname(name) {
    var w = name.split(" ");
    for (var i = 1; i < w.length; i++) if (/^[a-z]/.test(w[i])) return w.slice(i).join(" ");
    return w[w.length - 1];
  }
  function fmtViews(n) {
    if (n == null) return "no video";
    if (n >= 10000) return Math.round(n / 1000) + "k";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }
  function firstSentence(s) {
    var m = s.match(/^(.+?[.!?])(\s|$)/);
    return m ? [m[1], s.slice(m[0].length)] : [s, ""];
  }

  var T = {}; M.talks.forEach(function (t) { T[t.id] = t; });
  var tz = "Europe/Brussels";
  var fTime = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hour12: false });
  var fDay = new Intl.DateTimeFormat("en-CA", { timeZone: tz });
  var fDayLabel = new Intl.DateTimeFormat("en-GB", { timeZone: tz, weekday: "short", day: "numeric", month: "short" });
  function dayKey(t) { return fDay.format(new Date(t.start)); }

  /* ---------- derived layout: speaker dots from the who lists ---------- */
  var SIDE_COL = ["#F6921E", "#4FD1C5", "#BBA8FF"];
  var V = M.recap.trends.map(function (tr, vi) {
    var sides = tr.debate.sides, n = sides.length;
    var regions = n === 2 ? [[7, 41], [59, 93]] : [[6, 29], [39, 61], [71, 94]];
    var dots = [];
    sides.forEach(function (sd, si) {
      var lo = regions[si][0], hi = regions[si][1], m = sd.who.length;
      sd.who.forEach(function (name, k) {
        var x = m === 1 ? (lo + hi) / 2 : lo + (k + 0.5) / m * (hi - lo);
        var tks = sd.talkIds.filter(function (id) { return T[id] && T[id].speakers.some(function (p) { return p.name === name; }); });
        var company = "";
        tks.forEach(function (id) { T[id].speakers.forEach(function (p) { if (p.name === name && !company) company = p.company; }); });
        dots.push({ name: name, company: company, vi: vi, si: si, x: x, talks: tks, el: null });
      });
    });
    return { vi: vi, tr: tr, sides: sides, dots: dots };
  });
  var crossers = {};
  V.forEach(function (v) { v.dots.forEach(function (d) { (crossers[d.name] = crossers[d.name] || []).push(d); }); });
  Object.keys(crossers).forEach(function (k) { if (crossers[k].length < 2) delete crossers[k]; });
  var pickFor = {};
  M.picks.forEach(function (p) { pickFor[p.verdict] = p; });
  var pickIndex = M.picks.map(function (p) {
    for (var i = 0; i < V.length; i++) if (V[i].tr.title === p.verdict) return i;
    return -1;
  });

  /* ---------- state ---------- */
  var S = { mode: "args", vi: null, q: "", sort: "views", video: false, cited: null, day: null, intro: false, speaker: null };
  var days = []; // [{key,label,count}]
  M.talks.forEach(function (t) {
    if (!t.start) return;
    var k = dayKey(t), d = days.filter(function (x) { return x.key === k; })[0];
    if (!d) { d = { key: k, label: fDayLabel.format(new Date(t.start)).replace(",", ""), count: 0 }; days.push(d); }
    d.count++;
  });
  days.sort(function (a, b) { return a.key < b.key ? -1 : 1; });
  S.day = days[0] && days[0].key;

  /* ---------- toast + openTalk ---------- */
  var toastEl, toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("on"); }, 3200);
  }
  window.openTalk = function (id) {
    var t = T[id];
    if (!t) return;
    toast(t.seat ? "Walking to " + t.room + ", seat ready" : "Opening the summary");
  };

  /* ---------- shell ---------- */
  var headBtn, searchIn, tabsEl, contentEl, footEl, picksEl, introEl, pcard, mainEl;
  var rowEls = [], readout = null, threadSvg = null, stageEl = null;

  function build() {
    clear(menu);
    headBtn = el("button", { class: "headline", type: "button", "aria-expanded": "false", "aria-controls": "intro", onclick: function () { setIntro(!S.intro); } },
      "Mostly about coding agents: how to check, review and contain them", el("span", { class: "more", "aria-hidden": "true" }, " Read the intro"));
    var head = el("header", { class: "head" },
      el("div", { class: "brand" },
        el("div", { class: "wm", "aria-label": "Devoxx" }, "DEVOX", el("span", { class: "x" }, "X")),
        el("div", { class: "bsub" }, "Belgium 2026, " + M.talks.length + " talks")),
      headBtn);
    searchIn = el("input", { type: "search", id: "q", placeholder: "Search talks, speakers, tools", "aria-label": "Search talks, speakers, companies, keywords, topics", autocomplete: "off", spellcheck: "false" });
    searchIn.addEventListener("input", function () {
      S.q = searchIn.value;
      if (S.q.trim() && S.mode !== "talks") { S.mode = "talks"; S.cited = null; }
      renderTabs(); renderContent();
    });
    searchIn.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && searchIn.value) { searchIn.value = ""; S.q = ""; renderContent(); e.stopPropagation(); }
      if (e.key === "ArrowDown") { var f = menu.querySelector(".trow"); if (f) { f.focus(); e.preventDefault(); } }
    });
    var search = el("div", { class: "search" }, el("label", { for: "q", class: "sr" }, "Search"), searchIn);
    tabsEl = el("div", { class: "tabs", role: "tablist" });
    tabsEl.addEventListener("keydown", tabKeys);
    contentEl = el("div", { class: "content" });
    footEl = el("footer", { class: "foot" });
    introEl = el("div", { class: "intro", id: "intro", hidden: true }, el("p", null, M.recap.intro));
    mainEl = el("main", { class: "main" }, tabsEl, contentEl, footEl, introEl);
    picksEl = el("aside", { class: "picks", "aria-label": "Watch first" });
    pcard = el("div", { class: "pcard", hidden: true, "aria-hidden": "true" });
    toastEl = el("div", { class: "toast", role: "status", "aria-live": "polite" });
    menu.appendChild(head); menu.appendChild(search); menu.appendChild(mainEl); menu.appendChild(picksEl); menu.appendChild(pcard); menu.appendChild(toastEl);
    renderPicks(); renderTabs(); renderContent();
  }

  function setIntro(on) {
    S.intro = on;
    introEl.hidden = !on;
    headBtn.setAttribute("aria-expanded", on ? "true" : "false");
  }

  function go(mode, extra) {
    S.mode = mode;
    if (extra) for (var k in extra) S[k] = extra[k];
    setIntro(false);
    renderTabs(); renderContent();
  }

  function renderTabs() {
    clear(tabsEl);
    var list = [["args", "Arguments"], ["talks", "All talks"], ["prog", "Programme"]];
    if (PHONE) list.splice(1, 0, ["picks", "Watch first"]);
    list.forEach(function (t) {
      var on = S.mode === t[0] || (t[0] === "args" && S.mode === "verdict");
      tabsEl.appendChild(el("button", { type: "button", role: "tab", class: "tab", "aria-selected": on ? "true" : "false", onclick: function () {
        if (t[0] === "talks") { S.cited = null; }
        go(t[0]);
      } }, t[1]));
    });
    menu.classList.toggle("show-picks", S.mode === "picks");
    menu.classList.toggle("args-mode", S.mode === "args");
  }
  function tabKeys(e) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    var b = Array.prototype.slice.call(tabsEl.children), i = b.indexOf(document.activeElement);
    if (i < 0) return;
    b[(i + (e.key === "ArrowRight" ? 1 : b.length - 1)) % b.length].focus();
    e.preventDefault();
  }

  function renderFoot() {
    clear(footEl);
    var msg;
    if (S.mode === "args") msg = "Dots are speakers, placed on a side by our reading of the talks. Ringed: " + Object.keys(crossers).map(surname).join(", ") + ", who argued on more than one line.";
    else if (S.mode === "verdict") msg = "Speakers are placed on a side by our reading of the talks.";
    else if (S.mode === "talks") msg = "Hearts are app favourites before the talk: interest, not quality. Under 20 likes is shown as few votes and ranked last.";
    else if (S.mode === "prog") msg = "Times are Europe/Brussels. Open any talk to walk to its room.";
    else msg = "Provisional picks from the signals; editor's picks to follow.";
    footEl.appendChild(el("p", { class: "legend" }, msg));
    footEl.appendChild(el("a", { class: "textlink", href: TEXT_SITE }, "Text version of every talk"));
  }

  function renderContent() {
    clear(contentEl);
    threadSvg = null; readout = null; stageEl = null; rowEls = [];
    contentEl.className = "content mode-" + S.mode;
    if (S.mode === "args") renderArgs();
    else if (S.mode === "verdict") renderVerdict();
    else if (S.mode === "talks") renderTalks();
    else if (S.mode === "prog") renderProg();
    else if (S.mode === "picks") contentEl.appendChild(el("p", { class: "phone-note" }, "See the picks below."));
    renderFoot();
    hidePcard();
  }

  /* ---------- the spectrum (a line between two sides, speakers as dots) ---------- */
  function spectrum(v, big) {
    var n = v.sides.length;
    var segs = [];
    if (n === 2) segs = [[0, 46, 0], [54, 100, 1]];
    else segs = [[0, 34, 0], [37, 63, 1], [66, 100, 2]];
    var s = el("div", { class: "spec" + (big ? " big" : "") });
    segs.forEach(function (g) {
      s.appendChild(el("i", { class: "seg", style: "left:" + g[0] + "%;width:" + (g[1] - g[0]) + "%;background:" + SIDE_COL[g[2]] }));
    });
    s.appendChild(el("i", { class: "gap", style: "left:" + (n === 2 ? 46 : 34) + "%;right:" + (n === 2 ? 46 : 34) + "%" }));
    v.dots.forEach(function (d, k) {
      var isCross = !!crossers[d.name];
      var b = el("button", {
        type: "button", class: "dot" + (isCross ? " cross" : "") + (big && v.sides[d.si].who.length > 2 && v.sides[d.si].who.indexOf(d.name) % 2 ? " lo" : ""), tabindex: big ? "0" : "-1",
        style: "left:" + d.x + "%;--c:" + SIDE_COL[d.si],
        "aria-label": d.name + (d.company ? ", " + d.company : "") + (isCross ? ", argued on more than one line" : "") + (d.talks[0] ? ". Open talk: " + T[d.talks[0]].title : ""),
        onclick: function (e) { e.stopPropagation(); if (d.talks[0]) window.openTalk(d.talks[0]); }
      }, big ? el("span", { class: "dn" }, surname(d.name)) : null);
      if (!big) {
        var rec = v.dots[k]; rec.el = b;
        b.addEventListener("mouseenter", function () { speakerOn(rec); });
        b.addEventListener("focus", function () { speakerOn(rec); });
        b.addEventListener("mouseleave", function () { speakerOff(rec); });
        b.addEventListener("blur", function () { setTimeout(function () { if (!(document.activeElement && document.activeElement.classList.contains("dot"))) speakerOff(rec); }, 0); });
        b.addEventListener("keydown", function (e) { dotKeys(e, rec); });
      }
      s.appendChild(b);
    });
    return s;
  }

  /* ---------- arguments view ---------- */
  var READ_DEFAULT = "Each line is one argument. The dotted middle is what everyone agreed on; the two ends are the sides of the debate, and the dots are the speakers who argued them.";
  function renderArgs() {
    stageEl = el("div", { class: "stage" });
    readout = el("div", { class: "readout", "aria-live": "polite" });
    var rows = el("div", { class: "rows" });
    V.forEach(function (v, i) {
      var title = el("button", { type: "button", class: "rt", onclick: function () { openVerdict(i); }, onkeydown: function (e) { rowKeys(e, i); }, onfocus: function () { if (!S.speaker) readVerdict(i); }, "aria-label": v.tr.title + ". " + v.tr.debate.question + " Open the argument." }, v.tr.title);
      var row = el("div", { class: "row", "data-i": i,
        onmouseenter: function () { if (!S.speaker) readVerdict(i); },
        onclick: function (e) { if (e.target.closest(".dot")) return; openVerdict(i); } },
        title, spectrum(v, false), el("span", { class: "cnt" }, v.tr.count + " talks"));
      rowEls.push(row); rows.appendChild(row);
    });
    rows.addEventListener("mouseleave", function () { if (!S.speaker && !menu.contains(document.activeElement) || (document.activeElement === document.body)) readDefault(); });
    threadSvg = svg("svg", { class: "threads", "aria-hidden": "true" });
    stageEl.appendChild(readout); stageEl.appendChild(rows); stageEl.appendChild(threadSvg);
    contentEl.appendChild(stageEl);
    readDefault();
    if (!reduce && !window.__seen) { threadSvg.classList.add("unspool"); window.__seen = 1; }
    requestAnimationFrame(drawRest);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(drawRest);
  }

  function readDefault() { if (readout) { clear(readout); readout.appendChild(el("p", { class: "r-note" }, READ_DEFAULT)); } }
  function readVerdict(i) {
    if (!readout) return;
    var v = V[i]; clear(readout);
    readout.appendChild(el("p", { class: "r-line r-two" }, el("b", null, "Everyone agreed: "), v.tr.consensus));
    readout.appendChild(el("p", { class: "r-line r-one" }, el("b", null, "They split on: "), v.tr.debate.question));
  }

  /* ---------- signature: pulling a thread ---------- */
  function center(elm, base) {
    var r = elm.getBoundingClientRect();
    return { x: r.left + r.width / 2 - base.left, y: r.top + r.height / 2 - base.top };
  }
  function curve(a, b, cls) {
    var d = (b.y - a.y) * 0.5;
    var p = svg("path", { class: cls, d: "M" + a.x + "," + a.y + " C" + a.x + "," + (a.y + d) + " " + b.x + "," + (b.y - d) + " " + b.x + "," + b.y });
    return p;
  }
  function drawRest() {
    if (!threadSvg || PHONE) return;
    clear(threadSvg);
    var base = stageEl.getBoundingClientRect();
    Object.keys(crossers).forEach(function (name) {
      var ds = crossers[name].slice().sort(function (a, b) { return a.vi - b.vi; });
      for (var i = 0; i < ds.length - 1; i++) {
        if (!ds[i].el || !ds[i + 1].el) continue;
        threadSvg.appendChild(curve(center(ds[i].el, base), center(ds[i + 1].el, base), "th rest"));
      }
    });
  }
  function speakerOn(rec) {
    if (PHONE || !stageEl) return;
    S.speaker = rec;
    var name = rec.name, mine = crossers[name] || [rec];
    var base = stageEl.getBoundingClientRect();
    clear(threadSvg);
    // readout
    clear(readout);
    var also = (crossers[name] || []).filter(function (d) { return d !== rec; }).map(function (d) { return V[d.vi].tr.title; });
    readout.appendChild(el("p", { class: "r-line r-one" }, el("b", null, name), rec.company ? "  " + rec.company : "",
      also.length ? el("span", { class: "also" }, "  also argued in " + also.join(" and ")) : null));
    var chips = el("p", { class: "r-line r-one chips" });
    rec.talks.forEach(function (id) { chips.appendChild(el("span", { class: "chip" }, T[id].title)); });
    if (!rec.talks.length) chips.appendChild(el("span", { class: "chip" }, "No talk linked"));
    readout.appendChild(chips);
    (function () {
      var rb = readout.getBoundingClientRect(), db = rec.el.getBoundingClientRect();
      var cw = chips.firstChild.getBoundingClientRect().width;
      var cx = db.left + db.width / 2 - rb.left;
      chips.style.paddingLeft = Math.max(0, Math.min(rb.width - cw - 4, cx - cw / 2)) + "px";
      chips.style.textIndent = "0";
    })();
    // dim rows without this person, light kin
    var rowsWith = {};
    mine.forEach(function (d) { rowsWith[d.vi] = 1; });
    rowEls.forEach(function (r, i) { r.classList.toggle("dim", !rowsWith[i]); });
    var kin = [];
    V[rec.vi].dots.forEach(function (d) {
      var shared = d !== rec && d.talks.some(function (id) { return rec.talks.indexOf(id) >= 0; });
      if (d.el) d.el.classList.toggle("kin", shared || d === rec);
      if (shared) kin.push(d);
    });
    mine.forEach(function (d) { if (d.el) d.el.classList.add("kin"); });
    // threads: to the talk chip, across lines, to co-presenters
    var a = center(rec.el, base);
    var chip = readout.querySelector(".chip");
    if (chip) {
      var cr = chip.getBoundingClientRect();
      var tgt = { x: Math.min(cr.right - 6, Math.max(cr.left + 6, a.x)), y: cr.bottom + 1 - base.top };
      threadSvg.appendChild(svg("path", { class: "th hot", d: "M" + a.x + "," + a.y + " C" + a.x + "," + (a.y - 30) + " " + tgt.x + "," + (tgt.y + 30) + " " + tgt.x + "," + tgt.y }));
      threadSvg.appendChild(svg("circle", { class: "knot", cx: tgt.x, cy: tgt.y, r: 3.5 }));
    }
    mine.forEach(function (d) { if (d !== rec && d.el) threadSvg.appendChild(curve(a, center(d.el, base), "th hot")); });
    kin.forEach(function (d) { threadSvg.appendChild(curve(a, center(d.el, base), "th hot kinline")); });
    animateThreads();
  }
  function animateThreads() {
    if (reduce) return;
    var ps = threadSvg.querySelectorAll(".hot");
    Array.prototype.forEach.call(ps, function (p) {
      var L = p.getTotalLength ? p.getTotalLength() : 300;
      p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
      p.getBoundingClientRect();
      p.style.transition = "stroke-dashoffset 380ms cubic-bezier(.2,.7,.2,1)";
      p.style.strokeDashoffset = 0;
    });
  }
  function speakerOff(rec) {
    if (S.speaker !== rec) return;
    S.speaker = null;
    rowEls.forEach(function (r) { r.classList.remove("dim"); });
    V.forEach(function (v) { v.dots.forEach(function (d) { if (d.el) d.el.classList.remove("kin"); }); });
    if (threadSvg) drawRest();
    var hov = menu.querySelector(".row:hover");
    if (hov) readVerdict(+hov.getAttribute("data-i")); else if (menu.contains(document.activeElement) && document.activeElement.classList.contains("rt")) readVerdict(+document.activeElement.closest(".row").getAttribute("data-i")); else readDefault();
  }

  /* keyboard: Up/Down between lines, Left/Right through the dots of a line */
  function rowKeys(e, i) {
    var k = e.key, tgt;
    if (k === "ArrowDown") tgt = rowEls[Math.min(V.length - 1, i + 1)].querySelector(".rt");
    else if (k === "ArrowUp") tgt = rowEls[Math.max(0, i - 1)].querySelector(".rt");
    else if (k === "ArrowRight") tgt = V[i].dots[0] && V[i].dots[0].el;
    if (tgt) { tgt.focus(); e.preventDefault(); }
  }
  function dotKeys(e, rec) {
    var k = e.key, ds = V[rec.vi].dots, idx = ds.indexOf(rec), tgt;
    if (k === "ArrowRight") tgt = ds[Math.min(ds.length - 1, idx + 1)].el;
    else if (k === "ArrowLeft") tgt = idx === 0 ? rowEls[rec.vi].querySelector(".rt") : ds[idx - 1].el;
    else if (k === "ArrowDown" || k === "ArrowUp") {
      var nv = V[Math.max(0, Math.min(V.length - 1, rec.vi + (k === "ArrowDown" ? 1 : -1)))];
      var best = nv.dots[0];
      nv.dots.forEach(function (d) { if (Math.abs(d.x - rec.x) < Math.abs(best.x - rec.x)) best = d; });
      tgt = best.el;
    } else if (k === "Escape") { tgt = rowEls[rec.vi].querySelector(".rt"); e.stopPropagation(); }
    if (tgt) { tgt.focus(); e.preventDefault(); }
  }

  /* ---------- an opened argument ---------- */
  function openVerdict(i) { S.vi = i; go("verdict"); var b = contentEl.querySelector(".back"); if (b) b.focus(); }
  function talkBtn(id, primary) {
    var t = T[id];
    if (!t) return null;
    return el("button", { type: "button", class: "tk" + (primary ? " primary" : ""), onclick: function () { window.openTalk(id); } },
      el("span", { class: "tkt" }, t.title),
      el("span", { class: "tks" }, t.speakers.map(function (p) { return p.name; }).join(", ") + (t.views != null ? "  " + fmtViews(t.views) + " views" : "  no video")));
  }
  function renderVerdict() {
    var v = V[S.vi], tr = v.tr, n = v.sides.length;
    var pick = pickFor[tr.title];
    var pairIds = [0, n - 1].map(function (si) {
      var ids = v.sides[si].talkIds;
      return pick && ids.indexOf(pick.talkId) >= 0 ? pick.talkId : ids[0];
    });
    var vv = el("div", { class: "vv" });
    vv.appendChild(el("div", { class: "vhead" },
      el("h2", { class: "vt" }, tr.title, el("span", { class: "vc" }, tr.count + " talks")),
      el("span", { class: "vnav" },
        el("button", { type: "button", class: "back mini", onclick: function () { go("args"); } }, "All arguments"),
        el("button", { type: "button", class: "mini", "aria-label": "Previous argument", onclick: function () { S.vi = (S.vi + V.length - 1) % V.length; go("verdict"); } }, "Previous"),
        el("button", { type: "button", class: "mini", "aria-label": "Next argument", onclick: function () { S.vi = (S.vi + 1) % V.length; go("verdict"); } }, "Next"))));
    vv.appendChild(el("p", { class: "settled" }, el("b", null, "Everyone agreed: "), tr.consensus));
    vv.appendChild(el("h3", { class: "vq" }, tr.debate.question));
    vv.appendChild(spectrum(v, true));
    var cols = el("div", { class: "sides n" + n });
    v.sides.forEach(function (sd, si) {
      var fs = firstSentence(sd.stance);
      var col = el("div", { class: "side", style: "--c:" + SIDE_COL[si] },
        el("p", { class: "stance" }, el("b", null, fs[0] + " "), fs[1]),
        el("p", { class: "who" }, sd.who.join(", ")),
        el("div", { class: "tks" }, sd.talkIds.map(function (id) { return talkBtn(id); })));
      var also = [];
      sd.who.forEach(function (name) {
        (crossers[name] || []).forEach(function (d) { if (d.vi !== S.vi && also.indexOf(d.vi) < 0) also.push(d.vi); });
      });
      if (also.length) col.appendChild(el("p", { class: "alsoin" }, "Also argued in ", also.map(function (vi, k) {
        return [k ? ", " : "", el("button", { type: "button", class: "lnk", onclick: function () { S.vi = vi; go("verdict"); } }, V[vi].tr.title)];
      })));
      cols.appendChild(col);
    });
    vv.appendChild(cols);
    var foot = el("div", { class: "vfoot" }, el("b", { class: "pairl" }, "Watch both sides"));
    [0, n - 1].forEach(function (si, k) {
      var id = pairIds[k];
      foot.appendChild(el("button", { type: "button", class: "pill", style: "--c:" + SIDE_COL[si], onclick: function () { window.openTalk(id); } },
        el("i", { class: "pd" }), el("span", null, T[id].title)));
    });
    foot.appendChild(el("button", { type: "button", class: "lnk", onclick: function () { S.cited = S.vi; S.q = ""; searchIn.value = ""; go("talks"); } }, "All " + tr.talkIds.length + " cited"));
    vv.appendChild(foot);
    contentEl.appendChild(vv);
  }

  /* ---------- search + talk list ---------- */
  function haystack(t) {
    if (t._h) return t._h;
    t._h = norm([t.title, t.speakers.map(function (p) { return p.name + " " + p.company; }).join(" "), (t.keywords || []).join(" "), (t.themes || []).join(" "), t.tldr, t.track].join(" "));
    return t._h;
  }
  function filtered() {
    var terms = norm(S.q).split(/\s+/).filter(Boolean);
    var list = M.talks.filter(function (t) {
      if (S.video && t.views == null) return false;
      if (S.cited != null && V[S.cited].tr.talkIds.indexOf(t.id) < 0) return false;
      var h = haystack(t);
      return terms.every(function (w) { return h.indexOf(w) >= 0; });
    });
    var key = S.sort;
    list.sort(function (a, b) {
      if (key === "like") {
        if (a.thin !== b.thin) return a.thin ? 1 : -1;
        return (b.likeRate || 0) - (a.likeRate || 0);
      }
      if (key === "hearts") return (b.hearts || 0) - (a.hearts || 0);
      return (b.views || 0) - (a.views || 0);
    });
    return list;
  }
  var MAXV = Math.max.apply(null, M.talks.map(function (t) { return t.views || 0; }));
  var MAXH = Math.max.apply(null, M.talks.map(function (t) { return t.hearts || 0; }));
  var MAXL = Math.max.apply(null, M.talks.map(function (t) { return t.likeRate || 0; }));
  function cell(kind, t) {
    var txt, w, thin = false, none = false;
    if (kind === "views") { none = t.views == null; txt = fmtViews(t.views); w = none ? 0 : Math.sqrt(t.views / MAXV); }
    else if (kind === "like") { none = t.likeRate == null; txt = none ? "none" : t.likeRate.toFixed(2); thin = !none && t.thin; w = none ? 0 : t.likeRate / MAXL; }
    else { txt = String(t.hearts || 0); w = (t.hearts || 0) / MAXH; }
    return el("span", { class: "sig " + kind + (S.sort === kind ? " on" : "") },
      el("span", { class: "sv" }, txt),
      thin ? el("span", { class: "few" }, "few votes") : el("span", { class: "bar" }, el("i", { style: "width:" + Math.max(none ? 0 : 3, Math.round(w * 100)) + "%" })));
  }
  function renderTalks() {
    var list = filtered();
    var wrap = el("div", { class: "talks" });
    var q = S.q.trim();
    var sum = el("p", { class: "tsum", role: "status" },
      list.length + " of " + M.talks.length + " talks" + (q ? " match " : "") , q ? el("b", null, "“" + q + "”") : null);
    var chips = el("div", { class: "tchips" },
      el("button", { type: "button", class: "chipb", "aria-pressed": S.video ? "true" : "false", onclick: function () { S.video = !S.video; renderContent(); focusSel('.chipb'); } }, "Only with video"),
      S.cited != null ? el("button", { type: "button", class: "chipb on", onclick: function () { S.cited = null; renderContent(); focusSel('.chipb'); } }, "Cited in " + V[S.cited].tr.title + "  ×") : null);
    wrap.appendChild(el("div", { class: "thead" }, sum, chips));
    var hdr = el("div", { class: "lh" }, el("span", { class: "lt" }, "Talk"));
    [["views", "Views"], ["like", PHONE ? "Like rate" : "Likes per 100"], ["hearts", "Hearts"]].forEach(function (c) {
      hdr.appendChild(el("button", { type: "button", class: "sortb" + (S.sort === c[0] ? " on" : ""), "aria-pressed": S.sort === c[0] ? "true" : "false", "aria-label": "Sort by " + c[1], onclick: function () { S.sort = c[0]; renderContent(); focusSel('.sortb.on'); } }, c[1]));
    });
    wrap.appendChild(hdr);
    var ul = el("div", { class: "tlist" });
    if (!list.length) ul.appendChild(el("p", { class: "empty" }, "No talk matches “" + q + "”. Try a speaker, a tool such as Valhalla or MCP, or a company."));
    list.slice(0, 120).forEach(function (t) {
      ul.appendChild(el("button", { type: "button", class: "trow", onclick: function () { window.openTalk(t.id); }, onkeydown: function (e) {
        var s = e.target; if (e.key === "ArrowDown" && s.nextElementSibling) { s.nextElementSibling.focus(); e.preventDefault(); }
        if (e.key === "ArrowUp") { if (s.previousElementSibling) s.previousElementSibling.focus(); else searchIn.focus(); e.preventDefault(); }
      } },
        el("span", { class: "tt" }, el("span", { class: "tti" }, t.title), el("span", { class: "tts" }, t.speakers.map(function (p) { return p.name; }).join(", ") + (t.speakers[0] && t.speakers[0].company ? ", " + t.speakers[0].company : ""))),
        cell("views", t), cell("like", t), cell("hearts", t)));
    });
    if (list.length > 120) ul.appendChild(el("p", { class: "empty" }, (list.length - 120) + " more: narrow the search to see them."));
    wrap.appendChild(ul);
    contentEl.appendChild(wrap);
  }
  function focusSel(sel) { var n = contentEl.querySelector(sel); if (n) n.focus(); }

  /* ---------- programme ---------- */
  function renderProg() {
    var wrap = el("div", { class: "prog" });
    var dayrow = el("div", { class: "days", role: "group", "aria-label": "Day" });
    days.forEach(function (d) {
      dayrow.appendChild(el("button", { type: "button", class: "dayb", "aria-pressed": S.day === d.key ? "true" : "false", onclick: function () { S.day = d.key; renderContent(); focusSel('.dayb[aria-pressed="true"]'); } },
        el("b", null, d.label), el("span", null, d.count + " talks")));
    });
    wrap.appendChild(dayrow);
    var ts = M.talks.filter(function (t) { return t.start && dayKey(t) === S.day; }).sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : (a.room < b.room ? -1 : 1); });
    var list = el("div", { class: "plist" }), last = "";
    ts.forEach(function (t) {
      var tm = fTime.format(new Date(t.start));
      list.appendChild(el("button", { type: "button", class: "prow" + (tm === last ? " same" : ""), onclick: function () { window.openTalk(t.id); } },
        el("span", { class: "pt" }, tm === last ? "" : tm), el("span", { class: "pr" }, t.room),
        el("span", { class: "pti" }, t.title, el("span", { class: "pts" }, t.speakers.map(function (p) { return p.name; }).join(", ")))));
      last = tm;
    });
    wrap.appendChild(list);
    contentEl.appendChild(wrap);
  }

  /* ---------- watch first rail ---------- */
  function renderPicks() {
    clear(picksEl);
    picksEl.appendChild(el("h2", { class: "ph" }, "Watch first"));
    picksEl.appendChild(el("p", { class: "pn" }, M.picksNote ? M.picksNote.charAt(0).toUpperCase() + M.picksNote.slice(1) : ""));
    var ul = el("div", { class: "plist2" });
    M.picks.forEach(function (p, i) {
      var t = T[p.talkId]; if (!t) return;
      var b = el("button", { type: "button", class: "pick", "data-i": i,
        onclick: function () { window.openTalk(p.talkId); },
        onmouseenter: function () { showPcard(i, b); }, onfocus: function () { showPcard(i, b); },
        onmouseleave: hidePcard, onblur: hidePcard,
        onkeydown: function (e) {
          if (e.key === "ArrowDown" && b.nextElementSibling) { b.nextElementSibling.focus(); e.preventDefault(); }
          if (e.key === "ArrowUp") { if (b.previousElementSibling) b.previousElementSibling.focus(); e.preventDefault(); }
        } },
        el("span", { class: "pti2" }, t.title),
        el("span", { class: "psp" }, t.speakers.map(function (s) { return s.name; }).join(", ")),
        PHONE ? el("span", { class: "pwhy" }, p.why) : null);
      ul.appendChild(b);
    });
    picksEl.appendChild(ul);
  }
  function sigText(t) {
    var a = [t.views != null ? fmtViews(t.views) + " views" : "no video"];
    if (t.likeRate != null) a.push(t.likeRate.toFixed(1) + " likes per 100 views" + (t.thin ? " (few votes)" : ""));
    a.push((t.hearts || 0) + " app favourites");
    return a.join(", ");
  }
  function showPcard(i, btn) {
    if (PHONE) return;
    var p = M.picks[i], t = T[p.talkId];
    if (S.mode === "args" && readout && !S.speaker) {
      clear(readout);
      readout.appendChild(el("p", { class: "r-line r-two" }, el("b", null, "Why watch: "), p.why));
      readout.appendChild(el("p", { class: "r-line r-one" }, el("b", null, p.verdict), "  " + sigText(t)));
      pcard.hidden = true;
      lightPick(i);
      return;
    }
    clear(pcard);
    pcard.appendChild(el("p", { class: "pcv" }, p.verdict));
    pcard.appendChild(el("p", { class: "pcw" }, p.why));
    pcard.appendChild(el("p", { class: "pcs" }, sigText(t)));
    pcard.hidden = false;
    var mr = menu.getBoundingClientRect(), br = btn.getBoundingClientRect();
    var top = Math.max(8, Math.min(br.top - mr.top - 8, mr.height - pcard.offsetHeight - 8));
    pcard.style.top = top + "px";
    lightPick(i);
  }
  function lightPick(i) {
    var t = T[M.picks[i].talkId], vi = pickIndex[i];
    if (S.mode === "args" && rowEls[vi]) {
      rowEls[vi].classList.add("lit");
      var names = t.speakers.map(function (s) { return s.name; });
      V.forEach(function (v) { v.dots.forEach(function (d) { if (d.el && names.indexOf(d.name) >= 0) d.el.classList.add("pickdot"); }); });
    }
  }
  function hidePcard() {
    if (pcard) pcard.hidden = true;
    if (readout && !S.speaker && S.mode === "args") readDefault();
    rowEls.forEach(function (r) { r.classList.remove("lit"); });
    V.forEach(function (v) { v.dots.forEach(function (d) { if (d.el) d.el.classList.remove("pickdot"); }); });
  }

  /* ---------- global keys ---------- */
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (S.intro) { setIntro(false); headBtn.focus(); }
      else if (S.mode === "verdict") { go("args"); var r = contentEl.querySelector(".rt"); if (r) r.focus(); }
      else if (S.mode !== "args" && !(e.target === searchIn)) { go("args"); }
    } else if (e.key === "/" && document.activeElement !== searchIn) { e.preventDefault(); searchIn.focus(); }
  });

  build();
  window.__menu = { S: S, go: go, openVerdict: openVerdict };
})();
