/* Shadow Strings: who holds the strings.
   One lit panel of the hall's curtain. A single lamp behind the cloth casts every shadow. The agent is a cut-leather
   marionette; its eight strings are the eight verdicts, and each string ends in one tag on the bar: its number on the
   knob and its name on the plate above it. The visitor's hand holds the bar. Plain JS, canvas 2D. */
(() => {
"use strict";
const M = window.MENU || { recap: { intro: "", trends: [] }, picks: [], talks: [] };
const doc = document.documentElement;
const phone = doc.classList.contains("phone");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const W = phone ? 340 : 980, H = phone ? 690 : 613;
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const menu = $("#menu"), canvas = $("#cloth"), ctx = canvas.getContext("2d");
const dpr = Math.min(2, window.devicePixelRatio || 1);
canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); ctx.scale(dpr, dpr);
const panel = $("#panel"), scroll = $("#scroll"), tag = $("#tag"), band = $("#band"), toastEl = $("#toast"), q = $("#q"), closeBtn = $("#close");
const pegs = $$(".peg");

// ------------------------------------------------------------------ data
const T = M.recap.trends, talks = M.talks, byId = new Map(talks.map(t => [t.id, t]));
// one family of warm gels for the agent verdicts and the people ones, one cool pair for the Java platform (5, 6)
const GELS = ["#D9482B", "#E39A12", "#C23A58", "#B5681E", "#2F7CB8", "#1E8E86", "#A8402E", "#D47A2E"];
pegs.forEach((p, i) => p.style.setProperty("--c", GELS[i]));
const pickFor = i => M.picks.find(p => p.verdict === T[i].title) || M.picks[i];
const speakers = t => t.speakers.map(s => s.name).join(", ");
const fmtN = n => n >= 10000 ? Math.round(n / 1000) + "k" : n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
const timeBx = iso => new Date(iso).toLocaleTimeString("en-GB", { timeZone: "Europe/Brussels", hour: "2-digit", minute: "2-digit" });
const dayBx = iso => new Date(iso).toLocaleDateString("en-CA", { timeZone: "Europe/Brussels" });
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const DAYS = [["2026-10-05", "Mon 5"], ["2026-10-06", "Tue 6"], ["2026-10-07", "Wed 7"], ["2026-10-08", "Thu 8"], ["2026-10-09", "Fri 9"]];
const SORTS = [["views", "most seen"], ["likeRate", "best liked"], ["hearts", "most hearts"]];
let sortKey = "views", day = "2026-10-05";

function sorted(list) {
  const a = list.slice();
  if (sortKey === "views") a.sort((x, y) => (y.views ?? -1) - (x.views ?? -1));
  else if (sortKey === "likeRate") a.sort((x, y) => {
    const kx = x.views == null ? 2 : x.thin ? 1 : 0, ky = y.views == null ? 2 : y.thin ? 1 : 0;   // thin never ranks alone
    return kx - ky || (y.likeRate ?? 0) - (x.likeRate ?? 0);
  });
  else a.sort((x, y) => (y.hearts ?? 0) - (x.hearts ?? 0));
  return a;
}
// the signal's unit is said once, above the list; a row carries its number and only the flags that qualify it
function signal(t) {
  if (sortKey === "hearts") return `<b>${t.hearts ?? 0}</b>${t.views == null ? `<i>no video</i>` : ""}`;
  if (t.views == null) return `<b>no video</b><i>summary only</i>`;
  if (sortKey === "views") return `<b>${fmtN(t.views)}</b>`;
  return `<b>${t.likeRate}</b>${t.thin ? `<i class="flag">few votes</i>` : ""}`;
}
const UNIT = { views: "views on YouTube", likeRate: "likes per 100 views; <b>few votes</b> (under 20 likes) listed last", hearts: "hearts: favourites in the Devoxx app before the talk" };
const row = t => `<li><button type="button" class="talk" data-id="${t.id}"><b>${esc(t.title)}</b><small>${esc(speakers(t))} · ${esc(t.room)} · ${t.minutes} min</small><span class="sig">${signal(t)}</span></button></li>`;
const sortHtml = (lead = "") => `<div class="chips" role="group" aria-label="Sort the talks">${lead ? `<span class="lead">${lead}</span>` : ""}${SORTS.map(([k, l]) => `<button type="button" data-sort="${k}" aria-pressed="${k === sortKey}">${l}</button>`).join("")}</div>` +
  `<p class="note">${UNIT[sortKey]}</p>`;
const stance = s => { const m = /^(.{0,90}?[.!?])\s+([\s\S]*)$/.exec(s); return m ? `<b>${esc(m[1])}</b> ${esc(m[2])}` : esc(s); };
function talkOf(name, side) {
  const last = name.split(" ").pop().toLowerCase();
  const id = side.talkIds.find(id => (byId.get(id)?.speakers || []).some(s => s.name.toLowerCase().includes(last)));
  return id ?? side.talkIds[0];
}
const pickHtml = (t, lbl = "") => `<button type="button" class="pick" data-id="${t.id}">${lbl ? `<span class="lbl">${lbl}</span>` : ""}<b>${esc(t.title)}</b><small>${esc(speakers(t))} · <i>${t.minutes} min</i> · ${esc(t.room)}</small></button>`;
const dot = c => `<span class="dot" style="--c:${c}"></span>`;
const med = i => `<span class="med" style="--c:${GELS[i]}" aria-hidden="true">${i + 1}</span>`;   // the same number medallion as on the bar
const toVerdict = `<button type="button" class="sign sm light" data-go="verdict">◂ the verdict</button>`;
// long lists scroll inside the panel; a soft fade at the bottom says there is more
const list = (cls, inner) => `<div class="scroller"><ol class="list ${cls}">${inner}</ol></div>`;

// a verdict is three screens: the verdict (consensus, watch first, the debate's question), the debate, its talks
function verdictHtml(i, sub) {
  const v = T[i], p = pickFor(i), pt = byId.get(p.talkId), c = GELS[i];
  const n = v.talkIds.filter(id => byId.has(id)).length;
  const toTalks = `<button type="button" class="sign sm" data-go="talks">${n} key talks ▸</button>`;
  if (sub === "debate") return `<div class="head"><p class="eyebrow">${dot(c)}Verdict ${i + 1} · the debate</p><span class="navs">${toVerdict}${toTalks}</span></div>
    <h2 class="q">${esc(v.debate.question)}</h2>
    <div class="scroller"><div class="duo sides">${v.debate.sides.map(s => `<div class="side" style="--c:${c}"><p>${stance(s.stance)}</p><div class="who">${s.who.map(n => `<button type="button" data-id="${talkOf(n, s)}">${esc(n)}</button>`).join("")}</div></div>`).join("")}</div></div>`;
  if (sub === "talks") {
    const l = sorted(v.talkIds.map(id => byId.get(id)).filter(Boolean));
    return `<div class="head"><h2 class="title xs">${dot(c)}${esc(v.title)}</h2>${toVerdict}</div>
    ${sortHtml(`${n} key talks`)}${list("", l.map(row).join(""))}`;
  }
  return `<div class="head"><p class="eyebrow">${dot(c)}Verdict ${i + 1} of 8 · from ${v.count} talks</p>${toTalks}</div>
  <h2 class="title">${esc(v.title)}</h2>
  <p class="consensus">${esc(v.consensus)}</p>
  <div class="duo">${pickHtml(pt, "Watch first")}
  <button type="button" class="dsign" data-go="debate"><span class="lbl">The debate <span class="arr">▸</span></span><span class="dq">${esc(v.debate.question)}</span><span class="dw">${v.debate.sides.map(s => s.who.map(n => esc(n.split(" ").pop())).join(", ")).join(" <i>vs</i> ")}</span></button></div>`;
}
function picksHtml() {
  return `<div class="head"><p class="eyebrow">Watch first · eight talks to start with</p></div>
  ${list("picks", T.map((v, i) => { const p = pickFor(i), t = byId.get(p.talkId); return `<li data-v="${i}"><button type="button" class="pk" data-id="${t.id}" aria-label="${esc(t.title)}, by ${esc(speakers(t))}. Verdict ${i + 1}: ${esc(v.title)}. ${esc(p.why)}">${med(i)}<b>${esc(t.title)}</b><span class="why">${esc(p.why)}</span></button></li>`; }).join(""))}`;
}
function daysHtml() {
  const l = (day === "all" ? talks.slice() : talks.filter(t => dayBx(t.start) === day)).sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0) || a.room.localeCompare(b.room, "en", { numeric: true }));
  const label = day === "all" ? "All 205 talks" : (DAYS.find(d => d[0] === day) || [])[1] + " October";
  return `<div class="head"><p class="eyebrow">Programme · Brussels time</p><a class="sign sm light linkcard" href="../../../site/index.html">Text version</a></div>
  <div class="chips" role="group" aria-label="Day">${DAYS.map(([k, l]) => `<button type="button" data-day="${k}" aria-pressed="${k === day}">${l}</button>`).join("")}<button type="button" data-day="all" aria-pressed="${day === "all"}">all</button></div>
  <h2 class="title xs count">${label} · ${l.length} talks</h2>
  ${list("", l.map(t => `<li><button type="button" class="talk timed" data-id="${t.id}"><span class="time">${day === "all" ? (DAYS.find(d => d[0] === dayBx(t.start)) || ["", ""])[1].slice(0, 3) + " " : ""}${timeBx(t.start)}</span><b>${esc(t.title)}</b><small>${esc(speakers(t))} · ${esc(t.room)}</small></button></li>`).join(""))}`;
}
function searchHtml(qs) {
  const words = qs.toLowerCase().split(/\s+/).filter(Boolean);
  const head = `<div class="head"><p class="eyebrow">Search · 205 talks</p></div>`;
  if (!words.length) return `${head}<h2 class="title sm">Type a title, a speaker, a company or a topic</h2><p class="empty">Results print here as you type. Or pull a string on the bar for one of the eight verdicts.</p>`;
  const hay = t => [t.title, speakers(t), t.speakers.map(s => s.company).join(" "), (t.keywords || []).join(" "), (t.themes || []).join(" "), t.tldr, t.track].join(" ").toLowerCase();
  const res = sorted(talks.filter(t => { const h = hay(t); return words.every(w => h.includes(w)); }));
  if (!res.length) return `${head}<h2 class="title sm">Nothing for “${esc(qs)}”</h2><p class="empty">Try a speaker's surname, a topic like <b>Valhalla</b> or <b>MCP</b>, or open the <b>Programme</b> for a day's talks.</p>`;
  return `<h2 class="title xs count">${res.length} talk${res.length > 1 ? "s" : ""} for “${esc(qs)}”</h2>${sortHtml()}${list("", res.map(row).join(""))}`;
}

