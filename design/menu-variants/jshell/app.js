(() => {
"use strict";
const M = window.MENU;
const el = (tag, attrs, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) n.append(c.nodeType ? c : document.createTextNode(c));
  return n;
};
const $ = (s) => document.querySelector(s);
const menu = $("#menu"), logEl = $("#log"), pop = $("#pop"), inp = $("#cmd"), mirror = $("#mirror"), chipsEl = $("#chips"), toastEl = $("#toast");
const params = new URLSearchParams(location.search);
if (params.get("shape") === "phone") menu.classList.add("phone");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- data ---------- */
const talks = M.talks, byId = new Map(talks.map((t) => [t.id, t]));
const trends = M.recap.trends;
const pickByVerdict = new Map(M.picks.map((p) => [p.verdict, p]));
const DAYS = [["monday", "Mon", "2026-10-05"], ["tuesday", "Tue", "2026-10-06"], ["wednesday", "Wed", "2026-10-07"], ["thursday", "Thu", "2026-10-08"], ["friday", "Fri", "2026-10-09"]];
const fmtT = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Brussels", hour: "2-digit", minute: "2-digit", hour12: false });
const fmtD = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Brussels" });
const hhmm = (iso) => fmtT.format(new Date(iso));
const dayKey = (iso) => fmtD.format(new Date(iso));
const who = (t) => t.speakers.map((s) => s.name).join(", ");
const whoCo = (t) => t.speakers.map((s) => s.name + (s.company ? " (" + s.company + ")" : "")).join(", ");
const kfmt = (n) => (n >= 10000 ? Math.round(n / 1000) + "k" : n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n));
const plural = (n, w) => n + " " + w + (n === 1 ? "" : "s");

