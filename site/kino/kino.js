// Devoxx Kino: the Kinepolis Antwerp venue at night, rendered from Ghost Light's venue model.
// Venue coordinates are metres: +x east, +y north, +z up, floor 1 at 6.2 m.
// Three.js is y-up, so a venue point (x, y, z) maps to (x, z, -y).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const FH = 6.2;          // floor 1 above floor 0
const CLEAR = 5.4;       // floor to ceiling
const RAKE_DEPTH = 4.6;  // walls on floor 1 run down past the deepest seating rake
const TZ = "Europe/Brussels";
const params = new URLSearchParams(location.search);

// ---------- palette: photo-checked notes (charcoal walls, navy carpet, blue light) ----------
const C = {
  wall: 0x3a3d46, column: 0x2c2e35, carpetNavy: 0x161c2e, carpetHall: 0x3a3c42, stairCarpet: 0x2f3f86,
  nosing: 0x5b6aa0, concrete: 0x34363d, auditoriumFloor: 0x121318, seat: 0x6e1420, seatBack: 0x5e111b,
  vault: 0xcdc8bf, ceiling: 0x14151a, portal: 0xc61d3b, numeralPanel: 0xf0641e, led: 0x3f74ff,
  funnel: 0xf3f4f8, steel: 0xb8bcc4, signWhite: 0xf4f4f4, signOrange: 0xff6a1a, glass: 0x8fb4d8,
};

const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x07060c);
scene.fog = new THREE.FogExp2(0x07060c, 0.012);
const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.05, 400);

const v3 = (x, y, z) => new THREE.Vector3(x, z, -y);
const mat = (color, opts = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, ...opts });

// ---------- data ----------
const { venue } = await (await fetch("venue.json")).json();
const talks = (window.DEVOXX && window.DEVOXX.talks) || [];

// ---------- boxes, instanced per material ----------
const unitBox = new THREE.BoxGeometry(1, 1, 1);
const batches = new Map();
function addBox(key, material, b, bottom, top) {
  if (!(top - bottom > 0.005) || !(b.w > 0) || !(b.h > 0)) return;
  if (!batches.has(key)) batches.set(key, { material, matrices: [] });
  const m = new THREE.Matrix4().compose(
    v3(b.x + b.w / 2, b.y + b.h / 2, (bottom + top) / 2),
    new THREE.Quaternion(),
    new THREE.Vector3(b.w, top - bottom, b.h));
  batches.get(key).matrices.push(m);
}
const DEBUG_COLORS = params.has("debugmat");
const debugPalette = [0xff3b3b, 0x3bff6b, 0x3b7bff, 0xffe23b, 0xff3bf0, 0x3bfff0, 0xff9a3b, 0xffffff, 0x9a3bff, 0x6b6b6b];
function flushBoxes() {
  let k = 0;
  for (const [key, b] of batches) {
    if (DEBUG_COLORS) { b.material = new THREE.MeshBasicMaterial({ color: debugPalette[k++ % debugPalette.length] }); console.log("debugmat", key, "#" + b.material.color.getHexString()); }
  }
  for (const [, { material, matrices }] of batches) {
    const mesh = new THREE.InstancedMesh(unitBox, material, matrices.length);
    matrices.forEach((m, i) => mesh.setMatrixAt(i, m));
    mesh.instanceMatrix.needsUpdate = true;
    scene.add(mesh);
  }
}

const M = {
  wall: mat(C.wall, { roughness: 0.92 }),
  column: mat(C.column, { roughness: 0.9 }),
  concrete: mat(C.concrete),
  seat: mat(C.seat, { roughness: 0.95 }),
  seatBack: mat(C.seatBack, { roughness: 0.95 }),
  stair: mat(C.stairCarpet, { roughness: 1 }),
  rake: mat(0x1b1c22, { roughness: 0.95 }),
  steel: mat(C.steel, { metalness: 0.8, roughness: 0.35 }),
  sign: mat(C.signWhite, { emissive: C.signWhite, emissiveIntensity: 0.25 }),
  signAccent: mat(C.signOrange, { emissive: C.signOrange, emissiveIntensity: 0.6 }),
  signPlate: mat(0x101014),
  desk: mat(0x0d0d10, { roughness: 0.5 }),
  booth: mat(0xd8d8dc),
  chair: mat(0x3a3a40),
  glazing: new THREE.MeshPhysicalMaterial({ color: C.glass, roughness: 0.05, transmission: 0, transparent: true, opacity: 0.18 }),
  screen: mat(0x0e0f14, { emissive: 0x1a1d2a, emissiveIntensity: 1 }),
  paving: mat(0x2c2d31),
};

