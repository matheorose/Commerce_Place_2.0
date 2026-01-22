"""Mongo-backed storage for chat sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from bson import ObjectId
from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection

from ..core.config import Settings, settings


class ChatHistoryStore:
    """Persists chat sessions and provides helpers for context retrieval."""

    def __init__(self, config: Settings = settings) -> None:
        self.client = MongoClient(config.mongo_dsn)
        self.db = self.client[config.mongo_db_name]
        self.collection: Collection = self.db[config.mongo_collection]
        self.collection.create_index([("updated_at", DESCENDING)], name="updated_at_idx")

    # Session lifecycle --------------------------------------------------
    def ensure_session(self, session_id: Optional[str]) -> Tuple[str, bool]:
        """Return an existing session id or create a new one.

        Returns (session_id, created_flag).
        """
        if session_id:
            try:
                doc = self.collection.find_one({"_id": ObjectId(session_id)}, {"_id": 1})
                if doc:
                    return session_id, False
            except Exception:  # noqa: BLE001 - invalid ids are ignored
                pass
        new_id = self._create_session("Conversation en cours", has_title=False)
        return new_id, True

    def _create_session(self, title: str, *, has_title: bool) -> str:
        now = datetime.now(timezone.utc)
        result = self.collection.insert_one(
            {
                "title": title,
                "has_title": has_title,
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
        )
        return str(result.inserted_id)

    def needs_title(self, session_id: str) -> bool:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return False
        doc = self.collection.find_one(
            {"_id": obj_id},
            {"has_title": 1},
        )
        return bool(doc and not doc.get("has_title"))

    def update_title(self, session_id: str, title: str) -> None:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return
        safe_title = title.strip() or "Nouvelle conversation"
        self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"title": safe_title[:80], "has_title": True}},
        )

    # Persistence --------------------------------------------------------
    def record_turn(
        self,
        session_id: str,
        user_message: str,
        agent_message: str,
        *,
        assistant_view_file: Optional[str] = None,
    ) -> None:
        try:
            obj_id = ObjectId(session_id)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Identifiant de session invalide") from exc
        now = datetime.now(timezone.utc)
        payload = [
            {"role": "user", "content": user_message, "created_at": now, "view_file": None},
            {"role": "assistant", "content": agent_message, "created_at": now, "view_file": assistant_view_file},
        ]
        self.collection.update_one(
            {"_id": obj_id},
            {
                "$push": {"messages": {"$each": payload}},
                "$set": {"updated_at": now},
            },
            upsert=True,
        )

    # Retrieval helpers --------------------------------------------------
    def get_recent_turns(self, session_id: str, limit: int = 5) -> List[Tuple[str, str]]:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return []
        doc = self.collection.find_one(
            {"_id": obj_id},
            {"messages": {"$slice": -limit * 2}},
        )
        if not doc:
            return []
        messages = doc.get("messages", [])
        turns: List[Tuple[str, str]] = []
        current_user: Optional[str] = None
        for message in messages:
            role = message.get("role")
            content = message.get("content") or ""
            if role == "user":
                current_user = content
            elif role == "assistant" and current_user is not None:
                turns.append((current_user, content))
                current_user = None
        return turns[-limit:]

    def get_recent_user_messages(self, session_id: str, limit: int = 5) -> List[str]:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return []
        doc = self.collection.find_one(
            {"_id": obj_id},
            {"messages": {"$slice": -limit * 2}},
        )
        if not doc:
            return []
        return [msg.get("content", "") for msg in doc.get("messages", []) if msg.get("role") == "user"][-limit:]

    def list_sessions(self, limit: int = 20) -> List[dict]:
        cursor = (
            self.collection.find({}, {"title": 1, "updated_at": 1})
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return [
            {
                "id": str(doc["_id"]),
                "title": doc.get("title") or "Conversation",
                "updated_at": doc.get("updated_at"),
            }
            for doc in cursor
        ]

    def get_session(self, session_id: str) -> Optional[dict]:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return None
        doc = self.collection.find_one(
            {"_id": obj_id},
            {"title": 1, "messages": 1},
        )
        if not doc:
            return None
        messages = [
            {
                "role": entry.get("role", "assistant"),
                "content": entry.get("content") or "",
                "created_at": entry.get("created_at"),
                "view_file": entry.get("view_file"),
            }
            for entry in doc.get("messages", [])
        ]
        return {
            "id": str(doc["_id"]),
            "title": doc.get("title") or "Conversation",
            "messages": messages,
        }

    def delete_session(self, session_id: str) -> None:
        try:
            obj_id = ObjectId(session_id)
        except Exception:  # noqa: BLE001
            return
        self.collection.delete_one({"_id": obj_id})
