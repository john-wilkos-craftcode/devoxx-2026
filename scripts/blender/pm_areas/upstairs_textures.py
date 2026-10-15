"""Graphics for the upstairs foyer, drawn (not taken from the photos): the end screen's key visual and the quote
light boxes. Run with system Python (needs Pillow) before building the area:

  python3 scripts/blender/pm_areas/upstairs_textures.py
Writes build/photomatch/upstairs/tex/*.png.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build" / "photomatch" / "upstairs" / "tex"
FONT = ROOT / "scripts" / "blender" / "fonts" / "ArchivoBlack.ttf"


def font(size):
    try:
        return ImageFont.truetype(str(FONT), size)
    except OSError:
        return ImageFont.load_default()


def screen():
    """'BUILD, AGENTS + DEBUG' key visual: navy-to-magenta stage glow, cloud bank at the bottom, DEVOXX logo"""
    W, H = 1600, 900
    rnd = random.Random(4)
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = y / H
            # deep blue base, magenta haze centre-right, brighter towards the top lights
            d = math.hypot((x - 0.62 * W) / W, (y - 0.35 * H) / H)
            mag = max(0.0, 1 - d * 2.2)
            r = 25 + 200 * mag ** 1.4
            g = 20 + 40 * mag ** 2
            b = 90 + 110 * mag + 40 * (1 - t)
            px[x, y] = (int(min(r, 255)), int(min(g, 255)), int(min(b, 255)))
    d = ImageDraw.Draw(im)
    # stage lights along the top
    glow = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(glow)
    for i in range(9):
        x = 420 + i * 120
        col = (255, 60, 220) if i < 4 else (120, 170, 255)
        gd.ellipse([x - 22, 70 - 22, x + 22, 70 + 22], fill=col)
        gd.polygon([(x - 10, 80), (x + 10, 80), (x + 90, 600), (x - 90, 600)], fill=tuple(c // 5 for c in col))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    im = Image.composite(glow, im, glow.convert("L"))
    # clouds: soft white blobs along the bottom and a diagonal bank on the left
    clouds = Image.new("L", (W, H))
    cd = ImageDraw.Draw(clouds)
    for _ in range(260):
        x = rnd.uniform(-50, W + 50)
        base = H * 0.86 - (0.25 * H) * max(0, 1 - x / (0.45 * W))
        y = rnd.gauss(base, 45)
        r = rnd.uniform(25, 75)
        cd.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=rnd.randint(150, 255))
    clouds = clouds.filter(ImageFilter.GaussianBlur(9))
    white = Image.new("RGB", (W, H), (235, 240, 255))
    im = Image.composite(white, im, clouds)
    # a robot and figures on the stage, as silhouettes
    d = ImageDraw.Draw(im)
    for cx, s in ((830, 1.0), (980, 1.3), (1060, 1.25), (1250, 1.6)):
        d.ellipse([cx - 18 * s, 470 - 120 * s, cx + 18 * s, 470 - 84 * s], fill=(30, 25, 50))
        d.rectangle([cx - 22 * s, 470 - 84 * s, cx + 22 * s, 470], fill=(35, 28, 60))
    d.ellipse([1180, 330, 1420, 560], fill=(40, 70, 150))
    d.ellipse([1215, 360, 1385, 520], fill=(25, 40, 95))
    f = font(120)
    for i, line in enumerate(("BUILD,", "AGENTS", "+ DEBUG")):
        d.text((70, 60 + i * 125), line, font=f, fill=(250, 250, 255))
    fl = font(110)
    d.text((70, 690), "DEVOX", font=fl, fill=(250, 250, 255))
    w = d.textlength("DEVOX", font=fl)
    d.text((70 + w, 690), "X", font=fl, fill=(255, 140, 40))
    d.text((74, 815), "FROM DEVELOPERS TO BUILDERS", font=font(26), fill=(220, 225, 240))
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / "screen.png")


def quote(name, lines, W=1800, H=760):
    """backlit quote panel: near-white with the text a shade darker, as printed film over LEDs"""
    im = Image.new("RGB", (W, H), (246, 247, 250))
    d = ImageDraw.Draw(im)
    y = 40
    for text, size in lines:
        f = font(size)
        d.text((40, y), text, font=f, fill=(196, 200, 210))
        y += int(size * 1.15)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(OUT / f"{name}.png")


def totems():
    """the two signage screens on the near columns: a cinema-news page (portrait) and a supplier's logo slide"""
    rnd = random.Random(7)
    W, H = 600, 1050
    im = Image.new("RGB", (W, H), (244, 246, 250))
    d = ImageDraw.Draw(im)
    d.text((150, 30), "WE LOVE CINEMA", font=font(44), fill=(20, 70, 160))
    d.rectangle([0, 120, W, 175], fill=(30, 140, 70))
    d.text((20, 125), "BREAKING NEWS", font=font(38), fill=(255, 255, 255))
    for i in range(2):
        for j in range(3):
            x0, y0 = 20 + j * 190, 190 + i * 190
            base = [(250, 120, 60), (90, 170, 230), (240, 200, 70), (180, 90, 200), (90, 200, 120), (230, 80, 120)][i * 3 + j]
            d.rectangle([x0, y0, x0 + 180, y0 + 180], fill=base)
            for _ in range(5):
                cx, cy, r = x0 + rnd.uniform(20, 160), y0 + rnd.uniform(20, 160), rnd.uniform(12, 40)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(min(255, c + rnd.randint(-80, 80)) for c in base))
    y = 600
    for _ in range(9):
        d.rectangle([20, y, rnd.randint(380, 560), y + 14], fill=(60, 64, 72))
        y += 30
    d.rectangle([0, 880, W, H], fill=(40, 160, 90))
    d.text((20, 900), "DE REST VAN HET ARTIKEL LEZEN?", font=font(26), fill=(255, 255, 255))
    d.rectangle([440, 900, 580, 1040], fill=(255, 255, 255))
    for _ in range(120):
        x, y = rnd.randrange(450, 570, 8), rnd.randrange(910, 1030, 8)
        d.rectangle([x, y, x + 7, y + 7], fill=(0, 0, 0))
    im.save(OUT / "totem-cinema.png")
    im = Image.new("RGB", (960, 540), (232, 238, 250))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 120, 120, 180], 10, outline=(30, 90, 180), width=8)
    d.text((140, 105), "livedooh", font=font(84), fill=(30, 90, 180))
    d.ellipse([700, 120, 940, 420], fill=(110, 180, 240))
    d.ellipse([740, 170, 900, 380], fill=(60, 130, 210))
    im.save(OUT / "totem-livedooh.png")


