// Two Hundred and Five Seats: the hall screen draws the plan of the room behind it, one seat per talk.
// t4: one auditorium under one lit screen. The screen and every row are arcs round one centre C behind the screen;
// three (phone: one) radial aisles are the only breaks. The two front rows (phone: four) are the eight verdicts, runs
// of sand seats named right on them (the first front row's names above it, the second's below it, so the two rows sit
// together as one band); behind a cross aisle the back stalls are one flat slate field. The title is projected on the
// screen. Lists and verdicts clear the plan away instead of setting type over faded seats.
(() => {
  "use strict";
  const M = window.MENU;
  const menu = document.getElementById("menu");
  const $ = (s, r = menu) => r.querySelector(s);
  const PHONE = document.documentElement.dataset.shape === "phone";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)");
  const TRENDS = M.recap.trends;
  const TALKS = M.talks;
  const byId = new Map(TALKS.map((t) => [t.id, t]));
  const pickOf = new Map(M.picks.map((p) => [p.talkId, p]));

  // ---------- formatting ----------
  const TZ = "Europe/Brussels";
  const fTime = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });
  const fDay = new Intl.DateTimeFormat("en-CA", { timeZone: TZ });
  const fWd = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short", day: "numeric" });
  const fWdShort = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short" });
  const fLong = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });
  const fDM = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "numeric", month: "long" });
  const fD = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "numeric" });
  const dayKey = (t) => (t.start ? fDay.format(new Date(t.start)) : "");
  const whenOf = (t) => (t.start ? `${fWd.format(new Date(t.start))} at ${fTime.format(new Date(t.start))}` : "");
  const num = new Intl.NumberFormat("en-GB");
  const names = (t) => t.speakers.map((s) => s.name).join(", ");
  const el = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null && k !== false) e.append(k);
    return e;
  };

  // ---------- who sits where ----------
  // A talk sits in the run of the first verdict that lists it; everything else sits in the back stalls.
  const blockOf = new Map();
  TRENDS.forEach((tr, i) => tr.talkIds.forEach((id) => { if (byId.has(id) && !blockOf.has(id)) blockOf.set(id, i); }));
  const members = TRENDS.map((_, i) => TALKS.filter((t) => blockOf.get(t.id) === i));
  const backTalks = TALKS.filter((t) => !blockOf.has(t.id));

  // The order decides who sits first in each run (and in the centre front of the stalls) and which tenth is lit.
  const SORTS = {
    views: { word: "most watched", key: (t) => (t.views == null ? -1 : t.views), best: "the most watched" },
    likes: { word: "best liked", key: (t) => (t.likeRate == null ? -2 : t.thin ? -1 + t.likeRate / 100 : t.likeRate), best: "the best liked" },
    hearts: { word: "most hearts", key: (t) => t.hearts ?? -1, best: "the most hearts" },
  };
  for (const s of Object.values(SORTS)) {      // rank among the 205 (0 last, 1 first)
    const keys = TALKS.map(s.key).sort((a, b) => a - b);
    const rank = new Map(); keys.forEach((k, i) => rank.set(k, i / (keys.length - 1)));
    s.rank = (t) => rank.get(s.key(t));
  }
  const ORDER = ["views", "likes", "hearts"];
  const bySort = (a, b) => SORTS[S.sort].key(b) - SORTS[S.sort].key(a) || a.title.localeCompare(b.title);

  // ---------- the plan's geometry: polar, round a centre C behind the screen ----------
  // d is the distance below the screen arc. tiers: the verdict rows; side: where that row's names sit.
  const G = PHONE
    ? { W: 340, half: 157, R0: 650, screenHalf: 112, screenMid: 12, sections: 2, perRow: 2, aisle: 16, sw: 12, sh: 10, px: 14, splay: 0,
      tierD: [176, 190, 287, 301], side: ["above", "below", "above", "below"], back: { d0: 356, pitch: 13.5, rows: 8 }, gap: 4 }
    : { W: 980, half: 452, R0: 2800, screenHalf: 300, screenMid: 26, sections: 2, perRow: 4, aisle: 26, splay: .4, sw: 19, sh: 16, px: 25, pxFront: 24,
      tierD: [180, 205], side: ["above", "below"], back: { d0: 294, pitch: 24, rows: 5 }, gap: 6 };
  const C = { x: G.W / 2, y: G.screenMid - G.R0 };
  const at = (d, th) => { const r = G.R0 + d; return { x: C.x + r * Math.sin(th), y: C.y + r * Math.cos(th), a: (-th * 180) / Math.PI, d }; };
  const dLast = G.back.d0 + (G.back.rows - 1) * G.back.pitch;
  // the side walls splay out towards the back wall, as a fan does (the front rows are as wide as the stalls' first)
  const halfAt = (d) => G.half - (dLast - Math.max(d, G.back.d0)) * G.splay;
  const sectionsAt = (d) => {
    const r = G.R0 + d, aOut = Math.asin(halfAt(d) / r), gap = G.aisle / r, span = (2 * aOut - (G.sections - 1) * gap) / G.sections;
    return Array.from({ length: G.sections }, (_, k) => { const t0 = -aOut + k * (span + gap); return { t0, t1: t0 + span, mid: t0 + span / 2, arc: span * r }; });
  };
  // n seats of a row's section, packed against the centre aisle (a short row stays with the room's middle)
  const packed = (d, sec, k, n) => {
    const r = G.R0 + d, step = G.px / r, inner = k < G.sections / 2 ? sec.t1 - G.sw / 2 / r : sec.t0 + G.sw / 2 / r;
    if (G.sections !== 2) return centred(d, sec, n);
    return Array.from({ length: n }, (_, i) => at(d, k === 0 ? inner - i * step : inner + i * step));
  };
  const centred = (d, sec, n) => { const step = G.px / (G.R0 + d); return Array.from({ length: n }, (_, i) => at(d, sec.mid + (i - (n - 1) / 2) * step)); };
  const centreOut = (p, q) => Math.abs(p.x - C.x) - Math.abs(q.x - C.x) || p.x - q.x;

  // the front: G.perRow runs per row. On the big screen two per half: run b sits in half floor(j / 2), slot j % 2 of
  // row floor(b / 4); on the phone one per half. Each run starts at its slot's left edge, its first seat the best by
  // the current order.
  const runs = [], runMeta = [];
  TRENDS.forEach((_, b) => {
    const per = G.perRow, tier = Math.floor(b / per), j = b % per, slots = per / G.sections;
    const k = Math.floor(j / slots), slot = j % slots, d = G.tierD[tier], r = G.R0 + d;
    const sec = sectionsAt(d)[k], n = members[b].length, slotSpan = (sec.t1 - sec.t0) / slots;
    const s0 = sec.t0 + slot * slotSpan;
    const th0 = s0 + G.sw / 2 / r, step = (G.pxFront || G.px) / r;
    runs.push(Array.from({ length: n }, (_, i) => ({ ...at(d, th0 + i * step), row: tier })));
    runMeta.push({ tier, k, d, end: slot < slots - 1 ? s0 + slotSpan : k < G.sections - 1 ? sectionsAt(d)[k + 1].t0 : null });
  });
  // back stalls: rows front to back, each section's row as full as its arc allows, seats shared in proportion
  const nBack = backTalks.length;
  const back = [];
  {
    const rows = Array.from({ length: G.back.rows }, (_, i) => {
      const d = G.back.d0 + i * G.back.pitch, secs = sectionsAt(d);
      return { d, i, secs, cap: secs.map((sc) => Math.floor((sc.arc - G.sw) / G.px) + 1) };
    });
    const room = rows.reduce((a, r) => a + r.cap.reduce((x, y) => x + y, 0), 0);
    if (room < nBack) console.warn(`seat-plan: ${nBack - room} talks without a seat`);
    // rows fill from the back wall, every section full, so each row runs unbroken from wall to wall but for the
    // aisles; the stalls' front row takes what is left, shared over its sections and centred in each (a fan narrows
    // towards the screen)
    const cells = [];
    let left = nBack;
    [...rows].reverse().forEach((r) => {
      if (left <= 0) { r.cap.forEach((c, k) => cells.push({ r, k, n: 0 })); return; }
      const full = r.cap.reduce((x, y) => x + y, 0);
      if (left >= full) { r.cap.forEach((c, k) => cells.push({ r, k, n: c })); left -= full; return; }
      const f = left / full, part = r.cap.map((c, k) => ({ k, n: Math.floor(c * f), frac: c * f - Math.floor(c * f), c }));
      let rest = left - part.reduce((a, x) => a + x.n, 0);
      [...part].sort((a, b) => b.frac - a.frac).forEach((x) => { if (rest > 0 && x.n < x.c) { x.n++; rest--; } });
      part.forEach((x) => cells.push({ r, k: x.k, n: x.n }));
      left = 0;
    });
    rows.forEach((r) => {
      const row = r.secs.flatMap((sc, k) => packed(r.d, sc, k, cells.find((x) => x.r === r && x.k === k).n)).map((p) => ({ ...p, row: G.tierD.length + r.i }));
      row.sort(centreOut);
      back.push(...row);
    });
  }
  const allSlots = [...runs.flat(), ...back].sort((p, q) => p.row - q.row || p.x - q.x);

  // the screen: a lit band, an arc of the same circle
  const arcPath = (d, half) => {
    const r = G.R0 + d, t = Math.asin(half / r), pts = [];
    for (let i = 0; i <= 48; i++) { const th = -t + (2 * t * i) / 48; pts.push(`${(C.x + r * Math.sin(th)).toFixed(1)} ${(C.y + r * Math.cos(th)).toFixed(1)}`); }
    return "M " + pts.join(" L ");
  };
  $(".screen-band").setAttribute("d", arcPath(0, G.screenHalf));
  menu.style.setProperty("--title-top", `${G.screenMid + (PHONE ? 16 : 14)}px`);

  // ---------- state ----------
  const S = { mode: "rest", sort: "views", day: null, query: "", verdict: null, sel: null, hover: null, matches: [], list: [], navigable: null };
  const seats = new Map();     // id -> { t, el, slot }
  const plan = $(".plan");
  for (const t of [...members.flat(), ...backTalks]) {
    const b = el("button", { class: "seat" + (blockOf.has(t.id) ? " v" : ""), type: "button", tabindex: "-1", "data-id": t.id, "aria-label": `${t.title}, ${names(t)}, ${t.room}` });
    plan.append(b);
    seats.set(t.id, { t, el: b, slot: null });
  }
  const feature = () => [...TALKS].sort(bySort)[0].id;    // the top talk by the order is lit before anyone touches the screen

  const pose = (p, w, h) => `translate(${(p.x - w / 2).toFixed(1)}px, ${(p.y - h / 2).toFixed(1)}px) rotate(${p.a.toFixed(2)}deg)`;
  function place(assign, animate) {
    const reduce = REDUCED.matches || !animate;
    for (const [id, slot] of assign) {
      const s = seats.get(id);
      const moved = s.slot && (s.slot.x !== slot.x || s.slot.y !== slot.y);
      s.slot = slot;
      s.el.style.transitionDelay = reduce || !moved ? "0ms" : `${Math.min(slot.row * 30 + Math.abs(slot.x - C.x) * 0.12, 320) | 0}ms`;
      s.el.style.setProperty("--pose", pose(slot, G.sw, G.sh));
    }
    clearTimeout(place.t);
    place.t = setTimeout(() => { for (const [, s] of seats) s.el.style.transitionDelay = "0ms"; }, 900);
    if (reduce) { menu.classList.add("still"); void menu.offsetWidth; requestAnimationFrame(() => requestAnimationFrame(() => menu.classList.remove("still"))); }
  }
  // one flat colour per stall; the order's top tenth a step lighter (no front-to-back ramp)
  const TOP = 0.9;
  function light() {
    for (const [, s] of seats) s.el.classList.toggle("top", SORTS[S.sort].rank(s.t) >= TOP);
  }

  // seats move only when the order changes who sits first (and in watch mode, where each verdict's pick sits first)
  function seatAll(animate = true) {
    const assign = new Map();
    members.forEach((m, b) => {
      const list = [...m].sort(bySort);
      if (S.mode === "watch") list.sort((a, c) => pickOf.has(c.id) - pickOf.has(a.id));
      list.forEach((t, i) => assign.set(t.id, runs[b][i]));
    });
    [...backTalks].sort(bySort).forEach((t, i) => assign.set(t.id, back[i]));
    place(assign, animate);
    refresh();
  }
  // which seats can be reached, and the list
  function refresh() {
    if (S.mode === "day") S.navigable = new Set(TALKS.filter((t) => dayKey(t) === S.day).map((t) => t.id));
    else if (S.mode === "search") S.navigable = new Set(S.matches);
    else if (S.mode === "watch") S.navigable = new Set(pickOf.keys());
    else if (S.mode === "story") S.navigable = new Set();
    else S.navigable = null;
    const listed = S.mode === "day" ? TALKS.filter((t) => dayKey(t) === S.day).sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, "en", { numeric: true }))
      : S.mode === "search" ? S.matches.map((id) => byId.get(id)) : [];
    S.list = listed.map((t) => t.id);
    renderList(listed);
    paint();
  }

  // ---------- painting: the orange seat, what is lit and dim, the readout ----------
  const now = { title: $(".now-title"), meta: $(".now-meta") };
  const navOK = (id) => !S.navigable || S.navigable.has(id);
  const shown = () => (S.mode === "story" ? null : S.hover ?? S.sel ?? (S.mode === "rest" ? feature() : null));

  function metric(t, best) {
    const tail = best ? `, ${SORTS[S.sort].best}` : "";
    if (S.sort === "views") return t.views == null ? null : `${num.format(t.views)} views${tail}`;
    if (S.sort === "likes") return t.likeRate == null ? null : `${t.likeRate.toFixed(2)} likes per 100 views${t.thin ? ", few votes" : tail}`;
    return `${num.format(t.hearts)} hearts${tail}`;
  }
  const span = (x, cls) => (x == null ? null : el("span", { class: cls }, x));
  const glyph = () => el("i", { class: "glyph", "aria-hidden": "true" });

  function paint() {
    const id = shown();
    const story = S.mode === "story", listMode = S.mode === "day" || S.mode === "search";
    const isFeat = S.mode === "rest" && S.hover == null && S.sel == null && id === feature();
    for (const [sid, s] of seats) {
      const inRun = blockOf.has(sid);
      s.el.classList.toggle("on", !listMode && sid === id);
      s.el.classList.toggle("gone", story && !inRun);
      s.el.classList.toggle("dim", story ? inRun && S.verdict != null && blockOf.get(sid) !== S.verdict : S.mode === "watch" && !navOK(sid));
      s.el.classList.toggle("pk", S.mode === "watch" && pickOf.has(sid));
      s.el.tabIndex = -1;
    }
    if (!story && !listMode) {
      const rovingId = S.sel != null && navOK(S.sel) ? S.sel : S.mode === "rest" ? feature() : firstNav();
      const roving = seats.get(rovingId);
      if (roving) roving.el.tabIndex = 0;
    }
    vBtns.forEach((b, i) => {
      b.classList.toggle("lit", i === (story ? S.verdict : id != null && !listMode && blockOf.has(id) ? blockOf.get(id) : null));
      b.setAttribute("aria-pressed", String(story && S.verdict === i));
    });

    for (const r of rowsEl.children) {
      const b = r.firstChild, rid = +b.dataset.id;
      b.classList.toggle("on", rid === id);
      b.tabIndex = rid === (S.sel ?? +rowsEl.firstChild.firstChild.dataset.id) ? 0 : -1;
    }

    now.title.replaceChildren(); now.meta.replaceChildren();
    if (id == null || story || listMode) return;
    const t = byId.get(id);
    now.title.append(glyph(), t.title);
    const pick = pickOf.get(id);
    if (S.mode === "watch" && pick) { now.meta.append(span(pick.why)); return; }
    now.meta.append(...[span(`${names(t)}, ${t.room}, ${whenOf(t)}`, "who"), span(metric(t, isFeat), "num")].filter(Boolean));
  }

  // ---------- the list: a day's programme, or the search results ----------
  const findEl = $(".find"), rowsEl = $(".rows"), capEl = $(".cap"), moreEl = $(".more-note"), sortsEl = $(".sorts");
  const COLS = PHONE ? 1 : 2;
  function renderList(front) {
    const on = S.mode === "day" || S.mode === "search";
    findEl.hidden = !on;
    if (!on) { rowsEl.replaceChildren(); return; }
    if (S.mode === "day") {
      const d = DAYS.find((x) => x.key === S.day);
      capEl.textContent = `${d.long}: ${front.length} talks in time order. Times in Brussels.`;
    } else {
      capEl.textContent = !S.query ? `All ${TALKS.length} talks, ${SORTS[S.sort].word} first. Type a title, a speaker, a company or a topic.`
        : front.length ? `${front.length} ${front.length === 1 ? "talk matches" : "talks match"} “${S.query}”, ${SORTS[S.sort].word} first.`
          : `No talk matches “${S.query}”. Try a speaker, a company or a topic, like Valhalla or Spring.`;
    }
    const numbered = S.mode === "search";
    rowsEl.replaceChildren(...front.map((t, i) => el("li", {}, el("button", {
      class: "row", type: "button", tabindex: "-1", "data-id": t.id,
      "aria-label": `${numbered ? i + 1 + ". " : ""}${t.title}, ${names(t)}, ${t.room}, ${whenOf(t)}`,
    }, numbered ? el("span", { class: "lead seatno" + (blockOf.has(t.id) ? " v" : ""), "aria-hidden": "true", text: String(i + 1) })
      : el("span", { class: "lead time", text: t.start ? fTime.format(new Date(t.start)) : "" }),
      el("span", { class: "title", text: t.title }),
      el("span", { class: "meta" }, el("span", { class: "who", text: `${names(t)}, ${t.room}${numbered && t.start ? ", " + fWdShort.format(new Date(t.start)) + " " + fTime.format(new Date(t.start)) : ""}` }),
        metric(t) ? el("span", { class: "fig", text: metric(t) }) : null)))));
    rowsEl.scrollTop = 0;
    requestAnimationFrame(fitRows);
  }
  // the list stops at a whole row; a quiet note says how many more are below
  function fitRows() {
    if (findEl.hidden) return;
    rowsEl.style.height = "";
    const rowH = parseFloat(getComputedStyle(rowsEl).gridAutoRows) || 84;
    const avail = findEl.clientHeight - rowsEl.offsetTop - moreEl.offsetHeight - 4;
    rowsEl.style.height = `${Math.max(1, Math.floor(avail / rowH)) * rowH}px`;
    noteMore();
  }
  function noteMore() {
    const lis = [...rowsEl.children];
    const below = lis.filter((li) => li.offsetTop - rowsEl.offsetTop + li.offsetHeight > rowsEl.scrollTop + rowsEl.clientHeight + 2).length;
    moreEl.textContent = below ? `${below} more below` : "";
  }
  rowsEl.addEventListener("scroll", noteMore, { passive: true });
  const rowOf = (id) => rowsEl.querySelector(`[data-id="${id}"]`);
  const reveal = (id) => rowOf(id)?.scrollIntoView({ block: "nearest" });
  rowsEl.addEventListener("pointerover", (e) => { const b = e.target.closest(".row"); if (b && e.pointerType !== "touch") { S.hover = +b.dataset.id; paint(); } });
  rowsEl.addEventListener("pointerleave", () => { if (S.hover != null) { S.hover = null; paint(); } });
  rowsEl.addEventListener("click", (e) => { const b = e.target.closest(".row"); if (b) { S.sel = +b.dataset.id; paint(); openTalk(S.sel); } });
  rowsEl.addEventListener("focusin", (e) => { const b = e.target.closest(".row"); if (b) { S.sel = +b.dataset.id; S.hover = null; paint(); } });
  rowsEl.addEventListener("keydown", (e) => {
    const b = e.target.closest(".row");
    if (!b) return;
    const lis = [...rowsEl.children], i = lis.indexOf(b.parentElement);
    const j = { ArrowDown: i + COLS, ArrowUp: i - COLS, ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: lis.length - 1 }[e.key];
    if (j == null) return;
    e.preventDefault();
    lis[Math.max(0, Math.min(lis.length - 1, j))].firstChild.focus();
  });

  const idAt = (slot) => { for (const [id, s] of seats) if (s.slot === slot) return id; return null; };
  const firstNav = () => {
    if ((S.mode === "search" || S.mode === "day") && S.list.length) return S.list[0];
    for (const s of allSlots) { const id = idAt(s); if (id != null && navOK(id)) return id; }
    return null;
  };

  // ---------- opening a talk ----------
  const toast = $(".toast");
  let toastTimer = 0;
  function openTalk(id) {
    const t = byId.get(+id);
    if (!t) return;
    toast.replaceChildren(glyph(), t.seat ? `Walking to ${t.room}` : "Opening the summary");
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
    menu.dispatchEvent(new CustomEvent("opentalk", { detail: { id: t.id, seat: !!t.seat, room: t.room } }));
  }
  window.openTalk = openTalk;

  // ---------- seats: pointer and keys ----------
  let lastPointer = "mouse";
  plan.addEventListener("pointerdown", (e) => { lastPointer = e.pointerType || "mouse"; });
  plan.addEventListener("pointerover", (e) => {
    const b = e.target.closest(".seat");
    if (!b || S.mode === "story" || e.pointerType === "touch") return;
    const id = +b.dataset.id;
    if (!navOK(id)) return;
    S.hover = id; paint();
  });
  plan.addEventListener("pointerleave", () => { if (S.hover != null) { S.hover = null; paint(); } });
  plan.addEventListener("click", (e) => {
    const b = e.target.closest(".seat");
    if (!b) { if (S.mode !== "rest") go("rest"); return; }
    const id = +b.dataset.id;
    if (S.mode === "story") { if (blockOf.has(id)) pickVerdict(blockOf.get(id)); return; }
    if (!navOK(id)) return;
    if (lastPointer === "touch" && S.sel !== id) { S.sel = id; paint(); return; }   // tap selects, second tap opens
    S.sel = id; paint(); openTalk(id);
  });
  plan.addEventListener("focusin", (e) => {
    const b = e.target.closest(".seat");
    if (!b) return;
    S.sel = +b.dataset.id; S.hover = null; paint();
  });
  plan.addEventListener("focusout", (e) => {
    if (S.mode === "rest" && !plan.contains(e.relatedTarget)) { S.sel = null; paint(); }
  });

  function step(fromId, key) {
    const from = seats.get(fromId).slot;
    const dir = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }[key];
    let best = null, bestScore = Infinity;
    for (const [id, s] of seats) {
      if (id === fromId || !navOK(id)) continue;
      const dx = s.slot.x - from.x, dy = s.slot.y - from.y;
      const along = dx * dir[0] + dy * dir[1], across = Math.abs(dx * dir[1] + dy * dir[0]);
      if (along <= 2) continue;
      const score = along + across * (dir[0] ? 4 : 1.2);
      if (score < bestScore) { bestScore = score; best = id; }
    }
    return best;
  }
  function focusSeat(id) { if (id == null) return; S.sel = id; paint(); seats.get(id).el.focus(); }
  plan.addEventListener("keydown", (e) => {
    const b = e.target.closest(".seat");
    if (!b) return;
    const id = +b.dataset.id;
    if (e.key.startsWith("Arrow")) { e.preventDefault(); focusSeat(step(id, e.key)); }
    else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const ids = allSlots.map(idAt).filter((x) => x != null && navOK(x));
      focusSeat(e.key === "Home" ? ids[0] : ids[ids.length - 1]);
    } else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openTalk(id); }
  });

  // ---------- the verdict names, set right on their runs ----------
  const vWrap = $(".vlabels");
  const vBtns = TRENDS.map((tr, i) => {
    const b = el("button", { type: "button", class: "vlabel", tabindex: i === 0 ? "0" : "-1", "aria-pressed": "false", text: tr.title, onclick: () => pickVerdict(i, true) });
    vWrap.append(b);
    return b;
  });
  // Each name starts at its run's first seat and is flat, or follows the row by at most 3°. It sits as close to its
  // seats as the row's curve allows: GAP px clear of the highest seat under it (names above the row) or the lowest
  // (names below). The width may run on over the aisle, never over the next name.
  const MAXROT = 3;
  let frontBottom = 0, labelTop = Infinity;
  function layoutLabels() {
    frontBottom = 0; labelTop = Infinity;
    vBtns.forEach((b, i) => {
      const m = runMeta[i], run = runs[i], above = G.side[m.tier] === "above";
      const x0 = run[0].x - G.sw / 2;
      const room = m.end != null ? at(m.d, m.end).x - x0 - (PHONE ? -4 : 8) : G.W - 16 - x0;
      b.style.maxWidth = `${Math.floor(room)}px`;
      const w = b.offsetWidth, h = b.offsetHeight;
      const mid = run[Math.floor((run.length - 1) / 2)];
      const rot = Math.max(-MAXROT, Math.min(MAXROT, mid.a)), tan = Math.tan((rot * Math.PI) / 180);
      const row = allSlots.filter((p) => p.row === m.tier && p.x + G.sw / 2 >= x0 && p.x - G.sw / 2 <= x0 + w);
      const pts = row.length ? row : run;
      let y;
      if (above) y = Math.min(...pts.map((p) => p.y - G.sh / 2 - G.gap - (p.x - x0) * tan));
      else y = Math.max(...pts.map((p) => p.y + G.sh / 2 + G.gap - (p.x - x0) * tan));
      b.style.setProperty("--x", `${x0.toFixed(1)}px`);
      b.style.setProperty("--y", `${y.toFixed(1)}px`);
      b.style.setProperty("--rot", `${rot.toFixed(2)}deg`);
      b.style.setProperty("--ty", above ? "-100%" : "0");
      const ys = [0, w].map((dx) => y + dx * tan);
      const top = above ? Math.min(...ys) - h : Math.min(...ys), bottom = above ? Math.max(...ys) : Math.max(...ys) + h;
      labelTop = Math.min(labelTop, top);
      frontBottom = Math.max(frontBottom, bottom, ...run.map((p) => p.y + G.sh / 2));
    });
    menu.style.setProperty("--front-bottom", `${frontBottom.toFixed(0)}px`);
    menu.style.setProperty("--lift", `${Math.max(0, labelTop - (PHONE ? 14 : 18)).toFixed(0)}px`);
  }
  vWrap.addEventListener("keydown", (e) => {
    const d = { ArrowRight: 1, ArrowDown: G.perRow, ArrowLeft: -1, ArrowUp: -G.perRow }[e.key];
    if (!d) return;
    e.preventDefault();
    const i = vBtns.indexOf(document.activeElement), j = Math.max(0, Math.min(vBtns.length - 1, i + d));
    vBtns.forEach((b, k) => (b.tabIndex = k === j ? 0 : -1));
    vBtns[j].focus();
  });
  function pickVerdict(i, toggle = false) {
    if (S.mode !== "story") { go("story", { verdict: i }); return; }
    S.verdict = toggle && S.verdict === i ? null : i;
    vBtns.forEach((b, k) => (b.tabIndex = k === (S.verdict ?? i) ? 0 : -1));
    renderStory(); paint();
  }

  // ---------- modes ----------
  const lede = { days: $(".days"), search: $(".search") };
  const input = $("#q");
  const story = $(".story");
  const chrome = [...menu.querySelectorAll(".chrome button")];
  $(".heading .n").textContent = TALKS.length;
  input.placeholder = `Search ${TALKS.length} talks`;

  function go(mode, opts = {}) {
    if (mode === S.mode && mode !== "rest" && !opts.keep && opts.verdict == null) mode = "rest";        // the active word toggles back
    S.mode = mode; S.hover = null;
    menu.dataset.mode = mode;
    chrome.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.go === mode)));
    lede.days.hidden = mode !== "day";
    lede.search.hidden = mode !== "search";
    sortsEl.hidden = mode !== "search";
    story.hidden = mode !== "story";

    if (mode === "rest") { S.sel = null; S.verdict = null; seatAll(); return; }
    if (mode === "story") {
      S.verdict = opts.verdict ?? null; S.sel = null;
      renderStory(); seatAll();
      (S.verdict != null ? vBtns[S.verdict] : vBtns[0]).focus({ preventScroll: true });
      return;
    }
    if (mode === "watch") { S.sel = null; seatAll(); focusSeat(firstNav()); return; }
    if (mode === "day") { if (!S.day) S.day = DAYS[0].key; renderDays(); S.sel = null; refresh(); S.sel = firstNav(); paint(); lede.days.querySelector('[aria-pressed="true"]').focus(); return; }
    if (mode === "search") { input.value = opts.text ?? S.query; renderSorts(); runSearch(); input.focus(); return; }
  }
  chrome.forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));

  // the order lives where it changes something you read: the search list (which starts as all talks, most watched first)
  function renderSorts() {
    sortsEl.replaceChildren(...ORDER.map((k) => el("button", {
      type: "button", "aria-pressed": String(k === S.sort), text: SORTS[k].word,
      onclick: () => { S.sort = k; menu.dataset.sort = k; renderSorts(); light(); seatAll(false); runSearch(); },
    })));
  }

  // by day
  const DAYS = [...new Set(TALKS.map(dayKey).filter(Boolean))].sort().map((key) => {
    const t = TALKS.find((x) => dayKey(x) === key);
    return { key, date: new Date(t.start), label: fWd.format(new Date(t.start)), long: fLong.format(new Date(t.start)), n: TALKS.filter((x) => dayKey(x) === key).length };
  });
  function renderDays() {
    lede.days.replaceChildren(...DAYS.map((d) => el("button", {
      type: "button", "aria-pressed": String(d.key === S.day), "aria-label": `${d.label}: ${d.n} talks`, text: d.label,
      onclick: () => { S.day = d.key; renderDays(); S.sel = null; refresh(); S.sel = firstNav(); paint(); lede.days.querySelector('[aria-pressed="true"]').focus(); },
    })));
  }
  lede.days.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const i = DAYS.findIndex((d) => d.key === S.day) + (e.key === "ArrowRight" ? 1 : -1);
    if (DAYS[i]) lede.days.children[i].click();
  });

  // the credit under the title: the event, the venue, the week (all from the data)
  {
    const a = DAYS[0].date, z = DAYS[DAYS.length - 1].date;
    $(".credit").textContent = PHONE ? `${M.event}, ${fD.format(a)} to ${fDM.format(z)}` : `${M.event}, ${M.venue}, ${fD.format(a)} to ${fDM.format(z)}`;
  }

  // search: every talk at first (in the current order), then the matches
  const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const hay = new Map(TALKS.map((t) => [t.id, fold([t.title, ...t.speakers.flatMap((s) => [s.name, s.company || ""]), ...t.keywords, ...t.themes, t.tldr || "", t.track || "", t.room].join(" "))]));
  let searchTimer = 0;
  function runSearch() {
    S.query = input.value.trim();
    const terms = fold(S.query).split(/\s+/).filter(Boolean);
    S.matches = TALKS.filter((t) => terms.every((w) => hay.get(t.id).includes(w))).sort(bySort).map((t) => t.id);
    S.sel = S.matches[0] ?? null;
    refresh();
  }
  input.addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => runSearch(), 140); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!S.matches.length) return;
      const i = Math.max(0, S.matches.indexOf(S.sel)) + (e.key === "ArrowDown" ? 1 : -1);
      S.sel = S.matches[(i + S.matches.length) % S.matches.length]; paint(); reveal(S.sel);
    } else if (e.key === "Enter") { e.preventDefault(); clearTimeout(searchTimer); runSearch(); if (S.sel != null) openTalk(S.sel); }
  });

  // verdicts: the names on the front rows are the contents; the chosen verdict takes the back stalls' place
  function talkFor(name, ids) {
    const has = (t) => t.speakers.some((s) => s.name === name);
    return ids.map((i) => byId.get(i)).find((t) => t && has(t)) || TALKS.find(has) || byId.get(ids[0]);
  }
  function renderStory() {
    story.classList.toggle("reading", S.verdict != null);
    if (S.verdict == null) {
      const [first, ...more] = M.recap.intro.split(/(?<=\.)\s+(?=[A-Z])/);
      story.replaceChildren(
        el("p", { class: "intro", text: first }),
        el("p", { class: "intro-more", text: more.join(" ") }),
        el("p", { class: "hint", text: PHONE ? "Tap a verdict’s name to see what was argued." : "Choose a verdict by its name to see what was argued." }));
      story.style.removeProperty("--cs");
      return;
    }
    const tr = TRENDS[S.verdict], pick = M.picks.find((p) => p.verdict === tr.title);
    const pt = pick && byId.get(pick.talkId);
    story.replaceChildren(...[
      el("p", { class: "consensus", text: tr.consensus }),
      el("p", { class: "question", text: tr.debate.question }),
      el("div", { class: "sides", style: `--n:${tr.debate.sides.length}` }, tr.debate.sides.map((sd) => {
        const lead = sd.stance.split(/(?<=\.)\s+/)[0], long = lead.length > 90;
        const by = el(long ? "span" : "p", { class: "by" }, sd.who.map((n) => {
          const t = talkFor(n, sd.talkIds);
          return el("button", { type: "button", "aria-label": `${n}: open ${t.title}`, text: n, onclick: () => openTalk(t.id) });
        }));
        // a stance with no short claim is one long sentence that already names its speakers: the byline runs on after it
        return el("div", { class: "side" }, long ? el("p", { class: "claim long" }, lead + " ", by) : [el("p", { class: "claim", text: lead }), by]);
      })),
      el("div", { class: "foot" },
        pt ? el("button", { class: "watch", type: "button", "aria-label": `Watch first: ${pt.title}. ${pick.why}`, onclick: () => openTalk(pt.id) }, glyph(), `Watch first: ${pt.title}`) : null,
        el("button", { class: "back", type: "button", text: "back to the seats", onclick: () => go("rest") })),
    ].filter(Boolean));
    if (!PHONE) fitStory();
  }
  // the consensus is the heading of this state; it steps down until the verdict fits above the nav, never below 22 px
  function fitStory() {
    const over = () => story.scrollHeight > story.clientHeight + 1;
    for (const px of [29, 27, 25, 23, 22]) { story.style.setProperty("--cs", px + "px"); if (!over()) break; }
    if (over()) console.warn(`seat-plan: verdict ${S.verdict} overflows by ${story.scrollHeight - story.clientHeight}px`);
  }

  // ---------- global keys and the margin ----------
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (S.mode !== "rest") { const was = S.mode; go("rest"); chrome.find((b) => b.dataset.go === was)?.focus(); }
      else if (S.sel != null) { S.sel = null; paint(); }
      return;
    }
    const typing = e.target.closest?.("input");
    if (!typing && e.key.length === 1 && /\S/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey && e.key !== " ") {
      e.preventDefault();
      if (S.mode !== "search") go("search", { text: e.key }); else { input.value += e.key; input.focus(); runSearch(); }
    }
  });
  menu.addEventListener("click", (e) => { if ((e.target === menu || e.target.classList.contains("hall")) && S.mode !== "rest") go("rest"); });
  document.addEventListener("click", (e) => { if (e.target.isConnected && !menu.contains(e.target) && S.mode !== "rest") go("rest"); });

  light();
  seatAll(false);
  layoutLabels();
  // the names are measured in the signage face: lay them out again once it has loaded (they are visible meanwhile)
  document.fonts?.ready.then(() => { layoutLabels(); if (S.mode === "story" && !PHONE) fitStory(); fitRows(); });
})();
