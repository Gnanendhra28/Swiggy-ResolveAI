import sys
from pathlib import Path

# Add repository root and backend directory to sys.path so 'backend.app' imports succeed
backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.app.main import app

# Export app for Vercel FastAPI runtime detection
__all__ = ["app"]
