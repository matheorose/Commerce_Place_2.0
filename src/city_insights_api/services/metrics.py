"""KMeans helpers used by the API pipeline."""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score

from ..models.domain import KMeansMetrics


class KMeansEvaluator:
    def __init__(self, default_k_min: int = 2, default_k_max: int = 10) -> None:
        self.default_k_min = default_k_min
        self.default_k_max = default_k_max

    def suggest_k_range(
        self,
        cell_count: int,
        *,
        k_min: int | None = None,
        k_max: int | None = None,
    ) -> Tuple[int, int]:
        """Return a (min, max) range of clusters adapted to the dataset size."""

        if k_min is None and k_max is None:
            min_k, max_k = self._adaptive_range(cell_count)
        else:
            min_k = k_min if k_min is not None else self.default_k_min
            max_k = k_max if k_max is not None else self.default_k_max

        max_allowed = max(2, cell_count - 1)
        min_k = max(2, min(min_k, max_allowed))
        max_k = max(min_k, min(max_k, max_allowed))

        if max_k <= min_k and max_allowed > min_k:
            max_k = min(max_allowed, min_k + 1)

        return min_k, max_k

    def evaluate(
        self,
        cells: Sequence[Dict[str, float]],
        *,
        k_min: int | None = None,
        k_max: int | None = None,
    ) -> KMeansMetrics | None:
        if not cells:
            return None

        count = len(cells)

        k_min, k_max = self.suggest_k_range(count, k_min=k_min, k_max=k_max)

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

    def _adaptive_range(self, cell_count: int) -> Tuple[int, int]:
        if cell_count < 20:
            return 2, 4
        if cell_count < 60:
            return 3, 6
        if cell_count < 150:
            return 4, 8
        if cell_count < 300:
            return 5, 10
        if cell_count < 600:
            return 6, 12
        return 8, 15


__all__ = ["KMeansEvaluator"]
