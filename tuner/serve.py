"""Run with python -m tuner.serve; no web framework or network services required."""
import argparse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import webbrowser

from .model import Catalog, ROOT

MAX_BODY = 256 * 1024


class TunerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, root=ROOT):
        self.catalog = Catalog(root)
        self.token = secrets.token_urlsafe(32)
        self.busy = threading.BoundedSemaphore(1)
        self.cache = OrderedDict()
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, data, mime="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode() if mime.startswith("application/json") else data
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def local_request(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (origin is None or origin in {"http://" + h for h in hosts})

    def do_GET(self):
        if not self.local_request():
            return self.reply(403, {"error": "Use the local tuner URL."})
        path = urlsplit(self.path).path
        if path == "/api/catalog":
            c = self.server.catalog
            return self.reply(200, {"targets": c.targets, "sources": c.hashes, "token": self.server.token})
        static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        for font in ("sans-400", "sans-600", "mono-400"):
            static[f"/fonts/{font}.woff2"] = (f"fonts/{font}.woff2", "font/woff2")
        if path not in static:
            return self.reply(404, {"error": "Not found."})
        name, mime = static[path]
        self.reply(200, (ROOT / "tuner" / name).read_bytes(), mime if mime.startswith("font/") else mime + "; charset=utf-8")

    def do_POST(self):
        if not self.local_request() or not secrets.compare_digest(self.headers.get("X-Tuner-Token", ""), self.server.token):
            return self.reply(403, {"error": "Reload the local tuner page."})
        if self.headers.get_content_type() != "application/json":
            return self.reply(415, {"error": "Send JSON."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("Request must be between 1 and 262144 bytes.")
            self.connection.settimeout(10)
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Expected a JSON object.")
            catalog = self.server.catalog
            catalog.assert_fresh()
            catalog.validate(request.get("session"))
            path = urlsplit(self.path).path
            if path == "/api/export":
                return self.reply(200, {"patch": catalog.patch(request["session"])})
            if path != "/api/preview":
                return self.reply(404, {"error": "Not found."})
            # UI revision counters are bookkeeping, not geometry inputs. Undo
            # and redo should reuse a previously computed source state.
            inputs = {k: request[k] for k in ("session", "family", "char", "text", "validate") if k in request}
            key = json.dumps(inputs, sort_keys=True)
            if not self.server.busy.acquire(blocking=False):
                return self.reply(409, {"error": "A preview is still running. Try again when it finishes."})
            try:
                if key not in self.server.cache:
                    process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=key, capture_output=True,
                                             text=True, encoding="utf-8", cwd=catalog.root, timeout=180)
                    try:
                        data = json.loads(process.stdout)
                    except json.JSONDecodeError:
                        raise ValueError("Geometry worker failed. Check that requirements.txt is installed.") from None
                    if process.returncode or "error" in data:
                        return self.reply(422, {"error": data.get("error", "Geometry worker failed.")})
                    self.server.cache[key] = data
                    while len(self.server.cache) > 12:
                        self.server.cache.popitem(last=False)
                self.reply(200, self.server.cache[key])
            finally:
                self.server.busy.release()
        except (ValueError, KeyError, TypeError, TimeoutError, subprocess.TimeoutExpired) as exc:
            self.reply(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = TunerServer(args.port)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Fillaprint glyph tuner: {url}\nCtrl+C to stop. Edits stay in your browser until you export a patch.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
