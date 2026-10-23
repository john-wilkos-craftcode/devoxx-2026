// The rendered cinema: Blender stills and walk clips (scripts/blender/build_scene.py), with the programme and the
// talk as real HTML pinned onto the screens in them. shots.json says where each screen lands in each still; a CSS
// matrix3d (a projective transform) maps a fixed canvas onto that quad, like a real display, so text stays crisp,
// clickable and scrollable. Laptops get the landscape shots (the hall screen, the whole cinema screen); portrait
// viewports get the phone shots (a schedule totem in the hall, the middle of the cinema screen from the seat). What
// stands in front of the cinema screen (the "#DEVOXX" letters, the seats) is a separate cut-out laid over the talk.

import { inksMenu } from "./menu.js?v=25520f439f";

const TZ = "Europe/Brussels";
const fmt = (o) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...o });
const fTime = fmt({ hour: "2-digit", minute: "2-digit" });
const fDayLong = fmt({ weekday: "long", day: "numeric", month: "long" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const fYear = fmt({ year: "numeric" });   // apart: with the year in, en-GB puts a comma after the weekday
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
// which file of a walk plays (John 19/10: not one big mp4 each time). A final walk comes in AV1, HEVC and H.264
// (publish.py), each full size, smaller (-s) and as a glimpse (-g: its first and last half second, for walks off);
// H.264 has no full size. AV1 is the smallest; HEVC is what Apple devices without AV1 decode in hardware; H.264 is the
// fallback. A codec counts only if the browser says it plays it smoothly (Safari reports AV1 as not smooth on most
// Macs and iPhones, so those take HEVC).
const CODEC_TYPES = { av1: 'video/mp4; codecs="av01.0.08M.08"', hevc: 'video/mp4; codecs="hvc1.1.6.L120.90"' };
async function pickCodec() {
  for (const c of ["av1", "hevc"]) {
    if (!clip.canPlayType(CODEC_TYPES[c])) continue;
    try {
      const r = await Promise.race([
        navigator.mediaCapabilities.decodingInfo({ type: "file", video: { contentType: CODEC_TYPES[c], width: 1600, height: 900, bitrate: 1500000, framerate: 24 } }),
        new Promise((res) => setTimeout(() => res(null), 400)),
      ]);
      if (r && !(r.supported && r.smooth)) continue;
    } catch (e) { /* no MediaCapabilities: canPlayType's word goes */ }
    return c;
  }
  return "h264";
}
const codec = await pickCodec();
// the smaller files: on data saver or a slow network, and where the window shows the walk barely bigger than them
const lean = () => { const c = navigator.connection; return !!c && (c.saveData || /(^|-)(2g|3g)$/.test(c.effectiveType || "")); };
function clipSrc(name, glimpse = false) {
  const c = shots[name];
  if (!c || !c.codecs) return `media/${name}.mp4`;               // a walk from before the finals: one file
  const v = glimpse ? "-g" : codec === "h264" || lean() || stage.clientWidth * devicePixelRatio <= c.small[0] * 1.15 ? "-s" : "";
  return `media/${name}${v}${codec === "h264" ? "" : `.${codec}`}.mp4`;
}
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
// the walk back to the hall (forwards, never the walk played backwards) and the way in from outside, where rendered
const backClip = (n) => (shape === "phone" ? (shots[`back-phone-${n}`] ? `back-phone-${n}` : null) : shots[`back-${n}`] ? `back-${n}` : null);
const introClip = () => (shape === "phone" ? (shots["intro-phone"] ? "intro-phone" : null) : shots.intro ? "intro" : null);
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
  markPicture(face.key);
  const { iw, ih, s, ox, oy } = fit(face.key);
  const quad = shots[face.key].overlay[face.overlayName];
  face.el.style.transform = matrix3d(face.w, face.h, ordered(quad).map(([x, y]) => [ox + x * iw * s, oy + y * ih * s]));
}
function mount(panel, key, overlayName) {
  if (face) face.el.remove();
  const [mw, mh] = shots[key].size[overlayName];
  // laptops: a fixed canvas, like a real display; phones: laid out 1:1 for the width the totem takes on this screen
  let w = canvasFor(key);
  if (seat && key === seat.key) w = seat.layout.panelW;   // laid out for the screen as seen with the lid open: closed, it only grows   // the seat on laptops: laid out 1:1 for the screen's size
  else if (key.includes("phone") && !panel.classList.contains("inks")) {   // the menu keeps its 340 px design canvas
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
  for (const s of panel.querySelectorAll(".scroller")) watchScroll(s);
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
      if (!zoomed) alignStill(face.key);
      if (zoomed) { zoomTo(face.key, true); mount(face.el, face.key, face.overlayName); } else place();   // relaid for the new size
    }
  }, 180);
});

// fade the foot of anything that scrolls while there's more below
function watchScroll(s) {
  const update = () => s.classList.toggle("more-b", s.scrollTop + s.clientHeight < s.scrollHeight - 12);
  s.addEventListener("scroll", update, { passive: true });
  requestAnimationFrame(update);
}
// one tab stop per group of chips (the tabs): Tab lands on the chosen one, the arrow keys move along
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
// A still wider than its walk (inner: the laptop stills render wider than 16:9 so ultrawide windows fill, John 19/10)
// is moved from where object-fit puts it to where framing() frames it, so the walk's frame lines up and the rest fills
// the window; the seat then moves on from there (frameRoom)
function alignStill(key) {
  if (!(shots[key] && shots[key].inner)) return;
  const a = placed(key), f = framing(key), k = f.s / a.s;
  for (const e of [plate, front]) { e.style.transformOrigin = "0 0"; e.style.transform = `translate(${f.ox - k * a.ox}px, ${f.oy - k * a.oy}px) scale(${k})`; }
}
// the visible part of the picture (inside any bars), so the chips in its corners stay on the picture, not on black
function markPicture(key) {
  const f = fit(key), W = stage.clientWidth, H = stage.clientHeight, r = document.documentElement.style;
  r.setProperty("--pic-l", `${Math.max(0, f.ox)}px`);
  r.setProperty("--pic-t", `${Math.max(0, f.oy)}px`);
  r.setProperty("--pic-r", `${Math.max(0, W - (f.ox + f.iw * f.s))}px`);
}
const showStill = (key) => new Promise((resolve) => {
  const src = `media/${key}.jpg`;
  const done = () => {
    plate.src = src;
    const fr = shots[key] && shots[key].front;
    if (fr) { front.src = `media/${fr}.webp`; front.hidden = false; } else front.hidden = true;
    alignStill(key);
    markPicture(key);
    resolve();
  };
  const mode = framing(key).contain ? "contain" : "cover";
  plate.style.objectFit = front.style.objectFit = clip.style.objectFit = mode;
  if (plate.getAttribute("src") === src) { done(); return; }
  const img = new Image();
  img.onload = img.onerror = done;
  img.src = src;
});

// fetch a walk just before it's likely wanted, so the click plays at once without every walk being downloaded up
// front (a lot on a phone's data plan): the walk back once you sit down. The file is the one that will play (walks
// off: the glimpse).
const warmed = new Set();
function warmClip(name) {
  const src = name && shots[name] ? clipSrc(name, !walksOn) : null;
  if (!src || warmed.has(src)) return;
  warmed.add(src);
  const l = document.createElement("link");
  l.rel = "prefetch"; l.href = src;
  document.head.append(l);
}
// and the still the walk arrives on, so a walk cut short (skipped, or stalled on a slow network) lands at once
function warmStill(key) {
  for (const src of [`media/${key}.jpg`, shots[key]?.front && `media/${shots[key].front}.webp`]) {
    if (!src || warmed.has(src)) continue;
    warmed.add(src);
    new Image().src = src;
  }
}

// Walks on or off (John 19/10: the quick, swooping walk can make people queasy). Off: only a glimpse of each walk, its
// first and last half second with a dip through black between, so you still see where you set off and where you
// arrive. The button stays on screen during a walk (switching off mid-walk jumps to the end the same way); the
// choice is remembered in this browser, and starts off when the system asks for reduced motion.
const GLIMPSE = 0.5;                                    // s of a walk shown at each end with walks off
const walksBtn = document.getElementById("walks");
let walksOn = !reduceMotion;
try { const v = localStorage.getItem("cinema-walks"); if (v) walksOn = v === "on"; } catch (e) { /* no storage: the default */ }
const showWalks = () => {
  walksBtn.setAttribute("aria-pressed", String(walksOn));
  walksBtn.querySelector(".walks-state").textContent = walksOn ? "on" : "off";
  walksBtn.title = walksOn ? "Walk animations are on: switch them off for a short cut instead" : "Walk animations are off: switch them on for the full walk";
};
showWalks();
walksBtn.addEventListener("click", () => {
  walksOn = !walksOn;
  try { localStorage.setItem("cinema-walks", walksOn ? "on" : "off"); } catch (e) { /* this visit only */ }
  showWalks();
});

