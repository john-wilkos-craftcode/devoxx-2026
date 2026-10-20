// own state-exercising script: node design/menu-variants/reel/states.mjs <iterN> [phone]
import { chromium } from "/home/kevlarrelic/code/CRAFTCODE/devoxx-2026/tools/ux/node_modules/playwright-core/index.mjs";
import os from "node:os"; import path from "node:path"; import fs from "node:fs";
const [it, shape] = process.argv.slice(2);
const dir = path.resolve("design/menu-variants/reel/shots/" + it); fs.mkdirSync(dir, { recursive: true });
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const phone = shape === "phone";
const page = await browser.newPage({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 } });
const errs = []; page.on("console", m => m.type() === "error" && errs.push(m.text())); page.on("pageerror", e => errs.push(e.message));
await page.goto("file://" + path.resolve("design/menu-variants/reel/index.html") + (phone ? "?shape=phone" : ""));
await page.waitForTimeout(1200);
const shot = async (n) => { await page.waitForTimeout(700); await page.locator("#menu").screenshot({ path: `${dir}/${n}${phone ? "-phone" : ""}.png` }); };
const box = await page.locator(".reel").boundingBox();
// drag the strip mid-way
await page.mouse.move(box.x + 700, box.y + 100); await page.mouse.down(); await page.mouse.move(box.x + 520, box.y + 100, { steps: 6 });
await page.waitForTimeout(60); await shot("a-drag-mid");
await page.mouse.up(); await shot("b-after-drag");
await page.locator(".frame.gate").click(); await shot("c-versus");
await page.keyboard.press("Escape");
await page.keyboard.press("End"); await shot("d-credits");
await page.keyboard.press("Home");
await page.fill("#q", "security"); await shot("e-search");
await page.fill("#q", "zzzz"); await shot("f-empty");
await page.fill("#q", ""); await page.waitForTimeout(300);
await page.getByRole("button", { name: "Like rate" }).click(); await shot("g-sort-rate");
await page.getByRole("button", { name: "Programme", exact: true }).click(); await shot("h-programme");
await page.locator(".prow").first().click(); await shot("i-opentalk");
console.log(errs.length ? errs : "no errors");
await browser.close();