// ------------------------------------------------------------------ views (the right side of the cloth)
let view = null, opener = null, toastTimer = 0, restoring = false;   // restoring: focus is being handed back by close(), so the search field must not reopen itself
function render() {
  if (!view) return;
  scroll.innerHTML = view.kind === "verdict" ? verdictHtml(view.i, view.sub) : view.kind === "picks" ? picksHtml() : view.kind === "days" ? daysHtml() : searchHtml(view.q || "");
  for (const sc of scroll.querySelectorAll(".scroller")) { sc.addEventListener("scroll", () => cue(sc), { passive: true }); cue(sc); }
  pullFor();
}
// the fade at the foot of a list shows only while there is more below
function cue(sc) { sc.classList.toggle("more", sc.scrollHeight - sc.clientHeight - sc.scrollTop > 4); sc.classList.toggle("less", sc.scrollTop > 4); }
// which string the open view holds up: the verdict's own
function pullFor() {
  const on = view?.kind === "verdict" ? [view.i] : [];
  for (const s of strings) s.target = on.includes(s.i) ? 1 : 0;
  pegs.forEach((p, i) => p.classList.toggle("on", on.includes(i)));
  wake();
}
const baseTilt = () => view && !phone ? LAY.openTilt : LAY.bar.tilt;
function open(kind, opts = {}) {
  const was = view;
  stopAttract();
  view = { kind, ...opts };
  menu.dataset.mode = "open"; menu.dataset.view = kind;
  panel.hidden = false; closeBtn.hidden = false;
  render();
  $("#btnPicks").classList.toggle("on", kind === "picks");
  $("#btnDays").classList.toggle("on", kind === "days");
  if (kind === "verdict" && lit === opts.i) tag.hidden = true;
  lamp.tx = LAY.lampOpen[0]; lamp.ty = LAY.lampOpen[1];
  bar.shiftTarget = phone ? 0 : LAY.barShift; bar.tiltTarget = baseTilt();
  if (!was) opener = opener || document.activeElement;
  wake();
}
function close() {
  if (!view) return;
  view = null; menu.dataset.mode = "rest"; delete menu.dataset.view;
  panel.hidden = true; closeBtn.hidden = true; scroll.innerHTML = "";
  $("#btnPicks").classList.remove("on"); $("#btnDays").classList.remove("on");
  for (const s of strings) s.target = 0;
  pegs.forEach(p => p.classList.remove("on"));
  lamp.tx = LAY.lampRest[0]; lamp.ty = LAY.lampRest[1];
  bar.shiftTarget = 0; bar.tiltTarget = baseTilt();
  tag.hidden = true;
  if (opener && document.contains(opener)) { restoring = true; opener.focus({ preventScroll: true }); restoring = false; }
  opener = null;
  showBand(lit);
  wake();
}
function pull(i, from) { opener = from || opener; open("verdict", { i, sub: "verdict" }); }
function toast(msg) {
  toastEl.textContent = msg; toastEl.classList.add("show");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3200);
}
window.openTalk = id => { const t = byId.get(+id); if (!t) return; toast(t.seat ? `Walking to ${t.room}` : "Opening the summary"); };

panel.addEventListener("click", e => {
  const b = e.target.closest("button, a"); if (!b) return;
  if (b.dataset.id) window.openTalk(b.dataset.id);
  else if (b.dataset.sort) { sortKey = b.dataset.sort; render(); refocus(`[data-sort="${sortKey}"]`); }
  else if (b.dataset.day) { day = b.dataset.day; render(); refocus(`[data-day="${day}"]`); }
  else if (b.dataset.go) { view.sub = b.dataset.go; render(); scroll.focus({ preventScroll: true }); }
});
// in Watch first, the pick under the pointer or the focus lights its own string on the bar
const pickLit = e => { const li = e.target.closest?.("li[data-v]"); if (li) setLit(+li.dataset.v); };
panel.addEventListener("pointerover", pickLit); panel.addEventListener("focusin", pickLit);
panel.addEventListener("pointerleave", () => { if (view?.kind === "picks") setLit(-1); });
function refocus(sel) { const el = scroll.querySelector(sel); if (el) el.focus({ preventScroll: true }); }
closeBtn.addEventListener("click", close);
$("#btnPicks").addEventListener("click", e => { if (view?.kind === "picks") close(); else { opener = e.currentTarget; open("picks"); } });
$("#btnDays").addEventListener("click", e => { if (view?.kind === "days") close(); else { opener = e.currentTarget; open("days"); } });
$("#slot").addEventListener("submit", e => e.preventDefault());
q.addEventListener("input", () => { opener = q; open("search", { q: q.value }); });
q.addEventListener("focus", () => { if (restoring) return; if (!view || view.kind !== "search") { opener = q; open("search", { q: q.value }); } });
q.addEventListener("blur", () => {   // an empty search closes when the focus leaves it, unless it went into the panel or to "let go"
  if (view?.kind === "search" && !q.value.trim()) setTimeout(() => { const a = document.activeElement; if (a !== q && a !== closeBtn && !panel.contains(a) && view?.kind === "search" && !q.value.trim()) close(); }, 120);
});

