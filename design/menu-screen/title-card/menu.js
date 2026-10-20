// The Week in Eight Cards. Rest: one poster per verdict, each in its own ink: the verdict in the condensed voice at one
// size, then its debate question as the main door. A row of eight numbered chips in the eight inks is the pager and the
// colour code. The screen turns over every --hold seconds (not with reduced motion; paused while you point at or focus
// it). One step away: the debate (the card shrunk into a header over the positions on one axis), search and programme.
// Every talk that belongs to an argument carries that verdict's chip.
(() => {
  "use strict";
  const M = window.MENU;
  const menu = document.getElementById("menu");
  if (!M) return; // card 1 is in the HTML; without data the screen still reads
  const PHONE = document.documentElement.classList.contains("phone");
  const RM = matchMedia("(prefers-reduced-motion: reduce)");
  const T = M.recap.trends, N = T.length;
  const byId = new Map(M.talks.map((t) => [t.id, t]));
  const pickFor = new Map(M.picks.map((p) => [p.verdict, p]));
  const $ = (id) => document.getElementById(id);
  const S = { i: 0, layer: "card", sort: "views", day: 0, vf: null, argued: false };
  // eight printing inks, one per verdict; bone on each is 5.2:1 or more
  const INKS = ["#B6241C", "#2743B4", "#A4420F", "#1F5C38", "#9A1F5C", "#0B5A6A", "#5A5B14", "#5B2E8C"];

  // the talks of each verdict (its talkIds plus the talks its sides cite), and the verdicts of each talk
  const vTalks = T.map((t) => [...new Set([...t.talkIds, ...t.debate.sides.flatMap((s) => s.talkIds)])].map((id) => byId.get(id)).filter(Boolean));
  const owners = new Map();
  vTalks.forEach((list, i) => list.forEach((t) => owners.set(t.id, [...(owners.get(t.id) || []), i])));

  /* tiny element helper */
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "class") e.className = v;
      else if (k === "style") e.style.cssText = v;
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : String(c));
    return e;
  }

  /* ---------- formatting ---------- */
  const nf = new Intl.NumberFormat("en-GB");
  const tz = "Europe/Brussels";
  const dayOf = new Intl.DateTimeFormat("en-GB", { timeZone: tz, day: "numeric" });
  const timeOf = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  const pad2 = (n) => String(n).padStart(2, "0");
  // titles lose their emoji: the type system is the only picture here
  const clean = (s) => s.replace(/[\p{Extended_Pictographic}\u{FE0F}\u{200D}\u{1F3FB}-\u{1F3FF}]/gu, "")
    .replace(/\s+([)!?:,.])/g, "$1").replace(/\(\s+/g, "(").replace(/\s{2,}/g, " ").trim();
  const andList = (n) => n.length > 1 ? `${n.slice(0, -1).join(", ")} and ${n.at(-1)}` : (n[0] || "");
  const names = (t) => andList(t.speakers.map((s) => s.name)) || t.type;
  const firstSentence = (s) => {
    const m = s.match(/^(.+?[.!?])\s+([\s\S]*)$/);
    return m ? [m[1], m[2]] : [s, ""];
  };
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const hay = new Map(M.talks.map((t) => [t.id, norm([
    t.title, t.speakers.map((s) => `${s.name} ${s.company || ""}`).join(" "),
    (t.keywords || []).join(" "), (t.themes || []).join(" "), t.tldr || "", t.track || "", t.room,
  ].join(" "))]));
  const vHay = T.map((t) => norm([t.title, t.consensus, t.debate.question, ...t.debate.sides.map((s) => s.stance)].join(" ")));

  // the verdict tag: the card number on the card's ink
  function tags(t) {
    const own = owners.get(t.id) || [];
    return h("span", { class: "tags" },
      own.map((i) => h("span", { class: "tag", style: `--tg:${INKS[i]}`, "aria-hidden": "true", title: T[i].title }, pad2(i + 1))),
      own.length ? h("span", { class: "sr" }, `Argued in verdict ${own.map((i) => i + 1).join(" and ")}. `) : null);
  }

  /* ---------- sorting, named for what each number measures ----------
     views = reach; likes per 100 views = approval ("few votes" under 20 likes); hearts = interest before the talk */
  const SORTS = [
    { k: "views", label: "most watched", col: "views", val: (t) => t.views },
    { k: "likes", label: "best liked", col: "likes / 100 views", val: (t) => t.likeRate },
    { k: "hearts", label: "most awaited", col: "hearts before", val: (t) => t.hearts },
  ];
  const sortOf = () => SORTS.find((x) => x.k === S.sort);
  function sortTalks(list) {
    const f = sortOf().val;
    return [...list].sort((a, b) => {
      const va = f(a), vb = f(b);
      if (va == null || vb == null) return (va == null) - (vb == null);
      if (S.sort === "likes" && a.thin !== b.thin) return a.thin ? 1 : -1; // few votes rank after the trusted ones
      return vb - va;
    });
  }
  // the metric; a ▶ in front when the talk has a seat to walk to (else it opens the summary)
  function metric(t, play) {
    const v = sortOf().val(t), p = play ? h("span", { class: "play", "aria-hidden": "true" }, "▶") : null;
    if (v == null) return h("span", { class: "metric" }, p, h("small", {}, "no video yet"));
    if (S.sort === "likes") return h("span", { class: "metric", title: `${t.likes} likes` }, p, v.toFixed(2), t.thin ? h("small", {}, "few votes") : null);
    return h("span", { class: "metric" }, p, nf.format(v));
  }
  function setSort(k) {
    S.sort = k;
    document.querySelectorAll(".sort button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sort === k)));
    document.querySelectorAll(".thm").forEach((e) => { e.textContent = sortOf().col; });
    if (q) fillSearch();
  }
  // "only the argued talks": shared by search and the programme
  const arguedBtn = () => h("button", { type: "button", class: "argued", "aria-pressed": String(S.argued), onclick: () => setArgued(!S.argued) }, "Only the argued talks");
  function setArgued(on) {
    S.argued = on;
    document.querySelectorAll(".argued").forEach((b) => b.setAttribute("aria-pressed", String(on)));
    if (q) fillSearch();
    if (board) fillDay();
  }
  function row(t) {
    return h("li", {}, h("button", { type: "button", class: "row", onclick: (e) => openTalk(t.id, e.currentTarget), "aria-label": `${clean(t.title)}, ${names(t)}, ${t.room}. ${t.seat ? "Watch" : "Summary"}.` },
      tags(t),
      h("span", {}, h("span", { class: "rt" }, clean(t.title)), h("span", { class: "rs" }, `${names(t)}, ${t.room}`)),
      metric(t, t.seat)));
  }

  /* ---------- fitting the verdict: the condensed voice, one size per card, ragged left ----------
     Every way of breaking the verdict into lines is tried at the extra-condensed cut; each gets the biggest single size
     that fits both the height and its longest line. The biggest setting wins (a lone short word on a line costs a little). */
  const box = $("verdictBox"), vbtn = $("verdict");
  const COND = 62;
  const meas = h("span", { "aria-hidden": "true", style: `position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;font:800 100px/1 var(--sans);letter-spacing:-.005em;font-stretch:${COND}%` });
  menu.append(meas);
  const wCache = new Map();
  function widthAt(text) {
    if (!wCache.has(text)) { meas.textContent = text; wCache.set(text, meas.getBoundingClientRect().width); }
    return wCache.get(text);
  }
  function breaks(words, lo, hi) {
    const out = [];
    (function rec(start, acc) {
      if (start === words.length) { if (acc.length >= lo) out.push(acc.slice()); return; }
      if (acc.length >= hi) return;
      for (let e = start + 1; e <= words.length; e++) { acc.push(words.slice(start, e).join(" ")); rec(e, acc); acc.pop(); }
    })(0, []);
    return out;
  }
  const LH = 0.92;
  // a line with descenders pushes the next one down a little, so a g never meets the d below it
  const DROP = 0.1, hasDesc = (l) => /[gjpqy,]/.test(l);
  // lo/hi = line count, D = descender room under the last line (em), max = size cap (px)
  const REST = PHONE ? { lo: 2, hi: 6, D: 0.2, max: 999 } : { lo: 1, hi: 4, D: 0.2, max: 999 };
  const DEB = PHONE ? { lo: 1, hi: 4, D: 0.16, max: 76 } : { lo: 1, hi: 1, D: 0.16, max: 80 };
  function plan(title, W, H, o) {
    const words = title.split(/\s+/);
    let best = null;
    for (const L of breaks(words, Math.min(o.lo, words.length), o.hi)) {
      const em = LH * L.length + L.slice(0, -1).filter(hasDesc).length * DROP + o.D; // block height per px of size
      const s = Math.min(o.max, H / em, ...L.map((l) => W * 100 / widthAt(l)));
      const lone = L.length > 1 && L.some((l) => l.length <= 3) ? 0.92 : 1;
      const score = s * lone * (1 - 0.01 * L.length);
      if (!best || score > best.score) best = { score, s, L };
    }
    return best && { s: Math.floor(best.s * 10) / 10, L: best.L, D: o.D };
  }
  const fitCache = new Map();
  function fitLines(key, title, W, H, o) {
    if (!fitCache.has(key)) fitCache.set(key, plan(title, W, H, o));
    return fitCache.get(key);
  }
  function paint(el, f) {
    el.style.fontSize = f.s + "px";
    el.replaceChildren(...f.L.map((l, k) => h("span", { class: "vl", style: k && hasDesc(f.L[k - 1]) ? `margin-top:${DROP}em` : null }, l)));
  }
  // until Archivo has loaded, card 1 keeps the setting written into the HTML
  let fontsReady = !document.fonts || document.fonts.check("800 100px Archivo");
  const tease = $("tease");
  function fitVerdict(i) {
    if (!fontsReady && i === 0 && !PHONE) return;
    const W = box.clientWidth, cs = getComputedStyle(box);
    const H = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    if (!W || H < 40) return;
    const f = fitLines(`c${i}|${W}|${Math.round(H)}`, T[i].title, W, H, REST);
    if (f) paint(vbtn, f);
  }

  /* ---------- the poster ---------- */
  const card = $("card"), pager = $("pager");
  const chips = [...pager.querySelectorAll(".chip")];
  chips.forEach((d, k) => { d.setAttribute("aria-label", `Verdict ${k + 1}: ${T[k].title}`); d.addEventListener("click", () => cut(k, true)); });
  pager.addEventListener("animationend", () => { if (S.layer === "card" && !RM.matches) cut(S.i + 1); });
  $("sigN").textContent = `${M.talks.length} talks, ${N} verdicts`;
  function renderCard() {
    const t = T[S.i];
    menu.style.setProperty("--ink", INKS[S.i]);
    tease.textContent = t.debate.question;
    chips.forEach((d, k) => { d.setAttribute("aria-current", String(k === S.i)); d.tabIndex = k === S.i ? 0 : -1; });
    vbtn.setAttribute("aria-label", `${t.title}. ${t.debate.question} Open the debate.`);
    fitVerdict(S.i);
  }
  // pause the turn-over while someone points at the poster or has focus in it
  let hovering = false;
  const updPause = () => menu.classList.toggle("paused", hovering || card.contains(document.activeElement) && document.activeElement !== document.body);
  card.addEventListener("pointerenter", () => { hovering = true; updPause(); });
  card.addEventListener("pointerleave", () => { hovering = false; updPause(); });
  card.addEventListener("focusin", updPause);
  card.addEventListener("focusout", () => setTimeout(updPause));
  const syncStill = () => menu.classList.toggle("still", RM.matches);
  RM.addEventListener("change", syncStill); syncStill();

  /* the cut: one black frame (40 ms) like a splice, then the next card in its own ink */
  const splice = $("splice");
  let spliceTimer = 0;
  function cut(to, byUser) {
    to = ((to % N) + N) % N;
    if (to === S.i) return;
    S.i = to;
    if (byUser || S.layer !== "card") $("live").textContent = `${to + 1} of ${N}: ${T[to].title}`;
    if (RM.matches) return render();
    splice.hidden = false;
    clearTimeout(spliceTimer);
    requestAnimationFrame(() => { render(); spliceTimer = setTimeout(() => { splice.hidden = true; }, 40); });
  }
  function render() {
    menu.style.setProperty("--ink", INKS[S.i]);
    if (S.layer === "card") renderCard();
    else if (S.layer === "debate") renderDebate();
    else renderFoot();
    if (S.layer === "card" && chips[S.i] && pager.contains(document.activeElement)) chips[S.i].focus({ preventScroll: true });
  }

  /* ---------- the black foot strip, shared by the dark pages ---------- */
  const foot = $("lfoot");
  const toast = h("p", { class: "toast", role: "status" });
  const chip = (i, attrs) => h("span", { class: "chip", style: `--c:${INKS[i]}`, "aria-hidden": "true", ...attrs }, pad2(i + 1));
  function renderFoot() {
    const L = S.layer;
    const backLabel = L === "debate" ? "Back to the cards" : T[S.i].title;
    const nav = [["debate", PHONE ? "Debate" : "The debate"], ["programme", "Programme"], ["search", "Search"]].map(([k, label]) =>
      h("button", { type: "button", "aria-current": k === L ? "page" : null, onclick: () => show(k) }, label));
    foot.replaceChildren(
      h("button", { type: "button", class: "back", onclick: () => show("card"), title: "Esc", "aria-label": `Back to the cards (Esc)` },
        h("span", { "aria-hidden": "true" }, "←"), chip(S.i), h("span", { class: "blabel" }, backLabel)),
      toast,
      h("nav", { class: "lnav", "aria-label": "Pages" }, nav, h("a", { href: "../../../site/index.html" }, "Text version")));
  }

  /* ---------- the debate: the card shrunk into a header ---------- */
  const debate = $("debate");
  function talkFor(name, side) {
    const own = side.talkIds.map((id) => byId.get(id)).filter(Boolean);
    return own.find((t) => t.speakers.some((s) => s.name === name)) || own[0];
  }
  function whoLine(s) {
    const parts = [];
    s.who.forEach((nm, k) => {
      if (k) parts.push(k === s.who.length - 1 ? " and " : ", ");
      const tk = talkFor(nm, s);
      parts.push(tk ? h("button", { type: "button", onclick: (e) => openTalk(tk.id, e.currentTarget), "aria-label": `${nm}: ${clean(tk.title)}` }, nm) : nm);
    });
    return h("p", { class: "who" }, parts);
  }
  // one statement and one line of evidence per side
  function sideText(stance) {
    const [lead, rest] = firstSentence(stance);
    if (lead.length <= 70) {
      let ev = firstSentence(rest)[0];
      const semi = ev.indexOf("; ");
      if (semi > 40) ev = ev.slice(0, semi) + ".";
      // still long: end it at its first clause after 60 characters (", then …", " because …"), never mid-clause
      if (ev.length > 140) { const m = ev.slice(60).match(/,\s+(?:then|while|because|so)\s|\s+because\s/); if (m) ev = ev.slice(0, 60 + m.index) + "."; }
      return { claim: lead, ev, plain: false };
    }
    // no short claim to set big: split the stance at its first turn ("…: …", "…, and said …")
    const m = stance.match(/^(.{20,110}?)(?::\s|,\s+and said\s+|,\s+and\s+)(.+)$/);
    return m ? { claim: m[1], ev: cap(m[2]), plain: true } : { claim: stance, ev: "", plain: true };
  }
  function renderDebate() {
    const t = T[S.i], d = t.debate, p = pickFor.get(t.title), pt = p && byId.get(p.talkId);
    const total = d.sides.reduce((x, s) => x + s.talkIds.length, 0) || 1;
    // the positions along one axis: each column (and its bar) as wide as its share of the talks
    const sides = d.sides.map((s) => {
      const x = sideText(s.stance), n = s.talkIds.length;
      return h("div", { class: "side" + (x.plain ? " plain" : ""), style: `--w:${(100 * n / total).toFixed(1)}%` },
        h("p", { class: "tally" }, String(n), h("small", {}, n === 1 ? "talk" : "talks")),
        h("p", { class: "stance" }, x.claim), x.ev ? h("p", { class: "because" }, x.ev) : null, whoLine(s));
    });
    const cols = d.sides.map((s) => `minmax(236px, ${Math.max(1, s.talkIds.length)}fr)`).join(" ");
    const title = h("h2", { class: "dverdict", id: "debTitle", tabindex: "-1" }, t.title);
    const n = vTalks[S.i].length;
    debate.replaceChildren(
      h("header", { class: "dcard" },
        h("div", { class: "dhead" }, chip(S.i), title),
        h("div", { class: "dleft" },
          h("p", { class: "dcons" }, t.consensus),
          h("button", { type: "button", class: "door2", onclick: () => show("search", S.i) }, `All ${n} talks of this verdict`)),
        pt ? h("button", { type: "button", class: "door pick", onclick: (e) => openTalk(pt.id, e.currentTarget), "aria-label": `Watch first: ${clean(pt.title)}, ${names(pt)}, ${pt.room}. ${p.why}` },
          h("span", { class: "pk-l" }, "Watch first"),
          h("span", { class: "pk-t" }, clean(pt.title)),
          h("span", { class: "pk-w" }, h("b", {}, `${names(pt)}, ${pt.room}.`), ` ${p.why}`)) : null),
      h("div", { class: "dbody" },
        h("h3", { class: "question" }, d.question),
        h("div", { class: `sides n${d.sides.length}`, style: `grid-template-columns:${cols}` }, sides)));
    // fit the verdict into its header slot (the same voice as the poster, at header height)
    const W = title.clientWidth;
    if (W && !PHONE) { const f = fitLines(`d${S.i}|${W}`, t.title, W, 140, DEB); if (f) paint(title, f); }
    // the totem: the biggest setting (4, 3, then 2 lines) that keeps the header within the screen, so the black zone
    // always shows its top 16 px above the strip as the cue that there is more below
    if (W && PHONE) {
      const head = debate.querySelector(".dcard"), room = debate.clientHeight - 16;
      for (const hi of [4, 3, 2]) {
        const f = fitLines(`d${S.i}|${W}|${hi}`, t.title, W, 170, { ...DEB, hi });
        if (!f) continue;
        paint(title, f);
        if (head.offsetHeight <= room) break;
      }
    }
    renderFoot();
  }

  /* ---------- search ---------- */
  const search = $("search");
  let q, sList, sCount, chipSlot;
  function buildSearch() {
    q = h("input", { class: "q", type: "search", placeholder: `Search ${M.talks.length} talks`, "aria-label": "Search talks, speakers, companies and topics", autocomplete: "off", spellcheck: "false" });
    q.addEventListener("input", fillSearch);
    chipSlot = h("span", { style: "display:contents" });
    sList = h("ol", { class: "scroll s-list", "aria-label": "Results" });
    sCount = h("span", { class: "count", "aria-live": "polite" });
    const sorts = SORTS.map((x) => h("button", { type: "button", "aria-pressed": String(S.sort === x.k), "data-sort": x.k, onclick: () => setSort(x.k) }, x.label));
    search.replaceChildren(
      h("div", { class: "srch-head" },
        h("div", { class: "qrow" }, chipSlot, q),
        h("div", { class: "tools" }, sCount, arguedBtn(),
          h("div", { class: "sort", role: "group", "aria-label": "Sort talks" }, sorts),
          h("span", { class: "thm" }, sortOf().col))),
      sList);
  }
  function related(res, toks) {
    const score = new Map();
    for (const t of res) for (const i of owners.get(t.id) || []) score.set(i, (score.get(i) || 0) + 1);
    if (!score.size) T.forEach((_, i) => { if (toks.every((k) => vHay[i].includes(k))) score.set(i, 1); });
    return [...score].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([i]) => i);
  }
  function fillSearch() {
    const raw = q.value.trim(), toks = norm(raw).split(/\s+/).filter(Boolean);
    const vf = S.vf;
    chipSlot.replaceChildren(vf == null ? "" : h("button", { type: "button", class: "vchip", style: `--tg:${INKS[vf]}`, onclick: () => { S.vf = null; fillSearch(); q.focus(); }, "aria-label": `Showing the talks of verdict ${vf + 1}, ${T[vf].title}. Show all talks.` },
      h("b", {}, pad2(vf + 1)), h("span", {}, T[vf].title), h("b", { "aria-hidden": "true" }, "×")));
    q.placeholder = vf == null ? `Search ${M.talks.length} talks` : "Search its talks";
    let base = vf == null ? M.talks : vTalks[vf];
    if (S.argued) base = base.filter((t) => owners.has(t.id));
    const res = sortTalks(toks.length ? base.filter((t) => toks.every((k) => hay.get(t.id).includes(k))) : base);
    const n = res.length, talksW = n === 1 ? "talk" : "talks";
    sCount.textContent = toks.length ? `${n} ${n === 1 ? "talk matches" : "talks match"}`
      : vf != null ? `${n} ${talksW} in this argument` : S.argued ? `${n} argued talks` : `All ${n} talks`;
    sList.replaceChildren(...res.map((t) => row(t)));
    if (!n) sList.append(h("li", { class: "empty" }, `No talk mentions “${raw}”. Try a speaker, a company or a topic such as Leyden or Valhalla.`));
    const rel = toks.length && vf == null ? related(res, toks) : [];
    if (rel.length) {
      sList.append(h("li", { class: "related" },
        h("h3", {}, "Argued in"),
        h("div", { class: "rel-row" }, rel.map((i) => h("button", { type: "button", class: "rel", style: `--tg:${INKS[i]}`, onclick: () => { S.i = i; show("debate"); } },
          h("b", {}, pad2(i + 1)), h("span", {}, T[i].title))))));
    }
    sList.scrollTop = 0;
  }

  /* ---------- programme: a schedule board, Mon 5 to Fri 9 October, Brussels time ---------- */
  const prog = $("programme");
  const DAYS = [["Mon", 5, "Monday"], ["Tue", 6, "Tuesday"], ["Wed", 7, "Wednesday"], ["Thu", 8, "Thursday"], ["Fri", 9, "Friday"]];
  let board, dayBtns;
  function fillDay() {
    const n = DAYS[S.day][1];
    const talks = M.talks.filter((t) => +dayOf.format(new Date(t.start)) === n && (!S.argued || owners.has(t.id)))
      .sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, "en", { numeric: true }));
    const groups = [];
    for (const t of talks) {
      const tm = timeOf.format(new Date(t.start));
      if (!groups.length || groups.at(-1).tm !== tm) groups.push({ tm, talks: [] });
      groups.at(-1).talks.push(t);
    }
    board.setAttribute("aria-label", `${DAYS[S.day][2]} ${n} October, ${talks.length} talks`);
    board.replaceChildren(...groups.map((g) => h("li", { class: "tg" },
      h("time", {}, g.tm),
      h("div", {}, g.talks.map((t) => h("button", { type: "button", class: "slot", onclick: (e) => openTalk(t.id, e.currentTarget) },
        h("span", { class: "sroom" }, t.room), tags(t), h("span", { class: "st" }, clean(t.title)), h("span", { class: "sw" }, names(t))))))));
    dayBtns.forEach((b, j) => b.setAttribute("aria-pressed", String(j === S.day)));
    board.scrollTop = 0;
  }
  function buildProgramme() {
    dayBtns = DAYS.map(([d, n, full], k) => h("button", { type: "button", "aria-pressed": "false", "aria-label": `${full} ${n} October`, onclick: () => { S.day = k; fillDay(); } }, PHONE ? d : `${d} ${n}`));
    board = h("ol", { class: "scroll board" });
    prog.replaceChildren(
      h("div", { class: "p-head" }, h("div", { class: "days", role: "group", "aria-label": "Day" }, dayBtns),
        h("div", { class: "p-side" }, arguedBtn(), h("span", {}, "Brussels time"))),
      board);
    fillDay();
  }

  /* ---------- switching pages: hard cuts, no tweens ---------- */
  const layers = { card, debate, search, programme: prog };
  function show(layer, vf = null) {
    const from = S.layer;
    S.layer = layer;
    menu.dataset.layer = layer;
    for (const [k, el] of Object.entries(layers)) el.hidden = k !== layer;
    foot.hidden = layer === "card";
    if (layer === "card") { renderCard(); vbtn.focus({ preventScroll: true }); return; }
    if (layer === "debate") { renderDebate(); $("debTitle").focus({ preventScroll: true }); }
    if (layer === "search") {
      if (!q) buildSearch();
      S.vf = vf; q.value = "";
      fillSearch(); q.focus({ preventScroll: true });
    }
    if (layer === "programme") {
      if (!board) buildProgramme();
      dayBtns[S.day].focus({ preventScroll: true });
    }
    if (layer !== "debate") renderFoot();
    if (from === "card") $("live").textContent = "";
  }

  /* ---------- openTalk: the real page starts the walk here. The foot strip fills like the walk; the pages stay. ---------- */
  // The real page starts the walk here. The foot strip turns bone and fills like the walk; what you opened stays inverted.
  let toastTimer = 0, opened = null;
  function openTalk(id, src) {
    const t = byId.get(+id);
    if (!t) return;
    if (S.layer === "card") show("debate");
    if (opened) opened.classList.remove("opening");
    opened = src && src.isConnected ? src : null;
    if (opened) opened.classList.add("opening");
    toast.textContent = t.seat ? `Walking to ${t.room}` : "Opening the summary";
    foot.classList.remove("toasting");
    void foot.offsetWidth; // restart the fill
    foot.classList.add("toasting");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { foot.classList.remove("toasting"); if (opened) opened.classList.remove("opening"); opened = null; }, 2600);
  }
  window.openTalk = openTalk;

  /* ---------- wiring ---------- */
  vbtn.addEventListener("click", () => show("debate"));
  document.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => show(b.dataset.go)));
  // swipe on the totem
  let x0 = null;
  card.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  card.addEventListener("touchend", (e) => {
    if (x0 == null) return;
    const dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) cut(S.i + (dx < 0 ? 1 : -1), true);
  });

  // keys: ←/→ cut (held: a projector running up to speed, 6 cards a second); on the programme they change the day.
  // Enter = debate, Esc = back, typing on the poster = search.
  let lastCut = 0, run = 0;
  document.addEventListener("keydown", (e) => {
    const k = e.key, inField = e.target.matches && e.target.matches("input");
    if (k === "Escape") { if (S.layer !== "card") { e.preventDefault(); show("card"); } return; }
    if (inField) {
      if (k === "ArrowDown") { const f = sList && sList.querySelector("button"); if (f) { e.preventDefault(); f.focus(); } }
      return;
    }
    if ((k === "ArrowLeft" || k === "ArrowRight") && !e.altKey && !e.metaKey) {
      if (S.layer === "programme") {
        e.preventDefault();
        S.day = (S.day + (k === "ArrowRight" ? 1 : DAYS.length - 1)) % DAYS.length;
        fillDay(); dayBtns[S.day].focus({ preventScroll: true });
        return;
      }
      if (S.layer !== "card" && S.layer !== "debate") return;
      e.preventDefault();
      const now = performance.now();
      if (e.repeat) {
        if (RM.matches) return;
        if (now - lastCut < Math.max(1000 / 6, 320 - run * 40)) return;
        run++;
      } else run = 0;
      lastCut = now;
      cut(S.i + (k === "ArrowRight" ? 1 : -1), true);
      return;
    }
    if ((k === "ArrowDown" || k === "ArrowUp") && e.target.closest && e.target.closest("ol")) {
      const all = [...e.target.closest("ol").querySelectorAll("button")];
      const j = all.indexOf(e.target) + (k === "ArrowDown" ? 1 : -1);
      if (j < 0 && S.layer === "search") { e.preventDefault(); q.focus(); return; }
      if (all[j]) { e.preventDefault(); all[j].focus(); all[j].scrollIntoView({ block: "nearest" }); }
      return;
    }
    if (S.layer === "card" && (k === "Enter" || k === " ") && (e.target === document.body || e.target === menu)) {
      e.preventDefault(); show("debate"); return;
    }
    if (S.layer === "card" && k.length === 1 && /[\p{L}\p{N}]/u.test(k) && !e.ctrlKey && !e.metaKey && !e.altKey) {
      show("search"); // the key press lands in the field that now has focus
    }
  });

  renderCard();
  if (document.fonts) {
    Promise.all([document.fonts.load("800 100px Archivo"), document.fonts.ready]).then(() => {
      fontsReady = true; wCache.clear(); fitCache.clear();
      if (S.layer === "card") fitVerdict(S.i);
      else if (S.layer === "debate") renderDebate();
    });
  }
})();