let skipWalk = null;
// a walk's first and last frames are the stills it leaves and lands on (scripts/photomatch/seams.py), so it swaps in and
// out without a fade (a fade over a moving camera showed a double image, John 19/10: "it should feel seamless"); a walk
// that didn't play to its end (skipped, stalled) still fades
let landed = false;
const SHARPEN = 0.55;      // s before a walk ends: the still behind it is the arrival's, sharp, by the time it shows
// the still a walk lands on, put behind it while it still plays (only its sides show, on a window wider than 16:9)
function prepPlate(key) {
  const src = `media/${key}.jpg`, img = new Image();
  img.src = src;
  img.decode().catch(() => {}).then(() => {
    plate.style.transition = "filter .5s ease";
    plate.src = src;
    alignStill(key);
  });
}
function playClip(name, { from = 0, until = null, nearEnd = null, cut = false, arrive = null } = {}) {
  landed = false;
  return new Promise((resolve) => {
    let watching = true, glimpsing = false, sharpened = false;
    // walks off: the glimpse file where there is one (a second long: its two halves either side of the dip)
    const short = !walksOn && !!shots[name]?.glimpse && !from && until == null;
    // never hang on a frozen frame: a walk that hasn't started after 3 s, or stalls for 1.2 s, cuts to the arrival
    let stall = setTimeout(() => watching && done(), 3000);
    const done = () => { watching = false; clearTimeout(stall); clip.onended = clip.onerror = clip.onwaiting = clip.onplaying = null;
      clip.pause();
      // not on screen yet (it never got going): stop its download, the arrival still needs the bandwidth
      if (!clip.classList.contains("is-shown")) { clip.removeAttribute("src"); clip.load(); }
      skipWalk = null; skipBtn.hidden = true; resolve(); };
    skipWalk = done;
    clip.onwaiting = () => { clearTimeout(stall); stall = setTimeout(() => watching && done(), 1200); };
    clip.onplaying = () => clearTimeout(stall);
    clip.src = clipSrc(name, short);
    clip.classList.remove("is-shown");
    clip.style.transition = cut ? "none" : "";     // cut: shown from its first frame (nothing under it to fade from)
    clip.hidden = false;
    clip.onended = () => { landed = until == null && clip.classList.contains("is-shown"); done(); };
    clip.onerror = done;                       // a missing clip is a cut, not a dead end
    const end = () => (until != null ? until : clip.duration);
    // walks off: past the opening, dip to black, jump to the last GLIMPSE seconds and come back up for the arrival
    const glimpse = async () => {
      glimpsing = true;
      const to = end() - GLIMPSE;
      if (!short && to - clip.currentTime < 0.25) return;  // the end is already near: just let it play
      clip.pause();
      await dip(true);
      if (!watching) { dip(false); return; }
      if (!short) await new Promise((r) => { clip.addEventListener("seeked", r, { once: true }); clip.currentTime = to; });
      clip.play().catch(() => {});
      dip(false);
    };
    // from its start, the walk's first frame is the still under it: shown the moment that frame is on screen, no fade
    // (a seek elsewhere fades in, as it starts on a different picture). The still's cut-out layer (plants, seats)
    // belongs to the still: off as the clip shows, else it hangs in front of the moving walk; showStill puts it back
    const swap = !from;
    const show = () => {
      if (!watching) return;
      clip.style.transition = swap || cut ? "none" : "";
      clip.classList.add("is-shown");
      setTimeout(() => {
        if (!watching) return;
        front.hidden = true;
        // the walk is 16:9: where a wider window shows past it, the still it set off from stays, blurred and dimmed
        // (an ambient edge, not black bars), and the arrival's still sharpens back in as the walk ends
        plate.style.transition = [plate.style.transition, "filter .5s ease"].filter(Boolean).join(", ");
        stage.classList.toggle("is-cut", cut);
        stage.classList.add("is-walking");
      }, swap || cut ? 0 : 360);
    };
    // (from the start: frame 0 is decoded and on screen, paused, before it plays, so a slow decoder can't swap in a
    // picture already under way)
    const play = () => clip.play().then(() => { if (!watching) return; skipBtn.hidden = false; if (!swap) show(); tick(); }).catch(done);
    const go = () => {
      if (!watching) return;
      if (from) clip.currentTime = from;
      if (!swap) { play(); return; }
      const ready = () => { if (!watching) return; show(); requestAnimationFrame(() => requestAnimationFrame(play)); };   // painted, then on
      if (clip.readyState >= 2) ready(); else clip.addEventListener("loadeddata", ready, { once: true });
    };
    // every frame while it plays: the stop point (until), the glimpse (walks off, also when switched off mid-walk) and
    // nearEnd: [seconds, fn], fn called that long before the clip ends
    let nearCalled = false;
    const tick = () => {
      if (!watching) return;
      if (until != null && clip.currentTime >= until) { clip.pause(); done(); return; }
      if ((short || !walksOn) && !glimpsing && clip.currentTime >= from + GLIMPSE) glimpse();
      if (nearEnd && !nearCalled && end() - clip.currentTime <= nearEnd[0]) { nearCalled = true; nearEnd[1](); }
      if (!sharpened && until == null && end() - clip.currentTime <= SHARPEN) {
        sharpened = true;
        if (arrive) prepPlate(arrive);
        stage.classList.remove("is-walking", "is-cut");
      }
      requestAnimationFrame(tick);
    };
    if (clip.readyState >= 1) go(); else clip.addEventListener("loadedmetadata", go, { once: true });
  });
}
// fade the clip out over the still that replaced it, then let it go
// (a walk that landed: at once, its last frame is the still, once that is decoded behind it)
const hideClip = () => new Promise((resolve) => {
  clip.pause();
  stage.classList.remove("is-walking", "is-cut");
  const gone = () => { clip.hidden = true; clip.removeAttribute("src"); clip.load(); resolve(); };
  if (clip.hidden || !clip.classList.contains("is-shown") || reduceMotion) { clip.classList.remove("is-shown"); gone(); return; }
  if (landed) {
    landed = false;
    plate.decode().catch(() => {}).then(() => { clip.style.transition = "none"; clip.classList.remove("is-shown"); gone(); });
    return;
  }
  clip.style.transition = "";
  clip.classList.remove("is-shown");
  setTimeout(gone, 400);
});
skipBtn.addEventListener("click", () => skipWalk && skipWalk());
// a walk in a tab you left ends there: back in the tab, you've arrived
document.addEventListener("visibilitychange", () => { if (document.hidden && skipWalk) skipWalk(); });
// fade the whole stage to black and back
const dip = (on) => new Promise((resolve) => {
  fade.classList.toggle("is-on", on);
  setTimeout(resolve, 450);
});
const say = (text) => { statusBox.textContent = text || ""; statusBox.hidden = !text; };

// ---------- the inks ----------
// The hall menu prints the week in three inks (menu.js, Three Inks); a talk's ink is its category, the same map as
// menu.js TRACK_INK. Everything about a talk away from the menu takes its accents from it: the strip at the head of the
// talk screen and the laptop's notes, the bars, the scrubber's fill, the Play buttons. Set on the root as --t-ink (the
// ink as a fill), --t-on (type on it: paper on blue) and --t-mark (the ink as a mark on paper: black for "paper" talks,
// which have no ink); cleared in the hall.
const TRACK_INK = {
  "Agentic Engineering & Tooling": "pink",
  "Java Language & Platform": "blue",
  "Architecture & Modernization": "yellow", "Development Practices": "yellow", "People, Practices & Career": "yellow",
};
const inkOf = (t) => TRACK_INK[t.track] || "paper";
function setInk(t) {
  if (t) document.documentElement.dataset.ink = inkOf(t);
  else delete document.documentElement.dataset.ink;
}
// The theatre is dark (John 23/10): at a seat (and walking to it) everything is printed on black stock; the hall, and a
// talk shown on the hall's screen, stay paper (cinema.css :root[data-room="theatre"])
function setRoom(theatre) {
  if (theatre) document.documentElement.dataset.room = "theatre";
  else delete document.documentElement.dataset.room;
}

