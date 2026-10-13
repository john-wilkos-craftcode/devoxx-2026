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
const CANVAS = { hall: 980, "hall-phone": 340, seat: 1300, "door-phone": 340 };   // design widths in css px

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
const front = document.getElementById("front");
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
  const b = shots[`walk-b-${n}`], a = b && shots[`walk-a-${b.side}`];
  return a && b.door_frame != null ? (a.frames + b.door_frame) / b.fps : null;
};
const canvasFor = (key) => CANVAS[key.replace(/-\d+$/, "")];

// How a still sits in the viewport: cropped to fill it (cover) unless that would cut more than 6% off a side and
// risk cutting into a screen, then letterboxed (contain), black bars like a cinema.
function fit(key) {
  const [iw, ih] = IMG[key.includes("phone") ? "phone" : "laptop"];
  const W = stage.clientWidth, H = stage.clientHeight;
  const cover = Math.max(W / iw, H / ih), crop = Math.max(1 - W / (iw * cover), 1 - H / (ih * cover)) / 2;
  const s = crop > 0.06 ? Math.min(W / iw, H / ih) : cover;
  return { iw, ih, s, ox: (W - iw * s) / 2, oy: (H - ih * s) / 2, contain: crop > 0.06 };
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
  if (key.includes("phone")) {
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
  for (const s of panel.querySelectorAll(".strip, .scroller")) watchScroll(s);
}
const unmount = () => { if (face) { face.el.remove(); face = null; } front.hidden = true; };
let resizeTimer = 0;
addEventListener("resize", () => {
  place();
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    const next = form();
    if (next !== shape && !busy) { shape = next; rerender(); }
    else if (face) { const mode = fit(face.key).contain ? "contain" : "cover"; plate.style.objectFit = front.style.objectFit = mode; place(); }
  }, 180);
});

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
  const mode = fit(key).contain ? "contain" : "cover";
  plate.style.objectFit = front.style.objectFit = clip.style.objectFit = mode;
  if (plate.getAttribute("src") === src) { done(); return; }
  const img = new Image();
  img.onload = img.onerror = done;
  img.src = src;
});

let skipWalk = null;
function playClip(name, { from = 0, until = null } = {}) {
  return new Promise((resolve) => {
    if (reduceMotion) { resolve(); return; }
    const done = () => { clip.onended = clip.onerror = clip.ontimeupdate = null; skipWalk = null; skipBtn.hidden = true; resolve(); };
    skipWalk = done;
    clip.src = `media/${name}.mp4`;
    clip.hidden = false;
    clip.onended = done;
    clip.onerror = done;                       // a missing clip is a cut, not a dead end
    if (until != null) clip.ontimeupdate = () => { if (clip.currentTime >= until) { clip.pause(); done(); } };
    const go = () => { if (from) clip.currentTime = from; clip.play().then(() => { skipBtn.hidden = false; }).catch(done); };
    if (clip.readyState >= 1) go(); else clip.addEventListener("loadedmetadata", go, { once: true });
  });
}
const hideClip = () => { clip.pause(); clip.hidden = true; clip.removeAttribute("src"); clip.load(); };
skipBtn.addEventListener("click", () => skipWalk && skipWalk());
const say = (text) => { statusBox.textContent = text || ""; statusBox.hidden = !text; };

// ---------- the programme ----------
const days = [...new Set(talks.filter((t) => t.start).map((t) => dayKey(t.start)))].sort();
const startsOn = (d) => [...new Set(talks.filter((t) => t.start && dayKey(t.start) === d).map((t) => t.start))].sort();
const inSlot = (s) => talks.filter((t) => t.start === s).sort((a, b) => (roomNo(a) || 99) - (roomNo(b) || 99));
let day = days.includes("2026-10-07") ? "2026-10-07" : days[0];
let slot = startsOn(day).find((s) => inSlot(s).length >= 6) || startsOn(day)[0];
let query = "";
const blob = (t) => [t.title, ...t.speakers.map((s) => s.name), t.room, t.track, t.s && t.s.tldr, ...((t.s && t.s.tech) || []), ...(t.keywords || [])]
  .join(" ").toLowerCase();