/* ---------- search ---------- */
const norm = (s) => s.toLowerCase();
const tokensOf = (q) => norm(q).split(/[^\p{L}\p{N}+#.]+/u).filter(Boolean);
const idx = talks.map((t) => ({
  t, title: norm(t.title), who: norm(who(t)), co: norm(t.speakers.map((s) => s.company || "").join(" ")),
  kw: norm(t.keywords.join(" ")), th: norm(t.themes.join(" ")), tr: norm(t.track), tl: norm(t.tldr + " " + t.watchIf),
}));
function search(q) {
  const toks = tokensOf(q);
  if (!toks.length) return [];
  const out = [];
  for (const r of idx) {
    let score = 0, ok = true;
    for (const k of toks) {
      let s = 0;
      if (r.title.includes(k)) s += 5 + (new RegExp("(^|[^a-z0-9])" + k.replace(/[.+#]/g, "\\$&")).test(r.title) ? 2 : 0);
      if (r.who.includes(k)) s += 5;
      if (r.co.includes(k)) s += 3;
      if (r.kw.includes(k)) s += 4;
      if (r.th.includes(k)) s += 2;
      if (r.tr.includes(k)) s += 2;
      if (r.tl.includes(k)) s += 1;
      if (!s) { ok = false; break; }
      score += s;
    }
    if (ok) out.push({ t: r.t, score });
  }
  out.sort((a, b) => b.score - a.score || (b.t.views || 0) - (a.t.views || 0));
  return out.map((x) => x.t);
}
function hi(text, toks) {
  if (!toks.length) return text;
  const re = new RegExp("(" + toks.map((k) => k.replace(/[.*+?^${}()|[\]\\#]/g, "\\$&")).join("|") + ")", "ig");
  return text.split(re).map((p, i) => (i % 2 ? el("mark", {}, p) : p));
}
const topics = (() => {
  const c = {};
  talks.forEach((t) => t.themes.forEach((x) => (c[x] = (c[x] || 0) + 1)));
  return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 8);
})();

/* ---------- commands ---------- */
const CMDS = [
  { name: "verdicts", sample: "verdicts()", gloss: "the story in 8 verdicts" },
  { name: "watch", sample: "watch()", gloss: "watch first, one pick per verdict" },
  { name: "search", sample: 'search("")', gloss: "find talks, speakers, tools, topics" },
  { name: "sort", sample: "sort(views)", gloss: "all talks by views, likes or hearts" },
  { name: "programme", sample: "programme(monday)", gloss: "the talks by day, time and room" },
  { name: "debate", sample: "debate(1)", gloss: "one verdict: what they agreed, where they split" },
  { name: "intro", sample: "intro()", gloss: "the conference in a paragraph" },
  { name: "help", sample: "help()", gloss: "list every command" },
  { name: "clear", sample: "clear()", gloss: "empty the screen" },
];
const SORTS = [["views", "most watched"], ["likes", "best liked, ranked only with enough votes"], ["hearts", "most hearted before the talk"]];

function parse(text) {
  const s = text.trim().replace(/;$/, "");
  const m = s.match(/^([A-Za-z_]\w*)\s*(?:\((.*?)\)?)?$/s);
  const known = m && [...CMDS.map((c) => c.name), "opentalk", "program", "schedule", "verdict"].includes(m[1].toLowerCase());
  if (!known) return { cmd: "search", arg: s.replace(/^["']|["']$/g, ""), canon: `search("${s.replace(/"/g, "")}")` };
  let cmd = m[1].toLowerCase(), arg = (m[2] || "").trim().replace(/^["']|["']$/g, "");
  if (cmd === "program" || cmd === "schedule") cmd = "programme";
  if (cmd === "verdict") cmd = "debate";
  if (cmd === "debate") {
    let n = /^\d+$/.test(arg) ? +arg : arg ? trends.findIndex((t) => norm(t.title).includes(norm(arg))) + 1 : 1;
    if (!n || n < 1 || n > trends.length) return { cmd, err: `There is no verdict ${arg || ""}. Pick 1 to ${trends.length}.`, canon: `debate(${arg})`, fix: ["debate(1)", "verdicts()"] };
    return { cmd, n, canon: `debate(${n})` };
  }
  if (cmd === "sort") {
    const a = norm(arg || "views");
    const hit = SORTS.find(([k]) => k.startsWith(a)) || (a.startsWith("like") ? SORTS[1] : a.startsWith("heart") ? SORTS[2] : null);
    if (!hit) return { cmd, err: `Sort by views, likes or hearts, not "${arg}".`, canon: `sort(${arg})`, fix: ["sort(views)", "sort(likes)", "sort(hearts)"] };
    return { cmd, key: hit[0], canon: `sort(${hit[0]})` };
  }
  if (cmd === "programme") {
    const a = norm(arg || "monday");
    const d = DAYS.find(([n, sh, iso]) => n.startsWith(a) || sh.toLowerCase() === a || iso.endsWith("-0" + a));
    if (!d) return { cmd, err: `No day called "${arg}". The programme runs Monday 5 to Friday 9 October.`, canon: `programme(${arg})`, fix: DAYS.map((d) => `programme(${d[0]})`) };
    return { cmd, day: d, canon: `programme(${d[0]})` };
  }
  if (cmd === "search") return { cmd, arg, canon: `search("${arg.replace(/"/g, "")}")` };
  if (cmd === "opentalk") return { cmd, id: +arg, canon: `openTalk(${arg})` };
  return { cmd, canon: cmd + "()" };
}

/* ---------- renderers ---------- */
const cmdSpan = (text) => {
  const sp = el("span", { class: "cmdtxt" });
  sp.append(...hl(text));
  return sp;
};
function hl(str) {
  const out = []; const re = /([A-Za-z_]\w*)(?=\()|("[^"]*"?)|(\b\d+\b)|([()])/g; let last = 0, m;
  while ((m = re.exec(str))) {
    if (m.index > last) out.push(str.slice(last, m.index));
    out.push(el("span", { class: m[1] ? "fn" : m[2] ? "str" : m[3] ? "num" : "pn" }, m[0]));
    last = re.lastIndex;
  }
  if (last < str.length) out.push(str.slice(last));
  return out;
}
const runBtn = (cmd, attrs, ...kids) => el("button", { type: "button", "data-run": cmd, ...attrs }, ...kids);

function sigs(t) {
  return el("div", { class: "sig" },
    el("span", { title: "views: reach" }, el("b", {}, t.views == null ? "none" : kfmt(t.views)), el("i", {}, t.views == null ? "no video" : "views")),
    t.views == null ? el("span", {}, el("b", {}, "none"), el("i", {}, "like rate")) :
      el("span", { class: t.thin ? "thin" : "", title: "likes per 100 views" + (t.thin ? "; under 20 likes, so too few votes to trust" : "") },
        el("b", {}, t.likeRate.toFixed(2)), el("i", {}, t.thin ? "few votes" : "like rate")),
    el("span", { title: "Devoxx app favourites before the talk: interest, not quality" }, el("b", {}, kfmt(t.hearts)), el("i", {}, "hearts")));
}
function talkRow(t, o = {}) {
  const toks = o.toks || [];
  const cmd = `openTalk(${t.id})`;
  return el("button", { type: "button", class: "trow", "data-run": cmd, "aria-label": `${t.title}, ${who(t)}. Open talk` },
    el("span", { class: "tm" }, o.rank ? el("span", { class: "rank" }, o.rank) : null,
      el("div", {}, el("span", { class: "tt" }, hi(t.title, toks)), el("span", { class: "tw" }, hi(whoCo(t), toks)),
        o.tldr ? el("span", { class: "td" }, hi(t.tldr, toks)) : null)),
    o.sig === false ? null : sigs(t),
    el("span", { class: "rm" }, el("span", { class: "room" }, o.when ? `${hhmm(t.start)} ${t.room}` : t.seat ? t.room : "summary"), el("span", { class: "cmdhint" }, cmd)));
}

function rVerdicts(o = {}) {
  const lim = o.limit || trends.length;
  const rows = trends.slice(0, lim).map((tr, i) => {
    const p = pickByVerdict.get(tr.title), pt = p && byId.get(p.talkId);
    return el("div", { class: "vrow" },
      runBtn(`debate(${i + 1})`, { class: "vmain", "aria-label": `Verdict ${i + 1}: ${tr.title}, ${tr.count} talks. Open the debate` },
        el("span", { class: "idx" }, i + 1), el("span", { class: "vt" }, tr.title),
        el("span", { class: "vn" }, el("span", { class: "count" }, plural(tr.count, "talk")), el("span", { class: "cmdhint" }, `debate(${i + 1})`))),
      pt ? runBtn(`openTalk(${pt.id})`, { class: "vpick", title: `Watch first: ${pt.title}. ${p.why}`, "aria-label": `Watch first: ${pt.title}` }, el("span", { class: "play" }), el("span", { class: "ptitle" }, pt.title), el("span", { class: "pword" }, "watch")) : el("span"));
  });
  const wrap = el("div", { class: "vtable" },
    o.limit ? null : el("div", { class: "vhead", "aria-hidden": "true" }, el("span"), el("span", {}, "the verdict"), el("span"), el("span", {}, "watch first")),
    rows);
  return wrap;
}
const firstSentence = (s) => (s.match(/^.*?[.!?](?=\s|$)/) || [s])[0];
function rIntro(full) {
  return full ? el("p", { class: "intro-full" }, M.recap.intro) : null;
}
function rDebate(n, o = {}) {
  const tr = trends[n - 1], d = tr.debate;
  const inSides = new Set(d.sides.flatMap((s) => s.talkIds));
  const rest = tr.talkIds.filter((id) => !inSides.has(id));
  const mini = (id) => { const t = byId.get(id); return t ? runBtn(`openTalk(${id})`, { class: "mini" }, el("span", { class: "t" }, t.title), el("span", { class: "s" }, who(t) + " in " + t.room)) : null; };
  const sides = el("div", { class: "sides" }, d.sides.map((s) => el("div", { class: "side" },
    el("p", { class: "stance" }, s.stance),
    el("div", { class: "who" }, s.who.map((w) => runBtn(`search("${w}")`, { title: `Find talks by ${w}` }, w))),
    s.talkIds.map(mini))));
  return el("div", {},
    el("h2", { class: "dtitle" }, `${n}  ${tr.title}`),
    el("div", { class: "dmeta" }, plural(tr.count, "talk") + " in this verdict"),
    el("p", { class: "agreed" }, el("b", {}, "Everyone agreed. "), tr.consensus),
    el("p", { class: "question" }, el("span", { class: "split" }, "Where they split. "), d.question),
    sides,
    rest.length ? el("div", { class: "sides" }, el("div", { class: "side", style: "grid-column:1/-1;padding-left:0" }, el("p", { class: "stance", style: "color:var(--dim)" }, "Also in this verdict"), rest.map(mini))) : null,
    o.compact ? null : el("details", { class: "full" }, el("summary", {}, "Read the full summary"), el("p", {}, tr.body)),
    o.compact ? null : el("div", { class: "dnav" },
      n > 1 ? runBtn(`debate(${n - 1})`, { class: "tab cmd" }, `debate(${n - 1})`) : null,
      n < trends.length ? runBtn(`debate(${n + 1})`, { class: "tab cmd" }, `debate(${n + 1})`) : null,
      runBtn("verdicts()", { class: "tab cmd" }, "verdicts()")));
}
function rWatch(o = {}) {
  const items = M.picks.slice(0, o.limit || 99).map((p) => {
    const t = byId.get(p.talkId), vi = trends.findIndex((x) => x.title === p.verdict) + 1;
    return el("article", { class: "pick" },
      runBtn(`debate(${vi})`, { class: "pv", title: "Open this verdict" }, p.verdict),
      runBtn(`openTalk(${t.id})`, { class: "pt" }, t.title),
      el("div", { class: "pw" }, whoCo(t) + ", " + t.room),
      el("p", { class: "why" }, p.why), sigs(t));
  });
  return el("div", {}, o.limit ? null : el("p", { class: "msg" }, "One pick per verdict, each with its reason. " + M.picksNote[0].toUpperCase() + M.picksNote.slice(1) + "."), el("div", { class: "picks" }, items));
}
function rTalks(list, o = {}) {
  const shown = list.slice(0, o.limit || 20);
  const box = el("div", {});
  shown.forEach((t, i) => box.append(talkRow(t, { ...o, rank: o.ranked ? i + 1 : null })));
  if (list.length > shown.length && !o.limit) {
    const b = el("button", { type: "button", class: "morebtn" }, `Show ${Math.min(25, list.length - shown.length)} more of ${list.length - shown.length}`);
    b.addEventListener("click", () => {
      const from = box.querySelectorAll(".trow").length, next = list.slice(from, from + 25);
      next.forEach((t, i) => box.insertBefore(talkRow(t, { ...o, rank: o.ranked ? from + i + 1 : null }), b));
      const left = list.length - from - next.length;
      if (left > 0) b.textContent = `Show ${Math.min(25, left)} more of ${left}`; else b.remove();
    });
    box.append(b);
  }
  return box;
}
function rSearch(q, o = {}) {
  const toks = tokensOf(q), res = search(q);
  if (!toks.length) return el("div", {}, el("p", { class: o.compact ? "pv-head" : "msg" }, "Type a topic, a speaker, a company or a tool. Or start from one of these."), topicChips());
  const head = el("p", { class: o.compact ? "pv-head" : "msg" }, el("b", {}, plural(res.length, "talk")), ` match "${q}"`);
  if (!res.length) return el("div", {}, el("p", { class: o.compact ? "pv-head" : "msg" }, `No talk matches "${q}". Try fewer words, or a topic:`), topicChips());
  return el("div", {}, head, rTalks(res, { toks, tldr: true, limit: o.compact ? 4 : 0, sig: true }));
}
function topicChips() {
  return el("div", { class: "topics" }, topics.map(([name, n]) => runBtn(`search("${name}")`, {}, name, el("small", {}, n))));
}
function sortedList(key) {
  let list = talks.filter((t) => t.views != null);
  let skipped = 0;
  if (key === "likes") { const all = list.length; list = list.filter((t) => !t.thin); skipped = all - list.length; }
  const f = { views: (t) => t.views, likes: (t) => t.likeRate, hearts: (t) => t.hearts }[key];
  list.sort((a, b) => f(b) - f(a));
  return { list, skipped };
}
function rSort(key, o = {}) {
  const { list, skipped } = sortedList(key);
  if (o.compact) return el("div", {}, el("p", { class: "pv-head" }, el("b", {}, SORTS.find((s) => s[0] === key)[1]), `, top 4 of ${list.length}`), rTalks(list, { limit: 4, ranked: true }));
  return el("div", {},
    el("div", { class: "tabs" }, SORTS.map(([k]) => runBtn(`sort(${k})`, { class: "tab cmd", "aria-pressed": String(k === key) }, `sort(${k})`))),
    el("p", { class: "legend" }, "views show reach. Like rate is likes per 100 views, and a talk under 20 likes has too few votes to rank. Hearts are Devoxx app favourites before the talk: interest, not quality."
      + (key === "likes" ? ` ${plural(skipped, "talk")} with few votes are left out of this ranking.` : "")),
    rTalks(list, { ranked: true }));
}
function rProgramme(day, o = {}) {
  const list = talks.filter((t) => dayKey(t.start) === day[2]).sort((a, b) => a.start.localeCompare(b.start) || a.room.localeCompare(b.room, undefined, { numeric: true }));
  const slots = new Map();
  list.forEach((t) => { const k = hhmm(t.start); (slots.get(k) || slots.set(k, []).get(k)).push(t); });
  const dnum = +day[2].slice(-2), full = day[0][0].toUpperCase() + day[0].slice(1);
  const tabs = el("div", { class: "tabs" }, DAYS.map((d) => runBtn(`programme(${d[0]})`, { class: "tab", "aria-pressed": String(d[0] === day[0]) }, `${d[1]} ${+d[2].slice(-2)}`)));
  const lim = o.compact ? 4 : 0;
  const body = el("div", {});
  let c = 0;
  for (const [time, ts] of slots) {
    if (lim && c >= lim) break;
    const sl = el("div", { class: "slot" }, el("div", { class: "time" }, time), el("div", {}, ts.map((t) => { c++; return talkRow(t, { sig: false, when: false }); })));
    body.append(sl);
  }
  return el("div", {}, o.compact ? null : tabs,
    el("p", { class: o.compact ? "pv-head" : "msg" }, el("b", {}, `${full} ${dnum} October`), `, ${plural(list.length, "talk")}, times in Brussels`),
    body);
}
function rHelp() {
  return el("div", {}, el("p", { class: "msg" }, "Click any line to run it, or type it. Plain words search."),
    CMDS.map((c) => runBtn(c.sample, { class: "helprow" }, cmdSpan(c.sample), el("span", {}, c.gloss))));
}

/* ---------- transcript ---------- */
let entryCount = 0;
function addEntry(canon, outNode, { err = false, noScroll = false } = {}) {
  const e = el("section", { class: "entry" },
    el("div", { class: "echo" }, el("span", { class: "ps" }, "jshell> "), cmdSpan(canon)),
    el("div", { class: "out" + (err ? " err" : "") }, outNode));
  logEl.append(e);
  const all = logEl.querySelectorAll(".entry");
  if (all.length > 10) all[0].remove();
  entryCount++;
  if (!noScroll) requestAnimationFrame(() => logEl.scrollTo({ top: e.offsetTop - logEl.offsetTop - 4, behavior: reduced ? "auto" : "smooth" }));
  return e;
}
function execute(p, o = {}) {
  hidePop();
  if (p.err) {
    return addEntry(p.canon, el("div", {}, el("p", { class: "msg" }, p.err), el("div", { class: "topics" }, p.fix.map((f) => runBtn(f, {}, cmdSpan(f))))), { err: true });
  }
  switch (p.cmd) {
    case "verdicts": return addEntry(p.canon, el("div", {}, el("p", { class: "lede" }, firstSentence(M.recap.intro), " ", runBtn("intro()", { class: "more" }, "read more")), rVerdicts()));
    case "intro": return addEntry(p.canon, el("div", {}, el("p", { class: "intro-full" }, M.recap.intro), runBtn("verdicts()", { class: "tab cmd" }, "verdicts()")));
    case "debate": return addEntry(p.canon, rDebate(p.n));
    case "watch": return addEntry(p.canon, rWatch());
    case "search": return addEntry(p.canon, rSearch(p.arg));
    case "sort": return addEntry(p.canon, rSort(p.key));
    case "programme": return addEntry(p.canon, rProgramme(p.day));
    case "help": return addEntry(p.canon, rHelp());
    case "clear":
      logEl.querySelectorAll(".entry").forEach((e) => e.remove());
      logEl.append(el("section", { class: "entry" }, el("div", { class: "out" }, el("p", { class: "msg" }, "Screen cleared. Pick a command below, or run "), el("div", { class: "topics" }, runBtn("verdicts()", {}, cmdSpan("verdicts()"))))));
      return;
    case "opentalk":
      if (byId.has(p.id)) window.openTalk(p.id);
      return;
  }
}

/* ---------- toast + openTalk (the real page starts the walk here) ---------- */
let toastTimer;
window.openTalk = function (id) {
  const t = byId.get(id); if (!t) return;
  toastEl.textContent = "";
  toastEl.append(t.seat ? `Walking to ${t.room}, seat ready` : "Opening the summary", el("small", {}, t.title));
  toastEl.classList.add("on");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toastEl.classList.remove("on"), 2800);
};

/* ---------- typing + running ---------- */
let busy = false;
function setInput(v, caret) {
  inp.value = v; renderMirror();
  if (caret != null) inp.setSelectionRange(caret, caret);
}
async function runCmd(text) {
  if (busy) return;
  const p = parse(text);
  hidePop();
  busy = true;
  if (!reduced && !/^openTalk/.test(text)) {
    inp.readOnly = true;
    const step = Math.max(10, Math.min(26, 420 / p.canon.length));
    for (let i = 1; i <= p.canon.length; i++) { setInput(p.canon.slice(0, i)); await new Promise((r) => setTimeout(r, step)); }
    await new Promise((r) => setTimeout(r, 90));
    inp.readOnly = false;
  }
  setInput("");
  busy = false;
  execute(p);
  inp.focus({ preventScroll: true });
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-run]");
  if (!b || !menu.contains(b)) return;
  const c = b.getAttribute("data-run");
  if (c === 'search("")') { hidePop(); setInput('search("")', 8); inp.focus(); update(); return; }
  runCmd(c);
});

/* ---------- completion ---------- */
let cands = [], sel = 0, popMode = null;
function candidates(raw) {
  const v = raw.trim();
  if (!v) return [];
  const out = [];
  const m = v.match(/^([A-Za-z_]\w*)\s*\((.*)$/s);
  const add = (text, gloss) => { if (!out.some((c) => c.text === text)) out.push({ text, gloss }); };
  if (m) {
    const name = m[1].toLowerCase(), arg = m[2].replace(/\)\s*$/, "").trim().replace(/^["']|["']$/g, "");
    const cmd = CMDS.find((c) => c.name === name || c.name.startsWith(name));
    if (!cmd) { add(`search("${v.replace(/"/g, "")}")`, "find talks, speakers, tools, topics"); return out; }
    const a = norm(arg);
    if (cmd.name === "search") add(`search("${arg}")`, a ? "find talks matching these words" : "type what you want to find");
    else if (cmd.name === "debate") trends.forEach((t, i) => { if (!a || String(i + 1).startsWith(a) || norm(t.title).includes(a)) add(`debate(${i + 1})`, t.title); });
    else if (cmd.name === "sort") SORTS.forEach(([k, g]) => { if (k.startsWith(a) || !a) add(`sort(${k})`, g); });
    else if (cmd.name === "programme") DAYS.forEach(([n, sh, iso]) => { if (!a || n.startsWith(a) || sh.toLowerCase() === a) add(`programme(${n})`, `${sh} ${+iso.slice(-2)} October`); });
    else add(cmd.sample, cmd.gloss);
    return out.slice(0, 5);
  }
  if (/^[A-Za-z]+$/.test(v)) {
    CMDS.filter((c) => c.name.startsWith(norm(v))).forEach((c) => add(c.sample, c.gloss));
  }
  add(`search("${v.replace(/"/g, "")}")`, "find talks matching these words");
  return out.slice(0, 5);
}
function previewFor(text) {
  const p = parse(text);
  if (p.err) return { head: null, node: el("p", { class: "pv-head" }, p.err) };
  switch (p.cmd) {
    case "verdicts": return { node: el("div", {}, el("p", { class: "lede" }, firstSentence(M.recap.intro)), rVerdicts({ limit: 4 })) };
    case "debate": return { node: rDebate(p.n, { compact: true }) };
    case "watch": return { node: rWatch({ limit: 3 }) };
    case "search": return { node: rSearch(p.arg, { compact: true }) };
    case "sort": return { node: rSort(p.key, { compact: true }) };
    case "programme": return { node: rProgramme(p.day, { compact: true }) };
    case "intro": return { node: el("p", { class: "intro-full" }, M.recap.intro) };
    case "help": return { node: el("p", { class: "pv-head" }, "Lists every command, each one a click.") };
    case "clear": return { node: el("p", { class: "pv-head" }, "Empties the screen.") };
  }
  return { node: el("p") };
}
function showPop(list, selIdx, mode) {
  popMode = mode; cands = list; sel = selIdx;
  pop.replaceChildren();
  pop.classList.toggle("hover", mode === "hover");
  const candBox = el("div", { class: "cands" });
  list.forEach((c, i) => {
    const row = el("div", { class: "cand", role: "option", "aria-selected": String(i === selIdx), id: "cand" + i }, cmdSpan(c.text), el("span", { class: "gl" }, c.gloss),
      i === selIdx && mode === "typing" ? el("span", { class: "keys" }, el("kbd", {}, "Tab"), " accept  ", el("kbd", {}, "Enter"), " run") : null);
    row.addEventListener("mousedown", (e) => { e.preventDefault(); sel = i; accept(); });
    candBox.append(row);
  });
  const c = list[selIdx];
  const pv = el("div", { class: "pv-body" });
  if (c) pv.append(previewFor(c.text).node);
  pop.append(candBox, pv);
  pop.hidden = false;
  inp.setAttribute("aria-expanded", mode === "typing" ? "true" : "false");
  if (mode === "typing") inp.setAttribute("aria-activedescendant", "cand" + selIdx);
  const dock = $("#dock"), pr = $("#prompt");
  pop.style.bottom = (menu.clientHeight - (dock.offsetTop + pr.offsetTop) + 6) + "px";
}
function hidePop() { pop.hidden = true; popMode = null; cands = []; inp.setAttribute("aria-expanded", "false"); inp.removeAttribute("aria-activedescendant"); renderMirror(); }
function update() {
  renderMirror();
  const v = inp.value;
  if (!v.trim()) { if (popMode === "typing") hidePop(); return; }
  const list = candidates(v);
  if (!list.length) { hidePop(); return; }
  showPop(list, 0, "typing");
  renderMirror();
}
function renderMirror() {
  const v = inp.value;
  const c = popMode === "typing" ? cands[sel] : null;
  mirror.replaceChildren(...hl(v));
  if (c && c.text.toLowerCase().startsWith(v.toLowerCase()) && c.text.length > v.length && inp.selectionStart === v.length) {
    mirror.append(el("span", { class: "ghost" }, c.text.slice(v.length)));
  }
  mirror.scrollLeft = inp.scrollLeft;
}
function accept() {
  const c = cands[sel]; if (!c) return;
  setInput(c.text, c.text.endsWith('")') && c.text.startsWith("search(") && /\(""\)$/.test(c.text) ? c.text.length - 2 : c.text.length);
  update();
}
inp.addEventListener("input", update);
inp.addEventListener("keyup", renderMirror);
inp.addEventListener("click", renderMirror);
inp.addEventListener("keydown", (e) => {
  if (busy) { e.preventDefault(); return; }
  const typing = popMode === "typing" && cands.length;
  if (e.key === "Tab" && !e.shiftKey && typing && inp.value !== cands[sel].text) { e.preventDefault(); accept(); }
  else if (e.key === "Enter") {
    e.preventDefault();
    if (typing) runCmd(cands[sel].text); else if (inp.value.trim()) runCmd(inp.value);
  } else if (e.key === "ArrowDown" && typing) { e.preventDefault(); showPop(cands, (sel + 1) % cands.length, "typing"); renderMirror(); }
  else if (e.key === "ArrowUp" && typing) { e.preventDefault(); showPop(cands, (sel - 1 + cands.length) % cands.length, "typing"); renderMirror(); }
  else if (e.key === "Escape") { setInput(""); hidePop(); }
  else if (e.key === "ArrowRight" && typing && inp.selectionStart === inp.value.length && inp.value !== cands[sel].text) { e.preventDefault(); accept(); }
  else setTimeout(renderMirror, 0);
});
inp.addEventListener("blur", () => { if (popMode === "typing") setTimeout(() => { if (document.activeElement !== inp) hidePop(); }, 120); });

/* ---------- chips (hover or focus previews the result) ---------- */
let hoverTimer;
CMDS.slice(0, 5).forEach((c) => {
  const b = el("button", { type: "button", class: "chip", "data-run": c.sample === 'search("")' ? 'search("")' : c.sample },
    el("code", {}, ...hl(c.sample)), el("span", { class: "gloss" }, { verdicts: "the story", watch: "watch first", search: "find a talk", sort: "by views, likes", programme: "by day" }[c.name]));
  const show = () => { if (document.activeElement === inp && inp.value) return; showPop([{ text: c.sample, gloss: c.gloss }], 0, "hover"); };
  b.addEventListener("pointerenter", () => { clearTimeout(hoverTimer); hoverTimer = setTimeout(show, 280); });
  b.addEventListener("pointerleave", () => { clearTimeout(hoverTimer); if (popMode === "hover") hidePop(); });
  b.addEventListener("focus", () => { if (!busy) show(); });
  b.addEventListener("blur", () => { if (popMode === "hover") hidePop(); });
  chipsEl.append(b);
});
document.addEventListener("keydown", (e) => {
  // typing anywhere goes to the prompt
  if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && document.activeElement !== inp && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { inp.focus(); }
  if (e.key === "Escape" && document.activeElement !== inp) { hidePop(); inp.focus(); }
});

/* ---------- hall toggle ---------- */
const hb = $("#hallbtn");
hb.addEventListener("click", () => { const on = document.body.classList.toggle("hall"); hb.setAttribute("aria-pressed", String(on)); });

/* ---------- boot ---------- */
function boot() {
  if (menu.classList.contains("phone")) {
    inp.placeholder = "type a word to search";
    $("#hallbtn").hidden = true;
    document.querySelector("a.barbtn").textContent = "Text version";
  }
  inp.focus({ preventScroll: true });
  runCmd("verdicts()");
}
boot();
})();