// ---------- the talk ----------
const toSeconds = (at) => { const [m, sec] = String(at).split(":").map(Number); return (m || 0) * 60 + (sec || 0); };
function talkScreen(t, tall, onFloor) {
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
      el("h2", { text: t.title, style: `--title:${titleSize(t.title, 46, 32)}px;--title-s:${titleSize(t.title, 34, 25)}px` }),
      el("div", { class: "who-l", text: speakers(t, true) }),
      // laptops: the summary scrolls if it's long, so the buttons stay on the screen
      el("div", { class: "intro scroller" },
        s.tldr ? el("p", { class: "tldr", text: s.tldr }) : null,
        s.watchIf ? el("p", { class: "verdict" }, el("b", { text: "Worth it if" }), `${s.watchIf.replace(/\.$/, "")}.`) : null),
      actions());
    for (const sc of main.querySelectorAll(".scroller")) watchScroll(sc);
  };
  function actions() {
    return el("div", { class: "actions" }, watch(), tall ? null : el("button", { class: "btn is-back", type: "button", text: "Back to the programme", onclick: () => goHall() }));
  }
  playAt = (sec) => {
    const at = tall ? main : pane;                               // laptops: the recording takes the reading area
    at.textContent = "";
    if (!tall) for (const b of tabRow.children) b.setAttribute("aria-pressed", "false");
    put(at, tall ? el("div", { class: "meta", text: t.title }) : null,
      el("div", { class: "player" }, el("iframe", { src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${sec}`, title: t.title,
        allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true })),
      el("div", { class: "actions" }, el("button", { class: "btn", type: "button", text: "Close the recording", onclick: () => (tall ? intro() : fill(tabs[0][0])) }),
        tall ? el("button", { class: "btn is-back", type: "button", text: "Back to the programme", onclick: () => goHall() }) : null));
  };
  intro();
  fill(tabs[0][0]);
  // the head of the sheet: a strip in the talk's ink with where and when, as on the menu's talk card
  const where = [t.room, !onFloor && /^BOF/.test(t.room || "") ? "small room downstairs" : null, whenShort(t), typeLabel(t), t.videoId ? null : "no recording yet"];
  return el("section", { class: `face talk paper${tall ? " is-tall" : ""}`, "aria-label": t.title },
    el("div", { class: "talk-strip meta" }, where.filter(Boolean).map((x) => x.replace(/ /g, "\u00a0").replace(/-/g, "\u2011")).join(" \u00b7 ")),
    main, el("div", { class: "talk-side" }, tall ? tabRow : sideHead, pane),
    tall ? el("div", { class: "foot" }, el("span", { class: "foot-mark", "aria-hidden": "true" }, "Devoxx", el("span", { class: "be", text: " Belgium" }), " 2026"),
      el("button", { type: "button", class: "is-back", text: "Programme", "aria-label": "Back to the programme", onclick: () => goHall() })) : null);
}

// ---------- the seat, on laptops: the recording on the cinema screen, your notes on a laptop in your lap ----------
// The cinema screen carries the talk's recording, as big as the screen allows, with only the title, the speakers and why
// it's worth your time beside it. Everything else (the summary, what to try, the chapters to jump through the talk) is on
// a laptop on your lap: a separate picture laid over the room, like a first-person game draws the hands, so it can be
// placed for each window size without ever covering the recording. Open, it rises into the bottom of the view, the room
// tilted up a little to make room; closed, you look up: the recording fills the window, the lid's far edge (sticker
// peeking) and its Play / Open buttons at the foot, and opening it pulls the view back down; zoomed,
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
    closed: { src: "media/laptop-closed.webp", top: L.closed_top, bottom: L.closed_cut || L.closed_bottom, box: L.closed_box, sticker: L.sticker_box },
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
  const out = { frame, screen: { x: left, y: top, w: sw, h: sh }, panelW: Math.round(sw), lap: lapBox, cover, W, H };
  if (!st.open && !st.zoom && st.t.videoId && EMBED) {
    // Closed: you look up from your lap at the film. The view moves in until the recording fills the window, under the
    // way back to the programme; at the foot, the far edge of the lid (sticker and all) and its Play / Open buttons.
    // how much of the closed lid stays in view: its far edge down to just past the sticker (the buttons sit on it, beside)
    const stk = c.sticker || [0, 0, 0, c.top + 230];
    const lidShow = Math.round(Math.min(H * 0.2, Math.max(56, (stk[3] - c.top) * k + 12)));
    const vTop = 56, vBottom = H - lidShow - 12;               // clear of "← Programme" above and the lid below
    const vh = Math.min(vBottom - vTop, (W - 24) * 9 / 16), vw = vh * 16 / 9;
    const video = { x: (W - vw) / 2, y: vTop + (vBottom - vTop - vh) / 2, w: vw, h: vh };
    const zs = vh / Math.min(sy1 - sy0, (sx1 - sx0) * 9 / 16);   // the screen's scale: the picture at its full height
    const zw = (sx1 - sx0) * zs, zh = (sy1 - sy0) * zs, zl = W / 2 - zw / 2, zt = video.y - (zh - vh) / 2;
    Object.assign(out, { frame: { iw, ih, s: zs, ox: zl - sx0 * zs, oy: zt - sy0 * zs }, screen: { x: zl, y: zt, w: zw, h: zh }, video, cover: 0,
      lap: { ...lapBox, y: H - lidShow - c.top * k },
      // the Play / Open buttons on the lid, to the left of the sticker, halfway down the strip in view (css px in the laptop's box)
      lidBar: { right: (c.sticker ? stk[0] : LAP.w * 0.6) * k - 18, mid: c.top * k + lidShow / 2 } });
  }
  return out;
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
  setPip(false);                         // the box would hold only the error: it goes back (and the column with it)
  seat.starting = false; seat.failed = true;
  clearTimeout(seat.readyTimer);
  tube.textContent = "";
  tube.append(el("div", { class: "tube-error", role: "alert" },
    el("b", { text: "The recording won't play here" }),
    el("span", { text: "Something (a content blocker, or the network) kept YouTube's player from loading. The chapters on your laptop open on YouTube instead." }),
    el("div", { class: "actions" },
      el("button", { class: "btn is-retry", type: "button", text: "Try again", onclick: () => retryPlayer() }),
      el("a", { class: "btn is-main", href: ytUrl(t, Math.floor(seat.startAt || 0)), target: "_blank", rel: "noopener", text: "Watch on YouTube" }))));
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
    img, el("span", { class: "poster-title", "aria-hidden": "true" }, el("b", { text: t.title }), el("span", { text: speakers(t, true) })),
    el("span", { class: "play" }, el("i", { "aria-hidden": "true" }), "Play the talk", t.duration ? el("small", { text: `${t.duration} min` }) : null)));
  tube.hidden = false;
}
// the recording full screen (the browser's own): the picture alone, with a slim bar of our controls that shows when
// the mouse moves (YouTube's are off), Esc or the same button to come back
const FS_EXIT_ICON = `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
const FS_ICON = `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
function videoFullscreen() {
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  if (!seat || !seat.t.videoId || !EMBED || seat.failed || !tube.requestFullscreen) return;
  if (!seat.player && !seat.starting) jumpTo(0);               // full screen before play: start it too
  tube.requestFullscreen().catch(() => {});
}
const SPEED_ICON = `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M2.2 12a6 6 0 1 1 11.6 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M8 11.6l3.2-4.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
const PIP_ICON = `<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="11" rx="1.6" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="7.6" y="7.6" width="5.2" height="4.2" rx=".8" fill="currentColor"/></svg>`;
const iconButton = (attrs, svg) => { const b = el("button", { type: "button", ...attrs }); b.innerHTML = svg; return b; };
const speedButton = () => iconButton({ class: "icon speed", "aria-keyshortcuts": "< >", "aria-haspopup": "true", "aria-expanded": "false", "aria-label": "Playback speed",
  onclick: (e) => openSpeeds(e.currentTarget) }, SPEED_ICON);
const pipButton = () => iconButton({ class: "icon pip", "aria-keyshortcuts": "P", "aria-pressed": "false", "aria-label": "Picture in picture", title: "Picture in picture  P",
  onclick: () => setPip(!seat.pip) }, PIP_ICON);
function tubeControls() {
  // a corner button on the picture, and the bar that wakes on the pointer
  const scrub = el("div", { class: "scrub", role: "slider", tabindex: "0", "aria-label": "Position in the talk", "aria-valuemin": "0",
      onkeydown: (e) => { const d = { ArrowLeft: -10, ArrowRight: 10, PageDown: -60, PageUp: 60 }[e.key]; if (d) { e.preventDefault(); seekBy(d); } } },
    el("div", { class: "scrub-fill" }), el("div", { class: "scrub-ticks", "aria-hidden": "true" }));
  scrubber(scrub);
  const bar = el("div", { class: "tube-bar", role: "group", "aria-label": "Recording" },
    el("button", { class: "icon step is-prev", type: "button", "aria-keyshortcuts": "[", "aria-label": "Previous chapter", onclick: () => stepChapter(-1) }, el("span", { class: "ico", "aria-hidden": "true" })),
    el("button", { class: "toggle", type: "button", "aria-keyshortcuts": "K", onclick: () => playPause() }, el("span", { class: "glyph" })),
    el("button", { class: "icon step is-next", type: "button", "aria-keyshortcuts": "]", "aria-label": "Next chapter", onclick: () => stepChapter(1) }, el("span", { class: "ico", "aria-hidden": "true" })),
    scrub,
    el("span", { class: "now-time" }),
    el("span", { class: "now-text" }),
    el("button", { class: "icon cc", type: "button", "aria-keyshortcuts": "C", "aria-pressed": "false", "aria-label": "Captions", onclick: () => toggleCaptions() }, "CC"),
    el("button", { class: "icon mute", type: "button", "aria-keyshortcuts": "M", "aria-label": "Mute", onclick: () => toggleMute() }),
    speedButton(), pipButton(),
    el("button", { class: "icon fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Leave full screen", onclick: () => videoFullscreen() }));
  fsButton(bar);
  const corner = el("button", { class: "tube-fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Video full screen", title: "Video full screen  F", onclick: () => videoFullscreen() });
  corner.innerHTML = FS_ICON;
  return [corner, bar];
}
// A scrubber you can press anywhere along its strip and drag (John 19/10: only a click on the thin line counted), with
// the time and chapter under the pointer shown above it. The tip and the fill follow the pointer; the seek happens on
// release. The tip lives in the bar (or the laptop's screen), clear of the bar's clipped strip.
function scrubber(scrub) {
  const tip = el("div", { class: "scrub-tip", hidden: true, "aria-hidden": "true" });
  let dragging = false;
  const share = (e) => { const r = scrub.getBoundingClientRect(); return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); };
  const show = (e) => {
    const L = playerLength(), host = scrub.closest(".tube-bar, .face.notes");
    if (!L || !host || !seat) { tip.hidden = true; return; }
    const sec = share(e) * L, i = seat.chapters.length ? chapterAt(sec) : -1;
    tip.textContent = "";
    put(tip, el("b", { text: clock(sec) }), i >= 0 ? el("span", { text: seat.chapters[i].title }) : null);
    if (tip.parentNode !== host) host.append(tip);
    tip.hidden = false;
    // in the host's own px (the tube is scaled while it moves), kept inside it
    const h = host.getBoundingClientRect(), k = h.width / host.offsetWidth || 1, r = scrub.getBoundingClientRect(), half = tip.offsetWidth / 2;
    tip.style.left = `${Math.max(half + 4, Math.min(host.offsetWidth - half - 4, (e.clientX - h.left) / k))}px`;
    tip.style.top = `${(r.top - h.top) / k}px`;
    if (dragging) scrub.querySelector(".scrub-fill").style.width = `${share(e) * 100}%`;
  };
  scrub.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();                      // no text selection, no sticky focus ring from the mouse
    dragging = true;
    scrub.setPointerCapture(e.pointerId);
    scrub.classList.add("is-dragging");
    show(e);
  });
  scrub.addEventListener("pointermove", show);
  scrub.addEventListener("pointerup", (e) => {
    if (!dragging) return;
    dragging = false;
    scrub.classList.remove("is-dragging");
    const L = playerLength();
    jumpTo(L ? share(e) * L : 0);
    if (!scrub.matches(":hover")) tip.hidden = true;
  });
  const cancel = () => { dragging = false; scrub.classList.remove("is-dragging"); tip.hidden = true; tick(); };
  scrub.addEventListener("pointercancel", cancel);
  scrub.addEventListener("lostpointercapture", () => { if (dragging) cancel(); });   // the release went elsewhere: no seek
  scrub.addEventListener("pointerleave", () => { if (!dragging) tip.hidden = true; });
}
// the bar's last button: into full screen from the big view, out of it in full screen
function fsButton(bar = tube.querySelector(".tube-bar")) {
  const b = bar && bar.querySelector(".fs"), on = document.fullscreenElement === tube;
  if (!b) return;
  b.innerHTML = on ? FS_EXIT_ICON : FS_ICON;
  b.title = on ? "Leave full screen  F or Esc" : "Video full screen  F";
  b.setAttribute("aria-label", on ? "Leave full screen" : "Video full screen");
}
// The bar wakes on the pointer in every seat view (John 19/10: the seek bar should be there once you've moused over the
// video) and stays while the pointer is on the picture or the bar; it goes when the pointer leaves. Where the picture
// fills the window (full screen, the big view) a mouse resting on the picture also puts it away after 2.5 s, as before;
// one resting on the bar never does.
let barTimer = 0;
const fillsWindow = () => tube.classList.contains("is-full") || tube.classList.contains("is-big");
function wake(onBar = false) {
  tube.classList.add("is-awake");
  clearTimeout(barTimer);
  if (!onBar && fillsWindow()) barTimer = setTimeout(sleep, 2500);
}
function sleep() { clearTimeout(barTimer); tube.classList.remove("is-awake"); closeSpeeds(tube); }
tube.addEventListener("pointermove", (e) => { if (e.pointerType !== "touch") wake(!!e.target.closest(".tube-bar, .pip-bar")); });
tube.addEventListener("pointerleave", (e) => { if (e.pointerType !== "touch") sleep(); });
// a touch has no hover: a tap shows the bar for a while, wherever the picture is
tube.addEventListener("pointerdown", (e) => { if (e.pointerType === "touch") { tube.classList.add("is-awake"); clearTimeout(barTimer); barTimer = setTimeout(sleep, 3500); } });
// the bar's buttons are tab stops only where it's the only transport (full screen, the big view, the corner box with the
// lid closed); elsewhere the laptop has the same ones, and the cinema screen would put a dozen stops before the laptop
function barReach() {
  const reach = fillsWindow() || (!!seat && !!seat.pip && !seat.open);
  for (const b of tube.querySelectorAll(".tube-bar button, .tube-bar .scrub")) b.tabIndex = reach ? 0 : -1;
}
document.addEventListener("fullscreenchange", () => {
  tube.classList.toggle("is-full", document.fullscreenElement === tube);
  fsButton();
  wake();
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
  const pb = tube.querySelector(".pip-bar"); if (pb) tube.append(pb);   // the corner box's strip stays on top
  barReach();
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
          if (seat.cc) applyCaptions();
          applyRate();
          tick();
        },
        onStateChange: (e) => { if (e.data === 1) applyRate(); theatreFor(e.data); tick(); },
        onPlaybackRateChange: () => tick(),
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
// Speed (John 19/10): 1x to 2x, only the rates YouTube offers for this recording; < and > step down and up, as on
// YouTube. The choice is remembered in this browser, so the next talk starts at it.
const RATES = [1, 1.25, 1.5, 1.75, 2];
let wantRate = 1;
try { const v = Number(localStorage.getItem("cinema-speed")); if (RATES.includes(v)) wantRate = v; } catch (e) { /* no storage: 1x */ }
const rateText = (r) => `${r}×`;
const playerRate = () => { const p = seat && seat.player; return p && seat.ready && p.getPlaybackRate ? p.getPlaybackRate() : 1; };
function ratesOffered() {
  const p = seat && seat.player, have = p && seat.ready && p.getAvailablePlaybackRates ? p.getAvailablePlaybackRates() || [] : [];
  return RATES.filter((r) => have.includes(r));
}
function applyRate() {   // when the player is ready, and on play (a rate set before it plays can be dropped)
  const p = seat && seat.player;
  if (p && seat.ready && p.setPlaybackRate && ratesOffered().includes(wantRate) && p.getPlaybackRate() !== wantRate) p.setPlaybackRate(wantRate);
}
function setRate(r) {
  wantRate = r;
  try { localStorage.setItem("cinema-speed", String(r)); } catch (e) { /* this visit only */ }
  applyRate();
  setTimeout(tick, 100);
}
function stepRate(d) {
  const list = ratesOffered(), now = playerRate();
  const next = d > 0 ? list.find((r) => r > now) : [...list].reverse().find((r) => r < now);
  if (next != null) setRate(next);
}
const rateNote = () => (playerRate() !== 1 ? ` · ${rateText(playerRate())}` : "");   // next to the time, only off 1x
// the rates as a row of chips above the button, in whichever bar it is (the laptop's screen, or the recording's bar)
function openSpeeds(btn) {
  const host = btn.closest(".tube-bar, .face.notes"), was = host && host.querySelector(":scope > .speed-menu");
  closeSpeeds();
  if (!host || was) return;
  const now = playerRate();
  const menu = el("div", { class: "speed-menu", role: "group", "aria-label": "Playback speed" },
    ratesOffered().map((r) => el("button", { type: "button", "aria-pressed": String(r === now), text: rateText(r),
      onclick: () => { setRate(r); closeSpeeds(document, true); } })));
  host.append(menu);
  const h = host.getBoundingClientRect(), k = h.width / host.offsetWidth || 1, b = btn.getBoundingClientRect();
  Object.assign(menu.style, { right: `${Math.max(4, (h.right - b.right) / k)}px`, bottom: `${(h.bottom - b.top) / k + 6}px` });
  btn.setAttribute("aria-expanded", "true");
  (menu.querySelector('[aria-pressed="true"]') || menu.firstChild)?.focus({ preventScroll: true });
}
function closeSpeeds(root = document, refocus = false) {
  const open = root.querySelector(".speed[aria-expanded='true']");
  for (const m of root.querySelectorAll(".speed-menu")) m.remove();
  if (!open) return;
  open.setAttribute("aria-expanded", "false");
  if (refocus) open.focus({ preventScroll: true });
}
document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".speed-menu, .speed")) closeSpeeds(); });
// Captions: YouTube draws them at the foot of its frame, which the tube crops away (see .tube's --crop in the CSS), so
// with captions on the frame is uncropped and they sit on the picture's foot. The English track, else whatever the
// recording has (auto-generated tracks too). Asked for before the player exists, they come on when it's ready.
function toggleCaptions() {
  if (!seat) return;
  seat.cc = !seat.cc;
  applyCaptions();
  tick();
}
function applyCaptions() {
  const p = seat && seat.player;
  tube.classList.toggle("is-cc", !!(seat && seat.cc));
  if (!p || !p.loadModule || !seat.ready) return;
  if (!seat.cc) { p.setOption("captions", "track", {}); p.unloadModule("captions"); return; }
  p.loadModule("captions");
  p.setOption("captions", "track", { languageCode: "en" });
  captionSize();
  setTimeout(() => {             // no English track: the recording's first
    if (!seat || !seat.cc || seat.player !== p) return;
    const now = p.getOption("captions", "track"), list = p.getOption("captions", "tracklist") || [];
    if ((!now || !now.languageCode) && list.length) p.setOption("captions", "track", list[0]);
  }, 1500);
}
// YouTube sizes captions by its frame; on the cinema screen (seen from the seat) that's small: a step up there
function captionSize() {
  const p = seat && seat.player;
  if (seat && seat.cc && p && p.setOption && seat.ready) p.setOption("captions", "fontSize", tube.clientWidth < 1100 ? 2 : 1);
}
// Theatre: while the talk plays, the title column drifts off and the picture grows to the screen's full height, centred;
// pause (for a moment) or let it finish and the column comes back
let theatreTimer = 0;
function theatreFor(state) {
  if (!seat) return;
  clearTimeout(theatreTimer);
  if (state === 1) setTheatre(true);
  else if (state === 2 || state === 0) theatreTimer = setTimeout(() => setTheatre(false), 1200);
}
function setTheatre(on) {
  if (!seat || seat.theatre === on) return;
  seat.theatre = on;
  if (seat.cine) seat.cine.classList.toggle("is-theatre", inTheatre());
  if (!seat.zoom) placeTube(reduceMotion ? 0 : 750);
}
// the lid closed with the view on the film: the picture stays big, playing or not (and with the recording in the corner
// box, the screen keeps its column: there's no picture on it to make room for)
const inTheatre = () => !!seat && !seat.pip && (seat.theatre || !!seat.layout.video);
// where things on the cinema screen end up once the view has moved (read from the layout: mid-move, the DOM is not there yet)
function theatreRect() {
  const st = stage.getBoundingClientRect(), L = seat.layout, v = L.video;
  if (v) return { left: st.left + v.x, top: st.top + v.y, width: v.w, height: v.h };
  const fr = { left: st.left + L.screen.x, top: st.top + L.screen.y, width: L.screen.w, height: L.screen.h };
  const padX = fr.width * 0.015, padT = 8, padB = L.cover + 8;
  const aw = fr.width - 2 * padX, ah = fr.height - padT - padB;
  const h = Math.min(ah, aw * 9 / 16), w = h * 16 / 9;
  return { left: fr.left + (fr.width - w) / 2, top: fr.top + padT + (ah - h) / 2, width: w, height: h };
}
function onScreen(e) {
  const pr = seat.cine.getBoundingClientRect(), r = e.getBoundingClientRect(), st = stage.getBoundingClientRect(), L = seat.layout.screen;
  const kx = L.w / pr.width, ky = L.h / pr.height;
  return { left: st.left + L.x + (r.left - pr.left) * kx, top: st.top + L.y + (r.top - pr.top) * ky, width: r.width * kx, height: r.height * ky };
}
// the tube sits over whichever slot is showing: the cinema screen's, or the laptop's when zoomed; or in the corner box
function placeTube(ms = 0) {
  if (!seat || tube.hidden) return;
  const host = seat.zoom ? seat.notes : seat.cine, slot = host && host.querySelector(".slot");
  if (!slot && !seat.pip) { tube.classList.add("is-away"); return; }
  const r = seat.pip ? pipRect() : seat.zoom ? slot.getBoundingClientRect() : inTheatre() ? theatreRect() : onScreen(slot), st = stage.getBoundingClientRect();
  const was = tube.getBoundingClientRect(), w = Math.round(r.width), h = Math.round(r.height);
  const to = `translate(${Math.round(r.left - st.left)}px, ${Math.round(r.top - st.top)}px)`;
  // moving: the new size at once, scaled from the old box back to it (a transform alone runs in step with the room's;
  // animating width and height relaid the player every frame and fell behind)
  const flip = ms && was.width > 1 && !tube.classList.contains("is-away") && !tube.classList.contains("is-full");
  tube.style.transition = "opacity .25s ease";
  tube.style.transformOrigin = "0 0";
  Object.assign(tube.style, { width: `${w}px`, height: `${h}px`,
    transform: flip ? `translate(${was.left - st.left}px, ${was.top - st.top}px) scale(${was.width / w}, ${was.height / h})` : to });
  if (flip) {
    tube.getBoundingClientRect();
    tube.style.transition = `transform ${ms}ms ${EASE}, opacity .25s ease`;
    tube.style.transform = to;
  }
  tube.classList.toggle("is-big", !seat.pip && !seat.zoom && !!seat.layout.video);
  tube.classList.toggle("is-on-laptop", !seat.pip && seat.zoom);
  tube.classList.toggle("is-pip", !!seat.pip);
  tube.classList.remove("is-away");
  barReach();
}

