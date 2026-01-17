"""Render Folium maps combining INSEE cells with commerce locations."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

import branca.colormap as cm
import folium
from folium.plugins import HeatMap

from ..models.domain import BoundingBox, ZoneInsight
from .carroyage import CarroyagePayload


class MapBuilder:
    def __init__(self, *, scale: str = "log", radius: int = 22, blur: int = 18, min_opacity: float = 0.25) -> None:
        self.scale = scale
        self.radius = radius
        self.blur = blur
        self.min_opacity = min_opacity

    def build(
        self,
        inhabitants: CarroyagePayload | Dict[str, Any],
        commerce_data: Dict[str, Any],
        output_html: Path,
        *,
        zones: Sequence[ZoneInsight] | None = None,
    ) -> Path:
        inhabitants_payload = inhabitants if isinstance(inhabitants, dict) else inhabitants.data
        bbox = self._normalize_bbox(inhabitants_payload["bbox"])
        cells = inhabitants_payload.get("cells", [])
        commerce_items = commerce_data.get("items") or commerce_data.get("places") or []

        center_lat = (bbox.south + bbox.north) / 2.0
        center_lon = (bbox.west + bbox.east) / 2.0
        fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13)

        self._add_heatmap(fmap, cells)
        if zones:
            self._add_zones(fmap, zones)
        self._add_commerce_layer(fmap, commerce_items)

        output_html.parent.mkdir(parents=True, exist_ok=True)
        fmap.save(output_html)
        return output_html

    # Heatmap --------------------------------------------------------------
    def _add_heatmap(self, fmap: folium.Map, cells: Sequence[Dict[str, Any]]) -> None:
        pops = [float(cell.get("pop", 0.0)) for cell in cells if "lat" in cell and "lon" in cell]
        if not pops:
            return

        pops_sorted = sorted(pops)
        p10 = self._quantile(pops_sorted, 0.10)
        p25 = self._quantile(pops_sorted, 0.25)
        p50 = self._quantile(pops_sorted, 0.50)
        p75 = self._quantile(pops_sorted, 0.75)
        p90 = self._quantile(pops_sorted, 0.90)
        p95 = self._quantile(pops_sorted, 0.95)

        lo_raw = self._quantile(pops_sorted, 0.05)
        hi_raw = self._quantile(pops_sorted, 0.95)
        lo_t = self._transform_pop(lo_raw)
        hi_t = self._transform_pop(hi_raw)
        denom = (hi_t - lo_t) if (hi_t - lo_t) > 1e-12 else 1.0

        def weight(pop_raw: float) -> float:
            value = self._transform_pop(pop_raw)
            w01 = (value - lo_t) / denom
            w01 = self._clamp(w01, 0.0, 1.0)
            return max(0.03, w01)

        heat_data = [
            [float(cell["lat"]), float(cell["lon"]), weight(float(cell.get("pop", 0.0)))]
            for cell in cells
            if "lat" in cell and "lon" in cell
        ]

        HeatMap(
            heat_data,
            radius=self.radius,
            blur=self.blur,
            max_zoom=14,
            min_opacity=self.min_opacity,
        ).add_to(fmap)

        legend = cm.LinearColormap(
            colors=[
                "#2c7bb6",
                "#00a6ca",
                "#00ccbc",
                "#90eb9d",
                "#ffff8c",
                "#f9d057",
                "#f29e2e",
                "#e76818",
                "#d7191c",
            ],
            vmin=p10,
            vmax=p95,
        )
        legend.caption = (
            "Densité de population (hab/cell) — "
            f"p10={self._fmt_int(p10)} p25={self._fmt_int(p25)} médiane={self._fmt_int(p50)} "
            f"p75={self._fmt_int(p75)} p90={self._fmt_int(p90)} p95={self._fmt_int(p95)}"
        )
        legend.add_to(fmap)

    # Commerce markers -----------------------------------------------------
    def _add_commerce_layer(self, fmap: folium.Map, commerce_items: Sequence[Dict[str, Any]]) -> None:
        if not commerce_items:
            return

        feature_group = folium.FeatureGroup(name="Commerces", show=True)
        for item in commerce_items:
            try:
                lat = float(item["lat"])
                lon = float(item["lon"])
            except (KeyError, TypeError, ValueError):  # pragma: no cover - malformed entries
                continue
            label = item.get("name") or item.get("label") or "Commerce"

            folium.Marker(
                location=[lat, lon],
                tooltip=f"📍 {label}",
                icon=folium.Icon(icon="shopping-cart", prefix="fa"),
            ).add_to(feature_group)

            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                weight=2,
                fill=True,
                fill_opacity=0.25,
            ).add_to(feature_group)

        feature_group.add_to(fmap)

        folium.LayerControl(collapsed=False).add_to(fmap)

    def _add_zones(self, fmap: folium.Map, zones: Sequence[ZoneInsight]) -> None:
        zone_layer = folium.FeatureGroup(name="Zones", show=True)
        for zone in zones:
            bounds = zone.bounds
            folium.Rectangle(
                bounds=[
                    [bounds.south, bounds.west],
                    [bounds.north, bounds.east],
                ],
                color="#2563eb",
                weight=2,
                dash_array="6",
                fill=False,
            ).add_to(zone_layer)

            folium.map.Marker(
                [zone.lat, zone.lon],
                icon=folium.DivIcon(
                    icon_size=(120, 30),
                    icon_anchor=(30, 15),
                    html=(
                        f'<div style="background: rgba(37,99,235,0.1); '
                        f'color:#1d4ed8; font-weight:600; padding:4px 10px; '
                        f'border-radius:9999px; border:1px solid #1d4ed833; '
                        f'font-size:12px;">Zone {zone.zone_id}</div>'
                    ),
                ),
            ).add_to(zone_layer)

        zone_layer.add_to(fmap)

    # Utilities ------------------------------------------------------------
    def _normalize_bbox(self, bbox: Dict[str, Any]) -> BoundingBox:
        return BoundingBox(
            south=float(self._as_float(bbox.get("south"))),
            west=float(self._as_float(bbox.get("west"))),
            north=float(self._as_float(bbox.get("north"))),
            east=float(self._as_float(bbox.get("east"))),
        )

    def _as_float(self, value: Any) -> float:
        if isinstance(value, list):
            if not value:
                raise ValueError("bbox value is empty")
            value = value[0]
        return float(value)

    def _transform_pop(self, pop: float) -> float:
        pop = max(0.0, float(pop))
        if self.scale == "linear":
            return pop
        if self.scale == "sqrt":
            return pop ** 0.5
        return math.log1p(pop)

    def _quantile(self, values: List[float], q: float) -> float:
        if not values:
            return 0.0
        if q <= 0:
            return values[0]
        if q >= 1:
            return values[-1]

        n = len(values)
        pos = (n - 1) * q
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return values[lo]
        weight = pos - lo
        return values[lo] * (1 - weight) + values[hi] * weight

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _fmt_int(self, value: float) -> str:
        return f"{int(round(value)):,}".replace(",", " ")


__all__ = ["MapBuilder"]
