/* Lightbox: the screen is the search field. At rest the wall cuts slowly between the week's three arguments, each
   with the talk to start with. The field sits in the same place on every screen and the caret only ever lives in it;
   type anywhere and your letters land there. Above it the wall changes its text; below it, the other ways in. */
(() => {
  "use strict";
  const M = window.MENU;
  const $ = (s, r = document) => r.querySelector(s);
  const menu = $("#menu"), q = $("#q"), view = $("#view"), status = $("#status"), toast = $("#toast");
  const where = $(".where"), fmeta = $("#fmeta"), caret = $(".qbox .caret"), mirror = $(".mirror"), slidesEl = $("#slides");
  const phone = document.documentElement.classList.contains("phone");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");

  if (!M || !Array.isArray(M.talks)) { status.textContent = "The talk list did not load. Use the text version."; return; }

  /* ---------- helpers ---------- */
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "class") e.className = v;
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const k of kids.flat()) if (k != null && k !== false) e.append(k);
    return e;
  }
  const byId = new Map(M.talks.map((t) => [t.id, t]));
  const dash = (s) => String(s).replace(/ - /g, " – ");            // an en dash where a title says " - "
  const nb = (s) => String(s).replace(/ /g, "\u00A0");            // a name never breaks across lines
  const names = (t) => t.speakers.map((s) => nb(s.name)).join(", ");
  const firstName = (t) => t.speakers.length > 1 ? `${t.speakers[0].name} + ${t.speakers.length - 1}` : (t.speakers[0]?.name || "");
  const andList = (xs) => xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;
  const fold = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const hay = new Map(M.talks.map((t) => [t.id, fold([
    t.title, t.speakers.map((s) => `${s.name} ${s.company || ""}`).join(" "),
    (t.keywords || []).join(" "), (t.themes || []).join(" "), t.tldr || "", t.track || "",
  ].join(" "))]));
  const num = new Intl.NumberFormat("en-GB");
  const hhmm = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const dayKey = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Brussels", year: "numeric", month: "2-digit", day: "2-digit" });
  const dayShort = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", weekday: "short", day: "numeric" });
  const dayLong = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", weekday: "long", day: "numeric", month: "long" });
  const firstSentence = (s) => (s.match(/^.*?[.!?](?=\s|$)/) || [s])[0];
  const DATES = "Devoxx Belgium, 5–9 Oct 2026";
  const DATES_SHORT = "Devoxx Belgium, 5–9 Oct";      // the totem's foot shares its 292 px with "Text version"

  q.placeholder = `Search ${M.talks.length} talks`;
  q.setAttribute("aria-label", `Search ${M.talks.length} talks by title, speaker, company or topic`);

  /* ---------- "Start with": the talk the argument points to ---------- */
  // A long title with a subtitle shows its main title on the wall (schedule-board convention); the full title is
  // its accessible name.
  const wallTitle = (t) => { const s = dash(t.title), i = s.indexOf(": "); return s.length > 44 && i > 12 ? s.slice(0, i) : s; };
  function startWith(el, pick) {
    const t = pick && byId.get(pick.talkId);
    if (!t) { el.remove(); return; }
    el.replaceChildren(h("span", { class: "sw" }, "Start with"), " ",
      h("button", { type: "button", class: "in", "data-nav": "", "aria-label": `Start with ${dash(t.title)}`, onclick: () => openTalk(t.id) }, wallTitle(t)),
      h("span", { class: "d" }, `${names(t)}, ${t.minutes} min`));
  }
  const pickFor = (title) => M.picks.find((p) => p.verdict === title);

  /* ---------- the marquee: three arguments from MENU.recap.intro, each led by the same line ---------- */
  // Wording: the intro's own clauses ("how to check, review and contain them"; "a runtime that keeps getting leaner
  // and faster"; architecture "argued for clear boundaries") joined to the verdict titles they belong to.
  const ARGS = [
    { trend: "The harness outweighs the model" },    // the first slide is written in index.html
    { trend: "The JVM gets leaner and faster",
      w: ["Devoxx argued about", "the JVM: a runtime", "that keeps getting", "leaner and faster."],
      p: ["Devoxx", "argued about", "the JVM:", "a runtime that", "keeps getting", "leaner and faster."] },
    { trend: "Boundaries before services",
      w: ["Devoxx argued about", "architecture:", "clear boundaries", "before services."],
      p: ["Devoxx", "argued about", "architecture:", "clear boundaries", "before services."] },
  ].filter((a) => M.recap.trends.some((t) => t.title === a.trend));
  // two settings of the same words: .w for the wall (980 wide), .p for the totem; CSS shows one of them
  const lines = (xs, cls) => h("span", { class: cls },
    xs.flatMap((x, i) => (i ? [" ", h("span", {}, x)] : [h("span", {}, x)])));
  const slides = [slidesEl.querySelector(".slide")];
  startWith(slides[0].querySelector(".start"), pickFor(ARGS[0]?.trend));
  for (const a of ARGS.slice(1)) {
    const start = h("p", { class: "start" });
    const s = h("div", { class: "slide", "aria-hidden": "true", inert: true }, h("p", { class: "lead" }, lines(a.w, "w"), lines(a.p, "p")), start);
    startWith(start, pickFor(a.trend));
    slidesEl.append(s);
    slides.push(s);
  }
  const HOLD = 9000;
  let cur = 0, mTimer;
  const held = () => S.mode !== "rest" || document.hidden || slidesEl.matches(":hover") ||
    (menu.contains(document.activeElement) && document.activeElement !== document.body);
  function scheduleCut() { clearTimeout(mTimer); if (!reduce.matches && slides.length > 1) mTimer = setTimeout(cut, HOLD); }
  function cut() {
    if (held()) { scheduleCut(); return; }
    const old = slides[cur], nxt = slides[(cur + 1) % slides.length];
    cur = (cur + 1) % slides.length;
    for (const s of slides) s.classList.remove("wipe-in", "wipe-out");
    old.classList.remove("on"); old.setAttribute("aria-hidden", "true"); old.inert = true;
    nxt.classList.add("on"); nxt.removeAttribute("aria-hidden"); nxt.inert = false;
    void nxt.offsetWidth;
    old.classList.add("wipe-out"); nxt.classList.add("wipe-in");
    setTimeout(() => old.classList.remove("wipe-out"), 1300);
    scheduleCut();
  }
  scheduleCut();
  reduce.addEventListener?.("change", scheduleCut);

  /* ---------- the caret: drawn by us, 2 px, at cap height, the one orange thing ---------- */
  function placeCaret() {
    const v = q.value;
    if (!v) { caret.style.left = "0px"; return; }
    const at = document.activeElement === q && q.selectionStart != null ? q.selectionStart : v.length;
    mirror.textContent = v.slice(0, at);
    const x = mirror.getBoundingClientRect().width - q.scrollLeft;
    caret.style.left = `${Math.max(0, Math.min(q.clientWidth - 2, x + 2))}px`;
  }
  for (const ev of ["input", "keyup", "click", "select", "scroll", "focus", "blur"]) q.addEventListener(ev, () => requestAnimationFrame(placeCaret));
  document.fonts?.ready.then(placeCaret);

  /* ---------- sorting ---------- */
  // 24 talks have no view count yet (views and likes are null): they always sort last and say so.
  const none = (v) => v == null;
  const SORTS = {
    views: { word: "most seen", val: (t) => t.views, show: (t) => (none(t.views) ? "no count yet" : `${num.format(t.views)} views`) },
    likes: { word: "best liked", val: (t) => t.likeRate,
      show: (t) => (none(t.likeRate) ? "no count yet" : t.thin ? "few votes" : `${t.likeRate.toFixed(2)} likes/100 views`) },
    hearts: { word: "most hearts", val: (t) => t.hearts, show: (t) => (none(t.hearts) ? "no hearts yet" : `${num.format(t.hearts)} hearts`) },
  };
  const ORDER = ["views", "likes", "hearts"];
  const S = { mode: "rest", sort: "views", hits: [], active: -1, verdict: 0, day: 0 };

  function sorted(list) {
    const f = SORTS[S.sort].val;
    const tier = (t) => (none(f(t)) ? 2 : S.sort === "likes" && t.thin ? 1 : 0);   // likes: trusted rates first, "few votes" after
    return [...list].sort((a, b) => tier(a) - tier(b) || (f(b) ?? 0) - (f(a) ?? 0));
  }

  /* ---------- the bottom row's slot: your way back (the dates on the phone at rest) ---------- */
  function setSlot(content) { status.replaceChildren(content || (phone && S.mode === "rest" ? DATES_SHORT : "")); }
  setSlot(null);
  const backLink = (label) => h("button", { type: "button", class: "hit back", onclick: back }, label);

  function setMode(mode) {
    S.mode = mode;
    menu.dataset.mode = mode;
    q.setAttribute("aria-expanded", mode === "search" ? "true" : "false");
    if (mode !== "search") { q.removeAttribute("aria-activedescendant"); fmeta.replaceChildren(DATES); }
    const cur = { story: "story", verdict: "story", picks: "picks", days: "days" }[mode];
    for (const b of document.querySelectorAll(".ways [data-go]")) {
      if (b.dataset.go === cur) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    }
    if (mode === "rest") scheduleCut();
  }

  /* ---------- rest ---------- */
  function rest() {
    q.value = "";
    S.hits = []; S.active = -1;
    view.replaceChildren(); view.dataset.kind = "";
    setMode("rest");
    setSlot(null);
    placeCaret();
  }

  /* ---------- search: the letters stay in the field, the talks take the wall ---------- */
  let listEl, moreEl;
  function renderSearch() {
    const raw = q.value;
    const terms = fold(raw).split(/\s+/).filter(Boolean);
    S.hits = sorted(M.talks.filter((t) => terms.every((w) => hay.get(t.id).includes(w))));
    S.active = -1;
    q.removeAttribute("aria-activedescendant");
    if (view.dataset.kind !== "search") {
      listEl = h("ol", { class: "list", id: "results", role: "listbox", "aria-label": "Matching talks" });
      moreEl = h("p", { class: "more d", "aria-hidden": "true" });
      listEl.addEventListener("scroll", () => countMore(listEl, moreEl));
      view.replaceChildren(listEl, moreEl);
      view.dataset.kind = "search";
    }
    setMode("search");
    const n = S.hits.length;
    fmeta.replaceChildren(h("span", { class: "cnt" }, `${n} ${n === 1 ? "talk" : "talks"}, `),
      h("button", { type: "button", class: "hit sort", onclick: cycleSort, "aria-label": `${n} talks, sorted by ${SORTS[S.sort].word}. Change the order` }, SORTS[S.sort].word),
      h("span", { class: "cnt" }, " first"));
    if (!n) {
      listEl.replaceChildren(h("li", { class: "empty" }, h("p", { class: "m" }, `No talk matches “${raw.trim()}”.`),
        h("p", { class: "s" }, "Try a speaker, a company or a topic, like Valhalla, Leyden or MCP.")));
    } else {
      listEl.replaceChildren(...S.hits.map((t, i) => talkRow(t, i, SORTS[S.sort].show(t))));
    }
    listEl.scrollTop = 0;
    fitList(listEl, moreEl);
    setSlot(backLink("Clear search"));
  }
  function talkRow(t, i, metric) {
    return h("li", {
      class: "row", role: "option", id: `r-${t.id}`, "aria-selected": "false",
      onclick: () => openTalk(t.id), onmousemove: () => i !== S.active && setActive(i, false),
    }, h("span", { class: "t m" }, h("span", { class: "x" }, dash(t.title))),
      h("span", { class: "meta d", title: names(t) }, `${firstName(t)}   ${dayShort.format(new Date(t.start))}   ${t.minutes} min   ${metric}`));
  }
  function setActive(i, scroll = true) {
    const rows = listEl ? listEl.querySelectorAll(".row") : [];
    if (!rows.length) return;
    S.active = Math.max(0, Math.min(rows.length - 1, i));
    rows.forEach((r, k) => { r.classList.toggle("on", k === S.active); r.setAttribute("aria-selected", k === S.active ? "true" : "false"); });
    q.setAttribute("aria-activedescendant", rows[S.active].id);
    if (scroll) rows[S.active].scrollIntoView({ block: "nearest" });
  }
  function cycleSort() {
    S.sort = ORDER[(ORDER.indexOf(S.sort) + 1) % ORDER.length];
    renderSearch();
    fmeta.querySelector(".sort").focus();
  }

  // A list stops at the last row that fits whole, so the wall never shows half a title; a line under the last row
  // says how many more wait below, and counts down as you scroll.
  function fitList(el, more) {
    el.style.flex = ""; el.style.height = "";
    const box = el.getBoundingClientRect();
    let end = 0;
    for (const r of el.children) { const b = r.getBoundingClientRect(); if (b.bottom - box.top > box.height + 0.5) break; end = b.bottom - box.top; }
    if (end && end < box.height - 0.5) { el.style.flex = "none"; el.style.height = `${Math.ceil(end)}px`; }
    countMore(el, more);
  }
  function countMore(el, more) {
    if (!more) return;
    const lim = el.getBoundingClientRect().bottom + 0.5;
    const below = [...el.children].filter((r) => r.getBoundingClientRect().bottom > lim).length;
    more.textContent = below ? `${below} more, scroll` : "";
  }

  /* ---------- the story: eight verdicts ---------- */
  function hint(text) { return h("p", { class: "hint s", "aria-live": "polite" }, text); }
  function renderStory(focusIdx) {
    const trends = M.recap.trends;
    const idle = `${trends.length} verdicts from the week. Point at one for what the talks agreed on; open it for what they still argued about.`;
    const note = hint(idle);
    const ol = h("ol", { class: "verdicts" }, trends.map((t, i) => {
      const show = () => note.replaceChildren(t.consensus);
      return h("li", {}, h("button", {
        type: "button", class: "vbtn", "data-nav": "", onclick: () => renderVerdict(i, true),
        onmouseenter: show, onfocus: show, onmouseleave: () => { if (!document.activeElement?.closest?.(".verdicts")) note.replaceChildren(idle); },
      }, h("span", { class: "x m" }, t.title), h("span", { class: "d" }, `${t.count} talks`)));
    }));
    view.replaceChildren(ol, note); view.dataset.kind = "story";
    setMode("story");
    if (phone) fitList(ol, null);
    setSlot(backLink("Back to the start"));
    if (focusIdx != null) ol.querySelectorAll("button")[focusIdx].focus();
  }
  function talkForName(name, ids) {
    const has = (t) => t && t.speakers.some((s) => s.name === name);
    return ids.map((id) => byId.get(id)).find(has) || M.talks.find(has) || null;
  }
  function renderVerdict(i, moveFocus) {
    const all = M.recap.trends, t = all[i];
    S.verdict = i;
    const h2 = h("h2", { tabindex: "-1" }, `${t.title}.`);
    // Each side is a door: its claim opens the side's first talk.
    const sides = h("div", { class: "sides" }, t.debate.sides.map((s) => {
      const tk = byId.get(s.talkIds?.[0]) || talkForName(s.who[0], s.talkIds || []);
      const claim = firstSentence(s.stance);
      const short = claim.length <= 70;
      const text = h("span", { class: "x" }, short ? claim : s.stance);
      const door = tk
        ? h("button", { type: "button", class: short ? "claim m" : "body s", "data-nav": "", "aria-label": `${short ? claim : s.stance} Open ${dash(tk.title)}`, onclick: () => openTalk(tk.id) }, text)
        : h("p", { class: short ? "claim m" : "body s" }, text);
      return h("div", { class: "side" }, door, h("p", { class: "who d" }, andList(s.who.map(nb))));
    }));
    const start = h("p", { class: "start" });
    startWith(start, pickFor(t.title));
    const step = (d) => renderVerdict((i + d + all.length) % all.length, false);
    const pager = h("span", { class: "pager" },
      h("span", {}, `Verdict ${i + 1} of ${all.length}`),
      h("button", { type: "button", class: "hit next", "aria-label": `Next verdict, ${i + 2 > all.length ? 1 : i + 2} of ${all.length}`,
        onclick: () => { step(1); menu.querySelector(".next")?.focus(); } }, "Next"));
    // the pager sits where the field row keeps its context (the dates, the count); on the totem, under the talk
    const art = h("article", { class: "verdict" }, h2, h("p", { class: "qn m" }, t.debate.question), sides,
      h("div", { class: "vfoot" }, start, phone ? pager : null));
    view.replaceChildren(art);
    view.dataset.kind = "verdict";
    setMode("verdict");
    setSlot(backLink("Back to the start"));
    if (!phone) fmeta.replaceChildren(pager);
    // the title steps down only if the argument would not fit under it
    for (const px of [78, 70, 62, 56]) {
      if (phone) break;
      art.style.setProperty("--vL", `${px}px`);
      if (art.scrollHeight <= art.clientHeight + 1) break;
    }
    if (moveFocus) h2.focus();
  }

  /* ---------- watch first ---------- */
  function renderPicks() {
    const idle = `One talk for each of the ${M.recap.trends.length} verdicts. Point at one to see who it is for.`;
    const note = hint(idle);
    const ol = h("ol", { class: "picks" }, M.picks.map((p) => {
      const t = byId.get(p.talkId);
      if (!t) return null;
      const show = () => note.replaceChildren(h("b", {}, `${names(t)}, ${t.minutes} min. `), p.why);
      return h("li", {}, h("button", {
        type: "button", class: "pbtn", "data-nav": "", onclick: () => openTalk(t.id),
        onmouseenter: show, onfocus: show, onmouseleave: () => { if (!document.activeElement?.closest?.(".picks")) note.replaceChildren(idle); },
      }, h("span", { class: "x m" }, dash(t.title))));
    }));
    view.replaceChildren(ol, note); view.dataset.kind = "picks";
    setMode("picks");
    if (phone) fitList(ol, null);
    setSlot(backLink("Back to the start"));
  }

  /* ---------- by day ---------- */
  const DAYS = (() => {
    const m = new Map();
    for (const t of M.talks) {
      const k = dayKey.format(new Date(t.start));
      if (!m.has(k)) m.set(k, { key: k, d: new Date(t.start), talks: [] });
      m.get(k).talks.push(t);
    }
    return [...m.values()].sort((a, b) => a.key.localeCompare(b.key))
      .map((d) => ({ ...d, talks: d.talks.sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, "en", { numeric: true })) }));
  })();
  function renderDays(pick, focusPicked) {
    S.day = pick ?? 0;
    const row = h("div", { class: "days", role: "group", "aria-label": "Days, Brussels time" }, DAYS.map((d, i) =>
      h("button", { type: "button", class: "dbtn hit m", "data-nav": "", "aria-pressed": S.day === i ? "true" : "false",
        "aria-label": `${dayLong.format(d.d)}, ${d.talks.length} talks`, onclick: () => renderDays(i, true) },
        dayShort.format(d.d))));
    const d = DAYS[S.day];
    let slot = "";
    listEl = h("ol", { class: "list", "aria-label": `${dayLong.format(d.d)}, ${d.talks.length} talks` }, d.talks.map((t) => {
      const at = hhmm.format(new Date(t.start)), first = at !== slot; slot = at;
      return h("li", {
        class: "row day", tabindex: "-1", "data-nav": "", onclick: () => openTalk(t.id),
        onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openTalk(t.id); } },
      }, h("span", { class: "h d", "aria-label": at }, first ? at : ""), h("span", { class: "t m" }, h("span", { class: "x" }, dash(t.title))),
        h("span", { class: "who d" }, names(t)));
    }));
    moreEl = h("p", { class: "more d", "aria-hidden": "true" });
    listEl.addEventListener("scroll", () => countMore(listEl, moreEl));
    view.replaceChildren(row, listEl, moreEl); view.dataset.kind = "days";
    setMode("days");
    fitList(listEl, moreEl);
    setSlot(backLink("Back to the start"));
    fmeta.replaceChildren(`${d.talks.length} talks, Brussels time`);
    if (focusPicked) row.querySelectorAll("button")[S.day].focus();
  }

  /* ---------- open a talk: the walk starts here on the real page ---------- */
  let toastTimer;
  function openTalk(id) {
    const t = byId.get(Number(id));
    if (!t) return;
    toast.replaceChildren(t.seat ? `Walking to ${t.room}` : "Opening the summary");
    toast.title = t.title;
    where.classList.add("toasting");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.replaceChildren(); where.classList.remove("toasting"); }, 2800);
  }
  window.openTalk = openTalk;

  /* ---------- back: one level at a time ---------- */
  function back() {
    if (S.mode === "verdict") { renderStory(S.verdict); return; }
    rest();
    q.focus();
  }

  function go(which, byKeyboard) {
    const cur = S.mode;
    if (cur === which) { rest(); q.focus(); return; }
    q.value = ""; placeCaret();
    if (which === "story") { if (cur === "verdict") { renderStory(S.verdict); return; } renderStory(); }
    if (which === "picks") renderPicks();
    if (which === "days") renderDays(0);
    if (byKeyboard) view.querySelector("[data-nav]")?.focus();
  }
  for (const b of document.querySelectorAll(".ways [data-go]")) {
    b.addEventListener("click", (e) => { e.preventDefault(); go(b.dataset.go, e.detail === 0); });
  }

  /* ---------- input ---------- */
  // Like a text editor, the caret holds solid while you type and starts blinking again when you pause.
  let keyedTimer;
  q.addEventListener("input", () => {
    menu.classList.add("keyed"); clearTimeout(keyedTimer); keyedTimer = setTimeout(() => menu.classList.remove("keyed"), 900);
    if (q.value.trim()) renderSearch(); else if (S.mode === "search") rest();
  });
  q.addEventListener("keydown", (e) => {
    if (S.mode !== "search") return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(S.active + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(S.active - 1); }
    else if (e.key === "Enter") { e.preventDefault(); const t = S.hits[Math.max(0, S.active)]; if (t) openTalk(t.id); }
  });

  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const a = document.activeElement;
    if (e.key === "Escape") { e.preventDefault(); if (S.mode === "rest") { q.blur(); return; } back(); return; }
    if (a === q) return;
    const onControl = a && a !== document.body && a.matches("button, a, [tabindex]");
    // Type anywhere: a printable key goes to the field
    if (e.key.length === 1 && !(onControl && e.key === " ")) {
      e.preventDefault();
      q.value = S.mode === "search" ? q.value + e.key : e.key;
      q.focus();
      q.setSelectionRange(q.value.length, q.value.length);
      q.dispatchEvent(new Event("input"));
      return;
    }
    if (e.key === "Backspace" && S.mode === "search") { e.preventDefault(); q.value = q.value.slice(0, -1); q.focus(); q.dispatchEvent(new Event("input")); return; }
    // a verdict pages left and right
    if (S.mode === "verdict" && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
      e.preventDefault();
      const n = M.recap.trends.length;
      renderVerdict((S.verdict + (e.key === "ArrowRight" ? 1 : -1) + n) % n, true);
      return;
    }
    // Up / down walk through whatever list is on the wall
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const items = [...view.querySelectorAll("[data-nav]")];
      if (!items.length) return;
      e.preventDefault();
      const i = items.indexOf(a);
      const n = i < 0 ? 0 : Math.max(0, Math.min(items.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)));
      items[n].focus();
      items[n].scrollIntoView({ block: "nearest" });
    }
  });

  // The screen itself is the field: a click on the paper puts the caret in it; on the margin it also goes back.
  menu.addEventListener("click", (e) => {
    if (e.target.closest("button, a, input, label, .row")) return;
    const margin = e.target === menu || e.target.closest(".chrome") || e.target === $("#stage");
    if (margin && S.mode !== "rest" && S.mode !== "search") rest();
    q.focus();
  });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && S.mode === "rest") scheduleCut(); });
})();
