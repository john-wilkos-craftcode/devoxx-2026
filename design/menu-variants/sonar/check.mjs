import fs from "node:fs";
globalThis.window = {};
for (const f of ["../data.js", "./blips.js"]) new Function("window", fs.readFileSync(new URL(f, import.meta.url), "utf8"))(window);
const M = window.MENU, ids = new Set(M.talks.map(t => t.id)); let bad = 0;
for (const b of window.BLIPS) {
  const t = M.recap.trends[b.v], pool = new Set(b.side != null ? t.debate.sides[b.side].talkIds : t.talkIds);
  for (const id of b.talks) if (!ids.has(id) || !(pool.has(id) || t.talkIds.includes(id))) { console.log("BAD", b.id, id); bad++; }
}
console.log(window.BLIPS.length, "blips", bad, "problems");
