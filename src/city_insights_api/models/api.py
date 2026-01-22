"""Pydantic schemas exposed by the HTTP layer."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

from .domain import AgentPlace, BoundingBox, KMeansMetrics, ZoneInsight


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


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
    session_id: Optional[str] = None


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    updated_at: Optional[datetime] = None


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: Optional[datetime] = None
    view_file: Optional[str] = None


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    messages: List[ChatHistoryMessage]
