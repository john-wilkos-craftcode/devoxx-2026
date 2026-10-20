// The one-step-away states of the title card, plus every poster (to check the fitting of all eight verdicts).
//   node design/menu-screen/title-card/shoot-states.mjs <outDir> [phone] [cards]      (run from the repo root)
// writes 6-detail (the debate of verdict 2), 7-search (a typed query), 8-programme, 9-toast; with "cards" also
// card-1..card-8 (reduced motion, so nothing turns over by itself).
import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const out = process.argv[2], phone = process.argv.includes("phone"), cards = process.argv.includes("cards");
if (!out) { console.log("usage: node design/menu-screen/title-card/shoot-states.mjs <outDir> [phone] [cards]"); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve("design/menu-screen/title-card/index.html") + (phone ? "?shape=phone" : "");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 }, deviceScaleFactor: 1, reducedMotion: "reduce" });
const page = await ctx.newPage();
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(1800);
const menu = page.locator("#menu");
const snap = async (name) => { await page.waitForTimeout(400); await page.screenshot({ path: `${out}/${name}.png`, clip: await menu.boundingBox() }); console.log(`${name}.png`); };
const sfx = phone ? "-phone" : "";

if (cards) {
  for (let k = 1; k <= 8; k++) { await snap(`card-${k}${sfx}`); await page.keyboard.press("ArrowRight"); }
}

// 6: cut to verdict 2 (the three-sided debate on review), open its debate
await page.keyboard.press("ArrowRight");
await page.waitForTimeout(200);
await page.keyboard.press("Enter");
await snap(`6-detail${sfx}`);

// 7: Esc back to the card, type a query: typing at rest opens search
await page.keyboard.press("Escape");
await page.waitForTimeout(150);
await page.keyboard.type("leyden", { delay: 40 });
await snap(`7-search${sfx}`);

// extra: the programme and the toast after opening a talk
await page.keyboard.press("Escape");
await page.locator("[data-go=programme]").click();
await snap(`8-programme${sfx}`);
await page.locator("#programme .slot").first().click();
await snap(`9-toast${sfx}`);

await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