document.addEventListener("keydown", e => {
  const inField = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
  if (e.key === "Escape") {   // let go; from the search field it also leaves the field, so the number keys work again at once
    if (inField) { q.value = ""; opener = null; close(); q.blur(); } else close();
    return;
  }
  if (inField || e.metaKey || e.ctrlKey || e.altKey) return;
  if (/^[1-8]$/.test(e.key)) { e.preventDefault(); pull(+e.key - 1, pegs[+e.key - 1]); pegs[+e.key - 1].focus({ preventScroll: true }); }
  else if (e.key === "w" || e.key === "W") { e.preventDefault(); $("#btnPicks").click(); }
  else if (e.key === "d" || e.key === "D") { e.preventDefault(); $("#btnDays").click(); }
  else if (e.key === "/") { e.preventDefault(); q.focus(); }
  else if (e.target.closest?.(".scroller") && /^(Arrow|Page|Home|End)/.test(e.key)) return;   // inside a list these scroll it
  else if (panel.contains(e.target) && e.key.startsWith("Arrow")) return;
  else if (view && (e.key === "PageDown" || e.key === "PageUp")) {   // from a chip, the bar or a card: scroll the open list
    const sc = scroll.querySelector(".scroller"); if (sc) { e.preventDefault(); sc.scrollBy({ top: (e.key === "PageDown" ? 1 : -1) * sc.clientHeight * 0.85 }); }
  }
  else if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); bar.tiltTarget = clamp(bar.tiltTarget + (e.key === "ArrowLeft" ? -0.08 : 0.08), -LIM.tilt, LIM.tilt); hand.toBar = true; hand.keyAt = performance.now(); wake(); }
  else if (e.key === "ArrowUp" || e.key === "ArrowDown") { e.preventDefault(); bar.dyTarget = clamp(bar.dyTarget + (e.key === "ArrowUp" ? -8 : 8), -LIM.lift, LIM.drop); hand.toBar = true; hand.keyAt = performance.now(); wake(); }
});

// ------------------------------------------------------------------ layout per shape
// pegs: [tier, position along that tier from -1 to 1]. The laptop bar holds all eight in order; the phone control is
// a real marionette cross: the main bar holds the head and shoulder strings (3-6), the wide crossbar below it the
// elbows and hands (1, 2 left; 7, 8 right), so no string ever runs across another knob.
const LAY = phone ? {
  lampRest: [205, 330], lampOpen: [170, 220], lampR: 560, barShift: 0, openTilt: -0.03,
  bar: { cx: 170, cy: 84, half: 1, tilt: -0.02, tiers: [{ half: 72, dy: 0, cap: 18 }, { half: 136, dy: 50, cap: 14 }],
    pegs: [[1, -1], [1, -0.632], [0, -1], [0, -1 / 3], [0, 1 / 3], [0, 1], [1, 0.632], [1, 1]] },
  fig: { s: 0.225, neck: [174, 214] }, hand: 0.19, pleat: 34,
} : {
  lampRest: [660, 380], lampOpen: [812, 340], lampR: 1040, barShift: -74, openTilt: -0.08, openHalf: 0.68,
  bar: { cx: 300, cy: 156, half: 1, tilt: 0, tiers: [{ half: 214, dy: 0, cap: 18 }], pegs: [0, 1, 2, 3, 4, 5, 6, 7].map(i => [0, -1 + 2 * i / 7]) },
  fig: { s: 0.32, neck: [300, 296] }, hand: 0.25, pleat: 46,
};
// how far the visitor may take the bar: far enough to swing the puppet hard, never far enough to fold it over itself,
// and (on the laptop) never so steep that the two rows of name plates run into each other
const LIM = phone ? { gx: [-60, 60], gy: [-30, 20], tilt: 0.22, lift: 20, drop: 16, swing: 30, rise: 26, speed: 6 } : { gx: [-110, 150], gy: [-22, 24], tilt: 0.1, lift: 16, drop: 20, swing: 44, rise: 34, speed: 8 };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lamp = { x: LAY.lampRest[0], y: LAY.lampRest[1], tx: LAY.lampRest[0], ty: LAY.lampRest[1] };
const bar = { cx: LAY.bar.cx, cy: LAY.bar.cy, half: 1, tilt: LAY.bar.tilt, tiltTarget: LAY.bar.tilt, dy: 0, dyTarget: 0, shift: 0, shiftTarget: 0, gx: 0, gy: 0, gxT: 0, gyT: 0 };
const pointer = { x: -999, y: -999, in: false };
const hand = { x: LAY.bar.cx, y: LAY.bar.cy, pose: "open", toBar: true, lean: 0, alpha: 1, keyAt: -9999 };

// one lamp, one rule: a point at depth d (0 = pressed on the cloth) casts a shadow scaled by k = 1/(1-d) about the lamp
const project = (p, d) => { const k = 1 / (1 - d); return { x: k * p.x + (1 - k) * lamp.x, y: k * p.y + (1 - k) * lamp.y, k }; };

// ------------------------------------------------------------------ silhouettes (Codex-generated leather, sliced; see LOG.md)
// every part lies flat on the cloth (a few thousandths of depth, no blur): a softened far arm read as a ghost limb.
// Both shins use the same piece so both feet point the way the figure faces.
const PARTS = {
  head: { f: "p-head.webp", a: [111.5, 275.5], b: [111.5, 475.5], d: 0.006 },
  torso: { f: "p-torso.webp", a: [153, 45], b: [153, 390], d: 0 },
  hips: { f: "p-hips.webp", a: [44.5, 29.5], b: [44.5, 229.5], d: 0.003 },
  armA: { f: "p-armA.webp", a: [64, 26], b: [98.5, 255.5], d: 0.008 },
  armB: { f: "p-armB.webp", a: [48.5, 26], b: [25, 255.5], d: 0.008 },
  foreA: { f: "p-foreA.webp", a: [122, 26], b: [95, 200], d: 0.01 },
  foreB: { f: "p-foreB.webp", a: [35, 26], b: [60, 200], d: 0.01 },
  thighA: { f: "p-thighA.webp", a: [31, 26], b: [89.5, 289], d: 0.006 },
  thighB: { f: "p-thighB.webp", a: [91.5, 26], b: [68, 290], d: 0.006 },
  shinA: { f: "p-shinB.webp", a: [49, 26], b: [70, 290], d: 0.008 },
  shinB: { f: "p-shinB.webp", a: [49, 26], b: [70, 290], d: 0.008 },
  open: { f: "hand-open.webp", a: [220, 814] },
  grip: { f: "hand-grip.webp", a: [281.5, 544] },
};
const hold = $("#hold");
let pending = 0;
const loaded = {};
for (const [k, p] of Object.entries(PARTS)) {
  if (loaded[p.f]) { loaded[p.f].push(p); continue; }
  loaded[p.f] = [p];
  const im = new Image(); im.decoding = "async"; pending++;
  im.onload = () => { for (const q of loaded[p.f]) q.img = im; pending--; wake(); };
  im.onerror = () => { pending--; wake(); };
  im.src = "assets/parts/" + p.f; hold.appendChild(im);
}
const vlen = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);

