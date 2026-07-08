#!/usr/bin/env python3
"""Serve the pygbag web build with the cross-origin isolation headers that
pygame-web/WASM requires (SharedArrayBuffer). Usage:

    python serve_web.py [port] [dir]      # defaults: 8000  build/web

Then open http://localhost:8000  (or http://<your-LAN-ip>:8000 on a phone
on the same network).
"""
import functools
import http.server
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = sys.argv[2] if len(sys.argv) > 2 else "build/web"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=DIRECTORY)
    with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"Serving {DIRECTORY} at http://localhost:{PORT}  (COOP/COEP enabled)")
        httpd.serve_forever()
