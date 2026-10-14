// The rendered cinema: Blender stills and walk clips (scripts/blender/build_scene.py), with the programme and the
// talk as real HTML pinned onto the screens in them. shots.json says where each screen lands in each still; a CSS
// matrix3d (a projective transform) maps a fixed canvas onto that quad, like a real display, so text stays crisp,
// clickable and scrollable. Laptops get the landscape shots (the hall screen, the whole cinema screen); portrait
// viewports get the phone shots (a schedule totem in the hall, the middle of the cinema screen from the seat). What
// stands in front of the cinema screen (the "#DEVOXX" letters, the seats) is a separate cut-out laid over the talk.

const TZ = "Europe/Brussels";
const fmt = (o) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...o });
const fTime = fmt({ hour: "2-digit", minute: "2-digit" });
const fDayLong = fmt({ weekday: "long", day: "numeric", month: "long" });
const fDay = fmt({ weekday: "long" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const dayKey = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date(iso));
const roomNo = (t) => { const m = /^Room (\d+)$/.exec(t.room || ""); return m ? Number(m[1]) : null; };
const ytUrl = (t, sec = 0) => `https://www.youtube.com/watch?v=${t.videoId}${sec ? `&t=${sec}s` : ""}`;
const EMBED = window.self === window.top;      // YouTube can't be embedded inside the artifact sandbox
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const IMG = { laptop: [1920, 1080], phone: [1080, 2340] };
const CANVAS = { hall: 980, "hall-phone": 340, seat: 1180, "door-phone": 340 };   // design widths in css px

const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k === "style") n.style.cssText = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  return put(n, kids);
};
function put(node, ...kids) { for (const k of kids.flat(Infinity)) if (k != null && k !== false) node.append(k); return node; }   // append() would print "null"

// ---------- the data, tidied for the screens ----------
const clean = (s) => String(s || "").replace(/[\p{Extended_Pictographic}️‍]/gu, "").replace(/\s{2,}/g, " ").trim();
const capital = (name) => name.replace(/^\p{Ll}/u, (c) => c.toUpperCase());   // "yann Blazart" -> "Yann Blazart"; "van" mid-name untouched
const talks = window.DEVOXX.talks.filter((t) => t.type !== "Keynote Overflow").map((t) => ({
  ...t, title: clean(t.title), speakers: t.speakers.map((sp) => ({ ...sp, name: capital(clean(sp.name)) })) }));
const speakers = (t, withCompany) => t.speakers.map((sp) => withCompany && sp.company ? `${sp.name} (${sp.company})` : sp.name).join(", ");
const when = (t) => t.start ? `${fDay.format(new Date(t.start))} ${fTime.format(new Date(t.start))}` : null;
const whenShort = (t) => t.start ? `${fShort.format(new Date(t.start))} Oct, ${fTime.format(new Date(t.start))}` : null;
const whenLong = (t) => t.start ? `${fDayLong.format(new Date(t.start))}, ${fTime.format(new Date(t.start))}` : null;
// a plain talk needs no label; the rest in sentence case ("Hands-on lab"), BOF stays an acronym
const typeLabel = (t) => (t.type === "Conference" ? "" : t.type === "BOF" ? "BOF" : t.type[0] + t.type.slice(1).toLowerCase());
const titleSize = (title, big, small) => title.length > 90 ? small : title.length > 55 ? (big + small) / 2 : big;

// ---------- projective pinning ----------
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
function basis(p) {   // the matrix taking the unit basis to p[0..2], scaled so p[3] maps too
  const m = [p[0][0], p[1][0], p[2][0], p[0][1], p[1][1], p[2][1], 1, 1, 1];
  const v = mulv(adj(m), [p[3][0], p[3][1], 1]);
  return mul(m, [v[0], 0, 0, 0, v[1], 0, 0, 0, v[2]]);
}
function matrix3d(w, h, dst) {   // dst: top-left, top-right, bottom-left, bottom-right
  const t = mul(basis(dst), adj(basis([[0, 0], [w, 0], [0, h], [w, h]])));
  const n = t.map((x) => x / t[8]);
  // a square-on screen has (next to) no perspective: a plain 2D transform keeps the text rasterised sharp
  if (Math.abs(n[6] * w) < 0.004 && Math.abs(n[7] * h) < 0.004) {
    const [tl, tr, bl] = dst;
    return `matrix(${(tr[0] - tl[0]) / w},${(tr[1] - tl[1]) / w},${(bl[0] - tl[0]) / h},${(bl[1] - tl[1]) / h},${tl[0]},${tl[1]})`;
  }
  return `matrix3d(${[n[0], n[3], 0, n[6], n[1], n[4], 0, n[7], 0, 0, 1, 0, n[2], n[5], 0, n[8]].join(",")})`;
}
function ordered(quad) {
  const byY = [...quad].sort((a, b) => a[1] - b[1]);
  const [tl, tr] = byY.slice(0, 2).sort((a, b) => a[0] - b[0]);
  const [bl, br] = byY.slice(2).sort((a, b) => a[0] - b[0]);
  return [tl, tr, bl, br];
}

// ---------- the stage ----------
const stage = document.getElementById("stage");
const plate = document.getElementById("plate"), clip = document.getElementById("clip"), overlay = document.getElementById("overlay");
const front = document.getElementById("front"), fade = document.getElementById("fade");
const loading = document.getElementById("loading"), statusBox = document.getElementById("status"), skipBtn = document.getElementById("skip");
const shots = await fetch("media/shots.json").then((r) => r.json());
const walkable = new Set(Object.keys(shots).filter((k) => /^seat-\d+$/.test(k)).map((k) => Number(k.split("-")[1])));
const form = () => (stage.clientWidth / stage.clientHeight < 0.8 ? "phone" : "laptop");
let shape = form();
// the phone version of a shot: the hall totem instead of the hall screen, and the totem at the room's door instead
// of the seat (a cinema screen is far too wide to read in portrait)
const shotKey = (base) => {
  if (shape !== "phone") return base;
  const k = base === "hall" ? "hall-phone" : base.replace(/^seat-(\d+)$/, "door-phone-$1");
  return shots[k] ? k : base;
};
// on a phone the walk stops at the door: the time into walk-<n>.mp4 when the camera passes it
const doorTime = (n) => {
  const w = shots[`walk-${n}`];
  return w && w.door_frame != null ? w.door_frame / w.fps : null;
};
// phones have their own portrait walk, from the hall totem to the door totem; else the laptop's, stopped at the door
const walkClip = (n) => (shape === "phone" && shots[`walk-phone-${n}`] ? `walk-phone-${n}` : `walk-${n}`);
const canvasFor = (key) => CANVAS[key.replace(/-\d+$/, "")];

// How a still sits in the viewport: cropped to fill it (cover) unless that would cut more than 6% off a side and
// risk cutting into a screen, then letterboxed (contain), black bars like a cinema.
// A still rendered wider than the walk (the seat, where the laptop needs room below) says which part of it is the walk's
// frame (inner, 0-1): that part is framed like this, so the walk's last frame and the still line up.
function framing(key) {
  const sh = shots[key] || {};
  const [iw, ih] = sh.px || IMG[key.includes("phone") ? "phone" : "laptop"];
  const [x0, y0, x1, y1] = sh.inner || [0, 0, 1, 1];
  const fw = (x1 - x0) * iw, fh = (y1 - y0) * ih;
  const W = stage.clientWidth, H = stage.clientHeight;
  const cover = Math.max(W / fw, H / fh), crop = Math.max(1 - W / (fw * cover), 1 - H / (fh * cover)) / 2;
  const s = crop > 0.06 ? Math.min(W / fw, H / fh) : cover;
  return { iw, ih, s, ox: (W - fw * s) / 2 - x0 * iw * s, oy: (H - fh * s) / 2 - y0 * ih * s, contain: crop > 0.06 };
}
// where CSS object-fit puts the whole still: the base the transforms move it from
function placed(key) {
  const sh = shots[key] || {};
  if (!sh.inner) return framing(key);
  const [iw, ih] = sh.px, W = stage.clientWidth, H = stage.clientHeight;
  const s = framing(key).contain ? Math.min(W / iw, H / ih) : Math.max(W / iw, H / ih);
  return { iw, ih, s, ox: (W - iw * s) / 2, oy: (H - ih * s) / 2 };
}
// Phones, at a door: once the walk has settled, the still is zoomed by hand onto the totem until its screen nearly
// fills the phone (a sliver of the room round the edges), and the talk is laid out for that bigger screen.
let zoomed = false;
const SLIVER = 8;   // css px of the render left showing past the screen's edge, at the tighter side
function fit(key) {
  if (seat && seat.layout && key === seat.key) return seat.layout.frame;
  const f = framing(key);
  if (!zoomed || !key.startsWith("door-phone")) return f;
  const { iw, ih } = f, W = stage.clientWidth, H = stage.clientHeight;
  const q = shots[key].overlay.screen, xs = q.map((p) => p[0] * iw), ys = q.map((p) => p[1] * ih);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const s = Math.max(f.s, Math.min((W - 2 * SLIVER) / (x1 - x0), (H - 2 * SLIVER) / (y1 - y0)));
  const clamp = (o, size, view) => (size <= view ? (view - size) / 2 : Math.min(0, Math.max(view - size, o)));   // no black past the still
  return { iw, ih, s, ox: clamp(W / 2 - (x0 + x1) / 2 * s, iw * s, W), oy: clamp(H / 2 - (y0 + y1) / 2 * s, ih * s, H), contain: f.contain };
}
// the walk's last frame, the still and its cut-out moved from where object-fit puts them to where fit() wants them.
// Animated, it starts while the walk is still settling, so it reads as the same push-in carrying on.
const ZOOM_S = 0.75, ZOOM_LEAD = 0.3;   // its length, and how long before the walk's end it starts
function zoomTo(key, on, animate = false) {
  zoomed = on;
  const a = placed(key), b = fit(key), k = b.s / a.s;
  const tf = on ? `translate(${b.ox - k * a.ox}px, ${b.oy - k * a.oy}px) scale(${k})` : "";
  for (const e of [plate, front, clip]) {
    e.style.transformOrigin = "0 0";
    e.style.transition = animate ? `transform ${ZOOM_S}s cubic-bezier(.3, 0, .2, 1), opacity .35s ease` : "";
    e.style.transform = tf;
  }
  return new Promise((resolve) => setTimeout(resolve, animate ? ZOOM_S * 1000 : 0));
}
let face = null;      // { el, key, overlayName, w, h }
function place() {
  if (!face) return;
  const { iw, ih, s, ox, oy } = fit(face.key);
  const quad = shots[face.key].overlay[face.overlayName];
  face.el.style.transform = matrix3d(face.w, face.h, ordered(quad).map(([x, y]) => [ox + x * iw * s, oy + y * ih * s]));
}
function mount(panel, key, overlayName) {
  if (face) face.el.remove();
  const [mw, mh] = shots[key].size[overlayName];
  // laptops: a fixed canvas, like a real display; phones: laid out 1:1 for the width the totem takes on this screen
  let w = canvasFor(key);
  if (seat && key === seat.key) w = Math.round(seat.layout.screen.w);   // the seat on laptops: laid out 1:1 for the screen's size
  else if (key.includes("phone")) {
    const { iw, ih, s } = fit(key);
    const [tl, tr] = ordered(shots[key].overlay[overlayName]);
    w = Math.max(280, Math.round(Math.hypot((tr[0] - tl[0]) * iw * s, (tr[1] - tl[1]) * ih * s)));
  }
  const h = Math.round(w * mh / mw);
  panel.style.width = `${w}px`;
  panel.style.height = `${h}px`;
  if (shots[key].clear_bottom > 0) panel.style.paddingBottom = `${Math.round(shots[key].clear_bottom * h)}px`;   // keep clear of the letters
  overlay.append(panel);
  face = { el: panel, key, overlayName, w, h };
  place();
  fitCards(panel);
  for (const s of panel.querySelectorAll(".strip, .scroller")) watchScroll(s);
}
const unmount = () => { if (face) { face.el.remove(); face = null; } front.hidden = true; if (zoomed) zoomTo("hall", false); leaveSeat(); };
let resizeTimer = 0;
addEventListener("resize", () => {
  if (seat) { relayoutSeat(); return; }
  place();
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const next = form();
    if (next !== shape && !busy) { shape = next; rerender(); }
    else if (seat) relayoutSeat();
    else if (face) {
      const mode = framing(face.key).contain ? "contain" : "cover";
      plate.style.objectFit = front.style.objectFit = mode;
      if (zoomed) { zoomTo(face.key, true); mount(face.el, face.key, face.overlayName); } else place();   // relaid for the new size
    }
  }, 180);
});