// ------------------------------------------------------------------ the rig
// The torso is a rigid triangle (neck N, hip centre HC, right shoulder SB); every other torso point (left shoulder,
// hips, the two head-string eyelets) is derived from it. Limbs are bones with hard angle limits. Strings are ropes.
// Strings run, left to right, to: left hand, left elbow, left shoulder, back of the head, front of the head, right
// shoulder, right elbow, right hand. The joint limits keep the hands outside the elbows and the elbows outside the
// shoulders, so the attachments always keep the order of their pegs and the fan cannot cross itself.
const S = LAY.fig.s, N0 = LAY.fig.neck;
const LOC = {                                    // sheet units, torso frame: neck pivot at the origin, y down
  N: [0, 0], HC: [0, 345], SB: [93, 28], SA: [-93, 28], TA: [-60, 345], TB: [60, 345], HEAD: [10, -200], HIPS: [-85, 235],
  HEADL: [-40, -238], HEADR: [40, -238], SAe: [-114, 12], SBe: [114, 12],   // string eyelets: the crown, the shoulder tips
};
const ang = (dx, dy) => Math.atan2(dx, dy);      // 0 = straight down, + = towards the right of the screen
const wrap = a => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const clampAng = (a, lo, hi) => {                // to the nearer limit, the way round the joint actually turns
  a = wrap(a); if (a >= lo && a <= hi) return a;
  return Math.abs(wrap(a - lo)) < Math.abs(wrap(a - hi)) ? lo : hi;
};
const BL = k => vlen(PARTS[k].a, PARTS[k].b) * S;
// joint ranges, measured from the torso's own downward axis (left limbs negative = outwards, legs + = forwards)
const CHAINS = [
  { root: "SA", j: "elbowA", e: "handA", l1: BL("armA"), l2: BL("foreA"), r1: [-1.95, -0.36], r2: [-2.25, -0.32], bend: [-1.1, 0.45], rest: [-0.62, -1.02] },
  { root: "SB", j: "elbowB", e: "handB", l1: BL("armB"), l2: BL("foreB"), r1: [0.36, 1.95], r2: [0.32, 2.25], bend: [-0.45, 1.1], rest: [0.62, 1.02] },
  { root: "TA", j: "kneeA", e: "footA", l1: BL("thighA"), l2: BL("shinA"), r1: [-0.32, 0.55], r2: [-0.5, 0.55], bend: [-1.0, 0], rest: [-0.06, -0.08] },
  { root: "TB", j: "kneeB", e: "footB", l1: BL("thighB"), l2: BL("shinB"), r1: [-0.32, 0.55], r2: [-0.5, 0.55], bend: [-1.0, 0], rest: [0.07, 0.05] },
];
const TILT = 0.18;                                // the torso never leans further than this from upright
const nodes = {};
const put = (k, x, y) => { nodes[k] = { k, x, y, px: x, py: y }; };
put("N", N0[0], N0[1]); put("HC", N0[0] + LOC.HC[0] * S, N0[1] + LOC.HC[1] * S); put("SB", N0[0] + LOC.SB[0] * S, N0[1] + LOC.SB[1] * S);
const bary = (p) => { const c = p[0] / 93, b = (p[1] - 28 * c) / 345; return [1 - b - c, b, c]; };
const DERIVED = {}; for (const k of ["SA", "TA", "TB", "HEAD", "HIPS", "HEADL", "HEADR", "SAe", "SBe"]) DERIVED[k] = bary(LOC[k]);
const pos = k => {
  if (nodes[k]) return nodes[k];
  const [a, b, c] = DERIVED[k], n = nodes.N, h = nodes.HC, s = nodes.SB;
  return { x: a * n.x + b * h.x + c * s.x, y: a * n.y + b * h.y + c * s.y };
};
// the rest pose: arms held out and a little down, legs hanging straight
for (const ch of CHAINS) {
  const R = pos(ch.root), a1 = ch.rest[0], a2 = ch.rest[1];
  const J = { x: R.x + ch.l1 * Math.sin(a1), y: R.y + ch.l1 * Math.cos(a1) };
  put(ch.j, J.x, J.y); put(ch.e, J.x + ch.l2 * Math.sin(a2), J.y + ch.l2 * Math.cos(a2));
}
function nudge(k, dx, dy, f = 1) {
  if (nodes[k]) { nodes[k].x += dx * f; nodes[k].y += dy * f; return; }
  const w = DERIVED[k], norm = w[0] * w[0] + w[1] * w[1] + w[2] * w[2];
  nodes.N.x += dx * f * w[0] / norm; nodes.N.y += dy * f * w[0] / norm;
  nodes.HC.x += dx * f * w[1] / norm; nodes.HC.y += dy * f * w[1] / norm;
  nodes.SB.x += dx * f * w[2] / norm; nodes.SB.y += dy * f * w[2] / norm;
}
const tri = [["N", "HC"], ["N", "SB"], ["HC", "SB"]].map(([a, b]) => [a, b, vlen(LOC[a], LOC[b]) * S]);
const ATTACH = ["handA", "elbowA", "SAe", "HEADL", "HEADR", "SBe", "elbowB", "handB"];
const TIED = { SAe: "SA", SBe: "SB" };   // a shoulder eyelet sits on its own shoulder joint
// how much a pull shortens each string: a hand or elbow rises clearly, a shoulder or the head lifts the whole figure a little
const PULL = [104, 76, 30, 20, 20, 30, 76, 104];
const strings = ATTACH.map((k, i) => ({ i, k, len: 0, pull: 0, target: 0 }));

function pegPos(i) {
  const [tier, t] = LAY.bar.pegs[i], tr = LAY.bar.tiers[tier];
  const c = Math.cos(bar.tilt), s = Math.sin(bar.tilt), half = tr.half * bar.half;
  const cx = bar.cx + bar.shift + bar.gx, cy = bar.cy + bar.dy + bar.gy + tr.dy;
  return { x: cx + t * half * c, y: cy + t * half * s };
}
function barEnds(tier = 0) {
  const tr = LAY.bar.tiers[tier], c = Math.cos(bar.tilt), s = Math.sin(bar.tilt), half = tr.half * bar.half + tr.cap;
  const cx = bar.cx + bar.shift + bar.gx, cy = bar.cy + bar.dy + bar.gy + tr.dy;
  return [{ x: cx - half * c, y: cy - half * s }, { x: cx + half * c, y: cy + half * s }, { x: cx, y: cy }];
}
for (const s of strings) { const p = pegPos(s.i), a = pos(s.k); s.len = Math.hypot(p.x - a.x, p.y - a.y); }

