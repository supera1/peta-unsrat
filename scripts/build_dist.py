#!/usr/bin/env python3
"""Copy the public map into dist/ for upload to the university website."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

FILES = [
    "index.html",
    "css/app.css",
    "js/map.js",
    "js/public.js",
    "assets/campus.jpg",
    "data/buildings.json",
    "data/names.json",
    "data/campus.json",
    "vendor/leaflet.css",
    "vendor/leaflet.js",
    "vendor/images/marker-icon.png",
    "vendor/images/marker-icon-2x.png",
    "vendor/images/marker-shadow.png",
    "vendor/images/layers.png",
    "vendor/images/layers-2x.png",
]


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    for relative in FILES:
        source = ROOT / relative
        if not source.exists():
            raise SystemExit(f"missing {relative}")
        target = DIST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    index = (DIST / "index.html").read_text(encoding="utf-8")
    index = index.replace("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "vendor/leaflet.css")
    index = index.replace("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", "vendor/leaflet.js")
    (DIST / "index.html").write_text(index, encoding="utf-8")
    print(f"dist ready: {DIST}")


if __name__ == "__main__":
    main()