// ----- picture in picture, in the page (John 19/10): the same player moved into a box in a corner, the way it moves
// between the cinema screen and the laptop (never reloaded). The browser's own picture-in-picture can't take a
// cross-origin iframe, and Document Picture-in-Picture would move the iframe into another document, which reloads it.
// The box is dragged by its top strip and sized from its top-left corner (the opposite corner stays put), always 16:9;
// the laptop can zoom meanwhile and the recording stays in the box. P, or Put back, returns it.
const PIP_MIN = 240, PIP_EDGE = 12;
let pipAt = null;   // { w, fx, fy }: its width, and where it sits as a share of the room left each way (a corner stays a corner on resize)
function pipRect() {
  const st = stage.getBoundingClientRect(), W = st.width, H = st.height, E = PIP_EDGE;
  if (!pipAt) {   // first time: bottom right, clear of the laptop's transport when it's zoomed
    const w = Math.round(Math.min(480, Math.max(300, W * 0.28))), free = H - w * 9 / 16 - 2 * E;
    pipAt = { w, fx: 1, fy: free > 0 ? Math.max(0, (free - 72) / free) : 0 };
  }
  const w = Math.round(Math.max(Math.min(PIP_MIN, W - 2 * E), Math.min(pipAt.w, W - 2 * E, (H - 2 * E) * 16 / 9))), h = Math.round(w * 9 / 16);
  return { left: st.left + E + pipAt.fx * Math.max(0, W - w - 2 * E), top: st.top + E + pipAt.fy * Math.max(0, H - h - 2 * E), width: w, height: h };
}
function pipTo(x, y, w) {      // stage px
  const E = PIP_EDGE, share = (v, room) => (room > 0 ? Math.max(0, Math.min(1, (v - E) / room)) : 0);
  pipAt = { w, fx: share(x, stage.clientWidth - w - 2 * E), fy: share(y, stage.clientHeight - w * 9 / 16 - 2 * E) };
  placeTube();
}
function pipBar() {
  const grip = el("span", { class: "pip-size", title: "Drag to resize", "aria-hidden": "true" });
  const bar = el("div", { class: "pip-bar" }, grip, el("span", { class: "pip-title", text: seat.t.title }),
    el("button", { class: "pip-back", type: "button", "aria-keyshortcuts": "P", title: "Back to the screen  P", onclick: () => setPip(false) }, "Put back", key("P")));
  bar.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || e.target.closest("button")) return;
    e.preventDefault();
    const sizing = e.target === grip, r = pipRect(), st = stage.getBoundingClientRect(), x0 = e.clientX, y0 = e.clientY;
    const left = r.left - st.left, top = r.top - st.top;
    bar.setPointerCapture(e.pointerId);
    tube.classList.add("is-dragging");
    bar.onpointermove = (m) => {
      const dx = m.clientX - x0, dy = m.clientY - y0;
      if (!sizing) { pipTo(left + dx, top + dy, r.width); return; }
      const d = Math.abs(dx) > Math.abs(dy * 16 / 9) ? dx : dy * 16 / 9;   // whichever way the corner moved more
      const w = Math.round(Math.max(PIP_MIN, Math.min(r.width - d, stage.clientWidth - 2 * PIP_EDGE, (stage.clientHeight - 2 * PIP_EDGE) * 16 / 9)));
      pipTo(left + r.width - w, top + r.height - w * 9 / 16, w);
    };
    // the release can be lost (P mid-drag hides the strip): any end of the capture ends the drag
    bar.onpointerup = bar.onpointercancel = bar.onlostpointercapture = bar.endDrag;
  });
  bar.endDrag = () => { bar.onpointermove = bar.onpointerup = bar.onpointercancel = bar.onlostpointercapture = null; tube.classList.remove("is-dragging"); };
  return bar;
}
// the screen it left says where it went; a click there brings it back
function markPip() { for (const p of [seat.cinePanel, seat.notesPanel]) if (p) p.classList.toggle("is-pip", !!seat.pip); }
function setPip(on) {
  if (!seat || !seat.t.videoId || !EMBED || seat.failed || on === !!seat.pip) return;
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  const pb = tube.querySelector(".pip-bar"); if (pb) pb.endDrag();   // a drag under way ends here, not on the next hover
  if (on && !seat.player && !seat.starting) jumpTo(0);       // from the poster: it starts, in the box
  seat.pip = on;
  if (on && !tube.querySelector(".pip-bar")) tube.append(pipBar());
  markPip();
  if (seat.cine) seat.cine.classList.toggle("is-theatre", inTheatre());
  placeTube(reduceMotion ? 0 : 450);
  tick();
}

