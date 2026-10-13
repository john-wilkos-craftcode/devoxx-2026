// Check every talk and every programme slot for text that spills out of its box: buttons below the cinema screen,
// card text below its card. Serve the site first (node tools/ux/serve.mjs).
//   node tools/ux/overflow.mjs [baseUrl]
import { chromium } from "playwright-core";
import os from "node:os";
const base = process.argv[2] || "http://localhost:8765/cinema/";
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
for (const v of [{ name: "laptop", viewport: { width: 1440, height: 900 } }, { name: "phone", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }]) {
  const page = await (await browser.newContext(v)).newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.prog"); await page.waitForTimeout(800);
  // talks: does anything in the talk face end below the face (or below what's visible of it)?
  const ids = await page.evaluate(() => (window.TALKS || window.talks || window.DATA?.talks || []).map((t) => t.id));
  const allIds = ids.length ? ids : await page.evaluate(() => Object.values(window).find((x) => Array.isArray(x?.talks))?.talks.map((t) => t.id) || []);
  let bad = [];
  for (const id of allIds) {
    await page.evaluate((id) => { location.hash = `#talk-${id}`; dispatchEvent(new PopStateEvent("popstate")); }, id);
    await page.waitForTimeout(120);
    const r = await page.evaluate(() => {
      const f = document.querySelector(".face.talk"); if (!f) return null;
      const fb = f.getBoundingClientRect();
      const out = [...f.querySelectorAll(".btn, .actions, h2, .tldr, .verdict, .meta, .who-l, .tabs")].filter((e) => {
        // text inside something that scrolls (the laptop summary, the phone totem) is reachable: not cut off
        for (let a = e.parentElement; a && a !== f.parentElement; a = a.parentElement) if (/auto|scroll/.test(getComputedStyle(a).overflowY)) return false;
        const b = e.getBoundingClientRect(); return b.height && (b.bottom > fb.bottom + 1 || b.right > fb.right + 1); }).map((e) => e.className || e.tagName);
      return out.length ? out.join(",") : null;
    });
    if (r) bad.push(`${id}:${r}`);
  }
  console.log(v.name, "talks checked", allIds.length, "overflowing:", bad.length, bad.slice(0, 15).join(" "));
  await page.goto(base, { waitUntil: "networkidle" }); await page.waitForSelector(".face.prog"); await page.waitForTimeout(500);
  // the programme: every day and slot, any text box sticking out of its card
  const days = await page.locator(".face.prog .days .pill, .face.prog [data-day]").count();
  let hb = new Set();
  for (let d = 0; d < Math.max(days, 1); d++) {
    if (days) { await page.locator(".face.prog .days .pill, .face.prog [data-day]").nth(d).click(); await page.waitForTimeout(150); }
    const slots = await page.locator(".face.prog .times .pill").count();
    for (let s = 0; s < slots; s++) {
      await page.locator(".face.prog .times .pill").nth(s).click(); await page.waitForTimeout(150);
      const r = await page.evaluate(() => [...document.querySelectorAll(".face.prog .card")].flatMap((c) => { const cb = c.getBoundingClientRect(); return [...c.querySelectorAll("*")].filter((e) => { const b = e.getBoundingClientRect(); return b.height && (b.bottom > cb.bottom + 1 || b.right > cb.right + 1); }).map((e) => `${(e.className || e.tagName)}:"${c.textContent.trim().slice(0, 40)}"`); }));
      r.forEach((x) => hb.add(x));
    }
  }
  console.log(v.name, "programme days", days, "card overflows:", hb.size, [...hb].slice(0, 12).join(" | "));
}
await browser.close();