// where a search term was found, as a short highlighted snippet (title matches need none)
function why(t, terms) {
  if (terms.every((w) => t.title.toLowerCase().includes(w))) return null;
  const s = t.s || {};
  const fields = [["Speaker", speakers(t)], ["Tools", (s.tech || []).join(", ")], ["Topics", (t.keywords || []).join(", ")], ["Summary", s.tldr || ""], ["Abstract", (t.abstract || []).join(" ")]];
  for (const [name, text] of fields) {
    const lower = text.toLowerCase(), w = terms.find((x) => lower.includes(x));
    if (!w) continue;
    const i = lower.indexOf(w);
    const a = i;                                                     // start at the match, so it's always in view
    if (name === "Tools" || name === "Topics" || name === "Speaker") {        // lists: the matching item first, then whole items
      const items = text.split(/,\s*/), hit = items.find((x) => x.toLowerCase().includes(w));
      const more = items.length - 1;
      return el("span", { class: "why" }, el("b", { text: `${name}: ` }), el("mark", { text: hit }), more > 0 && name !== "Speaker" ? ` +${more} more` : "");
    }
    const word = text.slice(i).match(/^\S+/)[0].replace(/[,.;:]$/, "");    // the whole matched word, e.g. "Kotlin"
    return el("span", { class: "why" }, el("b", { text: `${name}: ` }), a > 0 ? "…" : "", el("mark", { text: word }), text.slice(i + word.length, i + word.length + 70));
  }
  return null;
}
function card(t, { when: showWhen = null, terms = null } = {}) {
  const n = roomNo(t), on = walkable.has(n);
  const label = showWhen === "day" ? `${fShort.format(new Date(t.start))}, ${fTime.format(new Date(t.start))}` : showWhen === "time" ? fTime.format(new Date(t.start))
    : /^BOF/.test(t.room || "") ? "Downstairs" : typeLabel(t);
  const hint = terms && why(t, terms);
  return el("button", { class: `card${on ? "" : " is-off"}`, type: "button", onclick: () => goTalk(t),
      "aria-label": [t.title, speakers(t), t.room, showWhen ? when(t) : null, on ? "walks you to your seat" : null].filter(Boolean).join(", ") },
    el("span", { class: "room" }, n ? el("span", { class: "where" }, el("small", { text: "Room" }), el("b", { text: String(n) })) : el("span", { class: "where" }, el("b", { class: "is-text", text: t.room || "Room TBC" })),
      el("span", { class: "label", text: label })),
    el("span", { class: "title", text: t.title }),
    el("span", { class: "who", text: speakers(t) }),
    hint);
}

