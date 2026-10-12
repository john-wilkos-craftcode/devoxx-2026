// The diegetic layer: the programme on the exhibition hall's LED wall, a fast walk up the side
// stairs to the room, and the talk on the cinema screen. Reading surfaces are real HTML placed in
// 3D with CSS3DRenderer, so they stay crisp, clickable and scrollable.
import { CSS3DRenderer, CSS3DObject } from "three/addons/renderers/CSS3DRenderer.js";

const TZ = "Europe/Brussels";
const fmt = (o) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...o });
const fTime = fmt({ hour: "2-digit", minute: "2-digit" });
const fDay = fmt({ weekday: "long" });
const fShort = fmt({ weekday: "short", day: "numeric" });
const dayKey = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date(iso));
const roomNo = (t) => Number(String(t.room || "").replace(/\D/g, "")) || null;
const EMBED = window.self === window.top;   // the claude.ai artifact sandbox can't embed YouTube
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

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

const CSS = `
.kx-layer { position: fixed; inset: 0; pointer-events: none; }
.kx-layer > div { pointer-events: none; }
.kx-panel { pointer-events: auto; box-sizing: border-box; color: #EEEBF7; font-family: "Source Serif 4", Georgia, serif; -webkit-font-smoothing: antialiased; }
.kx-panel *, .kx-panel *::before, .kx-panel *::after { box-sizing: border-box; }
.kx-panel button, .kx-panel a { font: inherit; color: inherit; }
.kx-panel :focus-visible { outline: 6px solid #FFC93C; outline-offset: 4px; }

.kx-wall { width: 1600px; height: 900px; background: #05060c; padding: 44px 56px; display: grid; grid-template-rows: auto auto 1fr; gap: 22px;
  box-shadow: 0 0 0 14px #0b0c12, 0 0 120px 30px rgba(70, 110, 255, .25); }
.kx-wall-head { display: flex; align-items: baseline; gap: 28px; flex-wrap: wrap; }
.kx-wall h1 { margin: 0; font: 900 76px/0.9 "Big Shoulders Display", sans-serif; letter-spacing: .01em; }
.kx-wall-sub { color: #9aa3c9; font-size: 26px; }
.kx-days { display: flex; gap: 10px; flex-wrap: wrap; }
.kx-days button, .kx-search { background: #10132a; border: 2px solid #252b55; border-radius: 999px; padding: 10px 24px; font-size: 26px; cursor: pointer; color: #c9cdea; }
.kx-days button[aria-pressed="true"] { background: #FFC93C; color: #17122B; border-color: #FFC93C; font-weight: 600; }
.kx-search { cursor: text; width: 420px; margin-left: auto; color: #EEEBF7; }
.kx-search::placeholder { color: #6f77a3; }
.kx-slots { overflow-y: auto; padding-right: 14px; scrollbar-color: #2b3266 transparent; }
.kx-slot { display: grid; grid-template-columns: 120px 1fr; gap: 18px; padding: 16px 0; border-top: 2px solid #171b38; }
.kx-slot-time { font: 800 40px/1 "Big Shoulders Display", sans-serif; color: #FFC93C; padding-top: 6px; }
.kx-slot-talks { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.kx-talk { display: grid; grid-template-columns: 64px 1fr; gap: 14px; text-align: left; background: #0d1024; border: 2px solid #1b2047; border-radius: 12px;
  padding: 12px 14px; cursor: pointer; min-height: 112px; }
.kx-talk:hover { border-color: #FFC93C; background: #141936; }
.kx-talk .kx-room { display: grid; place-items: center; background: #f0641e; color: #fff; font: 900 40px/1 "Big Shoulders Display", sans-serif; border-radius: 6px; height: 64px; margin: 0; }
.kx-talk .kx-room.is-bof { background: #2f3f86; font-size: 22px; }
.kx-talk b { display: block; font: 800 27px/1.08 "Big Shoulders Display", sans-serif; letter-spacing: .01em; }
.kx-talk span { display: block; color: #9aa3c9; font-size: 19px; margin-top: 6px; }
.kx-empty { color: #9aa3c9; font-size: 30px; padding: 40px 0; }

.kx-screen { background: #05050a; display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 56px; padding: 56px 72px; }
.kx-meta { color: #FFC93C; font: 800 34px/1 "Big Shoulders Display", sans-serif; letter-spacing: .02em; }
.kx-screen h2 { margin: 18px 0 0; font: 900 84px/0.95 "Big Shoulders Display", sans-serif; text-wrap: balance; }
.kx-who { color: #c9c3e6; font-size: 30px; margin-top: 18px; }
.kx-tldr { font-size: 34px; line-height: 1.38; margin-top: 26px; border-left: 8px solid #FFC93C; padding-left: 26px; max-width: 30em; }
.kx-actions { display: flex; gap: 14px; margin-top: 30px; flex-wrap: wrap; }
.kx-panel .kx-btn { border: 2px solid #3a3f70; background: transparent; border-radius: 999px; padding: 12px 28px; font-size: 28px; cursor: pointer; text-decoration: none; }
.kx-panel .kx-btn:hover { border-color: #FFC93C; }
.kx-panel .kx-btn.is-play { background: #FFC93C; color: #17122B; border-color: #FFC93C; font-weight: 600; }
.kx-side { display: grid; grid-template-rows: auto 1fr; gap: 18px; min-height: 0; }
.kx-tabs { display: flex; gap: 10px; }
.kx-tabs button { background: #10132a; border: 2px solid #252b55; border-radius: 999px; padding: 8px 22px; font-size: 26px; cursor: pointer; color: #c9cdea; }
.kx-tabs button[aria-pressed="true"] { background: #EEEBF7; color: #17122B; border-color: #EEEBF7; }
.kx-pane { overflow-y: auto; padding-right: 12px; font-size: 28px; line-height: 1.42; scrollbar-color: #2b3266 transparent; }
.kx-pane ul, .kx-pane ol { margin: 0; padding-left: 1.1em; display: grid; gap: 14px; }
.kx-pane li::marker { color: #FFC93C; }
.kx-chapter { display: grid; grid-template-columns: 110px 1fr; gap: 12px; width: 100%; text-align: left; background: none; border: 0; border-top: 2px solid #171b38; padding: 12px 0; cursor: pointer; text-decoration: none; }
.kx-chapter time { color: #FFC93C; font: 800 32px/1.1 "Big Shoulders Display", sans-serif; }
.kx-chapter:hover span { text-decoration: underline; text-decoration-color: #FFC93C; }
.kx-player { position: relative; width: 100%; aspect-ratio: 16 / 9; background: #000; border-radius: 10px; overflow: hidden; }
.kx-player iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
.kx-note { color: #9aa3c9; font-size: 24px; margin-top: 14px; }

.kx-hud { position: fixed; z-index: 5; left: 50%; bottom: calc(18px + env(safe-area-inset-bottom, 0px)); translate: -50% 0; pointer-events: auto;
  display: flex; gap: 8px; font: 15px/1 "Source Serif 4", Georgia, serif; }
.kx-hud button, .kx-hud a { background: rgba(14, 12, 28, .78); color: #EEEBF7; border: 1px solid #3A3060; border-radius: 999px; padding: 8px 16px; cursor: pointer; text-decoration: none; }
.kx-exit { position: fixed; z-index: 5; right: 18px; top: calc(16px + env(safe-area-inset-top, 0px)); pointer-events: auto; cursor: pointer;
  background: #0a8a3a; color: #fff; border: 0; border-radius: 4px; padding: 7px 14px 6px; font: 800 18px/1 "Big Shoulders Display", sans-serif; letter-spacing: .12em;
  box-shadow: 0 0 22px rgba(20, 220, 100, .45); }
.kx-exit[hidden] { display: none; }
.kx-skip { position: fixed; z-index: 5; left: 50%; top: calc(16px + env(safe-area-inset-top, 0px)); translate: -50% 0; color: #c9cdea; font: 15px/1 "Source Serif 4", Georgia, serif; pointer-events: none; opacity: .8; }
.kx-skip[hidden] { display: none; }
.kx-flat { position: fixed; z-index: 5; left: 18px; top: calc(14px + env(safe-area-inset-top, 0px)); color: #c9cdea; font: 15px/1 "Source Serif 4", Georgia, serif;
  background: rgba(14, 12, 28, .7); border: 1px solid #3A3060; border-radius: 999px; padding: 8px 14px; text-decoration: none; }
.kx-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
`;