// Ghost Light: a piece's base and height are its bottom and top above the plate it stands on
// (the smallest room containing it), except pieces cut to a flight (linkId), measured from the datum.
function groundAt(floor, x, y) {
  let best, area = Infinity;
  for (const r of venue.rooms) {
    const b = r.bounds;
    if (r.floor !== floor || x < b.x || x > b.x + b.w || y < b.y || y > b.y + b.h) continue;
    if (b.w * b.h < area) { best = r; area = b.w * b.h; }
  }
  return (best && best.elevation) || 0;
}
const plateUnder = (p) => p.linkId ? 0 : groundAt(p.floor, p.bounds.x + p.bounds.w / 2, p.bounds.y + p.bounds.h / 2);

// Walls and columns: Ghost Light keeps them low (3.2 m) for its isometric camera; ours run floor
// to ceiling, and on floor 1 down past the seating rakes so auditoriums are closed rooms.
const auditoriums = venue.rooms.filter((r) => r.kind === "auditorium" && r.floor === 1);
for (const o of venue.obstacles) {
  if (o.hidden) continue;   // collision-only volumes (seat blocks), never drawn
  const datum = o.floor * FH;
  const tall = o.height >= 3 && !o.linkId;   // treads cut to a flight can be 3 m up and are not walls
  const isColumn = tall && o.bounds.w < 1.2 && o.bounds.h < 1.2;
  const under = datum + plateUnder(o);
  const bottom = tall && o.floor === 1 ? datum - RAKE_DEPTH : under + (o.base || 0);
  let top = tall ? datum + CLEAR : under + o.height;
  // Auditorium rakes on floor 1 dip as low as 2 m above floor 0: ground-floor walls under them stop short.
  if (o.floor === 0) for (const a of auditoriums) {
    const b = a.bounds, ob = o.bounds;
    if (ob.x < b.x + b.w && ob.x + ob.w > b.x && ob.y < b.y + b.h && ob.y + ob.h > b.y) top = Math.min(top, FH - (a.rake || 0) - 0.35);
  }
  const key = isColumn ? "column" : tall ? "wall" : (o.material && M[o.material] ? o.material : "low");
  addBox(key, M[key] || M.concrete, o.bounds, bottom, top);
}

const STAIRS = new Set(["grand-stair", "stair-west", "stair-east", "hall-steps", "bof-1-steps", "bof-2-steps"]);
for (const d of venue.decor) {
  const under = d.floor * FH + plateUnder(d);
  const bottom = under + (d.base || 0);
  const top = under + d.height;
  let key = d.material || (d.linkId ? (STAIRS.has(d.linkId) ? "stair" : "rake") : "concrete");
  if (d.material === "floorBelow") continue;
  if (d.material === "structure") key = "rake";
  const m = M[key] || M.concrete;
  addBox(key, m, d.bounds, bottom, top);
}