def poster():
    """a lit film poster in the far left corner: pale sky, two figures, a big serif title"""
    W, H = 760, 620
    im = Image.new("RGB", (W, H), (205, 222, 240))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(190 + 40 * t), int(210 + 30 * t), int(238 + 10 * t)))
    for cx in (150, 250):
        d.ellipse([cx - 32, 120, cx + 32, 190], fill=(200, 160, 130))
        d.rectangle([cx - 60, 190, cx + 60, 480], fill=(40, 50, 80))
    try:
        serif = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 110)
    except OSError:
        serif = font(100)
    d.text((340, 120), "Focker", font=serif, fill=(30, 40, 70))
    d.text((360, 250), "In-Law", font=serif, fill=(30, 40, 70))
    d.text((360, 430), "Rated PG-13 - In cinemas now", font=font(22), fill=(60, 70, 100))
    im.save(OUT / "poster-left.png")


def exterior():
    """the view out of the glass front: overcast blue sky, a row of trees and low buildings, the road"""
    rnd = random.Random(11)
    W, H = 1600, 640
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(110 + 50 * t), int(175 + 40 * t), int(230 + 20 * t)))
    for x in range(0, W, 200):
        d.rectangle([x + 20, 330 - rnd.randint(30, 120), x + 170, 470], fill=(120, 150, 185))
    for _ in range(70):
        x, r = rnd.uniform(0, W), rnd.uniform(30, 70)
        d.ellipse([x - r, 400 - 2 * r, x + r, 430], fill=(70 + rnd.randint(0, 30), 95 + rnd.randint(0, 30), 95 + rnd.randint(0, 25)))
    d.rectangle([0, 470, W, H], fill=(120, 128, 140))
    d.rectangle([0, 540, W, 548], fill=(210, 214, 220))
    im = im.filter(ImageFilter.GaussianBlur(3))
    im.save(OUT / "exterior.png")


if __name__ == "__main__":
    screen()
    exterior()
    poster()
    totems()
    quote("quote-left", [("...OF THE FORCE", 120), ("\"I'll be back\" - the Terminator.  'Run Forrest, run!'", 52),
                         ("be back", 190), ("Here's looking at you, kid.", 60)])
    quote("quote-right", [("MAKE MY DAY", 140), ("Everybody you fight, ends up owning you.", 56),
                          ("may the force be with you", 104), ("Life was like a box of chocolates, you never know", 50)])
    print("textures in", OUT)
