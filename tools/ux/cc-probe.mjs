// Captions: play a talk, skip to where someone speaks, press C, and check YouTube's caption lines land inside the part of
// its frame the tube shows (the tube crops the frame to hide YouTube's overlays; captions sit at the frame's foot).
//   node tools/ux/cc-probe.mjs [talkId] [outDir]
import { chromium } from "playwright-core";
import os from "node:os";
const talk = process.argv[2] || "7011", out = process.argv[3] || "/tmp";
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
await page.goto(`http://localhost:8765/cinema/#talk-${talk}`, { waitUntil: "networkidle" });
await page.waitForSelector(".face.notes");
await page.keyboard.press("k");
await page.waitForTimeout(6000);
const yt = () => page.frames().find((f) => /youtube/.test(f.url()));
if (yt()) await yt().evaluate(() => document.getElementById("movie_player").seekTo(120, true));
await page.waitForTimeout(2000);
await page.keyboard.press("c");
await page.waitForTimeout(5000);
let ok = false;
if (yt()) {
  const lines = await yt().evaluate(() => [...document.querySelectorAll(".ytp-caption-segment")].map((e) => { const r = e.getBoundingClientRect(); return { text: e.textContent, top: r.top, bottom: r.bottom }; }));
  const frame = await page.locator("#tube iframe").boundingBox(), tube = await page.locator("#tube").boundingBox();
  const shown = lines.filter((l) => frame.y + l.top >= tube.y - 1 && frame.y + l.bottom <= tube.y + tube.height + 1);
  ok = lines.length > 0 && shown.length === lines.length;
  console.log(`${lines.length} caption line(s), ${shown.length} in view: ${lines.map((l) => l.text).join(" / ") || "(none)"}`);
}
await page.screenshot({ path: `${out}/cc.png` });
console.log(ok ? "ok" : "CAPTIONS NOT VISIBLE");
await browser.close();
process.exit(ok ? 0 : 1);
