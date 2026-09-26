"""Serve site/dist locally.

    python site/serve.py [--port 8765] [--host 0.0.0.0]

Binds to 127.0.0.1 by default. Pass --host 0.0.0.0 to also accept LAN connections
(Windows Python: its firewall rule allows inbound only once you do this).
"""
import functools
import http.server
import socket
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
HOST = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "127.0.0.1"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".ttf": "font/ttf", ".json": "application/json", ".md": "text/markdown; charset=utf-8",
                      ".js": "text/javascript", ".css": "text/css"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((HOST, PORT), functools.partial(Handler, directory=str(DIST)))
    if HOST == "0.0.0.0":
        label, note = socket.gethostbyname(socket.gethostname()), " (all interfaces)"
    else:
        label, note = HOST, ""
    print(f"Fillaprint site on http://{label}:{PORT}/{note}", flush=True)
    server.serve_forever()