// ----- the cinema screen: the recording, and beside it what the talk is, who gives it and why it's worth your time
const nb = (x) => x.replace(/ /g, " ").replace(/-/g, "‑");
function cineScreen(t) {
  const s = t.s || {};
  const slot = t.videoId && EMBED ? el("div", { class: "slot", "aria-hidden": "true", onclick: () => seat && seat.pip && setPip(false) })
    : el("div", { class: "slot is-poster" },
      t.videoId ? el("a", { class: "btn is-main", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" })
        : [el("b", { text: "No recording yet" }), el("span", { text: "Devoxx puts the talks on YouTube in the weeks after the conference. Your laptop has the notes, from the abstract." }),
          el("button", { class: "btn is-back", type: "button", text: "Back to the programme", onclick: () => goHall() })]);
  return el("section", { class: "face cine is-projected", "aria-label": `${t.title}: the cinema screen` },
    el("div", { class: "cine-info" },
      el("div", { class: "meta" }, el("span", { text: [t.room, whenShort(t), typeLabel(t)].filter(Boolean).map(nb).join(" · ") })),
      el("h2", { text: t.title }),
      el("p", { class: "who-l", text: speakers(t, true) }),
      s.watchIf ? el("p", { class: "verdict" }, el("b", { text: "Worth your time if" }), `${s.watchIf.replace(/\.$/, "")}.`) : null),
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
  // (the title is set in the menu's condensed display face: it starts bigger than a text face would)
  let size = Math.min(46, Math.max(30, Math.round(info.clientWidth / 7.5))), v = 16;
  h2.style.fontSize = `${size}px`;
  if (verdict) verdict.style.fontSize = "";
  while (over() && size > 30) h2.style.fontSize = `${--size}px`;          // the title keeps the lead...
  while (verdict && over() && v > 13) verdict.style.fontSize = `${--v}px`;   // ...the reason gives way first
  while (over() && size > 18) h2.style.fontSize = `${--size}px`;
}

// ----- the laptop: the notes, and below them the transport for the recording on the big screen: a scrubber with the
// chapters marked on it, play, previous/next chapter, the chapter playing (a menu of all of them), captions and sound
const key = (k) => el("kbd", { text: k, "aria-hidden": "true" });
// The summary set for reading: paragraphs of two or three sentences (the summaries come as two long blocks), the tools
// and products it names in bold the first time, the speaker's own words pulled out between them, with a jump to the
// moment when there's a recording.
const ABBR = /\b(e\.g|i\.e|vs|etc|Dr|Mr|Ms|Mrs|St|No|approx|cf|incl)\.$/i;
function sentences(p) {
  const out = [];
  let cur = "";
  for (const part of p.split(/(?<=[.!?…])\s+(?=[“"‘'(\p{Lu}\d])/u)) {
    cur = cur ? `${cur} ${part}` : part;
    if (!ABBR.test(cur)) { out.push(cur); cur = ""; }
  }
  if (cur) out.push(cur);
  return out;
}
function readingParas(paras) {
  const out = [];
  for (const p of paras) {
    let c = [];
    const flush = () => { if (c.length) out.push(c.join(" ")); c = []; };
    for (const x of sentences(p)) {
      c.push(x);
      if (c.length >= 3 || c.join(" ").length > 280) flush();
    }
    if (c.length && c.join(" ").length < 90 && out.length) { out[out.length - 1] += ` ${c.join(" ")}`; c = []; }
    flush();
  }
  return out;
}
const escRe = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function emphasise(text, terms, used) {
  if (!terms.length) return [text];
  const re = new RegExp(`(?<![\\p{L}\\d])(${terms.map(escRe).join("|")})(?![\\p{L}\\d])`, "gu");
  const out = [];
  let at = 0;
  for (const m of text.matchAll(re)) {
    const key = m[1].toLowerCase();
    if (used.has(key)) continue;
    used.add(key);
    out.push(text.slice(at, m.index), el("strong", { text: m[1] }));
    at = m.index + m[1].length;
  }
  out.push(text.slice(at));
  return out;
}
function readable(t, s, live) {
  const terms = [...new Set(s.tech || [])].filter((x) => x.length > 2).sort((a, b) => b.length - a.length);
  const used = new Set();
  const paras = readingParas(s.summary || t.abstract || []);
  const quotes = (s.quotes || []).filter((q) => q && q.text).slice(0, 2);
  const pull = (q) => el("figure", { class: "pull" },
    el("blockquote", { text: `“${q.text.replace(/^["“]|["”]$/g, "")}”` }),
    q.at ? (live ? el("button", { class: "pull-at", type: "button", onclick: () => jumpTo(toSeconds(q.at)) }, `▶ Play from ${q.at}`)
      : el("span", { class: "pull-at", text: q.at })) : null);
  const slots = paras.length >= 5 ? [1, 3] : [Math.min(1, paras.length - 1), paras.length - 1];
  const out = [];
  paras.forEach((p, i) => {
    out.push(el("p", {}, ...emphasise(p, terms, used)));
    slots.forEach((at, qi) => { if (at === i && quotes[qi] && !(qi === 1 && slots[0] === slots[1])) out.push(pull(quotes[qi])); });
  });
  return out;
}

// the overview's gist: two lines (one on a small laptop), and a "more" that shows the rest
function gist(text) {
  const p = el("p", { class: "lead is-short" }, el("span", { text }));
  const more = el("button", { class: "lead-more", type: "button", "aria-expanded": "false", text: "more ▾",
    onclick: () => { const open = p.classList.toggle("is-short"); more.textContent = open ? "more ▾" : "less ▴"; more.setAttribute("aria-expanded", String(!open)); } });
  return el("div", { class: "lead-wrap" }, p, more);
}

// The notepad (John 19/10): your own notes, one per talk, kept in this browser as you type (where storage is off, only
// while you stay on the talk: download them). Timestamp, or Ctrl+Enter, puts in where the talk is, like [12:40];
// downloaded as Markdown, each of those becomes a link to that moment on YouTube.
const noteKey = (id) => `cinema-note-${id}`;
function readNote(id) { try { return localStorage.getItem(noteKey(id)) || ""; } catch (e) { return ""; } }
function writeNote(id, text) {
  try { if (text.trim()) localStorage.setItem(noteKey(id), text); else localStorage.removeItem(noteKey(id)); return true; } catch (e) { return false; }
}
const STAMP = /\[(?:(\d+):)?(\d{1,2}):(\d{2})\](?!\()/g;          // [12:40] or [1:02:03], not one already linked
const linked = (t, text) => (t.videoId ? text.replace(STAMP, (m, h, mm, ss) => `${m}(https://youtu.be/${t.videoId}?t=${Number(h || 0) * 3600 + Number(mm) * 60 + Number(ss)})`) : text);
function noteMd(t, text, level = 1) {
  const head = [`${"#".repeat(level)} ${t.title}`, "", `- Speakers: ${speakers(t, true)}`, t.room ? `- Room: ${t.room}` : null,
    t.start ? `- Date: ${fDayLong.format(new Date(t.start))} ${fYear.format(new Date(t.start))}, ${fTime.format(new Date(t.start))}` : null, t.videoId ? `- YouTube: https://youtu.be/${t.videoId}` : null];
  return `${head.filter((x) => x != null).join("\n")}\n\n${linked(t, text.trim())}\n`;
}
// a file name every system takes: no path or reserved characters, no leading or trailing dots, not too long
const mdName = (title) => `${title.replace(/[\\/:*?"<>|\u0000-\u001f]+/g, " ").replace(/\s+/g, " ").trim().replace(/^\.+|\.+$/g, "").slice(0, 120).trim() || "Talk notes"}.md`;
function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const a = el("a", { href: url, download: name, hidden: true });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function downloadAll() {   // one file, a section per talk with notes, in programme order
  const mine = talks.filter((x) => readNote(x.id).trim()).sort((a, b) => (a.start || "").localeCompare(b.start || ""));
  if (mine.length) download("Devoxx Belgium 2026 notes.md", `# Devoxx Belgium 2026: my notes\n\n${mine.map((x) => noteMd(x, readNote(x.id), 2)).join("\n")}`);
  return mine.length;
}
function notepad(t, live) {
  const text = el("textarea", { class: "pad-text", "aria-label": "Your notes on this talk", spellcheck: "true",
    placeholder: live ? "Your notes on this talk, kept in this browser. Timestamp (or Ctrl+Enter) puts in where the talk is, like [12:40]: in the download it links to that moment."
      : "Your notes on this talk, kept in this browser." });
  text.value = readNote(t.id);
  const state = el("span", { class: "pad-state", role: "status", title: "Kept in this browser only", text: text.value ? "Saved" : "" });
  let timer = 0, dirty = false;
  const save = () => {
    clearTimeout(timer);
    if (!dirty) return;
    dirty = false;
    state.textContent = writeNote(t.id, text.value) ? "Saved" : "Not saved (private window?)";
  };
  const soon = () => { dirty = true; state.textContent = ""; clearTimeout(timer); timer = setTimeout(save, 400); };
  const stamp = () => {
    const sec = playerTime(), before = text.value.slice(0, text.selectionStart);
    const s = `${before && !/\s$/.test(before) ? " " : ""}[${clock(sec || 0)}] `;
    text.focus();
    if (!document.execCommand("insertText", false, s)) text.setRangeText(s, text.selectionStart, text.selectionEnd, "end");   // execCommand keeps undo
    soon();
  };
  text.addEventListener("input", soon);
  text.addEventListener("blur", save);
  text.addEventListener("keydown", (e) => {
    e.stopPropagation();                     // typing here is writing: none of the page's keys
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && live) { e.preventDefault(); stamp(); }
    else if (e.key === "Escape") { e.preventDefault(); text.closest(".pane").focus(); }   // out of the text; Esc again zooms out
  });
  const pad = el("div", { class: "pad" },
    el("div", { class: "pad-tools" },
      live ? el("button", { class: "notes-btn", type: "button", title: "Put in where the talk is  Ctrl+Enter", onclick: stamp }, "Timestamp", key("Ctrl+Enter")) : null,
      state, el("span", { class: "notes-spacer" }),
      el("button", { class: "notes-btn", type: "button", onclick: () => { save(); download(mdName(t.title), noteMd(t, text.value)); } }, "Download as .md"),
      el("button", { class: "notes-btn", type: "button", onclick: () => { save(); if (!downloadAll()) state.textContent = "No notes yet"; } }, "Download all notes")),
    text);
  pad.flush = save;
  return pad;
}

// Snake (John 19/10): something for the hands while you listen, on the laptop, never over the recording. Its keys
// (arrows, WASD, Space) only while the board has focus, and never the player's (K [ ] F L C M Z P < > still work);
// it pauses the moment the board loses focus, the tab changes or the lid closes. No sound: the talk is playing.
const SNAKE = { cols: 24, rows: 12 };
function snake() {
  const board = el("canvas", { class: "snake-board", tabindex: "0", "aria-label": "Snake: arrow keys or WASD steer, Space pauses" });
  const scoreEl = el("b", { text: "0" }), bestEl = el("b");
  let best = 0;
  try { best = Number(localStorage.getItem("cinema-snake-best")) || 0; } catch (e) { /* no storage: this visit's best */ }
  bestEl.textContent = String(best);
  let body, dir, turns, food, score, over, fresh = true, running = false, timer = 0;
  const same = (a, b) => a[0] === b[0] && a[1] === b[1];
  const drop = () => {
    const free = [];
    for (let x = 0; x < SNAKE.cols; x++) for (let y = 0; y < SNAKE.rows; y++) if (!body.some((b) => same(b, [x, y]))) free.push([x, y]);
    food = free[Math.floor(Math.random() * free.length)];
  };
  const reset = () => { body = [[6, 6], [5, 6], [4, 6]]; dir = [1, 0]; turns = []; score = 0; over = false; scoreEl.textContent = "0"; drop(); };
  const pace = () => Math.max(70, 140 - score * 3);
  const keepBest = () => { if (score <= best) return; best = score; bestEl.textContent = String(best);
    try { localStorage.setItem("cinema-snake-best", String(best)); } catch (e) { /* this visit only */ } };
  const draw = () => {
    const w = board.clientWidth, h = board.clientHeight, dpr = devicePixelRatio || 1;
    if (!w || !h) return;
    if (board.width !== Math.round(w * dpr) || board.height !== Math.round(h * dpr)) { board.width = Math.round(w * dpr); board.height = Math.round(h * dpr); }
    const g = board.getContext("2d"), c = Math.floor(Math.min(w / SNAKE.cols, h / SNAKE.rows));
    const ox = Math.round((w - c * SNAKE.cols) / 2), oy = Math.round((h - c * SNAKE.rows) / 2);
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    // printed on the notes' stock (cinema.css tokens: paper in the hall, black in the theatre): the board a card in a
    // rule, the snake in the type's colour, the food in the talk's ink
    const cs = getComputedStyle(board), tok = (n, d) => cs.getPropertyValue(n).trim() || d;
    const fg = tok("--fg", "#111111"), fg2 = tok("--fg-2", "#3b3d3a"), raised = tok("--raised", "#FAFBF8"), line = tok("--line", "#111111");
    const ink = tok("--t-mark", "#111111"), focused = document.activeElement === board;
    g.fillStyle = raised; g.fillRect(ox, oy, c * SNAKE.cols, c * SNAKE.rows);
    g.strokeStyle = focused ? fg : line; g.lineWidth = focused ? 3 : 1.5;
    g.strokeRect(ox + g.lineWidth / 2, oy + g.lineWidth / 2, c * SNAKE.cols - g.lineWidth, c * SNAKE.rows - g.lineWidth);
    g.fillStyle = ink; g.strokeStyle = fg; g.lineWidth = 1.5;
    g.beginPath(); g.arc(ox + (food[0] + 0.5) * c, oy + (food[1] + 0.5) * c, c * 0.34, 0, Math.PI * 2); g.fill(); g.stroke();
    body.forEach(([x, y], i) => { g.fillStyle = i ? fg2 : fg; g.fillRect(ox + x * c + 1, oy + y * c + 1, c - 2, c - 2); });
    if (running) return;
    g.fillStyle = raised; g.globalAlpha = 0.86; g.fillRect(ox, oy, c * SNAKE.cols, c * SNAKE.rows); g.globalAlpha = 1;
    const size = Math.max(14, Math.min(24, Math.round(c * 1.05)));
    g.textAlign = "center"; g.textBaseline = "middle";
    g.fillStyle = fg; g.font = `800 ${size}px "Big Shoulders Display", "Archivo Narrow", Impact, sans-serif`;
    g.fillText((over ? `Game over: ${score}. Space or click to play again` : fresh ? "Click, or Space, to play" : "Paused. Space or click to go on").toUpperCase(), w / 2, h / 2 - size * 0.6);
    g.fillStyle = fg2; g.font = `500 ${Math.max(12, Math.round(size * 0.62))}px Archivo, system-ui, sans-serif`;
    g.fillText("Arrows or WASD steer, while the board has focus", w / 2, h / 2 + size * 0.75);
  };
  const stop = () => { running = false; clearTimeout(timer); draw(); };
  const step = () => {
    // in front of you or not at all: focus elsewhere, another tab, the lid closed (the board gone) all pause it
    if (!board.isConnected || document.activeElement !== board || document.hidden) { stop(); return; }
    if (turns.length) dir = turns.shift();
    const head = [body[0][0] + dir[0], body[0][1] + dir[1]], ate = same(head, food);
    const hit = head[0] < 0 || head[1] < 0 || head[0] >= SNAKE.cols || head[1] >= SNAKE.rows || body.slice(0, ate ? body.length : -1).some((b) => same(b, head));
    if (hit) { over = true; keepBest(); stop(); return; }
    body.unshift(head);
    if (ate) { score++; scoreEl.textContent = String(score); keepBest(); drop(); } else body.pop();
    draw();
    timer = setTimeout(step, pace());
  };
  const go = () => {
    if (running) return;
    if (over) reset();
    if (document.activeElement !== board) board.focus({ preventScroll: true });
    running = true; fresh = false;
    draw();
    timer = setTimeout(step, pace());
  };
  const steer = (d) => {   // queued, so two quick turns both count, but never straight back into itself
    const last = turns.length ? turns[turns.length - 1] : dir;
    if ((d[0] === -last[0] && d[1] === -last[1]) || same(d, last) || turns.length > 1) return;
    turns.push(d);
  };
  const DIRS = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0], w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0] };
  board.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const d = DIRS[e.key.length === 1 ? e.key.toLowerCase() : e.key];
    if (d) { e.preventDefault(); if (!over) steer(d); go(); }                       // preventDefault: the page leaves them alone
    else if (e.key === " " || e.key === "Enter") { e.preventDefault(); if (running) stop(); else go(); }
  });
  board.addEventListener("click", () => { if (!running) go(); });
  board.addEventListener("focus", draw);
  board.addEventListener("blur", stop);
  const sized = new ResizeObserver(draw);
  sized.observe(board);
  reset();
  const game = el("div", { class: "snake" },
    el("div", { class: "snake-head" }, el("span", {}, "Score ", scoreEl), el("span", {}, "Best ", bestEl),
      el("span", { class: "snake-hint", text: "The talk keeps playing; its keys still work." })),
    board);
  game.dispose = () => { running = false; clearTimeout(timer); sized.disconnect(); };   // leaving the talk
  return game;
}
function notesScreen(t) {
  const s = t.s || {};
  const chapters = chaptersOf(t);
  const live = EMBED && t.videoId;
  // first: the gist and the chapters to jump to (when there are chapters)
  // then your own: the notepad and Snake (John 19/10), after the talk's
  const tabs = [["overview", "Overview"], ["summary", "Summary"], ["points", "Key points"], ["monday", "To try"], ["notepad", "My notes"], ["snake", "Snake"]]
    .filter(([id]) => (id === "overview" && chapters.length) || id === "summary" || (id === "points" && s.keyPoints && s.keyPoints.length)
      || (id === "monday" && s.takeaways && s.takeaways.length) || id === "notepad" || id === "snake");
  let pad = null, game = null;               // built once, so the text (and its undo) and a paused game survive a tab change
  const pane = el("div", { class: "pane scroller", tabindex: "0", "aria-label": "Notes" });
  const tabRow = el("div", { class: "tabs", role: "group", "aria-label": "Notes" });
  // reading: scrolling down puts the header, the tabs and the bar away; scrolling up, the top, or the pointer at an
  // edge (or keyboard focus on them) brings them back
  // Only a deliberate scroll counts: ~30 px one way. Folding changes the pane's height, and the browser then moves the
  // scroll position by itself; those moves are ignored while the fold animates, and a pane that would fit without the
  // chrome never folds (else it would fold, fit, unfold, overflow: a flicker).
  let lastY = 0, run = 0, lockUntil = 0, panel = null;
  const chrome = (show) => {
    if (!panel || panel.classList.contains("is-immersed") === !show) return;
    panel.classList.toggle("is-immersed", !show);
    lockUntil = performance.now() + 450;
    run = 0;
  };
  pane.addEventListener("scroll", () => {
    const y = pane.scrollTop, d = y - lastY;
    lastY = y;
    if (performance.now() < lockUntil) return;
    if (y < 8) { chrome(true); return; }
    run = Math.sign(d) === Math.sign(run) ? run + d : d;
    const spare = pane.scrollHeight - pane.clientHeight;      // what's left to scroll with the chrome showing
    const folds = [...panel.querySelectorAll(".chrome")].reduce((h, c) => h + c.offsetHeight, 0);   // what folding frees
    if (run > 30 && spare > folds + 32 && !panel.querySelector(".chapter-menu:not([hidden]), .keys-sheet:not([hidden])")) chrome(false);
    else if (run < -30) chrome(true);
  }, { passive: true });
  const chapterList = () => el("ol", { class: "chapters" }, chapters.map((c, i) => el("li", {},
    live ? el("button", { class: "chapter", type: "button", "data-i": i, onclick: () => { jumpTo(c.sec); menu.hidden = true; } }, el("time", { text: clock(c.sec) }), el("span", { text: c.title }))
      : el("a", { class: "chapter", href: ytUrl(t, c.sec), target: "_blank", rel: "noopener", "data-i": i }, el("time", { text: clock(c.sec) }), el("span", { text: c.title })))));
  const fill = (id) => {
    pane.textContent = "";
    if (id === "overview") put(pane, s.tldr ? gist(s.tldr) : null,
      el("p", { class: "label jump-label", text: live && !(seat && seat.failed) ? "Jump to a part: it plays on the big screen" : "Jump to a part: it opens on YouTube" }), chapterList());
    if (id === "summary") put(pane, el("div", { class: "reading" }, s.tldr ? el("p", { class: "in-short" }, el("b", { text: "In short " }), s.tldr) : null, readable(t, s, live)));
    if (id === "points") put(pane, el("ul", { class: "reading" }, s.keyPoints.map((p) => el("li", { text: p }))));
    if (id === "monday") put(pane, el("ol", { class: "reading" }, s.takeaways.map((p) => el("li", { text: p }))));
    if (id === "notepad") put(pane, pad || (pad = notepad(t, live)));
    if (id === "snake") put(pane, game || (game = snake()));
    pane.classList.toggle("is-tool", id === "notepad" || id === "snake");   // they fill the pane, it doesn't scroll
    pane.scrollTop = 0;
    chrome(true);
    for (const b of tabRow.children) b.setAttribute("aria-pressed", String(b.dataset.tab === id));
    rove(tabRow);
    requestAnimationFrame(() => { watchScroll(pane); if (seat) { seat.lastChapter = null; tick(); } });
  };
  for (const [id, label] of tabs) tabRow.append(el("button", { class: "pill", type: "button", "data-tab": id, text: label, onclick: () => fill(id) }));
  const menu = el("div", { class: "chapter-menu scroller", hidden: true, role: "dialog", "aria-label": "Chapters" }, chapters.length ? chapterList() : null);
  const ticks = el("div", { class: "scrub-ticks", "aria-hidden": "true" });
  const scrub = el("div", { class: "scrub", role: "slider", tabindex: "0", "aria-label": "Position in the talk", "aria-valuemin": "0", "aria-valuemax": "0", "aria-valuenow": "0",
      onkeydown: (e) => { const d = { ArrowLeft: -10, ArrowRight: 10, PageDown: -60, PageUp: 60 }[e.key]; if (d) { e.preventDefault(); seekBy(d); } } },
    el("div", { class: "scrub-fill" }), ticks);
  scrubber(scrub);
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
      speedButton(), pipButton(),
      (() => { const b = el("button", { class: "icon fs", type: "button", "aria-keyshortcuts": "F", "aria-label": "Video full screen", title: "Video full screen  F", onclick: () => videoFullscreen() }); b.innerHTML = FS_ICON; return b; })())) : null;
  const keysSheet = el("div", { class: "keys-sheet", hidden: true, role: "note" },
    el("b", { text: "Keys" }),
    el("dl", {}, [["K", "Play or pause"], ["[  ]", "Previous or next chapter"], ["← →", "Back or on 10 seconds"], ["<  >", "Slower or faster"], ["C  M", "Captions, sound"],
      ["F", "Video full screen"], ["P", "Picture in picture"], ["Z", "Zoom in on the laptop"], ["L", "Close or open the lid"], ["Esc", "Zoom out, or leave full screen"], ["?", "These keys"]]
      .filter(([k]) => live || !/^(K|\[|←|<|C|P)/.test(k)).map(([k, d]) => [el("dt", { text: k }), el("dd", { text: d })])),
    live ? el("p", { text: "Or double-click the picture for a full-screen video." }) : null);
  const keysBtn = el("button", { class: "notes-btn notes-keys", type: "button", "aria-label": "Keyboard shortcuts", "aria-expanded": "false", "aria-keyshortcuts": "?",
    onclick: () => toggleKeys() }, "Keys", key("?"));
  const toggleKeys = () => { keysSheet.hidden = !keysSheet.hidden; keysBtn.setAttribute("aria-expanded", String(!keysSheet.hidden)); };
  panel = el("section", { class: `face notes${live ? "" : " is-offline"}`, "aria-label": "Your laptop: notes on the talk" },
    el("div", { class: "chrome is-top" }, el("header", { class: "notes-top" },
      el("span", { class: "notes-app" }, el("i", { "aria-hidden": "true" }), "Notes"),
      el("span", { class: "notes-spacer" }),
      keysBtn,
      el("button", { class: "notes-btn notes-zoom", type: "button", "aria-keyshortcuts": "Z", onclick: () => setLaptop({ zoom: !seat.zoom }) }),
      el("button", { class: "notes-btn notes-close", type: "button", "aria-keyshortcuts": "L", onclick: () => setLaptop({ open: false }) }, "Close lid", key("L")))),
    keysSheet,
    el("div", { class: "notes-body" },
      el("div", { class: "notes-read" }, el("div", { class: "chrome is-tabs" }, tabRow), el("div", { class: "pane-wrap" }, pane)),
      el("aside", { class: "notes-watch" }, live ? el("div", { class: "watch-head is-top", text: "The talk, moved here from the big screen" }) : null,
        live ? el("div", { class: "slot", "aria-hidden": "true", onclick: () => seat && seat.pip && setPip(false) }) : null,
        chapters.length ? el("div", { class: "watch-head", text: "Chapters" }) : null,
        chapters.length ? el("div", { class: "pane-wrap is-list" }, el("div", { class: "scroller watch-list" }, chapterList())) : null)),
    menu, now ? el("div", { class: "chrome is-bottom" }, now) : null,
    el("button", { class: "peek", type: "button", tabindex: "-1", "aria-hidden": "true", onclick: () => chrome(true), onpointerenter: () => chrome(true) },
      live ? el("i", { class: "peek-fill" }) : null, el("span", { class: "peek-handle" })));
  panel.addEventListener("mousemove", (e) => {
    if (!panel.classList.contains("is-immersed")) return;
    const r = panel.getBoundingClientRect();
    if (e.clientY - r.top < 44 || r.bottom - e.clientY < 56) chrome(true);
  });
  panel.addEventListener("focusin", (e) => { if (e.target.closest(".chrome")) chrome(true); });
  panel.fill = fill;
  panel.toggleKeys = toggleKeys;
  panel.flush = () => pad && pad.flush();    // the notepad's last keystrokes, on leaving
  panel.dispose = () => { panel.flush(); if (game) game.dispose(); };
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
    tb.querySelector(".now-time").textContent = Lb ? `${clock(sec || 0)} / ${clock(Lb)}${rateNote()}` : "";
    tb.querySelector(".now-text").textContent = i >= 0 ? `${i + 1}/${ch.length}  ${ch[i].title}` : "";
    syncExtras(tb);
    if (Lb) {
      if (!sb.classList.contains("is-dragging")) tb.querySelector(".scrub-fill").style.width = `${Math.min(100, (sec || 0) / Lb * 100)}%`;
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
  if (L) put(time, el("span", { text: clock(sec || 0) }), el("span", { class: "t-len", text: ` / ${clock(L)}` }), rateNote() ? el("span", { class: "t-rate", text: rateNote() }) : null);
  syncExtras(now);
  const scrub = now.querySelector(".scrub");
  scrub.classList.toggle("is-ready", !!L);
  if (L) {
    n.ticks(L);
    if (!scrub.classList.contains("is-dragging")) now.querySelector(".scrub-fill").style.width = `${Math.min(100, (sec || 0) / L * 100)}%`;
    const pf = n.querySelector(".peek-fill"); if (pf) pf.style.width = `${Math.min(100, (sec || 0) / L * 100)}%`;
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
// the speed and picture-in-picture buttons of a bar, as things stand
function syncExtras(bar) {
  const r = playerRate(), can = ratesOffered().length > 1;
  for (const b of bar.querySelectorAll(".speed")) {
    b.disabled = !can;
    b.setAttribute("aria-label", `Playback speed: ${rateText(r)}`);
    b.title = can ? `Speed: ${rateText(r)}  < >` : "Speed: once the talk plays";
  }
  for (const b of bar.querySelectorAll(".pip")) {
    b.setAttribute("aria-pressed", String(!!seat.pip));
    b.setAttribute("aria-label", seat.pip ? "Put the recording back" : "Picture in picture");
    b.title = seat.pip ? "Put the recording back  P" : "Picture in picture  P";
  }
}

// ----- open, close, zoom
function syncControls() {
  const { open, zoom } = seat;
  lidBar.hidden = lidHit.hidden = open;
  const lb = seat.layout && seat.layout.lidBar;
  lidBar.classList.toggle("is-on-lid", !!lb);
  if (lb) Object.assign(lidBar.style, { left: `${lb.right}px`, top: `${lb.mid}px` });
  else placeLidBar();
  lidPlay.hidden = !seat.t.videoId || !EMBED;
  seatbar.hidden = zoom;                                    // full screen: the laptop's own header has the way out
  walksBtn.hidden = zoom;                                   // and the walks chip sat on its Zoom out (no walk starts from there)
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
  seat.cine.classList.toggle("is-theatre", inTheatre());
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
  for (const sc of panel.querySelectorAll(".scroller")) watchScroll(sc);
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
  if (opening && ms) ms = Math.round(ms * 1.3);           // the view travels further: up to the film and back
  if (seat.notes) seat.notes.classList.add("is-off");     // the screen goes dark first
  closeSpeeds();                                           // (an open speed row would come back stale with the screen)
  if (!next.open && seat.cine && seat.t.videoId && EMBED && !seat.pip) seat.cine.classList.add("is-theatre");   // and the column leaves the film
  lap.classList.add("is-moving");
  if (next.zoom !== seat.zoom && !seat.pip) tube.classList.add("is-away");   // in the corner box, it stays where it is
  await new Promise((r) => setTimeout(r, ms ? 140 : 0));
  Object.assign(seat, { open: next.open, zoom: next.zoom });
  seat.layout = seatLayout(seat);
  stage.classList.toggle("is-reading", seat.zoom);
  if (seat.cine) seat.cine.classList.toggle("is-theatre", inTheatre());
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
  captionSize();
  lap.classList.remove("is-moving");
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
}
// just above the lid's far edge, centred: never on the logo or the sticker
function placeLidBar() {
  const [x0, y0, x1] = LAP.closed.box, pc = (v, of) => `${v / of * 100}%`;
  Object.assign(lidBar.style, { left: pc((x0 + x1) / 2, LAP.closed.w || LAP.w), top: pc(y0 - (LAP.closed.h || LAP.h) * 0.035, LAP.closed.h || LAP.h) });
}
placeLidBar();
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
  else if (k === "<") stepRate(-1);
  else if (k === ">") stepRate(1);
  else if (k === "p") setPip(!seat.pip);
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
    await playClip(walkClip(n), { arrive: key });
  }
  await showStill(key);
  hideClip();
  say("");
  room = n; current = t;
  warmClip(backClip(n));
  seat = { t, n, key, open: true, zoom: false, layout: null, cine: null, notes: null, notesPanel: null, cinePanel: null, player: null, timer: 0,
    chapters: chaptersOf(t), lastChapter: null, starting: false, startAt: 0, pip: false };
  tube.classList.remove("is-cc", "is-pip", "is-awake");
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
    el("span", { text: seat.chapters.length && EMBED ? "Your laptop: the summary, key points and chapters. Pick a chapter and it plays on the big screen." : "Your laptop: the notes on this talk." }),
    el("button", { type: "button", "aria-label": "Dismiss", text: "×", onclick: () => dismiss() }));
  const dismiss = () => { hint.remove(); try { localStorage.setItem("cinema-laptop-hint", "1"); } catch (e) { /* fine */ } };   // the label stays this visit
  // beside the laptop's right edge, a quarter of the way down its screen
  Object.assign(hint.style, { left: `${(LAP.screen[2] + LAP.w * 0.035) / LAP.w * 100}%`, top: `${(LAP.screen[1] + (LAP.screen[3] - LAP.screen[1]) * 0.22) / LAP.h * 100}%` });
  lap.append(hint);
  seat.notes.addEventListener("click", dismiss, { once: true });
}
function leaveSeat() {
  if (!seat) return;
  if (seat.notesPanel) seat.notesPanel.dispose();
  clearInterval(seat.timer);
  clearTimeout(seat.readyTimer);
  clearTimeout(theatreTimer);
  sleep();
  if (seat.player && seat.player.destroy) seat.player.destroy();
  tube.textContent = ""; tube.hidden = true; tube.classList.remove("is-pip");
  lap.hidden = true; lidBar.hidden = lidHit.hidden = true;
  if (seat.notes) seat.notes.remove();
  for (const h of lap.querySelectorAll(".lap-hint")) h.remove();
  seatbar.hidden = true; walksBtn.hidden = false;
  stage.classList.remove("is-seated", "is-leaving");
  lap.style.transition = lap.style.transform = "";
  seat = null;
  resetRoom();
}
// closing the tab keeps what was typed in the notepad's last 400 ms
addEventListener("pagehide", () => { if (seat && seat.notesPanel) seat.notesPanel.flush(); });

