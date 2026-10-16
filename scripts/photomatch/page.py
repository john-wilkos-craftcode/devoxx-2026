"""The review page: every reference photo next to the model rendered from its solved camera, with a wipe slider,
an opacity blend, the edge overlay and side by side. Local only (the photos are not ours to publish).

  python3 scripts/photomatch/page.py [--open]
Writes C:\\Users\\wilkojo\\kino-renders\\photomatch\\index.html (run compare.py for each area first).
"""
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path("/mnt/c/Users/wilkojo/kino-renders/photomatch")
AREAS = [("outside", "Outside: the facade"), ("entrance", "Entrance and reception"),
         ("hollywood", "Hollywood room"), ("hollywood_side", "Hollywood room: the side aisles and booths"),
         ("upstairs", "Upstairs foyer")]

CSS = """
:root{--bg:#111214;--panel:#1b1d21;--line:#2c2f35;--text:#e8e6e1;--muted:#9a978f;--accent:#f2b134}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:28px 32px 8px;max-width:1500px;margin:auto}h1{font-size:22px;margin:0 0 6px;font-weight:650}
header p{color:var(--muted);margin:0;max-width:900px}
.decide{max-width:1500px;margin:18px auto 0;padding:0 32px}
.decide details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.decide summary{cursor:pointer;font-weight:600}
.decide li{margin:6px 0;color:var(--text)}.decide li span{color:var(--muted)}
@media (max-width:720px){.decide{padding:0 16px}}
nav{position:sticky;top:0;z-index:5;background:rgba(17,18,20,.94);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
nav div{max-width:1500px;margin:auto;padding:10px 32px;display:flex;gap:18px;flex-wrap:wrap}
nav a{color:var(--muted);text-decoration:none;font-size:14px}nav a:hover{color:var(--text)}
main{max-width:1500px;margin:auto;padding:8px 32px 80px}
h2{font-size:18px;margin:40px 0 12px;padding-top:8px;border-top:1px solid var(--line)}
.cam{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin:0 0 22px}
.head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.head h3{margin:0;font-size:15px;font-weight:600;overflow-wrap:anywhere;min-width:0}.head .meta{color:var(--muted);font-size:13px}
.modes{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.modes button{background:#26292e;color:var(--text);border:1px solid var(--line);border-radius:6px;padding:5px 11px;font:inherit;font-size:13px;cursor:pointer}
.modes button[aria-pressed=true]{background:var(--accent);color:#1a1405;border-color:var(--accent)}
.view{position:relative;user-select:none;touch-action:none;border-radius:6px;overflow:hidden;background:#000;cursor:ew-resize}
.view img{display:block;width:100%;height:auto}
.view .top{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.view .bar{position:absolute;top:0;bottom:0;width:2px;background:var(--accent);box-shadow:0 0 0 1px rgba(0,0,0,.4);pointer-events:none}
.tag{position:absolute;top:8px;font-size:12px;background:rgba(0,0,0,.65);padding:2px 8px;border-radius:4px;pointer-events:none}
.tag.l{left:8px}.tag.r{right:8px}
.side{display:grid;grid-template-columns:1fr 1fr;gap:8px}.side img{width:100%;display:block;border-radius:6px}
.op{display:flex;align-items:center;gap:10px;margin-top:8px;color:var(--muted);font-size:13px}.op input{flex:1;max-width:360px}
.notes{color:var(--muted);font-size:13.5px;margin-top:10px;white-space:pre-wrap}
.missing{color:var(--muted);font-style:italic;padding:20px 0}
.lede{color:var(--muted);max-width:900px}
.walk{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;margin:12px 0 18px}
.vids{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;margin:10px 0 16px}
.vids figure{margin:0}.vids video{display:block;border-radius:6px;background:#000;max-height:70vh;max-width:100%}
.vids figure:first-child video{width:min(100%,960px)}
.vids figcaption{color:var(--muted);font-size:12px;margin-top:2px}
.walk.phone{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
.walk figure{margin:0}.walk img{width:100%;display:block;border-radius:6px}
.walk figcaption{color:var(--muted);font-size:12px;margin-top:2px}
.plancheck{max-width:100%;border-radius:6px;display:block}
@media (max-width:720px){header,main,nav div{padding-left:16px;padding-right:16px}.side{grid-template-columns:1fr}}
"""

