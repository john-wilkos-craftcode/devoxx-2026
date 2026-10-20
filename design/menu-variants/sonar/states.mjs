// Exercises the interactive states. Run from repo root: node design/menu-variants/sonar/states.mjs <outDir>
import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import os from "node:os"; import path from "node:path"; import fs from "node:fs";
const out = process.argv[2] || "design/menu-variants/sonar/shots/states"; fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve("design/menu-variants/sonar/index.html");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errs = [];
async function run(name, { query = "", vp = { width: 1100, height: 720 }, act }) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 }); const page = await ctx.newPage();
  page.on("console", m => m.type() === "error" && errs.push(name + ": " + m.text())); page.on("pageerror", e => errs.push(name + ": " + e.message));
  await page.goto(url + query); await page.waitForTimeout(900);
  await act(page); await page.waitForTimeout(500);
  await page.locator("#menu").screenshot({ path: `${out}/${name}.png` }); await ctx.close();
}
const P = { width: 390, height: 760 };
await run("blip", { act: async p => { await p.click('.bl[data-id="valhalla-limits"]'); } });
await run("blip-drag", { act: async p => { const b = await p.locator("#radar").boundingBox(); await p.mouse.move(b.x + 280, b.y + 306); await p.mouse.down(); await p.mouse.move(b.x + 480, b.y + 400, { steps: 8 }); await p.mouse.move(b.x + 280, b.y + 540, { steps: 8 }); await p.mouse.up(); } });
await run("verdict", { act: async p => { await p.click("#tab-verdicts"); await p.click(".vd >> nth=2 >> button"); } });
await run("search", { act: async p => { await p.fill("#q", "valhalla"); } });
await run("search-agents", { act: async p => { await p.fill("#q", "archunit"); } });
await run("sort-rate", { act: async p => { await p.click("#tab-talks"); await p.click("text=Like rate"); } });
await run("watch", { act: async p => { await p.click("#tab-watch"); } });
await run("prog", { act: async p => { await p.click("#tab-prog"); await p.click("text=Wed 7"); } });
await run("talk-toast", { act: async p => { await p.click("#tab-watch"); await p.click(".pk .ti >> nth=0"); } });
await run("calm", { act: async p => {} });
await run("phone-blip", { query: "?shape=phone", vp: P, act: async p => { await p.click('.bl[data-id="microvm"]'); } });
await run("phone-verdict", { query: "?shape=phone", vp: P, act: async p => { await p.click("#tab-verdicts"); await p.click(".vd >> nth=0 >> button"); } });
await run("hall", { vp: { width: 1500, height: 520 }, act: async p => { await p.click("#hallToggle"); } });
await browser.close(); console.log(errs.length ? errs.join("\n") : "no errors");
