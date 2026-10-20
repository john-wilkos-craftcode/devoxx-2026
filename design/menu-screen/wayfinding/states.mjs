// One-step-away states of the wayfinding screen: 6-detail (the poster clicked: verdict 1 of 8 opens under it),
// 7-search (a query typed, results showing, the matched words lit), plus extra review shots (room list, by day, watch first, phone room).
//   node design/menu-screen/wayfinding/states.mjs <outDir> [--extra]
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(path.join(here, "../../../tools/ux/package.json"))("playwright-core");
const out = process.argv[2] || path.join(here, "shots/t4");
const extra = process.argv.includes("--extra");
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.join(here, "index.html");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [];
async function shoot(name, act, { query = "", viewport = { width: 1100, height: 720 } } = {}) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: pageerror: ${e.message}`));
  await page.goto(url + query, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  await act(page);
  await page.waitForTimeout(700);
  const box = await page.locator("#menu").boundingBox();
  const dir = name.startsWith("x-") ? path.join(out, "extra") : out;
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: `${dir}/${name}.png`, clip: box });
  console.log(`${name}.png`);
  await ctx.close();
}
await shoot("6-detail", async (page) => {
  await page.click("#band");
});
await shoot("7-search", async (page) => {
  await page.click("#sign [data-go=search]");
  await page.waitForTimeout(300);
  await page.keyboard.type("spring", { delay: 40 });
});
const P = { query: "?shape=phone", viewport: { width: 390, height: 760 } };
if (extra) {
  const P0 = { query: "?shape=phone", viewport: { width: 390, height: 760 } };
  await shoot("x-room", async (page) => { await page.click(".room[data-room='8']"); await page.waitForTimeout(300); await page.hover(".trow:nth-child(2)"); });
  await shoot("x-room-p2-likes", async (page) => { await page.click(".room[data-room='5']"); await page.click(".sort button:nth-of-type(2)"); await page.click(".pager .next"); });
  await shoot("x-week", async (page) => { await page.click("#sign [data-go=week]"); });
  await shoot("x-band-click", async (page) => { await page.click("#band"); });
  for (let v = 2; v <= 8; v++) await shoot(`x-verdict${v}`, async (page) => { await page.click("#sign [data-go=week]"); await page.click(`.index button:nth-child(${v})`); });
  await shoot("x-verdict1-talks", async (page) => { await page.click("#sign [data-go=week]"); await page.click(".index button:nth-child(1)"); await page.click(".vtalks"); });
  await shoot("x-verdict2-talks", async (page) => { await page.click("#sign [data-go=week]"); await page.click(".index button:nth-child(2)"); await page.click(".vtalks"); });
  await shoot("x-phone-verdict1", async (page) => { await page.click("#sign [data-go=week]"); await page.click("#top .next"); }, P);
  await shoot("x-phone-verdict2", async (page) => { await page.click("#sign [data-go=week]"); await page.click("#top .next"); await page.click("#top .next"); }, P);
  await shoot("x-picks", async (page) => { await page.click("#sign [data-go=picks]"); });
  await shoot("x-days", async (page) => { await page.click("#sign [data-go=days]"); await page.waitForTimeout(300); await page.click(".day:nth-child(3)"); });
  await shoot("x-search-empty", async (page) => { await page.click("#sign [data-go=search]"); });
  await shoot("x-search-valhalla", async (page) => { await page.click("#sign [data-go=search]"); await page.keyboard.type("valhalla"); });
  await shoot("x-kbd-room", async (page) => { for (let i = 0; i < 8; i++) await page.keyboard.press("Tab"); });
  await shoot("x-phone-verdict1-talks", async (page) => { await page.click("#band"); await page.click(".vtalks"); }, P);
  await shoot("x-search-none", async (page) => { await page.click("#sign [data-go=search]"); await page.keyboard.type("cobol"); });
  await shoot("x-toast", async (page) => { await page.click(".room[data-room='4']"); await page.waitForTimeout(300); await page.click(".trow:nth-child(1)"); });
  await shoot("x-hover10", async (page) => { await page.hover(".room[data-room='10']"); });
  await shoot("x-hover3", async (page) => { await page.hover(".room[data-room='3']"); });
  await shoot("x-kbd-pager", async (page) => { await page.click(".room[data-room='8']"); await page.waitForTimeout(300); await page.keyboard.press("Tab"); for (let i = 0; i < 12; i++) await page.keyboard.press("ArrowDown"); });
  await shoot("x-phone-hover", async (page) => { await page.hover(".room[data-room='8']"); }, P);
  await shoot("x-phone-room", async (page) => { await page.click(".room[data-room='8']"); }, P);
  await shoot("x-phone-week", async (page) => { await page.click("#sign [data-go=week]"); await page.click("#top .next"); await page.click("#top .next"); }, P);
  await shoot("x-phone-week0", async (page) => { await page.click("#sign [data-go=week]"); }, P);
  await shoot("x-phone-search", async (page) => { await page.click("#sign [data-go=search]"); await page.keyboard.type("spring"); }, P);
  await shoot("x-phone-days", async (page) => { await page.click("#sign [data-go=days]"); }, P);
  await shoot("x-phone-picks", async (page) => { await page.click("#sign [data-go=picks]"); }, P);
}
await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
