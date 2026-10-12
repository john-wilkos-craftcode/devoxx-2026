// The rendered cinema: Blender stills and walk clips (scripts/blender/build_scene.py), with the programme and the
// talk as real HTML pinned onto the screens. shots.json says where each screen lands in each still; a CSS matrix3d
// (a projective transform) maps the panel's rectangle onto that quad, so text stays crisp, clickable and
// scrollable. Only the rooms with a rendered walk can be walked to; other sessions open on the hall screen.

const TZ = "Europe/Brussels";
const fmt = (o) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...o });
const fTime = fmt({ hour: "2-digit", minute: "2-digit" });
const fDay = fmt({ weekday: "long" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const dayKey = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date(iso));
const roomNo = (t) => { const m = /^Room (\d+)$/.exec(t.room || ""); return m ? Number(m[1]) : null; };
const ytUrl = (t, sec = 0) => `https://www.youtube.com/watch?v=${t.videoId}${sec ? `&t=${sec}s` : ""}`;
const EMBED = window.self === window.top;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const SHEET = matchMedia("(max-width: 760px), (max-height: 520px)").matches;
const IMG_W = 1920, IMG_H = 1080;

const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid);
  return n;
};

// ---------- projective pinning ----------
// The 3x3 matrix taking the unit basis to four points, then src -> dst as dst * adj(src).
function adj(m) {
  return [m[4] * m[8] - m[5] * m[7], m[2] * m[7] - m[1] * m[8], m[1] * m[5] - m[2] * m[4],
          m[5] * m[6] - m[3] * m[8], m[0] * m[8] - m[2] * m[6], m[2] * m[3] - m[0] * m[5],
          m[3] * m[7] - m[4] * m[6], m[1] * m[6] - m[0] * m[7], m[0] * m[4] - m[1] * m[3]];
}
const mul = (a, b) => {
  const c = Array(9).fill(0);
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) c[3 * i + j] += a[3 * i + k] * b[3 * k + j];
  return c;
};
const mulv = (m, v) => [m[0] * v[0] + m[1] * v[1] + m[2] * v[2], m[3] * v[0] + m[4] * v[1] + m[5] * v[2], m[6] * v[0] + m[7] * v[1] + m[8] * v[2]];
function basis(p) {
  const m = [p[0][0], p[1][0], p[2][0], p[0][1], p[1][1], p[2][1], 1, 1, 1];
  const v = mulv(adj(m), [p[3][0], p[3][1], 1]);
  return mul(m, [v[0], 0, 0, 0, v[1], 0, 0, 0, v[2]]);
}
function matrix3d(w, h, dst) {
  const t = mul(basis(dst), adj(basis([[0, 0], [w, 0], [0, h], [w, h]])));
  const n = t.map((x) => x / t[8]);
  return `matrix3d(${[n[0], n[3], 0, n[6], n[1], n[4], 0, n[7], 0, 0, 1, 0, n[2], n[5], 0, n[8]].join(",")})`;
}
// shots.json corners in any order -> [top-left, top-right, bottom-left, bottom-right]
function ordered(quad) {
  const byY = [...quad].sort((a, b) => a[1] - b[1]);
  const [tl, tr] = byY.slice(0, 2).sort((a, b) => a[0] - b[0]);
  const [bl, br] = byY.slice(2).sort((a, b) => a[0] - b[0]);
  return [tl, tr, bl, br];
}

// ---------- state ----------
const talks = window.DEVOXX.talks;
const stage = document.getElementById("stage"), plate = document.getElementById("plate"), clip = document.getElementById("clip");
const overlay = document.getElementById("overlay"), loading = document.getElementById("loading");
const shots = await fetch("media/shots.json").then((r) => r.json());
const walkable = new Set(Object.keys(shots).filter((k) => k.startsWith("walk-")).map((k) => Number(k.slice(5))));
const wallHeight = Math.round(1600 * shots.hall.size.programme[1] / shots.hall.size.programme[0]);
let pinned = null;          // { el, quad, w, h }
let busy = false;