const relax = (ka, kb, len, wa, wb) => {
  const A = pos(ka), B = pos(kb), dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 1e-6, f = (d - len) / d;
  if (wa) nudge(ka, dx * f, dy * f, wa);
  if (wb) nudge(kb, -dx * f, -dy * f, wb);
};
// move a node to where the joint allows, carrying its velocity along (so a limit stops a limb without kicking it)
const place = (n, x, y) => { n.px += x - n.x; n.py += y - n.y; n.x = x; n.y = y; };
function limits() {
  const n = nodes.N, h = nodes.HC, s = nodes.SB;
  // the torso stays near upright
  const a0 = ang(h.x - n.x, h.y - n.y), a1 = clamp(wrap(a0), -TILT, TILT);
  if (a1 !== a0) {
    const r = a0 - a1, c = Math.cos(r), sn = Math.sin(r);   // turn HC and SB about N back by (a0 - a1)
    for (const p of [h, s]) { const dx = p.x - n.x, dy = p.y - n.y; place(p, n.x + dx * c - dy * sn, n.y + dx * sn + dy * c); }
  }
  const base = ang(h.x - n.x, h.y - n.y);
  // and stays one rigid piece: three distances alone would let it fold over into its mirror image
  const dn = { x: Math.sin(base), y: Math.cos(base) }, rt = { x: Math.cos(base), y: -Math.sin(base) };
  const at = k => ({ x: n.x + (LOC[k][0] * rt.x + LOC[k][1] * dn.x) * S, y: n.y + (LOC[k][0] * rt.y + LOC[k][1] * dn.y) * S });
  { const p = at("HC"); place(h, p.x, p.y); } { const p = at("SB"); place(s, p.x, p.y); }
  for (const ch of CHAINS) {
    const R = pos(ch.root), J = nodes[ch.j], E = nodes[ch.e];
    const r1 = clampAng(ang(J.x - R.x, J.y - R.y) - base, ch.r1[0], ch.r1[1]);
    place(J, R.x + ch.l1 * Math.sin(base + r1), R.y + ch.l1 * Math.cos(base + r1));
    const bend = clampAng(ang(E.x - J.x, E.y - J.y) - base - r1, ch.bend[0], ch.bend[1]);
    const r2 = clamp(r1 + bend, ch.r2[0], ch.r2[1]);
    place(E, J.x + ch.l2 * Math.sin(base + r2), J.y + ch.l2 * Math.cos(base + r2));
  }
}
let energy = 1;
function step() {
  const g = 0.3, damp = 0.958;   // leather on cloth: it swings and bounces, but settles within a second or two
  energy = 0;
  for (const n of Object.values(nodes)) {
    const vx = (n.x - n.px) * damp, vy = (n.y - n.py) * damp;
    n.px = n.x; n.py = n.y; n.x += vx; n.y += vy + g;
    energy = Math.max(energy, Math.abs(vx) + Math.abs(vy));
  }
  for (let it = 0; it < 8; it++) {
    for (const [a, b, len] of tri) relax(a, b, len, 0.5, 0.5);
    for (const ch of CHAINS) { relax(ch.root, ch.j, ch.l1, 0.2, 0.8); relax(ch.j, ch.e, ch.l2, 0.5, 0.5); }
    for (const s of strings) {
      const P = pegPos(s.i), A = pos(s.k), dx = P.x - A.x, dy = P.y - A.y, d = Math.hypot(dx, dy);
      const len = Math.max(12, s.len - PULL[s.i] * s.pull);
      if (d > len) nudge(s.k, dx * (d - len) / d, dy * (d - len) / d, 1);
    }
    for (const n of Object.values(nodes)) { if (n.y > H - 14) n.y = H - 14; }   // the cloth's lower edge is a floor
  }
  cone();
  limits();
}
// the puppet hangs in a cone under the bar: it may swing and bounce, but it can never be flung up over the bar or so
// far aside that its strings sweep across each other. Hitting the cone's edge soaks up most of the throw (a soft stop).
let REST0 = null;
function cone() {
  const c = barEnds(0)[2], n = nodes.N;
  if (!REST0) return;
  const ox = n.x - (c.x + REST0.x), oy = n.y - (c.y + REST0.y);
  const dx = clamp(ox, -LIM.swing, LIM.swing) - ox, dy = Math.max(oy, -LIM.rise) - oy;
  const all = Object.values(nodes);
  if (dx || dy) for (const p of all) { const vx = p.x - p.px, vy = p.y - p.py; p.x += dx; p.y += dy; p.px = p.x - vx * (dx ? 0.35 : 1); p.py = p.y - vy * (dy ? 0.35 : 1); }
  for (const p of all) {   // and no part ever moves faster than a hand can throw it
    const vx = p.x - p.px, vy = p.y - p.py, v = Math.hypot(vx, vy);
    if (v > LIM.speed) { p.px = p.x - vx * LIM.speed / v; p.py = p.y - vy * LIM.speed / v; }
  }
}
function settle(n = 240) { for (let i = 0; i < n; i++) { step(); for (const nd of Object.values(nodes)) { nd.px += (nd.x - nd.px) * 0.5; nd.py += (nd.y - nd.py) * 0.5; } } }
settle();
{ const c = barEnds(0)[2]; REST0 = { x: nodes.N.x - c.x, y: nodes.N.y - c.y }; }

// ------------------------------------------------------------------ the tangle meter: every frame, are any two strings
// crossing, or does a string cut across a limb it is not tied to? The worst since load is kept on #menu[data-rig]
// ("clean" or "tangled") so a scripted drag can prove the toy never tangles.
const rig = window.__rig = { cross: 0, wrap: 0, maxCross: 0, maxWrap: 0, frames: 0, worst: "" };
const BONES = [["SA", "elbowA"], ["elbowA", "handA"], ["SB", "elbowB"], ["elbowB", "handB"], ["TA", "kneeA"], ["kneeA", "footA"], ["TB", "kneeB"], ["kneeB", "footB"], ["SA", "SB"], ["N", "HC"]];
function segX(a, b, c, d) {   // proper crossing of segments ab and cd (touching at an end does not count)
  const o = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  const d1 = o(c, d, a), d2 = o(c, d, b), d3 = o(a, b, c), d4 = o(a, b, d);
  return ((d1 > 1e-6 && d2 < -1e-6) || (d1 < -1e-6 && d2 > 1e-6)) && ((d3 > 1e-6 && d4 < -1e-6) || (d3 < -1e-6 && d4 > 1e-6));
}
function meter(segs) {
  let cross = 0, wr = 0, worst = "";
  for (let i = 0; i < 8; i++) for (let j = i + 1; j < 8; j++) if (segX(segs[i][0], segs[i][1], segs[j][0], segs[j][1])) { cross++; worst = `strings ${i + 1}/${j + 1}`; }
  for (let i = 0; i < 8; i++) {
    const k = TIED[ATTACH[i]] || ATTACH[i];
    for (const [a, b] of BONES) {
      if (a === k || b === k) continue;
      // trim the string's last few pixels: it is tied there, on the limb's own edge
      const [P, A] = segs[i], L = Math.hypot(A.x - P.x, A.y - P.y) || 1, A2 = { x: A.x - (A.x - P.x) * 6 / L, y: A.y - (A.y - P.y) * 6 / L };
      if (segX(P, A2, pos(a), pos(b))) { wr++; worst = `string ${i + 1} over ${a}-${b}`; }
    }
  }
  rig.cross = cross; rig.wrap = wr; rig.frames++;
  if ((cross || wr) && (rig.log ||= []).length < 40) rig.log.push({ worst, cross, wr, gx: Math.round(bar.gx), gy: Math.round(bar.gy), tilt: +bar.tilt.toFixed(2), N: [Math.round(nodes.N.x), Math.round(nodes.N.y)], base: +ang(nodes.HC.x - nodes.N.x, nodes.HC.y - nodes.N.y).toFixed(2), segs: segs.map(([P, A]) => [Math.round(P.x), Math.round(P.y), Math.round(A.x), Math.round(A.y)]).join(" ") });
  if (cross > rig.maxCross || wr > rig.maxWrap) rig.worst = worst;
  rig.maxCross = Math.max(rig.maxCross, cross); rig.maxWrap = Math.max(rig.maxWrap, wr);
  const state = rig.maxCross || rig.maxWrap ? "tangled" : "clean";
  if (menu.dataset.rig !== state) menu.dataset.rig = state;
}

