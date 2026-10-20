(() => {
  "use strict";
  const M = window.MENU;
  const menu = document.getElementById("menu");
  if (!M || !menu) return;
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PHONE = new URLSearchParams(location.search).get("shape") === "phone";
  if (PHONE) menu.classList.add("phone");
  const TEXT_URL = "../../../site/index.html";

  /* ---------- helpers ---------- */
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid.nodeType ? kid : document.createTextNode(kid));
    return n;
  };
  const byId = new Map(M.talks.map((t) => [t.id, t]));
  const fmtViews = (v) => (v == null ? "no video" : v >= 10000 ? Math.round(v / 1000) + "k" : v >= 1000 ? (v / 1000).toFixed(1) + "k" : String(v));
  const speakerLine = (t) => t.speakers.map((s) => s.name).join(", ");
  const dtf = (o) => new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", ...o });
  const dayKey = (iso) => dtf({ year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(iso)).reduce((a, p) => (p.type !== "literal" ? a + p.value : a), "");
  const dayLabel = (iso) => dtf({ weekday: "short", day: "numeric" }).format(new Date(iso)).replace(",", "");
  const timeLabel = (iso) => dtf({ hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(iso));

  /* ---------- openTalk (the real page starts the walk here) ---------- */
  let toastTimer;
  window.openTalk = function (id) {
    const t = byId.get(id);
    if (!t) return;
    menu.querySelector(".toast")?.remove();
    const msg = t.seat ? `Walking to ${t.room}, seat ready` : "Opening the summary";
    menu.append(el("div", { class: "toast", role: "status" }, msg));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => menu.querySelector(".toast")?.remove(), 2800);
  };

  /* ---------- data ---------- */
  const verdicts = M.recap.trends.map((v, i) => {
    const cited = new Set(v.talkIds);
    v.debate.sides.forEach((s) => s.talkIds.forEach((x) => cited.add(x)));
    return { ...v, i, cited, pick: M.picks.find((p) => p.verdict === v.title) };
  });
  const verdictOf = new Map();
  verdicts.forEach((v) => v.cited.forEach((id) => { if (!verdictOf.has(id)) verdictOf.set(id, v.i); }));
  const hay = new Map(M.talks.map((t) => [t.id, {
    title: t.title.toLowerCase(),
    who: t.speakers.map((s) => s.name + " " + (s.company || "")).join(" ").toLowerCase(),
    kw: (t.keywords || []).join(" ").toLowerCase(),
    th: (t.themes || []).join(" ").toLowerCase(),
    rest: ((t.tldr || "") + " " + (t.track || "")).toLowerCase(),
  }]));
  const search = (q) => {
    const toks = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!toks.length) return null;
    const out = [];
    for (const t of M.talks) {
      const h = hay.get(t.id);
      let score = 0, ok = true;
      for (const k of toks) {
        const s = (h.title.includes(k) ? 5 : 0) + (h.who.includes(k) ? 4 : 0) + (h.kw.includes(k) ? 3 : 0) + (h.th.includes(k) ? 2 : 0) + (h.rest.includes(k) ? 1 : 0);
        if (!s) { ok = false; break; }
        score += s;
      }
      if (ok) out.push({ t, score });
    }
    return out;
  };

  /* ---------- state ---------- */
  const state = { mode: "story", query: "", sort: null, hideThin: false, day: null, results: null, hits: new Map() };
  const days = [...new Set(M.talks.map((t) => dayKey(t.start)))].sort();
  state.day = days[0];
  const frameDefs = () => ["leader", ...state.order.map((i) => "v" + i), "credits"];
  state.order = verdicts.map((v) => v.i);

  /* ---------- DOM skeleton ---------- */
  const q = el("input", { type: "search", id: "q", placeholder: "Search talks", "aria-label": "Search talks, speakers, tools and topics", autocomplete: "off", spellcheck: "false" });
  const bTalks = el("button", { class: "btn", type: "button", "aria-pressed": "false", on: { click: () => setMode(state.mode === "talks" ? "story" : "talks") } }, "All talks");
  const bProg = el("button", { class: "btn", type: "button", "aria-pressed": "false", on: { click: () => setMode(state.mode === "programme" ? "story" : "programme") } }, "Programme");
  const bFirst = el("button", { class: "btn", type: "button", on: { click: () => { setMode("story"); goTo(frameDefs().length - 1); } } }, "Watch first");
  const textLink = el("a", { class: "btn", href: TEXT_URL }, "Text version");
  const top = el("header", { class: "top" },
    el("div", { class: "brand" }, "DEVOX", el("b", {}, "X"), el("span", {}, "Belgium 2026")),
    el("p", { class: "headline" }, "Mostly about working with coding agents: how to check, review and contain them."),
    el("div", { class: "tools" }, el("div", { class: "search", role: "search" }, q), bFirst, bTalks, bProg, textLink));
  const track = el("div", { class: "track" });
  const gatemark = el("div", { class: "gatemark", "aria-hidden": "true" }, el("i"), el("i"), el("i"), el("i"));
  const viewport = el("div", { class: "viewport" }, track);
  const reel = el("section", { class: "reel", "aria-label": "The reel: eight verdicts between the intro and the credits. Drag, scroll or use the arrow keys." }, viewport, gatemark);
  const panel = el("main", { class: "panel" });
  const live = el("div", { class: "sr", "aria-live": "polite" });
  const versus = el("div", { class: "versus", role: "dialog", "aria-modal": "true", "aria-label": "The debate" });
  menu.append(top, reel, panel, versus, live);
  menu.addEventListener("scroll", () => { menu.scrollLeft = 0; menu.scrollTop = 0; });

  /* ---------- frames ---------- */
  const frameEls = new Map();
  const leaderSvg = () => {
    const ns = "http://www.w3.org/2000/svg";
    const s = document.createElementNS(ns, "svg");
    s.setAttribute("viewBox", "0 0 120 120");
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = '<g fill="none" stroke="currentColor" stroke-width="2"><circle cx="60" cy="60" r="52"/><circle cx="60" cy="60" r="40" stroke-width="1"/><path d="M60 4v112M4 60h112" stroke-width="1"/></g><text x="60" y="82" text-anchor="middle" font-family="Archivo, sans-serif" font-stretch="62%" font-weight="800" font-size="70" fill="currentColor">8</text>';
    return s;
  };
  const makeFrame = (key) => {
    let face;
    if (key === "leader") {
      face = el("span", { class: "face" }, leaderSvg(), el("span", { class: "lcap" }, "verdicts, 205 talks"));
    } else if (key === "credits") {
      face = el("span", { class: "face" }, el("span", { class: "ftitle" }, "Watch first"), el("span", { class: "fmeta" }, el("span", {}, "8 picks, one per verdict")));
    } else {
      const v = verdicts[+key.slice(1)];
      face = el("span", { class: "face" },
        el("span", { class: "ftitle" }, v.title),
        el("span", { class: "fmeta" }, el("span", { class: "fno" }), el("span", { class: "hit" })),
        el("span", { class: "hitflag" }));
    }
    const b = el("button", { class: "frame " + (key === "leader" ? "leader" : key === "credits" ? "credits" : "verdict"), type: "button", "data-key": key, tabindex: "-1" }, face);
    b.addEventListener("click", () => {
      if (dragMoved) return;
      const i = frameDefs().indexOf(key);
      if (i !== nearest) goTo(i);
      else if (key.startsWith("v")) openVersus(+key.slice(1));
    });
    return b;
  };
  const frameLabel = (key) => {
    if (key === "leader") return "Intro";
    if (key === "credits") return "Watch first";
    return verdicts[+key.slice(1)].title;
  };
  const layoutFrames = (animate) => {
    const keys = frameDefs();
    const before = new Map();
    if (animate) for (const [k, n] of frameEls) before.set(k, n.offsetLeft);
    keys.forEach((k, idx) => {
      if (!frameEls.has(k)) frameEls.set(k, makeFrame(k));
      const n = frameEls.get(k);
      track.append(n);
      if (k.startsWith("v")) {
        const v = verdicts[+k.slice(1)];
        const hits = state.hits.get(v.i);
        n.querySelector(".fno").textContent = `${idx} of 8`;
        const hit = n.querySelector(".hit");
        const flag = n.querySelector(".hitflag");
        const hasQ = state.results != null;
        hit.textContent = hasQ ? `${hits} ${hits === 1 ? "hit" : "hits"}` : `${v.count} talks`;
        flag.textContent = hasQ ? String(hits) : "";
        flag.style.display = hasQ && hits ? "" : "none";
        n.classList.toggle("miss", hasQ && !hits);
        n.setAttribute("aria-label", `Verdict ${idx} of 8: ${v.title}` + (hasQ ? `, ${hits} matching talks` : ""));
      } else n.setAttribute("aria-label", frameLabel(k));
    });
    if (animate && !REDUCED) {
      for (const [k, n] of frameEls) {
        const d = before.get(k) - n.offsetLeft;
        if (d) { n.style.transition = "none"; n.style.transform = `translateX(${d}px)`; }
      }
      track.offsetWidth;
      for (const [, n] of frameEls) {
        if (n.style.transform) { n.style.transition = "transform .55s cubic-bezier(.2,.8,.2,1)"; n.style.transform = ""; }
      }
      setTimeout(() => { for (const [, n] of frameEls) n.style.transition = ""; }, 650);
    }
  };

  /* ---------- reel physics ---------- */
  let pos = 1, vel = 0, target = 1, dragging = false, dragMoved = false, nearest = -1, raf = 0, last = 0, lastWheel = 0, wheelTimer;
  const clamp = (x) => Math.max(0, Math.min(frameDefs().length - 1, x));
  const geometry = () => {
    const f = track.children;
    if (f.length < 2) return { pitch: 300, c0: 0 };
    const pitch = f[1].offsetLeft - f[0].offsetLeft;
    return { pitch, c0: f[0].offsetLeft + f[0].offsetWidth / 2 };
  };
  const render = () => {
    const { pitch, c0 } = geometry();
    const cx = reel.clientWidth / 2;
    track.style.transform = `translateX(${(cx - (c0 + pos * pitch)).toFixed(2)}px)`;
    const n = Math.round(clamp(pos));
    if (n !== nearest) setNearest(n);
  };
  const setNearest = (n) => {
    const keys = frameDefs();
    const had = nearest >= 0;
    const focusOnFrame = document.activeElement && document.activeElement.classList.contains("frame");
    nearest = n;
    keys.forEach((k, i) => {
      const f = frameEls.get(k);
      f.classList.toggle("gate", i === n);
      f.tabIndex = i === n ? 0 : -1;
      f.setAttribute("aria-current", i === n ? "true" : "false");
    });
    if (focusOnFrame) frameEls.get(keys[n]).focus({ preventScroll: true });
    if (had && !REDUCED) { reel.classList.add("claw"); setTimeout(() => reel.classList.remove("claw"), 90); }
    if (state.mode === "story") renderPanel();
    live.textContent = frameLabel(keys[n]);
  };
  const loop = (t) => {
    const dt = Math.min(0.05, (t - last) / 1000 || 0.016);
    last = t;
    if (!dragging) {
      if (REDUCED) { pos = target; vel = 0; }
      else {
        const k = 190, c = 2 * Math.sqrt(k);
        vel += ((target - pos) * k - vel * c) * dt;
        pos += vel * dt;
      }
    }
    render();
    const settled = !dragging && Math.abs(target - pos) < 0.0008 && Math.abs(vel) < 0.002;
    if (settled) { pos = target; vel = 0; render(); raf = 0; return; }
    raf = requestAnimationFrame(loop);
  };
  const kick = () => { if (!raf) { last = performance.now(); raf = requestAnimationFrame(loop); } };
  const goTo = (i) => { target = clamp(i); kick(); };
  const step = (d) => goTo(target + d);

  // pointer drag
  let px = 0, pStart = 0, pPos = 0, pt = 0, pv = 0, pDown = false;
  reel.addEventListener("pointerdown", (e) => { if (e.button) return; pDown = true; dragMoved = false; px = pStart = e.clientX; pPos = pos; pt = performance.now(); pv = 0; });
  reel.addEventListener("pointermove", (e) => {
    if (!pDown) return;
    if (!dragging) {
      if (Math.abs(e.clientX - pStart) < 5) return;
      dragging = true; dragMoved = true; reel.classList.add("dragging");
      try { reel.setPointerCapture(e.pointerId); } catch (_) {}
      kick();
    }
    const { pitch } = geometry();
    const now = performance.now();
    const np = clamp(pPos - (e.clientX - pStart) / pitch);
    const dt = Math.max(1, now - pt) / 1000;
    pv = pv * 0.6 + ((np - pos) / dt) * 0.4;
    pos = np; pt = now; px = e.clientX;
  });
  const release = () => {
    if (!pDown) return;
    pDown = false;
    if (dragging) {
      dragging = false; reel.classList.remove("dragging");
      vel = pv;
      target = clamp(Math.round(pos + Math.max(-2, Math.min(2, pv * 0.22))));
      kick();
      setTimeout(() => { dragMoved = false; }, 0);
    }
  };
  reel.addEventListener("pointerup", release);
  reel.addEventListener("pointercancel", release);
  // wheel: notches step a frame, trackpads run the strip
  reel.addEventListener("wheel", (e) => {
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (!d) return;
    e.preventDefault();
    const now = performance.now();
    if (Math.abs(d) >= 80 && e.deltaMode === 0) {
      if (now - lastWheel > 130) { step(d > 0 ? 1 : -1); lastWheel = now; }
      return;
    }
    const { pitch } = geometry();
    pos = clamp(pos + d / pitch * 1.4); target = pos;
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => { target = Math.round(pos); kick(); }, 110);
    kick();
  }, { passive: false });

  /* ---------- panel ---------- */
  const signalsOf = (t) => {
    const rate = t.views == null ? null : t.likeRate;
    return el("div", { class: "signals" },
      el("span", {}, fmtViews(t.views), " ", el("small", {}, t.views == null ? "" : "views")),
      rate != null && el("span", {}, rate.toFixed(2), " ", el("small", {}, "like rate"), t.thin && el("span", { class: "few", title: "Under 20 likes: too few votes to rank on" }, "few votes")),
      el("span", {}, t.hearts, " ", el("small", {}, "hearts")));
  };
  const pickBlock = (v) => {
    const p = v.pick, t = p && byId.get(p.talkId);
    if (!t) return el("div", { class: "credit" }, el("p", { class: "hint" }, "No pick yet for this verdict."));
    return el("div", { class: "credit" },
      el("h3", {}, "Watch first"),
      el("p", { class: "ttl" }, t.title),
      el("p", { class: "who" }, speakerLine(t)),
      el("p", { class: "why" }, p.why),
      signalsOf(t),
      el("button", { class: "cta", type: "button", on: { click: () => openTalk(t.id) } }, t.seat ? "Go to this talk" : "Read the summary"));
  };
  const storyPanel = () => {
    const key = frameDefs()[nearest < 0 ? 1 : nearest];
    if (key === "leader") {
      return el("div", { class: "story" },
        el("div", { class: "left" },
          el("p", { class: "fcount" }, `${M.event}, ${M.dates}, ${M.venue}`),
          el("p", { class: "consensus intro" }, M.recap.intro),
          el("p", { class: "hint", style: "margin-top:auto" }, "Drag the reel, scroll it, or press ", el("kbd", {}, "←"), " ", el("kbd", {}, "→"), " to run it through the gate.")),
        el("div", { class: "credit" },
          el("h3", {}, "Eight verdicts follow"),
          el("p", { class: "why" }, "Each one says what the speakers agreed on, then where they split. The last frame lists one talk to watch first for each verdict."),
          el("button", { class: "cta", type: "button", on: { click: () => goTo(1) } }, "Start the reel")));
    }
    if (key === "credits") {
      return el("div", { class: "story" }, el("div", { class: "rollgrid" }, verdicts.map((v) => {
        const t = v.pick && byId.get(v.pick.talkId);
        if (!t) return null;
        return el("button", { class: "roll", type: "button", on: { click: () => openTalk(t.id) }, title: v.pick.why },
          el("span", { class: "rv" }, v.title),
          el("span", { class: "rt" }, t.title.length > 62 ? t.title.slice(0, 60) + "…" : t.title),
          el("span", { class: "rw" }, speakerLine(t) + ", " + fmtViews(t.views) + " views"));
      })));
    }
    const v = verdicts[+key.slice(1)];
    const idx = nearest;
    return el("div", { class: "story" },
      el("div", { class: "left" },
        el("p", { class: "fcount" }, `Verdict ${idx} of 8, ${v.count} talks`),
        el("p", { class: "consensus" }, v.consensus),
        el("div", { class: "versus-row" },
          el("p", { class: "q" }, "Where they split: ", v.debate.question),
          el("button", { class: "cta", type: "button", on: { click: () => openVersus(v.i) } }, "Open the debate")),
        el("div", { class: "duel", style: `grid-template-columns:repeat(${v.debate.sides.length},1fr)` }, v.debate.sides.map((sd, k) => el("div", { class: "duelside " + "abc"[k] },
          el("p", { class: "ds" }, sd.stance.split(/(?<=[.!?])\s/)[0]),
          el("p", { class: "dw" }, sd.who.join(", ")))))),
      pickBlock(v));
  };

  const sortTalks = (arr, key) => {
    const val = { views: (t) => t.views, rate: (t) => t.likeRate, hearts: (t) => t.hearts };
    if (key === "relevance") return arr;
    const f = val[key];
    return arr.slice().sort((a, b) => {
      const A = f(a.t), B = f(b.t);
      if (A == null && B == null) return 0;
      if (A == null) return 1;
      if (B == null) return -1;
      if (key === "rate" && a.t.thin !== b.t.thin) return a.t.thin ? 1 : -1; // never rank on few votes
      return B - A;
    });
  };
  const talkRows = () => {
    let base = state.results ? state.results.slice().sort((a, b) => b.score - a.score) : M.talks.map((t) => ({ t, score: 0 }));
    if (state.hideThin) base = base.filter((r) => !r.t.thin && r.t.views != null);
    const key = state.sort || (state.results ? "relevance" : "views");
    return { rows: sortTalks(base, key), key };
  };
  const talksPanel = () => {
    const { rows, key } = talkRows();
    const sb = (k, label, w) => el("button", { class: "sortbtn", type: "button", "aria-pressed": String(key === k), title: w, on: { click: () => { state.sort = k; renderPanel(true); } } }, label);
    const count = el("p", { class: "count" }, state.results ? `${rows.length} ${rows.length === 1 ? "talk" : "talks"} for “${state.query.trim()}”` : `${rows.length} talks`,
      state.results && key !== "relevance" ? el("small", {}, el("button", { class: "sortbtn", style: "text-align:left;color:var(--cyan)", type: "button", on: { click: () => { state.sort = null; renderPanel(true); } } }, "back to best match")) : null);
    const head = el("div", { class: "lhead" }, count, sb("views", "Views", "Reach: how many people watched"), sb("rate", "Like rate", "Likes per 100 views; talks with under 20 likes are ranked last"), sb("hearts", "Hearts", "Devoxx app favourites before the talk: interest, not quality"));
    const list = el("ul", { class: "rows" });
    if (!rows.length) {
      list.append(el("li", { class: "empty" }, el("p", {}, "No talk matches that. Try a speaker, a tool such as Leyden, or a topic such as security."),
        el("button", { class: "btn", type: "button", on: { click: () => { q.value = ""; onQuery(); q.focus(); } } }, "Clear the search")));
    }
    for (const { t } of rows) {
      const vi = verdictOf.get(t.id);
      list.append(el("li", {}, el("button", { class: "row", type: "button", on: { click: () => openTalk(t.id) } },
        el("span", {}, el("span", { class: "t" }, t.title), el("span", { class: "s" }, speakerLine(t), t.speakers[0] && t.speakers[0].company ? ", " + t.speakers[0].company : "", vi != null ? el("span", { class: "tag" }, ` (verdict ${vi + 1})`) : null)),
        el("span", { class: "n" }, fmtViews(t.views)),
        el("span", { class: "n" + (t.thin ? " thin" : "") }, t.views == null ? el("em", {}, "none") : [t.likeRate.toFixed(2), t.thin ? el("span", { class: "few" }, "few votes") : null]),
        el("span", { class: "n" }, String(t.hearts)))));
    }
    const legend = el("p", { class: "legend" }, (PHONE ? "Orange like rate: under 20 likes, few votes, ranked last. Hearts are interest, not quality." : "Like rate is likes per 100 views; under 20 likes means few votes, so it is ranked last. Hearts are interest before the talk, not quality."));
    const filt = el("button", { class: "btn", style: "height:28px;margin-left:8px;font-size:14px", type: "button", "aria-pressed": String(state.hideThin), on: { click: () => { state.hideThin = !state.hideThin; renderPanel(true); } } }, "Hide few votes");
    legend.append(filt);
    return el("div", { class: "list" }, head, list, legend);
  };
  const programmePanel = () => {
    const tabs = el("div", { class: "days", role: "group", "aria-label": "Day" }, days.map((d) => {
      const first = M.talks.find((t) => dayKey(t.start) === d);
      return el("button", { class: "btn", type: "button", "aria-pressed": String(state.day === d), on: { click: () => { state.day = d; renderPanel(true); } } }, dayLabel(first.start));
    }));
    const todays = M.talks.filter((t) => dayKey(t.start) === state.day).sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, "en", { numeric: true }));
    tabs.append(el("span", { class: "count" }, `${todays.length} talks, Brussels time`));
    const list = el("div", { class: "rows" });
    let cur = null, ul;
    for (const t of todays) {
      if (t.start !== cur) {
        cur = t.start; ul = el("ul");
        list.append(el("div", { class: "slot" }, el("time", { datetime: t.start }, timeLabel(t.start)), ul));
      }
      ul.append(el("li", {}, el("button", { class: "prow", type: "button", on: { click: () => openTalk(t.id) } },
        el("span", { class: "r" }, t.room), el("span", { class: "t" }, t.title), el("span", { class: "s" }, speakerLine(t)))));
    }
    return el("div", { class: "list" }, tabs, list);
  };
  let rowsScroll = 0;
  const renderPanel = (keepScroll) => {
    const old = panel.querySelector(".rows");
    if (keepScroll && old) rowsScroll = old.scrollTop; else rowsScroll = 0;
    panel.replaceChildren(state.mode === "story" ? storyPanel() : state.mode === "talks" ? talksPanel() : programmePanel());
    const r = panel.querySelector(".rows");
    if (r) r.scrollTop = rowsScroll;
  };

  /* ---------- modes ---------- */
  function setMode(m) {
    state.mode = m;
    menu.dataset.mode = m;
    bTalks.setAttribute("aria-pressed", String(m === "talks"));
    bProg.setAttribute("aria-pressed", String(m === "programme"));
    renderPanel();
    // frame sizes animate; keep the strip centred while they do
    const until = performance.now() + 450;
    const follow = () => { render(); if (performance.now() < until) requestAnimationFrame(follow); };
    follow();
  }
  function onQuery() {
    state.query = q.value;
    state.results = search(q.value);
    state.sort = null;
    const keep = frameDefs()[Math.round(pos)];
    const ranked = verdicts.map((v) => {
      const hits = state.results ? state.results.filter((r) => v.cited.has(r.t.id)).length : 0;
      state.hits.set(v.i, hits);
      return v;
    });
    state.order = state.results
      ? ranked.slice().sort((a, b) => state.hits.get(b.i) - state.hits.get(a.i) || a.i - b.i).map((v) => v.i)
      : verdicts.map((v) => v.i);
    layoutFrames(true);
    const j = frameDefs().indexOf(keep);
    if (j >= 0) { pos = j; render(); }
    if (state.results && state.mode === "story") state.mode = "talks";
    if (state.results) setMode("talks"); else renderPanel();
    goTo(1);
  }
  q.addEventListener("input", onQuery);

  /* ---------- versus overlay ---------- */
  let returnFocus = null;
  function openVersus(i) {
    const v = verdicts[i];
    returnFocus = document.activeElement;
    const side = (s, cls, label) => el("div", { class: "side " + cls },
      el("p", {}, s.stance),
      el("p", { class: "who" }, "Speakers: " + s.who.join(", ")),
      el("div", { class: "tl" }, s.talkIds.map((id) => {
        const t = byId.get(id);
        return t ? el("button", { class: "tbtn", type: "button", on: { click: () => openTalk(id) } }, t.title, el("small", {}, speakerLine(t))) : null;
      })));
    versus.replaceChildren(
      el("div", { class: "vtop" },
        el("button", { class: "btn back", type: "button", on: { click: closeVersus } }, "Back to the reel"),
        el("p", { class: "crumb" }, `Verdict ${state.order.indexOf(i) + 1} of 8: ${v.title}`)),
      el("div", { class: "vcons" }, el("p", {}, v.consensus)),
      el("div", { class: "vbody" },
        el("h2", { class: "vq" }, v.debate.question),
        el("div", { class: "vsides n" + v.debate.sides.length }, v.debate.sides.flatMap((sd, k) => [k ? el("div", { class: "vs", "aria-hidden": "true" }, "vs") : null, side(sd, "abc"[k])])),
        el("details", { class: "long" }, el("summary", {}, "What was said in the talks"), el("p", {}, v.body))));
    for (const n of [top, reel, panel]) n.inert = true;
    versus.className = "versus on" + (REDUCED ? "" : " anim");
    if (!REDUCED) {
      const g = frameEls.get("v" + i).getBoundingClientRect(), m = menu.getBoundingClientRect();
      versus.style.clipPath = `inset(${g.top - m.top}px ${m.right - g.right}px ${m.bottom - g.bottom}px ${g.left - m.left}px round 4px)`;
      versus.offsetWidth;
      versus.classList.add("go");
      versus.style.clipPath = "inset(0px 0px 0px 0px round 0px)";
    }
    versus.querySelector(".back").focus();
  }
  function closeVersus() {
    versus.className = "versus";
    versus.style.clipPath = "";
    for (const n of [top, reel, panel]) n.inert = false;
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus({ preventScroll: true });
    returnFocus = null;
  }

  /* ---------- keyboard ---------- */
  document.addEventListener("keydown", (e) => {
    const inField = /^(input|textarea|select)$/i.test(e.target.tagName);
    if (versus.classList.contains("on")) {
      if (e.key === "Escape") { e.preventDefault(); closeVersus(); }
      else if (e.key === "Tab") {
        const f = [...versus.querySelectorAll("button, summary, a[href]")].filter((n) => n.offsetParent);
        if (!f.length) return;
        const first = f[0], lastF = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastF.focus(); }
        else if (!e.shiftKey && document.activeElement === lastF) { e.preventDefault(); first.focus(); }
      }
      return;
    }
    if (e.key === "Escape") {
      if (inField && q.value) { q.value = ""; onQuery(); }
      if (state.mode !== "story") { setMode("story"); (inField ? q : bTalks).blur?.(); }
      return;
    }
    if (inField) return;
    if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
    else if (e.key === "Home") { e.preventDefault(); goTo(0); }
    else if (e.key === "End") { e.preventDefault(); goTo(frameDefs().length - 1); }
    else if (e.key === "/") { e.preventDefault(); q.focus(); }
  });

  /* ---------- gate weave: a hair of film wobble, 8 fps ---------- */
  if (!REDUCED) {
    setInterval(() => {
      const g = track.querySelector(".frame.gate .face");
      if (!g) return;
      const x = (Math.random() - 0.5) * 1.1, y = (Math.random() - 0.5) * 1.1;
      g.style.transform = `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
    }, 125);
  }

  /* ---------- boot ---------- */
  state.verdicts = verdicts;
  layoutFrames(false);
  menu.dataset.mode = "story";
  pos = target = 1;
  setNearest(1);
  render();
  document.fonts && document.fonts.ready.then(() => render());
  addEventListener("resize", render);
  window.__reel = { goTo, setMode, openVersus, q, onQuery, state };
})();
