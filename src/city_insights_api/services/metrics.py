"""KMeans helpers used by the API pipeline."""

from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score

from ..models.domain import KMeansMetrics


class KMeansEvaluator:
    def __init__(self, default_k_min: int = 2, default_k_max: int = 10) -> None:
        self.default_k_min = default_k_min
        self.default_k_max = default_k_max

    def evaluate(
        self,
        cells: Sequence[Dict[str, float]],
        *,
        k_min: int | None = None,
        k_max: int | None = None,
    ) -> KMeansMetrics | None:
        if not cells:
            return None

        k_min = k_min or self.default_k_min
        k_max = k_max or self.default_k_max
        if k_min < 2:
            k_min = 2
        if k_max <= k_min:
            k_max = k_min + 1

        count = len(cells)
        if count <= k_min:
            return None

        k_values = [k for k in range(k_min, k_max + 1) if k < count]
        if not k_values:
            return None

        lats = np.array([cell["lat"] for cell in cells], dtype=float)
        lons = np.array([cell["lon"] for cell in cells], dtype=float)
        pops = np.array([cell.get("pop", 1.0) for cell in cells], dtype=float)

        X = np.column_stack([lons, lats])

        inertias: List[float] = []
        silhouettes: List[float] = []
        davies_scores: List[float] = []

        for k in k_values:
            model = KMeans(n_clusters=k, n_init="auto", random_state=42)
            labels = model.fit_predict(X, sample_weight=pops)
            inertias.append(float(model.inertia_))

            try:
                silhouettes.append(float(silhouette_score(X, labels)))
            except ValueError:
                silhouettes.append(float("nan"))

            try:
                davies_scores.append(float(davies_bouldin_score(X, labels)))
            except ValueError:
                davies_scores.append(float("nan"))

        return KMeansMetrics(
            k_values=k_values,
            inertia=inertias,
            silhouette=silhouettes,
            davies_bouldin=davies_scores,
        )


__all__ = ["KMeansEvaluator"]
