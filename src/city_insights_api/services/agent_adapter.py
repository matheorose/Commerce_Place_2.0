"""Wrapper loading the legacy LangChain agent without touching the original code."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

from ..core.config import settings
from ..models.domain import AgentPayload, AgentPlace, BoundingBox


class AgentAdapter:
    """Provides a typed interface around the historical agent script."""

    def __init__(self, agent_path: Path | None = None) -> None:
        self.agent_path = agent_path or settings.legacy_agent_path
        if not self.agent_path.exists():
            raise FileNotFoundError(
                f"Legacy agent introuvable: {self.agent_path}. Copiez le script dans legacy_agent/ ou définissez LEGACY_AGENT_PATH."
            )
        self._module = self._load_module()

    def _load_module(self) -> ModuleType:
        spec = importlib.util.spec_from_file_location("city_agent_legacy", self.agent_path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise ImportError(f"Impossible de charger le script agent: {self.agent_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Public API -----------------------------------------------------------
    def run_from_message(self, message: str) -> AgentPayload:
        raw = self._invoke("run_agent_from_message", message)
        return self._to_model(raw)

    def run_from_params(self, **kwargs: Any) -> AgentPayload:
        raw = self._invoke("run_agent_from_params", **kwargs)
        return self._to_model(raw)

    # Internal helpers -----------------------------------------------------
    def _invoke(self, func_name: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        func = getattr(self._module, func_name, None)
        if func is None:
            raise AttributeError(f"Le module agent ne définit pas {func_name}")
        return func(*args, **kwargs)

    def _normalize_bbox(self, bbox: Dict[str, Any]) -> BoundingBox:
        try:
            return BoundingBox(
                south=float(bbox.get("south")),
                west=float(bbox.get("west")),
                north=float(bbox.get("north")),
                east=float(bbox.get("east")),
            )
        except (TypeError, ValueError) as exc:  # pragma: no cover - guards legacy payloads
            raise ValueError(f"bbox invalide dans le résultat agent: {bbox}") from exc

    def _to_model(self, data: Dict[str, Any]) -> AgentPayload:
        bbox = self._normalize_bbox(data.get("bbox", {}))
        places = [
            AgentPlace(
                id=str(place.get("id")) if place.get("id") is not None else None,
                name=place.get("name"),
                lat=float(place.get("lat")),
                lon=float(place.get("lon")),
            )
            for place in data.get("places", [])
            if place.get("lat") is not None and place.get("lon") is not None
        ]

        payload = data.get("payload") or {}

        city = data.get("city") or "unknown"
        category_key = data.get("category_key") or "unknown"

        result_file_str = data.get("result_file")
        if not result_file_str:
            raise ValueError("result_file absent du résultat agent")

        result_filename = data.get("result_filename") or Path(result_file_str).name

        return AgentPayload(
            city=city,
            category_key=category_key,
            category_label=data.get("category_label"),
            bbox=bbox,
            bbox_mode=data.get("bbox_mode"),
            expand_ratio=data.get("expand_ratio"),
            count=int(data.get("count", 0)),
            places=places,
            result_file=Path(result_file_str),
            result_filename=result_filename,
            payload=payload,
        )


__all__ = ["AgentAdapter"]
