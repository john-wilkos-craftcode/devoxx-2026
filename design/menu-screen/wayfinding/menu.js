/* Rooms Three to Ten: the hall screen as a cinema sign.
   Rest: a poster (the week's verdict against what it still argues), eight door numerals with one word each, and a sign
   strip. A numeral is a door: hover or focus lights it orange and the one small label above the doors gives the room's
   facts. Click walks through: in a room the numerals fold into a corridor rail and the talks fill the field, a page at
   a time (nothing scrolls, nothing is cut off). Clicking the poster opens the week with the poster held in place. */
(() => {
  "use strict";
  const M = window.MENU;
  const PHONE = document.documentElement.classList.contains("phone");
  const RM = matchMedia("(prefers-reduced-motion: reduce)");
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
      else if (k === "class") n.className = v;
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat(Infinity)) if (k != null && k !== false) n.append(k.nodeType ? k : String(k));
    return n;
  }
  const ARROW = "M2 10h13.2l-5.6-5.6 2.8-2.8L22.8 12 12.4 22.4l-2.8-2.8 5.6-5.6H2z";
  const arrow = () => {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("aria-hidden", "true");
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path"); p.setAttribute("d", ARROW); s.append(p);
    return s;
  };

  const menu = $("#menu"), band = $("#band"), panel = $("#panel"), toast = $("#toast"), top = $("#top"), how = $("#how");
  const numerals = $$(".room");

  /* ---------- data helpers ---------- */
  const byId = new Map(M.talks.map((t) => [t.id, t]));
  const TZ = "Europe/Brussels";
  const fWeekday = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "short" });
  const fTime = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const fDate = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });
  const fLong = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });
  const nf = new Intl.NumberFormat("en-GB");
  const dayOf = (t) => fDate.format(new Date(t.start));
  const timeOf = (t) => fTime.format(new Date(t.start));
  const dowOf = (t) => fWeekday.format(new Date(t.start));
  const speakers = (t) => t.speakers.map((s) => s.name).join(", ");
  const roomNo = (t) => (t && (t.room.match(/^Room (\d+)$/) || [])[1]) || null;
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const sentence = (s) => (/[.?!]$/.test(s) ? s : `${s}.`);

  /* each door carries one word, from its most-seen talk's own title or keywords, short enough to sit on one line
     in its column at 20px. If the data changes and the word is no longer in that talk, its first keyword is used. */
  const WORD = {
    3: "Agentic", 4: "Kubernetes", 5: "Sovereignty", 6: "Valhalla",
    7: "Snake", 8: "Monoliths", 9: "Orchestrator", 10: "Detroit",
  };
  function roomWord(r, top) {
    if (!top) return "";
    const w = WORD[r], hay = `${top.title} ${(top.keywords || []).join(" ")}`.toLowerCase();
    if (w && hay.includes(w.toLowerCase())) return w;
    const k = (top.keywords || [])[0] || "";
    return k.charAt(0).toUpperCase() + k.slice(1);
  }

  const ROOMS = numerals.map((b) => b.dataset.room);
  const INFO = {};
  for (const r of ROOMS) {
    const talks = M.talks.filter((t) => roomNo(t) === r);
    const top = talks.filter((t) => t.views != null).sort((a, b) => b.views - a.views)[0] || null;
    INFO[r] = { talks, top, word: roomWord(r, top) };
  }
  const DAYS = [...new Set(M.talks.map(dayOf))].sort();
  const TRENDS = M.recap.trends;

  /* the debate, named: the word each side would put on its banner, taken from its own stance */
  const HEADS = {
    "The harness outweighs the model": ["CLI", "MCP"],
    "Review is the new bottleneck": ["None", "Less", "Human"],
    "Treat coding agents as untrusted code": ["No", "One layer"],
    "AI-found CVEs force faster patching": ["Real fixes", "Noise"],
    "The JVM gets leaner and faster": ["Yes", "Not fully"],
    "Java reaches native code and GPUs": ["Nearly", "Native wins"],
    "Boundaries before services": ["Where needed", "Yes"],
    "From writing code to judging it": ["Let go", "Keep them"],
  };
  /* the counter-voice: each debate's question cut to what fits the poster's right column. The full question is
     printed under it on the verdict page. */
  const ASK = {
    "The harness outweighs the model": "CLI or MCP?",
    "Review is the new bottleneck": "How much review?",
    "Treat coding agents as untrusted code": "Prompt defences?",
    "AI-found CVEs force faster patching": "Safer software?",
    "The JVM gets leaner and faster": "Close the gap?",
    "Java reaches native code and GPUs": "Match native?",
    "Boundaries before services": "Layers worth it?",
    "From writing code to judging it": "Keep the skills?",
  };
  const ask = (tr) => ASK[tr.title] || tr.debate.question;

  /* ---------- sorting ---------- */
  const SORTS = { views: "views", likes: "likes", hearts: "hearts", match: "best match" };
  const state = { view: "rest", room: null, sort: "views", ssort: "match", q: "", day: DAYS[0], week: 0, weekTalks: false, page: 0, lastRoom: null };

  function sortTalks(list, key) {
    const a = list.slice();
    const nil = (v) => (v == null ? 1 : 0);
    if (key === "views") a.sort((x, y) => nil(x.views) - nil(y.views) || (y.views || 0) - (x.views || 0));
    else if (key === "likes") a.sort((x, y) => nil(x.likeRate) - nil(y.likeRate) || (x.thin ? 1 : 0) - (y.thin ? 1 : 0) || (y.likeRate || 0) - (x.likeRate || 0));
    else if (key === "hearts") a.sort((x, y) => (y.hearts || 0) - (x.hearts || 0));
    else if (key === "time") a.sort((x, y) => x.start.localeCompare(y.start) || x.room.localeCompare(y.room, "en", { numeric: true }));
    return a;
  }
  function metric(t, key) {
    if (key === "likes") {
      if (t.likeRate == null) return el("span", {}, "no video yet");
      return el("span", { title: "likes per 100 views" }, el("b", {}, t.likeRate.toFixed(2)), " like rate",
        t.thin ? el("span", { class: "few" }, "few votes") : null);
    }
    if (key === "hearts") return el("span", {}, el("b", {}, nf.format(t.hearts || 0)), " hearts");
    if (key === "room") return el("span", {}, t.room);
    if (t.views == null) return el("span", {}, "no video yet");
    return el("span", {}, el("b", {}, nf.format(t.views)), " views");
  }
  function sortSwitch(keys, current, onPick) {
    return el("div", { class: "sort", role: "group", "aria-label": "Sort talks" }, el("span", { class: "lbl" }, "Sort by"),
      keys.map((k) => el("button", { type: "button", "aria-pressed": String(k === current), on: { click: () => onPick(k) } }, SORTS[k])));
  }

  /* a title with the search words lit: the rest of the title stays in the counter-voice */
  function lit(title, toks) {
    if (!toks || !toks.length) return [title];
    const re = new RegExp(`(${toks.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
    return title.split(re).map((part, i) => (i % 2 ? el("mark", {}, part) : part));
  }
  /* a talk row: day | time | title + people | number. Enter or click walks to it. */
  function trow(t, { day = true, who = speakers(t), key = state.sort, toks = null } = {}) {
    const hl = !!(toks && toks.length);   // while a query is typed every title is in the counter-voice, so only matches light up
    return el("button", { type: "button", class: day ? "trow" : "trow nodow", "data-id": t.id, on: { click: () => openTalk(t.id) } },
      day ? el("span", { class: "dow" }, dowOf(t)) : null,
      el("span", { class: "tm" }, timeOf(t)),
      el("span", {}, el("span", { class: hl ? "t hl" : "t" }, ...(hl ? lit(t.title, toks) : [t.title])), el("span", { class: "who" }, who)),
      el("span", { class: "m" }, metric(t, key)));
  }

  /* ---------- openTalk: the toast, then (in the real page) the walk ---------- */
  let toastTimer = 0;
  function openTalk(id) {
    const t = byId.get(+id);
    if (!t) return;
    toast.textContent = t.seat ? `Walking to ${t.room}` : "Opening the summary";
    toast.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-on"), 2800);
  }
  window.openTalk = openTalk;

  /* ---------- rest: the door words and the poster ---------- */
  numerals.forEach((b) => {
    const I = INFO[b.dataset.room];
    $(".cap", b).textContent = I.word;
    b.setAttribute("aria-label", `Room ${b.dataset.room}, ${plural(I.talks.length, "talk")}. Most seen: ${I.top ? I.top.title : "none yet"}`);
  });

  /* the poster template: the statement in white (cols 1-5) against the open question in the counter-voice
     (cols 6-8), both at the poster size. The size is measured once, from the first verdict at rest; every week page
     keeps it, and a longer verdict only steps down if it would need a third line. */
  const LSIZES = PHONE ? [27, 26, 25, 24, 23, 22] : [52, 50, 48, 46, 44, 42, 40];
  function fitPoster(big, sizes) {
    for (const s of sizes) {
      big.style.setProperty("--lsize", `${s}px`);
      const lh = parseFloat(getComputedStyle(big).lineHeight);
      if (big.getBoundingClientRect().height <= lh * 1.7 + 2) return s;   // trimmed: one line height plus one cap height
    }
    return sizes[sizes.length - 1];
  }
  let posterSize = 0;
  function poster(tr) {
    const big = el("span", { class: "big" }, el("span", { class: "u" }, tr ? sentence(tr.title) : `${TRENDS.length === 8 ? "Eight" : TRENDS.length} verdicts.`));
    band.replaceChildren(el("span", { class: "l" }, big), el("span", { class: "r" }, tr ? el("span", { class: "big q" }, ask(tr)) : null));
    if (!posterSize) { posterSize = fitPoster(big, LSIZES); menu.style.setProperty("--poster", `${posterSize}px`); }
    fitPoster(big, LSIZES.filter((s) => s <= posterSize));
    return big;
  }
  function bandRest() {
    const tr = TRENDS[0];
    band.disabled = false;
    band.setAttribute("aria-label", `What the week agreed: ${sentence(tr.title)} Still argued: ${tr.debate.question} Open the week`);
    poster(tr);
  }
  function topRest() { top.replaceChildren(el("p", { class: "mast" }, "Devoxx Belgium 2026")); }

  /* the one small label: "Pick a room", or the pointed room's facts */
  function showRoom(btn) {
    if (state.view !== "rest") return;
    const r = btn.dataset.room, I = INFO[r];
    if (PHONE || !I.top) { how.replaceChildren(`Room ${r}, ${plural(I.talks.length, "talk")}`); return; }
    how.replaceChildren(`Room ${r}, ${plural(I.talks.length, "talk")}. Most seen: `, el("b", {}, I.top.title), ", ",
      el("span", { class: "v" }, nf.format(I.top.views)), " views");
  }
  function hideRoom() {
    if (state.view !== "rest") return;
    how.replaceChildren("Pick a room");
  }

  /* ---------- the fold: numerals into the corridor rail (FLIP on the digits) ---------- */
  function fold(mutate) {
    const digits = numerals.map((b) => $(".n", b));
    const before = digits.map((d) => d.getBoundingClientRect());
    mutate();
    if (RM.matches) return;
    const after = digits.map((d) => d.getBoundingClientRect());
    digits.forEach((d, i) => {
      const f = before[i], a = after[i];
      if (!a.height || !f.height) return;
      d.style.transition = "none";
      d.style.transform = `translate(${f.left - a.left}px, ${f.top - a.top}px) scale(${f.height / a.height})`;
    });
    void menu.offsetWidth;
    digits.forEach((d) => { d.style.transition = "transform 240ms cubic-bezier(.2,.7,.1,1)"; d.style.transform = ""; });
  }

  /* ---------- views of the second screen ---------- */
  const VIEWS = ["room", "week", "picks", "days", "search"];
  function go(view, arg, { focus = true } = {}) {
    const wasRest = state.view === "rest";
    if (view === "rest") return rest();
    const apply = () => {
      menu.classList.add("is-open");
      VIEWS.forEach((v) => menu.classList.toggle(`v-${v}`, v === view));
      state.view = view;
      state.page = 0;
      if (view === "room") state.room = state.lastRoom = arg;
      if (view === "week") { state.week = arg == null ? 0 : +arg; state.weekTalks = false; }
      numerals.forEach((b) => b.classList.toggle("is-on", view === "room" && b.dataset.room === state.room));
      $$("#sign [data-go]").forEach((b) => b.setAttribute("aria-current", String(b.dataset.go === view)));
      panel.hidden = false;
      render(focus);
    };
    // only a room folds the doors into the rail; the other views cut
    if (wasRest && view === "room") fold(apply); else apply();
    if (!RM.matches && wasRest && view !== "week") { panel.classList.remove("cuts"); void panel.offsetWidth; panel.classList.add("cuts"); }
  }
  function rest() {
    if (state.view === "rest") return;
    const mutate = () => {
      menu.classList.remove("is-open", "wk-talks", ...VIEWS.map((v) => `v-${v}`));
      state.view = "rest";
      panel.hidden = true;
      panel.replaceChildren();
      panel.style.top = "";
      numerals.forEach((b) => b.classList.remove("is-on"));
      $$("#sign [data-go]").forEach((b) => b.removeAttribute("aria-current"));
      topRest();
      bandRest();
      hideRoom();
    };
    if (state.view === "room") fold(mutate); else mutate();
  }

  function render(focus) {
    const v = state.view;
    let first = null;
    if (v === "room") first = renderRoom();
    else if (v === "week") first = renderWeek();
    else if (v === "picks") first = renderPicks();
    else if (v === "days") first = renderDays();
    else if (v === "search") first = renderSearch();
    if (focus && first) first.focus({ preventScroll: true });
  }

  /* a screen's head: a white statement and a muted voice, at the poster size */
  function head(title, voice, sub, right) {
    return el("div", { class: "head" },
      el("div", {}, el("h2", { tabindex: "-1" }, title, voice ? el("span", { class: "q" }, " ", voice) : null), sub ? el("p", { class: "sub" }, sub) : null), right || null);
  }

  /* ---------- paging: fill the page box until it is full, never scroll ---------- */
  function paginate(box, items, make) {
    const starts = [0];
    box.replaceChildren();
    for (let i = 0; i < items.length; i++) {
      const n = make(items[i]);
      box.append(n);
      if (box.scrollHeight > box.clientHeight + 1 && box.childElementCount > 1) {
        starts.push(i);
        box.replaceChildren(n);
      }
    }
    return starts;
  }
  /* a paged list: page box + pager. noun: what the count is of. */
  function pagedList(items, make, { noun = "talks", empty = null } = {}) {
    const box = el("div", { class: "page", role: "list" });
    const pager = el("div", { class: "pager" });
    let starts = [0];
    const show = (p, focusRow) => {
      state.page = Math.max(0, Math.min(starts.length - 1, p));
      const a = starts[state.page], b = starts[state.page + 1] ?? items.length;
      box.replaceChildren(...(items.length ? items.slice(a, b).map(make) : [empty || el("p", { class: "empty" }, "Nothing here.")]));
      pagerBar(pager, !items.length ? "" : items.length === 1 ? `1 ${noun.replace(/s$/, "")}` : b - a === items.length ? `All ${items.length} ${noun}` : `${a + 1}–${b} of ${items.length} ${noun}`, state.page, starts.length, (q, f) => show(q, f));
      if (focusRow) { const rows = $$(".trow, .prow", box); const r = focusRow === "last" ? rows[rows.length - 1] : rows[0]; if (r) r.focus({ preventScroll: true }); }
    };
    box.pageTo = (d, focusRow) => { if (state.page + d >= 0 && state.page + d < starts.length) show(state.page + d, focusRow); };
    // measure without the pager first: when everything fits on one page the pager row is not shown at all
    box.layout = () => {
      pager.hidden = true;
      starts = items.length ? paginate(box, items, make) : [0];
      if (starts.length > 1) { pager.hidden = false; starts = paginate(box, items, make); }
      show(Math.min(state.page, starts.length - 1));
    };
    return { box, pager };
  }
  function pagerBar(pager, at, p, n, onGo) {
    pager.replaceChildren(...[el("span", { class: "at" }, at), n > 1 ? stepBtn("prev", "Previous", p, n, onGo, pager) : null, n > 1 ? stepBtn("next", "Next", p, n, onGo, pager) : null].filter(Boolean));
  }
  function stepBtn(cls, label, p, n, onGo, host) {
    const d = cls === "prev" ? -1 : 1;
    const off = p + d < 0 || p + d >= n;
    return el("button", { type: "button", class: cls, "aria-label": label, "aria-disabled": String(off), on: { click: () => {
      if (off) return;
      const had = menu.contains(document.activeElement);
      onGo(p + d);
      // keep the keyboard where it was: on the same arrow, or on the other one at either end
      const h = host.isConnected ? host : menu;
      const same = $(`.${cls}[aria-disabled=false]`, h) || $(`.prev[aria-disabled=false], .next[aria-disabled=false]`, h);
      if (had && same) same.focus({ preventScroll: true });
    } } },
      cls === "prev" ? [arrow(), el("span", {}, label)] : [el("span", {}, label), arrow()]);
  }

  function renderRoom() {
    const r = state.room, I = INFO[r];
    const sorted = sortTalks(I.talks, state.sort);
    const { box, pager } = pagedList(sorted, (t) => trow(t, { who: companyLine(t) }), { noun: "talks" });
    panel.replaceChildren(
      head(`Room ${r}`, I.word, plural(I.talks.length, "talk"), sortSwitch(["views", "likes", "hearts"], state.sort, (k) => { state.sort = k; state.page = 0; keepFocus(() => render(false), ".sort [aria-pressed=true]"); })),
      box, pager);
    box.layout();
    return $("h2", panel);
  }
  const companyLine = (t) => t.speakers.map((s) => (s.company ? `${s.name}, ${s.company}` : s.name)).join("; ");

  /* the week: the poster stays where it was, at its size; the top line becomes the pager.
     Page 0 is the intro and the index of verdicts; pages 1-8 are one verdict each. */
  function weekTop() {
    const p = state.week, n = TRENDS.length;
    const goWeek = (q) => { state.week = q; state.weekTalks = false; render(false); };
    const tp = el("div", { class: "tp" }, stepBtn("prev", "Previous", p, n + 1, goWeek, top), stepBtn("next", "Next", p, n + 1, goWeek, top));
    const tr = p ? TRENDS[p - 1] : null;
    const at = p === 0 ? `The week, from ${M.talks.length} talks`
      : state.weekTalks ? (PHONE ? `Verdict ${p} of ${n}, its talks` : `Verdict ${p} of ${n}. ${sentence(tr.title)} The talks it rests on`) : `Verdict ${p} of ${n}`;
    top.replaceChildren(el("p", { class: "at" }, at), tp);
  }
  function placePanel() {
    // the talks a verdict rests on are one step further in: the poster gives the field to the evidence and the list
    panel.style.top = state.weekTalks ? `${top.offsetTop + top.offsetHeight + (PHONE ? 22 : 32)}px`
      : `${band.offsetTop + band.offsetHeight + (PHONE ? 22 : 32)}px`;
  }
  function renderWeek() {
    const p = state.week, n = TRENDS.length;
    weekTop();
    menu.classList.toggle("wk-talks", !!(p && state.weekTalks));
    const tr = p ? TRENDS[p - 1] : null;
    poster(tr);
    band.disabled = true;
    band.removeAttribute("aria-label");
    placePanel();
    if (p === 0) {
      panel.replaceChildren(el("h2", { tabindex: "-1", class: "sr" }, "The week"),
        el("div", { class: "page bare" }, el("div", { class: "overview" },
          el("p", { class: "intro" }, M.recap.intro),
          el("div", { class: "index" }, TRENDS.map((t, i) => el("button", { type: "button", on: { click: () => { state.week = i + 1; render(true); } } },
            el("span", { class: "i" }, String(i + 1)), el("span", {}, sentence(t.title)), el("span", { class: "c" }, plural(t.count, "talk"))))))));
      fit($(".overview", panel), PHONE ? ["tight", "tighter"] : ["tight"]);
      return $("h2", panel);
    }
    if (state.weekTalks) {
      const talks = sortTalks(tr.talkIds.map((id) => byId.get(id)).filter(Boolean), "views");
      const { box, pager } = pagedList(talks, (t) => trow(t, { key: "views" }), { noun: "talks" });
      const backAr = arrow(); backAr.style.transform = "scaleX(-1)";
      const back = el("button", { type: "button", class: "vtalks", on: { click: () => { state.weekTalks = false; render(true); } } }, backAr, el("span", {}, "Back to the verdict"));
      panel.replaceChildren(el("h2", { tabindex: "-1", class: "sr" }, `${sentence(tr.title)} The talks it rests on`),
        evidence(tr), box, el("div", { class: "vfoot" }, back, pager));
      pager.style.marginBottom = "0";
      box.layout();
      return $("h2", panel);
    }
    panel.replaceChildren(el("h2", { tabindex: "-1", class: "sr" }, sentence(tr.title)), verdictPage(tr));
    const v = $(".verdict", panel);
    v.classList.add("full");
    fitClasses(v, [["full"], [], ["s1"], ["s1", "s2"], ["s1", "s2", "s3"]]);
    return $("h2", panel);
  }
  function nameTalk(name, side) {
    const has = (t) => t && t.speakers.some((s) => s.name === name);
    const own = side.talkIds.map((id) => byId.get(id)).find(has);
    return own || M.talks.find(has) || null;
  }
  function names(s) {
    return el("div", { class: "names" }, s.who.map((name) => {
      const t = nameTalk(name, s);
      return t ? el("button", { type: "button", class: "name", title: t.title, on: { click: () => openTalk(t.id) } }, name) : el("span", { class: "name" }, name);
    }));
  }
  /* sides on identical neutral rules: the question is argued, so no side gets the accent */
  function verdictPage(tr) {
    const heads = HEADS[tr.title] || [];
    const pick = M.picks.find((p) => p.verdict === tr.title);
    const pt = pick && byId.get(pick.talkId);
    return el("div", { class: "page bare" }, el("article", { class: "verdict" },
      el("p", { class: "consensus" }, tr.consensus),
      el("p", { class: "question" }, tr.debate.question),
      el("div", { class: "sides" }, tr.debate.sides.map((s, i) => el("div", { class: "side" },
        el("span", { class: "w" }, heads[i] || s.stance.split(/[.,]/)[0]),
        el("p", {}, ...firstRest(s.stance)),
        names(s)))),
      el("div", { class: "vfoot" },
        pt ? el("div", { class: "vpick" }, el("span", { class: "k" }, "Watch first"),
          el("button", { type: "button", title: speakers(pt), on: { click: () => openTalk(pt.id) } }, pt.title)) : el("span"),
        el("button", { type: "button", class: "vtalks", on: { click: () => { state.weekTalks = true; state.page = 0; render(true); } } }, el("span", {}, `The ${plural(tr.talkIds.length, "talk")} it rests on`), arrow()))));
  }
  /* the evidence: each side's full stance, over the talks the verdict rests on */
  function evidence(tr) {
    const heads = HEADS[tr.title] || [];
    return el("div", { class: "evid" }, tr.debate.sides.map((s, i) => el("div", { class: "side" },
      el("span", { class: "w" }, heads[i] || s.stance.split(/[.,]/)[0]),
      el("p", {}, ...firstRest(s.stance)))));
  }
  /* a page must fit: try each set of classes in turn and keep the first that does not overflow */
  function fitClasses(v, sets) {
    const box = v.parentElement;
    const all = [...new Set(sets.flat())];
    const over = () => v.scrollHeight > box.clientHeight + 1 || box.scrollHeight > box.clientHeight + 1;
    for (const set of sets) {
      v.classList.remove(...all); v.classList.add(...set);
      if (!over()) return;
    }
  }
  function fit(v, steps) {
    const box = v.parentElement;
    const over = () => v.scrollHeight > box.clientHeight + 1 || box.scrollHeight > box.clientHeight + 1;
    for (const c of steps) { if (!over()) break; v.classList.add(c); }
  }
  /* a stance's first sentence is its claim; the rest is the evidence */
  function firstRest(t) {
    const m = t.match(/^(.+?[.!?])\s+(.*)$/);
    return m ? [el("span", { class: "claim" }, m[1]), el("span", { class: "ev" }, " ", m[2])] : [el("span", { class: "claim" }, t)];
  }

  function renderPicks() {
    const items = M.picks.map((p) => ({ p, t: byId.get(p.talkId) })).filter((x) => x.t);
    const { box, pager } = pagedList(items, ({ p, t }) => el("button", { type: "button", class: "prow", on: { click: () => openTalk(t.id) } },
      el("span", { class: "v" }, `${sentence(p.verdict)} In ${t.room.replace(" ", " ")}`),
      el("span", { class: "t" }, t.title),
      el("span", { class: "why" }, `${speakers(t)}. ${p.why}`)), { noun: "picks" });
    panel.replaceChildren(head("Watch first.", "One per verdict.", `${M.picksNote[0].toUpperCase() + M.picksNote.slice(1)}.`), box, pager);
    box.layout();
    return $("h2", panel);
  }

  function renderDays() {
    const talks = sortTalks(M.talks.filter((t) => dayOf(t) === state.day), "time");
    const days = el("div", { class: "days", role: "group", "aria-label": "Days, Monday 5 to Friday 9 October" }, DAYS.map((d) => {
      const date = new Date(`${d}T12:00:00Z`);
      return el("button", { type: "button", class: "day", "aria-pressed": String(d === state.day), "aria-label": fLong.format(date),
        on: { click: () => { state.day = d; state.page = 0; keepFocus(() => render(false), ".day[aria-pressed=true]"); } } },
        el("span", { class: "d" }, String(+d.slice(8))), el("span", { class: "wd" }, fWeekday.format(date)));
    }));
    const { box, pager } = pagedList(talks, (t) => trow(t, { day: false, key: "room" }), { noun: "talks" });
    panel.replaceChildren(
      el("h2", { tabindex: "-1", class: "sr" }, "By day"),
      days,
      el("p", { class: "daybar" }, `${fLong.format(new Date(`${state.day}T12:00:00Z`))}, Brussels time`),
      box, pager);
    box.layout();
    return $(".day[aria-pressed=true]", panel);
  }

  /* search over title, speakers, company, keywords, themes, tldr, track */
  const HAY = new Map(M.talks.map((t) => [t.id, {
    title: t.title.toLowerCase(),
    who: t.speakers.map((s) => `${s.name} ${s.company || ""}`).join(" ").toLowerCase(),
    tags: [...(t.keywords || []), ...(t.themes || []), t.track || ""].join(" ").toLowerCase(),
    body: (t.tldr || "").toLowerCase(),
  }]));
  const tokens = (q) => q.toLowerCase().split(/\s+/).filter(Boolean);
  function search(q) {
    const toks = tokens(q);
    if (!toks.length) return M.talks.map((t) => ({ t, s: 0 }));
    const out = [];
    for (const t of M.talks) {
      const h = HAY.get(t.id);
      let s = 0, ok = true;
      for (const k of toks) {
        const w = (h.title.includes(k) ? 4 : 0) + (h.who.includes(k) ? 4 : 0) + (h.tags.includes(k) ? 2 : 0) + (h.body.includes(k) ? 1 : 0);
        if (!w) { ok = false; break; }
        s += w;
      }
      if (ok) out.push({ t, s });
    }
    return out;
  }
  function renderSearch() {
    const input = el("input", { class: "q", type: "search", placeholder: `Search ${M.talks.length} talks`, "aria-label": "Search talks, speakers, topics",
      autocomplete: "off", spellcheck: "false" });
    input.value = state.q;
    const bar = el("div", { class: "resbar" });
    const slot = el("div", { class: "slot", style: "display:contents" });
    panel.replaceChildren(el("div", { class: "searchline" }, input, bar), slot);
    const update = (keepPage) => {
      state.q = input.value;
      if (!keepPage) state.page = 0;
      const hits = search(state.q);
      const key = state.ssort === "match" ? (state.q.trim() ? "match" : "views") : state.ssort;
      const talks = key === "match" ? hits.sort((a, b) => b.s - a.s || (b.t.views || 0) - (a.t.views || 0)).map((h) => h.t) : sortTalks(hits.map((h) => h.t), key);
      const mk = key === "match" ? "views" : key;
      const toks = tokens(state.q);
      bar.replaceChildren(
        el("span", {}, state.q.trim() ? `${plural(talks.length, "talk")} match` : `All ${talks.length} talks`),
        sortSwitch(["match", "views", "likes", "hearts"], state.ssort, (k) => { state.ssort = k; update(); $(".sort [aria-pressed=true]", bar).focus(); }));
      const { box, pager } = pagedList(talks, (t) => trow(t, { key: mk, who: `${speakers(t)}, in ${t.room}`, toks }),
        { noun: "talks", empty: el("p", { class: "empty" }, "No talk mentions that. Try a speaker, a company, or a topic like Valhalla.") });
      slot.replaceChildren(box, pager);
      box.layout();
    };
    input.addEventListener("input", () => update());
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { const f = $(".trow", panel); if (f) { e.preventDefault(); f.focus(); } }
    });
    update(true);
    return input;
  }

  function keepFocus(fn, sel) {
    const had = menu.contains(document.activeElement);
    fn();
    if (had) { const n = $(sel, panel); if (n) n.focus({ preventScroll: true }); }
  }

  /* ---------- wiring ---------- */
  numerals.forEach((b) => {
    b.addEventListener("pointerenter", () => showRoom(b));
    b.addEventListener("pointerleave", () => { const f = numerals.find((n) => n === document.activeElement && n.matches(":focus-visible")); if (f) showRoom(f); else hideRoom(); });
    b.addEventListener("focus", () => showRoom(b));
    b.addEventListener("blur", () => setTimeout(() => { if (!numerals.includes(document.activeElement)) hideRoom(); }, 0));
    b.addEventListener("click", () => {
      if (state.view === "room" && state.room === b.dataset.room) return;
      go("room", b.dataset.room);
    });
  });
  $$("#sign [data-go]").forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));
  band.addEventListener("click", () => { if (state.view === "rest") go("week", 1); });
  bandRest();
  // measure the poster again once Archivo has arrived (the first pass may have measured the fallback face)
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => {
    posterSize = 0;
    menu.style.removeProperty("--poster");
    bandRest();
    if (state.view === "week") render(false);
  });

  const rowSel = ".trow, .prow, .index button, .name, .vpick button, .vtalks";
  document.addEventListener("keydown", (e) => {
    const a = document.activeElement;
    const typing = a && a.tagName === "INPUT";
    if (e.key === "Escape") {
      if (state.view !== "rest") { e.preventDefault(); const r = state.lastRoom; rest(); (numerals.find((n) => n.dataset.room === r) || numerals[0]).focus({ preventScroll: true }); }
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    // the numerals answer arrow keys like a grid (the rail when open)
    const ni = numerals.indexOf(a);
    if (ni >= 0 && e.key.startsWith("Arrow")) {
      const open = state.view !== "rest";
      const cols = PHONE ? 2 : 8;   // one row of eight on the screen, two columns on the totem
      const d = open
        ? { ArrowRight: PHONE ? 1 : 0, ArrowLeft: PHONE ? -1 : 0, ArrowDown: PHONE ? 0 : 1, ArrowUp: PHONE ? 0 : -1 }[e.key]
        : { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols < 8 ? cols : 0, ArrowUp: cols < 8 ? -cols : 0 }[e.key];
      if (d) { e.preventDefault(); numerals[(ni + d + numerals.length) % numerals.length].focus(); }
      else if (open && e.key === "ArrowRight") { const f = $(rowSel, panel); if (f) { e.preventDefault(); f.focus(); } }
      return;
    }
    // pages: PageDown / PageUp anywhere; left/right turn the week's verdicts
    const box = $(".page[role=list]", panel);
    if (!typing && state.view !== "rest" && (e.key === "PageDown" || e.key === "PageUp")) {
      e.preventDefault();
      const d = e.key === "PageDown" ? 1 : -1;
      if (state.view === "week" && !state.weekTalks) { const q = state.week + d; if (q >= 0 && q <= TRENDS.length) { state.week = q; render(true); } }
      else if (box) box.pageTo(d, "first");
      return;
    }
    if (!typing && state.view === "week" && !state.weekTalks && (panel.contains(a) || top.contains(a)) && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      const q = state.week + (e.key === "ArrowRight" ? 1 : -1);
      if (q >= 0 && q <= TRENDS.length) { e.preventDefault(); state.week = q; render(!top.contains(a)); }
      return;
    }
    // lists answer up/down, and turn the page at either end
    if (!typing && panel.contains(a) && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      const rows = $$(rowSel, panel).filter((r) => r.offsetParent);
      const i = rows.indexOf(a);
      const down = e.key === "ArrowDown";
      if (i >= 0 || /^H[23]$/.test(a.tagName)) {
        e.preventDefault();
        if (box && i === rows.length - 1 && down) return box.pageTo(1, "first");
        if (box && i === 0 && !down && state.page > 0) return box.pageTo(-1, "last");
        if (i === 0 && !down && state.view === "search") return $(".q", panel).focus();
        const j = i < 0 ? 0 : Math.max(0, Math.min(rows.length - 1, i + (down ? 1 : -1)));
        if (rows[j]) rows[j].focus();
      }
      return;
    }
    if (typing) return;
    // a room number on the keyboard walks you there; "/" searches
    if (/^[3-9]$/.test(e.key) || e.key === "1" || e.key === "0") { e.preventDefault(); go("room", /^[3-9]$/.test(e.key) ? e.key : "10"); return; }
    if (e.key === "/") { e.preventDefault(); go("search"); }
  });
  // clicking the margin (outside the screen) returns to rest
  document.addEventListener("click", (e) => { if ((e.target === document.body || e.target === document.documentElement) && state.view !== "rest") rest(); });
})();
