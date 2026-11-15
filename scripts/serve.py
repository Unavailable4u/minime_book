#!/usr/bin/env python3
"""
serve.py -- serve the Atlas on your machine, the way Vercel will. Standard library only.

    python scripts/serve.py                 # http://localhost:8000
    python scripts/serve.py --port 8080 --open

Why not just open the files? Pages `fetch()` JSON, and browsers refuse that from file:// URLs.
Why not `python -m http.server`? On Windows it takes MIME types from the registry, where `.js` is
often `text/plain`, and then ES modules silently fail to load. This server pins the types the site needs.

Behaviour
    * every response is `Cache-Control: no-store`, so an edit shows up on the next reload
    * URLs are served as-is, like vercel.json (no "clean URLs": /index.html stays /index.html)
    * 404 shows 404.html when the site has one
    * the .git folder is never served
    * binds to 127.0.0.1 only, unless you pass --bind 0.0.0.0 (to test from a phone on your network)
"""
import argparse
import functools
import posixpath
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.dont_write_bytecode = True      # serving the site should not leave __pycache__ folders behind

ROOT = Path(__file__).resolve().parent.parent

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".map": "application/json",
    ".wasm": "application/wasm",
}


def mime_for(path):
    """MIME type for a file name; our table first, then the platform's, then binary."""
    ext = posixpath.splitext(str(path))[1].lower()
    if ext in MIME:
        return MIME[ext]
    import mimetypes
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"


class Handler(SimpleHTTPRequestHandler):
    def guess_type(self, path):
        return mime_for(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _blocked(self):
        parts = [p for p in self.path.split("?", 1)[0].split("/") if p]
        return ".git" in parts

    def do_GET(self):
        if self._blocked():
            return self.send_error(404, "File not found")
        return super().do_GET()

    def do_HEAD(self):
        if self._blocked():
            return self.send_error(404, "File not found")
        return super().do_HEAD()

    def send_error(self, code, message=None, explain=None):
        page = Path(self.directory) / "404.html"
        if code == 404 and page.is_file() and self.command == "GET":
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", MIME[".html"])
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string().split()[1], fmt % args))


def make_server(root, bind="127.0.0.1", port=8000):
    handler = functools.partial(Handler, directory=str(root))
    return ThreadingHTTPServer((bind, port), handler)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serve the Atlas locally.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--bind", default="127.0.0.1", help="address to listen on (default 127.0.0.1; 0.0.0.0 = whole network)")
    ap.add_argument("--dir", default=str(ROOT), help="folder to serve (default: the repo root)")
    ap.add_argument("--open", action="store_true", help="open the site in your browser")
    args = ap.parse_args(argv)
    try:
        server = make_server(args.dir, args.bind, args.port)
    except OSError as e:
        sys.exit(f"Cannot listen on {args.bind}:{args.port} ({e.strerror or e}). Is another server running? Try --port {args.port + 1}.")
    host = "localhost" if args.bind in ("127.0.0.1", "0.0.0.0") else args.bind
    url = f"http://{host}:{args.port}/"
    print(f"Serving {args.dir}\n  {url}\nCtrl+C to stop.", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
