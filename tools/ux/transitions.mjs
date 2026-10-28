// Record the hall -> seat -> hall round trip on a laptop window as a video, to look at the seams between the stills and
// the walks frame by frame (John 19/10: it should feel seamless going between the two). Serve the site first:
// node tools/ux/serve.mjs
//   node tools/ux/transitions.mjs <outDir> [room] [width] [height]
import { chromium } from "playwright-core";
import fs from "node:fs";
import os from "node:os";

const out = process.argv[2], room = process.argv[3] || "3";
const viewport = { width: +(process.argv[4] || 1600), height: +(process.argv[5] || 900) };
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`,
  args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
const ctx = await browser.newContext({ viewport, recordVideo: { dir: out, size: viewport } });
await ctx.addInitScript(() => { try { sessionStorage.setItem("cinema-intro", "1"); localStorage.setItem("cinema-walks", "on"); } catch (e) {} });
const page = await ctx.newPage();
const t0 = Date.now(), marks = [];
const mark = (what) => marks.push(`${((Date.now() - t0) / 1000).toFixed(2)} s  ${what}`);
await page.goto("http://localhost:8765/", { waitUntil: "networkidle" });
await page.waitForSelector(".face.prog .card");
await page.waitForTimeout(1500);
const card = page.locator(".face.prog .card:not(.is-off)").filter({ has: page.locator(".where b", { hasText: new RegExp(`^${room}$`) }) }).first();
if (!(await card.count())) { console.log(`no walkable card for room ${room} in the first slot; pick another room`); process.exit(1); }
mark(`click a room ${room} talk`);
await card.click();
await page.waitForSelector(".face.notes", { timeout: 60000 });
mark("seat (notes mounted)");
await page.waitForTimeout(3000);
mark("back to the programme");
await page.locator("#toProg").click();
await page.waitForSelector(".face.prog", { timeout: 60000 });
mark("hall (programme mounted)");
await page.waitForTimeout(2000);
await ctx.close();
await browser.close();
fs.writeFileSync(`${out}/marks.txt`, marks.join("\n") + "\n");
console.log(marks.join("\n"));
console.log(`video: ${fs.readdirSync(out).filter((f) => f.endsWith(".webm")).map((f) => `${out}/${f}`).join(" ")}`);