// ------------------------------------------------------------------ the cloth: lamp, pleats, weave (static bake)
const weave = document.createElement("canvas"); weave.width = W; weave.height = H;
{
  const c = weave.getContext("2d"), id = c.createImageData(W, H), d = id.data, P = LAY.pleat;
  let seed = 7;
  const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const ph = (x / P) * Math.PI * 2;
    const pleat = 0.045 * Math.sin(ph) + 0.018 * Math.sin(2 * ph + 1.1) + 0.012 * Math.sin(ph * 0.5 + y * 0.004);
    const grain = (rnd() - 0.5) * 0.05 + ((x * 7 + y * 13) % 3 === 0 ? 0.012 : -0.006);
    const v = Math.round(128 + 128 * (pleat + grain));
    const o = (y * W + x) * 4; d[o] = d[o + 1] = d[o + 2] = clamp(v, 0, 255); d[o + 3] = 255;
  }
  c.putImageData(id, 0, 0);
}
const clothC = document.createElement("canvas"); clothC.width = W; clothC.height = H;
let baked = { x: NaN, y: NaN };
function bakeCloth() {   // lamp, flame halo, the cool shade at the top, the weave: redone only when the lamp moves
  const c = clothC.getContext("2d"), R = LAY.lampR;
  const g = c.createRadialGradient(lamp.x, lamp.y, 0, lamp.x, lamp.y, R);
  g.addColorStop(0, "#FFF8EA"); g.addColorStop(0.1, "#FFF3DA"); g.addColorStop(0.3, "#F8E7C8"); g.addColorStop(0.52, "#EFE3CF");
  g.addColorStop(0.78, "#B8A4A6"); g.addColorStop(1, "#4A3B4C");
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  const halo = c.createRadialGradient(lamp.x, lamp.y, R * 0.14, lamp.x, lamp.y, R * 0.42);
  halo.addColorStop(0, "rgba(255,208,138,0)"); halo.addColorStop(0.45, "rgba(255,208,138,0.32)"); halo.addColorStop(1, "rgba(255,208,138,0)");
  c.fillStyle = halo; c.fillRect(0, 0, W, H);
  const top = c.createLinearGradient(0, 0, 0, H * 0.5);
  top.addColorStop(0, "rgba(74,59,76,0.5)"); top.addColorStop(0.55, "rgba(74,59,76,0.12)"); top.addColorStop(1, "rgba(74,59,76,0)");
  c.fillStyle = top; c.fillRect(0, 0, W, H);
  c.globalCompositeOperation = "overlay"; c.drawImage(weave, 0, 0); c.globalCompositeOperation = "source-over";
  baked = { x: lamp.x, y: lamp.y };
}
function drawCloth(t) {
  if (Math.abs(lamp.x - baked.x) > 0.3 || Math.abs(lamp.y - baked.y) > 0.3) bakeCloth();
  ctx.drawImage(clothC, 0, 0);
  if (reduced) return;
  const breath = 0.028 * Math.sin(t / 1900) + 0.01 * Math.sin(t / 610 + 1);   // the flame breathes: a slow brightening and dimming of the hotspot
  const R = LAY.lampR * 0.5, a = Math.abs(breath) * 2.4;
  const b = ctx.createRadialGradient(lamp.x, lamp.y, 0, lamp.x, lamp.y, R);
  const col = breath > 0 ? "255,243,218" : "74,59,76";
  b.addColorStop(0, `rgba(${col},${a.toFixed(3)})`); b.addColorStop(1, `rgba(${col},0)`);
  ctx.fillStyle = b; ctx.fillRect(0, 0, W, H);
}

// ------------------------------------------------------------------ drawing the puppet's shadow
function partTransform(part, A, B, d) {
  const pa = project(A, d), pb = project(B, d), m = PARTS[part];
  const a = Math.atan2(pb.y - pa.y, pb.x - pa.x) - Math.atan2(m.b[1] - m.a[1], m.b[0] - m.a[0]);
  return { x: pa.x, y: pa.y, ang: a, sc: S * pa.k };
}
function drawPart(c, part, tr) {
  const m = PARTS[part];
  c.save(); c.translate(tr.x, tr.y); c.rotate(tr.ang); c.scale(tr.sc, tr.sc);
  if (m.img) c.drawImage(m.img, -m.a[0], -m.a[1]);
  else {   // fallback: a cut capsule with holes, if the leather never arrived
    const len = vlen(m.a, m.b), w = part === "torso" ? 190 : part === "head" ? 120 : part === "hips" ? 220 : 70;
    c.rotate(Math.atan2(m.b[1] - m.a[1], m.b[0] - m.a[0]) - Math.PI / 2);
    c.beginPath(); c.roundRect(-w / 2, -20, w, len + 40, w / 2);
    for (let i = 0; i < 5; i++) c.ellipse(0, i * (len / 5) + 10, 9, 9, 0, 0, Math.PI * 2, true);
    c.fillStyle = "#2B1407"; c.fill("evenodd");
  }
  c.restore();
}
const ORDER = [["thighA", "TA", "kneeA"], ["shinA", "kneeA", "footA"], ["thighB", "TB", "kneeB"], ["shinB", "kneeB", "footB"],
  ["hips", "HIPS", "HIPS2"], ["armA", "SA", "elbowA"], ["foreA", "elbowA", "handA"], ["armB", "SB", "elbowB"], ["foreB", "elbowB", "handB"],
  ["torso", "N", "HC"], ["head", "N", "HEAD2"]];
function endOf(k) {   // second anchor for the torso-fixed pieces: a point further down the same local axis
  if (k === "HIPS2" || k === "HEAD2") {
    const a = pos(k === "HIPS2" ? "HIPS" : "N"), n = pos("N"), h = pos("HC"), L = Math.hypot(h.x - n.x, h.y - n.y);
    return { x: a.x + (h.x - n.x) / L * 200 * S, y: a.y + (h.y - n.y) / L * 200 * S };
  }
  return pos(k);
}
const GQ = 4;   // the gel glow is soft anyway: drawn at quarter size, blurred there, scaled up
const glow = document.createElement("canvas"); glow.width = Math.ceil(W / GQ); glow.height = Math.ceil(H / GQ); const gctx = glow.getContext("2d");

function drawPuppet() {
  const trs = ORDER.map(([part, a, b]) => [part, partTransform(part, endOf(a), endOf(b), PARTS[part].d)]);
  // the gel: orange light through the perforations and a thin spill round the leather
  gctx.setTransform(1, 0, 0, 1, 0, 0); gctx.clearRect(0, 0, glow.width, glow.height); gctx.filter = `blur(${(2.6 * S / 0.34).toFixed(1)}px)`;
  gctx.setTransform(1 / GQ, 0, 0, 1 / GQ, 0, 0);
  for (const [part, tr] of trs) drawPart(gctx, part, tr);
  gctx.setTransform(1, 0, 0, 1, 0, 0); gctx.filter = "none";
  gctx.globalCompositeOperation = "source-in"; gctx.fillStyle = "#FFA33A"; gctx.fillRect(0, 0, glow.width, glow.height); gctx.globalCompositeOperation = "source-over";
  ctx.save(); ctx.globalAlpha = 0.95; ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  ctx.drawImage(glow, 0, 0, glow.width, glow.height, 0, 0, glow.width * GQ, glow.height * GQ); ctx.restore();
  for (const [part, tr] of trs) drawPart(ctx, part, tr);
}