// ---------- floors (with stairwell voids) and the ceiling ----------
// A floor plate minus its voids. Voids often touch the room's outline (a rake runs wall to wall),
// which shape triangulation silently ignores, so cut the rectangle into cells instead of using holes.
function subtractRects(b, holes) {
  const xs = new Set([b.x, b.x + b.w]), ys = new Set([b.y, b.y + b.h]);
  for (const h of holes) {
    for (const x of [h.x, h.x + h.w]) if (x > b.x && x < b.x + b.w) xs.add(x);
    for (const y of [h.y, h.y + h.h]) if (y > b.y && y < b.y + b.h) ys.add(y);
  }
  const X = [...xs].sort((a, c) => a - c), Y = [...ys].sort((a, c) => a - c), out = [];
  for (let j = 0; j < Y.length - 1; j++) {
    let run = null;
    for (let i = 0; i < X.length - 1; i++) {
      const mx = (X[i] + X[i + 1]) / 2, my = (Y[j] + Y[j + 1]) / 2;
      const inHole = holes.some((h) => mx > h.x && mx < h.x + h.w && my > h.y && my < h.y + h.h);
      if (!inHole && run) run.w = X[i + 1] - run.x;
      else if (!inHole) run = { x: X[i], y: Y[j], w: X[i + 1] - X[i], h: Y[j + 1] - Y[j] };
      else if (run) { out.push(run); run = null; }
    }
    if (run) out.push(run);
  }
  return out;
}
function plate(b, z, material, holes = []) {
  const meshes = subtractRects(b, holes).map((r) => {
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(r.w, r.h), material);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.copy(v3(r.x + r.w / 2, r.y + r.h / 2, z));
    scene.add(mesh);
    return mesh;
  });
  return meshes;
}
const floorMat = {
  corridor: mat(C.carpetNavy, { roughness: 1, side: THREE.DoubleSide }),
  foyer: mat(C.carpetNavy, { roughness: 1, side: THREE.DoubleSide }),
  landing: mat(C.carpetNavy, { roughness: 1, side: THREE.DoubleSide }),
  hall: mat(C.carpetHall, { roughness: 1 }),
  auditorium: mat(C.auditoriumFloor, { roughness: 1 }),
  stage: mat(0x0b0b0e, { roughness: 0.6 }),
  service: mat(0x2e3036),
  outside: M.paving,
};
for (const r of venue.rooms) {
  const z = r.floor * FH + (r.elevation || 0);
  const material = (r.kind === "foyer" && r.floor === 0) ? mat(0x34363c, { roughness: 1 }) : (floorMat[r.kind] || floorMat.service);
  plate(r.bounds, z, material, r.voids || []);
}
const ceilMat = mat(C.ceiling, { roughness: 1, side: THREE.DoubleSide });
const ceilings = venue.extents.flatMap((e) => plate(e, FH + CLEAR, ceilMat));

// ---------- the cinema corridor: pale vault coves, blue LED lines, warm downlights ----------
const corridor = venue.rooms.find((r) => r.id === "corridor").bounds;
const vaultMat = mat(C.vault, { roughness: 0.9, side: THREE.DoubleSide });
const ledMat = new THREE.MeshBasicMaterial({ color: C.led });
ledMat.color.multiplyScalar(2.2);
{
  const len = corridor.h, cy = corridor.y + len / 2, R = 1.3;
  for (const side of [-1, 1]) {
    // a quarter-cylinder cove springing from the wall head up to the ceiling
    const geo = new THREE.CylinderGeometry(R, R, len, 24, 1, true, side < 0 ? 0 : Math.PI * 1.5, Math.PI / 2);
    const cove = new THREE.Mesh(geo, vaultMat);
    cove.rotation.x = Math.PI / 2;
    const wallX = side < 0 ? corridor.x : corridor.x + corridor.w;
    cove.position.copy(v3(wallX - side * R, cy, FH + CLEAR - R));
    cove.rotation.y = 0;
    scene.add(cove);
    const strip = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, len), ledMat);
    strip.position.copy(v3(wallX - side * (R + 0.05), cy, FH + CLEAR - 0.04));
    scene.add(strip);
  }
}
const lights = [];
function point(color, intensity, distance, x, y, z) {
  const l = new THREE.PointLight(color, intensity, distance, 2);
  l.position.copy(v3(x, y, z));
  scene.add(l);
  lights.push(l);
  return l;
}
const cx = corridor.x + corridor.w / 2;
// the reception concourse at the foot of the grand stair: warm pendants
{
  const g = venue.links.find((l) => l.id === "grand-stair").bounds;
  for (const fx of [g.x + 2, g.x + g.w / 2, g.x + g.w - 2]) point(0xffe2c4, 60, 14, fx, g.y - 4, 1.2 + 4.2);
}
// cool downlights down the middle, blue washes on the coves, as in the evening photos
for (let y = -44; y <= 62; y += 12) point(0xdfe3f5, 110, 18, cx, y, FH + CLEAR - 0.5);
for (let y = -40; y <= 60; y += 20) for (const x of [corridor.x + 1.5, corridor.x + corridor.w - 1.5]) point(0x3358ff, 70, 9, x, y, FH + CLEAR - 0.9);
scene.add(new THREE.HemisphereLight(0x4656a0, 0x0c0c14, params.has("bright") ? 6 : 0.6));

