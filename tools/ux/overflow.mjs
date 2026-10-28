// Check every talk for text that spills out of its box: buttons below the screen, the strip or the title past its edge.
// (The programme's cards are gone: the hall screen is the Three Inks menu, design/menu-round3/three-inks has its checks.)
// Serve the site first (node tools/ux/serve.mjs).
//   node tools/ux/overflow.mjs [baseUrl]
import { chromium } from "playwright-core";
import os from "node:os";
const base = process.argv[2] || "http://localhost:8765/";
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
for (const v of [{ name: "laptop", viewport: { width: 1440, height: 900 } }, { name: "phone", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }]) {
  const page = await (await browser.newContext(v)).newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.inks"); await page.waitForTimeout(800);
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
      const out = [...f.querySelectorAll(".btn, .actions, h2, .tldr, .verdict, .meta, .who-l, .tabs, .talk-strip, .foot")].filter((e) => {
        // text inside something that scrolls (the laptop summary, the phone totem) is reachable: not cut off
        for (let a = e.parentElement; a && a !== f.parentElement; a = a.parentElement) if (/auto|scroll/.test(getComputedStyle(a).overflowY)) return false;
        const b = e.getBoundingClientRect(); return b.height && (b.bottom > fb.bottom + 1 || b.right > fb.right + 1); }).map((e) => e.className || e.tagName);
      return out.length ? out.join(",") : null;
    });
    if (r) bad.push(`${id}:${r}`);
  }
  console.log(v.name, "talks checked", allIds.length, "overflowing:", bad.length, bad.slice(0, 15).join(" "));
}
await browser.close();
