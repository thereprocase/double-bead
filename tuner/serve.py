"""Run with python -m tuner.serve; no web framework or network services required."""
import argparse
from collections import OrderedDict
import errno
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from urllib.parse import urlsplit
import webbrowser

from .model import Catalog, ROOT, TunerError, source_commit
from .worker import CACHE_ENV, CACHE_SECRET_ENV

MAX_BODY = 256 * 1024
# A response is ~25 KB and a miss costs 6-30 s of geometry; keep enough for undo, redo and
# switching between a handful of glyphs.
CACHE_ENTRIES = 128
WORKER_TIMEOUT = 180     # s; a cold validation of all three families takes about 30 s
# s for a request line, headers or body to arrive: a client that sends part of a request and
# then stalls must not hold a server thread open.
REQUEST_TIMEOUT = 15
# Open connections, each holding a thread until it finishes or times out. One page uses a few;
# the cap keeps a flood of idle connections from exhausting threads within that timeout.
MAX_CONNECTIONS = 32
CACHE_PREFIX = "fillaprint-tuner-"
STALE_CACHE_AGE = 24 * 3600     # s
IN_USE = {errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", errno.EADDRINUSE)}
DENIED = {errno.EACCES, errno.EPERM, getattr(errno, "WSAEACCES", errno.EACCES)}
CACHE_PID = re.compile(re.escape(CACHE_PREFIX) + r"(\d+)-")

# Every error body is {"error": message, "code": short code}. Status codes:
#   400  the request or its session cannot be used: malformed JSON, invalid or stale session,
#        source files changed on disk
#   403  not the local page, or no valid token      404  unknown path
#   405  method other than GET and POST              408  request body arrived too slowly
#   409  another preview is running                  415  body is not JSON
#   422  the worker could not build or check the edited geometry; its code says why
#   500  the server or the worker failed             503  too many open connections
#   504  the worker ran out of time


class TunerServer(ThreadingHTTPServer):
    daemon_threads = True
    # Windows (the platform with SO_EXCLUSIVEADDRUSE) gives SO_REUSEADDR another meaning: a socket may
    # bind a port that another socket is already listening on. With it set, another program could take
    # over the tuner's port, and a busy port fails with WSAEACCES rather than WSAEADDRINUSE, which
    # bind_error would report as a forbidden port. The tuner reserves its port there instead. Elsewhere
    # SO_REUSEADDR only lets a restarted tuner bind while its old connections wind down.
    allow_reuse_address = not hasattr(socket, "SO_EXCLUSIVEADDRUSE")

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, port, root=ROOT, max_connections=MAX_CONNECTIONS):
        self.catalog = Catalog(root)
        self.commit = source_commit(root, [p for p in self.catalog.inputs if p.startswith("beadjoint/")])
        self.token = secrets.token_urlsafe(32)
        self.busy = threading.BoundedSemaphore(1)
        self.connections = threading.BoundedSemaphore(max_connections)
        self.cache = OrderedDict()
        self.cache_lock = threading.Lock()
        # Finished glyphs shared by this server's workers; private to this user and process. The
        # secret authenticates the cache records and is never written to disk.
        self.glyph_cache = tempfile.mkdtemp(prefix=f"{CACHE_PREFIX}{os.getpid()}-")
        self.worker_env = {**os.environ, CACHE_ENV: self.glyph_cache, CACHE_SECRET_ENV: secrets.token_hex(32)}
        try:
            super().__init__(("127.0.0.1", port), Handler)
        except (OSError, OverflowError):
            shutil.rmtree(self.glyph_cache, ignore_errors=True)
            raise

    def server_close(self):
        super().server_close()
        shutil.rmtree(self.glyph_cache, ignore_errors=True)

    def process_request(self, request, client_address):
        if not self.connections.acquire(blocking=False):
            self.refuse(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connections.release()

    def refuse(self, request):
        """Answer a connection over the cap at once, without reading from it or starting a thread."""
        body = json.dumps({"error": "The tuner has too many open connections. Try again shortly.",
                           "code": "too_many_connections"}).encode()
        head = ("HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\nCache-Control: no-store\r\nRetry-After: 1\r\n"
                "Connection: close\r\n\r\n").encode()
        try:
            request.settimeout(1)
            request.sendall(head + body)
        except OSError:
            pass
        self.shutdown_request(request)

    def cached(self, key):
        with self.cache_lock:
            data = self.cache.get(key)
            if data is not None:
                self.cache.move_to_end(key)
            return data

    def remember(self, key, data):
        with self.cache_lock:
            self.cache[key] = data
            while len(self.cache) > CACHE_ENTRIES:
                self.cache.popitem(last=False)

    def run_worker(self, key):
        """(HTTP status, response) for one geometry computation in a fresh process."""
        try:
            # errors="replace": the reply is ASCII JSON, and a stray byte on stderr (a library writing in
            # the Windows code page) must not cost the preview.
            process = subprocess.run([sys.executable, "-m", "tuner.worker"], input=key, capture_output=True,
                                     encoding="utf-8", errors="replace", cwd=self.catalog.root, timeout=WORKER_TIMEOUT,
                                     env=self.worker_env)
        except subprocess.TimeoutExpired:
            return 504, {"error": f"The preview took longer than {WORKER_TIMEOUT // 60} minutes and was stopped. "
                                  "Undo the last change, or try again.", "code": "timeout"}
        if process.stderr:
            sys.stderr.write(process.stderr)     # tracebacks for whoever runs the tuner; never sent to the page
        try:
            data = json.loads(process.stdout)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict):
            return 500, {"error": "The geometry worker stopped unexpectedly. Check that requirements.txt is installed.",
                         "code": "worker_failed"}
        if process.returncode or "error" in data:
            return 422, {"error": str(data.get("error") or "The geometry worker failed."),
                         "code": str(data.get("code") or "error")}
        return 200, data


