// Serve site/ with byte ranges, like GitHub Pages: python -m http.server has none, so a video can't be seeked
// before it has fully downloaded (the phone's walk starts at the door by seeking).
//   node tools/ux/serve.mjs [port]      (default 8765)
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const dir = new URL("../../site", import.meta.url).pathname, port = +(process.argv[2] || 8765);
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".mp4": "video/mp4", ".jpg": "image/jpeg", ".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2" };
http.createServer((req, res) => {
  let p = path.join(dir, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(dir)) { res.writeHead(404); return res.end(); }
  if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, "index.html");
  if (!fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  const size = fs.statSync(p).size, type = types[path.extname(p)] || "application/octet-stream";
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.range || "");
  if (m) {
    const s = m[1] ? +m[1] : size - +m[2], e = m[1] && m[2] ? +m[2] : size - 1;
    res.writeHead(206, { "Content-Type": type, "Content-Range": `bytes ${s}-${e}/${size}`, "Accept-Ranges": "bytes", "Content-Length": e - s + 1 });
    return fs.createReadStream(p, { start: s, end: e }).pipe(res);
  }
  res.writeHead(200, { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Length": size });
  fs.createReadStream(p).pipe(res);
}).listen(port);
