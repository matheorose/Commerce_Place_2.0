"""Domain models shared between services and the API layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    south: float
    west: float
    north: float
    east: float


class AgentPlace(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    lat: float
    lon: float


class AgentPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    city: str
    category_key: str
    category_label: Optional[str] = None
    bbox: BoundingBox
    bbox_mode: Optional[str] = None
    expand_ratio: Optional[float] = None
    count: int
    places: List[AgentPlace] = Field(default_factory=list)
    result_file: Path
    result_filename: str
    payload: dict[str, Any] = Field(default_factory=dict)


class KMeansMetrics(BaseModel):
    k_values: List[int]
    inertia: List[float]
    silhouette: List[float]
    davies_bouldin: List[float]


class ZoneInsight(BaseModel):
    zone_id: int
    lat: float
    lon: float
    population: float
    existing_commerces: int
    bounds: BoundingBox


class PipelineArtifacts(BaseModel):
    city: str
    category: str
    bbox: BoundingBox
    inhabitants_file: Path
    commerce_file: Path
    map_file: Path
    kmeans: Optional[KMeansMetrics] = None
    zones: List[ZoneInsight] = Field(default_factory=list)