function place() {
  if (!pinned || SHEET) return;
  const W = stage.clientWidth, H = stage.clientHeight, s = Math.max(W / IMG_W, H / IMG_H);
  const ox = (W - IMG_W * s) / 2, oy = (H - IMG_H * s) / 2;
  const dst = ordered(pinned.quad).map(([x, y]) => [ox + x * IMG_W * s, oy + y * IMG_H * s]);
  pinned.el.style.transform = matrix3d(pinned.w, pinned.h, dst);
}
addEventListener("resize", place);

function pin(panel, quad, w, h) {
  if (pinned) pinned.el.remove();
  if (SHEET) {
    panel.classList.add("kx-sheet");
    document.body.append(panel);
  } else {
    panel.classList.add("pinned");
    panel.style.width = `${w}px`;
    panel.style.height = `${h}px`;
    overlay.append(panel);
  }
  pinned = { el: panel, quad, w, h };
  place();
}
const unpin = () => { if (pinned) { pinned.el.remove(); pinned = null; } };

const showStill = (name) => new Promise((resolve) => {
  plate.onload = () => resolve();
  plate.src = `media/${name}.jpg`;
  if (plate.complete && plate.naturalWidth) resolve();
});

function playClip(name) {
  return new Promise((resolve) => {
    if (reduceMotion) { resolve(); return; }
    clip.src = `media/${name}.mp4`;
    clip.hidden = false;
    const done = () => { clip.onended = clip.onerror = null; resolve(); };
    clip.onended = done;
    clip.onerror = done;                     // a missing clip is a cut, not a dead end
    clip.play().catch(done);
  });
}
const hideClip = () => { clip.hidden = true; clip.removeAttribute("src"); clip.load(); };

// ---------- the programme on the hall screen ----------
const days = [...new Set(talks.filter((t) => t.start).map((t) => dayKey(t.start)))].sort();
let day = days.includes("2026-10-07") ? "2026-10-07" : days[0];
let query = "";
const slotsBox = el("div", { class: "kx-slots" });
const dayBox = el("div", { class: "kx-days", role: "group", "aria-label": "Day" });
const search = el("input", { class: "kx-search", type: "search", placeholder: "Search talks, speakers, tools", "aria-label": "Search talks" });
search.addEventListener("input", () => { query = search.value.trim().toLowerCase(); renderWall(); });
for (const d of days) {
  const iso = talks.find((t) => t.start && dayKey(t.start) === d).start;
  dayBox.append(el("button", { type: "button", text: fShort.format(new Date(iso)), "data-day": d,
    onclick: () => { day = d; renderWall(); slotsBox.scrollTop = 0; } }));
}
const wall = el("div", { class: "kx-panel kx-wall" },
  el("div", { class: "kx-wall-head" }, el("h1", { text: "Devoxx Belgium 2026" }),
    el("span", { class: "kx-wall-sub", text: `Choose a session. Room ${[...walkable].join(", ")} has a seat to walk you to.` })),
  el("div", { class: "kx-wall-head" }, dayBox, search),
  slotsBox);
const blob = (t) => [t.title, ...t.speakers.map((s) => s.name), t.s && t.s.tldr, ...((t.s && t.s.tech) || [])].join(" ").toLowerCase();

