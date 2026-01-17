"""Pydantic schemas exposed by the HTTP layer."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from .domain import AgentPlace, BoundingBox, KMeansMetrics, ZoneInsight


class ChatRequest(BaseModel):
    message: str


class ParsedInfo(BaseModel):
    city: Optional[str] = None
    category_key: Optional[str] = None
    category_label: Optional[str] = None
    bbox_mode: Optional[str] = None


class ChatData(BaseModel):
    count: int
    bbox: BoundingBox
    places: List[AgentPlace]
    result_file: str
    result_filename: str
    view_file: Optional[str] = None
    inhabitants_file: Optional[str] = None
    map_file: Optional[str] = None
    kmeans: Optional[KMeansMetrics] = None
    zones: Optional[List[ZoneInsight]] = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    answer: Optional[str] = None
    parsed: Optional[ParsedInfo] = None
    data: Optional[ChatData] = None
    message: Optional[str] = None