// ---------- tensile funnel canopies over the grand staircase, uplit blue ----------
const grand = venue.links.find((l) => l.id === "grand-stair").bounds;
{
  const pts = [];
  for (let i = 0; i <= 24; i++) {
    const t = i / 24;
    pts.push(new THREE.Vector2(0.12 + 2.8 * Math.pow(t, 2.6), t * 3.0));
  }
  const geo = new THREE.LatheGeometry(pts, 48);
  const funnelMat = mat(C.funnel, { roughness: 0.7, side: THREE.DoubleSide, emissive: 0x6f8cff, emissiveIntensity: 0.02 });
  const fy = grand.y + grand.h + 1.8;   // over the top landing, as in the photos
  for (const fx of [grand.x + grand.w * 0.17, grand.x + grand.w * 0.5, grand.x + grand.w * 0.83]) {
    const f = new THREE.Mesh(geo, funnelMat);
    f.position.copy(v3(fx, fy, FH + CLEAR - 3.0));
    scene.add(f);
    point(0x4a7dff, 90, 9, fx, fy, FH + 0.6);
  }
}

// ---------- steps: Ghost Light keeps stairs and seating rakes as links (rise, riser, direction) and
// builds their treads in its renderer, so build them here: solid terraces and carpeted treads ----------
const terrace = mat(0x1d2030, { roughness: 1 });
const nosing = mat(0x5d6694, { roughness: 0.8 });
for (const L of venue.links) {
  if (!(L.riser > 0)) continue;
  const datum = L.from * FH, b = L.bounds, n = Math.round(L.rise / L.riser);
  const alongX = L.axis === "x", len = alongX ? b.w : b.h, going = len / n;
  const isRake = L.id.startsWith("rake-");
  for (let i = 0; i < n; i++) {
    const top = datum + L.base + (L.ascending ? (i + 1) : (n - i)) * L.riser;
    const slice = alongX ? { x: b.x + i * going, y: b.y, w: going, h: b.h } : { x: b.x, y: b.y + i * going, w: b.w, h: going };
    addBox(isRake ? "terrace" : "stair", isRake ? terrace : M.stair, slice, datum + L.base - 0.3, top);
    if (!isRake) {
      // the lighter stripe on the edge you step up onto
      const edge = L.ascending ? 0 : going - 0.05;
      const strip = alongX ? { x: slice.x + edge, y: b.y, w: 0.05, h: b.h } : { x: b.x, y: slice.y + edge, w: b.w, h: 0.05 };
      addBox("nosing", nosing, strip, top - 0.004, top + 0.006);
    }
  }
}

// ---------- grand staircase rails, splitting it into three runs ----------
{
  const L = venue.links.find((l) => l.id === "grand-stair");
  const b = L.bounds;
  const railMat = M.steel, r = 0.025;
  const z0 = L.base, z1 = L.base + L.rise, y0 = L.ascending ? b.y : b.y + b.h, y1 = L.ascending ? b.y + b.h : b.y;
  const len = Math.hypot(b.h, L.rise);
  const tube = new THREE.CylinderGeometry(r, r, len, 10);
  for (const x of [b.x + 0.15, b.x + b.w / 3, b.x + (2 * b.w) / 3, b.x + b.w - 0.15]) {
    for (const hgt of [0.95, 0.5]) {
      const rail = new THREE.Mesh(tube, railMat);
      const mid = v3(x, (y0 + y1) / 2, (z0 + z1) / 2 + hgt);
      rail.position.copy(mid);
      rail.lookAt(v3(x, y1, z1 + hgt));
      rail.rotateX(Math.PI / 2);
      scene.add(rail);
    }
    const posts = 6;
    for (let k = 0; k <= posts; k++) {
      const f = k / posts, post = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.95, 8), railMat);
      post.position.copy(v3(x, y0 + (y1 - y0) * f, z0 + (z1 - z0) * f + 0.475));
      scene.add(post);
    }
  }
}

