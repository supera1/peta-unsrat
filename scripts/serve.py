#!/usr/bin/env python3
"""Campus map server. The public map is open; /editor requires a login."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
COOKIE = "peta_editor"
USER = "admin"
MAX_AGE = 60 * 60 * 8


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(SCRIPT_ROOT / ".env")
ROOT = Path(os.environ.get("SERVE_ROOT", SCRIPT_ROOT))
BUILDINGS = ROOT / "data" / "buildings.json"
LOGIN_FILE = Path(os.environ.get("LOGIN_FILE", SCRIPT_ROOT / "login.html"))
GATE = os.environ.get("SERVE_MODE") == "gate"
PASSWORD = os.environ.get("EDITOR_PASSWORD", "")
SECRET = hashlib.sha256(b"peta-unsrat-editor:" + PASSWORD.encode()).digest()


def digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def credentials_ok(username: str, password: str) -> bool:
    if not PASSWORD:
        return False
    user_ok = hmac.compare_digest(digest(username), digest(USER))
    pass_ok = hmac.compare_digest(digest(password), digest(PASSWORD))
    return user_ok and pass_ok


def make_token() -> str:
    exp = str(int(time.time()) + MAX_AGE)
    sig = hmac.new(SECRET, exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def token_ok(value: str) -> bool:
    exp, sep, sig = value.partition(".")
    if not sep or not exp.isdigit() or int(exp) < time.time():
        return False
    expected = hmac.new(SECRET, exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def cookie_header(token: str) -> str:
    return f"{COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={MAX_AGE}"


def clear_cookie_header() -> str:
    return f"{COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def path_only(self) -> str:
        return urlsplit(self.path).path

    def authed(self) -> bool:
        raw = self.headers.get("Cookie", "")
        if not raw:
            return False
        try:
            jar = SimpleCookie()
            jar.load(raw)
        except Exception:
            return False
        morsel = jar.get(COOKIE)
        return bool(morsel and token_ok(morsel.value))

    def redirect(self, location: str, set_cookie: str | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_html(self, status: int, html: str) -> None:
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_login(self) -> None:
        error = ""
        if "salah" in parse_qs(urlsplit(self.path).query):
            error = "Nama pengguna atau kata sandi salah."
        elif not PASSWORD:
            error = "Kata sandi editor belum diatur di server."
        template = LOGIN_FILE.read_text(encoding="utf-8")
        self.send_html(200, template.replace("__ERROR__", error))

    def serve_editor(self) -> None:
        if not self.authed():
            self.serve_login()
            return
        data = (ROOT / "editor.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self, limit: int) -> bytes | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > limit:
            self.send_error(413)
            return None
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        path = self.path_only()
        if path in ("/editor", "/editor/"):
            self.serve_editor()
            return
        if path == "/editor.html":
            self.redirect("/editor")
            return
        if path == "/js/editor.js":
            if not self.authed():
                self.send_error(401, "Perlu masuk")
                return
            return super().do_GET()
        if GATE:
            self.send_error(404)
            return
        return super().do_GET()

    def do_POST(self):
        path = self.path_only()
        if path == "/login":
            raw = self.read_body(8_192)
            if raw is not None:
                self.handle_login(raw)
            return
        if path == "/logout":
            self.redirect("/editor", clear_cookie_header())
            return
        if path != "/save":
            self.send_error(404)
            return
        raw = self.read_body(5_000_000)
        if raw is None:
            return
        if not self.authed():
            self.send_error(401, "Perlu masuk")
            return
        self.handle_save(raw)

    def handle_login(self, raw: bytes) -> None:
        form = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        if credentials_ok(username, password):
            self.redirect("/editor", cookie_header(make_token()))
            print("editor login ok")
            return
        self.redirect("/editor?salah=1")
        print("editor login failed")

    def handle_save(self, raw: bytes) -> None:
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
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        temporary = BUILDINGS.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(BUILDINGS)
        body = json.dumps({"saved": named, "polygons": len(data)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"saved {named} names / {len(data)} polygons")


if __name__ == "__main__":
    host = os.environ.get("SERVE_BIND", "127.0.0.1")
    port = int(os.environ.get("SERVE_PORT", "4173"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"http://{host}:{port}")
    server.serve_forever()