export function startExperience(k) {
  const { THREE, scene, camera, renderer, v3, venue, talks, doors, corridor, auditoriums, FH, CLEAR, lightRoom, roomLights, point, plateUnder } = k;
  document.head.append(el("style", { text: CSS }));

  // ---------- CSS3D layer over the WebGL canvas ----------
  const cssScene = new THREE.Scene();
  const css = new CSS3DRenderer();
  css.setSize(innerWidth, innerHeight);
  css.domElement.className = "kx-layer";
  document.body.append(css.domElement);
  window.__css = () => css.render(cssScene, camera);
  addEventListener("resize", () => { css.setSize(innerWidth, innerHeight); refit(); });

  const live = el("p", { class: "kx-sr", "aria-live": "polite" });
  const exitBtn = el("button", { class: "kx-exit", type: "button", text: "EXIT", title: "Back to the hall (Esc)", hidden: true, onclick: () => goLobby() });
  const skipNote = el("p", { class: "kx-skip", text: "Click to skip", hidden: true });
  const flatLink = el("a", { class: "kx-flat", href: "../", text: "Plain programme" });
  document.body.append(live, exitBtn, skipNote);
  if (EMBED) document.body.append(flatLink);

  // ---------- the programme wall: the big LED screen at the north end of the exhibition hall ----------
  const WALL = { x: corridor.x + corridor.w / 2, y: 18.0, z: 3.15, w: 8, h: 4.5 };
  {
    const frame = new THREE.Mesh(new THREE.BoxGeometry(WALL.w + 0.3, WALL.h + 0.3, 0.2), k.mat(0x0b0c12, { roughness: 0.6 }));
    frame.position.copy(v3(WALL.x, WALL.y + 0.05, WALL.z));
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(WALL.w, WALL.h), new THREE.MeshBasicMaterial({ color: 0x0b1030 }));
    glow.position.copy(v3(WALL.x, WALL.y - 0.06, WALL.z));
    scene.add(frame, glow);
    point(0x6a8cff, 140, 16, WALL.x, WALL.y - 4, WALL.z);
    point(0x6a8cff, 60, 22, WALL.x, WALL.y - 12, 4.5);
  }
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
    el("div", { class: "kx-wall-head" }, el("h1", { text: "Devoxx Belgium 2026" }), el("span", { class: "kx-wall-sub", text: "Choose a session and we'll take you to your seat." })),
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
    for (const [key, group] of slots) {
      const iso = group[0].start;
      slotsBox.append(el("div", { class: "kx-slot" },
        el("div", { class: "kx-slot-time" }, fTime.format(new Date(iso)), terms.length ? el("div", { style: "font-size:20px;color:#9aa3c9;margin-top:6px", text: fShort.format(new Date(iso)) }) : null),
        el("div", { class: "kx-slot-talks" }, group.map((t) => {
          const n = roomNo(t), isRoom = auditoriums.some((r) => r.label === `Room ${n}`);
          return el("button", { class: "kx-talk", type: "button", onclick: () => goTalk(t) },
            el("span", { class: `kx-room${isRoom ? "" : " is-bof"}`, text: isRoom ? String(n) : (t.room || "?") }),
            el("span", {}, el("b", { text: t.title }), el("span", { text: t.speakers.map((s) => s.name).join(", ") })));
        }))));
    }
  }
  renderWall();
  const wallObj = new CSS3DObject(wall);
  wallObj.position.copy(v3(WALL.x, WALL.y - 0.08, WALL.z));
  wallObj.scale.setScalar(WALL.w / 1600);
  cssScene.add(wallObj);

  // ---------- camera poses ----------
  // fill: how much of the viewport the surface takes. Under 1 so the venue frames it.
  const fitDistance = (w, h, fov, fill = 0.92) => {
    const t = Math.tan(THREE.MathUtils.degToRad(fov) / 2);
    return Math.max(h / 2 / t, w / 2 / (t * camera.aspect)) / fill;
  };
  const LOBBY_FOV = 50, SEAT_FOV = 52;
  const lobbyPose = () => {
    const d = fitDistance(WALL.w, WALL.h, LOBBY_FOV, 0.8);
    return { pos: new THREE.Vector3(WALL.x, WALL.y - d, WALL.z), look: new THREE.Vector3(WALL.x, WALL.y, WALL.z), fov: LOBBY_FOV };
  };
  const toThree = (p) => v3(p.x, p.y, p.z);
  function setPose(p) {
    camera.position.copy(toThree(p.pos));
    camera.fov = p.fov; camera.updateProjectionMatrix();
    camera.lookAt(toThree(p.look));
  }

  // ---------- rooms: screen geometry and the seat that frames it ----------
  const roomInfo = new Map();
  function infoFor(n) {
    if (roomInfo.has(n)) return roomInfo.get(n);
    const door = doors.find((d) => d.n === n);
    if (!door) return null;
    const r = door.room, b = r.bounds, west = b.x < corridor.x;
    const sd = venue.decor.find((d) => d.material === "screen" && d.room === r.id);
    const sb = sd.bounds, z0 = FH + plateUnder(sd) + (sd.base || 0), z1 = FH + plateUnder(sd) + sd.height;
    const sw = sb.h, sh = Math.min(z1 - z0, sw * 776 / 2048);
    const screen = { x: west ? sb.x + sb.w + 0.03 : sb.x - 0.03, y: sb.y + sb.h / 2, z: (z0 + z1) / 2, w: sw, h: sh, west };
    const seats = venue.decor.filter((d) => d.material === "seat" && d.floor === 1 && d.bounds.x > b.x && d.bounds.x < b.x + b.w && d.bounds.y > b.y && d.bounds.y < b.y + b.h);
    const want = fitDistance(sw, sh, SEAT_FOV);
    let best = seats[0], score = Infinity;
    for (const s of seats) {
      const sx = s.bounds.x + s.bounds.w / 2, sy = s.bounds.y + s.bounds.h / 2;
      const sc = Math.abs(Math.abs(sx - screen.x) - want) + Math.abs(sy - screen.y) * 0.6;
      if (sc < score) { score = sc; best = s; }
    }
    const seat = { x: best.bounds.x + best.bounds.w / 2, y: best.bounds.y + best.bounds.h / 2, z: FH + best.height + 0.8 };
    const info = { n, door, room: r, screen, seat };
    roomInfo.set(n, info);
    return info;
  }
  const seatPose = (info) => ({ pos: info.seat, look: { x: info.screen.x, y: info.seat.y, z: info.screen.z }, fov: SEAT_FOV });

  // ---------- the cinema screen: the talk, as HTML on the screen surface ----------
  let screenObj = null, current = null, state = "lobby";
  const pane = (t, tab) => {
    const s = t.s || {};
    if (tab === "points") return el("ul", {}, (s.keyPoints || []).map((p) => el("li", { text: p })));
    if (tab === "monday") return el("ol", {}, (s.takeaways || []).map((p) => el("li", { text: p })));
    if (tab === "chapters") return el("div", {}, (s.chapters || []).map((c) => seekTo(t, c.at, el("time", { text: c.at }), el("span", { text: c.title }))));
    return el("div", {}, (s.summary || t.abstract || []).map((p) => el("p", { style: "margin:0 0 18px", text: p })));
  };
  const toSeconds = (at) => { const [m, sec] = String(at).split(":").map(Number); return (m || 0) * 60 + (sec || 0); };
  const ytUrl = (t, sec = 0) => `https://www.youtube.com/watch?v=${t.videoId}${sec ? `&t=${sec}s` : ""}`;
  let playAt = null;
  function seekTo(t, at, ...kids) {
    if (!t.videoId) return el("div", { class: "kx-chapter" }, ...kids);
    if (!EMBED) return el("a", { class: "kx-chapter", href: ytUrl(t, toSeconds(at)), target: "_blank", rel: "noopener" }, ...kids);
    return el("button", { class: "kx-chapter", type: "button", onclick: () => playAt && playAt(toSeconds(at)) }, ...kids);
  }
  function buildScreen(info, t) {
    if (screenObj) { cssScene.remove(screenObj); screenObj.element.remove(); }
    const { screen } = info;
    const pxW = 2048, pxH = Math.round(pxW * screen.h / screen.w);
    const s = t.s || {};
    const tabs = [["story", "The story"], ["points", "Key points"], ["monday", "Try this on Monday"], ["chapters", "Chapters"]]
      .filter(([id]) => id === "story" || (id === "points" && s.keyPoints && s.keyPoints.length) || (id === "monday" && s.takeaways && s.takeaways.length) || (id === "chapters" && s.chapters && s.chapters.length));
    let tab = tabs.find(([id]) => id === "points") ? "points" : "story";
    const paneBox = el("div", { class: "kx-pane" });
    const tabBox = el("div", { class: "kx-tabs", role: "group", "aria-label": "Talk details" });
    const showTab = (id) => { tab = id; paneBox.textContent = ""; paneBox.append(pane(t, id)); for (const b of tabBox.children) b.setAttribute("aria-pressed", String(b.dataset.tab === id)); };
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
          el("button", { class: "kx-btn", type: "button", text: "Back to the hall", onclick: () => goLobby() })));
    };
    playAt = (sec) => {
      left.textContent = "";
      const player = el("div", { class: "kx-player" }, el("iframe", {
        src: `https://www.youtube-nocookie.com/embed/${t.videoId}?autoplay=1&rel=0&start=${sec}`, title: t.title,
        allow: "autoplay; encrypted-media; picture-in-picture; fullscreen", allowfullscreen: true }));
      left.append(player, el("div", { class: "kx-actions" },
        el("button", { class: "kx-btn", type: "button", text: "Stop and show the summary", onclick: intro }),
        el("button", { class: "kx-btn", type: "button", text: "Back to the hall", onclick: () => goLobby() })));
      if (tabs.find(([id]) => id === "chapters")) showTab("chapters");
    };
    intro();
    showTab(tab);
    const panel = el("div", { class: "kx-panel kx-screen", style: `width:${pxW}px;height:${pxH}px` }, left, el("div", { class: "kx-side" }, tabBox, paneBox));
    screenObj = new CSS3DObject(panel);
    screenObj.position.copy(toThree(screen));
    screenObj.rotation.y = screen.west ? Math.PI / 2 : -Math.PI / 2;
    screenObj.scale.setScalar(screen.w / pxW);
    cssScene.add(screenObj);
  }

  // ---------- walking: lobby -> side stair -> corridor -> door -> seat ----------
  let anim = null;
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  function pathTo(info) {
    const west = info.screen.west;
    const stair = venue.links.find((l) => l.id === (west ? "stair-west" : "stair-east")).bounds;
    const sx = stair.x + stair.w / 2, d = info.door, face = d.face;
    const lp = lobbyPose().pos;
    const pts = [
      { x: lp.x, y: lp.y, z: lp.z },
      { x: (lp.x + sx) / 2, y: stair.y + stair.h + 2.2, z: 1.7 },
      { x: sx, y: stair.y + stair.h - 0.4, z: 1.75 },
      { x: sx, y: stair.y + 0.6, z: FH + 1.65 },
      { x: (sx + corridor.x + corridor.w / 2) / 2, y: stair.y - 2.5, z: FH + 1.7 },
      { x: d.wallX + face * 3.2, y: d.yc, z: FH + 1.7 },
      { x: d.wallX - face * 1.4, y: d.yc, z: FH + 1.65 },
      { x: info.seat.x + (west ? 1.2 : -1.2), y: (info.seat.y + d.yc) / 2, z: info.seat.z + 0.5 },
      info.seat,
    ];
    return new THREE.CatmullRomCurve3(pts.map(toThree), false, "centripetal", 0.3);
  }
  function animate(curve, finalLook, fovTo, ms, done) {
    const from = { fov: camera.fov };
    const start = performance.now();
    skipNote.hidden = false;
    anim = { done, tick(now) {
      const t = THREE.MathUtils.clamp((now - start) / ms, 0, 1), u = ease(t);
      camera.position.copy(curve.getPointAt(u));
      const ahead = curve.getPointAt(Math.min(1, u + 0.06)).clone();
      ahead.y = THREE.MathUtils.lerp(ahead.y, camera.position.y, 0.6);
      const blend = THREE.MathUtils.smoothstep(t, 0.72, 1);
      camera.lookAt(ahead.lerp(finalLook, blend));
      camera.fov = THREE.MathUtils.lerp(from.fov, fovTo, u); camera.updateProjectionMatrix();
      if (t >= 1) finish();
    } };
  }
  function finish() {
    if (!anim) return;
    const { done } = anim;
    anim = null; skipNote.hidden = true;
    done();
  }
  addEventListener("pointerdown", (e) => { if (anim && !e.target.closest(".kx-panel")) finish(); });

  function goTalk(t, { instant = false } = {}) {
    const n = roomNo(t), info = n && infoFor(n);
    current = t;
    history.replaceState(null, "", `#talk-${t.id}`);
    if (!info) {   // BOFs and labs are in rooms we don't model: show the talk on the wall instead
      live.textContent = `${t.title} is in ${t.room}, which is not part of the cinema floor.`;
      return;
    }
    buildScreen(info, t);
    lightRoom(info.room);
    for (const [n2, plane] of k.screenPlanes) plane.visible = n2 !== n;
    const arrive = () => { state = "seated"; setPose(seatPose(info)); exitBtn.hidden = false; live.textContent = `Seated in Room ${n} for ${t.title}.`; };
    if (instant || reduceMotion) { arrive(); return; }
    state = "walking";
    const curve = pathTo(info);
    const ms = Math.min(4300, 2300 + curve.getLength() * 22);
    animate(curve, toThree({ x: info.screen.x, y: info.seat.y, z: info.screen.z }), SEAT_FOV, ms, arrive);
  }
  function goLobby({ instant = false } = {}) {
    history.replaceState(null, "", location.pathname + location.search);
    exitBtn.hidden = true;
    const back = () => { state = "lobby"; setPose(lobbyPose()); for (const l of roomLights) l.intensity = 0; live.textContent = "Back in the exhibition hall."; };
    if (state !== "seated" || instant || reduceMotion || !current || !infoFor(roomNo(current))) { back(); return; }
    state = "walking";
    const pts = pathTo(infoFor(roomNo(current))).getPoints(60).reverse();
    animate(new THREE.CatmullRomCurve3(pts), toThree(lobbyPose().look), LOBBY_FOV, 2400, back);
  }
  function refit() { if (state === "lobby") setPose(lobbyPose()); else if (state === "seated" && current) setPose(seatPose(infoFor(roomNo(current)))); }
  addEventListener("keydown", (e) => { if (e.key === "Escape" && state !== "lobby") goLobby(); });

  // ---------- start: a deep link seats you straight away; otherwise one dolly in towards the wall ----------
  const m = location.hash.match(/^#talk-(\d+)$/);
  const linked = m && talks.find((t) => t.id === Number(m[1]));
  if (linked) goTalk(linked, { instant: true });
  else if (k.params.has("still") || reduceMotion) setPose(lobbyPose());
  else {
    const end = lobbyPose();
    const curve = new THREE.CatmullRomCurve3([toThree({ x: end.pos.x - 3, y: end.pos.y - 16, z: 2.4 }), toThree({ x: end.pos.x - 1, y: end.pos.y - 7, z: 2.6 }), end.pos.clone()]);
    camera.fov = LOBBY_FOV;
    animate(curve, toThree(end.look), LOBBY_FOV, 2600, () => { state = "lobby"; setPose(lobbyPose()); });
  }
  // test hooks for headless checks
  window.__kino = {
    walkFrame: (id, u) => { const t = talks.find((x) => x.id === id), info = infoFor(roomNo(t)), c = pathTo(info);
      lightRoom(info.room); camera.fov = SEAT_FOV; camera.updateProjectionMatrix();
      camera.position.copy(c.getPointAt(u)); camera.lookAt(c.getPointAt(Math.min(1, u + 0.06))); }, goTalk: (id) => goTalk(talks.find((t) => t.id === id), { instant: true }), goLobby: () => goLobby({ instant: true }) };

  // performance.now(), not the rAF timestamp: that one can be earlier than an animation's start.
  return () => { if (anim) anim.tick(performance.now()); };
}
