// Scroll the laptop's notes with the mouse wheel and count how often the chrome folds and unfolds: it should fold once
// on the way down and unfold once on the way up, never flicker.
//   node tools/ux/flicker.mjs [talkId] [tab]
import { chromium } from "playwright-core";
import os from "node:os";
const talk = process.argv[2] || "7011", tab = process.argv[3] || "overview";
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
let bad = 0;
for (const vp of [{ width: 1920, height: 1080 }, { width: 1920, height: 1032 }, { width: 1536, height: 864 }, { width: 1440, height: 900 }, { width: 1280, height: 720 }]) {
  const page = await (await browser.newContext({ viewport: vp })).newPage();
  await page.goto(`http://localhost:8765/#talk-${talk}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.notes");
  await page.evaluate(() => { try { localStorage.setItem("cinema-laptop-hint", "1"); } catch (e) {} });
  const t = page.locator(`.notes .tabs .pill[data-tab="${tab}"]`);
  if (await t.count()) await t.click();
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const n = document.querySelector(".face.notes");
    window.__flips = [];
    new MutationObserver(() => window.__flips.push(n.classList.contains("is-immersed"))).observe(n, { attributes: true, attributeFilter: ["class"] });
  });
  const box = await page.locator(".notes .pane").boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, 40); await page.waitForTimeout(60); }
  await page.waitForTimeout(800);
  for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, -40); await page.waitForTimeout(60); }
  await page.waitForTimeout(800);
  const flips = await page.evaluate(() => window.__flips.filter((v, i, a) => i === 0 || v !== a[i - 1]));
  const ok = flips.length <= 2;
  if (!ok) bad++;
  console.log(`${vp.width}x${vp.height} ${tab}: ${flips.map((v) => (v ? "fold" : "unfold")).join(" ") || "(no change)"} ${ok ? "ok" : "FLICKER"}`);
  await page.context().close();
}
await browser.close();
process.exit(bad ? 1 : 0);
