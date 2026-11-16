"""Tiny read-only web server for the key map page (viz.html + /state JSON).

Runs in a daemon thread. It never touches Live's API: the script's main thread
publishes a plain dict snapshot, the server only serialises it.
"""
from __future__ import absolute_import

import json
import os
import threading
import time

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # pragma: no cover - Live without http.server
    BaseHTTPRequestHandler = HTTPServer = None

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viz.html")


if HTTPServer is not None:
    class LocalServer(HTTPServer):
        """HTTPServer whose bind skips socket.getfqdn(): Live's Python has no 'idna' codec."""

        def server_bind(self):
            HTTPServer.__bases__[0].server_bind(self)  # socketserver.TCPServer
            self.server_name, self.server_port = self.server_address[:2]


class Viz(object):
    def __init__(self, port):
        if HTTPServer is None:
            raise RuntimeError("http.server not available")
        self._state, self._stamp = {}, time.time()
        viz = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/state"):
                    state, stamp = viz._state, viz._stamp
                    snapshot = dict(state, age=round(time.time() - stamp, 3)) if state else {}
                    body, kind = json.dumps(snapshot).encode("utf-8"), "application/json"
                else:
                    with open(PAGE, "rb") as f:
                        body, kind = f.read(), "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self._server = LocalServer(("127.0.0.1", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="LoopMixViz")
        self._thread.daemon = True
        self._thread.start()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        """Set from Live's main thread; `age` lets the page correct for delivery time."""
        self._state, self._stamp = value, time.time()

    def close(self):
        self._server.shutdown()
        self._server.server_close()