function programme(tall) {
  const search = el("input", { class: "search", type: "search", placeholder: tall ? "Search talks, speakers, topics" : "Search", "aria-label": "Search all talks", value: query });
  const dayRow = el("div", { class: "strip days", role: "group", "aria-label": "Day" });
  const timeRow = el("div", { class: "strip times", role: "group", "aria-label": "Start time" });
  const nav = el("div", { class: "nav" }, tall ? dayRow : null, timeRow);
  const body = el("div", { class: "slot" });
  const panel = el("section", { class: `face prog is-lcd${tall ? " is-tall" : ""}`, "aria-label": "Programme" },
    el("div", { class: "prog-head" },
      el("h1", { class: "brand", "aria-label": "Devoxx Belgium 2026, 5 to 9 October" }, el("span", {}, "DEVOX", el("span", { class: "x", text: "X" })),
        el("small", { text: "Belgium 2026, summarised" })),
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
      if (face) for (const s of panel.querySelectorAll(".scroller")) watchScroll(s);
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
    const fill = here.length < (tall ? 4 : 8) ? later.slice(0, (tall ? 6 : 8) - here.length) : [];
    const cards = el("div", { class: `cards scroller${tall ? "" : fill.length ? " is-packed" : " is-exact"}`, tabindex: "-1" },
      here.map((t) => {
        const c = card(t, { when: fill.length ? "time" : null });
        if (fill.length) c.classList.add(here.length === 1 ? "is-now-wide" : "is-now");   // a lone talk takes the whole row
        if (fill.length && here.length === 1 && t.s && t.s.tldr) c.append(el("span", { class: "gist", text: t.s.tldr }));
        return c;
      }),
      fill.length ? el("div", { class: "later", text: "Later that day" }) : null, fill.map((t) => card(t, { when: "time" })));
    put(body, el("div", { class: "slot-head" }, el("b", { text: fTime.format(new Date(slot)) }),
        el("span", { text: `${fDayLong.format(new Date(slot))}, ${here.length} ${here.length === 1 ? "session" : "sessions"}. Pick one to read its summary.` })),
      cards);
    rove(dayRow); rove(timeRow);
    requestAnimationFrame(() => { centre(timeRow); if (tall) centre(dayRow); for (const s of panel.querySelectorAll(".strip, .scroller")) watchScroll(s); });
  }
  search.addEventListener("input", () => { query = search.value.trim().toLowerCase(); draw(); });
  draw();
  return panel;
}

// ---------- the talk ----------
const toSeconds = (at) => { const [m, sec] = String(at).split(":").map(Number); return (m || 0) * 60 + (sec || 0); };
function talkScreen(t, tall, onFloor, doorRoom = null) {
  const s = t.s || {};
  const tabs = [["short", "In short"], ["points", "Key points"], ["monday", "What to try"], ["chapters", "Chapters"], ["story", "Full summary"]]
    .filter(([id]) => (id === "short" && tall && s.tldr) || (id === "points" && s.keyPoints && s.keyPoints.length) || (id === "monday" && s.takeaways && s.takeaways.length)
      || (id === "chapters" && s.chapters && s.chapters.length && onFloor) || id === "story");
  const pane = el("div", { class: "pane scroller", tabindex: "0", "aria-label": "Talk details" });
  const tabRow = el("div", { class: `tabs${tall ? " strip" : ""}`, role: "group", "aria-label": "Talk details" });
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
  const watch = () => t.videoId
    ? (EMBED && onFloor ? el("button", { class: "btn is-main", type: "button", text: "Play the recording", onclick: () => playAt(0) })
      : el("a", { class: "btn is-main", href: ytUrl(t), target: "_blank", rel: "noopener", text: "Watch on YouTube" }))
    : null;
  const intro = () => {
    main.textContent = "";
    put(main,
      el("div", { class: "meta", text: [doorRoom && tall ? null : (!onFloor && /^BOF/.test(t.room || "") ? `${t.room} (downstairs)` : t.room),
        whenShort(t), typeLabel(t)].filter(Boolean).map((x) => x.replace(/ /g, "\u00a0")).join(", ") }),
      el("h2", { text: t.title, style: `--title:${onFloor ? titleSize(t.title, 40, 30) : titleSize(t.title, 34, 26)}px;--title-s:${titleSize(t.title, 23, 19)}px` }),
      el("div", { class: "who-l", text: speakers(t, true) }),
      s.watchIf ? el("p", { class: "verdict", text: `Worth it if ${s.watchIf.replace(/^\p{Lu}/u, (c) => c.toLowerCase()).replace(/\.$/, "")}.` }) : null,
      !tall && s.tldr ? el("p", { class: "tldr", text: s.tldr }) : null,
      el("div", { class: "actions" }, watch(), el("button", { class: "btn", type: "button", text: "Back to the programme", onclick: () => goHall() }),
        t.videoId ? null : el("span", { class: "note", text: "No recording yet." })),
      null);
  };
  playAt = (sec) => {
    main.textContent = "";
    put(main, el("div", { class: "meta", text: t.title }),
      el("div", { class: "player" }, el("iframe", { src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${sec}`, title: t.title,
        allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true })),
      el("div", { class: "actions" }, el("button", { class: "btn", type: "button", text: "Close the recording", onclick: intro }),
        el("button", { class: "btn", type: "button", text: "Back to the programme", onclick: () => goHall() })));
  };
  intro();
  fill(tabs[0][0]);
  return el("section", { class: `face talk ${onFloor && !tall ? "is-projected" : "is-lcd"}${tall ? " is-tall" : ""}`, "aria-label": t.title },
    main, el("div", { class: "talk-side" }, tabRow, pane),
    tall ? el("div", { class: "foot", "aria-hidden": "true" }, el("span", {}, "DEVOX", el("span", { class: "x", text: "X" })), el("span", { text: "Belgium 2026" })) : null);
}

// ---------- moving between the hall and a seat ----------
let room = null, current = null, busy = false;

async function toHall(withWalk) {
  unmount();
  if (withWalk && room) {
    say("Back to the hall");
    const d = shape === "phone" ? doorTime(room) : null, total = shots[`walk-${room}`] ? shots[`walk-${room}`].frames / 30 : 0;
    await playClip(`walk-${room}-back`, { from: d != null && total ? Math.max(0, total - d) : 0 });
  }
  room = null; current = null;
  await showStill(shotKey("hall"));
  hideClip();
  say("");
  mount(programme(shape === "phone"), shotKey("hall"), "programme");
}

async function toSeat(t, withWalk) {
  const n = roomNo(t);
  unmount();
  if (withWalk) { say(`Walking to Room ${n}`); await playClip(`walk-${n}`, { until: shape === "phone" ? doorTime(n) : null }); }
  await showStill(shotKey(`seat-${n}`));
  hideClip();
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
  if (e.key === "Escape") { if (skipWalk) skipWalk(); else if (current) goHall(); }
});

// ---------- start ----------
const deep = /^#talk-(\d+)$/.exec(location.hash);
const first = deep && talks.find((t) => t.id === Number(deep[1]));
if (first) await open(first, false); else await toHall(false);
loading.classList.add("is-done");
// warm the cache for the walks, so the first click plays at once
for (const n of walkable) { const l = document.createElement("link"); l.rel = "prefetch"; l.href = `media/walk-${n}.mp4`; document.head.append(l); }