let lit = -1;   // hovered, focused or demonstrated string
function stringSegs() { return strings.map(s => [pegPos(s.i), project(pos(s.k), 0.004)]); }
function drawStrings(segs) {
  for (const s of strings) {
    const [P, pa] = segs[s.i], on = pegs[s.i].classList.contains("on"), hi = on || lit === s.i;
    ctx.save(); ctx.globalCompositeOperation = "multiply"; ctx.lineCap = "round";
    ctx.strokeStyle = GELS[s.i];
    ctx.globalAlpha = hi ? 0.32 : 0.12; ctx.lineWidth = hi ? 12 : 7;    // bloom
    ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(pa.x, pa.y); ctx.stroke();
    ctx.globalAlpha = hi ? 1 : 0.86; ctx.lineWidth = hi ? 3.8 : 2.8;
    ctx.beginPath(); ctx.moveTo(P.x, P.y); ctx.lineTo(pa.x, pa.y); ctx.stroke();
    ctx.restore();
    // the tie: a small knot of leather where the string meets the limb
    ctx.save(); ctx.fillStyle = GELS[s.i]; ctx.globalAlpha = 0.95; ctx.beginPath(); ctx.arc(pa.x, pa.y, phone ? 2.4 : 3, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }
}
function drawBar() {
  const d = 0.03;
  for (let tier = 0; tier < LAY.bar.tiers.length; tier++) {
    const [e0, e1] = barEnds(tier), p0 = project(e0, d), p1 = project(e1, d);
    ctx.save(); ctx.globalAlpha = 0.94; ctx.strokeStyle = "#2B1407"; ctx.lineCap = "round"; ctx.lineWidth = (phone ? 10 : 12) * p0.k;
    ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y); ctx.stroke();
    if (tier === 1) {   // the crossbar is fixed under the main bar by a short upright at its middle
      const [, , c0] = barEnds(0), [, , c1] = barEnds(1); ctx.lineWidth = 6; ctx.globalAlpha = 0.9;
      ctx.beginPath(); ctx.moveTo(c0.x, c0.y); ctx.lineTo(c1.x, c1.y); ctx.stroke();
    }
    ctx.restore();
  }
}

// hands: far from the cloth, so big and soft; cached once per pose
const sprites = {};
function sprite(pose) {
  const m = PARTS[pose]; if (!m.img) return null;
  if (sprites[pose]) return sprites[pose];
  const d = 0.3, k = 1 / (1 - d), sc = LAY.hand * k, blur = 6 * (phone ? 0.75 : 1), pad = blur * 3;
  const c = document.createElement("canvas"); c.width = Math.ceil(m.img.width * sc + pad * 2); c.height = Math.ceil(m.img.height * sc + pad * 2);
  const g = c.getContext("2d"); g.filter = `blur(${blur}px)`; g.globalAlpha = 0.8;
  g.drawImage(m.img, pad, pad, m.img.width * sc, m.img.height * sc);
  return (sprites[pose] = { c, ax: pad + m.a[0] * sc, ay: pad + m.a[1] * sc });
}
function drawHand() {
  const sp = sprite(hand.pose); if (!sp || hand.alpha < 0.02) return;
  ctx.save(); ctx.globalAlpha = hand.alpha; ctx.translate(hand.x, hand.y); ctx.rotate(hand.pose === "grip" ? bar.tilt + hand.lean : hand.lean * 0.5);
  ctx.drawImage(sp.c, -sp.ax, -sp.ay); ctx.restore();
}

// ------------------------------------------------------------------ pointer: taking the bar, pulling a tag
let drag = null, pegDrag = null;
const nearBar = p => { let best = { dist: 1e9, t: 0.5 }; for (let tier = 0; tier < LAY.bar.tiers.length; tier++) { const [e0, e1] = barEnds(tier); const L = Math.hypot(e1.x - e0.x, e1.y - e0.y); const t = clamp(((p.x - e0.x) * (e1.x - e0.x) + (p.y - e0.y) * (e1.y - e0.y)) / (L * L), 0, 1); const x = e0.x + t * (e1.x - e0.x), y = e0.y + t * (e1.y - e0.y), dist = Math.hypot(p.x - x, p.y - y); if (dist < best.dist) best = { dist, x, y, t }; } return best; };
const local = e => { const r = menu.getBoundingClientRect(); return { x: (e.clientX - r.left) * W / r.width, y: (e.clientY - r.top) * H / r.height }; };
menu.addEventListener("pointermove", e => { const p = local(e); pointer.x = p.x; pointer.y = p.y; pointer.in = true; hand.toBar = false; wake(); });
menu.addEventListener("pointerleave", () => { pointer.in = false; hand.toBar = true; wake(); });
canvas.addEventListener("pointerdown", e => {
  const p = local(e), nb = nearBar(p);
  if (nb.dist < 30) { drag = { ox: p.x - bar.gxT, oy: p.y - bar.gyT, lx: p.x }; canvas.setPointerCapture(e.pointerId); e.preventDefault(); wake(); }
});
canvas.addEventListener("pointermove", e => {
  if (!drag) return; const p = local(e);
  // the bar follows the hand inside a box, and leans the way it is pulled, up to a limit
  bar.gxT = clamp(p.x - drag.ox, LIM.gx[0], LIM.gx[1]); bar.gyT = clamp(p.y - drag.oy, LIM.gy[0], LIM.gy[1]);
  bar.tiltTarget = clamp(bar.tiltTarget + (p.x - drag.lx) * 0.003, -LIM.tilt, LIM.tilt); drag.lx = p.x; wake();
});
const endDrag = () => { if (!drag) return; drag = null; bar.gxT = bar.gyT = 0; bar.tiltTarget = baseTilt(); wake(); };   // let go: the bar drifts home
canvas.addEventListener("pointerup", endDrag); canvas.addEventListener("pointercancel", endDrag);

pegs.forEach((p, i) => {
  p.addEventListener("click", () => { if (!pegDrag || !pegDrag.pulled) pull(i, p); pegDrag = null; });
  p.addEventListener("pointerdown", e => { pegDrag = { i, y: e.clientY, pulled: false }; p.setPointerCapture(e.pointerId); });
  p.addEventListener("pointermove", e => { if (pegDrag && !pegDrag.pulled && e.clientY - pegDrag.y > 26) { pegDrag.pulled = true; pull(i, p); } });
  p.addEventListener("pointerup", () => { setTimeout(() => { pegDrag = null; }, 0); });
  p.addEventListener("pointerenter", () => showTag(i)); p.addEventListener("pointerleave", () => hideTag(i));
  p.addEventListener("focus", () => showTag(i)); p.addEventListener("blur", () => hideTag(i));
});
// at rest the verdict being pointed at (or demonstrated) prints in the band under the headline; when a view is open,
// its full name hangs above its own number on the bar
const BAND_REST = band.innerHTML;
let bandShown = -2;
function showBand(i) {
  if (i === bandShown) return; bandShown = i;
  if (i < 0) { band.innerHTML = phone ? `<p class="band-hint"><span class="arrow">↑</span>Pull a string to open its verdict</p>` : BAND_REST; return; }
  const v = T[i], pk = pickFor(i), t = byId.get(pk.talkId);
  band.innerHTML = `<p class="band-k">${dot(GELS[i])}String ${i + 1} of 8 · ${v.count} talks</p><p class="band-t">${phone ? `${i + 1} · ` : ""}${esc(v.title)}</p><p class="band-w"><i>watch first:</i> ${esc(t?.title || "")}</p>`;
}
function showTag(i) {
  stopAttract();
  setLit(i);
  if (!view) { tag.hidden = true; showBand(i); return; }
  if (view.kind === "verdict" && view.i === i) { tag.hidden = true; return; }   // already printed on the cloth
  const v = T[i];
  tag.innerHTML = `${esc(v.title)}`;
  tag.style.setProperty("--c", GELS[i]);
  tag.hidden = false; placeTag();
}
function hideTag(i) { if (lit === i) { setLit(-1); tag.hidden = true; if (!view) showBand(-1); } }
function setLit(i) { lit = i; pegs.forEach((p, k) => p.classList.toggle("lit", k === i)); wake(); }
function placeTag() {
  if (tag.hidden || lit < 0) return;
  const P = pegPos(lit), w = tag.offsetWidth || 240, h = tag.offsetHeight || 40;
  const left = clamp(P.x - 30, 8, (phone ? W : 396) - 8 - w);   // never over the panel
  tag.style.left = left + "px"; tag.style.top = (P.y - (phone ? 22 : 13) - 12 - h) + "px";
  tag.style.setProperty("--kx", clamp(P.x - left, 10, w - 10) + "px");
}

