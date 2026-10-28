#!/usr/bin/env python3
"""Stamp the site's asset references with ?v=<content hash> (see build_site.stamp_assets), without rebuilding data.js.
Run after any change to site/menu.js, site/inks.js or the cinema's css/js (the metrics workflow runs it too).
  python3 scripts/stamp_assets.py
"""
from pathlib import Path
from build_site import stamp_assets

ROOT = Path(__file__).resolve().parents[1]
stamp_assets(ROOT / "site" / "cinema.js", ("./inks.js",))          # the module import, first: it changes cinema.js
stamp_assets(ROOT / "site" / "slop" / "index.html", ("styles.css", "app.js", "../data.js", "../edge.js"))
stamp_assets(ROOT / "site" / "index.html", ("cinema.css", "inks.css", "cinema.js", "data.js", "menu.js"))