// leaving: the laptop goes down and the view comes back up to the walk's framing (phones: the zoom on the door totem
// eases back out), so the walk back starts on exactly what's showing
const LEAVE = 650;
async function standUp() {
  if (seat) {
    walksBtn.hidden = false;                 // on screen for the walk back, even from the zoomed laptop
    if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
    if (seat.player && seat.player.pauseVideo) seat.player.pauseVideo();
    stage.classList.add("is-leaving");
    const b = seat.layout.lap;
    lap.style.transition = `transform ${LEAVE}ms ${EASE}`;
    lap.style.transform = `translateY(${seat.layout.H + 20 - b.y}px)`;
    const f = framing(seat.key), a = placed(seat.key), k = f.s / a.s;
    for (const e of [plate, front]) {
      e.style.transition = `transform ${LEAVE}ms ${EASE}`;
      e.style.transform = `translate(${f.ox - k * a.ox}px, ${f.oy - k * a.oy}px) scale(${k})`;
    }
    await new Promise((r) => setTimeout(r, LEAVE));
  } else if (zoomed) await zoomTo(face ? face.key : "hall", false, true);
}

// ---------- moving between the hall and a seat ----------
let room = null, current = null, busy = false;

async function toHall(withWalk) {
  // the way back: the walk back to the hall where it's rendered (it starts on the still you're looking at), else a fade
  // through black
  const back = withWalk && room ? backClip(room) : null;
  if (back) {
    say("Walking back to the hall");
    await standUp();
    await playClip(back, { arrive: shotKey("hall") });
    say("");
  }
  const dipped = withWalk && room && !back;
  if (dipped) await dip(true);
  unmount();
  room = null; current = null;
  setInk(null); setRoom(false);
  await showStill(shotKey("hall"));
  hideClip();
  mount(hallMenu(), shotKey("hall"), "programme");
  if (dipped) dip(false);
}