JS = """
document.querySelectorAll('.cam').forEach(card=>{
  const view=card.querySelector('.view'), top=view.querySelector('.top'), bar=view.querySelector('.bar'),
        tl=view.querySelector('.tag.l'), tr=view.querySelector('.tag.r'), side=card.querySelector('.side'),
        op=card.querySelector('.op'), range=op.querySelector('input'), base=view.querySelector('.base');
  const src={photo:card.dataset.photo,render:card.dataset.render,edges:card.dataset.edges};
  let mode='wipe', x=.5;
  function wipe(){top.style.clipPath=`inset(0 0 0 ${x*100}%)`;bar.style.left=`calc(${x*100}% - 1px)`;}
  function set(m){mode=m;card.querySelectorAll('.modes button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.m===m));
    view.hidden=m==='side';side.hidden=m!=='side';op.hidden=m!=='blend';
    base.src=m==='edges'?src.edges:src.photo;top.src=src.render;
    top.style.display=(m==='edges'||m==='photo')?'none':'block';
    if(m==='render'){base.src=src.render;}
    bar.hidden=m!=='wipe';tl.hidden=tr.hidden=m!=='wipe';
    if(m==='wipe'){top.style.opacity=1;wipe();}else{top.style.clipPath='none';}
    if(m==='blend'){top.style.opacity=range.value/100;}
    view.style.cursor=m==='wipe'?'ew-resize':'default';}
  card.querySelectorAll('.modes button').forEach(b=>b.onclick=()=>set(b.dataset.m));
  range.oninput=()=>{top.style.opacity=range.value/100;};
  function move(e){if(mode!=='wipe')return;const r=view.getBoundingClientRect();x=Math.min(1,Math.max(0,(e.clientX-r.left)/r.width));wipe();}
  view.addEventListener('pointerdown',e=>{view.setPointerCapture(e.pointerId);move(e);});
  view.addEventListener('pointermove',e=>{if(e.buttons)move(e);});
  view.addEventListener('mousemove',e=>{if(mode==='wipe'&&e.buttons===0)move(e);});
  set('wipe');
});
"""


DECISIONS = """<div class="decide"><details open><summary>Where the floor plan and the photos disagree: please confirm or overrule</summary>
<p style="color:var(--muted);margin:8px 0">Every area sits on the venue plan (data/venue/venue.json, Ghost Light's model of the Devoxx
floor plans). Rule used: the plan decides positions on the ground (walls, columns, stairs, facade bays); the photos decide
anything vertical or finer (heights, glazing, piers, colours, dressing).</p><ul>
<li>Hollywood room: no columns at (-3.8, -27.28) and (2.65, -27.28) under the raised ceiling. <span>The photos only fit
without them, taken from the top of the hall steps.</span></li>
<li>Hollywood booths: <span>the plan's two booth islands either side of the aisle, booths named as you remembered them
(left JetBrains, Google Cloud, Belfius, Docker; right ING, Java, unnamed, Red Hat). In the photos JetBrains and ING stand
about 3.5 m further in than the islands' front edge. The far hall beyond the islands isn't in any photo, so it's filled
in plausibly. The schedule screen is on the north wall between the stairwells.</span></li>
<li>Facade: <span>anchored so the three entrance bays face the grand stair; the ground floor is a wall of glass doors; the
walk's door is the pair just west of the stair (two bins moved 1-1.5 m east to clear it). Heights from the photos: the parapet
is ~14.6 m where the plan says 9.2 m.</span></li>
<li>Outside: <span>bollards, banner poles and the road where the Street View photos put them, not where the plan has them.</span></li>
<li>Entrance: <span>both photos stand west of the grand stair looking at the doors; the wood-slat reception is under the
stair; the queue is west of the stair. Glass to the 4.4 m ceiling and no corner pier at the west wall, as in the photos.</span></li>
<li>Upstairs: <span>the corridor is the plan's 19.4 m wide; the screen rig, its funnels and four dark columns come from the photos.</span></li>
<li>Hollywood side aisles: <span>column faces read ~0.55 m against the plan's 0.7 m; the side aisles have a black ceiling with
ducts at ~4.5 m. The ASML booth's bay and the robot photo's spot are best guesses.</span></li>
</ul></details></div>"""


