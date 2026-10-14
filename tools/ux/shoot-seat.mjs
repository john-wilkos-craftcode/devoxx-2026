// Screenshot the seat view on laptops (the recording on the cinema screen, the notes on the laptop in your lap) through
// its states, for the UX review agents (see RUBRIC-seat.md). Serve the site first: node tools/ux/serve.mjs
//   node tools/ux/shoot-seat.mjs tools/ux/out/s1 [baseUrl]
import { chromium } from "playwright-core";
import fs from "node:fs";
import os from "node:os";

const out = process.argv[2];
const base = process.argv[3] || "http://localhost:8765/cinema/";
fs.mkdirSync(out, { recursive: true });
const exe = `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`;
const browser = await chromium.launch({ executablePath: exe, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
const VIEWS = [
  { name: "1440x900", viewport: { width: 1440, height: 900 } },
  { name: "1280x720", viewport: { width: 1280, height: 720 } },
  { name: "1920x1080", viewport: { width: 1920, height: 1080 } },
];
const TALK = process.env.TALK || "7011";          // Room 8, recorded, with chapters
const NOVIDEO = process.env.NOVIDEO || "";
const log = [];
for (const v of VIEWS) {
  const ctx = await browser.newContext({ viewport: v.viewport });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error" && !/404|youtube|doubleclick|google/i.test(m.text())) log.push(`${v.name} console: ${m.text()}`); });
  page.on("pageerror", (e) => log.push(`${v.name} pageerror: ${e.message}`));
  const shot = async (state, wait = 900) => { await page.mouse.move(v.viewport.width / 2, 4); await page.waitForTimeout(wait); await page.screenshot({ path: `${out}/${v.name}-${state}.png` }); };
  // from the programme, choosing the talk: the walk (skipped) and sitting down
  await page.goto("about:blank"); await page.goto(`${base}#talk-${TALK}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.notes", { timeout: 20000 });
  await shot("1-seat", 2500);
  const tab = page.locator('.notes .tabs .pill[data-tab="points"]');
  if (await tab.count()) {
    await tab.click();
    await shot("2-other-tab");
    await page.locator('.notes .tabs .pill').first().click();
    await page.locator(".notes .chapter").nth(2).click();
    await shot("3-jumped", 3500);
  }
  await page.locator(".notes .notes-close").click();
  await shot("4-closed", 1200);
  await page.locator("#lapLid").click();
  await page.waitForSelector(".face.notes:not(.is-off)", { timeout: 5000 });
  await page.locator(".notes .notes-zoom").click();
  await shot("5-fullscreen", 1500);
  await page.locator(".notes .chapter").nth(4).click();
  await shot("6-fullscreen-jumped", 3000);
  await page.keyboard.press("Escape");
  await shot("7-back-from-fullscreen", 2000);
  // the recording full screen (the browser's), from the laptop's bar
  await page.locator(".notes .icon.fs").click();
  await page.waitForTimeout(1500);
  await page.mouse.move(v.viewport.width / 2, v.viewport.height / 2); await page.mouse.move(v.viewport.width / 2 + 20, v.viewport.height / 2);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/${v.name}-11-video-fullscreen.png` });
  await page.keyboard.press("f");
  await page.waitForTimeout(800);
  if (NOVIDEO) {
    await page.goto("about:blank"); await page.goto(`${base}#talk-${NOVIDEO}`, { waitUntil: "networkidle" });
    await page.waitForSelector(".face.notes", { timeout: 20000 });
    await shot("8-no-recording", 1500);
  }
  // the player can't load (blocked): what you see after pressing play
  await page.route(/youtube\.com\/iframe_api/, (r) => r.abort());
  await page.goto("about:blank"); await page.goto(`${base}#talk-${TALK}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.notes", { timeout: 20000 });
  await page.locator(".tube .poster").click();
  await shot("10-player-blocked", 1500);
  await page.unroute(/youtube\.com\/iframe_api/);
  await page.goto("about:blank"); await page.goto(`${base}#talk-${TALK}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.notes", { timeout: 20000 });
  await page.waitForTimeout(1500);
  for (let i = 0; i < 3; i++) await page.keyboard.press("Tab");
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${out}/${v.name}-9-keyboard.png` });
  await ctx.close();
}
await browser.close();
fs.writeFileSync(`${out}/log.txt`, log.join("\n") || "no console errors");
console.log(`${fs.readdirSync(out).length} files in ${out}`);
