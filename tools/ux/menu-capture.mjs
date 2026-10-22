// Capture a hall-screen menu design the way the reviewers and builders judge it: the menu canvas at rest (laptop,
// phone, reduced motion, a short animation strip), every state the design lists in states.json, hard facts about the
// page, and the in-hall composite of every laptop/phone shot (tools/ux/inhall.py).
//   node tools/ux/menu-capture.mjs <design folder> <outDir> [--states extra.json] [--no-hall]
//
// <design folder>/states.json is an array of states reached from a fresh load:
//   { "name": "story-open", "shape": "laptop" | "phone", "steps": [ ... ] }
// steps (all optional, run in order, then the #menu canvas is photographed):
//   { "click": "css" }  { "hover": "css" }  { "press": "Key" }  { "type": "text" }  { "fill": ["css", "text"] }
//   { "wait": ms }  { "mouse": [x, y] } (relative to #menu)  { "drag": [x1, y1, x2, y2] }  { "scroll": ["css", y] }
//   { "expectVisible": "css" }  { "expectText": "text" }   (logged to facts.json as pass/fail: use them to prove a function works)
// Writes <outDir>/<name>.png (flat #menu), <name>-hall.jpg (composited into the venue render), facts.json, log.txt.
import { chromium } from "playwright-core";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

