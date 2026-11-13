"""Local server for the FMMT 27.

    python server.py            then open http://127.0.0.1:8627

GET /                 the tool
GET /api/status       is the game running, which build, in-game date
GET /api/progress     how far the current load has got
GET /api/players      every player with minutes (?scope=competitive|league|all|cups|continental,
                      ?all=1 to also include players with no minutes yet (profile only),
                      ?rescan=1 to rebuild the player list)

Listens on 127.0.0.1 only. Reads the game's memory read-only.
"""
import json
import os
import random
import struct
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from export import to_row
from fm27 import SCOPES, Game
from sanity import KNOWN_BUILDS, check

PORT = 8627
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "FMMT 27.html"
ICON = "FMMT 27.ico"


def bundled(name: str) -> str:
    """A file bundled inside the exe, else next to the reader folder."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), name)
    return os.path.join(HERE, "..", name)


def page_path() -> str:
    return bundled(PAGE)


class Live:
    """One attached Game, re-created when the game restarts or the save changes."""

    def __init__(self):
        self.g: Game | None = None
        self.lock = threading.Lock()
        self.progress: dict = {}  # read without the lock while a load holds it

    def _attach(self):
        if self.g:
            try:
                self.g.close()
            except OSError:
                pass
        self.g = Game()

    def _healthy(self) -> bool:
        """Cached player addresses still point at players (same process, same save)?"""
        g = self.g
        if not g or g._players is None:
            return False
        try:
            if g.p.read(g.build.module.base, 2) != b"MZ":
                return False
            sample = random.sample(g._players, min(200, len(g._players)))
            ok = sum(g.p.u64(a) in (g.player_vt, g.staff_vt) and g._live(a, g.shift(a)) for a in sample)
            return ok >= 0.98 * len(sample)
        except (OSError, struct.error, TypeError):
            return False

    def status(self):
        with self.lock:
            try:
                if not self.g:
                    self._attach()
                return {"ok": True, "pid": self.g.p.pid, "build": self.g.build.id,
                        "build_known": self.g.build.id in KNOWN_BUILDS}
            except Exception as e:  # game not running, access denied, unknown build
                self.g = None
                return {"ok": False, "error": str(e)}

    def _read_progress(self, done: int, total: int):
        self.progress = {"phase": "read", "done": done, "total": total}

    def players(self, scope: str, rescan: bool, everyone: bool = False):
        with self.lock:
            t0 = time.time()
            for attempt in range(2):
                try:
                    if not self.g:
                        self._attach()
                    self.progress = {"phase": "scan"}
                    if rescan or not self._healthy():
                        self.g.players(refresh=True)
                    today, raw = self.g.read_all(scope, require_minutes=not everyone, progress=self._read_progress)
                    self.progress = {}
                    rows = [to_row(r) for r in raw]
                    rows.sort(key=lambda r: not r.get("Mins"))  # full rows first: the page reads columns from row 0
                    played = sum(1 for r in rows if r.get("Mins"))
                    warnings = check(rows, self.g.build.id, self.g.unlisted)
                    try:
                        mine = self.g.my_clubs()
                    except Exception:
                        traceback.print_exc()
                        mine = []
                    return {"ok": True, "build": self.g.build.id, "warnings": warnings, "my_clubs": mine,
                            "date": today.isoformat() if today else None,
                            "scope": scope, "players": len(self.g.players()), "count": len(rows),
                            "played": played, "everyone": everyone,
                            "seconds": round(time.time() - t0, 1), "rows": rows}
                except Exception as e:
                    traceback.print_exc()
                    self.progress = {}
                    self.g = None  # re-attach once (game restarted?)
                    if attempt:
                        return {"ok": False, "error": str(e)}


LIVE = Live()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # allow the page when opened straight from disk (file:// sends Origin: null), nothing else
        if self.headers.get("Origin") == "null":
            self.send_header("Access-Control-Allow-Origin", "null")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            try:
                with open(page_path(), "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"The tool page was not found next to the reader folder", "text/plain")
        elif u.path == "/favicon.ico":
            try:
                with open(bundled(ICON), "rb") as fh:
                    self._send(200, fh.read(), "image/x-icon")
            except FileNotFoundError:
                self._send(404, b"not found", "text/plain")
        elif u.path == "/api/status":
            self._json(LIVE.status())
        elif u.path == "/api/progress":
            self._json(LIVE.progress)
        elif u.path == "/api/players":
            scope = q.get("scope", ["competitive"])[0]
            if scope not in SCOPES:
                return self._json({"ok": False, "error": f"unknown scope {scope}"}, 400)
            res = LIVE.players(scope, q.get("rescan", ["0"])[0] == "1", q.get("all", ["0"])[0] == "1")
            # a failure while building or sending the reply would otherwise just drop the connection,
            # which the page can only report as "can't reach the reader"
            try:
                body = json.dumps(res, ensure_ascii=False, allow_nan=False).encode("utf-8")
                sys.stderr.write(f"players: {res.get('count', 0):,} rows, {len(body) / 1e6:.0f} MB, "
                                 f"{res.get('seconds', '?')}s, build {res.get('build', '?')}\n")
                self._send(200 if res.get("ok") else 503, body, "application/json; charset=utf-8")
            except (ConnectionError, OSError) as e:
                sys.stderr.write(f"players: the window closed the connection before the data was sent ({e})\n")
            except Exception as e:  # MemoryError, ValueError from an odd value, ...
                traceback.print_exc()
                self._json({"ok": False, "error": f"The reader failed while preparing the data: {type(e).__name__}: {e}"}, 500)
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        """Open one of the page's own outside links in the user's default browser.
        Only those exact links, and only when the request comes from the tool's own page."""
        if urlparse(self.path).path != "/api/open":
            return self._send(404, b"not found", "text/plain")
        port = self.server.server_address[1]
        if self.headers.get("Origin") not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return self._json({"ok": False, "error": "wrong origin"}, 403)
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            url = json.loads(self.rfile.read(n) or b"{}").get("url")
        except (ValueError, AttributeError):
            url = None
        if url not in OUTSIDE_LINKS:
            return self._json({"ok": False, "error": "unknown link"}, 400)
        webbrowser.open(url)
        self._json({"ok": True})


# the only addresses /api/open will open: the links on the tool's page
OUTSIDE_LINKS = {
    "https://buymeacoffee.com/fmoreo",
    "https://community.sports-interactive.com/forums/topic/580105-fm24-statistics-spreadsheet-for-those-that-love-moneyball/",
    "https://github.com/jamiebolden/fm-scoring",
    "https://www.youtube.com/@squirrel_plays_fof4318",
}


class Server(ThreadingHTTPServer):
    # Windows lets a second process bind the same port when SO_REUSEADDR is set, and an old copy
    # then keeps answering with old code. Refuse instead, so only one reader ever runs.
    allow_reuse_address = False


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT
    url = f"http://127.0.0.1:{port}"
    try:
        srv = Server(("127.0.0.1", port), Handler)
    except OSError:
        print(f"The reader is already running at {url} - close its other window first if you updated it.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        sys.exit(1)
    print(f"FMMT 27 running at {url}  (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