def main():
    cams = {}
    for f in sorted((ROOT / "data" / "photomatch" / "cameras").glob("*.json")):
        cams.update(json.loads(f.read_text()))
    nav, body = [], []
    walk = sorted((OUT / "venue" / "walk").glob("walk-*.png"))
    if walk:
        nav.append('<a href="#flythrough">Fly-through</a>')
        tiles = "".join(f'<figure><img loading="lazy" src="venue/walk/{w.name}" alt="walk frame"><figcaption>'
                        f'{(int(w.stem[5:]) - 1) / 30:.1f} s</figcaption></figure>' for w in walk)
        phone = sorted((OUT / "venue" / "walk-phone").glob("walk-*.png"))
        phone_tiles = ""
        if phone:
            phone_tiles = ('<h3 style="font-size:15px;margin:18px 0 6px">Phones: the same flight in portrait, drifting onto the totem at the end</h3>'
                           '<div class="walk phone">' + "".join(
                               f'<figure><img loading="lazy" src="venue/walk-phone/{w.name}" alt="phone walk frame"><figcaption>'
                               f'{(int(w.stem[5:]) - 1) / 30:.1f} s</figcaption></figure>' for w in phone) + "</div>")
        vids = [(n, t) for n, t in (("preview-laptop-crowd.mp4", "Laptop, with the crowd (new)"), ("preview-laptop.mp4", "Laptop"), ("preview-phone.mp4", "Phone"))
                if (OUT / "venue" / n).exists()]
        videos = ""
        if vids:
            videos = ('<p class="lede">EEVEE previews (Blender\'s real-time engine): for judging motion, pacing and '
                      'framing, not the final lighting.</p><div class="vids">' + "".join(
                          f'<figure><video src="venue/{n}" controls loop muted playsinline preload="metadata"></video>'
                          f'<figcaption>{t}</figcaption></figure>' for n, t in vids) + "</div>")
        body.append(f"""<h2 id="flythrough">Fly-through: the whole venue as one model</h2>
<p class="lede">Stills every 1.5 s along the walk (about {(int(walk[-1].stem[5:]) - 1) / 30:.0f} s at 30 fps): the forecourt, in through the
open door west of the grand stair, past the queue and the reception, down the hall steps, along the aisle between the
booth islands to the schedule screen on the north wall. No people yet. Below: the model cut at 2.3 m from above, with the
plan's columns and walls (red), booth footprints (magenta), steps (orange) and the walk (blue).</p>
{videos}
<div class="walk">{tiles}</div>
{phone_tiles}
<img class="plancheck" src="venue/plan-check.png" alt="the model from above with the plan and the walk drawn on">""")
    for area, title in AREAS:
        names = [k for k, v in cams.items() if v["area"] == area and "photo" in v]
        if not names:
            continue
        nav.append(f'<a href="#{area}">{html.escape(title)}</a>')
        body.append(f'<h2 id="{area}">{html.escape(title)}</h2>')
        for n in names:
            spec = cams[n]
            d = OUT / area / "cmp"
            if not (d / f"{n}-render.jpg").exists():
                body.append(f'<div class="cam"><div class="head"><h3>{html.escape(n)}</h3></div>'
                            f'<div class="missing">not rendered yet</div></div>')
                continue
            rel = f"{area}/cmp/{n}"
            notes = html.escape(spec.get("notes", ""))
            body.append(f"""
<section class="cam" data-photo="{rel}-photo.jpg" data-render="{rel}-render.jpg" data-edges="{rel}-edges.jpg">
 <div class="head"><h3>{html.escape(Path(spec['photo']).name)}</h3>
  <span class="meta">camera {', '.join(f'{c:.1f}' for c in spec['C'])} m</span></div>
 <div class="modes" role="group" aria-label="view">
  <button data-m="wipe">Wipe</button><button data-m="blend">Blend</button><button data-m="side">Side by side</button>
  <button data-m="edges">Edges</button><button data-m="photo">Photo</button><button data-m="render">Render</button></div>
 <div class="view"><img class="base" alt="reference photo" src="{rel}-photo.jpg"><img class="top" alt="render" src="{rel}-render.jpg">
  <div class="bar"></div><span class="tag l">photo</span><span class="tag r">model</span></div>
 <div class="side" hidden><img src="{rel}-photo.jpg" alt="photo"><img src="{rel}-render.jpg" alt="render"></div>
 <div class="op" hidden>model opacity <input type="range" min="0" max="100" value="50"></div>
 {f'<div class="notes">{notes}</div>' if notes else ''}
</section>""")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Photo match review</title>
<style>{CSS}</style></head><body>
<header><h1>Photo match: the model against the reference photos</h1>
<p>Each photo's camera was solved from its vanishing lines (fSpy-style), the photo used as the backplate, and the
architecture and objects modelled until they line up. People are left out on purpose. Drag across a picture to wipe
between photo and model; Edges shows the photo's edges in cyan and the model's in magenta (white where they agree).</p></header>
{DECISIONS}<nav><div>{''.join(nav)}</div></nav><main>{''.join(body)}</main><script>{JS}</script></body></html>"""
    (OUT / "index.html").write_text(page)
    print(OUT / "index.html")
    if "--open" in sys.argv:
        subprocess.run(["/mnt/c/Windows/explorer.exe", "C:\\Users\\wilkojo\\kino-renders\\photomatch\\index.html"],
                       cwd="/mnt/c/Users/wilkojo")


if __name__ == "__main__":
    main()