function renderWall() {
  for (const b of dayBox.children) b.setAttribute("aria-pressed", String(b.dataset.day === day));
  slotsBox.textContent = "";
  const terms = query.split(/\s+/).filter(Boolean);
  const list = talks.filter((t) => t.start && t.type !== "Keynote Overflow" && (terms.length ? true : dayKey(t.start) === day) && terms.every((w) => blob(t).includes(w)))
    .sort((a, b) => a.start.localeCompare(b.start) || (roomNo(a) || 99) - (roomNo(b) || 99));
  if (!list.length) { slotsBox.append(el("p", { class: "kx-empty", text: "No session matches. Try another word or day." })); return; }
  const slots = new Map();
  for (const t of list) { const key = terms.length ? `${dayKey(t.start)} ${t.start}` : t.start; if (!slots.has(key)) slots.set(key, []); slots.get(key).push(t); }
  for (const group of slots.values()) {
    const iso = group[0].start;
    slotsBox.append(el("div", { class: "kx-slot" },
      el("div", { class: "kx-slot-time" }, fTime.format(new Date(iso)), terms.length ? el("div", { style: "font-size:20px;color:#9aa3c9;margin-top:6px", text: fShort.format(new Date(iso)) }) : null),
      el("div", { class: "kx-slot-talks" }, group.map((t) => {
        const n = roomNo(t);
        return el("button", { class: "kx-talk", type: "button", onclick: () => goTalk(t) },
          el("span", { class: `kx-room${n ? "" : " is-bof"}`, text: n ? String(n) : (t.room || "?") }),
          el("span", {}, el("b", { text: t.title }), el("span", { text: t.speakers.map((s) => s.name).join(", ") })));
      }))));
  }
}

