"""Generate INSEE grid slices constrained to a bounding box."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
from pyproj import Transformer

from ..models.domain import BoundingBox

COL_X = "X"
COL_Y = "Y"
COL_POP = "ind_c"


@dataclass(slots=True)
class CarroyagePayload:
    bbox: BoundingBox
    cells: List[Dict[str, float]]
    count_cells: int
    total_population: int
    output_file: Path
    data: Dict[str, object]


class InseeCarroyageGenerator:
    """Load the heavy CSV by chunks and keep only cells inside a bbox."""

    def __init__(self, csv_path: Path, chunk_size: int = 200_000) -> None:
        self.csv_path = csv_path
        self.chunk_size = chunk_size
        self.transformer = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)

    def generate(self, bbox: BoundingBox, output_path: Path) -> CarroyagePayload:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV INSEE introuvable: {self.csv_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, float]] = []
        total_population = 0.0

        for chunk in pd.read_csv(self.csv_path, chunksize=self.chunk_size):
            x = chunk[COL_X].astype(float) * 100.0
            y = chunk[COL_Y].astype(float) * 100.0

            lon, lat = self.transformer.transform(x.to_numpy(), y.to_numpy())
            chunk.loc[:, "lat"] = lat
            chunk.loc[:, "lon"] = lon

            mask = (
                (chunk["lat"] >= bbox.south)
                & (chunk["lat"] <= bbox.north)
                & (chunk["lon"] >= bbox.west)
                & (chunk["lon"] <= bbox.east)
                & (chunk[COL_POP].fillna(0) > 0)
            )

            sub = chunk.loc[mask, ["lat", "lon", COL_POP]]

            for lat_val, lon_val, pop_val in sub.itertuples(index=False):
                pop = float(pop_val)
                results.append({
                    "lat": float(lat_val),
                    "lon": float(lon_val),
                    "pop": pop,
                })
                total_population += pop

        payload = {
            "bbox": bbox.model_dump(),
            "cell_size_m": 200,
            "crs_source": "EPSG:3035 (LAEA) from INSEE CSV",
            "crs_output": "EPSG:4326 (WGS84 lat/lon)",
            "count_cells": len(results),
            "total_population": int(round(total_population)),
            "cells": results,
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return CarroyagePayload(
            bbox=bbox,
            cells=results,
            count_cells=len(results),
            total_population=int(round(total_population)),
            output_file=output_path,
            data=payload,
        )


__all__ = ["CarroyagePayload", "InseeCarroyageGenerator"]
