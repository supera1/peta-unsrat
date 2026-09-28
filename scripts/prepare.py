#!/usr/bin/env python3
"""Fit the OSM campus boundary onto the drone photo and draft simple
polygons for large roofs inside that boundary."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC_IMAGE = ROOT / "DJI_20260306173942_0655_D copy.JPG"
OUT_IMAGE = ROOT / "assets" / "campus.jpg"
OUT_DATA = ROOT / "data"
DEBUG = ROOT / "data" / "debug"

IMG_W = 4000
IMG_H = 2256

# Independent scale, north-up. Fitted to the vegetated campus in the photo.
LAT_N, LAT_S = 1.4615773, 1.4533888
LON_W, LON_E = 124.8251447, 124.8306590
X_W, X_E = 0.125 * IMG_W, 0.775 * IMG_W
Y_N, Y_S = 0.075 * IMG_H, 0.930 * IMG_H

WAY_REFS = [
    2538840982, 2539652416, 4444977540, 2539652418, 2539652420, 2539652422,
    2539652424, 2539652426, 2539652428, 2538805283, 2539652430, 2539652432,
    2539652433, 8784957389, 8784957388, 2539652435, 2538851469, 2539652437,
    2646084389, 2539652439, 2539652441, 2539652443, 2539652445, 2539652446,
    2539652448, 2539652450, 2539652452, 2539652454, 2539652455, 4445027176,
    2539652459, 2646075115, 2539652461, 2539652462, 2646075113, 2646075114,
    2646075112, 2646076665, 2646076664, 2646075110, 2539652464, 8786266477,
    8786266476, 8786266478, 2539652470, 8786266479, 2539652472, 2539652474,
    2539652476, 12040143058, 2539652478, 2538858372, 2538858371, 2538840982,
]
NODES = {
    2538805283: (1.4608453, 124.8266229),
    2538840982: (1.4606239, 124.8299529),
    2538851469: (1.4567503, 124.8254100),
    2538858371: (1.4605472, 124.8298270),
    2538858372: (1.4601727, 124.8296982),
    2539652416: (1.4608322, 124.8292209),
    2539652418: (1.4613256, 124.8290385),
    2539652420: (1.4615293, 124.8287488),
    2539652422: (1.4615588, 124.8279401),
    2539652424: (1.4615773, 124.8275968),
    2539652426: (1.4610113, 124.8275001),
    2539652428: (1.4611443, 124.8269219),
    2539652430: (1.4597868, 124.8253517),
    2539652432: (1.4595960, 124.8252619),
    2539652433: (1.4588419, 124.8251647),
    2539652435: (1.4577218, 124.8252512),
    2539652437: (1.4565956, 124.8254336),
    2539652439: (1.4558341, 124.8256482),
    2539652441: (1.4554802, 124.8263563),
    2539652443: (1.4545364, 124.8271609),
    2539652445: (1.4538821, 124.8276437),
    2539652446: (1.4533888, 124.8283733),
    2539652448: (1.4536462, 124.8284377),
    2539652450: (1.4540752, 124.8284806),
    2539652452: (1.4547509, 124.8285664),
    2539652454: (1.4551263, 124.8287059),
    2539652455: (1.4552482, 124.8288141),
    2539652459: (1.4555124, 124.8296608),
    2539652461: (1.4556995, 124.8295463),
    2539652462: (1.4558043, 124.8295946),
    2539652464: (1.4560510, 124.8304296),
    2539652470: (1.4575241, 124.8306566),
    2539652472: (1.4594351, 124.8306590),
    2539652474: (1.4595183, 124.8303849),
    2539652476: (1.4593520, 124.8302830),
    2539652478: (1.4599178, 124.8296098),
    2646075110: (1.4561313, 124.8301957),
    2646075112: (1.4562251, 124.8298010),
    2646075113: (1.4558809, 124.8296269),
    2646075114: (1.4560486, 124.8297321),
    2646075115: (1.4555826, 124.8294979),
    2646076664: (1.4562370, 124.8299596),
    2646076665: (1.4562949, 124.8298257),
    2646084389: (1.4560205, 124.8255957),
    4444977540: (1.4612071, 124.8292005),
    4445027176: (1.4549366, 124.8294988),
    8784957388: (1.4580135, 124.8251702),
    8784957389: (1.4582990, 124.8251447),
    8786266476: (1.4565187, 124.8304097),
    8786266477: (1.4563074, 124.8304444),
    8786266478: (1.4567171, 124.8304877),
    8786266479: (1.4576327, 124.8300357),
    12040143058: (1.4597730, 124.8299504),
}


def ll_to_pixel(lat: float, lon: float) -> tuple[float, float]:
    x = X_W + (lon - LON_W) / (LON_E - LON_W) * (X_E - X_W)
    y = Y_N + (LAT_N - lat) / (LAT_N - LAT_S) * (Y_S - Y_N)
    return float(x), float(y)


def campus_pixels() -> list[tuple[float, float]]:
    return [ll_to_pixel(*NODES[ref]) for ref in WAY_REFS]


def campus_pct(points: list[tuple[float, float]]) -> list[list[float]]:
    return [[round(x / IMG_W * 100, 3), round(y / IMG_H * 100, 3)] for x, y in points]


def load_names() -> list[str]:
    raw = (ROOT / "NAMA-GEDUNG.csv").read_text(encoding="utf-8-sig")
    names = []
    for line in raw.splitlines():
        name = line.replace("\ufeff", "").replace("\xa0", " ").strip()
        if name:
            names.append(name)
    return names


def save_web_image() -> Image.Image:
    OUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(SRC_IMAGE).convert("RGB")
    image.save(OUT_IMAGE, "JPEG", quality=82, optimize=True, progressive=True)
    return image


def detect_roofs(image: Image.Image, campus_pts: list[tuple[float, float]]) -> list[np.ndarray]:
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    red = cv2.bitwise_or(
        cv2.inRange(hsv, (0, 50, 80), (16, 255, 240)),
        cv2.inRange(hsv, (168, 50, 80), (180, 255, 240)),
    )
    pale = cv2.inRange(hsv, (0, 0, 175), (35, 45, 255))
    mask = cv2.bitwise_or(red, pale)

    small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, small, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, small, iterations=2)

    campus_mask = np.zeros(mask.shape, np.uint8)
    cv2.fillPoly(campus_mask, [np.array(campus_pts, dtype=np.int32)], 255)
    campus_mask = cv2.erode(campus_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)), iterations=2)
    mask = cv2.bitwise_and(mask, campus_mask)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    picked: list[tuple[float, np.ndarray]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1800:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        if width < 36 or height < 28:
            continue
        if area / max(width * height, 1) < 0.32:
            continue
        box = cv2.boxPoints(cv2.minAreaRect(contour)).astype(np.int32)
        picked.append((area, box.reshape(-1, 1, 2)))

    picked.sort(key=lambda item: item[0], reverse=True)
    return [poly for _, poly in picked[:24]]


def poly_to_pct(poly: np.ndarray) -> list[list[float]]:
    points = []
    for x, y in poly.reshape(-1, 2):
        points.append([
            round(float(x) / IMG_W * 100, 3),
            round(float(y) / IMG_H * 100, 3),
        ])
    if points[0] != points[-1]:
        points.append(points[0])
    return points


def centroid(pct: list[list[float]]) -> list[float]:
    xs = [point[0] for point in pct[:-1]]
    ys = [point[1] for point in pct[:-1]]
    return [round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3)]


def write_debug(image: Image.Image, campus_pts, roofs) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.polygon(campus_pts, outline=(220, 40, 40, 255), width=5)
    for poly in roofs:
        pts = [tuple(map(float, point)) for point in poly.reshape(-1, 2)]
        draw.polygon(pts, outline=(255, 220, 70, 255), fill=(255, 210, 40, 80), width=3)
    overlay.save(DEBUG / "overlay.jpg", "JPEG", quality=80)


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    image = save_web_image()
    campus_pts = campus_pixels()
    roofs = detect_roofs(image, campus_pts)
    names = load_names()

    campus = {
        "type": "Feature",
        "properties": {
            "name": "Universitas Sam Ratulangi",
            "source": "OpenStreetMap way 247020582",
            "attribution": "© OpenStreetMap contributors",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [campus_pct(campus_pts)],
        },
    }

    buildings = []
    for index, poly in enumerate(roofs, start=1):
        pct = poly_to_pct(poly)
        buildings.append({
            "id": f"gedung-{index:02d}",
            "name": "",
            "polygon": pct,
            "anchor": centroid(pct),
        })

    (OUT_DATA / "campus.json").write_text(
        json.dumps(campus, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DATA / "names.json").write_text(
        json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DATA / "buildings.json").write_text(
        json.dumps(buildings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_debug(image, campus_pts, roofs)
    print(f"image {OUT_IMAGE.stat().st_size / 1024:.0f} KB")
    print(f"names {len(names)}")
    print(f"draft polygons {len(buildings)}")


if __name__ == "__main__":
    main()
