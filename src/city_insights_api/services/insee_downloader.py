"""Utilities to download the INSEE carroyage CSV on demand."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

INSEE_CARROYAGE_RESOURCE_ID = "2803f01d-13a1-488e-ab2b-fb47b482111b"
INSEE_CARROYAGE_URL = f"https://www.data.gouv.fr/api/1/datasets/r/{INSEE_CARROYAGE_RESOURCE_ID}"


def download_insee_carroyage(dest_path: Path, *, show_progress: bool = True) -> Path:
    """Download the official INSEE CSV into ``dest_path``."""

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_name(dest.name + ".part")

    req = urllib.request.Request(
        INSEE_CARROYAGE_URL,
        headers={"User-Agent": "Mozilla/5.0 (CityInsights downloader)"},
        method="GET",
    )

    downloaded = 0
    chunk_size = 1024 * 1024  # 1 MB
    try:
        with urllib.request.urlopen(req) as resp, tmp_path.open("wb") as fh:
            total = resp.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)

                if show_progress:
                    _display_progress(downloaded, total)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    finally:
        if show_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()

    size = tmp_path.stat().st_size
    if size < 1_000_000:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Le fichier téléchargé est trop petit ({size} octets) : téléchargement incomplet ?"
        )

    tmp_path.replace(dest)
    if show_progress:
        print(f"✅ CSV INSEE téléchargé dans {dest} ({size / 1e6:.1f} MB)")
    return dest


def _display_progress(downloaded: int, total: int | None) -> None:
    if total:
        pct = downloaded * 100 / total
        sys.stdout.write(
            f"\rTéléchargement: {pct:6.2f}% ({downloaded / 1e6:.1f}/{total / 1e6:.1f} MB)"
        )
    else:
        sys.stdout.write(f"\rTéléchargement: {downloaded / 1e6:.1f} MB")
    sys.stdout.flush()


__all__ = ["download_insee_carroyage", "INSEE_CARROYAGE_RESOURCE_ID", "INSEE_CARROYAGE_URL"]
