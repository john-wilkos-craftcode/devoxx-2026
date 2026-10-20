import { chromium } from "../../../tools/ux/node_modules/playwright-core/index.mjs";
import os from "node:os"; import path from "node:path";
const b = await chromium.launch({ executablePath: `${os.homedir()}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`, args: ["--no-sandbox"] });
const p = await b.newPage({ viewport: { width: 1500, height: 460 } });
await p.goto("file://" + path.resolve("design/menu-variants/sonar/index.html")); await p.waitForTimeout(800);
await p.click("#hallToggle"); await p.waitForTimeout(600);
await p.screenshot({ path: process.argv[2] }); await b.close();