// a card's text must fit its fixed height: shorten the title, then the speakers, a line at a time until it does
function fitCards(root) {
  const lines = (e) => (e && parseInt(getComputedStyle(e).webkitLineClamp, 10)) || 0;
  for (const c of root.querySelectorAll(".card")) {
    const title = c.querySelector(".title"), who = c.querySelector(".who");
    for (let i = 0; i < 4 && c.scrollHeight > c.clientHeight + 1; i++) {
      if (lines(title) > 2) title.style.webkitLineClamp = lines(title) - 1;
      else if (lines(who) > 1) who.style.webkitLineClamp = 1;
      else break;
    }
  }
}

// fade the edge of anything that scrolls, on the side where there's more
function watchScroll(s) {
  const update = () => {
    if (s.classList.contains("strip")) {
      s.classList.toggle("more-l", s.scrollLeft > 4);
      s.classList.toggle("more-r", s.scrollLeft + s.clientWidth < s.scrollWidth - 4);
    } else s.classList.toggle("more-b", s.scrollTop + s.clientHeight < s.scrollHeight - 12);
  };
  s.addEventListener("scroll", update, { passive: true });
  requestAnimationFrame(update);
}
// one tab stop per group of chips (days, times, tabs): Tab lands on the chosen one, the arrow keys move along
function rove(group) {
  const items = [...group.querySelectorAll("button")];
  const on = items.find((b) => b.getAttribute("aria-pressed") === "true") || items[0];
  for (const b of items) b.tabIndex = b === on ? 0 : -1;
  group.onkeydown = (e) => {
    const i = items.indexOf(document.activeElement);
    if (i < 0 || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const j = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (i + (e.key === "ArrowRight" ? 1 : -1) + items.length) % items.length;
    items[i].tabIndex = -1; items[j].tabIndex = 0; items[j].focus();
  };
}
function centre(strip) {   // bring the pressed chip into view without scrolling the page
  const on = strip.querySelector('[aria-pressed="true"]');
  if (on) strip.scrollLeft = on.offsetLeft - (strip.clientWidth - on.offsetWidth) / 2;
}

const showStill = (key) => new Promise((resolve) => {
  const src = `media/${key}.jpg`;
  const done = () => {
    plate.src = src;
    const fr = shots[key] && shots[key].front;
    if (fr) { front.src = `media/${fr}.webp`; front.hidden = false; } else front.hidden = true;
    resolve();
  };
  const mode = framing(key).contain ? "contain" : "cover";
  plate.style.objectFit = front.style.objectFit = clip.style.objectFit = mode;
  if (plate.getAttribute("src") === src) { done(); return; }
  const img = new Image();
  img.onload = img.onerror = done;
  img.src = src;
});

// fetch a room's walk when its card is pointed at or focused, so the click plays at once without every walk
// being downloaded up front (a lot on a phone's data plan)
const warmed = new Set();
function warm(n) {
  if (!walkable.has(n) || warmed.has(n) || reduceMotion) return;
  warmed.add(n);
  const l = document.createElement("link");
  l.rel = "prefetch"; l.href = `media/${walkClip(n)}.mp4`;
  document.head.append(l);
}

let skipWalk = null;
function playClip(name, { from = 0, until = null, nearEnd = null } = {}) {
  return new Promise((resolve) => {
    if (reduceMotion) { resolve(); return; }
    let watching = true;
    const done = () => { watching = false; clip.onended = clip.onerror = clip.ontimeupdate = null; skipWalk = null; skipBtn.hidden = true; resolve(); };
    skipWalk = done;
    clip.src = `media/${name}.mp4`;
    clip.classList.remove("is-shown");
    clip.hidden = false;
    clip.onended = done;
    clip.onerror = done;                       // a missing clip is a cut, not a dead end
    if (until != null) clip.ontimeupdate = () => { if (clip.currentTime >= until) { clip.pause(); done(); } };
    // fade in over the still (the first frame is the still), which hides the moment the video starts
    const go = () => { if (from) clip.currentTime = from; clip.play().then(() => { clip.classList.add("is-shown"); skipBtn.hidden = false; watchEnd(); }).catch(done); };
    // nearEnd: [seconds, fn], fn called that long before the clip ends
    const watchEnd = () => {
      if (!watching || !nearEnd) return;
      if (clip.duration - clip.currentTime <= nearEnd[0]) { nearEnd[1](); return; }
      requestAnimationFrame(watchEnd);
    };
    if (clip.readyState >= 1) go(); else clip.addEventListener("loadedmetadata", go, { once: true });
  });
}
// fade the clip out over the still that replaced it, then let it go
const hideClip = () => new Promise((resolve) => {
  clip.pause();
  const gone = () => { clip.hidden = true; clip.removeAttribute("src"); clip.load(); resolve(); };
  if (clip.hidden || !clip.classList.contains("is-shown") || reduceMotion) { clip.classList.remove("is-shown"); gone(); return; }
  clip.classList.remove("is-shown");
  setTimeout(gone, 400);
});
skipBtn.addEventListener("click", () => skipWalk && skipWalk());
// fade the whole stage to black and back
const dip = (on) => new Promise((resolve) => {
  fade.classList.toggle("is-on", on);
  setTimeout(resolve, 450);
});
const say = (text) => { statusBox.textContent = text || ""; statusBox.hidden = !text; };

// ---------- the programme ----------
const days = [...new Set(talks.filter((t) => t.start).map((t) => dayKey(t.start)))].sort();
const startsOn = (d) => [...new Set(talks.filter((t) => t.start && dayKey(t.start) === d).map((t) => t.start))].sort();
const inSlot = (s) => talks.filter((t) => t.start === s).sort((a, b) => (roomNo(a) || 99) - (roomNo(b) || 99));
let day = days.includes("2026-10-07") ? "2026-10-07" : days[0];
let slot = startsOn(day)[0];                                   // the day from its start
let query = "";
const blob = (t) => [t.title, ...t.speakers.map((s) => s.name), t.room, t.track, t.s && t.s.tldr, ...((t.s && t.s.tech) || []), ...(t.keywords || [])]
  .join(" ").toLowerCase();

// where a search term was found, as a short highlighted snippet (title matches need none)
function why(t, terms) {
  if (terms.every((w) => t.title.toLowerCase().includes(w))) return null;
  const s = t.s || {};
  const fields = [["Speaker", speakers(t)], ["Summary", [s.tldr, ...(s.summary || [])].filter(Boolean).join(" ")], ["Abstract", (t.abstract || []).join(" ")],
    ["Mentions", (s.tech || []).join(", ")], ["Topics", (t.keywords || []).join(", ")]];
  for (const [name, text] of fields) {
    const lower = text.toLowerCase(), w = terms.find((x) => lower.includes(x));
    if (!w) continue;
    const i = lower.indexOf(w);
    const a = i;                                                     // start at the match, so it's always in view
    if (name === "Mentions" || name === "Topics" || name === "Speaker") {        // lists: the matching item first, then whole items
      const items = text.split(/,\s*/), hit = items.find((x) => x.toLowerCase().includes(w));
      const more = items.length - 1;
      return el("span", { class: "why" }, el("b", { text: `${name}: ` }), el("mark", { text: hit }), more > 0 && name !== "Speaker" ? `, plus ${more}\u00a0other ${name === "Topics" ? "topics" : "tools"}` : "");
    }
    // a sentence from the summary: a few words before the match, the match, the rest of the line
    const word = text.slice(i).match(/^\S+/)[0].replace(/[,.;:)]$/, "");
    let from = Math.max(0, text.lastIndexOf(" ", Math.max(0, i - 24)));
    if (i - from > 30) from = i;
    return el("span", { class: "why is-quote" }, from > 0 ? "…" : "", text.slice(from, i).trimStart(), el("mark", { text: word }), text.slice(i + word.length, i + word.length + 90));
  }
  return null;
}
function card(t, { when: showWhen = null, terms = null } = {}) {
  const n = roomNo(t), on = walkable.has(n);
  const label = showWhen === "day" ? `${fShort.format(new Date(t.start))}, ${fTime.format(new Date(t.start))}` : showWhen === "time" ? fTime.format(new Date(t.start))
    : /^BOF/.test(t.room || "") ? "Downstairs" : typeLabel(t);
  const hint = terms && why(t, terms);
  return el("button", { class: `card${on ? "" : " is-off"}`, type: "button", onclick: () => goTalk(t), onpointerenter: () => warm(n), onfocus: () => warm(n),
      "aria-label": [t.title, speakers(t), t.room, showWhen ? when(t) : null, on ? "walks you to your seat" : null].filter(Boolean).join(", ") },
    el("span", { class: "room" }, n ? el("span", { class: "where" }, el("small", { text: "Room" }), el("b", { text: String(n) })) : el("span", { class: "where" }, ...(/^(\S+) (\d+)$/.test(t.room || "") ? [el("small", { text: t.room.split(" ")[0] }), el("b", { text: t.room.split(" ")[1] })] : [el("b", { class: "is-text", text: t.room || "Room TBC" })])),
      el("span", { class: "label", text: label })),
    el("span", { class: "title", text: t.title }),
    el("span", { class: "who", text: speakers(t) }),
    hint);
}

