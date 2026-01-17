"""High level orchestration for the inhabitants/commerces pipeline."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.cluster import KMeans

from ..core.config import Settings, settings
from ..models.domain import (
    AgentPayload,
    BoundingBox,
    PipelineArtifacts,
    ZoneInsight,
)
from .carroyage import InseeCarroyageGenerator
from .map_builder import MapBuilder
from .metrics import KMeansEvaluator


class PipelineService:
    def __init__(
        self,
        config: Settings | None = None,
        *,
        carroyage: InseeCarroyageGenerator | None = None,
        map_builder: MapBuilder | None = None,
        evaluator: KMeansEvaluator | None = None,
    ) -> None:
        self.config = config or settings
        self.carroyage = carroyage or InseeCarroyageGenerator(self.config.insee_csv_path)
        self.map_builder = map_builder or MapBuilder()
        self.evaluator = evaluator or KMeansEvaluator()

    def run_from_agent(self, agent_result: AgentPayload) -> PipelineArtifacts:
        commerce_data = agent_result.payload or self._load_json(agent_result.result_file)
        return self.run_pipeline(agent_result.result_filename, commerce_data=commerce_data)

    def run_pipeline(self, result_filename: str, *, commerce_data: Dict[str, Any] | None = None) -> PipelineArtifacts:
        json_path = self._result_path(result_filename)
        data = commerce_data or self._load_json(json_path)

        bbox = self._extract_bbox(data)
        city = self._normalize_city(data.get("city") or json_path.stem.split("_", 1)[0])
        category = self._extract_category(data, fallback=self._category_from_filename(json_path.name))

        inhabitants_path = self.config.data_dir / f"carroyage_bbox_{city}.json"
        carroyage_payload = self.carroyage.generate(bbox, inhabitants_path)

        metrics = self.evaluator.evaluate(carroyage_payload.cells)
        commerce_items = data.get("items") or data.get("places") or []
        zones = self._build_zones(carroyage_payload.cells, commerce_items, metrics)

        map_filename = f"map_insee_{city}_{category}.html"
        map_path = self.map_builder.build(
            carroyage_payload,
            data,
            self.config.views_dir / map_filename,
            zones=zones,
        )

        return PipelineArtifacts(
            city=city,
            category=category,
            bbox=bbox,
            inhabitants_file=inhabitants_path,
            commerce_file=json_path,
            map_file=map_path,
            kmeans=metrics,
            zones=zones,
        )

    def build_points_map(self, agent_payload: AgentPayload) -> Path:
        """Generate a lightweight map with only commerce markers."""
        map_filename = f"map_points_{agent_payload.city}_{agent_payload.category_key}.html"
        return self.map_builder.build_points_map(
            agent_payload.bbox,
            agent_payload.places,
            self.config.views_dir / map_filename,
        )

    # Helpers --------------------------------------------------------------
    def _result_path(self, filename: str) -> Path:
        name = filename if filename.lower().endswith(".json") else f"{filename}.json"
        return self.config.result_dir / name

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Fichier commerce introuvable: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_bbox(self, data: Dict[str, Any]) -> BoundingBox:
        bbox = data.get("bbox")
        if not isinstance(bbox, dict):
            raise ValueError("Champ bbox manquant dans le JSON de commerce")
        return BoundingBox(
            south=float(bbox.get("south")),
            west=float(bbox.get("west")),
            north=float(bbox.get("north")),
            east=float(bbox.get("east")),
        )

    def _normalize_city(self, value: str) -> str:
        value = (value or "").strip().lower()
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"[^a-z0-9]+", "_", value)
        value = re.sub(r"_+", "_", value)
        return value.strip("_") or "ville"

    def _category_from_filename(self, filename: str) -> str:
        base = Path(filename).stem
        parts = base.split("_", 1)
        if len(parts) == 2:
            return self._normalize_city(parts[1])
        return self._normalize_city(base)

    def _extract_category(self, data: Dict[str, Any], *, fallback: str) -> str:
        category_info = data.get("category")
        if isinstance(category_info, dict):
            label = category_info.get("key") or category_info.get("label")
            if label:
                return self._normalize_city(str(label))
        return fallback

    def _build_zones(
        self,
        cells: List[Dict[str, Any]],
        commerce_items: List[Dict[str, Any]],
        metrics,
    ) -> List[ZoneInsight]:
        if not cells:
            return []

        k = self._choose_k(metrics, len(cells))
        if k < 2 or len(cells) < k:
            return []

        lats = np.array([cell["lat"] for cell in cells], dtype=float)
        lons = np.array([cell["lon"] for cell in cells], dtype=float)
        pops = np.array([cell.get("pop", 1.0) for cell in cells], dtype=float)

        X = np.column_stack([lons, lats])
        model = KMeans(n_clusters=k, n_init="auto", random_state=42)
        labels = model.fit_predict(X, sample_weight=pops)

        commerce_coords: List[tuple[float, float]] = []
        for item in commerce_items:
            try:
                commerce_coords.append((float(item["lon"]), float(item["lat"])))
            except (KeyError, TypeError, ValueError):
                continue

        commerce_counts = {idx: 0 for idx in range(k)}
        if commerce_coords:
            coords = np.array(commerce_coords, dtype=float)
            predicted = model.predict(coords)
            for label in predicted:
                commerce_counts[int(label)] = commerce_counts.get(int(label), 0) + 1

        raw_zones = []
        for idx in range(k):
            mask = labels == idx
            if not np.any(mask):
                continue
            weights = pops[mask]
            lon_center = float(np.average(lons[mask], weights=weights))
            lat_center = float(np.average(lats[mask], weights=weights))
            total_pop = float(weights.sum())
            lat_values = lats[mask]
            lon_values = lons[mask]
            bounds = BoundingBox(
                south=float(lat_values.min()),
                north=float(lat_values.max()),
                west=float(lon_values.min()),
                east=float(lon_values.max()),
            )

            raw_zones.append(
                {
                    "cluster": idx,
                    "lat": lat_center,
                    "lon": lon_center,
                    "population": total_pop,
                    "bounds": bounds,
                }
            )

        raw_zones.sort(key=lambda zone: zone["population"], reverse=True)

        zones: List[ZoneInsight] = []
        for position, zone in enumerate(raw_zones, start=1):
            cluster_idx = zone["cluster"]
            zones.append(
                ZoneInsight(
                    zone_id=position,
                    lat=zone["lat"],
                    lon=zone["lon"],
                    population=zone["population"],
                    existing_commerces=commerce_counts.get(cluster_idx, 0),
                    bounds=zone["bounds"],
                )
            )

        return zones

    def _choose_k(self, metrics, cell_count: int) -> int:
        if metrics and metrics.k_values:
            silhouettes = metrics.silhouette
            best_idx = None
            best_score = -float("inf")
            for idx, score in enumerate(silhouettes):
                if score is None or (isinstance(score, float) and np.isnan(score)):
                    continue
                if score > best_score:
                    best_score = score
                    best_idx = idx
            if best_idx is not None:
                return metrics.k_values[best_idx]

            davies = metrics.davies_bouldin
            best_idx = None
            best_score = float("inf")
            for idx, score in enumerate(davies):
                if score is None or (isinstance(score, float) and np.isnan(score)):
                    continue
                if score < best_score:
                    best_score = score
                    best_idx = idx
            if best_idx is not None:
                return metrics.k_values[best_idx]

        if cell_count <= 5:
            return 2
        if cell_count <= 50:
            return 3
        if cell_count <= 150:
            return 4
        return 5


__all__ = ["PipelineService"]