// ---------- fonts and canvas signage ----------
await Promise.all([
  document.fonts.load('900 300px "Big Shoulders Display"'),
  document.fonts.load('800 60px "Big Shoulders Display"'),
  document.fonts.load('400 40px "Source Serif 4"'),
]).catch(() => {});

function canvasTexture(w, h, draw) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
function wrap(ctx, text, maxW) {
  const words = text.split(/\s+/), lines = [];
  let line = "";
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width > maxW && line) { lines.push(line); line = w; } else line = test;
  }
  if (line) lines.push(line);
  return lines;
}

const fmtTime = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" });
const dayKey = (iso) => new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date(iso));
const DAY = params.get("day") || "2026-10-07";

function scheduleTexture(roomNo) {
  const list = talks.filter((t) => t.room === `Room ${roomNo}` && t.start && dayKey(t.start) === DAY)
    .sort((a, b) => a.start.localeCompare(b.start));
  return canvasTexture(600, 1000, (ctx, w, h) => {
    ctx.fillStyle = "#0d1022"; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#1c2a6b"; ctx.fillRect(0, 0, w, 120);
    ctx.fillStyle = "#fff"; ctx.font = '800 64px "Big Shoulders Display"';
    ctx.fillText(`Room ${roomNo}`, 36, 84);
    ctx.font = '400 26px "Source Serif 4"'; ctx.fillStyle = "#b8c3ff";
    ctx.fillText(list[0] ? fmtDay.format(new Date(list[0].start)) : "No sessions today", 36, 160);
    let y = 210;
    for (const t of list) {
      if (y > h - 80) break;
      ctx.fillStyle = "#FFC93C"; ctx.font = '800 40px "Big Shoulders Display"';
      ctx.fillText(fmtTime.format(new Date(t.start)), 36, y + 30);
      ctx.fillStyle = "#fff"; ctx.font = '800 34px "Big Shoulders Display"';
      const lines = wrap(ctx, t.title, w - 170).slice(0, 2);
      lines.forEach((ln, i) => ctx.fillText(ln, 140, y + 30 + i * 36));
      ctx.fillStyle = "#9aa3c9"; ctx.font = '400 22px "Source Serif 4"';
      ctx.fillText(t.speakers.map((s) => s.name).join(", ").slice(0, 44), 140, y + 30 + lines.length * 36 + 4);
      y += 54 + lines.length * 36 + 22;
    }
  });
}
function numeralTexture(n) {
  return canvasTexture(512, 820, (ctx, w, h) => {
    ctx.fillStyle = "#f0641e"; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#fff"; ctx.font = `900 ${n >= 10 ? 520 : 700}px "Big Shoulders Display"`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(String(n), w / 2, h / 2 + 30);
  });
}

