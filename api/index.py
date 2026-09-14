import sys
from pathlib import Path

# Add backend directory to sys.path so app.* package imports resolve properly
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

# Vercel's Python runtime detects and exposes the ASGI `app` callable
