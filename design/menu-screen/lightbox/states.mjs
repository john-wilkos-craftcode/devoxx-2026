// States the shot tool does not reach: the one-step-away detail and a typed search.
// usage (repo root): node design/menu-screen/lightbox/states.mjs <outDir> [--all]
//   always writes 6-detail.png (verdict 1 opened) and 7-search.png ("valhalla" typed, results showing);
//   --all also writes the other states (story list, picks with why, a day, sort by likes, empty search, toast, phone).
import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import os from "node:os"; import path from "node:path"; import fs from "node:fs";

const out = process.argv[2], all = process.argv.includes("--all");
if (!out) { console.log("usage: node design/menu-screen/lightbox/states.mjs <outDir> [--all]"); process.exit(2); }
fs.mkdirSync(out, { recursive: true });
const base = "file://" + path.resolve("design/menu-screen/lightbox/index.html");
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const errors = [];

async function open(phone = false) {
  const ctx = await browser.newContext({ viewport: phone ? { width: 390, height: 760 } : { width: 1100, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  await page.goto(base + (phone ? "?shape=phone" : ""), { waitUntil: "load" });
  await page.waitForTimeout(1200);
  return { ctx, page };
}
async function snap(page, name) {
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/${name}.png`, clip: await page.locator("#menu").boundingBox() });
  console.log(`${name}.png`);
}

{ // 6: the story, verdict 1 opened (consensus, debate sides with names, the pick)
  const { ctx, page } = await open();
  await page.click("button[data-go=story]");
  if (all) await snap(page, "s-story");
  await page.locator(".vbtn").first().click();
  await page.mouse.move(4, 4);
  await snap(page, "6-detail");
  await ctx.close();
}
{ // 7: a typed search with results
  const { ctx, page } = await open();
  await page.mouse.click(700, 300);
  await page.keyboard.type("valhalla", { delay: 40 });
  await page.keyboard.press("ArrowDown");
  await page.mouse.move(4, 4);
  await snap(page, "7-search");
  if (all) {
    await page.click(".sort"); await snap(page, "s-sort-likes");
    await page.keyboard.press("Escape"); await page.keyboard.type("agent", { delay: 30 }); await snap(page, "s-search-agent");
    await page.keyboard.press("Enter"); await snap(page, "s-toast");
    await page.keyboard.press("Escape"); await page.keyboard.type("zzqx", { delay: 30 }); await snap(page, "s-empty");
    await page.keyboard.type("aaaaaaaaaaaaaaaaaaaaaaaaaa", { delay: 5 }); await snap(page, "s-long-query");
  }
  await ctx.close();
}
if (all) { // the marquee: the second and third arguments, and a frame in the middle of a wipe
  for (const phone of [false, true]) {
    const { ctx, page } = await open(phone);
    for (const i of [1, 2]) {
      await page.evaluate((i) => document.querySelectorAll(".slide").forEach((s, k) => s.classList.toggle("on", k === i)), i);
      await snap(page, `s-arg-${i + 1}${phone ? "-phone" : ""}`);
    }
    await page.evaluate(() => { const s = document.querySelectorAll(".slide"); s.forEach((x) => x.classList.remove("on"));
      s[1].classList.add("on", "wipe-in"); s[0].classList.add("wipe-out");
      document.getAnimations().forEach((a) => { if (a.animationName?.startsWith("wipe")) { a.pause(); a.currentTime = 600; } }); });
    await page.screenshot({ path: `${out}/s-wipe${phone ? "-phone" : ""}.png`, clip: await page.locator("#menu").boundingBox() });
    await ctx.close();
  }
}
if (all) {
  const { ctx, page } = await open();
  await page.click("button[data-go=picks]"); await page.locator(".pbtn").nth(2).hover(); await snap(page, "s-picks");
  await page.click("button[data-go=days]"); await snap(page, "s-days");
  await page.locator(".dbtn").nth(3).click(); await snap(page, "s-day-thu");
  await page.click("button[data-go=story]");
  await page.locator(".vbtn").nth(1).click(); await snap(page, "s-verdict-3sides");
  await ctx.close();
  const p = await open(true);
  await p.page.locator("#q").fill("leyden"); await snap(p.page, "s-phone-search");
  await p.page.keyboard.press("Escape");
  await p.page.click("button[data-go=story]"); await snap(p.page, "s-phone-story");
  await p.page.locator(".vbtn").first().click(); await snap(p.page, "s-phone-verdict");
  await p.page.click("button[data-go=days]"); await p.page.locator(".dbtn").nth(2).click(); await snap(p.page, "s-phone-day");
  await p.page.click("button[data-go=picks]"); await p.page.locator(".pbtn").nth(2).hover(); await snap(p.page, "s-phone-picks");
  await p.ctx.close();
}
await browser.close();
console.log(errors.length ? `ERRORS (${errors.length}):\n` + errors.join("\n") : "no console errors");
