// own state-exercising script: node design/menu-variants/split-flap/states.mjs <outDir>
import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import os from "node:os"; import path from "node:path"; import fs from "node:fs";
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve("design/menu-variants/split-flap/index.html");
const b = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errs = [];
async function run(shape) {
  const phone = shape === "phone";
  const ctx = await b.newContext({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 } });
  const p = await ctx.newPage();
  p.on("console", m => m.type() === "error" && errs.push(m.text())); p.on("pageerror", e => errs.push(e.message));
  await p.goto(url + (phone ? "?shape=phone" : "")); await p.waitForTimeout(2500);
  const shot = async n => { await p.waitForTimeout(100); await p.locator("#menu").screenshot({ path: `${out}/${shape}-${n}.png` }); };
  await p.locator(".row").first().click(); await p.waitForTimeout(1500); await shot("a-verdict");
  await p.keyboard.press("Escape"); await p.waitForTimeout(300);
  await p.locator(".row").nth(1).click(); await p.waitForTimeout(1500); await shot("a2-verdict2");
  await p.keyboard.press("Escape");
  await p.locator(".tab", { hasText: "Watch first" }).click(); await p.waitForTimeout(1600); await shot("b-picks");
  await p.locator("input").type("agent", { delay: 90 }); await p.waitForTimeout(260); await shot("c-search-midflip");
  await p.waitForTimeout(1500); await shot("c2-search");
  await p.locator("input").fill("zzzq"); await p.waitForTimeout(1500); await shot("c3-empty");
  await p.locator("input").fill(""); await p.waitForTimeout(300);
  await p.locator(".tab", { hasText: "All talks" }).click(); await p.waitForTimeout(1500);
  await p.locator(phone ? ".chip >> text=Like rate" : ".heads button >> text=Like rate").click(); await p.waitForTimeout(1600); await shot("d-sort-rate");
  await p.locator(".tab", { hasText: "Programme" }).click(); await p.waitForTimeout(1600);
  await p.locator(".chip >> text=/Wed/").click(); await p.waitForTimeout(1600); await shot("e-programme");
  await p.locator(".row").first().click(); await p.waitForTimeout(300); await shot("f-toast");
  await ctx.close();
}
await run("laptop"); await run("phone"); await b.close(); console.log(errs.length ? errs : "no errors");
