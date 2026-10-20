// Screenshot a main-menu variant (design/menu-variants/<name>/index.html) the way the critique loop needs it: the menu
// canvas at its real size at rest, after hovering and keyboard-focusing into it, with reduced motion, and the phone
// totem shape. Prints every console error and page error. The page must render its canvas as #menu; ?shape=phone gives
// the phone canvas.
//   node tools/ux/shot.mjs design/menu-variants/<name>/index.html <outDir> [--wait ms] [--hover "<selector>"]
import { chromium } from "playwright-core";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [file, out] = process.argv.slice(2);
if (!file || !out) { console.log("usage: node tools/ux/shot.mjs <page.html> <outDir> [--wait ms] [--hover selector]"); process.exit(2); }
const opt = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const wait = +opt("--wait", 1800), hoverSel = opt("--hover", null);
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve(file);
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [];
async function shoot(name, { viewport, query = "", reduced = false, act = null }) {
  const ctx = await browser.newContext({ viewport, reducedMotion: reduced ? "reduce" : "no-preference", deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: pageerror: ${e.message}`));
  await page.goto(url + query, { waitUntil: "load" });
  await page.waitForTimeout(wait);
  const menu = page.locator("#menu");
  if (!(await menu.count())) { errors.push(`${name}: no #menu element`); await page.screenshot({ path: `${out}/${name}.png` }); await ctx.close(); return; }
  if (act) await act(page, menu);
  const box = await menu.boundingBox();
  await page.screenshot({ path: `${out}/${name}.png`, clip: box });
  console.log(`${name}.png  #menu ${Math.round(box.width)}x${Math.round(box.height)}`);
  await ctx.close();
}
const laptop = { width: 1100, height: 720 }, phone = { width: 390, height: 760 };
await shoot("1-rest", { viewport: laptop });
await shoot("2-hover", { viewport: laptop, act: async (page, menu) => {
  const target = hoverSel ? page.locator(hoverSel).first() : menu.locator("a, button, [tabindex], input").first();
  if (await target.count()) { await target.hover(); await page.waitForTimeout(700); }
} });
await shoot("3-keyboard", { viewport: laptop, act: async (page) => {
  for (let i = 0; i < 4; i++) { await page.keyboard.press("Tab"); await page.waitForTimeout(150); }
  await page.waitForTimeout(500);
  const f = await page.evaluate(() => { const e = document.activeElement; return e ? `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""} "${(e.textContent || e.value || "").trim().slice(0, 40)}"` : "none"; });
  console.log(`   focus after 4 Tabs: ${f}`);
} });
await shoot("4-reduced-motion", { viewport: laptop, reduced: true });
await shoot("5-phone", { viewport: phone, query: "?shape=phone" });
await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