// ---------- auditorium entrances: red box portal, ring handles, numeral panel, schedule stand ----------
const portalMat = mat(C.portal, { roughness: 0.6, emissive: C.portal, emissiveIntensity: 0.12 });
const doorMat = mat(0x1a1416, { roughness: 0.55 });
const ringGeo = new THREE.TorusGeometry(0.34, 0.025, 12, 48);
const doors = [];
for (const r of venue.rooms.filter((x) => x.kind === "auditorium")) {
  const n = Number(r.label.replace(/\D/g, ""));
  const west = r.bounds.x < corridor.x;                // west rooms open east into the corridor
  const wallX = west ? r.bounds.x + r.bounds.w : r.bounds.x;
  const face = west ? 1 : -1;                          // +1 faces east
  const margin = (r.doorMargin ?? 1.2) + 1.25;
  const yc = r.doorSide === "low" ? r.bounds.y + margin : r.bounds.y + r.bounds.h - margin;
  const along = r.doorSide === "low" ? 1 : -1;         // direction along the wall, away from the door end
  const g = new THREE.Group();
  g.position.copy(v3(wallX + face * 0.16, yc, FH));
  g.rotation.y = face > 0 ? Math.PI / 2 : -Math.PI / 2; // local +z points into the corridor
  // portal frame: a red box around the doors, standing proud of the wall
  const frame = new THREE.Mesh(new THREE.BoxGeometry(3.1, 3.5, 0.55), portalMat);
  frame.position.set(0, 1.75, 0.27);
  const recess = new THREE.Mesh(new THREE.BoxGeometry(2.3, 2.7, 0.1), doorMat);
  recess.position.set(0, 1.35, 0.56);
  g.add(frame, recess);
  for (const dx of [-0.42, 0.42]) {
    const ring = new THREE.Mesh(ringGeo, M.steel);
    ring.position.set(dx, 1.25, 0.63);
    g.add(ring);
  }
  // big numeral panel beside the portal
  const panel = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 3.05),
    new THREE.MeshStandardMaterial({ map: numeralTexture(n), emissive: 0xffffff, emissiveMap: numeralTexture(n), emissiveIntensity: 0.12, roughness: 0.8 }));
  const side = -along * (face > 0 ? 1 : -1);          // local x towards the long stretch of wall
  panel.position.set(side * 2.75, 1.85, 0.03);
  g.add(panel);
  // blue LED line over the portal
  const led = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.05, 0.05), ledMat);
  led.position.set(0, 3.55, 0.56);
  g.add(led);
  // schedule screen on a stand, on the other side of the portal
  const stand = new THREE.Group();
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 1.2, 12), M.steel);
  pole.position.y = 0.6;
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.02, 24), M.steel);
  const tex = scheduleTexture(n);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.66, 1.1),
    new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
  screen.position.y = 1.75;
  const bezel = new THREE.Mesh(new THREE.BoxGeometry(0.72, 1.16, 0.04), M.desk);
  bezel.position.set(0, 1.75, -0.025);
  stand.add(pole, foot, bezel, screen);
  stand.position.set(-side * 2.4, 0, 1.2);
  stand.rotation.y = side * 0.35;
  g.add(stand);
  scene.add(g);
  doors.push({ n, room: r, group: g, wallX, yc, face });
}

// ---------- cinema screens: the session on now, as a title card ----------
const SLOT = params.get("at") || "2026-10-07T12:00:00Z";
function sessionIn(roomNo) {
  const list = talks.filter((t) => t.room === `Room ${roomNo}` && t.start && dayKey(t.start) === DAY)
    .sort((a, b) => a.start.localeCompare(b.start));
  return list.find((t) => t.start <= SLOT && t.end > SLOT) || list.find((t) => t.start > SLOT) || list[list.length - 1];
}
function titleCard(t) {
  return canvasTexture(2048, 776, (ctx, w, h) => {
    const g = ctx.createLinearGradient(0, 0, w, h);
    g.addColorStop(0, "#1b1440"); g.addColorStop(1, "#07060c");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#FFC93C"; ctx.font = '800 54px "Big Shoulders Display"';
    if (!t) { ctx.fillText("Devoxx Belgium 2026", 120, 200); return; }
    ctx.fillText(`${t.type}, ${fmtTime.format(new Date(t.start))}`, 120, 150);
    ctx.fillStyle = "#fff"; ctx.font = '900 118px "Big Shoulders Display"';
    const lines = wrap(ctx, t.title, w - 240).slice(0, 3);
    lines.forEach((ln, i) => ctx.fillText(ln, 120, 290 + i * 124));
    ctx.fillStyle = "#c9c3e6"; ctx.font = '400 50px "Source Serif 4"';
    ctx.fillText(t.speakers.map((sp) => sp.name).join(", "), 120, 290 + lines.length * 124 + 40);
  });
}
const screenPlanes = new Map();
for (const d of venue.decor.filter((x) => x.material === "screen" && x.room)) {
  const room = venue.rooms.find((r) => r.id === d.room);
  if (!room || room.floor !== 1) continue;
  const n = Number(room.label.replace(/\D/g, ""));
  const west = room.bounds.x < corridor.x;
  const b = d.bounds, z0 = FH + plateUnder(d) + (d.base || 0), z1 = FH + plateUnder(d) + d.height;
  const w = b.h, hgt = Math.min(z1 - z0, w * 776 / 2048);
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, hgt),
    new THREE.MeshBasicMaterial({ map: titleCard(sessionIn(n)), toneMapped: false, color: 0xd8d8d8 }));
  const faceX = west ? b.x + b.w + 0.01 : b.x - 0.01;
  plane.position.copy(v3(faceX, b.y + b.h / 2, (z0 + z1) / 2));
  plane.rotation.y = west ? Math.PI / 2 : -Math.PI / 2;
  scene.add(plane);
  screenPlanes.set(n, plane);
}

