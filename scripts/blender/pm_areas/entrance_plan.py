"""The entrance on Ghost Light's floor plan (data/venue/venue.json): every box of floor 0 in the reception's
neighbourhood, in venue coordinates (metres, +x east, +y north, z up), with z made absolute the way build_scene.py
does it: a piece stands on the floor of the room under its centre (the reception's floor is at 1.2), stair pieces
(linkId) are absolute already. Pure Python so the CPython photo-match tools can draw it over the photos too."""
import json
from pathlib import Path

REGION = (-16.0, -64.0, 25.0, -33.0)          # x0, y0, x1, y1
FLOOR = 1.2                                    # reception floor (room "reception", elevation 1.2)
STAIR_VOID = (-2.4, -59.45, 12.4, -49.25)      # grand stair: no ceiling over it


def _inside(b, x, y):
    return b["x"] <= x <= b["x"] + b["w"] and b["y"] <= y <= b["y"] + b["h"]


def load(root):
    v = json.loads((Path(root) / "data" / "venue" / "venue.json").read_text())["venue"]
    rooms = [r for r in v["rooms"] if r["floor"] == 0]

    def ground(x, y):
        best, area = None, float("inf")
        for r in rooms:
            if _inside(r["bounds"], x, y) and r["bounds"]["w"] * r["bounds"]["h"] < area:
                best, area = r, r["bounds"]["w"] * r["bounds"]["h"]
        return (best or {}).get("elevation", 0) or 0

    x0r, y0r, x1r, y1r = REGION
    boxes = []
    for kind in ("obstacles", "decor"):
        for o in v[kind]:
            b = o["bounds"]
            if o.get("floor") != 0 or o.get("hidden"):
                continue
            if b["x"] > x1r or b["x"] + b["w"] < x0r or b["y"] > y1r or b["y"] + b["h"] < y0r:
                continue
            under = 0 if o.get("linkId") else ground(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
            z0, z1 = under + o.get("base", 0), under + o["height"]
            if z1 <= z0:
                continue
            boxes.append({"kind": kind, "x0": b["x"], "y0": b["y"], "x1": b["x"] + b["w"], "y1": b["y"] + b["h"],
                          "z0": z0, "z1": z1, "material": o.get("material"), "link": o.get("linkId"),
                          "exterior": o.get("exterior", False)})
    links = [ln for ln in v["links"] if ln["from"] == 0 and ln["id"] in ("grand-stair", "hall-steps")]
    return boxes, links, [r for r in rooms if r["id"] in ("reception", "threshold", "forecourt")]


def stair_steps(link):
    """the treads of a link as boxes (x0, y0, x1, y1, z0, z1)"""
    b = link["bounds"]
    n = round(link["rise"] / link["riser"])
    going = b["h"] / n
    out = []
    for i in range(n):
        top = link["base"] + ((i + 1) if link["ascending"] else (n - i)) * link["riser"]
        y0 = b["y"] + i * going
        out.append((b["x"], y0, b["x"] + b["w"], y0 + going, top - 0.3, top))
    return out