async function toSeat(t, withWalk) {
  const n = roomNo(t), key = shotKey(`seat-${n}`);
  if (withWalk && face && !reduceMotion) {      // the programme fades off the screen first, not gone in a frame
    face.el.style.animation = "off .25s ease-in both";     // (an inline opacity loses to the entrance animation's fill)
    await new Promise((r) => setTimeout(r, 250));
  }
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
  warmClip(backClip(n));
  mount(talkScreen(t, shape === "phone", true), shotKey(`seat-${n}`), "screen");
}

async function toOffFloor(t) {   // no seat to walk to (BOFs downstairs): the summary stays on the hall screen
  unmount();
  await showStill(shotKey("hall"));
  current = t; room = null;
  mount(talkScreen(t, shape === "phone", false), shotKey("hall"), "programme");
}

// the hall screen: the Three Inks menu (menu.js). A talk's card asks first; WATCH IT walks you there
const byTalk = new Map(talks.map((t) => [t.id, t]));
const hallMenu = () => inksMenu({ phone: shape === "phone", textHref: "../",
  walks: (id) => byTalk.has(id) && walkable.has(roomNo(byTalk.get(id))),
  watch: (id) => { const t = byTalk.get(id); if (t) goTalk(t); } });
const open = (t, withWalk) => { setInk(t); setRoom(walkable.has(roomNo(t))); return walkable.has(roomNo(t)) ? toSeat(t, withWalk) : toOffFloor(t); };
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
  else if (document.querySelector(".speed-menu")) closeSpeeds(document, true);
  else if (seat && seat.notesPanel && seat.notesPanel.querySelector(".keys-sheet:not([hidden]), .chapter-menu:not([hidden])")) {
    for (const p of seat.notesPanel.querySelectorAll(".keys-sheet, .chapter-menu")) p.hidden = true;
  }
  else if (seat && seat.zoom) setLaptop({ zoom: false });
  else if (current && !seat) goHall();
});

// ---------- start ----------
const deep = /^#talk-(\d+)$/.exec(location.hash);
const first = deep && talks.find((t) => t.id === Number(deep[1]));
if (first) await open(first, false);
else {
  // the first visit of a session walks in from outside, through the doors and the crowd, to the programme
  let seen = true;
  try { seen = sessionStorage.getItem("cinema-intro") === "1"; sessionStorage.setItem("cinema-intro", "1"); } catch (e) { /* no storage: skip it */ }
  const intro = !seen ? introClip() : null;
  if (intro) {
    busy = true;
    await showStill(shotKey("hall"));
    const walking = playClip(intro, { cut: true, arrive: shotKey("hall") });
    clip.addEventListener("playing", () => loading.classList.add("is-done"), { once: true });
    await walking;
    busy = false;
  }
  await toHall(false);
}
loading.classList.add("is-done");