// ---------- close every auditorium floor to ceiling (Ghost Light's walls stop at 3.2 m), door left open ----------
for (const d of doors) {
  const b = d.room.bounds, t = 0.3, lo = FH - RAKE_DEPTH, hi = FH + CLEAR;
  const corridorX = d.face > 0 ? b.x + b.w - t : b.x, farX = d.face > 0 ? b.x : b.x + b.w - t;
  addBox("wall", M.wall, { x: b.x, y: b.y - t / 2, w: b.w, h: t }, lo, hi);
  addBox("wall", M.wall, { x: b.x, y: b.y + b.h - t / 2, w: b.w, h: t }, lo, hi);
  addBox("wall", M.wall, { x: farX, y: b.y, w: t, h: b.h }, lo, hi);
  const gap0 = d.yc - 1.15, gap1 = d.yc + 1.15;
  addBox("wall", M.wall, { x: corridorX, y: b.y, w: t, h: gap0 - b.y }, lo, hi);
  addBox("wall", M.wall, { x: corridorX, y: gap1, w: t, h: b.y + b.h - gap1 }, lo, hi);
  addBox("wall", M.wall, { x: corridorX, y: gap0, w: t, h: gap1 - gap0 }, FH + 2.7, hi);   // over the door
}

flushBoxes();

// ---------- the room you are in: a small pool of lights moved there, so the shader cost stays flat ----------
const roomLights = [point(0xffe0c0, 0, 30, 0, 0, 0), point(0xffe0c0, 0, 30, 0, 0, 0), point(0x8fa8ff, 0, 26, 0, 0, 0)];
function lightRoom(room) {
  const b = room.bounds, west = b.x < corridor.x;
  const screenX = west ? b.x + 1 : b.x + b.w - 1, backX = west ? b.x + b.w - 3 : b.x + 3;
  const [a, c, s] = roomLights;
  a.position.copy(v3((screenX + backX) / 2, b.y + b.h * 0.3, FH + CLEAR - 0.6)); a.intensity = 140;
  c.position.copy(v3((screenX + backX) / 2, b.y + b.h * 0.7, FH + CLEAR - 0.6)); c.intensity = 140;
  s.position.copy(v3(screenX + (west ? 3 : -3), b.y + b.h / 2, FH + 1)); s.intensity = 160; // spill from the screen
}

