#!/usr/bin/env python3
"""Standalone helper to download the INSEE carroyage CSV."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    project_root = Path(__file__).resolve().parents[1]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def main() -> None:
    _ensure_src_on_path()
    from city_insights_api.services.insee_downloader import download_insee_carroyage

    project_root = Path(__file__).resolve().parents[1]
    dest = project_root / "data" / "carroyage-insee-metro-s2.csv"
    download_insee_carroyage(dest)


if __name__ == "__main__":
    main()
