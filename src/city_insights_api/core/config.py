"""Global settings shared across the service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

from ..services.insee_downloader import download_insee_carroyage

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEGACY_AGENT_DIR = PROJECT_ROOT / "legacy_agent"

if Path.cwd() != PROJECT_ROOT:
    os.chdir(PROJECT_ROOT)


def _split_env_list(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    """Encapsulates filesystem paths and runtime options."""

    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:4200"])
    insee_csv_name: str = "carroyage-insee-metro-s2.csv"
    legacy_agent_path: Path = field(
        default_factory=lambda: LEGACY_AGENT_DIR / "Agent-Python-Donnes_de_commerces_a_partir_dune_ville.py"
    )

    result_dir: Path = field(init=False)
    views_dir: Path = field(init=False)
    insee_csv_path: Path = field(init=False)
    mongo_dsn: str = field(default_factory=lambda: os.getenv("MONGO_DSN", "mongodb://localhost:27017"))
    mongo_db_name: str = field(default_factory=lambda: os.getenv("MONGO_DB_NAME", "cityinsights"))
    mongo_collection: str = field(default_factory=lambda: os.getenv("MONGO_COLLECTION", "chat_sessions"))

    def __post_init__(self) -> None:
        origins_env = _split_env_list(os.getenv("API_ALLOWED_ORIGINS"))
        if origins_env:
            self.allowed_origins = origins_env

        legacy_env = os.getenv("LEGACY_AGENT_PATH")
        if legacy_env:
            self.legacy_agent_path = Path(legacy_env)

        self.result_dir = self.data_dir / "result"
        self.views_dir = self.data_dir / "views"
        self.insee_csv_path = self.data_dir / self.insee_csv_name

        for directory in (self.data_dir, self.result_dir, self.views_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_files(self) -> None:
        """Surface actionable errors for required assets."""

        if not self.legacy_agent_path.exists():
            raise FileNotFoundError(
                "Legacy agent introuvable. Définissez LEGACY_AGENT_PATH ou placez le script dans legacy_agent/."
            )
        if not self.insee_csv_path.exists():
            try:
                print("CSV INSEE manquant, téléchargement en cours...")
                download_insee_carroyage(self.insee_csv_path)
            except Exception as exc:  # pragma: no cover - network failure
                raise FileNotFoundError(
                    f"CSV INSEE introuvable à {self.insee_csv_path} et téléchargement impossible ({exc})."
                ) from exc


settings = Settings()