class Handler(BaseHTTPRequestHandler):
    timeout = REQUEST_TIMEOUT

    def log_message(self, *args):
        pass

    def reply(self, code, data, mime="application/json; charset=utf-8", headers=()):
        body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode() if mime.startswith("application/json") else data
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        if self.command == "HEAD":
            return
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def fail(self, code, message, error_code, headers=()):
        self.reply(code, {"error": message, "code": error_code}, headers=headers)

    def send_error(self, code, message=None, explain=None):
        """The standard library's own errors (unknown method, malformed request line, oversized
        headers) in the same JSON form as every other error."""
        self.close_connection = True
        if code == HTTPStatus.NOT_IMPLEMENTED:          # no do_<METHOD> for this request's method
            return self.fail(405, "The tuner only answers GET and POST.", "method_not_allowed",
                             headers=[("Allow", "GET, POST")])
        text = {HTTPStatus.REQUEST_URI_TOO_LONG: "The request line is too long.",
                HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE: "The request headers are too large."}
        self.fail(code, text.get(code, "The request is malformed."), "bad_request")

    def local_request(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        return self.headers.get("Host") in hosts and (origin is None or origin in {"http://" + h for h in hosts})

    def do_GET(self):
        if not self.local_request():
            return self.fail(403, "Use the local tuner URL.", "forbidden")
        path = urlsplit(self.path).path
        if path == "/api/catalog":
            c = self.server.catalog
            return self.reply(200, {"targets": c.targets, "sources": c.hashes, "token": self.server.token,
                                    "commit": self.server.commit, "derived": c.derived})
        static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        for font in ("sans-400", "sans-600", "mono-400"):
            static[f"/fonts/{font}.woff2"] = (f"fonts/{font}.woff2", "font/woff2")
        if path not in static:
            return self.fail(404, "Not found.", "not_found")
        name, mime = static[path]
        self.reply(200, (ROOT / "tuner" / name).read_bytes(), mime if mime.startswith("font/") else mime + "; charset=utf-8")

    def do_POST(self):
        if not self.local_request() or not secrets.compare_digest(self.headers.get("X-Tuner-Token", ""), self.server.token):
            return self.fail(403, "Reload the local tuner page.", "forbidden")
        path = urlsplit(self.path).path
        if path not in ("/api/export", "/api/preview"):
            return self.fail(404, "Not found.", "not_found")
        if self.headers.get_content_type() != "application/json":
            return self.fail(415, "Send JSON.", "unsupported_media_type")
        try:
            request = self.read_json()
            session = request.get("session")
            catalog = self.server.catalog
            catalog.assert_fresh(session)
            values = catalog.validate(session)
            if path == "/api/export":
                return self.reply(200, {"patch": catalog.patch(session)})
            self.preview(request, values, session)
        except TunerError as exc:
            self.reply(400, exc.payload())
        except TimeoutError:
            self.fail(408, "The request arrived too slowly.", "timeout")
        except Exception:
            traceback.print_exc()
            self.fail(500, "The tuner server failed. Restart it and try again.", "internal")

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY:
            raise TunerError(f"Request must be between 1 and {MAX_BODY} bytes.", "bad_request")
        try:
            request = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, ValueError, RecursionError):
            # ValueError also covers integers past Python's digit limit; RecursionError deep nesting.
            raise TunerError("The request is not valid JSON.", "bad_request") from None
        if not isinstance(request, dict):
            raise TunerError("Expected a JSON object.", "bad_request")
        return request

    def preview(self, request, values, session):
        # Only geometry inputs make the key: the validated edits, not UI revision counters or a
        # session's commit, so undo and redo reuse a previously computed source state.
        inputs = {k: request[k] for k in ("family", "char", "text", "validate") if k in request}
        inputs["session"] = {"schema": 1, "sources": self.server.catalog.hashes, "values": values}
        key = json.dumps(inputs, sort_keys=True)
        data = self.server.cached(key)
        if data is not None:
            return self.reply(200, data)
        if not self.server.busy.acquire(blocking=False):
            return self.fail(409, "A preview is still running. Try again when it finishes.", "busy")
        try:
            status, data = self.server.run_worker(key)
            # A file that changed while the worker ran may have been read either way: neither
            # keep nor return that result.
            self.server.catalog.assert_fresh(session)
            if status == 200:
                self.server.remember(key, data)
            self.reply(status, data)
        finally:
            self.server.busy.release()


