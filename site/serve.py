"""Serve site/dist on the LAN.

    python site/serve.py [--port 8765]      (Windows Python: its firewall rule allows inbound)
"""
import functools
import http.server
import socket
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765


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
    host = socket.gethostbyname(socket.gethostname())
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), functools.partial(Handler, directory=str(DIST)))
    print(f"Fillaprint site on http://{host}:{PORT}/ (all interfaces)", flush=True)
    server.serve_forever()
