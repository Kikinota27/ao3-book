"""Lanzador simple: python run.py  (equivale a python -m ao3book, sin configurar nada más)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ao3book.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())