function programme(tall) {
  const search = el("input", { class: "search", type: "search", placeholder: tall ? "Search talks, speakers, topics" : "Search talks", "aria-label": "Search all talks", value: query });
  const dayRow = el("div", { class: "strip days", role: "group", "aria-label": "Day" });
  const timeRow = el("div", { class: "strip times", role: "group", "aria-label": "Start time" });
  const nav = el("div", { class: "nav" }, tall ? dayRow : null, timeRow);
  const body = el("div", { class: "slot" });
  const panel = el("section", { class: `face prog is-lcd${tall ? " is-tall" : ""}`, "aria-label": "Programme" },
    el("div", { class: "prog-head" },
      el("h1", { class: "brand", "aria-label": "Devoxx Belgium 2026, 5 to 9 October" }, el("span", {}, "DEVOX", el("span", { class: "x", text: "X" })),
        el("small", { text: `Belgium 2026: ${window.DEVOXX.talks.length} talks, summarised` })),
      tall ? null : dayRow,
      search),
    nav, body,
    el("div", { class: "prog-foot" }, el("a", { class: "textlink is-foot", href: "../", text: "Text version of every talk" })));

  function draw() {
    dayRow.textContent = ""; timeRow.textContent = ""; body.textContent = "";
    const terms = query.split(/\s+/).filter(Boolean);
    nav.hidden = terms.length > 0;
    if (terms.length) {
      const hits = talks.filter((t) => terms.every((w) => blob(t).includes(w))).sort((a, b) => (a.start || "").localeCompare(b.start || ""));
      put(body, el("div", { class: "slot-head is-plain" },
          el("span", { text: `${hits.length} ${hits.length === 1 ? "talk matches" : "talks match"} “${query}”, in programme order` })),
        hits.length ? el("div", { class: "cards scroller", tabindex: "0", "aria-label": "Search results" }, hits.map((t) => card(t, { when: "day", terms })))
          : el("p", { class: "empty", text: "Nothing matches. Try a speaker's surname or a tool, like Kotlin or Quarkus." }));
      if (face) { for (const s of panel.querySelectorAll(".scroller")) watchScroll(s); requestAnimationFrame(() => fitCards(panel)); }
      return;
    }
    for (const d of days) {
      dayRow.append(el("button", { class: "pill", type: "button", text: fShort.format(new Date(startsOn(d)[0])), "aria-pressed": String(d === day),
        onclick: () => { day = d; slot = startsOn(d)[0]; draw(); } }));
    }
    for (const s of startsOn(day)) {
      timeRow.append(el("button", { class: "pill", type: "button", text: fTime.format(new Date(s)), "aria-pressed": String(s === slot),
        onclick: () => { slot = s; draw(); } }));
    }
    const here = inSlot(slot);
    // a short slot leaves room for what's on next: fill the screen with the following talks, each with its time
    const later = talks.filter((t) => t.start && dayKey(t.start) === day && t.start > slot).sort((a, b) => a.start.localeCompare(b.start) || (roomNo(a) || 99) - (roomNo(b) || 99));
    // laptops: one full row of four after the slot's own row, so nothing is cut at the bottom of the screen
    const fill = here.length < (tall ? 4 : 4) ? later.slice(0, tall ? 6 - here.length : 4) : [];
    const cards = el("div", { class: `cards scroller${tall ? "" : fill.length ? " is-packed" : " is-exact"}`, tabindex: "-1" },
      here.map((t) => {
        const c = card(t, { when: fill.length ? "time" : null });
        if (fill.length) c.classList.add(here.length === 1 ? "is-now-wide" : "is-now");   // a lone talk takes the whole row
        if (fill.length && here.length === 1 && t.s && t.s.tldr) c.append(el("span", { class: "gist", text: t.s.tldr }));
        return c;
      }),
      fill.length ? el("div", { class: "later", text: "Later that day" }) : null,
      fill.map((t) => { const c = card(t, { when: "time" }); c.classList.add("is-later"); return c; }));
    put(body, el("div", { class: "slot-head" }, el("b", { text: fTime.format(new Date(slot)) }),
        el("span", { text: tall ? `${here.length} ${here.length === 1 ? "session" : "sessions"}, ${fShort.format(new Date(slot))} Oct`
          : `${fDayLong.format(new Date(slot))}, ${here.length} ${here.length === 1 ? "session. Choose it to read its summary." : "sessions. Pick one to read its summary."}` })),
      cards);
    rove(dayRow); rove(timeRow);
    requestAnimationFrame(() => { fitCards(panel); centre(timeRow); if (tall) centre(dayRow); for (const s of panel.querySelectorAll(".strip, .scroller")) watchScroll(s); });
  }
  search.addEventListener("input", () => { query = search.value.trim().toLowerCase(); draw(); });
  draw();
  return panel;
}

