// The lid closed: the view moves up onto the film (the picture fills the window, the lid's edge and its buttons below),
// and back down when it opens. Shots of each state, mid-move too, and the tube's box against the cinema screen's.
//   node tools/ux/closed.mjs [outDir] [talkId]
import { chromium } from "playwright-core";
import os from "node:os";
const out = process.argv[2] || "/tmp", talk = process.argv[3] || "7011";
const browser = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"] });
for (const vp of [{ width: 1440, height: 900 }, { width: 1280, height: 720 }, { width: 1920, height: 1080 }]) {
  const name = `${vp.width}x${vp.height}`;
  const page = await (await browser.newContext({ viewport: vp })).newPage();
  await page.goto(`http://localhost:8765/#talk-${talk}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".face.notes");
  await page.evaluate(() => { try { localStorage.setItem("cinema-laptop-hint", "1"); } catch (e) {} });
  const shot = (s) => page.screenshot({ path: `${out}/${name}-${s}.png` });
  const boxes = () => page.evaluate(() => {
    const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom].map(Math.round); };
    return { tube: r(document.querySelector("#tube")), bar: r(document.querySelector("#lidBar")), cine: r(document.querySelector(".face.cine")), lap: r(document.querySelector("#lap")) };
  });
  await page.mouse.move(vp.width / 2, 4);
  await page.keyboard.press("l");
  await page.waitForTimeout(300); await shot("a-closing");
  await page.waitForTimeout(1400); await shot("b-closed-poster");
  console.log(name, "closed", JSON.stringify(await boxes()));
  await page.keyboard.press("k");
  await page.waitForTimeout(7000); await shot("c-closed-playing");
  console.log(name, "playing", JSON.stringify(await boxes()));
  await page.keyboard.press("k");
  await page.waitForTimeout(2500); await shot("d-closed-paused");
  await page.locator("#lapLid").click();
  await page.waitForTimeout(350); await shot("e-opening");
  await page.waitForTimeout(1500); await shot("f-open");
  console.log(name, "open", JSON.stringify(await boxes()));
  await page.context().close();
}
await browser.close();
