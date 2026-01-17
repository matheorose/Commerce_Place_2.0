"""Convenience entrypoint to launch the API with a single command."""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


if __name__ == "__main__":
    _ensure_src_on_path()
    uvicorn.run(
        "city_insights_api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
