import pathm from "node:path"; const path0 = (p) => pathm.resolve(p) + "/";
// Captures extra states: node design/menu-variants/debate-arena/states.mjs <outDir>
import { createRequire } from "node:module"; const { chromium } = createRequire(path0("tools/ux/"))("playwright-core");
import os from "node:os"; import path from "node:path"; import fs from "node:fs";
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve("design/menu-variants/debate-arena/index.html");
const b = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errs = [];
async function run(name, shape, fn) {
  const ctx = await b.newContext({ viewport: shape ? { width: 390, height: 760 } : { width: 1100, height: 720 } });
  const p = await ctx.newPage();
  p.on("console", m => m.type() === "error" && errs.push(name + ": " + m.text()));
  p.on("pageerror", e => errs.push(name + ": " + e.message));
  await p.goto(url + (shape ? "?shape=phone" : "")); await p.waitForTimeout(1200);
  await fn(p);
  await p.waitForTimeout(600);
  await p.locator("#menu").screenshot({ path: `${out}/${name}.png` });
  await ctx.close();
}
await run("a-row-hover", 0, p => p.locator(".row").nth(3).hover());
await run("b-dot-cross", 0, p => p.locator(".row").nth(7).locator(".dot.cross").first().hover());
await run("c-verdict0", 0, p => p.locator(".row .rt").nth(0).click());
await run("d-verdict1", 0, p => p.locator(".row .rt").nth(1).click());
await run("e-search", 0, async p => { await p.fill("#q", "valhalla"); });
await run("f-sort-like", 0, async p => { await p.click(".tab:nth-child(2)"); await p.click(".sortb:nth-of-type(2)"); });
await run("g-programme", 0, async p => { await p.click(".tab:nth-child(3)"); await p.locator(".dayb").nth(2).click(); });
await run("h-open-talk", 0, async p => { await p.locator(".pick").nth(1).click(); });
await run("i-pick-hover", 0, async p => { await p.locator(".pick").nth(4).hover(); });
await run("j-intro", 0, async p => { await p.click(".headline"); });
await run("k-kbd-dot", 0, async p => { await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("ArrowRight"); });
await run("p1-verdict", 1, p => p.locator(".row .rt").nth(1).click());
await run("p2-picks", 1, p => p.locator(".tab").nth(1).click());
await run("p3-talks", 1, p => p.locator(".tab").nth(2).click());
await run("p4-prog", 1, p => p.locator(".tab").nth(3).click());
await run("p5-search", 1, p => p.fill("#q", "agent"));
await b.close(); console.log(errs.length ? errs.join("\n") : "no errors");
