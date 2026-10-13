// Screenshot the cinema page (site/cinema/) through its main states on laptop and phone viewports, for the UX
// review agents (see RUBRIC.md). Serve the site first: python3 -m http.server 8765 -d site
//   node tools/ux/shoot.mjs tools/ux/out/r1 [baseUrl]
import { chromium } from "playwright-core";
import fs from "node:fs";
import os from "node:os";

const out = process.argv[2];
const base = process.argv[3] || "http://localhost:8765/cinema/";
fs.mkdirSync(out, { recursive: true });
const exe = `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`;
const browser = await chromium.launch({ executablePath: exe, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
const VIEWS = [
  { name: "laptop-1440", viewport: { width: 1440, height: 900 }, dpr: 1 },
  { name: "laptop-1280", viewport: { width: 1280, height: 720 }, dpr: 1 },
  { name: "phone-390", viewport: { width: 390, height: 844 }, dpr: 2, mobile: true },
];
const log = [];
for (const v of VIEWS) {
  const ctx = await browser.newContext({ viewport: v.viewport, deviceScaleFactor: v.dpr, isMobile: !!v.mobile, hasTouch: !!v.mobile });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error" && !/404/.test(m.text())) log.push(`${v.name} console: ${m.text()}`); });
  page.on("pageerror", (e) => log.push(`${v.name} pageerror: ${e.message}`));
  const shot = async (state) => { await page.mouse.move(2, v.viewport.height - 2); await page.waitForTimeout(700); await page.screenshot({ path: `${out}/${v.name}-${state}.png` }); };
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.prog", { timeout: 15000 });
  await page.waitForTimeout(1200);
  await shot("1-hall");
  const times = page.locator(".times .pill");
  if (await times.count() > 3) { await times.nth(3).click(); await shot("2-other-slot"); }
  await page.fill(".search", "kotlin");
  await shot("3-search");
  await page.fill(".search", "");
  await page.locator(".face.prog .times .pill").first().click();
  const seatCard = page.locator(".card:not(.is-off)").first();
  if (await seatCard.count()) {
    await seatCard.click();
    await page.waitForSelector(".face.talk", { timeout: 20000 });
    await page.waitForTimeout(1500);
    await shot("4-talk");
    const tabs = page.locator(".face.talk .tabs .pill");
    if (await tabs.count() > 2) { await tabs.nth(2).click(); await shot("5-talk-tab"); }
    await page.locator(".face.talk .btn", { hasText: "Back to the programme" }).click();
    await page.waitForSelector(".face.prog", { timeout: 20000 });
    await shot("6-back");
  } else log.push(`${v.name}: no walkable card in the first slot`);
  await page.fill(".search", "bof");
  await page.waitForTimeout(300);
  const off = page.locator(".card.is-off").first();
  if (await off.count()) { await off.click(); await shot("7-offfloor"); }
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.prog");
  await page.waitForTimeout(800);
  for (let i = 0; i < 4; i++) await page.keyboard.press("Tab");
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${out}/${v.name}-8-keyboard.png` });
  await ctx.close();
}
await browser.close();
fs.writeFileSync(`${out}/log.txt`, log.join("\n") || "no console errors (404s for walk videos not yet rendered are filtered out)");
console.log(`${fs.readdirSync(out).length} files in ${out}`);
