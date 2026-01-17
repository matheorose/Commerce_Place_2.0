"""HTTP routes exposed by the FastAPI application."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core.config import settings
from ..models.api import ChatData, ChatRequest, ChatResponse, ParsedInfo
from ..services.conversation_agent import CityInsightsAgent

logger = logging.getLogger(__name__)

router = APIRouter()
try:
    city_agent = CityInsightsAgent()
except Exception as exc:  # noqa: BLE001
    logger.warning("Impossible d'initialiser l'agent conversationnel: %s", exc)
    city_agent = None


@router.get("/health")
def healthcheck() -> dict[str, bool]:
    return {"ok": True}


@router.get("/views/{filename}")
def get_view(filename: str) -> FileResponse:
    safe_name = os.path.basename(filename)
    file_path = settings.views_dir / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(file_path)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if city_agent is None:
        return ChatResponse(success=False, message="Agent non initialisé (clé API manquante ?)")

    try:
        outcome = city_agent.run(request.message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent error")
        return ChatResponse(success=False, message=str(exc))

    if not outcome.fetch:
        return ChatResponse(success=True, answer=outcome.answer)

    fetch = outcome.fetch
    analysis = outcome.analysis

    parsed = ParsedInfo(
        city=fetch.city,
        category_key=fetch.category_key,
        category_label=fetch.category_label,
        bbox_mode=fetch.bbox_mode,
    )

    data = ChatData(
        count=fetch.count,
        bbox=analysis.bbox if analysis else fetch.bbox,
        places=fetch.places,
        result_file=str(fetch.result_file),
        result_filename=fetch.result_filename,
        view_file=analysis.map_file.name if analysis else None,
        inhabitants_file=str(analysis.inhabitants_file) if analysis else None,
        map_file=str(analysis.map_file) if analysis else None,
        kmeans=analysis.kmeans if analysis else None,
        zones=analysis.zones if analysis else None,
    )

    return ChatResponse(success=True, answer=outcome.answer, parsed=parsed, data=data)


__all__ = ["router"]
