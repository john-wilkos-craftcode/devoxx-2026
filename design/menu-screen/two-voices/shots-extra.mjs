// Extra shots for two-voices: the one-step-away states.
//   node design/menu-screen/two-voices/shots-extra.mjs <outDir> [--phone] [--debates]
// 6-detail.png: open the left voice of the first debate (its stance, the talk to start with, the side's other talks).
// 7-search.png: "All talks" with a search typed and results showing.
// --debates: also every debate at rest (d1..d8) and leaning on each side, for review.
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.resolve(here, "../../../tools/ux/package.json"));
const { chromium } = require("playwright-core");

const out = process.argv[2] || path.join(here, "shots/extra");
const phone = process.argv.includes("--phone");
const debates = process.argv.includes("--debates");
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.join(here, "index.html") + (phone ? "?shape=phone" : "");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [];
async function shoot(name, act, { reduced = false } = {}) {
  const ctx = await browser.newContext({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 }, deviceScaleFactor: 1, reducedMotion: reduced ? "reduce" : "no-preference" });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: pageerror: ${e.message}`));
  await page.goto(url, { waitUntil: "load" });
  await page.waitForTimeout(1800);
  await act(page);
  const box = await page.locator("#menu").boundingBox();
  await page.screenshot({ path: `${out}/${name}.png`, clip: box });
  console.log(`${name}.png`);
  await ctx.close();
}
await shoot("6-detail", async (page) => {
  await page.locator('.voice[data-side="0"]').hover();
  await page.waitForTimeout(600);
  await page.locator('.voice[data-side="0"]').click();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(900);
});
await shoot("7-search", async (page) => {
  await page.locator('.rail [data-act="all"]').click();
  await page.waitForTimeout(800);
  await page.locator(".search").type("valhalla", { delay: 40 });
  await page.waitForTimeout(500);
});
if (debates) {
  await shoot("8-watch", async (page) => { await page.locator('.rail [data-act="watch"]').click(); await page.waitForTimeout(900); });
  await shoot("9-side-3way", async (page) => { await page.keyboard.press("ArrowDown"); await page.waitForTimeout(700); await page.locator('.voice[data-side="2"]').click(); await page.waitForTimeout(900); });
  await shoot("10-day", async (page) => { await page.locator('.rail [data-act="all"]').click(); await page.waitForTimeout(700); await page.locator('[data-day]').nth(5).click(); await page.waitForTimeout(500); });
  for (let i = 0; i < 8; i++) {
    const go = async (page) => { for (let j = 0; j < i; j++) { await page.keyboard.press("ArrowDown"); await page.waitForTimeout(80); } };
    await shoot(`d${i + 1}-rest`, async (page) => { await go(page); await page.waitForTimeout(500); }, { reduced: true });
    if (!phone) {
      await shoot(`d${i + 1}-lean-left`, async (page) => { await go(page); await page.mouse.move(120, 300); await page.mouse.move(130, 300); await page.waitForTimeout(900); });
      await shoot(`d${i + 1}-lean-right`, async (page) => { await go(page); await page.mouse.move(1000, 300); await page.mouse.move(990, 300); await page.waitForTimeout(900); });
    }
  }
}
await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