// a session without a rendered walk: its summary on the hall screen
function showOnWall(t) {
  const s = t.s || {};
  slotsBox.textContent = "";
  slotsBox.append(el("div", { class: "kx-detail" },
    el("div", { class: "kx-meta", text: [t.type, t.start ? `${fDay.format(new Date(t.start))} ${fTime.format(new Date(t.start))}` : null, t.room].filter(Boolean).join(", ") }),
    el("h2", { text: t.title }),
    el("div", { class: "kx-who", text: t.speakers.map((sp) => sp.name).join(", ") }),
    s.tldr ? el("p", { class: "kx-tldr", text: s.tldr }) : null,
    s.keyPoints && s.keyPoints.length ? el("ul", { class: "kx-points" }, s.keyPoints.map((x) => el("li", { text: x }))) : null,
    el("div", { class: "kx-actions" },
      t.videoId ? el("a", { class: "kx-btn is-play", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" }) : null,
      el("button", { class: "kx-btn", type: "button", text: "Back to the programme", onclick: () => { history.replaceState(null, "", location.pathname); renderWall(); } })),
    el("p", { class: "kx-note", text: roomNo(t) ? `The walk to Room ${roomNo(t)} isn't rendered yet.` : `${t.room || "This room"} is off the cinema floor, so there is no seat to walk you to.` })));
  slotsBox.scrollTop = 0;
}

// ---------- the talk on the cinema screen ----------
const pane = (t, tab) => {
  const s = t.s || {};
  if (tab === "points") return el("ul", {}, (s.keyPoints || []).map((p) => el("li", { text: p })));
  if (tab === "monday") return el("ol", {}, (s.takeaways || []).map((p) => el("li", { text: p })));
  if (tab === "chapters") return el("div", {}, (s.chapters || []).map((c) => chapter(t, c)));
  return el("div", {}, (s.summary || t.abstract || []).map((p) => el("p", { style: "margin:0 0 18px", text: p })));
};
const toSeconds = (at) => { const [m, sec] = String(at).split(":").map(Number); return (m || 0) * 60 + (sec || 0); };
let playAt = null;
function chapter(t, c) {
  const kids = [el("time", { text: c.at }), el("span", { text: c.title })];
  if (!t.videoId) return el("div", { class: "kx-chapter" }, ...kids);
  if (!EMBED) return el("a", { class: "kx-chapter", href: ytUrl(t, toSeconds(c.at)), target: "_blank", rel: "noopener" }, ...kids);
  return el("button", { class: "kx-chapter", type: "button", onclick: () => playAt && playAt(toSeconds(c.at)) }, ...kids);
}
function screenPanel(t, w, h) {
  const s = t.s || {};
  const tabs = [["story", "The story"], ["points", "Key points"], ["monday", "Try this on Monday"], ["chapters", "Chapters"]]
    .filter(([id]) => id === "story" || (id === "points" && s.keyPoints && s.keyPoints.length) || (id === "monday" && s.takeaways && s.takeaways.length) || (id === "chapters" && s.chapters && s.chapters.length));
  const paneBox = el("div", { class: "kx-pane" });
  const tabBox = el("div", { class: "kx-tabs", role: "group", "aria-label": "Talk details" });
  const showTab = (id) => { paneBox.textContent = ""; paneBox.append(pane(t, id)); for (const b of tabBox.children) b.setAttribute("aria-pressed", String(b.dataset.tab === id)); };
  for (const [id, label] of tabs) tabBox.append(el("button", { type: "button", "data-tab": id, text: label, onclick: () => showTab(id) }));
  const left = el("div", { style: "min-width:0;display:flex;flex-direction:column" });
  const intro = () => {
    left.textContent = "";
    left.append(
      el("div", { class: "kx-meta", text: [t.type, t.start ? `${fDay.format(new Date(t.start))} ${fTime.format(new Date(t.start))}` : null, t.room].filter(Boolean).join(", ") }),
      el("h2", { text: t.title }),
      el("div", { class: "kx-who", text: t.speakers.map((sp) => sp.company ? `${sp.name} (${sp.company})` : sp.name).join(", ") }),
      s.tldr ? el("p", { class: "kx-tldr", text: s.tldr }) : null,
      el("div", { class: "kx-actions" },
        t.videoId ? (EMBED ? el("button", { class: "kx-btn is-play", type: "button", text: "Play the talk", onclick: () => playAt(0) })
          : el("a", { class: "kx-btn is-play", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" }))
          : el("span", { class: "kx-note", text: "No recording on YouTube yet. This summary is from the abstract." }),
        el("button", { class: "kx-btn", type: "button", text: "Back to the hall", onclick: () => goHall() })));
  };
  playAt = (sec) => {
    left.textContent = "";
    left.append(el("div", { class: "kx-player" }, el("iframe", {
      src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${sec}`, title: t.title,
      allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true })),
    el("div", { class: "kx-actions" },
      el("button", { class: "kx-btn", type: "button", text: "Stop and show the summary", onclick: intro }),
      el("button", { class: "kx-btn", type: "button", text: "Back to the hall", onclick: () => goHall() })));
    if (tabs.find(([id]) => id === "chapters")) showTab("chapters");
  };
  intro();
  showTab(tabs.find(([id]) => id === "points") ? "points" : "story");
  return el("div", { class: "kx-panel kx-screen" }, left, el("div", { class: "kx-side" }, tabBox, paneBox));
}

// ---------- moving between the hall and a seat ----------
let room = null;   // the room we're sitting in, or null in the hall

async function goHall() {
  if (busy) return;
  busy = true;
  history.replaceState(null, "", location.pathname);
  unpin();
  if (room) {
    await playClip(`walk-${room}-back`);
    room = null;
  }
  await showStill("hall");
  hideClip();
  renderWall();
  pin(wall, shots.hall.overlay.programme, 1600, wallHeight);
  busy = false;
}

async function goTalk(t) {
  if (busy) return;
  history.replaceState(null, "", `#talk-${t.id}`);
  const n = roomNo(t);
  if (!walkable.has(n)) { showOnWall(t); return; }
  busy = true;
  unpin();
  await playClip(`walk-${n}`);
  await showStill(`seat-${n}`);
  hideClip();
  room = n;
  const shot = shots[`seat-${n}`];
  const [sw, sh] = shot.size.screen;                 // metres: the panel keeps the real screen's shape
  const w = 2048, h = Math.round(w * sh / sw);
  pin(screenPanel(t, w, h), shot.overlay.screen, w, h);
  busy = false;
}

// ---------- start ----------
await showStill("hall");
renderWall();
pin(wall, shots.hall.overlay.programme, 1600, wallHeight);
loading.classList.add("is-done");
const deep = /^#talk-(\d+)$/.exec(location.hash);
if (deep) { const t = talks.find((x) => x.id === Number(deep[1])); if (t) goTalk(t); }
addEventListener("keydown", (e) => { if (e.key === "Escape" && room) goHall(); });
