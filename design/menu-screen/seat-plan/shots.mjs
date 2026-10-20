// One step away (t2-t4): #menu with a verdict opened from its name on the plan (6-detail) and with a search typed (7-search), plus
// states for checking (watch first, by day, likes sort, phone story). Launch lines copied from tools/ux/shot.mjs.
//   node design/menu-screen/seat-plan/shots.mjs <outDir> [--extra]
import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const out = process.argv[2];
const extra = process.argv.includes("--extra");
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.join(path.dirname(fileURLToPath(import.meta.url)), "index.html");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [];
async function shoot(name, act, { phone = false } = {}) {
  const ctx = await browser.newContext({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: pageerror: ${e.message}`));
  await page.goto(url + (phone ? "?shape=phone" : ""), { waitUntil: "load" });
  await page.waitForTimeout(1200);
  await act(page);
  await page.waitForTimeout(1100);
  const box = await page.locator("#menu").boundingBox();
  await page.screenshot({ path: `${out}/${name}.png`, clip: box });
  console.log(`${name}.png`);
  await ctx.close();
}
// a verdict opened straight from its name on the plan
const verdict = (i) => async (page) => { await page.locator(".vlabel").nth(i).click(); };
await shoot("6-detail", verdict(0));
await shoot("7-search", async (page) => {
  await page.click('.chrome [data-go="search"]');
  await page.keyboard.type("valhalla", { delay: 60 });
  await page.waitForTimeout(300);
  await page.keyboard.press("ArrowDown");
});
if (extra) {
  await shoot("x-story-intro", async (page) => { await page.click('.chrome [data-go="story"]'); });
  await shoot("x-detail-3sides", verdict(1));
  await shoot("x-watch", async (page) => { await page.click('.chrome [data-go="watch"]'); });
  await shoot("x-search-long", async (page) => { await page.click('.chrome [data-go="search"]'); await page.keyboard.type("agent", { delay: 30 }); });
  await shoot("x-detail-jvm", verdict(4));
  await shoot("x-day", async (page) => { await page.click('.chrome [data-go="day"]'); await page.waitForTimeout(300); await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowRight"); });
  await shoot("x-likes", async (page) => { await page.click('.chrome [data-go="search"]'); await page.click(".sorts button >> nth=1"); await page.waitForTimeout(400); await page.keyboard.press("Escape"); await page.hover(".plan .seat >> nth=120"); });
  await shoot("x-search-empty", async (page) => { await page.click('.chrome [data-go="search"]'); });
  await shoot("x-phone-hover", async (page) => { await page.locator(".plan .seat").nth(20).click(); }, { phone: true });
  await shoot("x-hover-right", async (page) => { await page.hover(".plan .seat >> nth=30"); });
  await shoot("x-keyboard-seat", async (page) => { await page.keyboard.press("Tab"); await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowDown"); });
  await shoot("x-keyboard-label", async (page) => { await page.keyboard.press("Tab"); await page.keyboard.press("Tab"); await page.keyboard.press("ArrowRight"); });
  await shoot("x-phone-detail", verdict(0), { phone: true });
  await shoot("x-toast", async (page) => { await page.keyboard.press("Tab"); await page.keyboard.press("Enter"); });
  await shoot("x-search-none", async (page) => { await page.keyboard.type("zzzq"); });
  await shoot("x-phone-story", verdict(1), { phone: true });
  await shoot("x-phone-search", async (page) => { await page.click('.chrome [data-go="search"]'); await page.keyboard.type("spring"); }, { phone: true });
  await shoot("x-phone-day", async (page) => { await page.click('.chrome [data-go="day"]'); }, { phone: true });
}
await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