const args = process.argv.slice(2);
const flag = (k) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : null; };
const extra = flag("--states");
const noHall = args.includes("--no-hall");
const [folder, out] = args.filter((a) => !a.startsWith("--"));
if (!folder || !out) { console.log("usage: node tools/ux/menu-capture.mjs <design folder> <outDir> [--states extra.json] [--no-hall]"); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const page0 = path.resolve(folder, "index.html");
if (!fs.existsSync(page0)) { console.log(`no ${page0}`); process.exit(2); }
const url = process.env.CAPTURE_URL || "file://" + page0;   // CAPTURE_URL: an http page instead (ES modules need one)
const ROOT = path.resolve(new URL("../..", import.meta.url).pathname);

const states = [];
for (const f of [path.join(folder, "states.json"), extra].filter(Boolean)) {
  if (fs.existsSync(f)) states.push(...JSON.parse(fs.readFileSync(f, "utf8")));
}

const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [], facts = { shots: {}, expectations: [], errors };
const VIEW = { laptop: { width: 1100, height: 720 }, phone: { width: 390, height: 760 } };

async function open(shape, reduced = false, name = "") {
  const ctx = await browser.newContext({ viewport: VIEW[shape], reducedMotion: reduced ? "reduce" : "no-preference", deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: pageerror: ${e.message}`));
  await page.goto(url + (shape === "phone" ? "?shape=phone" : ""), { waitUntil: "load" });
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForFunction(() => [...document.images].every((i) => i.complete), null, { timeout: 7000 }).catch(() => {});
  await page.waitForTimeout(1800);
  return { ctx, page };
}

async function measure(page) {  // hard facts about what the menu shows right now
  return page.evaluate(() => {
    const m = document.querySelector("#menu");
    if (!m) return null;
    const r = m.getBoundingClientRect();
    let words = 0, minFont = 999, small = 0, clipped = 0;
    const walker = document.createTreeWalker(m, NodeFilter.SHOW_TEXT);
    for (let n; (n = walker.nextNode());) {
      const t = n.textContent.trim();
      if (!t) continue;
      const el = n.parentElement, cs = getComputedStyle(el), b = el.getBoundingClientRect();
      if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity === 0 || b.width < 1 || b.height < 1) continue;
      if (b.right < r.left || b.left > r.right || b.bottom < r.top || b.top > r.bottom) continue;
      words += t.split(/\s+/).length;
      const fs = parseFloat(cs.fontSize);
      if (fs < minFont) minFont = fs;
      if (fs < 14) small += t.split(/\s+/).length;
      if (b.right > r.right + 1 || b.bottom > r.bottom + 1 || b.left < r.left - 1 || b.top < r.top - 1) clipped++;
    }
    const focusables = m.querySelectorAll("a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])").length;
    return { menuSize: [Math.round(r.width), Math.round(r.height)], visibleWords: words, minFontPx: minFont === 999 ? null : minFont,
      wordsUnder14px: small, textNodesOutsideMenu: clipped, focusables, openTalkDefined: typeof window.openTalk === "function",
      scrollOverflow: [m.scrollWidth - m.clientWidth, m.scrollHeight - m.clientHeight] };
  });
}

async function snap(page, name, shape) {
  const menu = page.locator("#menu");
  if (!(await menu.count())) { errors.push(`${name}: no #menu element`); return; }
  await page.waitForTimeout(450);
  const box = await menu.boundingBox();
  await page.screenshot({ path: `${out}/${name}.png`, clip: box });
  facts.shots[name] = { shape, ...(await measure(page)) };
  console.log(`${name}.png  #menu ${Math.round(box.width)}x${Math.round(box.height)}`);
}

async function run(step, page, menu) {
  const box = await menu.boundingBox();
  if (step.click) await page.locator(step.click).first().click();
  else if (step.hover) await page.locator(step.hover).first().hover();
  else if (step.press) await page.keyboard.press(step.press);
  else if (step.type) await page.keyboard.type(step.type, { delay: 35 });
  else if (step.fill) await page.locator(step.fill[0]).first().fill(step.fill[1]);
  else if (step.wait) await page.waitForTimeout(step.wait);
  else if (step.mouse) await page.mouse.move(box.x + step.mouse[0], box.y + step.mouse[1], { steps: 6 });
  else if (step.drag) {
    await page.mouse.move(box.x + step.drag[0], box.y + step.drag[1]); await page.mouse.down();
    await page.mouse.move(box.x + step.drag[2], box.y + step.drag[3], { steps: 12 }); await page.mouse.up();
  } else if (step.scroll) await page.locator(step.scroll[0]).first().evaluate((e, y) => { e.scrollTop = y; }, step.scroll[1]);
  else if (step.expectVisible) {
    const ok = await page.locator(step.expectVisible).first().isVisible().catch(() => false);
    facts.expectations.push({ expect: `visible ${step.expectVisible}`, ok });
  } else if (step.expectText) {
    const ok = (await menu.innerText().catch(() => "")).toLowerCase().includes(step.expectText.toLowerCase());
    facts.expectations.push({ expect: `text "${step.expectText}"`, ok });
  }
  await page.waitForTimeout(120);
}

// at rest: laptop, phone, reduced motion, and a 4-frame strip (does it move, and is the movement worth having?)
{
  const { ctx, page } = await open("laptop", false, "rest");
  await snap(page, "rest-laptop", "laptop");
  for (const [i, ms] of [[1, 1200], [2, 1800], [3, 2500]]) { await page.waitForTimeout(ms); await snap(page, `rest-laptop-motion-${i}`, "laptop"); }
  // keyboard: tab four times and shoot (is the focus ring visible and on something meaningful?)
  await page.reload({ waitUntil: "load" }); await page.waitForTimeout(1500);
  for (let i = 0; i < 4; i++) { await page.keyboard.press("Tab"); await page.waitForTimeout(120); }
  facts.focusAfter4Tabs = await page.evaluate(() => { const e = document.activeElement; return e ? `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""} "${(e.textContent || e.value || "").trim().slice(0, 40)}"` : "none"; });
  await snap(page, "keyboard-4-tabs", "laptop");
  await ctx.close();
}
{ const { ctx, page } = await open("phone", false, "rest-phone"); await snap(page, "rest-phone", "phone"); await ctx.close(); }
{ const { ctx, page } = await open("laptop", true, "reduced"); await snap(page, "reduced-motion", "laptop"); await ctx.close(); }

for (const st of states) {
  const shape = st.shape === "phone" ? "phone" : "laptop";
  const { ctx, page } = await open(shape, false, st.name);
  const menu = page.locator("#menu");
  try { for (const step of st.steps || []) await run(step, page, menu); }
  catch (e) { errors.push(`${st.name}: step failed: ${String(e.message).split("\n")[0]}`); }
  await snap(page, st.name, shape);
  await ctx.close();
}
await browser.close();

// the picture that counts: the same shots on the real screen in the rendered hall
if (!noHall) {
  for (const [name, f] of Object.entries(facts.shots)) {
    if (f.shape !== "laptop" && f.shape !== "phone") continue;
    if (/motion-[23]$/.test(name) || name === "reduced-motion") continue;       // keep the review set small
    try {
      execFileSync("python3", [path.join(ROOT, "tools/ux/inhall.py"), `${out}/${name}.png`, `${out}/${name}-hall.jpg`, ...(f.shape === "phone" ? ["--phone"] : [])], { stdio: "pipe" });
    } catch (e) { errors.push(`${name}: inhall failed: ${String(e.stderr || e.message).split("\n").slice(-2).join(" ")}`); }
  }
}
fs.writeFileSync(`${out}/facts.json`, JSON.stringify(facts, null, 1));
fs.writeFileSync(`${out}/log.txt`, errors.length ? errors.join("\n") + "\n" : "no console errors\n");
const failed = facts.expectations.filter((e) => !e.ok);
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
console.log(`expectations: ${facts.expectations.length - failed.length}/${facts.expectations.length} pass` + (failed.length ? "; FAILED: " + failed.map((e) => e.expect).join(", ") : ""));
