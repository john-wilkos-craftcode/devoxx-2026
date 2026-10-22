#!/usr/bin/env python3
"""CSS mask images are fetched with CORS, which file:// forbids, so the three plates (drum ink, drum key, loupe) go
into assets/masks.css as data URIs (lossy WebP with alpha, sized for the largest use at 2x).
  python3 tools/inline.py
"""
import base64
import io
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets"


def data_uri(name, height, quality=82):
    im = Image.open(OUT / f"{name}.png").convert("RGBA")
    w = round(im.width * height / im.height)
    im = im.resize((w, height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=6, exact=False)
    b = buf.getvalue()
    print(f"{name}: {w}x{height} {len(b) // 1024} KB")
    return "data:image/webp;base64," + base64.b64encode(b).decode()


css = ":root {\n  --drum-ink: url(\"%s\");\n  --drum-key: url(\"%s\");\n  --loupe-mask: url(\"%s\");\n}\n" % (
    data_uri("drum-ink", 440), data_uri("drum-key", 440), data_uri("loupe", 320))
(OUT / "masks.css").write_text(css)
print("masks.css", (OUT / "masks.css").stat().st_size // 1024, "KB")