// ---------- the talk ----------
const toSeconds = (at) => { const [m, sec] = String(at).split(":").map(Number); return (m || 0) * 60 + (sec || 0); };
function talkScreen(t, tall, onFloor, doorRoom = null) {
  const s = t.s || {};
  // the short summary is in the header; the tabs are the reading, the same on every device
  const tabs = [["points", "Key points"], ["monday", "To try"], ["chapters", "Chapters"], ["story", "Summary"]]
    .filter(([id]) => (id === "points" && s.keyPoints && s.keyPoints.length) || (id === "monday" && s.takeaways && s.takeaways.length)
      || (id === "chapters" && s.chapters && s.chapters.length && onFloor) || id === "story");
  const pane = el("div", { class: "pane scroller", tabindex: "0", "aria-label": "Talk details" });
  const tabRow = el("div", { class: "tabs", role: "group", "aria-label": "Talk details" });
  let playAt = null;
  const chapter = (c) => {
    const kids = [el("time", { text: c.at }), el("span", { text: c.title })];
    if (!t.videoId) return el("div", { class: "chapter" }, ...kids);
    if (!EMBED) return el("a", { class: "chapter", href: ytUrl(t, toSeconds(c.at)), target: "_blank", rel: "noopener" }, ...kids);
    return el("button", { class: "chapter", type: "button", onclick: () => playAt(toSeconds(c.at)) }, ...kids);
  };
  const fill = (id) => {
    pane.textContent = "";
    if (id === "short") put(pane, el("p", { text: s.tldr }));
    if (id === "points") put(pane, el("ul", {}, s.keyPoints.map((p) => el("li", { text: p }))));
    if (id === "monday") put(pane, el("ol", {}, s.takeaways.map((p) => el("li", { text: p }))));
    if (id === "chapters") put(pane, el("div", {}, s.chapters.map(chapter)));
    if (id === "story") put(pane, (s.summary || t.abstract || []).map((p) => el("p", { text: p })));
    pane.scrollTop = 0;
    requestAnimationFrame(() => watchScroll(pane));
    for (const b of tabRow.children) b.setAttribute("aria-pressed", String(b.dataset.tab === id));
    if (tabRow.children.length) rove(tabRow);
  };
  for (const [id, label] of tabs) tabRow.append(el("button", { class: "pill", type: "button", "data-tab": id, text: label, onclick: () => fill(id) }));
  const main = el("div", { class: "talk-main" });
  const sideHead = el("div", { class: "side-head" }, tabRow);   // laptops: the tabs and the actions share a row
  const watch = () => t.videoId
    ? (EMBED && onFloor ? el("button", { class: "btn is-main", type: "button", text: "Play the recording", onclick: () => playAt(0) })
      : el("a", { class: "btn is-main", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" }))
    : null;
  const intro = () => {
    main.textContent = "";
    put(main,
      el("div", { class: "meta", text: [!onFloor && /^BOF/.test(t.room || "") ? `${t.room} (small room downstairs)` : t.room,
        whenShort(t), typeLabel(t), t.videoId ? null : "no recording yet"].filter(Boolean).map((x) => x.replace(/ /g, "\u00a0").replace(/-/g, "\u2011")).join(", ") }),
      el("h2", { text: t.title, style: `--title:${onFloor ? titleSize(t.title, 40, 30) : titleSize(t.title, 34, 26)}px;--title-s:${titleSize(t.title, 23, 19)}px` }),
      el("div", { class: "who-l", text: speakers(t, true) }),
      // laptops: the summary scrolls if it's long, so the buttons stay on the screen
      el("div", { class: "intro scroller" },
        s.tldr ? el("p", { class: "tldr", text: s.tldr }) : null,
        s.watchIf ? el("p", { class: "verdict" }, el("b", { text: "Worth it if " }), `${s.watchIf.replace(/^\p{Lu}/u, (c) => c.toLowerCase()).replace(/\.$/, "")}.`) : null),
      actions());
    for (const sc of main.querySelectorAll(".scroller")) watchScroll(sc);
  };
  function actions() {
    return el("div", { class: "actions" }, watch(), tall ? null : el("button", { class: "btn", type: "button", text: "Back to the programme", onclick: () => goHall() }),
      null);
  }
  playAt = (sec) => {
    const at = tall ? main : pane;                               // laptops: the recording takes the reading area
    at.textContent = "";
    if (!tall) for (const b of tabRow.children) b.setAttribute("aria-pressed", "false");
    put(at, tall ? el("div", { class: "meta", text: t.title }) : null,
      el("div", { class: "player" }, el("iframe", { src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${sec}`, title: t.title,
        allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true })),
      el("div", { class: "actions" }, el("button", { class: "btn", type: "button", text: "Close the recording", onclick: () => (tall ? intro() : fill(tabs[0][0])) }),
        tall ? el("button", { class: "btn", type: "button", text: "Back to the programme", onclick: () => goHall() }) : null));
  };
  intro();
  fill(tabs[0][0]);
  return el("section", { class: `face talk ${onFloor && !tall ? "is-projected" : "is-lcd"}${tall ? " is-tall" : ""}`, "aria-label": t.title },
    main, el("div", { class: "talk-side" }, tall ? tabRow : sideHead, pane),
    tall ? el("div", { class: "foot" }, el("span", { "aria-hidden": "true" }, "DEVOX", el("span", { class: "x", text: "X" })),
      el("button", { type: "button", text: "Back to the programme", onclick: () => goHall() })) : null);
}

// ---------- the seat, on laptops: the recording on the cinema screen, your notes on a laptop in your lap ----------
// The cinema screen carries the talk's recording, as big as the screen allows, with only the title, the speakers and why
// it's worth your time beside it. Everything else (the summary, what to try, the chapters to jump through the talk) is on
// a laptop on your lap: a separate picture laid over the room, like a first-person game draws the hands, so it can be
// placed for each window size without ever covering the recording. Open, it rises into the bottom of the view, the room
// tilted up a little to make room; closed, its lid (and the sticker on it) lies low and the screen is all yours; zoomed,
// it's lifted until its screen fills the window, the room dims behind, and the recording moves onto it.
// Keys: K play/pause, [ and ] previous/next chapter, F full screen, L open/close the laptop, Esc back out.
// The laptop's pictures and where things are in them, in art px (scripts/blender/build_laptop.py writes laptop.json, which
// publish_renders.py puts in shots.json as "laptop"): every picture is the same frame from the same eye, so open, closed
// and the frames between only move up or down. top: the lid's top edge; cut: where the view's bottom edge cuts the open
// laptop (cutShort on short windows: fewer keys, a bigger screen); bottom: the closed laptop's front edge.
const LAP = shots.laptop ? (() => {
  const L = shots.laptop, [tl, tr, bl] = L.screen, hingeCut = (f) => Math.min(L.h, L.open_cut + (f - 0.32) * (bl[1] - tl[1]));
  return { w: L.w, h: L.h, screen: [tl[0], tl[1], tr[0], bl[1]],
    open: { src: "media/laptop-open.webp", top: L.open_top, cut: L.open_cut, cutShort: hingeCut(0.1) },
    closed: { src: "media/laptop-closed.webp", top: L.closed_top, bottom: L.closed_cut || L.closed_bottom, box: L.closed_box },
    frames: Array.from({ length: L.frames || 0 }, (_, i) => `media/laptop-anim-${String(i).padStart(2, "0")}.webp`) };
})() : {   // a drawn stand-in until the render is in
  w: 1600, h: 1060, screen: [176, 26, 1424, 806],
  open: { src: "media/mock/laptop-open.svg", top: 0, cut: 1060, cutShort: 905 },
  closed: { src: "media/mock/laptop-closed.svg", top: 40, bottom: 560, w: 1600, h: 560, box: [70, 40, 1530, 518] },
  frames: [],
};
const $ = (id) => document.getElementById(id);
const tube = $("tube"), lap = $("lap"), lapArt = $("lapArt"), lapLid = $("lapLid"), seatbar = $("seatbar");
const MOVE = reduceMotion ? 0 : 650;                       // ms for the laptop and the view to move
const EASE = "cubic-bezier(.3, 0, .2, 1)";
let seat = null;   // { t, n, key, open, zoom, layout, cine, notes, player, timer, chapters }

// the chapters YouTube shows on the player's scrubber, so the laptop and the player agree; else the summary's own
function chaptersOf(t) {
  if (!t.videoId) return [];
  if (t.ytChapters && t.ytChapters.length > 1) return t.ytChapters.map(([sec, title]) => ({ sec, title }));
  return ((t.s && t.s.chapters) || []).map((c) => ({ sec: toSeconds(c.at), title: c.title }));
}
const clock = (sec) => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor(sec / 60) % 60, x = String(sec % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`; };

function seatLayout(st) {
  const W = stage.clientWidth, H = stage.clientHeight, key = st.key;
  const { iw, ih } = framing(key);
  const q = shots[key].overlay.screen, xs = q.map((p) => p[0] * iw), ys = q.map((p) => p[1] * ih);
  const sx0 = Math.min(...xs), sx1 = Math.max(...xs), sy0 = Math.min(...ys), sy1 = Math.max(...ys);
  const aspect = (sx1 - sx0) / (sy1 - sy0);
  const pad = Math.round(Math.min(28, Math.max(12, H * 0.03)));
  const o = LAP.open, c = LAP.closed, ow = LAP.screen[2] - LAP.screen[0], oh = LAP.screen[3] - LAP.screen[1];
  // the laptop's screen: about a third of the height (more on short windows, where it would be cramped), at most 60% wide
  const short = H < 820;                                    // short windows: less keyboard, more screen
  const cut = short ? o.cutShort : o.cut;                   // where the view's bottom edge cuts the open laptop
  const k = Math.min(H * (short ? 0.42 : 0.36) / oh, W * 0.6 / ow);
  const lidTop = H - (cut - o.top) * k;
  const overlap = Math.round(H * 0.015);                    // the lid may cover a sliver of the screen's foot
  let sh = lidTop + overlap - pad, sw = sh * aspect;
  if (sw > W * 0.95) { sw = W * 0.95; sh = sw / aspect; }
  const s = sw / (sx1 - sx0);
  // open: the screen in the space above the lid; closed: you look up, the screen in the middle of what the lid leaves
  const openTop = pad + Math.max(0, (lidTop + overlap - pad - sh) / 2);
  const top = openTop;                                      // the screen stays put whether the lid is open or not
  const left = (W - sw) / 2;
  const frame = { iw, ih, s, ox: left - sx0 * s, oy: top - sy0 * s };
  let lapBox;
  if (st.zoom) {                                            // its screen fills the window, the lid just past the edges
    const m = H < 820 ? 8 : 14;                                    // a sliver of bezel and lid: you leaned in, it is still a laptop
    const dw = Math.min(W - 2 * m, (H - 2 * m) * ow / oh), kz = dw / ow;
    lapBox = { x: W / 2 - (LAP.screen[0] + ow / 2) * kz, y: H / 2 - (LAP.screen[1] + oh / 2) * kz, w: LAP.w * kz, h: LAP.h * kz, k: kz };
  } else if (st.open) lapBox = { x: W / 2 - (LAP.screen[0] + ow / 2) * k, y: H - cut * k, w: LAP.w * k, h: LAP.h * k, k };
  else if (c.w) lapBox = { x: (W - c.w * k) / 2, y: H - c.bottom * k, w: c.w * k, h: c.h * k, k };   // the stand-in's own picture
  else lapBox = { x: W / 2 - (LAP.screen[0] + ow / 2) * k, y: H - c.bottom * k, w: LAP.w * k, h: LAP.h * k, k };
  // the recording keeps clear of the open lid, so its controls are never under it
  const cover = Math.max(0, Math.ceil(openTop + sh - lidTop));
  return { frame, screen: { x: left, y: top, w: sw, h: sh }, lap: lapBox, cover, W, H };
}

// the room (still, cut-out) moved from where object-fit puts it to the seat's framing (from: start at the walk's framing)
function frameRoom(key, ms, from = false) {
  const a = placed(key), b = fit(key), k = b.s / a.s;
  const tf = `translate(${b.ox - k * a.ox}px, ${b.oy - k * a.oy}px) scale(${k})`;
  if (from) {
    const f = framing(key), kf = f.s / a.s;
    for (const e of [plate, front]) { e.style.transition = ""; e.style.transformOrigin = "0 0"; e.style.transform = `translate(${f.ox - kf * a.ox}px, ${f.oy - kf * a.oy}px) scale(${kf})`; }
    plate.getBoundingClientRect();
  }
  for (const e of [plate, front]) {
    e.style.transformOrigin = "0 0";
    e.style.transition = ms ? `transform ${ms}ms ${EASE}, opacity .35s ease, filter ${ms}ms ease` : "";
    e.style.transform = tf;
  }
}
const resetRoom = () => { for (const e of [plate, front, clip]) { e.style.transition = ""; e.style.transform = ""; } stage.classList.remove("is-reading"); };

// the lid opening or closing: the rendered frames in turn while the laptop moves (else a straight swap)
const lidFrames = [];
function preloadLid() {
  if (lidFrames.length || !LAP.frames.length) return;
  for (const src of [...LAP.frames, LAP.open.src, LAP.closed.src]) { const im = new Image(); im.src = src; lidFrames.push(im); }
}
function playLid(open, ms) {
  const fr = LAP.frames, end = open ? LAP.open.src : LAP.closed.src;
  if (!ms || !fr.length) { lapArt.src = end; return; }
  const t0 = performance.now();
  const step = (now) => {
    const p = Math.min(1, (now - t0) / ms), e = 0.5 - 0.5 * Math.cos(Math.PI * p);
    const i = Math.round((open ? e : 1 - e) * (fr.length - 1));
    if (p < 1) { lapArt.src = fr[i]; requestAnimationFrame(step); } else lapArt.src = end;
  };
  requestAnimationFrame(step);
}

// FLIP: put the laptop where it now belongs, and animate from where it was
function moveLaptop(box, ms, from = null) {
  const was = from || (lap.hidden ? null : lap.getBoundingClientRect());
  Object.assign(lap.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px`, height: `${box.h}px`, transition: "", transform: "" });
  lap.hidden = false;
  if (!ms || !was) return;
  lap.style.transformOrigin = "0 0";
  lap.style.transform = `translate(${was.left - box.x}px, ${was.top - box.y}px) scale(${was.width / box.w})`;
  lap.getBoundingClientRect();
  lap.style.transition = `transform ${ms}ms ${EASE}`;
  lap.style.transform = "";
}

// ----- the recording: our own poster until you press play, then one YouTube player for the visit, moved (never reloaded)
// between the cinema screen and the laptop. YouTube's own chrome is off (its title bar, pause overlay and "more videos"
// made the screen busy and doubled the laptop's controls): the laptop has the transport, and a click on the picture
// plays or pauses it, a double click makes it full screen, and pausing shows our own quiet overlay.
let ytApi = null;
const loadYT = () => ytApi || (ytApi = new Promise((resolve, reject) => {
  window.onYouTubeIframeAPIReady = () => resolve(window.YT);
  const sc = el("script", { src: "https://www.youtube.com/iframe_api" });
  sc.onerror = () => { ytApi = null; reject(new Error("blocked")); };
  document.head.append(sc);
  setTimeout(() => { if (!window.YT || !window.YT.Player) { ytApi = null; reject(new Error("timeout")); } }, 7000);
}));
function playerFailed(t) {
  if (!seat || seat.t !== t) return;
  seat.starting = false; seat.failed = true;
  clearTimeout(seat.readyTimer);
  tube.textContent = "";
  tube.append(el("div", { class: "tube-error", role: "alert" },
    el("b", { text: "The recording won't play here" }),
    el("span", { text: "Something (a content blocker, or the network) kept YouTube's player from loading. The chapters on your laptop open on YouTube instead." }),
    el("div", { class: "actions" },
      el("button", { class: "btn", type: "button", text: "Try again", onclick: () => retryPlayer() }),
      el("a", { class: "btn is-main", href: ytUrl(t, Math.floor(seat.startAt || 0)), target: "_blank", rel: "noopener", text: "Watch on YouTube ↗" }))));
  if (seat.notesPanel) seat.notesPanel.classList.add("is-failed");
  for (const l of document.querySelectorAll(".notes .jump-label")) l.textContent = "Jump to a part: it opens on YouTube";
  tick();
}
function retryPlayer() {
  if (!seat) return;
  const at = seat.startAt || 0;
  if (seat.player && seat.player.destroy) seat.player.destroy();
  Object.assign(seat, { failed: false, starting: false, ready: false, player: null });
  ytApi = null;
  if (seat.notesPanel) seat.notesPanel.classList.remove("is-failed");
  if (seat.notes) tick();
  for (const l of document.querySelectorAll(".notes .jump-label")) l.textContent = "Jump to a part: it plays on the big screen";
  tube.textContent = "";
  jumpTo(at);
}
function posterOn(t) {
  if (!t.videoId || !EMBED) { tube.hidden = true; return; }
  const img = el("img", { alt: "", src: `https://i.ytimg.com/vi/${t.videoId}/maxresdefault.jpg` });
  img.onerror = () => { img.onerror = null; img.src = `https://i.ytimg.com/vi/${t.videoId}/hqdefault.jpg`; };
  tube.textContent = "";
  tube.append(el("button", { class: "poster", type: "button", "aria-label": `Play the recording of ${t.title}`, "aria-keyshortcuts": "K", onclick: () => jumpTo(0) },
    img, el("span", { class: "play" }, el("i", { "aria-hidden": "true" }), "Play the talk", t.duration ? el("small", { text: `${t.duration} min` }) : null)));
  tube.hidden = false;
}
// the recording full screen (the browser's own): the picture alone, with a slim bar of our controls that shows when
// the mouse moves (YouTube's are off), Esc or the same button to come back
const FS_ICON = `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
function videoFullscreen() {
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  if (!seat || !seat.t.videoId || !EMBED || seat.failed || !tube.requestFullscreen) return;
  if (!seat.player && !seat.starting) jumpTo(0);               // full screen before play: start it too
  tube.requestFullscreen().catch(() => {});
}
function tubeControls() {
  // a corner button on the picture, and the bar for full screen
  const scrub = el("div", { class: "scrub", role: "slider", tabindex: "0", "aria-label": "Position in the talk", "aria-valuemin": "0",
      onclick: (e) => { const L = playerLength(), r = scrub.getBoundingClientRect(); if (L) jumpTo((e.clientX - r.left) / r.width * L); },
      onkeydown: (e) => { const d = { ArrowLeft: -10, ArrowRight: 10, PageDown: -60, PageUp: 60 }[e.key]; if (d) { e.preventDefault(); seekBy(d); } } },
    el("div", { class: "scrub-fill" }), el("div", { class: "scrub-ticks", "aria-hidden": "true" }));
  const bar = el("div", { class: "tube-bar", role: "group", "aria-label": "Recording" },
    el("button", { class: "icon step is-prev", type: "button", "aria-keyshortcuts": "[", "aria-label": "Previous chapter", onclick: () => stepChapter(-1) }, el("span", { class: "ico", "aria-hidden": "true" })),
    el("button", { class: "toggle", type: "button", "aria-keyshortcuts": "K", onclick: () => playPause() }, el("span", { class: "glyph" })),
    el("button", { class: "icon step is-next", type: "button", "aria-keyshortcuts": "]", "aria-label": "Next chapter", onclick: () => stepChapter(1) }, el("span", { class: "ico", "aria-hidden": "true" })),
    scrub,
    el("span", { class: "now-time" }),
    el("span", { class: "now-text" }),
    el("button", { class: "icon cc", type: "button", "aria-keyshortcuts": "C", "aria-pressed": "false", "aria-label": "Captions", onclick: () => toggleCaptions() }, "CC"),
    el("button", { class: "icon mute", type: "button", "aria-keyshortcuts": "M", "aria-label": "Mute", onclick: () => toggleMute() }),
    el("button", { class: "icon fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Leave full screen", onclick: () => videoFullscreen() }));
  bar.querySelector(".fs").innerHTML = FS_ICON;
  const corner = el("button", { class: "tube-fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Video full screen", title: "Video full screen  F", onclick: () => videoFullscreen() });
  corner.innerHTML = FS_ICON;
  return [corner, bar];
}
let barTimer = 0;
tube.addEventListener("mousemove", () => {
  if (document.fullscreenElement !== tube) return;
  tube.classList.add("is-awake");
  clearTimeout(barTimer);
  barTimer = setTimeout(() => tube.classList.remove("is-awake"), 2500);
});
document.addEventListener("fullscreenchange", () => {
  tube.classList.toggle("is-full", document.fullscreenElement === tube);
  tube.classList.add("is-awake");
  clearTimeout(barTimer);
  barTimer = setTimeout(() => tube.classList.remove("is-awake"), 2500);
  setTimeout(() => { placeTube(); tick(); }, 60);
});
function jumpTo(sec) {
  if (!seat || !seat.t.videoId) return;
  if (seat.failed || !EMBED) { window.open(ytUrl(seat.t, Math.floor(sec)), "_blank", "noopener"); return; }
  const p = seat.player;
  seat.waitSince = performance.now();
  if (p && p.seekTo) { p.seekTo(sec, true); p.playVideo(); setTimeout(tick, 150); return; }
  if (seat.starting) { seat.startAt = sec; return; }
  seat.starting = true; seat.startAt = sec;
  const t = seat.t, host = el("div", { class: "yt" });
  tube.append(host, ...tubeControls(), el("div", { class: "tube-catch", "aria-hidden": "true", onclick: () => playPause(), ondblclick: () => videoFullscreen() }),
    el("div", { class: "tube-paused is-loading" }, el("button", { class: "resume", type: "button", tabindex: "-1", onclick: () => playPause() },
      el("i", { "aria-hidden": "true" }), el("span", { class: "resume-text", text: "Loading…" }))));
  const poster0 = tube.querySelector(".poster"); if (poster0) poster0.remove();
  seat.readyTimer = setTimeout(() => { if (seat && seat.t === t && !seat.ready) playerFailed(t); }, 10000);
  tick();
  loadYT().then((YT) => {
    if (!seat || seat.t !== t) return;
    seat.player = new YT.Player(host, {
      videoId: t.videoId, host: "https://www.youtube-nocookie.com",
      playerVars: { rel: 0, playsinline: 1, autoplay: 1, controls: 0, disablekb: 1, fs: 0, iv_load_policy: 3, cc_load_policy: 0,
        start: Math.floor(seat.startAt), origin: location.origin },
      events: {
        onReady: (e) => {
          const f = tube.querySelector("iframe");
          if (f) { f.title = `Recording: ${t.title}`; f.tabIndex = -1; }   // the laptop has the controls; the picture isn't a tab stop
          if (seat.startAt) e.target.seekTo(seat.startAt, true);
          e.target.playVideo();
          seat.ready = true;
          clearTimeout(seat.readyTimer);
          tick();
        },
        onStateChange: () => tick(),
        onError: () => playerFailed(t),
      },
    });
  }).catch(() => playerFailed(t));
}
const playerTime = () => { const p = seat && seat.player; return p && p.getCurrentTime ? p.getCurrentTime() : null; };
const playerLength = () => { const p = seat && seat.player; return Math.round((p && p.getDuration && p.getDuration()) || (seat && seat.t.videoLength) || 0); };
function playPause() {
  const p = seat && seat.player;
  if (!p || !p.getPlayerState) { jumpTo(0); return; }
  if (p.getPlayerState() === 1) p.pauseVideo(); else p.playVideo();
  setTimeout(tick, 150);
}
function seekBy(d) { const sec = playerTime(); if (sec != null) jumpTo(Math.max(0, Math.min(playerLength() - 1, sec + d))); }
function toggleMute() {
  const p = seat && seat.player;
  if (!p || !p.isMuted) return;
  if (p.isMuted()) p.unMute(); else p.mute();
  setTimeout(tick, 100);
}
function toggleCaptions() {
  const p = seat && seat.player;
  if (!p || !p.loadModule) return;
  seat.cc = !seat.cc;
  if (seat.cc) { p.loadModule("captions"); p.setOption("captions", "track", { languageCode: "en" }); } else p.unloadModule("captions");
  tick();
}
// the tube sits over whichever slot is showing: the cinema screen's, or the laptop's when zoomed
function placeTube(ms = 0) {
  if (!seat || tube.hidden) return;
  const host = seat.zoom ? seat.notes : seat.cine, slot = host && host.querySelector(".slot");
  if (!slot) { tube.classList.add("is-away"); return; }
  const r = slot.getBoundingClientRect(), st = stage.getBoundingClientRect();
  tube.style.transition = ms ? `transform ${ms}ms ${EASE}, opacity .25s ease` : "opacity .25s ease";
  Object.assign(tube.style, { width: `${Math.round(r.width)}px`, height: `${Math.round(r.height)}px`, transform: `translate(${Math.round(r.left - st.left)}px, ${Math.round(r.top - st.top)}px)` });
  tube.classList.toggle("is-on-laptop", seat.zoom);
  tube.classList.remove("is-away");
}

// ----- the cinema screen: the recording, and beside it what the talk is, who gives it and why it's worth your time
const nb = (x) => x.replace(/ /g, " ").replace(/-/g, "‑");
function cineScreen(t) {
  const s = t.s || {};
  const slot = t.videoId && EMBED ? el("div", { class: "slot", "aria-hidden": "true" })
    : el("div", { class: "slot is-poster" },
      t.videoId ? el("a", { class: "btn is-main", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" })
        : [el("b", { text: "No recording yet" }), el("span", { text: "Devoxx puts the talks on YouTube in the weeks after the conference. Your laptop has the notes, from the abstract." }),
          el("button", { class: "btn", type: "button", text: "Back to the programme", onclick: () => goHall() })]);
  return el("section", { class: "face cine is-projected", "aria-label": `${t.title}: the cinema screen` },
    el("div", { class: "cine-info" },
      el("div", { class: "meta", text: [t.room, whenShort(t), typeLabel(t)].filter(Boolean).map(nb).join(" · ") }),
      el("h2", { text: t.title }),
      el("p", { class: "who-l", text: speakers(t, true) }),
      s.watchIf ? el("p", { class: "verdict" }, el("b", { text: "Worth your time if " }), `${s.watchIf.replace(/^\p{Lu}/u, (c) => c.toLowerCase()).replace(/\.$/, "")}.`) : null),
    slot);
}
// the whole title and the reason always show: the type steps down until the column holds them
function fitCine(panel) {
  const info = panel.querySelector(".cine-info"), h2 = info.querySelector("h2"), verdict = info.querySelector(".verdict");
  const over = () => info.scrollHeight > info.clientHeight + 1;
  // the recording: 16:9, the full height of the screen unless that leaves the column under 290 px (or a third)
  const cs = getComputedStyle(panel), slot = panel.querySelector(".slot");
  const ah = panel.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  const aw = panel.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - parseFloat(cs.columnGap || 26);
  const sh = Math.floor(Math.min(ah, (aw - Math.max(290, aw * 0.3)) * 9 / 16));
  if (slot.classList.contains("is-poster")) Object.assign(slot.style, { height: "auto", width: `${Math.round(Math.max(300, aw * 0.5))}px` });
  else Object.assign(slot.style, { height: `${sh}px`, width: `${Math.round(sh * 16 / 9)}px` });
  let size = Math.min(36, Math.max(24, Math.round(info.clientWidth / 10.5))), v = 16;
  h2.style.fontSize = `${size}px`;
  if (verdict) verdict.style.fontSize = "";
  while (over() && size > 24) h2.style.fontSize = `${--size}px`;          // the title keeps the lead...
  while (verdict && over() && v > 14) verdict.style.fontSize = `${--v}px`;   // ...the reason gives way first
  while (over() && size > 18) h2.style.fontSize = `${--size}px`;
}

// ----- the laptop: the notes, and below them the transport for the recording on the big screen: a scrubber with the
// chapters marked on it, play, previous/next chapter, the chapter playing (a menu of all of them), captions and sound
const key = (k) => el("kbd", { text: k, "aria-hidden": "true" });
// the overview's gist: two lines (one on a small laptop), and a "more" that shows the rest
function gist(text) {
  const p = el("p", { class: "lead is-short" }, el("span", { text }));
  const more = el("button", { class: "lead-more", type: "button", "aria-expanded": "false", text: "more ▾",
    onclick: () => { const open = p.classList.toggle("is-short"); more.textContent = open ? "more ▾" : "less ▴"; more.setAttribute("aria-expanded", String(!open)); } });
  return el("div", { class: "lead-wrap" }, p, more);
}
function notesScreen(t) {
  const s = t.s || {};
  const chapters = chaptersOf(t);
  const live = EMBED && t.videoId;
  // first: the gist and the chapters to jump to (when there are chapters)
  const tabs = [["overview", "Overview"], ["summary", "Summary"], ["points", "Key points"], ["monday", "To try"]]
    .filter(([id]) => (id === "overview" && chapters.length) || id === "summary" || (id === "points" && s.keyPoints && s.keyPoints.length)
      || (id === "monday" && s.takeaways && s.takeaways.length));
  const pane = el("div", { class: "pane scroller", tabindex: "0", "aria-label": "Notes" });
  const tabRow = el("div", { class: "tabs", role: "group", "aria-label": "Notes" });
  const chapterList = () => el("ol", { class: "chapters" }, chapters.map((c, i) => el("li", {},
    live ? el("button", { class: "chapter", type: "button", "data-i": i, onclick: () => { jumpTo(c.sec); menu.hidden = true; } }, el("time", { text: clock(c.sec) }), el("span", { text: c.title }))
      : el("a", { class: "chapter", href: ytUrl(t, c.sec), target: "_blank", rel: "noopener", "data-i": i }, el("time", { text: clock(c.sec) }), el("span", { text: c.title })))));
  const fill = (id) => {
    pane.textContent = "";
    if (id === "overview") put(pane, s.tldr ? gist(s.tldr) : null,
      el("p", { class: "label jump-label", text: live && !(seat && seat.failed) ? "Jump to a part: it plays on the big screen" : "Jump to a part: it opens on YouTube" }), chapterList());
    if (id === "summary") put(pane, s.tldr && !chapters.length ? el("p", { class: "lead", text: s.tldr }) : null, (s.summary || t.abstract || []).map((p) => el("p", { text: p })));
    if (id === "points") put(pane, el("ul", {}, s.keyPoints.map((p) => el("li", { text: p }))));
    if (id === "monday") put(pane, el("ol", {}, s.takeaways.map((p) => el("li", { text: p }))));
    pane.scrollTop = 0;
    for (const b of tabRow.children) b.setAttribute("aria-pressed", String(b.dataset.tab === id));
    rove(tabRow);
    requestAnimationFrame(() => { watchScroll(pane); if (seat) { seat.lastChapter = null; tick(); } });
  };
  for (const [id, label] of tabs) tabRow.append(el("button", { class: "pill", type: "button", "data-tab": id, text: label, onclick: () => fill(id) }));
  const menu = el("div", { class: "chapter-menu scroller", hidden: true, role: "dialog", "aria-label": "Chapters" }, chapters.length ? chapterList() : null);
  const ticks = el("div", { class: "scrub-ticks", "aria-hidden": "true" });
  const scrub = el("div", { class: "scrub", role: "slider", tabindex: "0", "aria-label": "Position in the talk", "aria-valuemin": "0", "aria-valuemax": "0", "aria-valuenow": "0",
      onclick: (e) => { const L = playerLength(), r = scrub.getBoundingClientRect(); if (L) jumpTo((e.clientX - r.left) / r.width * L); else jumpTo(0); },
      onkeydown: (e) => { const d = { ArrowLeft: -10, ArrowRight: 10, PageDown: -60, PageUp: 60 }[e.key]; if (d) { e.preventDefault(); seekBy(d); } } },
    el("div", { class: "scrub-fill" }), ticks);
  const now = live ? el("div", { class: "now" }, scrub,
    el("div", { class: "now-row" },
      el("div", { class: "transport", role: "group", "aria-label": "Recording" },
        chapters.length ? el("button", { class: "step is-prev", type: "button", "aria-keyshortcuts": "[", "aria-label": "Previous chapter", title: "Previous chapter  [", onclick: () => stepChapter(-1) }, el("span", { class: "ico", "aria-hidden": "true" })) : null,
        el("button", { class: "toggle", type: "button", "aria-keyshortcuts": "K", onclick: () => playPause() }, el("span", { class: "glyph" }), key("K")),
        chapters.length ? el("button", { class: "step is-next", type: "button", "aria-keyshortcuts": "]", "aria-label": "Next chapter", title: "Next chapter  ]", onclick: () => stepChapter(1) }, el("span", { class: "ico", "aria-hidden": "true" })) : null),
      chapters.length ? el("button", { class: "now-chapter", type: "button", "aria-haspopup": "dialog", "aria-expanded": "false",
        onclick: (e) => { menu.hidden = !menu.hidden; e.currentTarget.setAttribute("aria-expanded", String(!menu.hidden)); if (!menu.hidden) { seat.lastChapter = null; tick(); } } },
        el("span", { class: "now-num" }), el("span", { class: "now-text" }), el("span", { class: "caret", "aria-hidden": "true", text: "▾" })) : el("span", { class: "now-chapter is-plain" }),
      el("span", { class: "now-time" }),
      el("button", { class: "notes-btn retry", type: "button", text: "Try again", onclick: () => retryPlayer() }),
      el("button", { class: "icon cc", type: "button", "aria-keyshortcuts": "C", "aria-pressed": "false", "aria-label": "Captions", onclick: () => toggleCaptions() }, "CC"),
      el("button", { class: "icon mute", type: "button", "aria-keyshortcuts": "M", "aria-label": "Mute", onclick: () => toggleMute() }),
      (() => { const b = el("button", { class: "icon fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Video full screen", title: "Video full screen  F", onclick: () => videoFullscreen() }); b.innerHTML = FS_ICON; return b; })())) : null;
  const keysSheet = el("div", { class: "keys-sheet", hidden: true, role: "note" },
    el("b", { text: "Keys" }),
    el("dl", {}, [["K", "Play or pause"], ["[  ]", "Previous or next chapter"], ["← →", "Back or on 10 seconds"], ["C  M", "Captions, sound"],
      ["F", "Video full screen"], ["Z", "Zoom in on the laptop"], ["L", "Close or open the lid"], ["Esc", "Zoom out, or leave full screen"], ["?", "These keys"]]
      .filter(([k]) => live || !/^(K|\[|←|C)/.test(k)).map(([k, d]) => [el("dt", { text: k }), el("dd", { text: d })])),
    live ? el("p", { text: "Or double-click the picture for a full-screen video." }) : null);
  const keysBtn = el("button", { class: "notes-btn notes-keys", type: "button", "aria-label": "Keyboard shortcuts", "aria-expanded": "false", "aria-keyshortcuts": "?",
    onclick: () => toggleKeys() }, "Keys", key("?"));
  const toggleKeys = () => { keysSheet.hidden = !keysSheet.hidden; keysBtn.setAttribute("aria-expanded", String(!keysSheet.hidden)); };
  const panel = el("section", { class: `face notes${live ? "" : " is-offline"}`, "aria-label": "Your laptop: notes on the talk" },
    el("header", { class: "notes-top" },
      el("span", { class: "notes-app" }, el("i", { "aria-hidden": "true" }), "Notes"),
      el("span", { class: "notes-spacer" }),
      keysBtn,
      el("button", { class: "notes-btn notes-zoom", type: "button", "aria-keyshortcuts": "Z", onclick: () => setLaptop({ zoom: !seat.zoom }) }),
      el("button", { class: "notes-btn notes-close", type: "button", "aria-keyshortcuts": "L", onclick: () => setLaptop({ open: false }) }, "Close lid", key("L"))),
    keysSheet,
    el("div", { class: "notes-body" },
      el("div", { class: "notes-read" }, tabRow, el("div", { class: "pane-wrap" }, pane)),
      el("aside", { class: "notes-watch" }, live ? el("div", { class: "watch-head is-top", text: "The talk, moved here from the big screen" }) : null,
        live ? el("div", { class: "slot", "aria-hidden": "true" }) : null,
        chapters.length ? el("div", { class: "watch-head", text: "Chapters" }) : null,
        chapters.length ? el("div", { class: "pane-wrap is-list" }, el("div", { class: "scroller watch-list" }, chapterList())) : null)),
    menu, now);
  panel.fill = fill;
  panel.toggleKeys = toggleKeys;
  panel.ticks = (L) => {                       // the chapters marked on the scrubber, once the length is known
    if (ticks.dataset.len === String(Math.round(L)) || !L) return;
    ticks.dataset.len = String(Math.round(L));
    ticks.textContent = "";
    for (const c of chapters.slice(1)) ticks.append(el("i", { style: `left:${c.sec / L * 100}%` }));
  };
  fill(tabs[0][0]);
  return panel;
}
const chapterAt = (sec) => { let i = -1; seat.chapters.forEach((c, j) => { if (c.sec <= sec + 0.5) i = j; }); return i; };
function stepChapter(d) {
  const ch = seat.chapters, sec = playerTime();
  if (!ch.length) return;
  const i = sec == null ? -1 : chapterAt(sec);
  // back: to the start of this chapter, unless you're just past it
  const j = d < 0 && i >= 0 && sec - ch[i].sec > 3 ? i : Math.max(0, Math.min(ch.length - 1, i + d));
  jumpTo(ch[j].sec);
}
function tick() {
  if (!seat) return;
  const p = seat.player, sec = playerTime(), L = playerLength();
  const state = p && p.getPlayerState ? p.getPlayerState() : -1;
  const playing = state === 1 || state === 3;
  const started = sec != null && (sec > 0.5 || playing);
  const i = started ? chapterAt(sec) : -1;
  const ch = seat.chapters;
  // the picture: our paused overlay instead of YouTube's
  const paused = tube.querySelector(".tube-paused");
  if (paused) {
    // paused or finished: our quiet overlay; loading: say so; cued but not playing (a browser that wants a click): ask
    const loading = state === 3 || !seat.ready;
    const waiting = loading || (seat.waitSince && performance.now() - seat.waitSince > 1200 && (state === -1 || state === 5));
    paused.hidden = !(state === 2 || state === 0 || waiting);
    paused.classList.toggle("is-loading", loading);
    paused.querySelector(".resume-text").textContent = loading ? "Loading…" : state === 0 ? "Finished. Play it again"
      : state === 2 ? (i >= 0 ? `Paused: ${ch[i].title}` : "Paused") : "Press play (K)";
    if (state === 1 || state === 2) seat.waitSince = 0;
  }
  const tb = tube.querySelector(".tube-bar");
  if (tb) {
    const Lb = playerLength(), sb = tb.querySelector(".scrub");
    tb.querySelector(".glyph").textContent = playing ? "❚❚" : "▶";
    tb.querySelector(".toggle").setAttribute("aria-label", playing ? "Pause" : "Play");
    tb.querySelector(".now-time").textContent = Lb ? `${clock(sec || 0)} / ${clock(Lb)}` : "";
    tb.querySelector(".now-text").textContent = i >= 0 ? `${i + 1}/${ch.length}  ${ch[i].title}` : "";
    if (Lb) {
      tb.querySelector(".scrub-fill").style.width = `${Math.min(100, (sec || 0) / Lb * 100)}%`;
      const tk = sb.querySelector(".scrub-ticks");
      if (tk.dataset.len !== String(Lb)) { tk.dataset.len = String(Lb); tk.textContent = ""; for (const c of ch.slice(1)) tk.append(el("i", { style: `left:${c.sec / Lb * 100}%` })); }
      sb.setAttribute("aria-valuemax", String(Lb)); sb.setAttribute("aria-valuenow", String(Math.round(sec || 0)));
      sb.setAttribute("aria-valuetext", `${clock(sec || 0)} of ${clock(Lb)}`);
    }
    const mutedB = p && p.isMuted && p.isMuted(), mb = tb.querySelector(".mute");
    if (mb.dataset.muted !== String(!!mutedB)) {
      mb.dataset.muted = String(!!mutedB);
      mb.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M4 9h4l5-4v14l-5-4H4z"/>${mutedB
        ? '<path d="M16 9l5 6M21 9l-5 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        : '<path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'}</svg>`;
    }
    tb.querySelector(".cc").setAttribute("aria-pressed", String(!!seat.cc));
  }
  if (!lidBar.hidden && !lidPlay.hidden) { lidPlay.querySelector(".glyph").textContent = playing ? "❚❚ Pause" : "▶ Play"; lidPlay.setAttribute("aria-label", playing ? "Pause" : "Play"); }
  const n = seat.notes;
  if (!n) return;
  n.classList.toggle("is-playing", started);
  for (const c of n.querySelectorAll(".chapter")) {
    const on = Number(c.dataset.i) === i;
    c.classList.toggle("is-now", on);
    if (on) c.setAttribute("aria-current", "true"); else c.removeAttribute("aria-current");
  }
  if (i !== seat.lastChapter) {          // keep the playing chapter in view as the talk moves on
    const wasNull = seat.lastChapter === null;
    seat.lastChapter = i;
    if (!wasNull) seat.remounted = false;
    for (const c of n.querySelectorAll(".chapter.is-now")) {
      const box = c.closest(".scroller");
      if (!box || !c.offsetParent || (seat.remounted && box.classList.contains("pane"))) continue;
      const top = c.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop;
      const clear = box.clientHeight * 0.78;                 // above the fade at the bottom
      if (top < box.scrollTop) box.scrollTo({ top: top - 8, behavior: reduceMotion ? "auto" : "smooth" });
      else if (top + c.offsetHeight > box.scrollTop + clear) {
        // in the overview, scroll past the whole gist (never leave half of it under the tabs)
        const label = box.classList.contains("pane") && box.querySelector(".jump-label, .chapters");
        const want = top + c.offsetHeight - clear;
        box.scrollTo({ top: label ? Math.max(want, label.offsetTop - box.offsetTop - 4) : want, behavior: reduceMotion ? "auto" : "smooth" });
      }
    }
  }
  const now = n.querySelector(".now");
  if (!now) return;
  now.classList.toggle("is-failed", !!seat.failed);
  const text = now.querySelector(".now-text"), toggle = now.querySelector(".toggle"), time = now.querySelector(".now-time");
  if (seat.failed) {
    if (text) text.textContent = "Chapters open on YouTube";
    toggle.querySelector(".glyph").textContent = "Watch on YouTube ↗";
    toggle.setAttribute("aria-label", "Watch on YouTube");
    time.textContent = "";
    return;
  }
  if (text) text.textContent = i >= 0 ? ch[i].title : `All ${ch.length} chapters`;
  const num = now.querySelector(".now-num");
  if (num) num.textContent = i >= 0 ? `${i + 1}/${ch.length}` : "";
  toggle.querySelector(".glyph").textContent = seat.starting && !seat.ready ? "Loading…" : playing ? "❚❚ Pause" : "▶ Play";
  toggle.setAttribute("aria-label", playing ? "Pause" : "Play");
  time.textContent = "";
  if (L) put(time, el("span", { text: clock(sec || 0) }), el("span", { class: "t-len", text: ` / ${clock(L)}` }));
  const scrub = now.querySelector(".scrub");
  scrub.classList.toggle("is-ready", !!L);
  if (L) {
    n.ticks(L);
    now.querySelector(".scrub-fill").style.width = `${Math.min(100, (sec || 0) / L * 100)}%`;
    scrub.setAttribute("aria-valuemax", String(Math.round(L)));
    scrub.setAttribute("aria-valuenow", String(Math.round(sec || 0)));
    scrub.setAttribute("aria-valuetext", `${clock(sec || 0)} of ${clock(L)}${i >= 0 ? `, chapter ${i + 1}: ${ch[i].title}` : ""}`);
  }
  const muted = p && p.isMuted && p.isMuted();
  const mute = now.querySelector(".mute"), cc = now.querySelector(".cc");
  if (mute.dataset.muted !== String(!!muted)) {
    mute.dataset.muted = String(!!muted);
    mute.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M4 9h4l5-4v14l-5-4H4z"/>${muted
      ? '<path d="M16 9l5 6M21 9l-5 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
      : '<path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'}</svg>`;
  }
  mute.setAttribute("aria-label", muted ? "Sound off: turn it on" : "Mute");
  cc.setAttribute("aria-pressed", String(!!seat.cc));
  for (const b of [mute, cc]) { b.disabled = !seat.ready; b.title = seat.ready ? "" : "Once the talk plays"; }
}

// ----- open, close, zoom
function syncControls() {
  const { open, zoom } = seat;
  lidBar.hidden = lidHit.hidden = open;
  lidPlay.hidden = !seat.t.videoId || !EMBED;
  seatbar.hidden = zoom;                                    // full screen: the laptop's own header has the way out
  const n = seat.notesPanel;
  if (!n) return;
  const z = n.querySelector(".notes-zoom");
  z.textContent = zoom ? "Zoom out" : "Zoom in";
  z.append(el("kbd", { text: zoom ? "Esc" : "Z", "aria-hidden": "true" }));
  n.querySelector(".notes-close").hidden = zoom;
  n.classList.toggle("is-zoomed", zoom);
}
function mountCine() {
  mount(seat.cinePanel || (seat.cinePanel = cineScreen(seat.t)), seat.key, "screen");
  seat.cine = face.el;
  seat.cine.style.setProperty("--cover", `${seat.layout.cover}px`);
  fitCine(seat.cine);
}
function mountNotes() {
  if (seat.notes) { seat.notes.remove(); seat.notes = null; }
  if (!seat.open) return;
  const o = LAP, k = seat.layout.lap.k;
  const panel = seat.notesPanel || (seat.notesPanel = notesScreen(seat.t));
  const x0 = Math.floor(o.screen[0] * k) - 1, y0 = Math.floor(o.screen[1] * k) - 1;
  Object.assign(panel.style, { left: `${x0}px`, top: `${y0}px`,
    width: `${Math.ceil(o.screen[2] * k) + 1 - x0}px`, height: `${Math.ceil(o.screen[3] * k) + 1 - y0}px` });
  panel.classList.remove("is-off");
  panel.classList.toggle("is-compact", !seat.zoom && (LAP.screen[3] - LAP.screen[1]) * k < 380);
  panel.classList.toggle("is-tiny", !seat.zoom && (LAP.screen[3] - LAP.screen[1]) * k < 310);
  let told = false;
  try { told = localStorage.getItem("cinema-laptop-hint") === "1"; } catch (e) { /* no storage */ }
  panel.classList.toggle("is-told", told);
  panel.classList.toggle("is-short-zoom", seat.layout.H < 820 && seat.zoom);
  lap.append(panel);
  seat.notes = panel;
  syncControls();
  if (seat.zoom) fitWatch(panel);
  seat.remounted = true;
  for (const sc of panel.querySelectorAll(".strip, .scroller")) watchScroll(sc);
  seat.lastChapter = null;
  tick();
}
// full screen: the video as big as the column allows once every chapter row has its place
function fitWatch(panel) {
  const col = panel.querySelector(".notes-watch"), slot = col && col.querySelector(".slot"), list = col && col.querySelector(".watch-list");
  if (!slot) return;
  slot.style.width = "";
  if (!list) return;
  const over = list.scrollHeight - list.clientHeight;
  if (over > 0) slot.style.width = `${Math.max(col.clientWidth * 0.5, slot.clientWidth - over * 16 / 9 - 4)}px`;
}
let moving = false;
async function setLaptop(change, ms = MOVE) {
  if (!seat || moving) return;
  const next = { ...seat, ...change };
  if (next.zoom && !next.open) next.zoom = false;
  if (!next.open) next.zoom = false;
  if (next.open === seat.open && next.zoom === seat.zoom) return;
  moving = true;
  const opening = next.open !== seat.open;
  if (seat.notes) seat.notes.classList.add("is-off");     // the screen goes dark first
  if (next.zoom !== seat.zoom) tube.classList.add("is-away");
  await new Promise((r) => setTimeout(r, ms ? 140 : 0));
  Object.assign(seat, { open: next.open, zoom: next.zoom });
  seat.layout = seatLayout(seat);
  stage.classList.toggle("is-reading", seat.zoom);
  const np = seat.notesPanel, pressed = np && np.querySelector('.tabs [aria-pressed="true"]');
  if (seat.zoom && pressed && pressed.dataset.tab === "overview") { seat.tabBeforeZoom = "overview"; np.fill("summary"); }
  else if (!seat.zoom && seat.tabBeforeZoom) { if (pressed && pressed.dataset.tab === "summary") np.fill(seat.tabBeforeZoom); seat.tabBeforeZoom = null; }
  if (opening) playLid(seat.open, ms);
  frameRoom(seat.key, ms);
  if (face) { face.el.style.transition = ms ? `transform ${ms}ms ${EASE}` : ""; place(); }
  moveLaptop(seat.layout.lap, ms);
  if (!seat.zoom) placeTube(ms);
  if (seat.notes) { seat.notes.remove(); seat.notes = null; }
  syncControls();
  await new Promise((r) => setTimeout(r, ms));
  if (face) face.el.style.transition = "";
  mountNotes();
  placeTube();
  moving = false;
  // focus follows: into the laptop when it opens or zooms, onto the lid when it closes
  if (!seat.open) lapLid.focus({ preventScroll: true });
  else if (seat.notes && (opening || seat.zoom || change.zoom === false)) seat.notes.querySelector(seat.zoom || change.zoom === false ? ".notes-zoom" : ".tabs [aria-pressed=\"true\"]").focus({ preventScroll: true });
}
lapLid.addEventListener("click", () => setLaptop({ open: true }));
const lidPlay = $("lidPlay"), lidBar = $("lidBar"), lidHit = $("lidHit");
lidHit.addEventListener("click", () => setLaptop({ open: true }));
// the closed lid in the picture, as % of the art box: the click target, and the controls at its front
{
  const [x0, y0, x1, yb] = LAP.closed.box, y1 = Math.min(yb, LAP.closed.bottom), pc = (v, of) => `${v / of * 100}%`;
  Object.assign(lidHit.style, { left: pc(x0, LAP.closed.w || LAP.w), top: pc(y0, LAP.closed.h || LAP.h), width: pc(x1 - x0, LAP.closed.w || LAP.w), height: pc(y1 - y0, LAP.closed.h || LAP.h) });
  // just above the lid's far edge, centred: never on the logo or the sticker
  Object.assign(lidBar.style, { left: pc((x0 + x1) / 2, LAP.closed.w || LAP.w), top: pc(y0 - (LAP.closed.h || LAP.h) * 0.035, LAP.closed.h || LAP.h) });
}
lidPlay.addEventListener("click", () => playPause());
$("toProg").addEventListener("click", () => goHall());
addEventListener("keydown", (e) => {
  if (!seat || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) return;
  const k = e.key.length === 1 ? e.key.toLowerCase() : e.key, n = seat.notesPanel;
  const free = document.activeElement === document.body || document.activeElement === null;   // arrows belong to what has focus
  if (k === "k" || (k === " " && free)) { e.preventDefault(); playPause(); }
  else if (k === "[") stepChapter(-1);
  else if (k === "]") stepChapter(1);
  else if (k === "ArrowLeft" && free) seekBy(-10);
  else if (k === "ArrowRight" && free) seekBy(10);
  else if (k === "c") toggleCaptions();
  else if (k === "m") toggleMute();
  else if (k === "?" && n && seat.open) n.toggleKeys();
  else if (k === "f" || k === "v") videoFullscreen();
  else if (k === "z" && seat.open) setLaptop({ zoom: !seat.zoom });
  else if (k === "l") setLaptop({ open: !seat.open });
});

function relayoutSeat() {
  if (!seat || !seat.layout) return;
  seat.layout = seatLayout(seat);
  frameRoom(seat.key, 0);
  if (face) mountCine();
  moveLaptop(seat.layout.lap, 0);
  mountNotes();
  syncControls();
  placeTube();
}

// arriving: the walk ends on the still; the view tilts down a little and the laptop comes up into your lap, open
async function sitDown(t, n, key, withWalk) {
  if (withWalk) {
    say(`Walking to Room ${n}`);
    await playClip(walkClip(n));
  }
  await showStill(key);
  hideClip();
  say("");
  room = n; current = t;
  seat = { t, n, key, open: true, zoom: false, layout: null, cine: null, notes: null, notesPanel: null, cinePanel: null, player: null, timer: 0,
    chapters: chaptersOf(t), lastChapter: null, starting: false, startAt: 0 };
  seat.layout = seatLayout(seat);
  preloadLid();
  lapArt.src = LAP.open.src;
  const ms = withWalk ? MOVE + 250 : 0;
  frameRoom(key, ms, true);
  const b = seat.layout.lap;
  moveLaptop(b, ms, ms ? { left: b.x, top: seat.layout.H + 20, width: b.w } : null);
  seatbar.hidden = false;
  stage.classList.add("is-seated");
  if (ms) await new Promise((r) => setTimeout(r, ms));
  mountCine();
  mountNotes();
  posterOn(t);
  placeTube();
  seat.timer = setInterval(tick, 500);
  document.fonts.ready.then(() => { if (seat && seat.t === t && seat.cine) fitCine(seat.cine); });
  hintOnce();
}
// the first time: say the laptop is yours to use
function hintOnce() {
  let seen = false;
  try { seen = localStorage.getItem("cinema-laptop-hint") === "1"; } catch (e) { /* private window: show it */ }
  if (seen || !seat.notes) return;
  const hint = el("div", { class: "lap-hint", role: "status" },
    el("span", { text: seat.chapters.length && EMBED ? "Your laptop: the notes, and the chapters. Pick one and it plays on the big screen." : "Your laptop: the notes on this talk." }),
    el("button", { type: "button", "aria-label": "Dismiss", text: "×", onclick: () => dismiss() }));
  const dismiss = () => { hint.remove(); try { localStorage.setItem("cinema-laptop-hint", "1"); } catch (e) { /* fine */ } };   // the label stays this visit
  // beside the laptop's right edge, a quarter of the way down its screen
  Object.assign(hint.style, { left: `${(LAP.screen[2] + LAP.w * 0.035) / LAP.w * 100}%`, top: `${(LAP.screen[1] + (LAP.screen[3] - LAP.screen[1]) * 0.22) / LAP.h * 100}%` });
  lap.append(hint);
  seat.notes.addEventListener("click", dismiss, { once: true });
}
function leaveSeat() {
  if (!seat) return;
  clearInterval(seat.timer);
  clearTimeout(seat.readyTimer);
  if (seat.player && seat.player.destroy) seat.player.destroy();
  tube.textContent = ""; tube.hidden = true;
  lap.hidden = true; lidBar.hidden = lidHit.hidden = true;
  if (seat.notes) seat.notes.remove();
  for (const h of lap.querySelectorAll(".lap-hint")) h.remove();
  seatbar.hidden = true;
  stage.classList.remove("is-seated");
  seat = null;
  resetRoom();
}

// ---------- moving between the hall and a seat ----------
let room = null, current = null, busy = false;

async function toHall(withWalk) {
  // the way back is a fade through black, not the walk played backwards
  const dipped = withWalk && room && !reduceMotion;
  if (dipped) await dip(true);
  unmount();
  room = null; current = null;
  await showStill(shotKey("hall"));
  hideClip();
  mount(programme(shape === "phone"), shotKey("hall"), "programme");
  if (dipped) dip(false);
}

async function toSeat(t, withWalk) {
  const n = roomNo(t), key = shotKey(`seat-${n}`);
  unmount();
  if (shape === "laptop") return sitDown(t, n, key, withWalk);
  // phones: the walk pushes in on the door totem and the zoom carries on from it until the totem's screen fills the
  // phone; the walk then fades off the still underneath, and the totem lights up
  const zoomsIn = key.startsWith("door-phone");
  let zooming = null;
  if (withWalk) {
    say(`Walking to Room ${n}`);
    await playClip(walkClip(n), { until: walkClip(n) === `walk-${n}` && shape === "phone" ? doorTime(n) : null,
      nearEnd: zoomsIn && walkClip(n) !== `walk-${n}` ? [ZOOM_LEAD, () => { zooming = zoomTo(key, true, true); }] : null });
  }
  await showStill(key);
  if (zoomsIn && !zooming) zooming = zoomTo(key, true, withWalk && !reduceMotion);   // skipped, or no phone walk
  if (shape === "phone") await Promise.all([hideClip(), zooming]); else hideClip();
  say("");
  room = n; current = t;
  mount(talkScreen(t, shape === "phone", true, n), shotKey(`seat-${n}`), "screen");
}

async function toOffFloor(t) {   // no seat to walk to (BOFs downstairs): the summary stays on the hall screen
  unmount();
  await showStill(shotKey("hall"));
  current = t; room = null;
  mount(talkScreen(t, shape === "phone", false), shotKey("hall"), "programme");
}

const open = (t, withWalk) => (walkable.has(roomNo(t)) ? toSeat(t, withWalk) : toOffFloor(t));
function rerender() { if (current) open(current, false); else toHall(false); }

async function goTalk(t) {
  if (busy) return;
  busy = true;
  history.pushState({ talk: t.id }, "", `#talk-${t.id}`);
  await open(t, true);
  busy = false;
}
async function goHall() {
  if (busy) return;
  busy = true;
  history.pushState({}, "", location.pathname);
  await toHall(true);
  busy = false;
}

addEventListener("popstate", () => {
  if (busy) return;
  const m = /^#talk-(\d+)$/.exec(location.hash);
  const t = m && talks.find((x) => x.id === Number(m[1]));
  if (t) open(t, false); else toHall(false);
});
addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (skipWalk) skipWalk();
  else if (seat && seat.notesPanel && seat.notesPanel.querySelector(".keys-sheet:not([hidden]), .chapter-menu:not([hidden])")) {
    for (const p of seat.notesPanel.querySelectorAll(".keys-sheet, .chapter-menu")) p.hidden = true;
  }
  else if (seat && seat.zoom) setLaptop({ zoom: false });
  else if (current && !seat) goHall();
});

// ---------- start ----------
const deep = /^#talk-(\d+)$/.exec(location.hash);
const first = deep && talks.find((t) => t.id === Number(deep[1]));
if (first) await open(first, false); else await toHall(false);
loading.classList.add("is-done");

