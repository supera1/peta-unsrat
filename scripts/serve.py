#!/usr/bin/env python3
"""Local server for the campus map. Saves named polygons from the browser."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDINGS = ROOT / "data" / "buildings.json"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.send_error(400, "JSON tidak valid")
            return
        if not isinstance(data, list) or not data:
            self.send_error(400, "Data poligon kosong")
            return
        named = 0
        for item in data:
            if not isinstance(item, dict) or not item.get("id") or not item.get("polygon"):
                self.send_error(400, "Poligon tidak lengkap")
                return
            if str(item.get("name") or "").strip():
                named += 1
        if named == 0:
            self.send_response(204)
            self.end_headers()
            return
        BUILDINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        body = json.dumps({"saved": named, "polygons": len(data)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"saved {named} names / {len(data)} polygons")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 4173), Handler)
    print("http://127.0.0.1:4173")
    server.serve_forever()
