#!/usr/bin/env python3
"""SmartResume.ai Dedicated Admin Panel Standalone Development Server.

Serves the standalone Admin Frontend SPA on port 4174.
Run directly with:
    python admin-panel/server.py
"""

import sys
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("ADMIN_PORT", 4174))
ADMIN_DIR = Path(__file__).resolve().parent

class AdminHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ADMIN_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_GET(self):
        # Fallback to index.html for SPA hash/clean routes if file does not exist
        path = self.translate_path(self.path)
        if not os.path.exists(path) and not path.endswith(".js") and not path.endswith(".css"):
            self.path = "/index.html"
        return super().do_GET()


def run_server(port=PORT):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, AdminHandler)
    print("=" * 65)
    print("  [ADMIN CONSOLE] SMARTRESUME.AI - DEDICATED ADMIN MANAGEMENT")
    print("=" * 65)
    print(f"  Admin Web App running at:  http://127.0.0.1:{port}")
    print(f"  Local Host alias:          http://localhost:{port}")
    print(f"  Directory:                 {ADMIN_DIR}")
    print("  Target Backend API:        http://127.0.0.1:8000 (configurable in UI)")
    print("=" * 65)
    print("  Press Ctrl+C to stop the admin development server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopping Admin Console development server...")
        httpd.server_close()
        sys.exit(0)


if __name__ == "__main__":
    run_server()
