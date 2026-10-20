(function () {
  "use strict";
  var M = window.MENU, BL = window.BLIPS;
  var phone = /[?&]shape=phone/.test(location.search);
  var calm = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var menu = document.getElementById("menu");
  if (phone) menu.classList.add("phone");

  function el(tag, attrs) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      var v = attrs[k];
      if (v == null || v === false) continue;
      if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else if (k === "class") n.className = v;
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

  /* ---------- data ---------- */
  var RINGS = ["Do it now", "Try it", "Watch it", "Push back"];
  var F = [0, 0.38, 0.64, 0.84, 1];
  var SECTORS = [
    { id: "agents", name: "Agents and teams", a0: 0, a1: 120, color: "#7CCBF5" },
    { id: "security", name: "Security", a0: 120, a1: 200, color: "#F58BA0" },
    { id: "jvm", name: "JVM and Java", a0: 200, a1: 290, color: "#A6DE8A" },
    { id: "arch", name: "Architecture", a0: 290, a1: 360, color: "#C9A8F7" }
  ];
  var secBy = {}; SECTORS.forEach(function (s) { secBy[s.id] = s; });
  var byId = {}; M.talks.forEach(function (t) { byId[t.id] = t; });
  var TR = M.recap.trends;
  var hay = {};
  M.talks.forEach(function (t) {
    hay[t.id] = [t.title, t.speakers.map(function (s) { return s.name + " " + s.company; }).join(" "), (t.keywords || []).join(" "),
      (t.themes || []).join(" "), t.tldr, t.track].join(" ").toLowerCase();
  });
  var blipBy = {}; BL.forEach(function (b) { blipBy[b.id] = b; });

  /* ---------- state ---------- */
  var S = { arm: calm ? 150 : 40, auto: !calm, sel: null, tab: "sweep", openV: -1, q: "", sort: "views", day: "2026-10-05", dragging: false, resumeAt: 0, matchT: null, matchB: null };

  /* ---------- structure ---------- */
  var radar = el("div", { id: "radar", class: calm ? "calm" : "" });
  var cv = el("canvas", { id: "cv", "aria-hidden": "true" });
  var blipsEl = el("div", { id: "blips", role: "group", "aria-label": "Practices on the radar, in sweep order" });
  var playBtn = el("button", { id: "play", type: "button", onclick: function () { S.auto = !S.auto; S.resumeAt = 0; updatePlay(); } });
  radar.append(cv, blipsEl);
  if (!phone) radar.append(
    el("div", { class: "radar-title" }, el("b", null, "What the talks told you to do"), el("span", null, "Our reading of the talks")),
    el("div", { class: "legend" }, el("span", null, el("i"), "agreed"), el("span", null, el("i", { class: "dia" }), "debated")),
    el("div", { class: "hint" }, "Each mark is a practice. Drag the arm, or step with arrow keys."));
  radar.append(playBtn);

  var q = el("input", { id: "q", type: "search", placeholder: phone ? "Search talks" : "Search talks, speakers, tools", "aria-label": "Search talks, speakers, companies, keywords and topics", autocomplete: "off",
    oninput: function (e) { S.q = e.target.value; if (S.q.trim()) { S.tab = "talks"; S.sel = null; } recompute(); render(); } });
  var brand = el("div", { class: "brand", "aria-label": "Devoxx" });
  brand.innerHTML = "DEVOX<i>X</i>";
  var top = el("div", { id: "top" }, brand, q);
  var tabsEl = el("div", { id: "tabs", role: "tablist" });
  var view = el("div", { id: "view", role: "tabpanel" });
  var foot = el("div", { id: "foot" }, el("a", { href: "../../../site/index.html" }, "Text version of every talk"));
  var panel = el("aside", { id: "panel" }, tabsEl, view, foot);
  var toast = el("div", { id: "toast", role: "status", "aria-live": "polite" });
  menu.append(radar, top, panel, toast);

  var TABS = [["sweep", "Sweep"], ["verdicts", "Verdicts"], ["watch", "Watch first"], ["talks", "Talks"], ["prog", phone ? "Days" : "Programme"]];
  function renderTabs() {
    tabsEl.textContent = "";
    TABS.forEach(function (t, i) {
      tabsEl.append(el("button", { type: "button", role: "tab", id: "tab-" + t[0], "aria-selected": S.tab === t[0] ? "true" : "false", tabindex: S.tab === t[0] ? "0" : "-1",
        onclick: function () { S.tab = t[0]; if (t[0] === "sweep") S.sel = null; render(); updateAll(); },
        onkeydown: function (e) {
          var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0; if (!d) return;
          S.tab = TABS[(i + d + TABS.length) % TABS.length][0]; render(); document.getElementById("tab-" + S.tab).focus(); e.preventDefault();
        } }, t[1]));
    });
  }

  /* ---------- geometry ---------- */
  var W = 0, H = 0, cx = 0, cy = 0, R = 0, dpr = 1, ctx = cv.getContext("2d");
  function layout() {
    W = radar.clientWidth; H = radar.clientHeight; cx = W / 2; cy = H / 2;
    R = phone ? Math.min(W / 2 - 14, H / 2 - 24) : 248;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    place();
  }
  function pt(a, r) { var t = a * Math.PI / 180; return [cx + r * Math.sin(t), cy - r * Math.cos(t)]; }
  var order = [];
  function place() {
    var groups = {};
    BL.forEach(function (b) { (groups[b.sector + b.ring] = groups[b.sector + b.ring] || []).push(b); });
    Object.keys(groups).forEach(function (k) {
      var g = groups[k].sort(function (x, y) { return x.v - y.v || (x.side || 0) - (y.side || 0); });
      var s = secBy[g[0].sector], ring = g[0].ring, pad = 10, span = s.a1 - s.a0 - 2 * pad;
      var r0 = F[ring] * R, r1 = F[ring + 1] * R, tr = ring === 0 ? [0.45, 0.7, 0.9] : [0.25, 0.55, 0.8];
      g.forEach(function (b, i) {
        b.a = s.a0 + pad + (i + 0.5) / g.length * span;
        b.r = r0 + (r1 - r0) * tr[i % 3];
        var p = pt(b.a, b.r); b.x = p[0]; b.y = p[1];
      });
    });
    relax();
    order = BL.slice().sort(function (x, y) { return x.a - y.a; });
    order.forEach(function (b, i) { b.i = i; });
    blipsEl.textContent = "";
    order.forEach(function (b) {
      var c = secBy[b.sector].color;
      var n = el("button", { type: "button", class: "bl r" + b.ring + (b.side != null ? " dia" : "") + (b.x > cx ? " left" : ""), "data-id": b.id, tabindex: b.i === 0 ? "0" : "-1",
        "aria-label": b.label + ", " + RINGS[b.ring] + ", " + secBy[b.sector].name + (b.side != null ? ", debated" : ""),
        style: "left:" + b.x.toFixed(1) + "px;top:" + b.y.toFixed(1) + "px;--c:" + c,
        onclick: function (e) { e.stopPropagation(); select(b.id); },
        onkeydown: function (e) { blipKey(e, b); },
        onpointerdown: function (e) { e.stopPropagation(); },
        onfocus: function () { rove(b); } }, el("span", { class: "d" }), el("span", { class: "lb" }, b.label));
      b.node = n; blipsEl.append(n);
    });
    updateAll();
  }
  function relax() {
    var md = phone ? 17 : 28;
    for (var it = 0; it < 80; it++) {
      for (var i = 0; i < BL.length; i++) for (var j = i + 1; j < BL.length; j++) {
        var p = BL[i], q2 = BL[j], dx = q2.x - p.x, dy = q2.y - p.y, d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        if (d < md) { var k = (md - d) / 2 / d; p.x -= dx * k; p.y -= dy * k; q2.x += dx * k; q2.y += dy * k; }
      }
      BL.forEach(function (b) {
        var s = secBy[b.sector], dx = b.x - cx, dy = b.y - cy, r = Math.sqrt(dx * dx + dy * dy), a = (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
        var lo = Math.max(F[b.ring] * R + (b.ring ? 9 : 14), 0), hi = F[b.ring + 1] * R - 9;
        r = Math.min(hi, Math.max(lo, r)); a = Math.min(s.a1 - 5, Math.max(s.a0 + 5, a));
        var p = pt(a, r); b.x = p[0]; b.y = p[1]; b.a = a; b.r = r;
      });
    }
  }
  function rove(b) { order.forEach(function (o) { o.node.tabIndex = o === b ? 0 : -1; }); }
  function blipKey(e, b) {
    var d = (e.key === "ArrowRight" || e.key === "ArrowDown") ? 1 : (e.key === "ArrowLeft" || e.key === "ArrowUp") ? -1 : 0;
    if (!d) return;
    var n = order[(b.i + d + order.length) % order.length];
    n.node.focus(); S.arm = n.a; S.resumeAt = performance.now() + 8000; lastArm = S.arm; updateAll(); e.preventDefault();
  }

  /* ---------- drawing ---------- */
  function arcText(text, rad, mid, color, size) {
    ctx.font = "700 " + size + "px Archivo, Helvetica, Arial, sans-serif"; ctx.fillStyle = color; ctx.textBaseline = "middle";
    var ws = text.split("").map(function (c) { return ctx.measureText(c).width + 0.6; });
    var tot = ws.reduce(function (a, b) { return a + b; }, 0) / rad * 180 / Math.PI, cum = 0;
    var bottom = Math.cos(mid * Math.PI / 180) < 0;
    text.split("").forEach(function (c, i) {
      var w = ws[i], off = (cum + w / 2) / rad * 180 / Math.PI; cum += w;
      var a = bottom ? mid + tot / 2 - off : mid - tot / 2 + off, p = pt(a, rad);
      ctx.save(); ctx.translate(p[0], p[1]); ctx.rotate((a + (bottom ? 180 : 0)) * Math.PI / 180); ctx.fillText(c, -w / 2, 0); ctx.restore();
    });
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    var i, alphas = [0.07, 0.045, 0.07, 0.045];
    for (i = 3; i >= 0; i--) { ctx.beginPath(); ctx.arc(cx, cy, F[i + 1] * R, 0, 7); ctx.fillStyle = "rgba(130,160,255," + alphas[i] + ")"; ctx.fill(); }
    ctx.strokeStyle = "#2A3E8F"; ctx.lineWidth = 1.5;
    for (i = 1; i <= 4; i++) { ctx.beginPath(); ctx.arc(cx, cy, F[i] * R, 0, 7); ctx.stroke(); }
    ctx.lineWidth = 1; ctx.strokeStyle = "rgba(60,84,180,.8)";
    SECTORS.forEach(function (s) { var p = pt(s.a0, R); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(p[0], p[1]); ctx.stroke(); });
    SECTORS.forEach(function (s) {
      ctx.beginPath(); ctx.arc(cx, cy, R + 7, (s.a0 - 90 + 2) * Math.PI / 180, (s.a1 - 90 - 2) * Math.PI / 180);
      ctx.strokeStyle = s.color; ctx.lineWidth = 4; ctx.stroke();
      arcText(s.name, R + (phone ? 20 : 25), (s.a0 + s.a1) / 2, s.color, phone ? 13 : 16);
    });
    /* ring names, on the vertical axis at the outer edge of each ring */
    ctx.font = "600 " + (phone ? 12 : 14) + "px Archivo, Helvetica, Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (i = 0; i < 4; i++) {
      var ty = cy - F[i + 1] * R + (phone ? 8 : 10);
      ctx.lineWidth = 4; ctx.strokeStyle = "#0B1440"; ctx.strokeText(RINGS[i], cx, ty); ctx.fillStyle = "#A9B8EA"; ctx.fillText(RINGS[i], cx, ty);
    }
    ctx.textAlign = "start";
    /* sweep */
    var th = (S.arm - 90) * Math.PI / 180, span = 70 * Math.PI / 180;
    if (ctx.createConicGradient) {
      var g = ctx.createConicGradient(th - span, cx, cy);
      g.addColorStop(0, "rgba(246,146,30,0)"); g.addColorStop(70 / 360, "rgba(246,146,30,.30)"); g.addColorStop(70 / 360 + 0.0005, "rgba(246,146,30,0)"); g.addColorStop(1, "rgba(246,146,30,0)");
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, th - span, th); ctx.closePath(); ctx.fillStyle = g; ctx.fill();
    }
    var e = pt(S.arm, R + 3);
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(e[0], e[1]); ctx.strokeStyle = "#F6921E"; ctx.lineWidth = 2.5; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, 4, 0, 7); ctx.fillStyle = "#F6921E"; ctx.fill();
    ctx.beginPath(); ctx.arc(e[0], e[1], 5, 0, 7); ctx.fill();
  }

  /* ---------- sweep ---------- */
  var lastArm = S.arm, feedKey = "";
  function behind(b) { return ((S.arm - b.a) % 360 + 360) % 360; }
  function updateAll() {
    BL.forEach(function (b) {
      var d = behind(b), v = d < 70 ? 1 - d / 70 : 0;
      b.node.style.setProperty("--i", v.toFixed(2));
      var lw = phone ? 9 : 30; b.node.style.setProperty("--l", (d < lw ? 1 - d / lw : 0).toFixed(2));
    });
    draw(); updateFeed();
  }
  function ping() {
    var a = lastArm, c = S.arm, d = ((c - a) % 360 + 360) % 360;
    if (d === 0 || d > 40) { lastArm = c; return; }
    BL.forEach(function (b) {
      var x = ((b.a - a) % 360 + 360) % 360;
      if (x > 0 && x <= d && !calm) { b.node.classList.remove("ping"); void b.node.offsetWidth; b.node.classList.add("ping"); }
    });
    lastArm = c;
  }
  var t0 = performance.now();
  function tick(now) {
    var dt = Math.min(0.1, (now - t0) / 1000); t0 = now;
    if (S.auto && !S.dragging && now > S.resumeAt && !document.hidden) { S.arm = (S.arm + 6 * dt) % 360; ping(); updateAll(); }
    requestAnimationFrame(tick);
  }
  function angleOf(e) {
    var r = radar.getBoundingClientRect(), k = r.width / W;
    var x = (e.clientX - r.left) / k - cx, y = (e.clientY - r.top) / k - cy;
    return (Math.atan2(x, -y) * 180 / Math.PI + 360) % 360;
  }
  radar.addEventListener("pointerdown", function (e) {
    if (e.button) return;
    S.dragging = true; radar.classList.add("drag"); radar.setPointerCapture(e.pointerId); S.arm = angleOf(e); lastArm = S.arm; updateAll();
  });
  radar.addEventListener("pointermove", function (e) {
    if (!S.dragging) return; S.arm = angleOf(e); ping(); updateAll();
  });
  function endDrag() { if (!S.dragging) return; S.dragging = false; radar.classList.remove("drag"); S.resumeAt = performance.now() + 6000; }
  radar.addEventListener("pointerup", endDrag); radar.addEventListener("pointercancel", endDrag);
  function updatePlay() { playBtn.textContent = S.auto ? "Pause sweep" : "Start sweep"; playBtn.setAttribute("aria-pressed", S.auto ? "true" : "false"); }

  /* ---------- search ---------- */
  function terms() { return S.q.toLowerCase().split(/\s+/).filter(Boolean); }
  function recompute() {
    var ts = terms(); radar.classList.toggle("searching", ts.length > 0);
    if (!ts.length) { S.matchT = null; S.matchB = null; BL.forEach(function (b) { b.node.classList.remove("match"); }); return; }
    var mt = {}; M.talks.forEach(function (t) { if (ts.every(function (w) { return hay[t.id].indexOf(w) >= 0; })) mt[t.id] = 1; });
    S.matchT = mt; S.matchB = {};
    BL.forEach(function (b) {
      var own = (b.label + " " + b.why).toLowerCase(), m = ts.every(function (w) { return own.indexOf(w) >= 0; }) || b.talks.some(function (id) { return mt[id]; });
      if (m) S.matchB[b.id] = 1; b.node.classList.toggle("match", !!m);
    });
  }

  /* ---------- views ---------- */
  function compact(n) { return n >= 10000 ? Math.round(n / 1000) + "k" : n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n); }
  function sig(t) {
    return el("div", { class: "sg" },
      t.views == null ? el("span", { class: "no" }, "no video") : el("span", null, compact(t.views) + " views"),
      t.views == null ? null : el("span", { class: t.thin ? "few" : "" }, "like rate " + t.likeRate.toFixed(2) + (t.thin ? " (few votes)" : "")),
      el("span", null, t.hearts + " hearts"));
  }
  function who(t) { return t.speakers.map(function (s) { return s.name; }).join(", "); }
  function talkRow(t) {
    return el("button", { type: "button", class: "talk", onclick: function () { openTalk(t.id); } },
      el("span", { class: "ti" }, t.title), el("span", { class: "sp" }, who(t) + " (" + t.speakers.map(function (s) { return s.company; }).filter(function (v, i, a) { return v && a.indexOf(v) === i; }).join(", ") + ")"), sig(t));
  }
  function openTalk(id) {
    var t = byId[id]; if (!t) return;
    toast.textContent = t.seat ? "Walking to " + t.room + ", seat ready" : "Opening the summary";
    toast.classList.add("on"); clearTimeout(openTalk.h); openTalk.h = setTimeout(function () { toast.classList.remove("on"); }, 2600);
  }
  window.openTalk = openTalk;

  function feedList() {
    var arr = BL.filter(function (b) { return behind(b) < 75; }).sort(function (x, y) { return behind(y) - behind(x); });
    return arr.slice(-(phone ? 3 : 5));
  }
  var feedEl = null;
  function renderFeed() {
    var l = feedList(); feedEl.textContent = "";
    l.forEach(function (b, i) {
      var ts = b.talks.slice(0, 2).map(function (id) { return byId[id].title; });
      feedEl.append(el("li", null, el("button", { type: "button", class: "fe" + (i === l.length - 1 ? " now" : ""), style: "--c:" + secBy[b.sector].color, onclick: function () { select(b.id); } },
        el("span", { class: "t" }, el("span", null, b.label), el("em", null, RINGS[b.ring])),
        ts.map(function (x) { return el("span", { class: "ti" }, x); }))));
    });
    if (!l.length) feedEl.append(el("li", { class: "empty" }, "Nothing under the arm yet."));
  }
  function updateFeed() {
    if (!feedEl || !feedEl.isConnected) return;
    var k = feedList().map(function (b) { return b.id; }).join();
    if (k !== feedKey) { feedKey = k; renderFeed(); }
  }

  function sweepView() {
    if (S.sel) return detail(blipBy[S.sel]);
    feedKey = ""; feedEl = el("ul", { class: "feed", "aria-label": "Practices the arm has just passed, in sweep order" });
    var go = function (t) { return function () { S.tab = t; render(); }; };
    var h = el("p", { class: "start" }, "Start with ", el("button", { type: "button", class: "lnk", onclick: go("verdicts") }, "the 8 verdicts"), " or ", el("button", { type: "button", class: "lnk", onclick: go("watch") }, "the 8 talks to watch first"), ".");
    var n = el("div", null, el("h2", { class: "headline" }, "Mostly about working with coding agents: how to check, review and contain them."), h, feedEl);
    setTimeout(updateFeed, 0); return n;
  }
  function select(id) {
    S.sel = id; S.tab = "sweep"; var b = blipBy[id]; S.arm = b.a + 1; lastArm = S.arm; S.resumeAt = performance.now() + 10000;
    BL.forEach(function (x) { x.node.classList.toggle("sel", x.id === id); });
    render(); updateAll();
  }
  function deselect() { S.sel = null; BL.forEach(function (x) { x.node.classList.remove("sel"); }); render(); }
  function detail(b) {
    var c = secBy[b.sector].color, t = TR[b.v], n = el("div", { class: "detail", style: "--c:" + c });
    n.append(el("button", { type: "button", class: "back", onclick: deselect }, "Back to the sweep"),
      el("h2", null, b.label),
      el("div", { class: "meta" }, el("span", { class: "chip" }, RINGS[b.ring]), el("span", { class: "chip" }, secBy[b.sector].name), b.side != null ? el("span", { class: "chip" }, "debated") : null),
      el("p", { class: "rd" }, b.why.replace(/^(One|Other) side: /, "").replace(/^./, function (c) { return c.toUpperCase(); })),
      el("p", { class: "sub", style: "margin-top:6px" }, "Our reading of the talks, placed from the verdict and the takeaways."),
      el("h3", null, "From the verdict"),
      el("button", { type: "button", class: "lnk", onclick: function () { S.tab = "verdicts"; S.openV = b.v; render(); } }, t.title));
    if (b.side != null) {
      n.append(el("h3", null, "The debate"), el("p", null, t.debate.question));
      BL.filter(function (o) { return o.v === b.v && o.side != null && o.id !== b.id; }).forEach(function (o) {
        n.append(el("button", { type: "button", class: "oth", style: "border-left-color:" + secBy[o.sector].color, onclick: function () { select(o.id); } },
          el("b", null, o.label), el("span", null, "Other side, on the radar as " + RINGS[o.ring].toLowerCase())));
      });
    }
    n.append(el("h3", null, "Talks")); b.talks.forEach(function (id) { n.append(talkRow(byId[id])); });
    return n;
  }

  function verdictsView() {
    var n = el("div");
    TR.forEach(function (t, i) {
      var open = S.openV === i, bs = BL.filter(function (b) { return b.v === i; });
      var item = el("div", { class: "vd" + (open ? " open" : "") },
        el("button", { type: "button", "aria-expanded": open ? "true" : "false", onclick: function () { S.openV = open ? -1 : i; var st = view.scrollTop; render(); view.scrollTop = st; } }, el("span", null, t.title), el("small", null, t.count + " talks")));
      if (open) {
        var bd = el("div", { class: "bd" }, el("p", { class: "cons" }, t.consensus), el("p", { class: "q" }, t.debate.question));
        t.debate.sides.forEach(function (s) {
          bd.append(el("div", { class: "side" }, el("span", { class: "who" }, s.who.join(", ")), el("span", null, s.stance),
            el("div", { class: "tl" }, s.talkIds.map(function (id) { return el("button", { type: "button", onclick: function () { openTalk(id); } }, byId[id].title); }))));
        });
        bd.append(el("p", { class: "note" }, "On the radar: ", bs.map(function (b, k) { return [k ? ", " : "", el("button", { type: "button", class: "lnk", onclick: function () { select(b.id); } }, b.label)]; })));
        item.append(bd);
      }
      n.append(item);
    });
    return n;
  }
  function watchView() {
    var n = el("div", null, el("p", { class: "note" }, M.picksNote.charAt(0).toUpperCase() + M.picksNote.slice(1) + "."));
    M.picks.forEach(function (p) {
      var t = byId[p.talkId];
      n.append(el("div", { class: "pk" }, el("span", { class: "v" }, p.verdict), el("button", { type: "button", class: "ti", onclick: function () { openTalk(t.id); } }, t.title), el("span", null, p.why), sig(t)));
    });
    return n;
  }
  function sorted(list) {
    var s = S.sort, f = {
      views: function (a, b) { return (b.views == null ? -1 : b.views) - (a.views == null ? -1 : a.views); },
      rate: function (a, b) { var ka = a.views == null ? -2 : a.thin ? -1 : a.likeRate, kb = b.views == null ? -2 : b.thin ? -1 : b.likeRate; return kb - ka || f.views(a, b); },
      hearts: function (a, b) { return b.hearts - a.hearts; },
      time: function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : 0; }
    };
    return list.slice().sort(f[s]);
  }
  function talksView() {
    var list = M.talks.filter(function (t) { return !S.matchT || S.matchT[t.id]; });
    var n = el("div"), bar = el("div", { class: "bar", role: "group", "aria-label": "Sort talks" }, el("span", { class: "lab" }, "Sort by"));
    [["views", "Views"], ["rate", "Like rate"], ["hearts", "Hearts"], ["time", "Time"]].forEach(function (o) {
      bar.append(el("button", { type: "button", class: "pill", "aria-pressed": S.sort === o[0] ? "true" : "false", onclick: function () { S.sort = o[0]; var st = view.scrollTop; render(); view.scrollTop = st; } }, o[1]));
    });
    n.append(bar, el("p", { class: "note" }, (S.matchT ? list.length + " of " + M.talks.length + " talks match. " : M.talks.length + " talks. ") +
      "Views are reach. Like rate is likes per 100 views; talks with few votes (under 20 likes) rank last. Hearts are interest before the talk, not quality."));
    if (S.matchB) { var bs = BL.filter(function (b) { return S.matchB[b.id]; }); if (bs.length) n.append(el("p", { class: "note" }, "Lit on the radar: ", bs.slice(0, 4).map(function (b, k) { return [k ? ", " : "", el("button", { type: "button", class: "lnk", onclick: function () { select(b.id); } }, b.label)]; }), bs.length > 4 ? " and " + (bs.length - 4) + " more" : "")); }
    if (!list.length) n.append(el("p", { class: "empty" }, "No talk matches \"" + S.q + "\". Try a speaker, a tool such as ArchUnit, or a topic such as security."));
    sorted(list).forEach(function (t) { n.append(talkRow(t)); });
    return n;
  }
  var DAYS = [["2026-10-05", "Mon 5"], ["2026-10-06", "Tue 6"], ["2026-10-07", "Wed 7"], ["2026-10-08", "Thu 8"], ["2026-10-09", "Fri 9"]];
  var tf = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", hour: "2-digit", minute: "2-digit", hour12: false });
  var df = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Brussels" });
  function progView() {
    var n = el("div"), bar = el("div", { class: "bar", role: "group", "aria-label": "Day" });
    DAYS.forEach(function (d) { bar.append(el("button", { type: "button", class: "pill", "aria-pressed": S.day === d[0] ? "true" : "false", onclick: function () { S.day = d[0]; render(); } }, d[1])); });
    n.append(bar, el("p", { class: "note" }, "October 2026, times in Brussels."));
    var list = M.talks.filter(function (t) { return df.format(new Date(t.start)) === S.day; }).sort(function (a, b) { return a.start < b.start ? -1 : a.start > b.start ? 1 : (a.room > b.room ? 1 : -1); });
    list.forEach(function (t) {
      n.append(el("button", { type: "button", class: "pr", onclick: function () { openTalk(t.id); } }, el("span", null, el("span", { class: "tm" }, tf.format(new Date(t.start))), el("span", { class: "rm", style: "display:block" }, t.room)),
        el("span", null, el("span", { class: "ti" }, t.title), el("span", { class: "sp" }, who(t)))));
    });
    return n;
  }
  function render() {
    renderTabs(); view.textContent = ""; view.scrollTop = 0;
    view.setAttribute("aria-labelledby", "tab-" + S.tab);
    view.append({ sweep: sweepView, verdicts: verdictsView, watch: watchView, talks: talksView, prog: progView }[S.tab]());
    radar.classList.toggle("hlv", S.tab === "verdicts" && S.openV >= 0);
    BL.forEach(function (b) { b.node.classList.toggle("hl", S.tab === "verdicts" && b.v === S.openV); b.node.classList.toggle("sel", b.id === S.sel); });
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (S.sel) deselect(); else if (S.q) { S.q = ""; q.value = ""; recompute(); render(); }
  });

  /* hall toggle */
  var frame = document.getElementById("frame"), ht = document.getElementById("hallToggle");
  function fit() { if (frame.classList.contains("hall")) frame.style.setProperty("--hs", (frame.clientWidth * 0.383 / menu.offsetWidth).toFixed(4)); else frame.style.removeProperty("--hs"); }
  ht.addEventListener("click", function () { var on = frame.classList.toggle("hall"); ht.setAttribute("aria-pressed", on); fit(); });
  window.addEventListener("resize", fit);

  updatePlay(); layout(); render(); updateAll();
  window.addEventListener("resize", layout);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
  requestAnimationFrame(tick);
})();