// ------------------------------------------------------------------ the idle demonstration: when nobody is at the screen,
// one string at a time is tugged and its verdict prints in the band; any pointer, key or touch stops it at once
let attractT = 0, attractK = -1, attractOn = false, idleCloseT = 0;
function scheduleAttract(ms) { clearTimeout(attractT); if (!reduced) attractT = setTimeout(attractStep, ms); }
function attractStep() {
  if (view || lit >= 0 || drag || document.activeElement?.closest?.("#menu")) { scheduleAttract(6000); return; }
  attractOn = true; attractK = (attractK + 1) % 8;
  tug(attractK, true);
  attractT = setTimeout(() => { tug(attractK, false); attractT = setTimeout(attractStep, 1300); }, 3600);
}
function tug(i, on) {
  strings[i].target = on ? 0.7 : 0;
  lit = on ? i : -1; pegs.forEach((p, k) => p.classList.toggle("lit", k === lit));
  showBand(on ? i : -1);
  const t = LAY.bar.pegs[i][1];
  bar.tiltTarget = baseTilt() - (on ? t * 0.035 : 0);   // a puppeteer lifts the side of the control that holds the string
  if (on) { hand.keyAt = performance.now() + 2200; hand.toBar = true; }
  wake();
}
function stopAttract() {
  if (attractOn) {
    attractOn = false;
    if (!view) strings[attractK].target = 0;
    lit = -1; pegs.forEach(p => p.classList.remove("lit"));
    if (!view) showBand(-1);
    bar.tiltTarget = baseTilt(); hand.keyAt = -9999;
    wake();
  }
  scheduleAttract(25000);
}
function userActive() {
  stopAttract();
  clearTimeout(idleCloseT);
  idleCloseT = setTimeout(() => { if (view && document.activeElement !== q) close(); }, 90000);   // a shared wall: a walked-away visitor's view lets go by itself
}
for (const ev of ["pointerover", "pointerdown", "keydown", "wheel", "touchstart"]) window.addEventListener(ev, userActive, { capture: true, passive: true });
menu.addEventListener("pointermove", () => { if (attractOn) userActive(); }, { capture: true, passive: true });
scheduleAttract(4000);
showBand(-1);

// ------------------------------------------------------------------ frame loop
let running = true, idleFrames = 0, last = 0;
function wake() { idleFrames = 0; if (!running) { running = true; requestAnimationFrame(frame); } }
function lerp(a, b, f) { return a + (b - a) * f; }
function frame(t) {
  // the rig and the eases run on wall-clock time: a slow frame takes up to four 60 fps steps, so a swing settles in
  // the same second on a weak machine (or in a headless capture) as on a fast one
  const dt = last ? Math.min(100, t - last) : 16.7; last = t;
  const n = Math.max(1, Math.min(4, Math.round(dt / 16.7)));
  const pw = k => reduced ? 1 : 1 - Math.pow(1 - k, n);
  const f = pw(0.16);
  lamp.x = lerp(lamp.x, lamp.tx, f); lamp.y = lerp(lamp.y, lamp.ty, f);
  bar.shift = lerp(bar.shift, bar.shiftTarget, pw(0.128)); bar.dy = lerp(bar.dy, bar.dyTarget, pw(0.128)); bar.tilt = lerp(bar.tilt, bar.tiltTarget, pw(0.08));
  const halfTo = view && LAY.openHalf ? LAY.openHalf : 1;
  bar.half = lerp(bar.half, halfTo, pw(0.128));   // with the name plates hoisted, the pegs draw in, clear of the opened side
  // the bar has weight: it follows the hand closely while held and drifts home after a let-go (a snap would fling the puppet)
  { const k = pw(drag ? 0.3 : 0.05); bar.gx = lerp(bar.gx, bar.gxT, k); bar.gy = lerp(bar.gy, bar.gyT, k); }
  for (const s of strings) s.pull = reduced ? s.target : lerp(s.pull, s.target, pw(attractOn ? 0.035 : 0.12));   // the demonstration tugs slowly: it must not swing
  // the hand: a fist on the wood while the bar is being moved, an open shadow following the pointer otherwise
  const nb = nearBar(pointer);
  const atBar = drag || hand.toBar || !pointer.in || nb.dist < 42;
  const steering = drag || (t - hand.keyAt < 1500);
  hand.pose = steering ? "grip" : "open";
  const [e0, e1, c] = barEnds(0);
  const onCentre = drag || !pointer.in || hand.toBar;
  let gx = onCentre ? c.x : e0.x + clamp(nb.t, 0.25, 0.75) * (e1.x - e0.x), gy = onCentre ? c.y : e0.y + clamp(nb.t, 0.25, 0.75) * (e1.y - e0.y);
  if (attractOn) { const P = pegPos(attractK); gx = P.x; gy = P.y; }   // the demonstration's hand grips the bar at the string it tugs
  const over = hand.pose === "open" ? (phone ? 22 : 34) : 0;
  const hx = atBar ? gx : pointer.x, hy = atBar ? gy + over : pointer.y;
  const hf = pw(atBar ? 0.22 : 0.3);
  hand.x = lerp(hand.x, hx, hf); hand.y = lerp(hand.y, hy, hf);
  hand.lean = lerp(hand.lean, (lamp.x - LAY.lampRest[0]) * 0.0009, f);
  // the open hand is a shadow on the cloth side only: never over the type people are reading
  const overType = !atBar && (phone ? !!view : pointer.x > W * 0.44);
  const handWanted = !overType && (pointer.in || (steering && !attractOn));
  const handTo = handWanted ? (atBar && !view && !drag ? 0.55 : 1) : 0;
  hand.alpha = reduced ? handTo : lerp(hand.alpha, handTo, pw(handWanted ? 0.12 : 0.08));

  if (reduced) settle(40); else for (let i = 0; i < n; i++) step();

  const segs = stringSegs();
  meter(segs);
  ctx.clearRect(0, 0, W, H);
  drawCloth(t);
  drawStrings(segs);
  drawPuppet();
  drawBar();
  drawHand();

  // the HTML that rides on the canvas: each peg carries its number and its name plate, so they move as one
  pegs.forEach((p, i) => { const P = pegPos(i); p.style.transform = `translate(${P.x.toFixed(1)}px, ${P.y.toFixed(1)}px)`; });
  placeTag();
  menu.style.setProperty("--sx", ((720 - lamp.x) * 0.045).toFixed(1) + "px");
  menu.style.setProperty("--sy", ((300 - lamp.y) * 0.05 + 7).toFixed(1) + "px");

  const moving = energy > 0.03 || Math.abs(hand.alpha - handTo) > 0.02 || Math.abs(lamp.x - lamp.tx) > 0.3 || Math.abs(hand.x - hx) + Math.abs(hand.y - hy) > 0.4 || strings.some(s => Math.abs(s.pull - s.target) > 0.002) || drag || Math.abs(bar.tilt - bar.tiltTarget) > 0.001 || Math.abs(bar.shift - bar.shiftTarget) > 0.3 || Math.abs(bar.half - halfTo) > 0.002 || Math.abs(bar.dy - bar.dyTarget) > 0.3 || Math.abs(bar.gx - bar.gxT) + Math.abs(bar.gy - bar.gyT) > 0.3 || pending > 0;
  idleFrames = moving ? 0 : idleFrames + 1;
  if (reduced && idleFrames > 3) { running = false; return; }   // calm version: nothing breathes
  if (idleFrames > 40) { running = true; setTimeout(() => requestAnimationFrame(frame), 40); return; }   // at rest only the flame breathes: 25 fps is plenty
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
})();