// ---------- post-processing: bloom for the LEDs, screens and signs ----------
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.55, 0.6, 0.82);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---------- views (matched to the reference photos) ----------
const door = (n) => doors.find((d) => d.n === n);
const VIEWS = {
  corridor: { pos: [cx, -44, FH + 1.7], look: [cx, 10, FH + 1.9], fov: 62 },
  stairs: { pos: [grand.x + grand.w * 0.42, grand.y + grand.h * 0.3, 1.2 + 5 * 0.3 + 2.6], look: [grand.x + grand.w * 0.5, grand.y + grand.h + 8, FH + 1.8], fov: 70 },
  stairtop: { pos: [grand.x + grand.w * 0.45, grand.y + grand.h + 0.6, FH + 2.4], look: [grand.x + grand.w * 0.5, grand.y + 2, 1.2], fov: 70 },
  door5: (() => { const d = door(5); return { pos: [d.wallX + d.face * 7, d.yc - 4, FH + 1.6], look: [d.wallX, d.yc + 1, FH + 1.7], fov: 60 }; })(),
  seat8: (() => {
    // a real seat two-thirds of the way up room 8's rake, eyes 1.15 m over the pan
    const r = door(8).room.bounds;
    const seats = venue.decor.filter((d) => d.material === "seat" && d.floor === 1 &&
      d.bounds.x > r.x && d.bounds.x < r.x + r.w && d.bounds.y > r.y && d.bounds.y < r.y + r.h);
    const midY = r.y + r.h / 2;
    seats.sort((a, b) => a.bounds.x - b.bounds.x);
    const xs = [...new Set(seats.map((d) => d.bounds.x.toFixed(1)))];
    const rowX = Number(xs[Math.floor(xs.length * 0.22)]);
    const seat = seats.filter((d) => Math.abs(d.bounds.x - rowX) < 0.2)
      .sort((a, b) => Math.abs(a.bounds.y - midY) - Math.abs(b.bounds.y - midY))[0];
    const sx = seat.bounds.x + seat.bounds.w / 2, sy = seat.bounds.y + seat.bounds.h / 2;
    const sz = FH + seat.height + 0.8;    // pan top, then seated eye height above it
    const screen = venue.decor.find((d) => d.material === "screen" && d.room === "aud-8");
    const lx = screen ? screen.bounds.x + screen.bounds.w / 2 : r.x + r.w;
    const lz = screen ? FH + (screen.base + screen.height) / 2 : sz;
    return { pos: [sx, sy, sz], look: [lx, sy, lz], fov: 58 };
  })(),
};
VIEWS.room8 = (() => { const r = door(8).room.bounds; return { pos: [r.x + 2, r.y + 2, FH + 4.8], look: [r.x + r.w, r.y + r.h, FH - 2.5], fov: 75 }; })();
VIEWS.side8 = (() => { const r = door(8).room.bounds; return { pos: [r.x + r.w / 2, r.y - 25, FH + 1], look: [r.x + r.w / 2, r.y + r.h / 2, FH - 1], fov: 60, plan: true, cutaway: r }; })();
VIEWS.plan = { pos: [cx, -10, 120], look: [cx, -9.9, 0], fov: 60, plan: true };
// ---------- run: the experience by default, free-look camera views with ?dev or ?view ----------
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});
document.getElementById("loading").remove();

const devMode = params.has("dev") || params.has("view");
let tick = () => {};
if (devMode) {
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  const setView = (name) => {
    const v = VIEWS[name] || VIEWS.corridor;
    for (const c of ceilings) c.visible = !v.plan;
    if (v.cutaway) camera.near = 24.5;
    scene.fog.density = v.plan ? 0 : 0.012;
    const inRoom = auditoriums.find((r) =>
      v.pos[0] > r.bounds.x && v.pos[0] < r.bounds.x + r.bounds.w && v.pos[1] > r.bounds.y && v.pos[1] < r.bounds.y + r.bounds.h);
    if (inRoom) lightRoom(inRoom); else for (const l of roomLights) l.intensity = 0;
    camera.position.copy(v3(...v.pos));
    camera.fov = v.fov;
    camera.updateProjectionMatrix();
    controls.target.copy(v3(...v.look));
    controls.update();
    for (const b of document.querySelectorAll("#dev button")) b.setAttribute("aria-pressed", String(b.dataset.view === name));
  };
  const dev = document.getElementById("dev");
  for (const name of Object.keys(VIEWS)) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = name; b.dataset.view = name;
    b.addEventListener("click", () => setView(name));
    dev.append(b);
  }
  setView(params.get("view") || "corridor");
  tick = () => controls.update();
} else {
  document.getElementById("dev").remove();
  const { startExperience } = await import("./experience.js");
  tick = startExperience({ THREE, scene, camera, renderer, v3, venue, talks, doors, corridor, auditoriums,
    FH, CLEAR, lightRoom, roomLights, point, ledMat, mat, M, params, plateUnder, screenPlanes });
}

window.__renderOnce = () => { composer.render(); if (window.__css) window.__css(); };
// ?still renders a couple of frames and stops: for headless screenshots on software WebGL.
const still = params.has("still");
let frames = 0;
renderer.setAnimationLoop((t) => {
  tick(t);
  composer.render();
  if (window.__css) window.__css();
  if (++frames === 2) {
    window.__ready = true;
    if (still) renderer.setAnimationLoop(null);
  }
});
