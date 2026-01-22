"""HTTP routes exposed by the FastAPI application."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..core.config import settings
from ..models.api import (
    ChatData,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionSummary,
    ParsedInfo,
)
from ..services.conversation_agent import CityInsightsAgent, ConversationIntent
from ..services.chat_history import ChatHistoryStore

logger = logging.getLogger(__name__)

router = APIRouter()
try:
    city_agent = CityInsightsAgent()
except Exception as exc:  # noqa: BLE001
    logger.warning("Impossible d'initialiser l'agent conversationnel: %s", exc)
    city_agent = None

try:
    history_store = ChatHistoryStore()
except Exception as exc:  # noqa: BLE001
    logger.warning("Impossible d'initialiser l'historique de chat: %s", exc)
    history_store = None

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
    if history_store is None:
        raise HTTPException(status_code=503, detail="Historique indisponible (MongoDB absent ?)")

    session_id, _ = history_store.ensure_session(request.session_id)
    prior_turns = history_store.get_recent_turns(session_id)
    prior_users = history_store.get_recent_user_messages(session_id)

    try:
        outcome = city_agent.run(
            request.message,
            session_id=session_id,
            prior_turns=prior_turns,
            prior_user_messages=prior_users,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent error")
        fallback = city_agent.build_error_answer(request.message, exc)
        history_store.record_turn(session_id, request.message, fallback)
        return ChatResponse(success=True, answer=fallback, session_id=session_id)

    assistant_view_file = None
    if outcome.map_file:
        assistant_view_file = outcome.map_file.name

    history_store.record_turn(
        session_id,
        request.message,
        outcome.answer,
        assistant_view_file=assistant_view_file,
    )

    if history_store.needs_title(session_id):
        title = city_agent.build_title(request.message, outcome.answer)
        history_store.update_title(session_id, title)

    if not outcome.fetch:
        return ChatResponse(success=True, answer=outcome.answer, session_id=session_id)

    fetch = outcome.fetch
    analysis = outcome.analysis
    map_path = outcome.map_file

    parsed = ParsedInfo(
        city=fetch.city,
        category_key=fetch.category_key,
        category_label=fetch.category_label,
        bbox_mode=fetch.bbox_mode,
    )

    places_for_ui = fetch.places if outcome.intent == ConversationIntent.LISTING else []

    data = ChatData(
        count=fetch.count,
        bbox=analysis.bbox if analysis else fetch.bbox,
        places=places_for_ui,
        result_file=str(fetch.result_file),
        result_filename=fetch.result_filename,
        view_file=map_path.name if map_path else None,
        inhabitants_file=str(analysis.inhabitants_file) if analysis else None,
        map_file=str(map_path) if map_path else None,
        kmeans=analysis.kmeans if analysis else None,
        zones=analysis.zones if analysis else None,
    )

    return ChatResponse(
        success=True,
        answer=outcome.answer,
        parsed=parsed,
        data=data,
        session_id=session_id,
    )


@router.get("/chat/sessions", response_model=list[ChatSessionSummary])
def list_sessions() -> list[ChatSessionSummary]:
    if history_store is None:
        return []
    return history_store.list_sessions()


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(session_id: str) -> ChatSessionDetail:
    if history_store is None:
        raise HTTPException(status_code=503, detail="Historique indisponible")
    detail = history_store.get_session(session_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return ChatSessionDetail(**detail)


__all__ = ["router"]