def remove_stale_caches(directory=None, now=None):
    """Remove glyph caches that tuner servers left in the temporary directory (a server that was
    killed cannot clean up): this user's own real directories, untouched for a day, whose server
    is not running. Windows cannot tell whether that server runs, so there the day alone decides.
    Returns the names removed."""
    directory = directory or tempfile.gettempdir()
    now = time.time() if now is None else now
    uid = os.getuid() if hasattr(os, "getuid") else None     # Windows: the temporary directory is per user
    removed = []
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return removed
    for entry in entries:
        if not entry.name.startswith(CACHE_PREFIX):
            continue
        try:
            info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if (not stat.S_ISDIR(info.st_mode) or uid is not None and info.st_uid != uid
                or now - info.st_mtime < STALE_CACHE_AGE or _server_running(entry.name)):
            continue
        shutil.rmtree(entry.path, ignore_errors=True)
        removed.append(entry.name)
    return removed


def _server_running(name):
    """Whether the process a cache directory is named after still runs. Older names carry no
    process id, and Windows has no harmless probe, so those count as not running."""
    match = CACHE_PID.match(name)
    if not match or os.name != "posix":
        return False
    try:
        os.kill(int(match[1]), 0)       # signal 0: an existence check, nothing is sent
    except (ProcessLookupError, OverflowError):
        return False
    except OSError:
        return True                     # exists, owned by someone else
    return True


class _Stop(Exception):
    """A termination signal: leave serve_forever so the cache directory is removed."""


def _stop(signum, frame):
    raise _Stop


def bind_error(exc, port, windows=os.name == "nt"):
    """One line explaining why the server cannot listen on port."""
    other = port + 1 if 1024 <= port < 65535 else 8767
    if getattr(exc, "errno", None) in IN_USE:
        return f"Cannot start the tuner: port {port} is already in use. Choose another: python -m tuner.serve --port {other}"
    if getattr(exc, "errno", None) in DENIED and windows:
        # Windows has no privileged ports. It refuses a port another program holds exclusively, or one in
        # a range the system reserves (Hyper-V, WSL and Docker reserve ranges of ports).
        return (f"Cannot start the tuner: Windows does not allow listening on port {port}; another program holds it "
                "or the system reserves it (netsh interface ipv4 show excludedportrange protocol=tcp). Choose another: "
                f"python -m tuner.serve --port {other}")
    if getattr(exc, "errno", None) in DENIED:
        return (f"Cannot start the tuner: this system does not allow listening on port {port}. Choose a port from "
                "1024 to 65535: python -m tuner.serve --port 8767")
    reason = getattr(exc, "strerror", None) or "it could not listen there"
    return f"Cannot start the tuner on port {port}: {reason}. Choose another: python -m tuner.serve --port {other}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    remove_stale_caches()
    try:
        server = TunerServer(args.port)
    except ImportError as exc:
        sys.exit(f"Cannot start the tuner: the Python package {exc.name or 'it needs'} is not installed. Install the "
                 "requirements: python -m pip install --only-binary=:all: -r requirements.txt")
    except ValueError as exc:
        sys.exit(f"Cannot start the tuner: {exc}")
    except (OSError, OverflowError) as exc:
        sys.exit(bind_error(exc, args.port))
    stops = [getattr(signal, name) for name in ("SIGTERM", "SIGHUP") if hasattr(signal, name)]
    for sig in stops:
        signal.signal(sig, _stop)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Fillaprint glyph tuner: {url}\nCtrl+C to stop. Edits stay in your browser until you export a patch.", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except (KeyboardInterrupt, _Stop):
        pass
    finally:
        for sig in stops:
            signal.signal(sig, signal.SIG_IGN)   # a second signal must not interrupt the cleanup
        server.server_close()


if __name__ == "__main__":
    main()
